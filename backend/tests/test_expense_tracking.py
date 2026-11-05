import json
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fallback_or_mock_gemini_if_exhausted(monkeypatch):
    """
    Auto-detects live Gemini 429 quota exhaustion (500 requests/day exceeded on free tier)
    and mocks recommendations so calculations and constraints can be tested deterministically.
    """
    try:
        import google.genai.models as genai_models
        real_generate = genai_models.Models.generate_content

        def safe_generate_content(self, *args, **kwargs):
            try:
                return real_generate(self, *args, **kwargs)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    fake_res = MagicMock()
                    fake_res.text = json.dumps({
                        "revised_total_budget": 0.0,
                        "category_recommendations": [
                            {"category": "Venue & Accommodation", "weight": 30.0, "reason": "Preserved core venue."},
                            {"category": "Catering & Beverages", "weight": 25.0, "reason": "Streamlined menu."},
                            {"category": "Contingency", "weight": 8.0, "reason": "Maintained buffer."}
                        ],
                        "where_money_saved": ["Balanced vendor allocations"],
                        "why_recommended": "Optimized budget preserving key event elements",
                        "expenses_preserved": ["Venue & Accommodation"]
                    })
                    return fake_res
                raise

        monkeypatch.setattr(genai_models.Models, "generate_content", safe_generate_content)
    except Exception:
        pass


