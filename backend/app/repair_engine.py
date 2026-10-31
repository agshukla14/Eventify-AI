from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import uuid
import re

from .schemas import (
    EventIntake,
    BudgetItem,
    BudgetSummary,
    TimelineTask,
    RunOfShowItem,
    TimelinePlan,
    VendorCategory,
    VendorChecklistItem,
    PersonalizedIdeaItem,
    PersonalizedIdeasPlan,
    FullEventPlan,
)

# Mandatory vendor categories by event type
MANDATORY_VENDORS = {
    "wedding": [
        "Venue & Reception Hall",
        "Catering & Drinks",
        "Photography & Video",
        "Decor & Flowers",
        "Music & DJ / Live Band",
    ],
    "birthday": [
        "Venue / Party Space",
        "Cake & Catering",
        "Entertainment / Host",
        "Decor & Balloons",
    ],
    "community": [
        "Venue / Public Grounds & Permits",
        "Sound & AV Equipment",
        "Catering & Refreshments",
        "Security & Safety / First Aid",
    ],
}

# Standard budget categories by event type
DEFAULT_BUDGET_CATEGORIES = {
    "wedding": [
        ("Venue & Lodging", 25.0, True),
        ("Catering & Bar", 25.0, True),
        ("Decor & Floral", 12.0, True),
        ("Photography & Videography", 10.0, True),
        ("Entertainment & Music", 7.0, True),
        ("Attire & Beauty", 6.0, True),
        ("Invitations & Stationery", 3.0, False),
        ("Logistics & Transport", 4.0, False),
        ("Contingency", 8.0, True),
    ],
    "birthday": [
        ("Venue & Space Rental", 22.0, True),
        ("Catering & Cake", 30.0, True),
        ("Decor & Balloons", 12.0, True),
        ("Entertainment & Activities", 15.0, True),
        ("Photography", 7.0, False),
        ("Return Gifts & Favors", 6.0, True),
        ("Contingency", 8.0, True),
    ],
    "community": [
        ("Venue / Grounds & Permits", 20.0, True),
        ("Catering & Refreshments", 24.0, True),
        ("Stage, Sound & AV Equipment", 18.0, True),
        ("Decor, Signage & Banners", 10.0, False),
        ("Security, First Aid & Sanitation", 12.0, True),
        ("Marketing & Badges", 8.0, False),
        ("Contingency", 8.0, True),
    ],
}


def parse_date_safe(date_str: str) -> date:
    """Parses date string or returns today + 30 days if invalid."""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except Exception:
        return date.today() + timedelta(days=30)


