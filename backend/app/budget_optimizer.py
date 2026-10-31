import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from .schemas import (
    FullEventPlan,
    BudgetSummary,
    BudgetItem,
    BudgetAnalysis,
    BudgetOptimizationResponse,
    CategoryOptimization,
    OptimizationExplanation,
)
from .repair_engine import DeterministicRepairEngine
from .gemini_client import GeminiClient, sanitize_user_input

logger = logging.getLogger(__name__)


def analyze_budget(budget: BudgetSummary) -> BudgetAnalysis:
    """Analyzes existing budget allocations to surface actionable savings insights."""
    items = budget.items
    total_budget = budget.total_budget
    total_allocated = budget.total_allocated
    total_spent = budget.total_actual_spent

    remaining_budget = round(max(0.0, total_budget - total_spent), 2)

    # Highest expense category (excluding contingency if other items exist)
    non_contingency = [i for i in items if not i.is_contingency]
    candidate_items = non_contingency if non_contingency else items

    highest_item = max(candidate_items, key=lambda x: x.allocated_amount) if candidate_items else None
    highest_cat = highest_item.category if highest_item else "General"
    highest_amt = highest_item.allocated_amount if highest_item else 0.0
    highest_pct = highest_item.percentage if highest_item else 0.0

    # Identify categories with high potential for cost optimization
    potential_savings = []
    for item in non_contingency:
        cat_lower = item.category.lower()
        # Decor, entertainment, attire, invitations, and large allocations (>12%) usually have high supplier variance
        if any(w in cat_lower for w in ["decor", "floral", "entertainment", "music", "attire", "invitation", "gift", "favor", "balloon"]):
            potential_savings.append(item.category)
        elif item.percentage >= 15.0 and "venue" not in cat_lower and "catering" not in cat_lower:
            potential_savings.append(item.category)

    if not potential_savings and non_contingency:
        # Default to the 2nd and 3rd largest expenses
        sorted_by_size = sorted(non_contingency, key=lambda x: x.allocated_amount, reverse=True)
        potential_savings = [i.category for i in sorted_by_size[1:3]]

    distribution = [
        {
            "category": i.category,
            "allocated_amount": i.allocated_amount,
            "percentage": i.percentage,
            "actual_spent": i.actual_spent,
            "is_contingency": i.is_contingency,
        }
        for i in items
    ]

    return BudgetAnalysis(
        total_budget=total_budget,
        total_allocated=total_allocated,
        remaining_budget=remaining_budget,
        total_actual_spent=total_spent,
        highest_expense_category=highest_cat,
        highest_expense_amount=highest_amt,
        highest_expense_percentage=highest_pct,
        potential_savings_categories=potential_savings,
        category_distribution=distribution,
    )


