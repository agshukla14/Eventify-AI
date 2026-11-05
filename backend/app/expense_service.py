import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .models import EventModel, ExpenseModel
from .schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    CategoryExpenseComparison,
    BudgetAlert,
    ExpenseTrackingSummary,
    FullEventPlan,
)

logger = logging.getLogger(__name__)


def categories_match(cat1: str, cat2: str) -> bool:
    """Matches category names taking into account canonical category taxonomy."""
    c1 = (cat1 or "").strip().lower()
    c2 = (cat2 or "").strip().lower()
    if not c1 or not c2:
        return False
    if c1 == c2:
        return True
    try:
        from .budget_optimizer import map_category_to_canonical
        canon1, _, _ = map_category_to_canonical(c1)
        canon2, _, _ = map_category_to_canonical(c2)
        if canon1 and canon2 and canon1.lower() == canon2.lower():
            return True
    except Exception:
        pass
    return False


class ExpenseService:
    def __init__(self, db: Session):
        self.db = db

    def _sync_plan_actual_spent(self, event_record: EventModel):
        """
        Recompute actual spent per category and total actual spent from
        the SQLite expenses table, updating the event's plan_json so that
        all tabs (BudgetTab, DashboardStats) remain in 100% real-time sync.
        """
        if not event_record or not event_record.plan_json:
            return

        expenses = self.db.query(ExpenseModel).filter(ExpenseModel.event_id == event_record.id).all()

        try:
            plan_data = json.loads(event_record.plan_json)
            budget = plan_data.get("budget", {})
            items = budget.get("items", [])

            # Reset each item's actual_spent
            item_spents = {i.get("id", i.get("category")): Decimal("0.00") for i in items}

            # Map each expense to the most specific budget item (exact match first, then canonical)
            for exp in expenses:
                exp_cat = (exp.category or "").strip().lower()
                amt = Decimal(str(exp.amount or 0.0))

                # 1. Exact match
                matched_item = next((i for i in items if i.get("category", "").strip().lower() == exp_cat), None)
                if not matched_item:
                    # 2. Canonical match
                    matched_item = next((i for i in items if categories_match(exp.category, i.get("category", ""))), None)

                if matched_item:
                    key = matched_item.get("id", matched_item.get("category"))
                    item_spents[key] = item_spents.get(key, Decimal("0.00")) + amt

            for item in items:
                key = item.get("id", item.get("category"))
                item["actual_spent"] = float(round(item_spents.get(key, Decimal("0.00")), 2))

            total_spent = sum((Decimal(str(exp.amount or 0.0)) for exp in expenses), Decimal("0.00"))
            budget["total_actual_spent"] = float(round(total_spent, 2))
            total_budget = Decimal(str(budget.get("total_budget", event_record.total_budget)))
            budget["is_over_budget"] = total_spent > total_budget
            budget["over_budget_amount"] = float(max(Decimal("0.00"), round(total_spent - total_budget, 2)))

            event_record.plan_json = json.dumps(plan_data)
            event_record.updated_at = datetime.utcnow().isoformat()
            self.db.commit()
            self.db.refresh(event_record)
        except Exception as e:
            logger.error(f"Error syncing actual spent to plan: {e}")

    def create_expense(self, event_id: str, expense_in: ExpenseCreate) -> ExpenseResponse:
        event = self.db.query(EventModel).filter(EventModel.id == event_id).first()
        if not event:
            raise ValueError(f"Event '{event_id}' not found")

        expense_id = f"exp_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        expense = ExpenseModel(
            id=expense_id,
            event_id=event_id,
            expense_name=expense_in.expense_name.strip(),
            category=expense_in.category.strip(),
            amount=round(expense_in.amount, 2),
            expense_date=expense_in.expense_date,
            payment_status=expense_in.payment_status,
            payment_method=expense_in.payment_method.strip() if expense_in.payment_method else None,
            vendor_name=expense_in.vendor_name.strip() if expense_in.vendor_name else None,
            notes=expense_in.notes.strip() if expense_in.notes else None,
            created_at=now,
            updated_at=now,
        )

        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)

        # Update event's plan actual spent
        self._sync_plan_actual_spent(event)

        return ExpenseResponse(
            id=expense.id,
            event_id=expense.event_id,
            expense_name=expense.expense_name,
            category=expense.category,
            amount=expense.amount,
            expense_date=expense.expense_date,
            payment_status=expense.payment_status,
            payment_method=expense.payment_method,
            vendor_name=expense.vendor_name,
            notes=expense.notes,
            created_at=expense.created_at,
            updated_at=expense.updated_at,
        )

    def get_expense(self, event_id: str, expense_id: str) -> Optional[ExpenseResponse]:
        expense = (
            self.db.query(ExpenseModel)
            .filter(ExpenseModel.event_id == event_id, ExpenseModel.id == expense_id)
            .first()
        )
        if not expense:
            return None

        return ExpenseResponse(
            id=expense.id,
            event_id=expense.event_id,
            expense_name=expense.expense_name,
            category=expense.category,
            amount=expense.amount,
            expense_date=expense.expense_date,
            payment_status=expense.payment_status,
            payment_method=expense.payment_method,
            vendor_name=expense.vendor_name,
            notes=expense.notes,
            created_at=expense.created_at,
            updated_at=expense.updated_at,
        )

    def list_expenses(
        self,
        event_id: str,
        category: Optional[str] = None,
        payment_status: Optional[str] = None,
        search: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[ExpenseResponse]:
        query = self.db.query(ExpenseModel).filter(ExpenseModel.event_id == event_id)

        if category and category.lower() != "all":
            query = query.filter(ExpenseModel.category.ilike(category.strip()))

        if payment_status and payment_status.lower() != "all":
            query = query.filter(ExpenseModel.payment_status.ilike(payment_status.strip()))

        if start_date:
            query = query.filter(ExpenseModel.expense_date >= start_date)

        if end_date:
            query = query.filter(ExpenseModel.expense_date <= end_date)

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                (ExpenseModel.expense_name.ilike(search_pattern))
                | (ExpenseModel.vendor_name.ilike(search_pattern))
                | (ExpenseModel.notes.ilike(search_pattern))
                | (ExpenseModel.category.ilike(search_pattern))
            )

        expenses = query.order_by(desc(ExpenseModel.expense_date), desc(ExpenseModel.created_at)).all()

        return [
            ExpenseResponse(
                id=e.id,
                event_id=e.event_id,
                expense_name=e.expense_name,
                category=e.category,
                amount=e.amount,
                expense_date=e.expense_date,
                payment_status=e.payment_status,
                payment_method=e.payment_method,
                vendor_name=e.vendor_name,
                notes=e.notes,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in expenses
        ]

    def update_expense(
        self, event_id: str, expense_id: str, expense_in: ExpenseUpdate
    ) -> Optional[ExpenseResponse]:
        expense = (
            self.db.query(ExpenseModel)
            .filter(ExpenseModel.event_id == event_id, ExpenseModel.id == expense_id)
            .first()
        )
        if not expense:
            return None

        if expense_in.expense_name is not None:
            expense.expense_name = expense_in.expense_name.strip()
        if expense_in.category is not None:
            expense.category = expense_in.category.strip()
        if expense_in.amount is not None:
            expense.amount = round(expense_in.amount, 2)
        if expense_in.expense_date is not None:
            expense.expense_date = expense_in.expense_date
        if expense_in.payment_status is not None:
            expense.payment_status = expense_in.payment_status
        if expense_in.payment_method is not None:
            expense.payment_method = expense_in.payment_method.strip() if expense_in.payment_method else None
        if expense_in.vendor_name is not None:
            expense.vendor_name = expense_in.vendor_name.strip() if expense_in.vendor_name else None
        if expense_in.notes is not None:
            expense.notes = expense_in.notes.strip() if expense_in.notes else None

        expense.updated_at = datetime.utcnow().isoformat()
        self.db.commit()
        self.db.refresh(expense)

        # Sync actual spent to plan
        event = self.db.query(EventModel).filter(EventModel.id == event_id).first()
        if event:
            self._sync_plan_actual_spent(event)

        return ExpenseResponse(
            id=expense.id,
            event_id=expense.event_id,
            expense_name=expense.expense_name,
            category=expense.category,
            amount=expense.amount,
            expense_date=expense.expense_date,
            payment_status=expense.payment_status,
            payment_method=expense.payment_method,
            vendor_name=expense.vendor_name,
            notes=expense.notes,
            created_at=expense.created_at,
            updated_at=expense.updated_at,
        )

    def delete_expense(self, event_id: str, expense_id: str) -> bool:
        expense = (
            self.db.query(ExpenseModel)
            .filter(ExpenseModel.event_id == event_id, ExpenseModel.id == expense_id)
            .first()
        )
        if not expense:
            return False

        self.db.delete(expense)
        self.db.commit()

        # Sync actual spent to plan
        event = self.db.query(EventModel).filter(EventModel.id == event_id).first()
        if event:
            self._sync_plan_actual_spent(event)

        return True

    def adjust_budget_spent(
        self,
        event_id: str,
        category: str,
        target_spent: float,
        notes: Optional[str] = None,
    ) -> FullEventPlan:
        """
        Adjusts actual spending for a category in Budget Planner by creating
        or modifying auditable ExpenseModel ledger records in SQLite.
        Guarantees single source of truth between Budget Planner and Expense Tracking.
        """
        event = self.db.query(EventModel).filter(EventModel.id == event_id).first()
        if not event:
            raise ValueError(f"Event '{event_id}' not found")

        expenses = self.db.query(ExpenseModel).filter(ExpenseModel.event_id == event_id).all()

        has_exact = any((exp.category or "").strip().lower() == category.strip().lower() for exp in expenses)
        current_spent = Decimal("0.00")
        for exp in expenses:
            is_match = (
                (exp.category or "").strip().lower() == category.strip().lower()
                if has_exact
                else categories_match(exp.category, category)
            )
            if is_match:
                current_spent += Decimal(str(exp.amount or 0.0))

        target_d = Decimal(str(max(0.0, target_spent or 0.0))).quantize(Decimal("0.01"))
        delta = target_d - current_spent

        if delta > Decimal("0.00"):
            now_iso = datetime.utcnow().isoformat()
            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            adj_id = f"exp_adj_{uuid.uuid4().hex[:10]}"
            adj_exp = ExpenseModel(
                id=adj_id,
                event_id=event_id,
                expense_name=f"Manual Adjustment - {category}",
                category=category,
                amount=float(delta),
                expense_date=today_str,
                payment_status="Paid",
                payment_method="Direct Entry / Manual Adjustment",
                notes=notes or f"Auditable manual spending adjustment entered via Budget Planner for {category}.",
                created_at=now_iso,
                updated_at=now_iso,
            )
            self.db.add(adj_exp)
            self.db.commit()
        elif delta < Decimal("0.00"):
            needed_reduction = abs(delta)
            matching_adjs = [
                e for e in expenses
                if (
                    ((e.category or "").strip().lower() == category.strip().lower())
                    if has_exact
                    else categories_match(e.category, category)
                ) and "adjustment" in e.expense_name.lower()
            ]
            for adj in matching_adjs:
                adj_amt = Decimal(str(adj.amount))
                if adj_amt <= needed_reduction:
                    needed_reduction -= adj_amt
                    self.db.delete(adj)
                else:
                    adj.amount = float(adj_amt - needed_reduction)
                    adj.updated_at = datetime.utcnow().isoformat()
                    needed_reduction = Decimal("0.00")
                    break

            if needed_reduction > Decimal("0.00"):
                remaining_matching = [
                    e for e in expenses
                    if (
                        ((e.category or "").strip().lower() == category.strip().lower())
                        if has_exact
                        else categories_match(e.category, category)
                    ) and e not in matching_adjs
                ]
                if remaining_matching:
                    remaining_matching.sort(key=lambda x: x.created_at or "", reverse=True)
                    for exp in remaining_matching:
                        e_amt = Decimal(str(exp.amount))
                        if e_amt <= needed_reduction:
                            needed_reduction -= e_amt
                            self.db.delete(exp)
                        else:
                            exp.amount = float(e_amt - needed_reduction)
                            exp.updated_at = datetime.utcnow().isoformat()
                            needed_reduction = Decimal("0.00")
                            break
            self.db.commit()

        self._sync_plan_actual_spent(event)
        plan_data = json.loads(event.plan_json)
        return FullEventPlan(**plan_data)

    def get_expense_summary(self, event_id: str) -> ExpenseTrackingSummary:
        event = self.db.query(EventModel).filter(EventModel.id == event_id).first()
        if not event:
            raise ValueError(f"Event '{event_id}' not found")

        plan_data = json.loads(event.plan_json)
        plan = FullEventPlan(**plan_data)

        expenses = (
            self.db.query(ExpenseModel)
            .filter(ExpenseModel.event_id == event_id)
            .order_by(desc(ExpenseModel.expense_date))
            .all()
        )

        # Group actual expenses by category
        cat_actual_map: Dict[str, float] = {}
        paid_count = 0
        pending_count = 0
        for exp in expenses:
            norm_cat = exp.category.strip().lower()
            cat_actual_map[norm_cat] = cat_actual_map.get(norm_cat, 0.0) + exp.amount
            if exp.payment_status == "Paid":
                paid_count += 1
            else:
                pending_count += 1

        # Planned allocations from event budget
        planned_items = plan.budget.items
        categories_comparison: List[CategoryExpenseComparison] = []
        seen_expense_cats = set()

        for item in planned_items:
            cat_name = item.category
            matched_expenses = [e for e in expenses if categories_match(e.category, cat_name)]
            actual = round(sum(e.amount for e in matched_expenses), 2)
            for e in matched_expenses:
                seen_expense_cats.add(e.category.strip().lower())

            planned = round(item.allocated_amount, 2)
            diff = round(planned - actual, 2)
            rem = max(0.0, diff)
            is_over = actual > planned
            over_amt = max(0.0, round(actual - planned, 2))
            util_pct = round((actual / planned * 100), 1) if planned > 0 else (100.0 if actual > 0 else 0.0)

            categories_comparison.append(
                CategoryExpenseComparison(
                    category=cat_name,
                    planned_budget=planned,
                    actual_spent=actual,
                    remaining=rem,
                    difference=diff,
                    is_overspent=is_over,
                    overspent_amount=over_amt,
                    utilization_percentage=util_pct,
                )
            )

        # Check if there are any expenses logged in categories not matching planned items
        for exp in expenses:
            exp_norm = exp.category.strip().lower()
            if exp_norm not in seen_expense_cats:
                seen_expense_cats.add(exp_norm)
                other_matching = [e for e in expenses if e.category.strip().lower() == exp_norm]
                unmatched_spent = round(sum(e.amount for e in other_matching), 2)
                categories_comparison.append(
                    CategoryExpenseComparison(
                        category=exp.category,
                        planned_budget=0.0,
                        actual_spent=unmatched_spent,
                        remaining=0.0,
                        difference=-unmatched_spent,
                        is_overspent=True,
                        overspent_amount=unmatched_spent,
                        utilization_percentage=100.0,
                    )
                )

        # Totals
        total_budget = round(plan.budget.total_budget, 2)
        total_actual = round(sum(e.amount for e in expenses), 2)
        rem_budget = round(total_budget - total_actual, 2)
        total_util_pct = (
            round((total_actual / total_budget * 100), 1) if total_budget > 0 else 0.0
        )
        is_over_budget = total_actual > total_budget
        over_budget_amt = max(0.0, round(total_actual - total_budget, 2))

        # Highest spending category
        highest_cat = ""
        highest_amt = 0.0
        for comp in categories_comparison:
            if comp.actual_spent > highest_amt:
                highest_amt = comp.actual_spent
                highest_cat = comp.category

        # Intelligent Budget Alerts
        alerts: List[BudgetAlert] = []

        # 1. Total budget exceeded
        if is_over_budget:
            alerts.append(
                BudgetAlert(
                    level="danger",
                    title="Total Budget Exceeded!",
                    message=(
                        f"Total spending of {total_actual:,.2f} {plan.intake.currency} has exceeded "
                        f"the overall budget of {total_budget:,.2f} by {over_budget_amt:,.2f} {plan.intake.currency}."
                    ),
                )
            )
        # 2. Total budget >= 80% threshold
        elif total_util_pct >= 80.0:
            alerts.append(
                BudgetAlert(
                    level="warning",
                    title="80% Budget Threshold Reached",
                    message=(
                        f"You have utilized {total_util_pct}% ({total_actual:,.2f} / {total_budget:,.2f} {plan.intake.currency}) "
                        "of your total event budget."
                    ),
                )
            )

        # 3. Category-level overspending alerts
        for comp in categories_comparison:
            if comp.is_overspent:
                alerts.append(
                    BudgetAlert(
                        level="danger",
                        category=comp.category,
                        title=f"Overspending in {comp.category}",
                        message=(
                            f"Spent {comp.actual_spent:,.2f} {plan.intake.currency} exceeding the planned "
                            f"{comp.planned_budget:,.2f} by {comp.overspent_amount:,.2f} {plan.intake.currency} "
                            f"({comp.utilization_percentage}% utilized)."
                        ),
                    )
                )
            elif comp.planned_budget > 0 and 85.0 <= comp.utilization_percentage <= 100.0:
                alerts.append(
                    BudgetAlert(
                        level="warning",
                        category=comp.category,
                        title=f"{comp.category} Approaching Budget Limit",
                        message=(
                            f"{comp.category} has reached {comp.utilization_percentage}% of its planned budget "
                            f"({comp.actual_spent:,.2f} / {comp.planned_budget:,.2f} {plan.intake.currency})."
                        ),
                    )
                )

        # 4. Healthy budget indicator if no warnings/dangers
        if not alerts:
            alerts.append(
                BudgetAlert(
                    level="info",
                    title="Healthy Budget Pacing",
                    message=(
                        f"All expenses are currently well-paced. {rem_budget:,.2f} {plan.intake.currency} "
                        f"remaining ({100.0 - total_util_pct:.1f}% unspent)."
                    ),
                )
            )

        return ExpenseTrackingSummary(
            event_id=event_id,
            total_event_budget=total_budget,
            total_actual_spent=total_actual,
            remaining_budget=rem_budget,
            budget_utilization_percentage=total_util_pct,
            is_over_budget=is_over_budget,
            over_budget_amount=over_budget_amt,
            currency=plan.intake.currency,
            categories=categories_comparison,
            alerts=alerts,
            total_expenses_count=len(expenses),
            paid_expenses_count=paid_count,
            pending_expenses_count=pending_count,
            highest_spending_category=highest_cat,
            highest_spending_amount=highest_amt,
        )
