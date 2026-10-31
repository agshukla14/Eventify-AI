from fastapi.testclient import TestClient
from datetime import date, timedelta
from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "gemini_configured" in data


def test_create_and_retrieve_event_flow():
    today = date.today()
    ev_date = (today + timedelta(days=75)).strftime("%Y-%m-%d")

    payload = {
        "event_type": "wedding",
        "title": "Aarav & Meera Royal Wedding",
        "date": ev_date,
        "city": "Jaipur",
        "guest_count": 350,
        "total_budget": 2500000.0,
        "currency": "INR",
        "theme_style": "Royal Rajasthani Heritage",
        "cultural_preferences": "Marwari Traditional",
        "dietary_preferences": ["Pure Vegetarian"],
        "must_haves": ["Grand Baraat Procession", "Live Folk Music"],
    }

    # 1. Create event
    res = client.post("/api/events", json=payload)
    assert res.status_code == 200
    created = res.json()
    event_id = created["event_id"]
    assert event_id is not None
    assert created["intake"]["title"] == "Aarav & Meera Royal Wedding"
    assert created["budget"]["total_budget"] == 2500000.0
    assert len(created["timeline"]["milestones"]) > 0
    assert len(created["vendors"]) >= 5

    # 2. Get event by ID
    res_get = client.get(f"/api/events/{event_id}")
    assert res_get.status_code == 200
    retrieved = res_get.json()
    assert retrieved["event_id"] == event_id

    # 3. List events
    res_list = client.get("/api/events")
    assert res_list.status_code == 200
    summaries = res_list.json()
    assert any(s["event_id"] == event_id for s in summaries)

    # 4. Export CSV
    res_csv = client.get(f"/api/events/{event_id}/export/csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "BUDGET ALLOCATION" in res_csv.text

    # 5. Export PDF
    res_pdf = client.get(f"/api/events/{event_id}/export/pdf")
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers["content-type"]
    assert len(res_pdf.content) > 1000

    # 6. Delete event
    res_del = client.delete(f"/api/events/{event_id}")
    assert res_del.status_code == 200
