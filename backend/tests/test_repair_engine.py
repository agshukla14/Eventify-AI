from datetime import date, timedelta
from backend.app.schemas import EventIntake
from backend.app.repair_engine import DeterministicRepairEngine, MANDATORY_VENDORS


def test_budget_repair_integrity():
    today = date.today()
    ev_date = (today + timedelta(days=90)).strftime("%Y-%m-%d")

    intake = EventIntake(
        event_type="wedding",
        title="Priya & Rahul Wedding",
        date=ev_date,
        city="Mumbai",
        guest_count=250,
        total_budget=1500000.0,
        currency="INR",
        dietary_preferences=["Vegetarian"],
    )

    budget = DeterministicRepairEngine.repair_budget(None, intake, contingency_pct=8.0)

    # Percentage sum == 100.00
    total_pct = round(sum(i.percentage for i in budget.items), 2)
    assert total_pct == 100.00

    # Allocated sum == total_budget
    total_alloc = round(sum(i.allocated_amount for i in budget.items), 2)
    assert total_alloc == 1500000.0

    # Contingency present and between 5% and 10%
    contingency_items = [i for i in budget.items if i.is_contingency]
    assert len(contingency_items) == 1
    assert 5.0 <= contingency_items[0].percentage <= 10.0

    # No negative values
    for i in budget.items:
        assert i.percentage >= 0.0
        assert i.allocated_amount >= 0.0


def test_timeline_repair_dates_and_compression():
    today = date.today()

    # Case 1: Short lead time (14 days away -> compressed, high risk)
    short_date = (today + timedelta(days=14)).strftime("%Y-%m-%d")
    short_intake = EventIntake(
        event_type="birthday",
        title="Leo's 10th Birthday",
        date=short_date,
        city="Bengaluru",
        guest_count=40,
        total_budget=50000.0,
        currency="INR",
    )

    t_plan = DeterministicRepairEngine.repair_timeline(None, None, short_intake)

    assert t_plan.is_compressed is True
    assert t_plan.high_risk_count > 0
    assert len(t_plan.milestones) >= 4
    assert len(t_plan.run_of_show) >= 4

    # All dates in chronological order and <= event_date
    prev_d = "1900-01-01"
    for m in t_plan.milestones:
        assert m.due_date >= prev_d
        assert m.due_date <= short_date
        prev_d = m.due_date


def test_vendor_mandatory_coverage_all_event_types():
    today = date.today()
    ev_date = (today + timedelta(days=60)).strftime("%Y-%m-%d")

    for ev_type in ["wedding", "birthday", "community"]:
        intake = EventIntake(
            event_type=ev_type,
            title=f"Sample {ev_type.title()}",
            date=ev_date,
            city="Delhi",
            guest_count=100,
            total_budget=300000.0,
            currency="INR",
        )
        budget = DeterministicRepairEngine.repair_budget(None, intake)
        vendors = DeterministicRepairEngine.repair_vendors(None, intake, budget)

        mand_list = MANDATORY_VENDORS[ev_type]
        existing_cats = [v.category for v in vendors]

        for m in mand_list:
            assert m in existing_cats

        for v in vendors:
            assert len(v.checklist) >= 4
            # Contains document, deposit date, question, and final payment
            types = [c.item_type for c in v.checklist]
            assert "document" in types
            assert "deposit_date" in types
            assert "question" in types
            assert "final_payment_date" in types


def test_ideas_constraint_guarding():
    today = date.today()
    ev_date = (today + timedelta(days=45)).strftime("%Y-%m-%d")

    intake = EventIntake(
        event_type="birthday",
        title="Aryan's 5th Birthday Party",
        date=ev_date,
        city="Pune",
        guest_count=50,
        total_budget=40000.0,
        currency="INR",
        dietary_preferences=["Strict Vegetarian", "Jain"],
        age_group_details="Kids aged 4 to 7 years",
    )

    ideas = DeterministicRepairEngine.repair_ideas(None, intake)

    # Vegetarian / Jain check on food
    meat_words = ["chicken", "mutton", "beef", "pork", "fish", "meat"]
    for f in ideas.food_menu:
        text = (f.title + " " + f.description).lower()
        for m in meat_words:
            assert m not in text
        assert f.budget_friendly_swap != ""

    # Kids party check: no alcohol
    for cat in [ideas.activities, ideas.entertainment, ideas.food_menu]:
        for it in cat:
            text = (it.title + " " + it.description).lower()
            assert "cocktail" not in text
            assert "liquor" not in text
            assert "vodka" not in text
            assert it.budget_friendly_swap != ""
