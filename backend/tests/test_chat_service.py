from fastapi.testclient import TestClient
from datetime import date, timedelta
from backend.app.main import app

client = TestClient(app)


def test_chat_grounded_qa_and_tools():
    today = date.today()
    ev_date = (today + timedelta(days=90)).strftime("%Y-%m-%d")

    # Create an initial event
    payload = {
        "event_type": "birthday",
        "title": "Sam's 30th Birthday Bash",
        "date": ev_date,
        "city": "Goa",
        "guest_count": 60,
        "total_budget": 100000.0,
        "currency": "INR",
        "theme_style": "Bohemian Sunset Beach",
        "dietary_preferences": ["Continental", "Cocktails"],
    }
    create_res = client.post("/api/events", json=payload)
    assert create_res.status_code == 200
    event_id = create_res.json()["event_id"]

    # 1. Grounded Question: "How many days left until my event?"
    chat_res1 = client.post("/api/chat", json={"event_id": event_id, "message": "How many days left until my event?"})
    assert chat_res1.status_code == 200
    data1 = chat_res1.json()
    assert "days remaining" in data1["reply"] or "days left" in data1["reply"].lower()

    # 2. Tool execution: Budget move
    chat_res2 = client.post(
        "/api/chat",
        json={"event_id": event_id, "message": "move 5000 from Decor to Catering"}
    )
    assert chat_res2.status_code == 200
    data2 = chat_res2.json()
    assert len(data2["tools_executed"]) > 0
    assert data2["updated_plan"] is not None
    # Re-validate budget integrity on updated plan
    b_items = data2["updated_plan"]["budget"]["items"]
    assert round(sum(i["percentage"] for i in b_items), 2) == 100.00
    assert round(sum(i["allocated_amount"] for i in b_items), 2) == 100000.0

    # 3. Tool execution: Update vendor status
    chat_res3 = client.post(
        "/api/chat",
        json={"event_id": event_id, "message": "mark cake as booked"}
    )
    assert chat_res3.status_code == 200
    data3 = chat_res3.json()
    assert len(data3["tools_executed"]) > 0
    # Verify vendor status in updated plan
    booked_cake = next(
        (v for v in data3["updated_plan"]["vendors"] if "cake" in v["category"].lower()),
        None
    )
    assert booked_cake is not None
    assert booked_cake["status"] == "booked"

    # Clean up
    client.delete(f"/api/events/{event_id}")
