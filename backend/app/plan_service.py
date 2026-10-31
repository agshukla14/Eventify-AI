import json
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy.orm import Session

from .models import EventModel
from .schemas import EventIntake, FullEventPlan, DashboardSummary
from .repair_engine import DeterministicRepairEngine, parse_date_safe
from .gemini_client import GeminiClient


class PlanService:
    def __init__(self, db: Session):
        self.db = db
        self.gemini = GeminiClient()

    def create_plan(self, intake: EventIntake, owner_id: Optional[str] = None) -> FullEventPlan:
        # Generate plan via Gemini or deterministic fallback
        plan = self.gemini.generate_event_plan(intake)

        # Persist to database
        event_record = EventModel(
            id=plan.event_id,
            owner_id=owner_id,
            title=intake.title,
            event_type=intake.event_type,
            date=intake.date,
            city=intake.city,
            guest_count=intake.guest_count,
            total_budget=intake.total_budget,
            currency=intake.currency,
            intake_json=json.dumps(intake.model_dump()),
            plan_json=json.dumps(plan.model_dump()),
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )
        self.db.add(event_record)
        self.db.commit()
        self.db.refresh(event_record)

        return plan

    def get_plan(self, event_id: str) -> Optional[FullEventPlan]:
        record = self.db.query(EventModel).filter(EventModel.id == event_id).first()
        if not record:
            return None
        data = json.loads(record.plan_json)
        return FullEventPlan(**data)

    def update_plan(self, event_id: str, updated_plan: FullEventPlan) -> FullEventPlan:
        # Ensure updated plan is run through the repair engine to maintain invariants
        repaired = DeterministicRepairEngine.repair_full_plan(
            raw_plan=updated_plan.model_dump(),
            intake=updated_plan.intake,
            existing_event_id=event_id,
        )

        record = self.db.query(EventModel).filter(EventModel.id == event_id).first()
        if record:
            record.title = repaired.intake.title
            record.event_type = repaired.intake.event_type
            record.date = repaired.intake.date
            record.city = repaired.intake.city
            record.guest_count = repaired.intake.guest_count
            record.total_budget = repaired.intake.total_budget
            record.currency = repaired.intake.currency
            record.intake_json = json.dumps(repaired.intake.model_dump())
            record.plan_json = json.dumps(repaired.model_dump())
            record.updated_at = repaired.updated_at
            self.db.commit()
            self.db.refresh(record)

        return repaired

    def list_events(self, user_id: Optional[str] = None) -> List[DashboardSummary]:
        query = self.db.query(EventModel)
        if user_id:
            if user_id == "usr_demo_organizer":
                query = query.filter((EventModel.owner_id == user_id) | (EventModel.owner_id.is_(None)))
            else:
                query = query.filter(EventModel.owner_id == user_id)
        records = query.order_by(EventModel.updated_at.desc()).all()
        summaries: List[DashboardSummary] = []
        today = date.today()

        for rec in records:
            try:
                plan_data = json.loads(rec.plan_json)
                plan = FullEventPlan(**plan_data)
                ev_date = parse_date_safe(plan.intake.date)
                days_left = (ev_date - today).days

                spent = plan.budget.total_actual_spent
                total_b = plan.budget.total_budget
                used_pct = round((spent / total_b * 100), 1) if total_b > 0 else 0.0

                tasks = plan.timeline.milestones
                t_total = len(tasks)
                t_done = sum(1 for t in tasks if t.status == "completed")
                t_pct = round((t_done / t_total * 100), 1) if t_total > 0 else 0.0

                v_total = len(plan.vendors)
                v_booked = sum(1 for v in plan.vendors if v.status in ["booked", "paid"])

                summaries.append(
                    DashboardSummary(
                        event_id=plan.event_id,
                        title=plan.intake.title,
                        event_type=plan.intake.event_type,
                        days_left=days_left,
                        total_budget=total_b,
                        total_spent=spent,
                        budget_used_percentage=used_pct,
                        tasks_total=t_total,
                        tasks_completed=t_done,
                        tasks_completion_percentage=t_pct,
                        vendors_total=v_total,
                        vendors_booked=v_booked,
                        high_risk_tasks_count=plan.timeline.high_risk_count,
                        is_over_budget=plan.budget.is_over_budget,
                        currency=plan.intake.currency,
                    )
                )
            except Exception:
                continue

        return summaries

    def delete_event(self, event_id: str) -> bool:
        record = self.db.query(EventModel).filter(EventModel.id == event_id).first()
        if not record:
            return False
        self.db.delete(record)
        self.db.commit()
        return True
