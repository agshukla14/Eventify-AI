import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas import DailyWeatherPoint, SaveTimelineMitigationsRequest
from backend.app.weather_service import WeatherService

client = TestClient(app)


def test_location_geocoding():
    # 1. Geocode prominent Indian celebration city (Jaipur)
    res = client.get("/api/weather/geocode?city=Jaipur")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["name"] == "Jaipur"
    assert round(data["latitude"], 1) == 26.9
    assert round(data["longitude"], 1) == 75.8
    assert data["country"] == "India"

    # 2. Geocode coastal destination (Goa)
    res_goa = client.get("/api/weather/geocode?city=Goa")
    assert res_goa.status_code == 200
    data_goa = res_goa.json()
    assert "Goa" in data_goa["name"] or "Goa" in data_goa["admin1"]


def test_live_forecast_retrieval_and_labeling():
    # Target date: 3 days from today (within 16-day forecast horizon)
    target_date = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")

    res = client.get(f"/api/weather/report?city=Mumbai&date={target_date}&event_type=wedding")
    assert res.status_code == 200, res.text
    data = res.json()

    # Verify forecast horizon labeling
    assert data["is_forecast"] is True
    assert data["data_type_label"] == "Live Meteorological Forecast"
    assert "Open-Meteo" in data["data_source"]
    assert "UTC" in data["retrieved_at"]

    # Verify weather metrics present
    day = data["day_summary"]
    assert day["temp_max"] > -20.0
    assert day["temp_min"] < 60.0
    assert "apparent_temp_max" in day
    assert "rain_probability_max" in day
    assert "precipitation_sum" in day
    assert "wind_speed_max" in day
    assert "humidity_mean" in day
    assert day["condition_text"] != ""

    # Verify risk assessment
    assert data["risk_assessment"]["overall_risk"] in ["Low", "Moderate", "High"]
    assert len(data["risk_assessment"]["factors"]) >= 4

    # Verify smart recommendations
    assert len(data["recommendations"]) >= 1


def test_historical_climate_retrieval_and_labeling():
    # Target date: 120 days from today (well beyond 16-day forecast horizon)
    target_date = (date.today() + timedelta(days=120)).strftime("%Y-%m-%d")

    res = client.get(f"/api/weather/report?city=Ahmedabad&date={target_date}&event_type=wedding")
    assert res.status_code == 200, res.text
    data = res.json()

    # Strict requirement: Never present historical averages as actual weather forecasts
    assert data["is_forecast"] is False
    assert data["data_type_label"] == "Historical Climate Reference – Not an Actual Forecast"
    assert "Historical" in data["data_source"]

    # Verify day metrics and climate stats
    day = data["day_summary"]
    assert day["temp_max"] > 10.0
    assert day["humidity_mean"] > 0.0


