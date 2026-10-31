import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_guest_crud_and_rsvp_flow():
    # 1. Create a test event
    intake = {
        "event_type": "wedding",
        "title": "Guest Management Test Wedding",
        "date": "2027-11-20",
        "city": "Bengaluru",
        "guest_count": 150,
        "total_budget": 1200000.0,
        "currency": "INR",
    }
    create_res = client.post("/api/events", json=intake)
    assert create_res.status_code == 200
    plan = create_res.json()
    event_id = plan["event_id"]

    try:
        # 2. Initially empty
        res = client.get(f"/api/events/{event_id}/guests")
        assert res.status_code == 200
        assert res.json() == []

        # 3. Add Guest 1 (Family)
        g1_payload = {
            "full_name": "Aarav Sharma",
            "email": "aarav.sharma@example.com",
            "phone": "+91-9876543210",
            "category": "Family",
            "plus_ones": 2,
            "invitation_status": "Not Sent",
            "rsvp_status": "Pending",
            "special_requirements": "Vegetarian meal required",
            "notes": "Bride's cousin brother",
        }
        g1_res = client.post(f"/api/events/{event_id}/guests", json=g1_payload)
        assert g1_res.status_code == 200
        g1 = g1_res.json()
        assert g1["id"].startswith("gst_")
        assert g1["full_name"] == "Aarav Sharma"
        assert g1["invitation_status"] == "Not Sent"
        assert g1["rsvp_status"] == "Pending"

        # 4. Duplicate prevention test: adding same email should fail
        dup_res = client.post(
            f"/api/events/{event_id}/guests",
            json={
                "full_name": "Aarav Sharma Clone",
                "email": "aarav.sharma@example.com",
                "category": "Family",
            },
        )
        assert dup_res.status_code == 400
        assert "already exists" in dup_res.json()["detail"].lower()

        # 5. Add Guest 2 (VIP with 1 plus-one)
        g2_payload = {
            "full_name": "Vikram Malhotra",
            "email": "vikram.m@example.com",
            "phone": "+91-9123456789",
            "category": "VIP",
            "plus_ones": 1,
            "invitation_status": "Sent",
            "rsvp_status": "Accepted",
            "notes": "Keynote dignitary",
        }
        g2_res = client.post(f"/api/events/{event_id}/guests", json=g2_payload)
        assert g2_res.status_code == 200
        g2 = g2_res.json()

        # 6. Add Guest 3 (Colleague who Declined)
        g3_payload = {
            "full_name": "Priya Nair",
            "email": "priya.nair@example.com",
            "category": "Colleagues",
            "plus_ones": 0,
            "invitation_status": "Sent",
            "rsvp_status": "Declined",
        }
        g3_res = client.post(f"/api/events/{event_id}/guests", json=g3_payload)
        assert g3_res.status_code == 200
        g3 = g3_res.json()

        # 7. Add Guest 4 (Friend with no email or phone, valid name)
        g4_payload = {
            "full_name": "Rohan Gupta",
            "category": "Friends",
            "plus_ones": 1,
        }
        g4_res = client.post(f"/api/events/{event_id}/guests", json=g4_payload)
        assert g4_res.status_code == 200
        g4 = g4_res.json()

        # 8. Check RSVP Summary and Attendance Calculations:
        # Total Invited = 4
        # Confirmed = Vikram Malhotra (Accepted) -> 1 primary + 1 plus-one = 2 expected attendees
        # Pending = Aarav Sharma (Pending), Rohan Gupta (Pending) -> 2
        # Declined = Priya Nair (Declined) -> 1
        summary_res = client.get(f"/api/events/{event_id}/guests/summary")
        assert summary_res.status_code == 200
        summary = summary_res.json()

        assert summary["total_guests_invited"] == 4
        assert summary["total_invitations_sent"] == 2
        assert summary["total_invitations_pending"] == 2
        assert summary["confirmed_guests"] == 1
        assert summary["confirmed_plus_ones"] == 1
        assert summary["total_expected_attendance"] == 2
        assert summary["pending_responses"] == 2
        assert summary["declined_guests"] == 1
        # Responded: 1 accepted + 1 declined = 2. Response rate = (2/4) * 100 = 50.0%
        assert summary["rsvp_response_rate"] == 50.0
        # Acceptance rate: 1 accepted / 2 responded = 50.0%
        assert summary["acceptance_rate"] == 50.0

        # 9. Update Guest 1 RSVP status from Pending to Accepted using quick status patch
        patch_res = client.patch(
            f"/api/events/{event_id}/guests/{g1['id']}/status",
            json={"invitation_status": "Sent", "rsvp_status": "Accepted"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["rsvp_status"] == "Accepted"
        assert patch_res.json()["invitation_status"] == "Sent"

        # Now Aarav (Accepted) has 2 plus-ones!
        # Total confirmed = Vikram (1 + 1) + Aarav (1 + 2) = 2 primary + 3 plus-ones = 5 expected attendance!
        summary_after = client.get(f"/api/events/{event_id}/guests/summary").json()
        assert summary_after["confirmed_guests"] == 2
        assert summary_after["confirmed_plus_ones"] == 3
        assert summary_after["total_expected_attendance"] == 5
        assert summary_after["pending_responses"] == 1

        # 10. Test Search & Filter:
        # Search by name
        s_res = client.get(f"/api/events/{event_id}/guests", params={"search": "Malhotra"})
        assert s_res.status_code == 200
        assert len(s_res.json()) == 1
        assert s_res.json()[0]["full_name"] == "Vikram Malhotra"

        # Filter by Category (VIP)
        vip_res = client.get(f"/api/events/{event_id}/guests", params={"category": "VIP"})
        assert vip_res.status_code == 200
        assert len(vip_res.json()) == 1

        # Filter by RSVP Status (Accepted)
        acc_res = client.get(f"/api/events/{event_id}/guests", params={"rsvp_status": "Accepted"})
        assert acc_res.status_code == 200
        assert len(acc_res.json()) == 2

        # 11. Edit a guest
        edit_res = client.put(
            f"/api/events/{event_id}/guests/{g1['id']}",
            json={"plus_ones": 3, "special_requirements": "Jain vegetarian"},
        )
        assert edit_res.status_code == 200
        assert edit_res.json()["plus_ones"] == 3
        assert edit_res.json()["special_requirements"] == "Jain vegetarian"

        # 12. Delete a guest
        del_res = client.delete(f"/api/events/{event_id}/guests/{g3['id']}")
        assert del_res.status_code == 200
        assert del_res.json()["message"] == "Guest deleted successfully"

        # Verify count decreased to 3
        list_after_del = client.get(f"/api/events/{event_id}/guests").json()
        assert len(list_after_del) == 3

        # 13. Test CSV and PDF exports
        csv_res = client.get(f"/api/events/{event_id}/guests/export/csv")
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]
        assert "Aarav Sharma" in csv_res.text
        assert "Vikram Malhotra" in csv_res.text

        # Filtered CSV export (Accepted only)
        csv_acc_res = client.get(f"/api/events/{event_id}/guests/export/csv", params={"filter_status": "Accepted"})
        assert csv_acc_res.status_code == 200
        assert "Accepted Guests" in csv_acc_res.text

        # PDF Export
        pdf_res = client.get(f"/api/events/{event_id}/guests/export/pdf")
        assert pdf_res.status_code == 200
        assert "application/pdf" in pdf_res.headers["content-type"]
        assert len(pdf_res.content) > 1000

    finally:
        client.delete(f"/api/events/{event_id}")


def test_csv_import_preview_and_confirm():
    # Create event
    intake = {
        "event_type": "birthday",
        "title": "CSV Import Test Birthday",
        "date": "2027-08-10",
        "city": "Delhi",
        "guest_count": 50,
        "total_budget": 80000.0,
        "currency": "INR",
    }
    create_res = client.post("/api/events", json=intake)
    event_id = create_res.json()["event_id"]

    try:
        # Pre-seed one guest with email "existing@test.com"
        client.post(
            f"/api/events/{event_id}/guests",
            json={"full_name": "Original Guest", "email": "existing@test.com", "category": "Family"},
        )

        # Prepare a CSV with:
        # Row 1: Valid with all fields
        # Row 2: Valid with missing email/phone (allowed requirement)
        # Row 3: Duplicate email (matches existing in DB)
        # Row 4: Invalid row (empty name)
        csv_content = (
            "name,email,phone,category,plus_ones\n"
            "Ananya Sen,ananya@test.com,9998887771,Friends,1\n"
            "Deepak Verma,,,Relatives,2\n"
            "Duplicate Person,existing@test.com,9998887773,VIP,0\n"
            ",bad@test.com,9998887774,Colleagues,1\n"
        )

        # Post to preview endpoint
        preview_res = client.post(
            f"/api/events/{event_id}/guests/import/preview",
            json={"csv_content": csv_content, "filename": "guestlist.csv"},
        )
        assert preview_res.status_code == 200
        preview = preview_res.json()

        assert preview["total_rows"] == 4
        assert preview["valid_rows_count"] == 2
        assert preview["duplicate_rows_count"] == 1
        assert preview["invalid_rows_count"] == 1

        # Confirm import with the 2 valid rows
        valid_rows = [
            {
                "full_name": "Ananya Sen",
                "email": "ananya@test.com",
                "phone": "9998887771",
                "category": "Friends",
                "plus_ones": 1,
            },
            {
                "full_name": "Deepak Verma",
                "category": "Relatives",
                "plus_ones": 2,
            },
        ]
        confirm_res = client.post(
            f"/api/events/{event_id}/guests/import/confirm",
            json={"rows": valid_rows},
        )
        assert confirm_res.status_code == 200
        assert confirm_res.json()["imported_count"] == 2

        # Check total guests in database is now 1 (original) + 2 (imported) = 3
        guests = client.get(f"/api/events/{event_id}/guests").json()
        assert len(guests) == 3
        assert any(g["full_name"] == "Ananya Sen" for g in guests)
        assert any(g["full_name"] == "Deepak Verma" for g in guests)

    finally:
        client.delete(f"/api/events/{event_id}")


def test_event_wise_guest_isolation():
    # Event A
    evA = client.post(
        "/api/events",
        json={"event_type": "birthday", "title": "Event A", "date": "2027-05-01", "city": "Goa", "guest_count": 20, "total_budget": 50000.0},
    ).json()["event_id"]

    # Event B
    evB = client.post(
        "/api/events",
        json={"event_type": "wedding", "title": "Event B", "date": "2027-06-01", "city": "Pune", "guest_count": 100, "total_budget": 200000.0},
    ).json()["event_id"]

    try:
        # Add guest to Event A
        client.post(f"/api/events/{evA}/guests", json={"full_name": "Alice in Event A"})

        # Add guest to Event B
        client.post(f"/api/events/{evB}/guests", json={"full_name": "Bob in Event B"})

        # Guests in Event A must only contain Alice
        guestsA = client.get(f"/api/events/{evA}/guests").json()
        assert len(guestsA) == 1
        assert guestsA[0]["full_name"] == "Alice in Event A"

        # Guests in Event B must only contain Bob
        guestsB = client.get(f"/api/events/{evB}/guests").json()
        assert len(guestsB) == 1
        assert guestsB[0]["full_name"] == "Bob in Event B"

    finally:
        client.delete(f"/api/events/{evA}")
        client.delete(f"/api/events/{evB}")
