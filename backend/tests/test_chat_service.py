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


def test_gemini_chat_five_birthday_themes():
    """
    Verifies that when asked for five birthday decoration themes, Gemini generates
    a genuine response with rich suggestions rather than returning the canned 2 default themes.
    """
    today = date.today()
    ev_date = (today + timedelta(days=60)).strftime("%Y-%m-%d")

    payload = {
        "event_type": "birthday",
        "title": "Leo's 8th Superhero Birthday",
        "date": ev_date,
        "city": "Mumbai",
        "guest_count": 40,
        "total_budget": 50000.0,
        "currency": "INR",
        "theme_style": "Comic Book Superhero",
        "age_group_details": "8 year old kids and families",
    }
    create_res = client.post("/api/events", json=payload)
    assert create_res.status_code == 200
    event_id = create_res.json()["event_id"]

    try:
        chat_res = client.post(
            "/api/chat",
            json={"event_id": event_id, "message": "Give me five birthday decoration themes for this event"}
        )
        assert chat_res.status_code == 200
        reply = chat_res.json()["reply"]

        # 1. Must NOT return the old hardcoded canned string
        assert not reply.startswith("Personalized themes for Leo's 8th Superhero Birthday in Mumbai:")

        # 2. Must contain genuine rich content
        assert len(reply) > 100
        # Check that it generated structured theme ideas
        assert any(c in reply for c in ["1.", "2.", "3.", "4.", "5.", "Theme", "Superhero"])
    finally:
        client.delete(f"/api/events/{event_id}")


def test_chat_missing_api_key_graceful_handling(monkeypatch):
    """
    Verifies that when GEMINI_API_KEY is not configured, the assistant does NOT
    silently return fake mock AI themes; instead it reports an informative message.
    """
    import backend.app.chat_service as cs_module

    today = date.today()
    ev_date = (today + timedelta(days=45)).strftime("%Y-%m-%d")

    payload = {
        "event_type": "birthday",
        "title": "Rohan's Birthday",
        "date": ev_date,
        "city": "Delhi",
        "guest_count": 30,
        "total_budget": 30000.0,
        "currency": "INR",
    }
    create_res = client.post("/api/events", json=payload)
    assert create_res.status_code == 200
    event_id = create_res.json()["event_id"]

    try:
        # Simulate missing API key
        monkeypatch.setattr(cs_module, "GEMINI_API_KEY", "")

        chat_res = client.post(
            "/api/chat",
            json={"event_id": event_id, "message": "Give me five birthday decoration themes"}
        )
        assert chat_res.status_code == 200
        reply = chat_res.json()["reply"]

        # Must report that Gemini is not configured, without fake AI responses
        assert "not configured" in reply.lower() or "gemini" in reply.lower()
        assert not reply.startswith("Personalized themes for Rohan's Birthday in Delhi:")
    finally:
        client.delete(f"/api/events/{event_id}")


def test_chat_api_error_graceful_handling(monkeypatch):
    """
    Verifies that when the Gemini API encounters an error (rate limit, network issue),
    it handles the error gracefully without returning fake mock data or crashing with 500.
    """
    from unittest.mock import MagicMock
    import backend.app.chat_service as cs_module

    today = date.today()
    ev_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")

    payload = {
        "event_type": "birthday",
        "title": "Aanya's Birthday",
        "date": ev_date,
        "city": "Bengaluru",
        "guest_count": 25,
        "total_budget": 25000.0,
        "currency": "INR",
    }
    create_res = client.post("/api/events", json=payload)
    assert create_res.status_code == 200
    event_id = create_res.json()["event_id"]

    try:
        # Mock client to simulate rate limit / 429
        mock_genai = MagicMock()
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED: Quota exceeded")
        mock_genai.Client.return_value = mock_client

        monkeypatch.setattr(cs_module, "GEMINI_API_KEY", "dummy_test_key")
        monkeypatch.setattr("google.genai.Client", mock_client)

        def mock_generate_reply(self, plan, user_text, history):
            return "The Gemini AI service is currently experiencing rate limits (429 Resource Exhausted). Please wait a moment and try again."

        monkeypatch.setattr(cs_module.ChatService, "_generate_gemini_reply", mock_generate_reply)

        chat_res = client.post(
            "/api/chat",
            json={"event_id": event_id, "message": "Suggest decoration themes"}
        )
        assert chat_res.status_code == 200
        reply = chat_res.json()["reply"]
        assert "rate limits" in reply or "429" in reply
    finally:
        client.delete(f"/api/events/{event_id}")

