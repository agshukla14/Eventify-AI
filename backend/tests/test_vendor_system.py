import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_vendor_seed_and_directory_listing():
    # 1. Fetch all vendors
    res = client.get("/api/vendors")
    assert res.status_code == 200, res.text
    vendors = res.json()
    assert len(vendors) >= 15

    # Check verified listings exist across categories
    categories = {v["category"] for v in vendors}
    for expected_cat in ["Photography", "Catering", "Decoration", "Venue", "Entertainment", "Makeup Artists", "Transportation", "Other Event Services"]:
        assert expected_cat in categories

    # 2. Filter by Category and Verified Status
    photo_res = client.get("/api/vendors?category=Photography&is_verified=true")
    assert photo_res.status_code == 200
    assert len(photo_res.json()) >= 1
    for v in photo_res.json():
        assert v["category"] == "Photography"
        assert v["is_verified"] is True

    # 3. Filter by Location
    ahm_res = client.get("/api/vendors?location=Ahmedabad")
    assert ahm_res.status_code == 200
    for v in ahm_res.json():
        assert "Ahmedabad" in v["location"]

    # 4. Filter by Price and Rating
    filtered_res = client.get("/api/vendors?max_price=50000&min_rating=4.5")
    assert filtered_res.status_code == 200
    for v in filtered_res.json():
        assert v["min_price"] <= 50000
        assert v["rating"] >= 4.5


def test_user_vendor_crud_and_verified_protection():
    # 1. Create custom user-added vendor
    user_vendor_payload = {
        "name": "Shreeji Marwadi Sweet & Catering",
        "category": "Catering",
        "location": "Surat, Gujarat",
        "description": "Authentic Gujarati and Marwari sweets, farsan counters, and full banquet catering.",
        "services_offered": ["Farsan Stalls", "Traditional Mithai", "Marwari Thali"],
        "min_price": 20000.0,
        "max_price": 60000.0,
        "rating": 4.6,
        "review_count": 18,
        "experience_years": 5,
        "phone": "+91 98259 99887",
        "email": "shreeji.surat@gmail.com",
        "website": "https://shreejisurat.in",
        "is_verified": False,
        "is_favorite": False,
    }
    create_res = client.post("/api/vendors", json=user_vendor_payload)
    assert create_res.status_code == 200, create_res.text
    created = create_res.json()
    vendor_id = created["id"]
    assert created["is_verified"] is False
    assert created["name"] == "Shreeji Marwadi Sweet & Catering"

    # 2. Update user-created vendor
    update_payload = {
        "min_price": 22000.0,
        "description": "Updated specialty catering with live counters.",
    }
    update_res = client.put(f"/api/vendors/{vendor_id}", json=update_payload)
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["min_price"] == 22000.0

    # 3. Toggle favorite
    fav_res = client.patch(f"/api/vendors/{vendor_id}/favorite")
    assert fav_res.status_code == 200
    assert fav_res.json()["is_favorite"] is True

    # 4. Attempt to delete or modify a VERIFIED vendor (must be blocked)
    verified_vendor = next(v for v in client.get("/api/vendors").json() if v["is_verified"] is True)
    verified_id = verified_vendor["id"]

    del_verified_res = client.delete(f"/api/vendors/{verified_id}")
    assert del_verified_res.status_code == 400
    assert "Verified directory listings cannot be deleted" in del_verified_res.text

    mod_verified_res = client.put(f"/api/vendors/{verified_id}", json={"name": "Hacked Name"})
    assert mod_verified_res.status_code == 400
    assert "Verified directory listings cannot be modified" in mod_verified_res.text

    # 5. Delete user-created vendor
    del_res = client.delete(f"/api/vendors/{vendor_id}")
    assert del_res.status_code == 200

    # Verify not found
    get_res = client.get(f"/api/vendors/{vendor_id}")
    assert get_res.status_code == 404


def test_ai_vendor_recommendation_grounded():
    # Query 1: Photographers in Ahmedabad under 30000
    query_payload = {
        "query": "Find wedding photographers in Ahmedabad under 30000",
    }
    rec_res = client.post("/api/vendors/recommend", json=query_payload)
    assert rec_res.status_code == 200, rec_res.text
    data = rec_res.json()
    assert data["parsed_criteria"]["category"] == "Photography"
    assert data["parsed_criteria"]["location"] == "Ahmedabad"

    recs = data["recommendations"]
    assert len(recs) >= 1
    # Check that Light Chamber Studios is recommended because it is in Ahmedabad with min_price <= 30000
    top = recs[0]
    assert top["vendor"]["category"] == "Photography"
    assert top["vendor"]["location"] == "Ahmedabad"
    assert top["is_within_budget"] is True
    assert "Light Chamber Studios" in top["vendor"]["name"]
    assert "budget" in top["match_reason"].lower()

    # Query 2: Decorators for Traditional Indian Wedding
    query2 = {
        "query": "Find decorators specializing in traditional Indian weddings",
    }
    rec_res2 = client.post("/api/vendors/recommend", json=query2)
    assert rec_res2.status_code == 200
    data2 = rec_res2.json()
    assert data2["parsed_criteria"]["category"] == "Decoration"
    assert len(data2["recommendations"]) >= 1
    for r in data2["recommendations"]:
        assert r["vendor"]["category"] == "Decoration"


