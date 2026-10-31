from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_budget_analysis_endpoint():
    # 1. Create a sample wedding
    intake = {
        "event_type": "wedding",
        "title": "Optimizer Test Wedding",
        "date": "2027-05-20",
        "city": "Mumbai",
        "guest_count": 250,
        "total_budget": 2000000.0,
        "currency": "INR",
        "dietary_preferences": ["Vegetarian"],
    }
    create_res = client.post("/api/events", json=intake)
    assert create_res.status_code == 200
    event_id = create_res.json()["event_id"]

    # 2. Get budget analysis
    res = client.get(f"/api/events/{event_id}/budget-analysis")
    assert res.status_code == 200
    data = res.json()
    assert data["total_budget"] == 2000000.0
    assert data["total_allocated"] == 2000000.0
    assert data["highest_expense_category"] != ""
    assert data["highest_expense_amount"] > 0
    assert len(data["potential_savings_categories"]) > 0
    assert len(data["category_distribution"]) > 0

    # Clean up
    client.delete(f"/api/events/{event_id}")


def test_budget_optimization_reduction_amount_and_constraints():
    intake = {
        "event_type": "wedding",
        "title": "Constraint Test Wedding",
        "date": "2027-06-15",
        "city": "Jaipur",
        "guest_count": 300,
        "total_budget": 1000000.0,
        "currency": "INR",
        "dietary_preferences": ["Vegetarian"],
    }
    create_res = client.post("/api/events", json=intake)
    assert create_res.status_code == 200
    plan = create_res.json()
    event_id = plan["event_id"]

    orig_catering = next(
        i for i in plan["budget"]["items"] if "cater" in i["category"].lower()
    )

    # Prompt: Reduce by 50,000 but DO NOT reduce catering
    opt_res = client.post(
        f"/api/events/{event_id}/optimize-budget",
        json={"user_prompt": "Reduce my wedding budget by ₹50,000. Do not reduce catering expenses!"}
    )
    assert opt_res.status_code == 200
    data = opt_res.json()

    assert data["revised_total_budget"] == 950000.0
    assert data["total_savings"] == 50000.0
    assert data["engine_used"] in ["gemini", "fallback_rule_engine"]

    # Verify catering was protected
    new_catering = next(
        c for c in data["categories"] if "cater" in c["category"].lower()
    )
    assert new_catering["recommended_amount"] >= orig_catering["allocated_amount"] * 0.99

    # Verify explanation highlights preserved catering
    preserved_text = " ".join(data["explanation"]["expenses_preserved"]).lower()
    assert "cater" in preserved_text or "food" in preserved_text

    # Verify optimized budget summary adheres to 100% invariant
    opt_summary = data["optimized_budget_summary"]
    total_pct = round(sum(i["percentage"] for i in opt_summary["items"]), 2)
    assert total_pct == 100.00
    total_amt = round(sum(i["allocated_amount"] for i in opt_summary["items"]), 2)
    assert total_amt == 950000.0
    assert any(i["is_contingency"] for i in opt_summary["items"])

    # Clean up
    client.delete(f"/api/events/{event_id}")


def test_budget_optimization_percentage_savings():
    intake = {
        "event_type": "birthday",
        "title": "Percentage Savings Birthday",
        "date": "2027-02-10",
        "city": "Bengaluru",
        "guest_count": 50,
        "total_budget": 100000.0,
        "currency": "INR",
    }
    create_res = client.post("/api/events", json=intake)
    event_id = create_res.json()["event_id"]

    # Prompt: Save 15% of my total budget
    opt_res = client.post(
        f"/api/events/{event_id}/optimize-budget",
        json={"user_prompt": "I want to save 15% of my total budget."}
    )
    assert opt_res.status_code == 200
    data = opt_res.json()

    assert data["revised_total_budget"] == 85000.0
    assert data["total_savings"] == 15000.0
    assert data["optimized_budget_summary"]["total_budget"] == 85000.0
    assert round(sum(i["percentage"] for i in data["optimized_budget_summary"]["items"]), 2) == 100.00

    # Clean up
    client.delete(f"/api/events/{event_id}")


def test_budget_optimization_reallocation():
    intake = {
        "event_type": "wedding",
        "title": "Reallocation Test",
        "date": "2027-08-15",
        "city": "Delhi",
        "guest_count": 200,
        "total_budget": 500000.0,
        "currency": "INR",
    }
    create_res = client.post("/api/events", json=intake)
    event_id = create_res.json()["event_id"]

    # Prompt: Reallocate photography expenses to entertainment
    opt_res = client.post(
        f"/api/events/{event_id}/optimize-budget",
        json={"user_prompt": "Reallocate unused photography expenses to entertainment"}
    )
    assert opt_res.status_code == 200
    data = opt_res.json()

    # Budget total stays 500,000
    assert data["revised_total_budget"] == 500000.0
    opt_summary = data["optimized_budget_summary"]
    assert round(sum(i["percentage"] for i in opt_summary["items"]), 2) == 100.00
    assert round(sum(i["allocated_amount"] for i in opt_summary["items"]), 2) == 500000.0

    # Clean up
    client.delete(f"/api/events/{event_id}")