def test_weather_risk_detection_thresholds():
    service = WeatherService()

    # 1. Test High Rain Risk
    rainy_day = DailyWeatherPoint(
        date="2026-07-15",
        temp_max=29.0,
        temp_min=24.0,
        apparent_temp_max=32.0,
        apparent_temp_min=24.0,
        rain_probability_max=85.0,
        precipitation_sum=22.5,
        wind_speed_max=16.0,
        humidity_mean=88.0,
        weather_code=65,
        condition_text="Heavy rain",
    )
    risk_rain = service.calculate_risk_assessment(rainy_day)
    assert risk_rain.overall_risk == "High"
    rain_factor = next(f for f in risk_rain.factors if "Rain" in f.category)
    assert rain_factor.risk_level == "High"
    assert "85%" in rain_factor.value_display

    # 2. Test Extreme Heat Risk
    hot_day = DailyWeatherPoint(
        date="2026-05-20",
        temp_max=42.0,
        temp_min=29.0,
        apparent_temp_max=44.5,
        apparent_temp_min=29.0,
        rain_probability_max=5.0,
        precipitation_sum=0.0,
        wind_speed_max=12.0,
        humidity_mean=35.0,
        weather_code=0,
        condition_text="Clear sky",
    )
    risk_heat = service.calculate_risk_assessment(hot_day)
    assert risk_heat.overall_risk == "High"
    heat_factor = next(f for f in risk_heat.factors if "Temperature" in f.category)
    assert heat_factor.risk_level == "High"
    assert "42.0°C" in heat_factor.value_display

    # 3. Test High Wind Risk
    windy_day = DailyWeatherPoint(
        date="2026-03-10",
        temp_max=28.0,
        temp_min=18.0,
        apparent_temp_max=28.0,
        apparent_temp_min=18.0,
        rain_probability_max=10.0,
        precipitation_sum=0.0,
        wind_speed_max=42.0,
        humidity_mean=45.0,
        weather_code=2,
        condition_text="Partly cloudy",
    )
    risk_wind = service.calculate_risk_assessment(windy_day)
    assert risk_wind.overall_risk == "High"
    wind_factor = next(f for f in risk_wind.factors if "Wind" in f.category)
    assert wind_factor.risk_level == "High"
    assert "42.0 km/h" in wind_factor.value_display

    # 4. Test Low Risk / Favorable Day
    pleasant_day = DailyWeatherPoint(
        date="2026-11-20",
        temp_max=27.0,
        temp_min=16.0,
        apparent_temp_max=27.0,
        apparent_temp_min=16.0,
        rain_probability_max=10.0,
        precipitation_sum=0.0,
        wind_speed_max=11.0,
        humidity_mean=48.0,
        weather_code=0,
        condition_text="Clear sky",
    )
    risk_pleasant = service.calculate_risk_assessment(pleasant_day)
    assert risk_pleasant.overall_risk == "Low"


def test_ai_weather_assistant_grounded():
    target_date = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")

    req_payload = {
        "question": "Is this date suitable for an outdoor wedding ceremony, and what precautions should I take?",
        "location": "Jaipur",
        "target_date": target_date,
        "event_type": "wedding",
    }
    res = client.post("/api/weather/ask-ai", json=req_payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["answer"] != ""
    assert "Jaipur" in data["answer"] or "condition" in data["answer"].lower()
    assert data["data_grounding"] != ""
    assert data["is_forecast_based"] is True
    assert len(data["key_suggestions"]) >= 2


def test_timeline_mitigation_integration_and_deduplication():
    # 1. Fetch existing event
    events_res = client.get("/api/events")
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) >= 1
    event_id = events[0]["event_id"]

    # 2. Get event weather
    w_res = client.get(f"/api/events/{event_id}/weather")
    assert w_res.status_code == 200
    w_data = w_res.json()
    assert w_data["location"] != ""

    # 3. Save weather mitigations to event timeline (with unique run ID to allow re-running tests cleanly)
    import uuid
    run_id = uuid.uuid4().hex[:6]
    tasks_to_add = [
        f"Confirm tent waterproof side-curtains & drainage channels - {run_id}",
        f"Setup 3 guest hydration & electrolyte beverage stations - {run_id}",
    ]
    save_req = {
        "task_titles": tasks_to_add,
        "phase": "Week Of Event",
        "priority": "high",
    }
    save_res = client.post(f"/api/events/{event_id}/weather/save-timeline-tasks", json=save_req)
    assert save_res.status_code == 200, save_res.text
    save_data = save_res.json()

    assert len(save_data["added_tasks"]) == 2
    assert len(save_data["skipped_duplicates"]) == 0
    assert any("waterproof" in t["title"].lower() for t in save_data["added_tasks"])

    # 4. Verify duplicate prevention on subsequent save
    save_again_res = client.post(f"/api/events/{event_id}/weather/save-timeline-tasks", json=save_req)
    assert save_again_res.status_code == 200
    again_data = save_again_res.json()

    assert len(again_data["added_tasks"]) == 0
    assert len(again_data["skipped_duplicates"]) == 2

    # 5. Verify the tasks exist in event timeline
    ev_check = client.get(f"/api/events/{event_id}")
    assert ev_check.status_code == 200
    milestones = ev_check.json()["timeline"]["milestones"]
    titles = [m["title"] for m in milestones]
    assert tasks_to_add[0] in titles
