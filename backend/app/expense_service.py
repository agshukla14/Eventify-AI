import json
import uuid
from datetime import datetime
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
        category_spending: Dict[str, float] = {}
        total_spent = 0.0

        for exp in expenses:
            cat_norm = exp.category.strip().lower()
            category_spending[cat_norm] = category_spending.get(cat_norm, 0.0) + exp.amount
            total_spent += exp.amount

        try:
            plan_data = json.loads(event_record.plan_json)
            budget = plan_data.get("budget", {})
            items = budget.get("items", [])

            for item in items:
                cat_norm = item.get("category", "").strip().lower()
                matched_spent = category_spending.get(cat_norm, 0.0)
                item["actual_spent"] = round(matched_spent, 2)

            budget["total_actual_spent"] = round(total_spent, 2)
            total_budget = budget.get("total_budget", event_record.total_budget)
            budget["is_over_budget"] = total_spent > total_budget
            budget["over_budget_amount"] = max(0.0, round(total_spent - total_budget, 2))

            event_record.plan_json = json.dumps(plan_data)
            event_record.updated_at = datetime.utcnow().isoformat()
            self.db.commit()
            self.db.refresh(event_record)
        except Exception as e:
            print(f"Error syncing actual spent to plan: {e}")

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

        # Planned allocations from event budget (which includes Phase 1 optimizations if applied)
        planned_items = plan.budget.items
        categories_comparison: List[CategoryExpenseComparison] = []
        seen_categories = set()

        for item in planned_items:
            cat_name = item.category
            norm_cat = cat_name.strip().lower()
            seen_categories.add(norm_cat)

            planned = round(item.allocated_amount, 2)
            actual = round(cat_actual_map.get(norm_cat, 0.0), 2)
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

        # Check if there are any expenses logged in categories not originally in planned items
        for norm_cat, actual in cat_actual_map.items():
            if norm_cat not in seen_categories:
                # Find original casing from first matching expense
                first_exp = next((e for e in expenses if e.category.strip().lower() == norm_cat), None)
                cat_name = first_exp.category if first_exp else norm_cat.title()
                diff = -actual
                categories_comparison.append(
                    CategoryExpenseComparison(
                        category=cat_name,
                        planned_budget=0.0,
                        actual_spent=round(actual, 2),
                        remaining=0.0,
                        difference=diff,
                        is_overspent=True,
                        overspent_amount=round(actual, 2),
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