class DeterministicRepairEngine:
    @staticmethod
    def repair_budget(
        raw_items: Optional[List[Dict[str, Any]]],
        intake: EventIntake,
        contingency_pct: float = 8.0
    ) -> BudgetSummary:
        """
        Enforces deterministic arithmetic:
        1. Guarantees 5-10% contingency.
        2. Normalizes percentages so sum == 100.00%.
        3. Normalizes amounts so sum == total_budget.
        4. Injects mandatory categories if missing.
        """
        total_budget = max(0.0, float(intake.total_budget))
        contingency_pct = max(5.0, min(10.0, float(contingency_pct)))

        # 1. Collect or seed categories
        defaults = DEFAULT_BUDGET_CATEGORIES.get(intake.event_type, DEFAULT_BUDGET_CATEGORIES["wedding"])
        items_dict: Dict[str, Dict[str, Any]] = {}

        # Add defaults first
        for cat_name, def_pct, is_mand in defaults:
            items_dict[cat_name.lower()] = {
                "id": str(uuid.uuid4())[:8],
                "category": cat_name,
                "weight": def_pct,
                "is_contingency": cat_name.lower() == "contingency",
                "is_mandatory": is_mand,
                "notes": f"Standard allocation for {intake.event_type}",
                "actual_spent": 0.0,
            }

        # Override or supplement with raw_items if provided
        if raw_items:
            for item in raw_items:
                cat = item.get("category", "").strip()
                if not cat:
                    continue
                cat_key = cat.lower()
                weight = float(item.get("weight", item.get("percentage", 1.0)))
                actual_spent = float(item.get("actual_spent", 0.0))
                notes = item.get("notes", "")
                is_contingency = "contingency" in cat_key

                if cat_key in items_dict:
                    items_dict[cat_key]["weight"] = max(0.1, weight)
                    items_dict[cat_key]["actual_spent"] = max(0.0, actual_spent)
                    if notes:
                        items_dict[cat_key]["notes"] = notes
                else:
                    items_dict[cat_key] = {
                        "id": str(uuid.uuid4())[:8],
                        "category": cat,
                        "weight": max(0.1, weight),
                        "is_contingency": is_contingency,
                        "is_mandatory": False,
                        "notes": notes,
                        "actual_spent": max(0.0, actual_spent),
                    }

        # Guarantee contingency exists
        has_contingency = any(v["is_contingency"] for v in items_dict.values())
        if not has_contingency:
            items_dict["contingency"] = {
                "id": str(uuid.uuid4())[:8],
                "category": "Contingency Fund",
                "weight": contingency_pct,
                "is_contingency": True,
                "is_mandatory": True,
                "notes": "Emergency reserve for unforeseen costs",
                "actual_spent": 0.0,
            }

        contingency_entry = next(v for v in items_dict.values() if v["is_contingency"])
        non_contingency_entries = [v for v in items_dict.values() if not v["is_contingency"]]

        # 2. Deterministic Weight Normalization
        remaining_pct = 100.0 - contingency_pct
        total_non_con_weight = sum(v["weight"] for v in non_contingency_entries)
        if total_non_con_weight <= 0:
            total_non_con_weight = float(len(non_contingency_entries))
            for v in non_contingency_entries:
                v["weight"] = 1.0

        # Calculate percentages
        allocated_pcts = []
        for v in non_contingency_entries:
            pct = round((v["weight"] / total_non_con_weight) * remaining_pct, 2)
            v["percentage"] = pct
            allocated_pcts.append(pct)

        contingency_entry["percentage"] = round(contingency_pct, 2)

        # Reconcile any rounding diff on percentage
        current_sum_pct = round(sum(v["percentage"] for v in non_contingency_entries) + contingency_entry["percentage"], 2)
        pct_diff = round(100.0 - current_sum_pct, 2)
        if pct_diff != 0.0 and non_contingency_entries:
            largest_entry = max(non_contingency_entries, key=lambda x: x["percentage"])
            largest_entry["percentage"] = round(largest_entry["percentage"] + pct_diff, 2)

        # 3. Calculate Currency Amounts
        for v in items_dict.values():
            raw_amt = round((v["percentage"] / 100.0) * total_budget, 2)
            v["allocated_amount"] = raw_amt

        # Reconcile rounding diff on total amount
        current_sum_amt = round(sum(v["allocated_amount"] for v in items_dict.values()), 2)
        amt_diff = round(total_budget - current_sum_amt, 2)
        if amt_diff != 0.0 and non_contingency_entries:
            largest_entry = max(non_contingency_entries, key=lambda x: x["allocated_amount"])
            largest_entry["allocated_amount"] = round(largest_entry["allocated_amount"] + amt_diff, 2)

        # Build final BudgetItem list
        final_items: List[BudgetItem] = []
        total_actual_spent = 0.0
        warnings: List[str] = []

        for v in items_dict.values():
            spent = round(v["actual_spent"], 2)
            alloc = round(v["allocated_amount"], 2)
            total_actual_spent += spent
            if spent > alloc and alloc > 0:
                warnings.append(
                    f"Warning: Category '{v['category']}' is over budget! Spent {spent} {intake.currency} vs allocated {alloc} {intake.currency}."
                )
            final_items.append(
                BudgetItem(
                    id=v["id"],
                    category=v["category"],
                    weight=v["weight"],
                    percentage=v["percentage"],
                    allocated_amount=alloc,
                    actual_spent=spent,
                    is_contingency=v["is_contingency"],
                    is_mandatory=v["is_mandatory"],
                    notes=v["notes"],
                )
            )

        # Sort items: non-contingency sorted by allocated_amount desc, contingency at end
        final_items.sort(key=lambda x: (x.is_contingency, -x.allocated_amount))

        total_allocated = round(sum(i.allocated_amount for i in final_items), 2)
        is_over = total_actual_spent > total_budget
        over_budget_amt = round(max(0.0, total_actual_spent - total_budget), 2)

        return BudgetSummary(
            total_budget=total_budget,
            currency=intake.currency,
            contingency_percentage=contingency_pct,
            items=final_items,
            total_allocated=total_allocated,
            total_actual_spent=round(total_actual_spent, 2),
            is_over_budget=is_over,
            over_budget_amount=over_budget_amt,
            warnings=warnings,
        )

    @staticmethod
    def repair_timeline(
        raw_tasks: Optional[List[Dict[str, Any]]],
        raw_run_of_show: Optional[List[Dict[str, Any]]],
        intake: EventIntake,
    ) -> TimelinePlan:
        """
        Enforces valid chronological dates, lead-time adaptation, risk flags, and day-of schedule.
        """
        today = date.today()
        event_date = parse_date_safe(intake.date)
        lead_days = (event_date - today).days

        is_compressed = lead_days < 30
        is_past = lead_days < 0

        # Milestone generator templates based on lead time
        tasks: List[TimelineTask] = []

        def make_task_date(days_before: int) -> date:
            if lead_days <= 0:
                return today
            offset = max(0, min(lead_days, days_before))
            computed = event_date - timedelta(days=offset)
            if computed < today:
                return today
            if computed > event_date:
                return event_date
            return computed

        if raw_tasks and len(raw_tasks) >= 4:
            for item in raw_tasks:
                task_id = item.get("id") or str(uuid.uuid4())[:8]
                title = item.get("title", "Planning Milestone")
                desc = item.get("description", "")
                due_raw = item.get("due_date", "")
                task_date = parse_date_safe(due_raw) if due_raw else make_task_date(14)

                # Clamp task date: today <= task_date <= event_date (or clamp to event_date if past)
                if task_date > event_date:
                    task_date = event_date
                if not is_past and task_date < today:
                    task_date = today

                phase = item.get("milestone_phase", "Milestone")
                owner = item.get("owner", "user")
                if owner not in ["user", "vendor", "helper"]:
                    owner = "user"
                priority = item.get("priority", "medium")
                if priority not in ["high", "medium", "low"]:
                    priority = "medium"
                status = item.get("status", "pending")
                if status not in ["pending", "in_progress", "completed"]:
                    status = "pending"

                is_high_risk = bool(item.get("is_high_risk", False)) or (is_compressed and priority == "high")
                is_past_due = (task_date < today and status != "completed")

                tasks.append(
                    TimelineTask(
                        id=task_id,
                        milestone_phase=phase,
                        title=title,
                        description=desc,
                        due_date=task_date.strftime("%Y-%m-%d"),
                        owner=owner,
                        priority=priority,
                        status=status,
                        is_high_risk=is_high_risk,
                        is_past_due=is_past_due,
                    )
                )
        else:
            # Deterministic milestone generation tailored to lead time & event type
            if lead_days >= 180:
                milestone_templates = [
                    (180, "6 Months Before", "Finalize Venue & Date", "Book main venue and lock in contract", "user", "high"),
                    (120, "4 Months Before", "Catering & Menu Tasting", "Select caterer and decide menu options", "user", "high"),
                    (90, "3 Months Before", "Book Photo & Video Crew", "Lock in lead photographers and shot list", "vendor", "medium"),
                    (60, "2 Months Before", "Send Invitations & Collect RSVPs", "Distribute invites with RSVP deadline", "user", "high"),
                    (30, "1 Month Before", "Finalize Decor & Entertainment", "Confirm setup layout, stage, audio and playlist", "vendor", "medium"),
                    (14, "2 Weeks Before", "Vendor Walkthrough & Headcount", "Submit final guest count to venue & caterer", "helper", "high"),
                    (7, "1 Week Before", "Prepare Emergency Kit & Rehearsal", "Pack emergency supplies, run rehearsal schedule", "user", "medium"),
                    (1, "1 Day Before", "Venue Handover & Early Setup", "Inspect venue layout and deliver place cards/signage", "helper", "high"),
                ]
            elif lead_days >= 30:
                milestone_templates = [
                    (lead_days - 2, "Kickoff Phase", "Secure Primary Venue & Key Vendors", "Lock down contracts immediately", "user", "high"),
                    (21, "3 Weeks Before", "Send Digital Invitations & Collect RSVPs", "Expedited invite distribution", "user", "high"),
                    (14, "2 Weeks Before", "Confirm Catering, Decor & Sound", "Finalize vendor schedules and requirements", "vendor", "high"),
                    (7, "1 Week Before", "Final Headcount & Run-of-Show Review", "Align team on hour-by-hour timing", "helper", "medium"),
                    (2, "2 Days Before", "Finalize Payments & Pickup Supplies", "Settle balances and verify equipment", "user", "high"),
                    (1, "1 Day Before", "Venue Inspection & Setup", "Check AV soundcheck and stage prep", "helper", "medium"),
                ]
            else:
                # Compressed sprint (<= 30 days, e.g. 3 weeks, 1 week away)
                milestone_templates = [
                    (min(lead_days, 18), "Immediate Priority", "URGENT: Lock Venue & Catering Contracts", "Direct phone bookings with immediate deposits", "user", "high"),
                    (min(lead_days, 14), "Sprint Phase 1", "Send Digital RSVPs & Urgent Guest Headcount", "Broadcast invites via WhatsApp/Email", "user", "high"),
                    (min(lead_days, 7), "Sprint Phase 2", "Confirm Audio/Visual, Decor & Cake/Food", "Confirm delivery windows with backup options", "vendor", "high"),
                    (min(lead_days, 3), "Final Countdown", "Submit Final Headcount & Settle Balances", "Lock final plates and balances", "user", "high"),
                    (1, "1 Day Before", "Day-Before Staging & Run-of-Show Alignment", "Coordinate helpers and rehearsal walk", "helper", "high"),
                ]

            for days_off, phase, title, desc, owner, prio in milestone_templates:
                task_date = make_task_date(days_off)
                is_high_risk = is_compressed or prio == "high"
                tasks.append(
                    TimelineTask(
                        id=str(uuid.uuid4())[:8],
                        milestone_phase=phase,
                        title=title,
                        description=desc,
                        due_date=task_date.strftime("%Y-%m-%d"),
                        owner=owner,
                        priority=prio,
                        status="pending",
                        is_high_risk=is_high_risk,
                        is_past_due=task_date < today,
                    )
                )

        # Sort tasks chronologically by due_date
        tasks.sort(key=lambda t: t.due_date)

        # Day-Of Hourly Run of Show
        run_of_show_items: List[RunOfShowItem] = []
        if raw_run_of_show and len(raw_run_of_show) >= 4:
            for r in raw_run_of_show:
                run_of_show_items.append(
                    RunOfShowItem(
                        id=r.get("id") or str(uuid.uuid4())[:8],
                        time_slot=r.get("time_slot", "09:00 - 10:00"),
                        activity=r.get("activity", "Activity"),
                        lead_person=r.get("lead_person", "Coordinator"),
                        location=r.get("location", "Main Venue"),
                        notes=r.get("notes", ""),
                    )
                )
        else:
            # Deterministic default run-of-show
            if intake.event_type == "wedding":
                default_ros = [
                    ("08:00 - 10:00", "Bridal & Groom Prep / Makeup & Hair", "Lead Stylist", "Bridal Suite", "Keep breakfast & water ready"),
                    ("10:00 - 11:30", "Vendor Arrivals & Venue Decor Setup", "Event Lead & Florist", "Main Hall", "AV soundcheck, floral arch installation"),
                    ("11:30 - 12:30", "Photographer Pre-Ceremony Portraits", "Lead Photographer", "Garden / Foyer", "Family & wedding party shots"),
                    ("12:30 - 13:30", "Guest Arrival & Welcome Refreshments", "Welcome Host", "Entrance Lobby", "Welcome drinks & seating ushering"),
                    ("13:30 - 15:00", "Ceremony & Traditional Rituals", "Officiant / MC", "Mandap / Main Altar", "Audio mics live, ring exchange/vows"),
                    ("15:00 - 16:30", "Cocktail Hour & Guest Photography", "Catering Lead", "Courtyard", "Passed hors d'oeuvres, music"),
                    ("16:30 - 19:30", "Grand Banquet Lunch / Dinner & Speeches", "Caterer & Toastmaster", "Dining Hall", "Buffet/plated meal service, speeches"),
                    ("19:30 - 22:30", "Live Music, Dancing & Celebration", "DJ / Band", "Dance Floor", "First dance, open dance floor"),
                    ("22:30 - 23:30", "Grand Send-Off & Teardown", "Event Coordinator", "Exit Gate", "Gift distribution & vendor breakdown"),
                ]
            elif intake.event_type == "birthday":
                default_ros = [
                    ("14:00 - 15:00", "Venue Access & Decorator Setup", "Party Coordinator", "Party Hall", "Balloons, backdrop, table setups"),
                    ("15:00 - 15:30", "Cake & Catering Delivery Check", "Helper Lead", "Pantry Area", "Check cake integrity and food warming"),
                    ("15:30 - 16:00", "Guest Arrival & Welcome Tattoo/Photo Station", "Welcome Greeter", "Entrance", "Kids nametags and welcome drinks"),
                    ("16:00 - 17:00", "Interactive Games & Entertainer Show", "MC / Magician / Host", "Main Floor", "Age-appropriate group games"),
                    ("17:00 - 17:30", "Cake Cutting Ceremony & Birthday Songs", "Family & MC", "Stage Area", "Sparkler candles & birthday toast"),
                    ("17:30 - 18:30", "Buffet Dinner / Snacks & Mingling", "Catering Lead", "Dining Area", "Kid-friendly & adult food stations"),
                    ("18:30 - 19:30", "Dance Party & Pinata Smash", "DJ / Host", "Dance Area", "High-energy playlist & pinata fun"),
                    ("19:30 - 20:00", "Return Gifts Handout & Farewell", "Host Family", "Exit Counter", "Personalized favors distribution"),
                ]
            else:  # community
                default_ros = [
                    ("07:00 - 08:30", "Grounds Setup, Stage & Sound Engineering", "Sound Crew Lead", "Main Grounds", "Power test, microphones, emergency exit verify"),
                    ("08:30 - 09:30", "Volunteer Briefing & Registration Desk Open", "Volunteer Coordinator", "Registration Canopy", "Distribute badges, lanyards, schedules"),
                    ("09:30 - 10:15", "Opening Ceremony & Welcome Address", "Community Lead", "Main Stage", "Welcome speech & safety announcement"),
                    ("10:15 - 13:00", "Main Events, Workshops & Interactive Stalls", "Stage Manager", "Event Zone", "Rotational activities and exhibits"),
                    ("13:00 - 14:15", "Community Lunch & Refreshment Break", "Food Committee", "Catering Tents", "Organized queue line & waste sorting"),
                    ("14:15 - 16:30", "Performances, Competitions & Keynote", "Cultural Secretary", "Main Stage", "Community showcases & youth activities"),
                    ("16:30 - 17:30", "Awards Ceremony & Volunteer Recognition", "Event Chair", "Main Stage", "Felicitation and trophy distribution"),
                    ("17:30 - 19:00", "Ground Cleandown, Waste Segregation & Security Sign-off", "Safety & Waste Team", "Entire Facility", "Leave ground spotless and return keys"),
                ]

            for slot, act, lead, loc, notes in default_ros:
                run_of_show_items.append(
                    RunOfShowItem(
                        id=str(uuid.uuid4())[:8],
                        time_slot=slot,
                        activity=act,
                        lead_person=lead,
                        location=loc,
                        notes=notes,
                    )
                )

        high_risk_count = sum(1 for t in tasks if t.is_high_risk)

        return TimelinePlan(
            milestones=tasks,
            run_of_show=run_of_show_items,
            lead_time_days=lead_days,
            is_compressed=is_compressed,
            high_risk_count=high_risk_count,
        )

    @staticmethod
    def repair_vendors(
        raw_vendors: Optional[List[Dict[str, Any]]],
        intake: EventIntake,
        budget: BudgetSummary,
    ) -> List[VendorCategory]:
        """
        Enforces mandatory coverage rule:
        1. 100% mandatory vendor categories present.
        2. At least 4 checklist items per category (question, doc/contract, deposit date, final date).
        3. Links quotes and balances to budget categories.
        """
        mandatory_list = MANDATORY_VENDORS.get(intake.event_type, MANDATORY_VENDORS["wedding"])
        vendors_by_cat: Dict[str, Dict[str, Any]] = {}

        # Index any provided raw vendors
        if raw_vendors:
            for v in raw_vendors:
                cat_name = v.get("category", "").strip()
                if not cat_name:
                    continue
                vendors_by_cat[cat_name.lower()] = v

        event_date = parse_date_safe(intake.date)
        deposit_target = (event_date - timedelta(days=max(14, int((event_date - date.today()).days * 0.7)))).strftime("%Y-%m-%d")
        final_payment_target = (event_date - timedelta(days=3)).strftime("%Y-%m-%d")

        final_vendors: List[VendorCategory] = []

        # Ensure all mandatory categories exist
        for mand_cat in mandatory_list:
            cat_key = mand_cat.lower()
            existing = None
            for k in list(vendors_by_cat.keys()):
                if k in cat_key or cat_key in k:
                    existing = vendors_by_cat.pop(k)
                    break

            # Find matching budget category
            linked_budget = "General"
            for b_item in budget.items:
                if any(word in b_item.category.lower() for word in mand_cat.lower().split() if len(word) > 3):
                    linked_budget = b_item.category
                    break
            if linked_budget == "General" and budget.items:
                linked_budget = budget.items[0].category

            # Checklist items (minimum 4)
            checklist_items: List[VendorChecklistItem] = [
                VendorChecklistItem(
                    id=str(uuid.uuid4())[:8],
                    task_text=f"Verify license, insurance, and service agreement for {mand_cat}",
                    item_type="document",
                    is_completed=False,
                    target_date=deposit_target,
                    notes="Must include cancellation and refund clause",
                ),
                VendorChecklistItem(
                    id=str(uuid.uuid4())[:8],
                    task_text=f"Pay initial reservation deposit (approx 20-30%) for {mand_cat}",
                    item_type="deposit_date",
                    is_completed=False,
                    target_date=deposit_target,
                    notes="Collect receipt and confirmation voucher",
                ),
                VendorChecklistItem(
                    id=str(uuid.uuid4())[:8],
                    task_text=f"Interview questions: confirm setup timeline, equipment backup, and staff count",
                    item_type="question",
                    is_completed=False,
                    target_date=deposit_target,
                    notes="Ask what happens in case of lead technician absence",
                ),
                VendorChecklistItem(
                    id=str(uuid.uuid4())[:8],
                    task_text=f"Final walkthrough and balance payment completion for {mand_cat}",
                    item_type="final_payment_date",
                    is_completed=False,
                    target_date=final_payment_target,
                    notes="Release only upon satisfactory pre-event check",
                ),
            ]

            if existing:
                vendor_name = existing.get("vendor_name", "")
                contact_info = existing.get("contact_info", "")
                quote_amount = float(existing.get("quote_amount", 0.0))
                status = existing.get("status", "not_contacted")
                if status not in ["not_contacted", "quoted", "booked", "paid"]:
                    status = "not_contacted"
                backup_vendor = existing.get("backup_vendor", f"Backup {mand_cat} Agency")

                # If existing had custom checklist items, merge them
                raw_cl = existing.get("checklist", [])
                if isinstance(raw_cl, list) and len(raw_cl) >= 4:
                    custom_items = []
                    for c_raw in raw_cl:
                        custom_items.append(
                            VendorChecklistItem(
                                id=c_raw.get("id") or str(uuid.uuid4())[:8],
                                task_text=c_raw.get("task_text", "Checklist Item"),
                                item_type=c_raw.get("item_type", "question"),
                                is_completed=bool(c_raw.get("is_completed", False)),
                                target_date=c_raw.get("target_date") or deposit_target,
                                notes=c_raw.get("notes", ""),
                            )
                        )
                    checklist_items = custom_items
            else:
                vendor_name = f"Top {mand_cat} Specialist ({intake.city})"
                contact_info = f"contact@{mand_cat.lower().replace(' ', '')}.com"
                quote_amount = round(budget.total_budget * 0.15, 2)
                status = "not_contacted"
                backup_vendor = f"Secondary {mand_cat} Provider ({intake.city})"

            final_vendors.append(
                VendorCategory(
                    id=str(uuid.uuid4())[:8],
                    category=mand_cat,
                    is_mandatory=True,
                    vendor_name=vendor_name,
                    contact_info=contact_info,
                    quote_amount=quote_amount,
                    status=status,
                    linked_budget_category=linked_budget,
                    checklist=checklist_items,
                    backup_vendor=backup_vendor,
                )
            )

        # Append any remaining non-mandatory vendors from raw_vendors
        for k, remaining_raw in vendors_by_cat.items():
            cat_title = remaining_raw.get("category", k.title())
            final_vendors.append(
                VendorCategory(
                    id=remaining_raw.get("id") or str(uuid.uuid4())[:8],
                    category=cat_title,
                    is_mandatory=False,
                    vendor_name=remaining_raw.get("vendor_name", f"{cat_title} Vendor"),
                    contact_info=remaining_raw.get("contact_info", ""),
                    quote_amount=float(remaining_raw.get("quote_amount", 0.0)),
                    status=remaining_raw.get("status", "not_contacted"),
                    linked_budget_category=budget.items[0].category if budget.items else "General",
                    checklist=[
                        VendorChecklistItem(
                            id=str(uuid.uuid4())[:8],
                            task_text=f"Review scope for {cat_title}",
                            item_type="question",
                            target_date=deposit_target,
                        ),
                        VendorChecklistItem(
                            id=str(uuid.uuid4())[:8],
                            task_text=f"Sign agreement for {cat_title}",
                            item_type="document",
                            target_date=deposit_target,
                        ),
                        VendorChecklistItem(
                            id=str(uuid.uuid4())[:8],
                            task_text=f"Pay initial deposit for {cat_title}",
                            item_type="deposit_date",
                            target_date=deposit_target,
                        ),
                        VendorChecklistItem(
                            id=str(uuid.uuid4())[:8],
                            task_text=f"Final payment balance for {cat_title}",
                            item_type="final_payment_date",
                            target_date=final_payment_target,
                        ),
                    ],
                    backup_vendor=remaining_raw.get("backup_vendor"),
                )
            )

        return final_vendors

    @staticmethod
    def repair_ideas(
        raw_ideas: Optional[Dict[str, Any]],
        intake: EventIntake,
    ) -> PersonalizedIdeasPlan:
        """
        Enforces:
        1. All 6 categories: themes, decor, food_menu, activities, entertainment, return_gifts.
        2. References user inputs (city, culture, theme, guest count, age group).
        3. Enforces strict dietary and age constraint guarding (e.g. no meat if vegetarian, no alcohol if kids).
        4. Every idea has a budget-friendly swap.
        """
        dietary_str = " ".join(intake.dietary_preferences).lower()
        is_vegetarian = any(d in dietary_str for d in ["veg", "vegetarian", "jain", "vegan"])
        is_vegan = "vegan" in dietary_str
        is_jain = "jain" in dietary_str

        age_str = (intake.age_group_details or "").lower() + " " + intake.title.lower()
        is_kids = any(k in age_str for k in ["kid", "child", "baby", "1st", "5th", "10th", "toddler", "teen"])

        # Prohibited word filters
        meat_words = ["chicken", "mutton", "beef", "pork", "fish", "seafood", "bacon", "meat", "lamb", "prawn", "crab"]
        jain_prohibited = ["onion", "garlic", "potato", "root vegetable"]
        alcohol_words = ["cocktail", "liquor", "beer", "wine", "vodka", "whiskey", "bar station", "champagne"]

        def sanitize_item(item: PersonalizedIdeaItem, cat_name: str) -> PersonalizedIdeaItem:
            text = (item.title + " " + item.description + " " + item.budget_friendly_swap).lower()

            # Dietary sanitation
            if cat_name == "food_menu":
                if is_vegetarian:
                    for w in meat_words:
                        if w in text:
                            item.title = item.title.replace(w.capitalize(), "Paneer").replace(w, "paneer")
                            item.description = f"Artisanal vegetarian delicacy customized for {intake.cultural_preferences or 'special guests'}: Paneer and seasonal organic ingredients."
                            item.budget_friendly_swap = "Switch to classic regional vegetarian street-food platters."
                            item.tags = [t for t in item.tags if t.lower() not in meat_words] + ["Vegetarian"]
                if is_jain:
                    for w in jain_prohibited:
                        if w in text:
                            item.description = f"Strict Jain culinary selection prepared without root vegetables, garlic, or onions."
                            item.tags.append("Jain Friendly")
                if is_vegan:
                    item.tags.append("100% Plant-Based")

            # Age sanitation
            if is_kids:
                for a in alcohol_words:
                    if a in text:
                        item.title = "Artisanal Fresh Fruit Mocktail & Smoothie Bar"
                        item.description = f"Colorful, kid-friendly fruit smoothies, sparkling juice spritzers, and boba drinks tailored for young guests."
                        item.budget_friendly_swap = "DIY infused water and lemonade hydration station with colorful straws."
                        item.tags = ["Kid-Safe", "Non-Alcoholic"]

            # Ensure budget swap exists
            if not item.budget_friendly_swap or len(item.budget_friendly_swap.strip()) < 5:
                item.budget_friendly_swap = f"Sustainably source locally in {intake.city} or opt for DIY decor elements."

            return item

        # Helper to parse category list
        def build_category_list(key: str, default_items: List[PersonalizedIdeaItem]) -> List[PersonalizedIdeaItem]:
            items: List[PersonalizedIdeaItem] = []
            raw_list = raw_ideas.get(key, []) if raw_ideas else []
            if isinstance(raw_list, list) and len(raw_list) > 0:
                for r in raw_list:
                    item_obj = PersonalizedIdeaItem(
                        id=r.get("id") or str(uuid.uuid4())[:8],
                        title=r.get("title", f"Custom {key.title()} Concept"),
                        description=r.get("description", f"Tailored for {intake.title} in {intake.city}"),
                        rationale=r.get("rationale", f"Incorporates {intake.theme_style or 'celebration aesthetics'} and local {intake.city} flair."),
                        budget_friendly_swap=r.get("budget_friendly_swap", "Opt for minimal local rental alternatives."),
                        tags=r.get("tags", []),
                    )
                    items.append(sanitize_item(item_obj, key))
            else:
                for default_it in default_items:
                    items.append(sanitize_item(default_it, key))
            return items

        # Default rich seed ideas reflecting user inputs
        city_ref = intake.city
        theme_ref = intake.theme_style or "Elegant Celebration"
        culture_ref = intake.cultural_preferences or "Festive Tradition"

        default_themes = [
            PersonalizedIdeaItem(
                id="th-1",
                title=f"{theme_ref} Fusion in {city_ref}",
                description=f"A bespoke visual atmosphere blending {culture_ref} heritage with contemporary elegance in {city_ref}.",
                rationale=f"Accentuates the {theme_ref} aesthetic requested for {intake.guest_count} guests.",
                budget_friendly_swap="Use repurposed brass lamps, marigold drapes, and fairy lights for high-impact warmth.",
                tags=["Theme", theme_ref, city_ref],
            ),
            PersonalizedIdeaItem(
                id="th-2",
                title="Eco-Chic Botanical Elegance",
                description="Zero-waste organic florals, potted botanical centerpieces, and warm ambient LED lanterns.",
                rationale="Modern, sustainable, and highly photogenic.",
                budget_friendly_swap="Rent potted plants from local nurseries instead of cut flower arrangements.",
                tags=["Sustainable", "Eco-Friendly"],
            ),
        ]

        default_decor = [
            PersonalizedIdeaItem(
                id="dec-1",
                title=f"Illuminated Heritage Archway inspired by {city_ref}",
                description=f"Grand entryway featuring handcrafted wooden arches, hanging bells, and warm fairy light curtains.",
                rationale=f"Creates a striking first impression for arriving guests in {city_ref}.",
                budget_friendly_swap="Replace imported florals with locally sourced marigold garlands and fabric drapes.",
                tags=["Decor", "Entrance"],
            ),
            PersonalizedIdeaItem(
                id="dec-2",
                title="Interactive Memory Photo Wall",
                description="Hanging Polaroid photo grid and warm Edison bulbs where guests can pin personal notes and selfies.",
                rationale="Engages guests immediately and builds lasting sentimental memories.",
                budget_friendly_swap="Use fairy lights on a jute twine grid with mini wooden clothespins.",
                tags=["Decor", "Interactive"],
            ),
        ]

        food_title_1 = "Royal Vegetarian Feast" if is_vegetarian else "Signature Multi-Cuisine Live Stations"
        food_desc_1 = (
            f"Four-course gourmet vegetarian banquet featuring regional {city_ref} specialties and seasonal delicacies."
            if is_vegetarian else
            f"Gourmet culinary stations highlighting live tandoor, pasta bar, and regional {city_ref} favorites."
        )
        default_food = [
            PersonalizedIdeaItem(
                id="fd-1",
                title=food_title_1,
                description=food_desc_1,
                rationale=f"Directly respects dietary requirements: {', '.join(intake.dietary_preferences) or 'Universal crowd-pleasers'}.",
                budget_friendly_swap="Limit live stations to 2 signature counters and feature a rich shared buffet.",
                tags=["Catering", "Gourmet", "Vegetarian" if is_vegetarian else "Multi-Cuisine"],
            ),
            PersonalizedIdeaItem(
                id="fd-2",
                title="Artisanal Dessert & Chaat Boulevard",
                description="Interactive live chaat counter paired with artisanal dessert jars, kulfi, and mini warm pastries.",
                rationale=f"High interactive engagement suited for all {intake.guest_count} attendees.",
                budget_friendly_swap="Serve miniature shot-glass desserts and a single classic dessert counter.",
                tags=["Dessert", "Live Counter"],
            ),
        ]

        default_activities = [
            PersonalizedIdeaItem(
                id="act-1",
                title="Custom Trivia & Digital Interactive Polls",
                description=f"Live smartphone trivia about the hosts/honorees with leaderboard on the main AV screen.",
                rationale="Engages both shy and extroverted guests without awkward pressure.",
                budget_friendly_swap="Use free web polling tools with paper answer cards as backup.",
                tags=["Activity", "Interactive", "Fun"],
            ),
            PersonalizedIdeaItem(
                id="act-2",
                title="Bespoke Photo Booth with Curated Props",
                description=f"Custom backdrop reflecting {theme_ref} with instant digital sharing and printouts.",
                rationale=f"Provides physical keepsakes and high social engagement for {intake.guest_count} guests.",
                budget_friendly_swap="Set up a self-service ring light tripod with custom printed cardstock props.",
                tags=["PhotoBooth", "Keepsake"],
            ),
        ]

        default_entertainment = [
            PersonalizedIdeaItem(
                id="ent-1",
                title=f"Acoustic Duo & Live Percussion Set",
                description=f"Live melodic performance transitioning into upbeat fusion music during the celebration.",
                rationale=f"Matches the lively ambiance expected in {city_ref}.",
                budget_friendly_swap="Hire a talented local college music duo or a curated professional Spotify playlist setup.",
                tags=["Music", "Live Entertainment"],
            ),
        ]

        default_gifts = [
            PersonalizedIdeaItem(
                id="gft-1",
                title=f"Artisanal Handcrafted Gift Boxes from {city_ref}",
                description=f"Sustainably packaged gift boxes containing organic local teas, scented beeswax candles, and sweets.",
                rationale=f"A classy, memorable takeaway representing {culture_ref} and {city_ref}.",
                budget_friendly_swap="Eco-friendly seed-paper thank-you cards paired with traditional homemade confectioneries in jute pouches.",
                tags=["Return Gifts", "Sustainable"],
            ),
        ]

        return PersonalizedIdeasPlan(
            themes=build_category_list("themes", default_themes),
            decor=build_category_list("decor", default_decor),
            food_menu=build_category_list("food_menu", default_food),
            activities=build_category_list("activities", default_activities),
            entertainment=build_category_list("entertainment", default_entertainment),
            return_gifts=build_category_list("return_gifts", default_gifts),
        )

    @classmethod
    def repair_full_plan(
        cls,
        raw_plan: Optional[Dict[str, Any]],
        intake: EventIntake,
        existing_event_id: Optional[str] = None,
    ) -> FullEventPlan:
        """
        Master deterministic post-processing layer:
        Guarantees that regardless of LLM output, network blips, or bad schemas,
        the output plan satisfies 100% of M1-M7 accuracy constraints.
        """
        event_id = existing_event_id or (raw_plan.get("event_id") if raw_plan else None) or str(uuid.uuid4())
        raw_budget = raw_plan.get("budget", {}) if raw_plan else {}
        raw_timeline = raw_plan.get("timeline", {}) if raw_plan else {}
        raw_vendors = raw_plan.get("vendors", []) if raw_plan else []
        raw_ideas = raw_plan.get("ideas", {}) if raw_plan else {}

        # 1. Repair Budget
        budget_summary = cls.repair_budget(
            raw_items=raw_budget.get("items") if isinstance(raw_budget, dict) else None,
            intake=intake,
            contingency_pct=float(raw_budget.get("contingency_percentage", 8.0)) if isinstance(raw_budget, dict) else 8.0,
        )

        # 2. Repair Timeline
        timeline_plan = cls.repair_timeline(
            raw_tasks=raw_timeline.get("milestones") if isinstance(raw_timeline, dict) else None,
            raw_run_of_show=raw_timeline.get("run_of_show") if isinstance(raw_timeline, dict) else None,
            intake=intake,
        )

        # 3. Repair Vendors
        vendor_list = cls.repair_vendors(
            raw_vendors=raw_vendors if isinstance(raw_vendors, list) else None,
            intake=intake,
            budget=budget_summary,
        )

        # 4. Repair Ideas
        ideas_plan = cls.repair_ideas(
            raw_ideas=raw_ideas if isinstance(raw_ideas, dict) else None,
            intake=intake,
        )

        now_str = datetime.now().isoformat()
        created_at = (raw_plan.get("created_at") if raw_plan else None) or now_str

        return FullEventPlan(
            event_id=event_id,
            intake=intake,
            budget=budget_summary,
            timeline=timeline_plan,
            vendors=vendor_list,
            ideas=ideas_plan,
            created_at=created_at,
            updated_at=now_str,
        )