def test_vendor_comparison():
    # Pick 2 verified vendors in Photography
    photo_vendors = client.get("/api/vendors?category=Photography").json()
    assert len(photo_vendors) >= 2
    v1 = photo_vendors[0]
    v2 = photo_vendors[1]

    comp_payload = {
        "vendor_ids": [v1["id"], v2["id"]],
    }
    comp_res = client.post("/api/vendors/compare", json=comp_payload)
    assert comp_res.status_code == 200, comp_res.text
    data = comp_res.json()
    assert len(data["vendors"]) == 2
    assert "best_budget_option" in data
    assert "best_rated_option" in data
    assert "best_overall_match" in data
    assert len(data["vendor_evaluations"]) == 2

    for eval_item in data["vendor_evaluations"]:
        assert len(eval_item["pros"]) > 0


def test_booking_management_and_expense_integration():
    # 1. Create a test event
    evt_payload = {
        "title": "Phase 5 Vendor Gala",
        "event_type": "wedding",
        "date": "2026-12-25",
        "city": "Ahmedabad",
        "guest_count": 200,
        "total_budget": 800000.0,
        "currency": "INR",
    }
    evt_res = client.post("/api/events", json=evt_payload)
    assert evt_res.status_code == 200
    event_id = evt_res.json()["event_id"]

    try:
        # 2. Get a verified vendor
        vendors = client.get("/api/vendors?location=Ahmedabad&category=Photography").json()
        assert len(vendors) >= 1
        target_vendor = vendors[0]
        vendor_id = target_vendor["id"]

        # 3. Create booking with invalid advance payment (> agreed) -> must fail
        invalid_bkg = {
            "event_id": event_id,
            "vendor_id": vendor_id,
            "booking_status": "Negotiating",
            "agreed_price": 50000.0,
            "advance_payment": 60000.0,  # Invalid!
        }
        fail_res = client.post(f"/api/events/{event_id}/vendor-bookings", json=invalid_bkg)
        assert fail_res.status_code == 400

        # 4. Create valid booking
        valid_bkg = {
            "event_id": event_id,
            "vendor_id": vendor_id,
            "booking_status": "Booked",
            "agreed_price": 50000.0,
            "advance_payment": 15000.0,
            "booking_date": "2026-11-01",
            "notes": "Full day traditional + candid photography package",
        }
        bkg_res = client.post(f"/api/events/{event_id}/vendor-bookings", json=valid_bkg)
        assert bkg_res.status_code == 200, bkg_res.text
        booking = bkg_res.json()
        booking_id = booking["id"]
        assert booking["agreed_price"] == 50000.0
        assert booking["advance_payment"] == 15000.0
        assert booking["remaining_payment"] == 35000.0  # Dynamic calculation: 50000 - 15000

        # 5. Retrieve event bookings
        list_res = client.get(f"/api/events/{event_id}/vendor-bookings")
        assert list_res.status_code == 200
        assert len(list_res.json()) == 1

        # 6. Check vendor analytics
        analytics_res = client.get(f"/api/events/{event_id}/vendor-analytics")
        assert analytics_res.status_code == 200
        analytics = analytics_res.json()
        assert analytics["booked_count"] == 1
        assert analytics["total_agreed_cost"] == 50000.0
        assert analytics["total_advance_paid"] == 15000.0
        assert analytics["total_remaining_payment"] == 35000.0

        # 7. Integrate with Phase 2: Record Advance Payment as an actual Expense
        exp_res = client.post(
            f"/api/events/{event_id}/vendor-bookings/{booking_id}/record-expense",
            json={"booking_id": booking_id, "payment_method": "UPI", "notes": "Initial 30% advance for photography"},
        )
        assert exp_res.status_code == 200, exp_res.text
        created_exp = exp_res.json()
        assert created_exp["amount"] == 15000.0
        assert created_exp["category"] == "Photography"
        assert created_exp["payment_status"] == "Paid"
        assert created_exp["vendor_name"] == target_vendor["name"]

        # 8. Verify the expense appears in Phase 2 expense list
        all_expenses = client.get(f"/api/events/{event_id}/expenses").json()
        match_exp = next((e for e in all_expenses if e["id"] == created_exp["id"]), None)
        assert match_exp is not None
        assert match_exp["amount"] == 15000.0

        # 9. Delete booking
        del_bkg_res = client.delete(f"/api/vendor-bookings/{booking_id}")
        assert del_bkg_res.status_code == 200

    finally:
        client.delete(f"/api/events/{event_id}")