def test_expense_crud_and_summary_flow():
    # 1. Create a test event
    intake = {
        "event_type": "wedding",
        "title": "Expense Tracking Test Gala",
        "date": "2027-10-15",
        "city": "Mumbai",
        "guest_count": 200,
        "total_budget": 500000.0,
        "currency": "INR",
        "dietary_preferences": ["Vegetarian"],
    }
    create_res = client.post("/api/events", json=intake)
    assert create_res.status_code == 200
    plan = create_res.json()
    event_id = plan["event_id"]

    try:
        # 2. Initially, expenses list should be empty
        list_res = client.get(f"/api/events/{event_id}/expenses")
        assert list_res.status_code == 200
        assert list_res.json() == []

        # 3. Initially, summary should show 0 spent
        summary_res = client.get(f"/api/events/{event_id}/expenses/summary")
        assert summary_res.status_code == 200
        summary = summary_res.json()
        assert summary["total_event_budget"] == 500000.0
        assert summary["total_actual_spent"] == 0.0
        assert summary["remaining_budget"] == 500000.0
        assert summary["budget_utilization_percentage"] == 0.0
        assert summary["is_over_budget"] is False

        # 4. Add First Expense (e.g. Venue advance)
        venue_cat = next(i["category"] for i in plan["budget"]["items"] if "venue" in i["category"].lower())
        exp1_payload = {
            "expense_name": "Palace Venue Booking Deposit",
            "category": venue_cat,
            "amount": 75000.0,
            "expense_date": "2027-02-01",
            "payment_status": "Paid",
            "payment_method": "Bank Transfer",
            "vendor_name": "Royal Heritage Palace",
            "notes": "50% initial advance paid via RTGS",
        }
        exp1_res = client.post(f"/api/events/{event_id}/expenses", json=exp1_payload)
        assert exp1_res.status_code == 200
        exp1 = exp1_res.json()
        assert exp1["id"].startswith("exp_")
        assert exp1["amount"] == 75000.0
        assert exp1["payment_status"] == "Paid"

        # 5. Add Second Expense in SAME category (Multiple expenses per category requirement)
        exp2_payload = {
            "expense_name": "Venue Additional Lighting Fee",
            "category": venue_cat,
            "amount": 25000.0,
            "expense_date": "2027-02-05",
            "payment_status": "Pending",
            "payment_method": "UPI",
            "vendor_name": "Royal Heritage Palace",
            "notes": "Extra power generator fee",
        }
        exp2_res = client.post(f"/api/events/{event_id}/expenses", json=exp2_payload)
        assert exp2_res.status_code == 200
        exp2 = exp2_res.json()

        # 6. Verify listing with filter by category
        cat_filter_res = client.get(f"/api/events/{event_id}/expenses", params={"category": venue_cat})
        assert cat_filter_res.status_code == 200
        cat_items = cat_filter_res.json()
        assert len(cat_items) == 2

        # 7. Verify listing with search filter
        search_res = client.get(f"/api/events/{event_id}/expenses", params={"search": "Lighting"})
        assert search_res.status_code == 200
        assert len(search_res.json()) == 1
        assert search_res.json()[0]["expense_name"] == "Venue Additional Lighting Fee"

        # 8. Verify listing with status filter
        paid_res = client.get(f"/api/events/{event_id}/expenses", params={"payment_status": "Paid"})
        assert paid_res.status_code == 200
        assert len(paid_res.json()) == 1
        assert paid_res.json()[0]["payment_status"] == "Paid"

        # 9. Verify updated summary calculations
        summary2_res = client.get(f"/api/events/{event_id}/expenses/summary")
        assert summary2_res.status_code == 200
        s2 = summary2_res.json()
        assert s2["total_actual_spent"] == 100000.0
        assert s2["remaining_budget"] == 400000.0
        assert s2["budget_utilization_percentage"] == 20.0
        assert s2["paid_expenses_count"] == 1
        assert s2["pending_expenses_count"] == 1
        assert s2["highest_spending_category"] == venue_cat
        assert s2["highest_spending_amount"] == 100000.0

        # Check category-wise comparison
        venue_comp = next(c for c in s2["categories"] if c["category"] == venue_cat)
        assert venue_comp["actual_spent"] == 100000.0
        assert venue_comp["remaining"] == max(0.0, round(venue_comp["planned_budget"] - 100000.0, 2))
        assert venue_comp["difference"] == round(venue_comp["planned_budget"] - 100000.0, 2)

        # 10. Edit an expense (update amount from 25000 to 30000 and status to Paid)
        edit_res = client.put(
            f"/api/events/{event_id}/expenses/{exp2['id']}",
            json={"amount": 30000.0, "payment_status": "Paid"},
        )
        assert edit_res.status_code == 200
        edited = edit_res.json()
        assert edited["amount"] == 30000.0
        assert edited["payment_status"] == "Paid"

        # Total is now 75000 + 30000 = 105000
        s3 = client.get(f"/api/events/{event_id}/expenses/summary").json()
        assert s3["total_actual_spent"] == 105000.0

        # 11. Overspending scenario test
        # Let's find decor category and add an expense exceeding planned
        decor_item = next(i for i in plan["budget"]["items"] if "decor" in i["category"].lower())
        decor_planned = decor_item["allocated_amount"]
        over_exp_res = client.post(
            f"/api/events/{event_id}/expenses",
            json={
                "expense_name": "Luxury Exotic Florals",
                "category": decor_item["category"],
                "amount": decor_planned + 15000.0,
                "expense_date": "2027-02-10",
                "payment_status": "Paid",
            },
        )
        assert over_exp_res.status_code == 200
        over_exp = over_exp_res.json()

        # Check summary alerts: should detect category overspending
        s4 = client.get(f"/api/events/{event_id}/expenses/summary").json()
        decor_comp = next(c for c in s4["categories"] if c["category"] == decor_item["category"])
        assert decor_comp["is_overspent"] is True
        assert decor_comp["overspent_amount"] == 15000.0

        # Check intelligent alerts
        alert_titles = [a["title"] for a in s4["alerts"]]
        assert any("Overspending in" in title for title in alert_titles)

        # 12. Delete an expense
        del_res = client.delete(f"/api/events/{event_id}/expenses/{over_exp['id']}")
        assert del_res.status_code == 200
        assert del_res.json()["message"] == "Expense deleted successfully"

        # Verify expense no longer in list
        s5 = client.get(f"/api/events/{event_id}/expenses/summary").json()
        decor_comp_after = next(c for c in s5["categories"] if c["category"] == decor_item["category"])
        assert decor_comp_after["is_overspent"] is False
        assert decor_comp_after["actual_spent"] == 0.0

        # 13. Test CSV and PDF exports
        csv_res = client.get(f"/api/events/{event_id}/expenses/export/csv")
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]
        assert "CATEGORY-WISE PLANNED VS ACTUAL BUDGET" in csv_res.text
        assert "EXPENSE TRANSACTION HISTORY" in csv_res.text
        assert "Palace Venue Booking Deposit" in csv_res.text

        pdf_res = client.get(f"/api/events/{event_id}/expenses/export/pdf")
        assert pdf_res.status_code == 200
        assert "application/pdf" in pdf_res.headers["content-type"]
        assert len(pdf_res.content) > 1000

        # 14. Test Phase 1 Integration: Preserving Expenses after Budget Optimization
        # Run AI Budget Optimizer on this event
        opt_res = client.post(
            f"/api/events/{event_id}/optimize-budget",
            json={"user_prompt": "Reduce my wedding budget by ₹20,000"}
        )
        assert opt_res.status_code == 200
        opt_data = opt_res.json()

        # Apply new budget via PUT /api/events/{id}
        updated_plan_payload = dict(plan)
        updated_plan_payload["intake"]["total_budget"] = opt_data["revised_total_budget"]
        updated_plan_payload["budget"] = opt_data["optimized_budget_summary"]

        put_res = client.put(f"/api/events/{event_id}", json=updated_plan_payload)
        assert put_res.status_code == 200

        # Now verify expenses are fully intact!
        expenses_after_opt = client.get(f"/api/events/{event_id}/expenses").json()
        assert len(expenses_after_opt) == 2  # exp1 and exp2 still exist!
        assert any(e["expense_name"] == "Palace Venue Booking Deposit" for e in expenses_after_opt)

        # And expense summary now compares against the REVISED planned budget ceiling!
        s_after = client.get(f"/api/events/{event_id}/expenses/summary").json()
        assert s_after["total_event_budget"] == 480000.0  # 500,000 - 20,000
        assert s_after["total_actual_spent"] == 105000.0
        assert s_after["remaining_budget"] == 480000.0 - 105000.0

    finally:
        # Clean up event (also tests cascade delete of expenses)
        client.delete(f"/api/events/{event_id}")