class SmartBudgetOptimizer:
    def __init__(self):
        self.gemini = GeminiClient()

    def optimize(self, plan: FullEventPlan, user_prompt: str) -> BudgetOptimizationResponse:
        sanitized_prompt = sanitize_user_input(user_prompt)

        # 1. Try Gemini AI if available
        if self.gemini.is_available():
            try:
                res = self._optimize_with_gemini(plan, sanitized_prompt)
                if res:
                    return res
            except Exception as e:
                logger.warning(f"Gemini budget optimization failed, falling back to rule engine: {e}")

        # 2. Fallback to smart deterministic rule optimizer
        return self._optimize_with_fallback(plan, sanitized_prompt)

    def _optimize_with_gemini(self, plan: FullEventPlan, user_prompt: str) -> Optional[BudgetOptimizationResponse]:
        from google.genai import types

        categories_summary = [
            {"category": i.category, "allocated": i.allocated_amount, "percentage": i.percentage, "is_contingency": i.is_contingency}
            for i in plan.budget.items
        ]

        system_instruction = """You are an elite Wedding & Celebration Financial Optimizer.
Analyze the current budget allocation and the user's natural language goal.
Return a single JSON object recommending revised category weights and a detailed savings explanation.

RULES:
1. Adhere strictly to user constraints. If user says "do not reduce catering", preserve catering 100%.
2. Never suggest negative budgets or eliminate contingency (keep ~8% contingency).
3. If user requests saving an absolute amount (e.g. ₹30,000) or percentage (e.g. 15%), calculate revised_total_budget accordingly.
4. Output JSON strictly adhering to this schema:
{
  "revised_total_budget": 2400000.0,
  "category_recommendations": [
    {"category": "Venue & Lodging", "weight": 25.0, "reason": "..."},
    {"category": "Catering & Bar", "weight": 25.0, "reason": "..."},
    {"category": "Contingency", "weight": 8.0, "reason": "..."}
  ],
  "where_money_saved": ["Reduced imported floral decor in favor of seasonal greenery", "..."],
  "why_recommended": "...",
  "expenses_preserved": ["Catering & Bar preserved at 100% per host requirement", "..."]
}
"""

        prompt_content = f"""
Event: {plan.intake.title} ({plan.intake.event_type.title()} in {plan.intake.city})
Guests: {plan.intake.guest_count}
Current Total Budget: {plan.budget.total_budget} {plan.budget.currency}
Current Allocations: {json.dumps(categories_summary, indent=2)}

User Optimization Request:
"{user_prompt}"
"""

        response = self.gemini.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[system_instruction, prompt_content],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )

        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(json)?\n", "", raw_text)
            raw_text = re.sub(r"\n```$", "", raw_text)

        parsed = json.loads(raw_text)

        revised_budget = float(parsed.get("revised_total_budget", plan.budget.total_budget))
        if revised_budget <= 0 or revised_budget > plan.budget.total_budget * 2:
            revised_budget = plan.budget.total_budget

        recs = parsed.get("category_recommendations", [])
        raw_items = []
        notes_by_cat = {}
        for r in recs:
            c_name = r.get("category", "")
            w = float(r.get("weight", 1.0))
            reason = r.get("reason", "")
            notes_by_cat[c_name.lower()] = reason
            raw_items.append({"category": c_name, "weight": w, "notes": reason})

        # Deterministic repair on recommended weights
        mock_intake = plan.intake.model_copy()
        mock_intake.total_budget = revised_budget
        optimized_summary = DeterministicRepairEngine.repair_budget(raw_items, mock_intake)

        return self._build_response(
            plan=plan,
            user_prompt=user_prompt,
            engine_used="gemini",
            revised_budget=revised_budget,
            optimized_summary=optimized_summary,
            where_saved=parsed.get("where_money_saved", []),
            why_recommended=parsed.get("why_recommended", "AI optimized allocation based on host goals."),
            expenses_preserved=parsed.get("expenses_preserved", []),
            notes_by_cat=notes_by_cat,
        )

    def _optimize_with_fallback(self, plan: FullEventPlan, user_prompt: str) -> BudgetOptimizationResponse:
        """
        Intelligent deterministic fallback optimizer when Gemini is unavailable.
        Parses constraints, target savings amounts/percentages, and category protection.
        """
        lower = user_prompt.lower()
        orig_budget = plan.budget.total_budget
        orig_items = plan.budget.items

        # 1. Detect target savings amount or percentage
        target_savings = 0.0
        # Check percentage savings: "save 15%", "reduce by 10%", "cut budget by 20%"
        pct_match = re.search(r"(?:save|reduce|cut|lower|decrease)\s+(?:.*?by\s+)?(\d+(?:\.\d+)?)\s*%", lower)
        # Check absolute amount savings: "reduce my wedding budget by ₹50,000", "save ₹30,000", "cut by 25000"
        amt_match = re.search(r"(?:save|reduce|cut|lower|decrease)\s+(?:.*?by\s+)?(?:₹|rs\.?|inr|\$|€)?\s*(\d+[\d,]+|\d{3,})", lower)

        if pct_match:
            pct_val = float(pct_match.group(1))
            pct_val = min(50.0, max(1.0, pct_val))
            target_savings = round((pct_val / 100.0) * orig_budget, 2)
        elif amt_match:
            raw_num = amt_match.group(1).replace(",", "")
            amt_val = float(raw_num)
            if amt_val > 0 and amt_val < orig_budget:
                target_savings = amt_val
            elif amt_val >= orig_budget:
                target_savings = round(orig_budget * 0.15, 2)
        else:
            # Default smart savings target of 10%
            target_savings = round(orig_budget * 0.10, 2)

        # 2. Detect protected categories ("do not reduce catering", "keep food high", "preserve photography")
        protected_cats = set()
        for i in orig_items:
            cat_name = i.category.lower()
            words = [w for w in cat_name.split() if len(w) > 3]
            for w in words:
                if (
                    f"do not reduce {w}" in lower
                    or f"don't reduce {w}" in lower
                    or f"keep {w}" in lower
                    or f"preserve {w}" in lower
                    or f"protect {w}" in lower
                ):
                    protected_cats.add(i.category.lower())

        # Also protect food/catering if user says "keep food quality high"
        if "food" in lower or "catering" in lower:
            for i in orig_items:
                if any(k in i.category.lower() for k in ["cater", "food", "bar"]):
                    protected_cats.add(i.category.lower())

        # 3. Detect specific categories user explicitly asked to reduce
        targeted_reduction_cats = set()
        for i in orig_items:
            cat_name = i.category.lower()
            words = [w for w in cat_name.split() if len(w) > 3]
            for w in words:
                if (
                    f"reduce {w}" in lower
                    or f"cut {w}" in lower
                    or f"lower {w}" in lower
                    or f"affordable {w}" in lower
                    or f"cheaper {w}" in lower
                ):
                    targeted_reduction_cats.add(i.category.lower())

        # 4. Check for reallocation: "reallocate photography to entertainment"
        realloc_match = re.search(r"reallocate\s+([a-z\s]+?)\s+(?:expenses?\s+)?to\s+([a-z\s]+)", lower)
        realloc_from = None
        realloc_to = None
        if realloc_match:
            r_from_query = realloc_match.group(1).strip()
            r_to_query = realloc_match.group(2).strip()
            for i in orig_items:
                if r_from_query in i.category.lower():
                    realloc_from = i.category
                if r_to_query in i.category.lower():
                    realloc_to = i.category

        # 5. Compute new category weights
        revised_budget = max(1000.0, orig_budget - target_savings) if "save" in lower or "reduce" in lower or pct_match or amt_match else orig_budget

        new_weights: List[Dict[str, Any]] = []
        where_saved = []
        expenses_preserved = []
        notes_by_cat = {}

        for item in orig_items:
            cat_l = item.category.lower()
            w = item.percentage

            if item.is_contingency:
                # Always preserve contingency at healthy 8%
                new_weights.append({"category": item.category, "weight": 8.0})
                notes_by_cat[cat_l] = "Emergency contingency buffer preserved."
                expenses_preserved.append("Emergency Contingency Fund (8%) preserved")
                continue

            # Case: Reallocation
            if realloc_from and realloc_to:
                if item.category == realloc_from:
                    cut_w = w * 0.35
                    new_weights.append({"category": item.category, "weight": max(1.0, w - cut_w)})
                    notes_by_cat[cat_l] = f"Reallocated surplus funds to {realloc_to}."
                    where_saved.append(f"Trimmed {item.category} surplus to fund {realloc_to}")
                    continue
                elif item.category == realloc_to:
                    add_w = w * 0.35
                    new_weights.append({"category": item.category, "weight": w + add_w})
                    notes_by_cat[cat_l] = f"Boosted allocation via reallocated funds from {realloc_from}."
                    continue

            # Case: Protected
            if cat_l in protected_cats:
                new_weights.append({"category": item.category, "weight": w * 1.05})
                notes_by_cat[cat_l] = "Priority category preserved per host instruction."
                expenses_preserved.append(f"{item.category} preserved at full quality")
                continue

            # Case: Targeted reduction
            if cat_l in targeted_reduction_cats:
                new_weights.append({"category": item.category, "weight": max(1.0, w * 0.75)})
                notes_by_cat[cat_l] = "Optimized via budget-friendly local vendor swaps."
                where_saved.append(f"Negotiated supplier and rental package discounts on {item.category}")
                continue

            # Standard flexible expense reduction (decor, entertainment, transport)
            if any(flx in cat_l for flx in ["decor", "floral", "entertainment", "music", "attire", "invitation", "logistics"]):
                new_weights.append({"category": item.category, "weight": max(1.0, w * 0.85)})
                notes_by_cat[cat_l] = "Streamlined non-essential expenses and decorative rentals."
                where_saved.append(f"Substituted premium rentals for local vendor packages in {item.category}")
            else:
                new_weights.append({"category": item.category, "weight": w})
                notes_by_cat[cat_l] = "Maintained standard allocation."

        if not expenses_preserved:
            expenses_preserved.append("Core celebration essentials and contingency reserve")

        if not where_saved:
            where_saved.append(f"Scaled non-critical category weights to achieve {plan.intake.currency} {target_savings:,.2f} total savings")

        why_rec = (
            f"Optimized budget allocations to fulfill: '{user_prompt}'. "
            f"Preserved primary experiential elements while trimming decorative rentals and secondary logistical costs."
        )

        # Deterministic normalization
        mock_intake = plan.intake.model_copy()
        mock_intake.total_budget = revised_budget
        optimized_summary = DeterministicRepairEngine.repair_budget(new_weights, mock_intake)

        return self._build_response(
            plan=plan,
            user_prompt=user_prompt,
            engine_used="fallback_rule_engine",
            revised_budget=revised_budget,
            optimized_summary=optimized_summary,
            where_saved=where_saved,
            why_recommended=why_rec,
            expenses_preserved=expenses_preserved,
            notes_by_cat=notes_by_cat,
        )

    def _build_response(
        self,
        plan: FullEventPlan,
        user_prompt: str,
        engine_used: str,
        revised_budget: float,
        optimized_summary: BudgetSummary,
        where_saved: List[str],
        why_recommended: str,
        expenses_preserved: List[str],
        notes_by_cat: Dict[str, str],
    ) -> BudgetOptimizationResponse:
        orig_items_by_cat = {i.category.lower(): i for i in plan.budget.items}
        categories: List[CategoryOptimization] = []

        for new_item in optimized_summary.items:
            cat_l = new_item.category.lower()
            orig = orig_items_by_cat.get(cat_l)
            orig_amt = orig.allocated_amount if orig else 0.0
            orig_pct = orig.percentage if orig else 0.0

            rec_amt = new_item.allocated_amount
            rec_pct = new_item.percentage

            savings = round(orig_amt - rec_amt, 2)
            pct_change = round(((rec_amt - orig_amt) / orig_amt * 100), 1) if orig_amt > 0 else 0.0

            note = notes_by_cat.get(cat_l, new_item.notes or "Adjusted allocation.")

            categories.append(
                CategoryOptimization(
                    category=new_item.category,
                    original_amount=orig_amt,
                    original_percentage=orig_pct,
                    recommended_amount=rec_amt,
                    recommended_percentage=rec_pct,
                    savings=savings,
                    percentage_change=pct_change,
                    notes=note,
                )
            )

        total_savings = round(max(0.0, plan.budget.total_budget - revised_budget), 2)
        if total_savings == 0.0:
            # Check if internal reallocations produced specific savings
            positive_savings = sum(c.savings for c in categories if c.savings > 0)
            if positive_savings > 0:
                saved_summary = f"{plan.budget.currency} {positive_savings:,.2f} reallocated across categories without changing total budget."
            else:
                saved_summary = f"Budget rebalanced to preserve 100% of critical services."
        else:
            saved_summary = f"Total savings of {plan.budget.currency} {total_savings:,.2f} ({(total_savings / plan.budget.total_budget * 100):.1f}% reduction)."

        explanation = OptimizationExplanation(
            where_money_saved=where_saved if isinstance(where_saved, list) else [str(where_saved)],
            why_recommended=why_recommended,
            expenses_preserved=expenses_preserved if isinstance(expenses_preserved, list) else [str(expenses_preserved)],
            total_saved_summary=saved_summary,
        )

        return BudgetOptimizationResponse(
            event_id=plan.event_id,
            user_prompt=user_prompt,
            engine_used=engine_used,
            original_total_budget=plan.budget.total_budget,
            revised_total_budget=revised_budget,
            total_savings=total_savings,
            currency=plan.budget.currency,
            categories=categories,
            explanation=explanation,
            optimized_budget_summary=optimized_summary,
        )
