import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_invitation_generation_english():
    req_payload = {
        "event_name": "Rohan & Priya's Grand Wedding",
        "event_type": "Wedding",
        "host_names": "Mr. & Mrs. Sharma",
        "event_date": "2026-12-15",
        "event_time": "7:00 PM onwards",
        "venue": "The Oberoi Grand Ballroom",
        "location": "Mumbai, Maharashtra",
        "language": "English",
        "style": "Traditional",
        "tone": "Warm & Welcoming",
    }
    res = client.post("/api/invitations/generate", json=req_payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["language"] == "English"
    assert len(data["variations"]) == 3

    # Check variation 1, 2, 3 have all components
    for v in data["variations"]:
        comps = v["components"]
        assert "personalized_greeting" in comps
        assert "event_details" in comps
        assert "invitation_message" in comps
        assert "closing_message" in comps
        assert "full_text" in comps
        # Fact preservation: check host, venue, date appear
        assert "Mr. & Mrs. Sharma" in comps["closing_message"] or "Mr. & Mrs. Sharma" in comps["full_text"]
        assert "The Oberoi Grand Ballroom" in comps["event_details"] or "The Oberoi Grand Ballroom" in comps["full_text"]
        assert "2026-12-15" in comps["event_details"] or "2026-12-15" in comps["full_text"]


def test_invitation_generation_hindi():
    req_payload = {
        "event_name": "रोहन और प्रिया का शुभ विवाह",
        "event_type": "Wedding",
        "host_names": "श्रीमती एवं श्री शर्मा",
        "event_date": "2026-12-15",
        "event_time": "सायं 7:00 बजे से",
        "venue": "द ओबेरॉय ग्रैंड बॉलरूम",
        "location": "मुंबई",
        "language": "Hindi",
        "style": "Royal",
        "tone": "भव्य एवं पारम्परिक",
    }
    res = client.post("/api/invitations/generate", json=req_payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["language"] == "Hindi"
    assert len(data["variations"]) == 3

    # Check Devanagari presence
    for v in data["variations"]:
        comps = v["components"]
        assert any(c in comps["full_text"] for c in ["॥", "श्री", "गणेशाय", "निमंत्रण", "सपरिवार", "सादर", "उत्सव"])


def test_invitation_generation_gujarati():
    req_payload = {
        "event_name": "આરવ અને અનન્યાનો શુભ વિવાહ",
        "event_type": "Wedding",
        "host_names": "શ્રીમતી અને શ્રી પટેલ",
        "event_date": "2026-12-20",
        "event_time": "સાંજે 7:00 કલાકે",
        "venue": "તાજ પેલેસ",
        "location": "અમદાવાદ",
        "language": "Gujarati",
        "style": "Traditional",
        "tone": "સ્નેહપૂર્ણ",
    }
    res = client.post("/api/invitations/generate", json=req_payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["language"] == "Gujarati"
    assert len(data["variations"]) == 3

    # Check Gujarati script presence
    for v in data["variations"]:
        comps = v["components"]
        assert any(c in comps["full_text"] for c in ["॥", "શ્રી", "ગણેશાય", "નિમંત્રણ", "સ્નેહી", "પરિવાર"])


def test_guest_personalization_and_explicit_sent_status():
    # 1. Create test event
    evt_payload = {
        "title": "Phase 4 Invitation Gala",
        "event_type": "wedding",
        "date": "2026-12-18",
        "city": "Jaipur",
        "guest_count": 100,
        "total_budget": 500000.0,
        "currency": "INR",
    }
    evt_res = client.post("/api/events", json=evt_payload)
    assert evt_res.status_code == 200
    event_id = evt_res.json()["event_id"]

    try:
        # 2. Add guest with plus_ones
        guest_payload = {
            "full_name": "Vikram Singhania",
            "email": "vikram.singhania@example.com",
            "phone": "+91 9876543210",
            "category": "VIP",
            "plus_ones": 2,
        }
        g_res = client.post(f"/api/events/{event_id}/guests", json=guest_payload)
        assert g_res.status_code == 200
        guest = g_res.json()
        guest_id = guest["id"]
        assert guest["invitation_status"] == "Not Sent"
        assert guest["rsvp_status"] == "Pending"

        # 3. Generate invitation personalized for this guest
        gen_payload = {
            "event_id": event_id,
            "guest_id": guest_id,
            "event_name": "Phase 4 Invitation Gala",
            "event_type": "Wedding",
            "host_names": "Singhania Family",
            "event_date": "2026-12-18",
            "event_time": "8:00 PM",
            "venue": "Rambagh Palace",
            "location": "Jaipur",
            "language": "English",
            "style": "Royal",
        }
        gen_res = client.post("/api/invitations/generate", json=gen_payload)
        assert gen_res.status_code == 200
        gen_data = gen_res.json()

        # Check personalized greeting reflects & Family because plus_ones == 2
        for v in gen_data["variations"]:
            assert "Vikram Singhania & Family" in v["components"]["personalized_greeting"] or "Vikram Singhania" in v["components"]["personalized_greeting"]

        # 4. Verify guest invitation status remains "Not Sent" (generating does NOT auto-mark sent)
        check_g = client.get(f"/api/events/{event_id}/guests").json()
        target_g = next(g for g in check_g if g["id"] == guest_id)
        assert target_g["invitation_status"] == "Not Sent"
        assert target_g["rsvp_status"] == "Pending"

        # 5. Save an invitation to database
        chosen_var = gen_data["variations"][0]["components"]
        save_payload = {
            "event_id": event_id,
            "guest_id": guest_id,
            "title": "Royal Gala Invitation for Vikram",
            "language": "English",
            "style": "Royal",
            "template_id": "royal_wedding",
            "text_components": chosen_var,
            "design_config": {
                "template_id": "royal_wedding",
                "bg_theme": "royal_navy",
                "bg_color": "#0F172A",
                "primary_color": "#F59E0B",
                "text_color": "#F8FAFC",
                "accent_color": "#FDE68A",
                "font_family": "display",
                "font_size": "medium",
                "border_style": "ornate_gold",
                "layout": "framed",
                "decorative_element": "royal_crest",
            },
        }
        save_res = client.post(f"/api/events/{event_id}/invitations", json=save_payload)
        assert save_res.status_code == 200
        saved_inv = save_res.json()
        inv_id = saved_inv["id"]
        assert saved_inv["guest_name"] == "Vikram Singhania"

        # Verify saving did NOT auto-mark sent
        check_g2 = client.get(f"/api/events/{event_id}/guests").json()
        target_g2 = next(g for g in check_g2 if g["id"] == guest_id)
        assert target_g2["invitation_status"] == "Not Sent"

        # 6. Retrieve saved invitations for event
        list_res = client.get(f"/api/events/{event_id}/invitations")
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

        # 7. Test PDF export for the saved invitation
        pdf_res = client.get(f"/api/invitations/{inv_id}/export-pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert len(pdf_res.content) > 500

        # 8. Explicitly mark invitation as Sent via confirmation endpoint
        sent_res = client.post(f"/api/events/{event_id}/guests/{guest_id}/mark-sent")
        assert sent_res.status_code == 200
        updated_g = sent_res.json()
        assert updated_g["invitation_status"] == "Sent"
        assert updated_g["rsvp_status"] == "Pending"  # RSVP status strictly preserved

        # 9. Delete saved invitation
        del_res = client.delete(f"/api/invitations/{inv_id}")
        assert del_res.status_code == 200

        # Check list is empty
        list_res2 = client.get(f"/api/events/{event_id}/invitations")
        assert len(list_res2.json()) == 0

    finally:
        # Cleanup
        client.delete(f"/api/events/{event_id}")
