import json
from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from .models import (
    EventModel,
    ExpenseModel,
    GuestModel,
    EventVendorBookingModel,
    EventWeatherPlanModel,
    UserModel,
)
from .schemas import (
    ExecutiveDashboardResponse,
    ExecutiveKpiMetrics,
    UpcomingEventItem,
    RecentActivityItem,
    BudgetUtilizationCategory,
    GuestRsvpBreakdown,
    VendorSummaryStats,
    ExecutiveWeatherAlert,
)


class ExecutiveDashboardService:
    def __init__(self, db: Session, user: Optional[UserModel] = None):
        self.db = db
        self.user = user

    def _get_base_events_query(self):
        query = self.db.query(EventModel)
        if self.user:
            if self.user.id == "usr_demo_organizer":
                query = query.filter((EventModel.owner_id == self.user.id) | (EventModel.owner_id.is_(None)))
            else:
                query = query.filter(EventModel.owner_id == self.user.id)
        return query

    def get_executive_summary(self, event_id: Optional[str] = None) -> ExecutiveDashboardResponse:
        today_date = date.today()
        today_str = today_date.isoformat()

        events = self._get_base_events_query().all()
        event_ids = [ev.id for ev in events]

        total_events_count = len(events)

        # Filter target events if event_id is supplied with strict IDOR verification
        target_event = None
        if event_id:
            target_event = next((ev for ev in events if ev.id == event_id), None)
            if not target_event:
                # Check whether the event belongs to another user
                other_ev = self.db.query(EventModel).filter(EventModel.id == event_id).first()
                if other_ev:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access forbidden: You do not have permission to access this celebration plan.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Event '{event_id}' not found.",
                )

        # 1. Upcoming Events
        upcoming_events_list: List[UpcomingEventItem] = []
        for ev in events:
            try:
                ev_date = datetime.strptime(ev.date[:10], "%Y-%m-%d").date()
                days_left = (ev_date - today_date).days
            except Exception:
                days_left = 0

            # Compute actual spent for this event
            spent = (
                self.db.query(func.coalesce(func.sum(ExpenseModel.amount), 0.0))
                .filter(ExpenseModel.event_id == ev.id)
                .scalar()
            ) or 0.0

            # Check weather risk if available
            w_plan = (
                self.db.query(EventWeatherPlanModel)
                .filter(EventWeatherPlanModel.event_id == ev.id)
                .order_by(desc(EventWeatherPlanModel.created_at))
                .first()
            )
            risk_level = "Low"
            if w_plan and w_plan.weather_summary_json:
                try:
                    w_obj = json.loads(w_plan.weather_summary_json)
                    risk_level = w_obj.get("risk_assessment", {}).get("overall_risk_level", "Low")
                except Exception:
                    pass

            upcoming_events_list.append(
                UpcomingEventItem(
                    event_id=ev.id,
                    title=ev.title,
                    event_type=ev.event_type,
                    date=ev.date,
                    city=ev.city,
                    days_left=days_left,
                    total_budget=round(ev.total_budget, 2),
                    actual_spent=round(float(spent), 2),
                    guest_count=ev.guest_count,
                    weather_risk_level=risk_level,
                )
            )

        # Sort upcoming events: future first, closest date first
        upcoming_events_list.sort(key=lambda x: (x.days_left < 0, abs(x.days_left)))
        upcoming_events_count = sum(1 for e in upcoming_events_list if e.days_left >= 0)

        # 2. Budget & Expense Calculations
        if target_event:
            total_planned = round(target_event.total_budget, 2)
            total_spent = round(
                float(
                    self.db.query(func.coalesce(func.sum(ExpenseModel.amount), 0.0))
                    .filter(ExpenseModel.event_id == target_event.id)
                    .scalar()
                    or 0.0
                ),
                2,
            )
        else:
            total_planned = round(sum(ev.total_budget for ev in events), 2)
            if event_ids:
                total_spent = round(
                    float(
                        self.db.query(func.coalesce(func.sum(ExpenseModel.amount), 0.0))
                        .filter(ExpenseModel.event_id.in_(event_ids))
                        .scalar()
                        or 0.0
                    ),
                    2,
                )
            else:
                total_spent = 0.0

        remaining_budget = round(total_planned - total_spent, 2)

        # 3. Guest Stats
        active_ids = [target_event.id] if target_event else event_ids
        if active_ids:
            all_guests = self.db.query(GuestModel).filter(GuestModel.event_id.in_(active_ids)).all()
        else:
            all_guests = []

        confirmed_guests = 0
        total_attending = 0
        pending_rsvps = 0
        declined_guests = 0

        for g in all_guests:
            status_norm = (g.rsvp_status or "").lower()
            if status_norm in ["confirmed", "attending"]:
                confirmed_guests += 1
                total_attending += 1 + (g.plus_ones or 0)
            elif status_norm in ["declined", "not attending"]:
                declined_guests += 1
            else:
                pending_rsvps += 1

        # 4. Vendor Bookings
        if active_ids:
            all_bookings = (
                self.db.query(EventVendorBookingModel)
                .filter(EventVendorBookingModel.event_id.in_(active_ids))
                .all()
            )
        else:
            all_bookings = []

        booked_count = sum(1 for b in all_bookings if b.booking_status.lower() in ["booked", "paid", "contracted"])
        shortlisted_count = sum(1 for b in all_bookings if b.booking_status.lower() in ["shortlisted", "contacted"])
        total_contracted = round(sum(b.agreed_price for b in all_bookings if b.agreed_price), 2)
        advance_paid = round(sum(b.advance_payment for b in all_bookings if b.advance_payment), 2)

        # 5. Budget Utilization Categories
        # Retrieve planned categories from selected or first event plan_json
        category_spent_map: Dict[str, float] = {}
        if active_ids:
            exp_groups = (
                self.db.query(ExpenseModel.category, func.sum(ExpenseModel.amount))
                .filter(ExpenseModel.event_id.in_(active_ids))
                .group_by(ExpenseModel.category)
                .all()
            )
            for cat, amt in exp_groups:
                category_spent_map[cat] = float(amt)

        budget_util_list: List[BudgetUtilizationCategory] = []
        sample_event = target_event if target_event else (events[0] if events else None)
        if sample_event and sample_event.plan_json:
            try:
                plan_dict = json.loads(sample_event.plan_json)
                b_items = plan_dict.get("budget", {}).get("items", [])
                for it in b_items:
                    cat_name = it.get("category", "General")
                    alloc = float(it.get("allocated_amount", 0.0))
                    sp = category_spent_map.get(cat_name, 0.0)
                    pct = round((sp / alloc * 100), 1) if alloc > 0 else 0.0
                    budget_util_list.append(
                        BudgetUtilizationCategory(
                            category=cat_name,
                            allocated=round(alloc, 2),
                            spent=round(sp, 2),
                            percentage_used=pct,
                        )
                    )
            except Exception:
                pass

        if not budget_util_list:
            # Fallback if no parsed items
            for cat, amt in category_spent_map.items():
                budget_util_list.append(
                    BudgetUtilizationCategory(
                        category=cat,
                        allocated=round(amt * 1.2, 2),
                        spent=round(amt, 2),
                        percentage_used=round((amt / (amt * 1.2)) * 100, 1),
                    )
                )

        # 6. Recent Activity Feed
        recent_activities: List[RecentActivityItem] = []

        # Recent expenses
        recent_expenses = (
            self.db.query(ExpenseModel)
            .filter(ExpenseModel.event_id.in_(active_ids))
            .order_by(desc(ExpenseModel.created_at))
            .limit(4)
            .all()
            if active_ids
            else []
        )
        for re in recent_expenses:
            recent_activities.append(
                RecentActivityItem(
                    id=f"act_exp_{re.id}",
                    activity_type="expense",
                    title=f"Expense Recorded: {re.expense_name}",
                    description=f"₹{re.amount:,.0f} paid for {re.category} ({re.payment_status})",
                    timestamp=re.expense_date,
                    badge="Expense",
                )
            )

        # Recent RSVPs
        recent_guests = (
            self.db.query(GuestModel)
            .filter(GuestModel.event_id.in_(active_ids))
            .order_by(desc(GuestModel.updated_at))
            .limit(3)
            .all()
            if active_ids
            else []
        )
        for rg in recent_guests:
            recent_activities.append(
                RecentActivityItem(
                    id=f"act_gst_{rg.id}",
                    activity_type="rsvp",
                    title=f"RSVP Updated: {rg.full_name}",
                    description=f"Status set to {rg.rsvp_status} (+{rg.plus_ones} guests) • {rg.category}",
                    timestamp=rg.updated_at[:10] if rg.updated_at else today_str,
                    badge="RSVP",
                )
            )

        # Recent Bookings
        recent_b = (
            self.db.query(EventVendorBookingModel)
            .filter(EventVendorBookingModel.event_id.in_(active_ids))
            .order_by(desc(EventVendorBookingModel.created_at))
            .limit(3)
            .all()
            if active_ids
            else []
        )
        for rb in recent_b:
            v_name = rb.vendor.name if rb.vendor else "Vendor"
            recent_activities.append(
                RecentActivityItem(
                    id=f"act_vnd_{rb.id}",
                    activity_type="booking",
                    title=f"Vendor Status: {v_name}",
                    description=f"{rb.booking_status} with agreed amount ₹{rb.agreed_price:,.0f}",
                    timestamp=rb.created_at[:10] if rb.created_at else today_str,
                    badge="Vendor",
                )
            )

        # Sort combined activity feed by timestamp or ID
        recent_activities.sort(key=lambda x: x.timestamp, reverse=True)
        recent_activities = recent_activities[:8]

        # 7. Next Event Weather Alert
        next_weather_alert: Optional[ExecutiveWeatherAlert] = None
        next_event = upcoming_events_list[0] if upcoming_events_list else None
        if next_event:
            # Check if there is a saved weather plan
            saved_wp = (
                self.db.query(EventWeatherPlanModel)
                .filter(EventWeatherPlanModel.event_id == next_event.event_id)
                .order_by(desc(EventWeatherPlanModel.created_at))
                .first()
            )
            if saved_wp and saved_wp.weather_summary_json:
                try:
                    w_dict = json.loads(saved_wp.weather_summary_json)
                    ra = w_dict.get("risk_assessment", {})
                    recs = w_dict.get("recommendations", [])
                    primary_rec = recs[0]["action_item"] if recs else "Monitor atmospheric forecast regularly."
                    next_weather_alert = ExecutiveWeatherAlert(
                        event_id=next_event.event_id,
                        event_title=next_event.title,
                        location=saved_wp.location_name,
                        date=next_event.date,
                        overall_risk_level=ra.get("overall_risk_level", "Low"),
                        primary_concern=ra.get("summary", "Stable weather anticipated for event date."),
                        recommended_action=primary_rec,
                    )
                except Exception:
                    pass

            if not next_weather_alert:
                next_weather_alert = ExecutiveWeatherAlert(
                    event_id=next_event.event_id,
                    event_title=next_event.title,
                    location=next_event.city,
                    date=next_event.date,
                    overall_risk_level="Low",
                    primary_concern=f"Ideal planning window for {next_event.city}. Check Weather tab for 16-day live radar.",
                    recommended_action="Set up outdoor backup canopy and hydrate guests.",
                )

        kpis = ExecutiveKpiMetrics(
            total_events=total_events_count,
            upcoming_events=upcoming_events_count,
            total_planned_budget=total_planned,
            total_actual_expenses=total_spent,
            remaining_budget=remaining_budget,
            total_confirmed_guests=total_attending,
            pending_rsvps=pending_rsvps,
            booked_vendors=booked_count,
        )

        return ExecutiveDashboardResponse(
            kpis=kpis,
            upcoming_events=upcoming_events_list,
            recent_activities=recent_activities,
            budget_utilization=budget_util_list,
            guest_rsvp_breakdown=GuestRsvpBreakdown(
                confirmed=confirmed_guests,
                declined=declined_guests,
                pending=pending_rsvps,
                total_invited=len(all_guests),
                total_attending=total_attending,
            ),
            vendor_summary=VendorSummaryStats(
                booked_count=booked_count,
                shortlisted_count=shortlisted_count,
                total_contracted_amount=total_contracted,
                advance_paid_amount=advance_paid,
            ),
            next_event_weather_alert=next_weather_alert,
        )
