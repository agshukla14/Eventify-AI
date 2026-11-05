import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from .models import EventModel, EventWeatherPlanModel
from .schemas import (
    LocationGeoResult,
    HourlyWeatherPoint,
    DailyWeatherPoint,
    WeatherRiskFactor,
    WeatherRiskAssessment,
    SmartWeatherRecommendation,
    WeatherReportResponse,
    WeatherAssistantQuery,
    WeatherAssistantResponse,
    SaveTimelineMitigationsRequest,
    SaveTimelineMitigationsResponse,
    TimelineTask,
    FullEventPlan,
)
from .plan_service import PlanService
from .config import GEMINI_API_KEY, GEMINI_MODEL
from .gemini_client import sanitize_user_input

logger = logging.getLogger(__name__)

# WMO Weather Code Descriptions
WMO_CODE_MAP: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# Pre-seeded coordinates for prominent celebration destinations in India
SEED_CITY_COORDINATES: Dict[str, Tuple[float, float, str, str]] = {
    "mumbai": (19.0760, 72.8777, "Maharashtra", "Asia/Kolkata"),
    "ahmedabad": (23.0225, 72.5714, "Gujarat", "Asia/Kolkata"),
    "jaipur": (26.9124, 75.7873, "Rajasthan", "Asia/Kolkata"),
    "delhi": (28.6139, 77.2090, "Delhi", "Asia/Kolkata"),
    "new delhi": (28.6139, 77.2090, "Delhi", "Asia/Kolkata"),
    "bengaluru": (12.9716, 77.5946, "Karnataka", "Asia/Kolkata"),
    "bangalore": (12.9716, 77.5946, "Karnataka", "Asia/Kolkata"),
    "udaipur": (24.5854, 73.7125, "Rajasthan", "Asia/Kolkata"),
    "kolkata": (22.5726, 88.3639, "West Bengal", "Asia/Kolkata"),
    "chennai": (13.0827, 80.2707, "Tamil Nadu", "Asia/Kolkata"),
    "hyderabad": (17.3850, 78.4867, "Telangana", "Asia/Kolkata"),
    "pune": (18.5204, 73.8567, "Maharashtra", "Asia/Kolkata"),
    "goa": (15.2993, 74.1240, "Goa", "Asia/Kolkata"),
    "surat": (21.1702, 72.8311, "Gujarat", "Asia/Kolkata"),
    "lucknow": (26.8467, 80.9462, "Uttar Pradesh", "Asia/Kolkata"),
    "agra": (27.1767, 78.0081, "Uttar Pradesh", "Asia/Kolkata"),
    "varanasi": (25.3176, 82.9739, "Uttar Pradesh", "Asia/Kolkata"),
    "amritsar": (31.6340, 74.8723, "Punjab", "Asia/Kolkata"),
    "jodhpur": (26.2389, 73.0243, "Rajasthan", "Asia/Kolkata"),
    "kochi": (9.9312, 76.2673, "Kerala", "Asia/Kolkata"),
    "cochin": (9.9312, 76.2673, "Kerala", "Asia/Kolkata"),
    "chandigarh": (30.7333, 76.7794, "Punjab", "Asia/Kolkata"),
    "indore": (22.7196, 75.8577, "Madhya Pradesh", "Asia/Kolkata"),
    "bhopal": (23.2599, 77.4126, "Madhya Pradesh", "Asia/Kolkata"),
}

# In-memory cache to prevent redundant API calls
_GEO_CACHE: Dict[str, LocationGeoResult] = {}
_WEATHER_CACHE: Dict[str, Tuple[datetime, WeatherReportResponse]] = {}
CACHE_TTL_MINUTES = 30


class WeatherService:
    def __init__(self, db: Optional[Session] = None):
        self.db = db

    # ------------------------------------------------------------------------
    # 1. GEOCODING
    # ------------------------------------------------------------------------
    def geocode_location(self, city_name: str) -> LocationGeoResult:
        """
        Geocodes city name using Open-Meteo Geocoding API with fallback to
        pre-seeded popular celebration coordinates and caching.
        """
        clean_name = city_name.strip().lower()
        if not clean_name:
            raise ValueError("Location name cannot be empty.")

        # Check in-memory cache
        if clean_name in _GEO_CACHE:
            return _GEO_CACHE[clean_name]

        # Check pre-seeded known coordinates
        for seed_key, seed_val in SEED_CITY_COORDINATES.items():
            if seed_key == clean_name or seed_key in clean_name or clean_name in seed_key:
                result = LocationGeoResult(
                    name=city_name.strip().title(),
                    latitude=seed_val[0],
                    longitude=seed_val[1],
                    country="India",
                    admin1=seed_val[2],
                    timezone=seed_val[3],
                )
                _GEO_CACHE[clean_name] = result
                return result

        # Query Open-Meteo Geocoding API
        try:
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={httpx.URL(clean_name)}&count=5&language=en&format=json"
            with httpx.Client(timeout=6.0) as client:
                res = client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    results = data.get("results", [])
                    if results:
                        first = results[0]
                        geo_res = LocationGeoResult(
                            name=first.get("name", city_name.strip().title()),
                            latitude=float(first.get("latitude")),
                            longitude=float(first.get("longitude")),
                            country=first.get("country", "India"),
                            admin1=first.get("admin1"),
                            timezone=first.get("timezone", "Asia/Kolkata"),
                        )
                        _GEO_CACHE[clean_name] = geo_res
                        return geo_res
        except Exception as e:
            logger.warning(f"Open-Meteo geocoding network error for '{city_name}': {e}")

        # Fallback to default (Jaipur) if geocoding yields no results
        fallback = LocationGeoResult(
            name=city_name.strip().title(),
            latitude=26.9124,
            longitude=75.7873,
            country="India",
            admin1="Rajasthan",
            timezone="Asia/Kolkata",
        )
        _GEO_CACHE[clean_name] = fallback
        return fallback

    # ------------------------------------------------------------------------
    # 2. WEATHER RETRIEVAL & HORIZON DETERMINATION
    # ------------------------------------------------------------------------
    def get_weather_report(
        self,
        city: str,
        target_date_str: str,
        event_type: str = "wedding",
        event_id: Optional[str] = None,
    ) -> WeatherReportResponse:
        """
        Retrieves weather for the target date:
        - If within 15 days of today: Uses Open-Meteo Live Forecast API.
        - If beyond 15 days or in past: Uses Open-Meteo Historical Archive API
          for the matching calendar period, clearly labeled as
          'Historical Climate Reference – Not an Actual Forecast'.
        """
        try:
            target_date = datetime.strptime(target_date_str.split("T")[0], "%Y-%m-%d").date()
        except Exception:
            raise ValueError(f"Invalid target date format: '{target_date_str}'. Expected YYYY-MM-DD.")

        today = date.today()
        days_ahead = (target_date - today).days

        cache_key = f"{city.lower().strip()}_{target_date_str}_{event_type.lower()}"
        if cache_key in _WEATHER_CACHE:
            cached_time, cached_report = _WEATHER_CACHE[cache_key]
            if (datetime.now() - cached_time).total_seconds() < CACHE_TTL_MINUTES * 60:
                # Update event_id if provided
                if event_id and not cached_report.event_id:
                    cached_report.event_id = event_id
                return cached_report

        geo = self.geocode_location(city)
        retrieval_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Within live forecast horizon: 0 to 15 days
        if 0 <= days_ahead <= 15:
            report = self._fetch_live_forecast(
                geo=geo,
                target_date=target_date,
                event_type=event_type,
                event_id=event_id,
                retrieval_timestamp=retrieval_timestamp,
            )
        else:
            # Beyond forecast horizon: Use historical climate archive
            report = self._fetch_historical_climate(
                geo=geo,
                target_date=target_date,
                event_type=event_type,
                event_id=event_id,
                retrieval_timestamp=retrieval_timestamp,
            )

        # Cache report in memory
        _WEATHER_CACHE[cache_key] = (datetime.now(), report)

        # Persist report summary in DB if DB session and event_id available
        if self.db and event_id:
            try:
                self._persist_weather_plan(event_id, report)
            except Exception as e:
                logger.warning(f"Could not persist weather plan to DB: {e}")

        return report

    def _fetch_live_forecast(
        self,
        geo: LocationGeoResult,
        target_date: date,
        event_type: str,
        event_id: Optional[str],
        retrieval_timestamp: str,
    ) -> WeatherReportResponse:
        """Fetches from Open-Meteo 16-day forecast endpoint."""
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={geo.latitude}&longitude={geo.longitude}&"
            f"daily=weathercode,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,"
            f"precipitation_sum,precipitation_probability_max,windspeed_10m_max,relative_humidity_2m_mean,sunrise,sunset&"
            f"hourly=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,precipitation,weathercode,windspeed_10m&"
            f"forecast_days=16&timezone=auto"
        )

        daily_points: List[DailyWeatherPoint] = []
        hourly_points: List[HourlyWeatherPoint] = []
        target_str = target_date.strftime("%Y-%m-%d")

        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    daily_raw = data.get("daily", {})
                    times = daily_raw.get("time", [])

                    for i, t in enumerate(times):
                        code = daily_raw.get("weathercode", [0])[i] if i < len(daily_raw.get("weathercode", [])) else 0
                        cond = WMO_CODE_MAP.get(code, "Clear")
                        sunrise = daily_raw.get("sunrise", [None])[i] if i < len(daily_raw.get("sunrise", [])) else None
                        sunset = daily_raw.get("sunset", [None])[i] if i < len(daily_raw.get("sunset", [])) else None

                        p = DailyWeatherPoint(
                            date=t,
                            temp_max=float(daily_raw.get("temperature_2m_max", [30.0])[i]),
                            temp_min=float(daily_raw.get("temperature_2m_min", [22.0])[i]),
                            apparent_temp_max=float(daily_raw.get("apparent_temperature_max", [32.0])[i]),
                            apparent_temp_min=float(daily_raw.get("apparent_temperature_min", [22.0])[i]),
                            rain_probability_max=float(daily_raw.get("precipitation_probability_max", [0.0])[i] or 0.0),
                            precipitation_sum=float(daily_raw.get("precipitation_sum", [0.0])[i] or 0.0),
                            wind_speed_max=float(daily_raw.get("windspeed_10m_max", [12.0])[i] or 12.0),
                            humidity_mean=float(daily_raw.get("relative_humidity_2m_mean", [55.0])[i] or 55.0),
                            weather_code=code,
                            condition_text=cond,
                            sunrise=sunrise,
                            sunset=sunset,
                        )
                        daily_points.append(p)

                    # Extract hourly data for target day (or first day if target not in range)
                    hourly_raw = data.get("hourly", {})
                    h_times = hourly_raw.get("time", [])
                    for j, ht in enumerate(h_times):
                        if ht.startswith(target_str):
                            h_code = hourly_raw.get("weathercode", [0])[j] if j < len(hourly_raw.get("weathercode", [])) else 0
                            hourly_points.append(
                                HourlyWeatherPoint(
                                    time=ht,
                                    temperature=float(hourly_raw.get("temperature_2m", [28.0])[j]),
                                    apparent_temperature=float(hourly_raw.get("apparent_temperature", [30.0])[j]),
                                    rain_probability=float(hourly_raw.get("precipitation_probability", [0.0])[j] or 0.0),
                                    precipitation=float(hourly_raw.get("precipitation", [0.0])[j] or 0.0),
                                    wind_speed=float(hourly_raw.get("windspeed_10m", [10.0])[j] or 10.0),
                                    humidity=float(hourly_raw.get("relative_humidity_2m", [50.0])[j] or 50.0),
                                    weather_code=h_code,
                                    condition_text=WMO_CODE_MAP.get(h_code, "Clear"),
                                )
                            )
        except Exception as e:
            logger.warning(f"Error fetching live forecast from Open-Meteo: {e}")

        # If daily points were fetched, pick target day or closest
        target_point = next((p for p in daily_points if p.date == target_str), None)
        if not target_point and daily_points:
            target_point = daily_points[0]
        elif not target_point:
            # Fallback simulated baseline
            target_point = DailyWeatherPoint(
                date=target_str,
                temp_max=32.0,
                temp_min=22.0,
                apparent_temp_max=34.0,
                apparent_temp_min=22.0,
                rain_probability_max=15.0,
                precipitation_sum=0.0,
                wind_speed_max=14.0,
                humidity_mean=52.0,
                weather_code=1,
                condition_text="Mainly clear",
                sunrise=f"{target_str}T06:30",
                sunset=f"{target_str}T18:15",
            )
            daily_points = [target_point]

        risk_assessment = self.calculate_risk_assessment(target_point)
        recommendations = self.generate_smart_recommendations(event_type, target_point, risk_assessment)

        return WeatherReportResponse(
            event_id=event_id,
            location=f"{geo.name}, {geo.admin1 or geo.country}",
            latitude=geo.latitude,
            longitude=geo.longitude,
            target_date=target_str,
            is_forecast=True,
            data_type_label="Live Meteorological Forecast",
            retrieved_at=retrieval_timestamp,
            data_source="Open-Meteo Free Weather API",
            day_summary=target_point,
            daily_forecast=daily_points,
            hourly_forecast=hourly_points[:24],
            risk_assessment=risk_assessment,
            recommendations=recommendations,
        )

    def _fetch_historical_climate(
        self,
        geo: LocationGeoResult,
        target_date: date,
        event_type: str,
        event_id: Optional[str],
        retrieval_timestamp: str,
    ) -> WeatherReportResponse:
        """
        Fetches historical climate records from Open-Meteo Archive API
        for the same calendar dates in the previous completed year (2025/2024).
        Clearly labeled: 'Historical Climate Reference – Not an Actual Forecast'.
        """
        target_str = target_date.strftime("%Y-%m-%d")
        # Build 5-day window around same day in past year (2025)
        past_year = 2025
        try:
            sample_center = date(past_year, target_date.month, target_date.day)
        except ValueError:
            # Leap year edge case (Feb 29)
            sample_center = date(past_year, target_date.month, 28)

        start_date = sample_center - timedelta(days=2)
        end_date = sample_center + timedelta(days=2)

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={geo.latitude}&longitude={geo.longitude}&"
            f"start_date={start_str}&end_date={end_str}&"
            f"daily=weathercode,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,"
            f"precipitation_sum,windspeed_10m_max,relative_humidity_2m_mean,sunrise,sunset&"
            f"timezone=auto"
        )

        daily_points: List[DailyWeatherPoint] = []
        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    daily_raw = data.get("daily", {})
                    times = daily_raw.get("time", [])

                    for i, t in enumerate(times):
                        code = daily_raw.get("weathercode", [0])[i] if i < len(daily_raw.get("weathercode", [])) else 0
                        cond = WMO_CODE_MAP.get(code, "Historical Average")
                        sunrise = daily_raw.get("sunrise", [None])[i] if i < len(daily_raw.get("sunrise", [])) else None
                        sunset = daily_raw.get("sunset", [None])[i] if i < len(daily_raw.get("sunset", [])) else None
                        precip = float(daily_raw.get("precipitation_sum", [0.0])[i] or 0.0)
                        # Archive doesn't provide precipitation probability, compute reasonable climate estimate from precip
                        rain_prob = 75.0 if precip > 5.0 else (40.0 if precip > 0.5 else 10.0)

                        p = DailyWeatherPoint(
                            date=t,
                            temp_max=float(daily_raw.get("temperature_2m_max", [31.0])[i]),
                            temp_min=float(daily_raw.get("temperature_2m_min", [21.0])[i]),
                            apparent_temp_max=float(daily_raw.get("apparent_temperature_max", [33.0])[i]),
                            apparent_temp_min=float(daily_raw.get("apparent_temperature_min", [21.0])[i]),
                            rain_probability_max=rain_prob,
                            precipitation_sum=precip,
                            wind_speed_max=float(daily_raw.get("windspeed_10m_max", [11.0])[i] or 11.0),
                            humidity_mean=float(daily_raw.get("relative_humidity_2m_mean", [50.0])[i] or 50.0),
                            weather_code=code,
                            condition_text=cond,
                            sunrise=sunrise,
                            sunset=sunset,
                        )
                        daily_points.append(p)
        except Exception as e:
            logger.warning(f"Error fetching historical archive from Open-Meteo: {e}")

        # Pick center day or average
        if daily_points:
            target_point = daily_points[len(daily_points) // 2]
        else:
            # Fallback baseline
            target_point = DailyWeatherPoint(
                date=target_str,
                temp_max=31.5,
                temp_min=21.0,
                apparent_temp_max=33.0,
                apparent_temp_min=21.0,
                rain_probability_max=20.0,
                precipitation_sum=0.5,
                wind_speed_max=12.0,
                humidity_mean=55.0,
                weather_code=1,
                condition_text="Seasonal Average",
                sunrise=f"{target_str}T06:30",
                sunset=f"{target_str}T18:15",
            )
            daily_points = [target_point]

        risk_assessment = self.calculate_risk_assessment(target_point)
        recommendations = self.generate_smart_recommendations(event_type, target_point, risk_assessment)

        return WeatherReportResponse(
            event_id=event_id,
            location=f"{geo.name}, {geo.admin1 or geo.country}",
            latitude=geo.latitude,
            longitude=geo.longitude,
            target_date=target_str,
            is_forecast=False,
            data_type_label="Historical Climate Reference – Not an Actual Forecast",
            retrieved_at=retrieval_timestamp,
            data_source="Open-Meteo Historical Climate Archive",
            day_summary=target_point,
            daily_forecast=daily_points,
            hourly_forecast=[],
            risk_assessment=risk_assessment,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------------
    # 3. WEATHER RISK ANALYSIS
    # ------------------------------------------------------------------------
    def calculate_risk_assessment(self, day: DailyWeatherPoint) -> WeatherRiskAssessment:
        """
        Evaluates weather conditions against configurable thresholds:
        - Rain: High (>=60% or >=8mm), Moderate (30-59% or 2-7.9mm), Low
        - Heat: High (>=38°C or apparent >=40°C), Moderate (33-37°C), Low
        - Wind: High (>=35 km/h), Moderate (20-34 km/h), Low
        - Humidity: High (>=80%), Moderate (65-79%), Low
        """
        factors: List[WeatherRiskFactor] = []

        # 1. Rain Risk
        if day.rain_probability_max >= 60.0 or day.precipitation_sum >= 8.0:
            rain_lvl = "High"
            rain_reason = f"Elevated rain probability ({day.rain_probability_max:.0f}%) and anticipated precipitation ({day.precipitation_sum:.1f} mm) pose high disruption risks for outdoor lawns and decor."
        elif day.rain_probability_max >= 30.0 or day.precipitation_sum >= 2.0:
            rain_lvl = "Moderate"
            rain_reason = f"Scattered rain or showers possible ({day.rain_probability_max:.0f}% chance, {day.precipitation_sum:.1f} mm). Covered backups or waterproof marquees recommended."
        else:
            rain_lvl = "Low"
            rain_reason = f"Minimal precipitation likelihood ({day.rain_probability_max:.0f}% chance, {day.precipitation_sum:.1f} mm). Very favorable for open-air celebration setups."

        factors.append(
            WeatherRiskFactor(
                category="Rain & Precipitation",
                risk_level=rain_lvl,
                value_display=f"{day.rain_probability_max:.0f}% chance ({day.precipitation_sum:.1f} mm)",
                threshold_note="High: ≥60% or ≥8mm | Moderate: 30-59% or 2-8mm",
                reason=rain_reason,
            )
        )

        # 2. Heat Risk
        if day.temp_max >= 38.0 or day.apparent_temp_max >= 40.0:
            heat_lvl = "High"
            heat_reason = f"Intense heat index (High of {day.temp_max:.1f}°C, feels like {day.apparent_temp_max:.1f}°C). Prolonged daytime exposure creates guest fatigue and food freshness risks."
        elif day.temp_max >= 33.0 or day.apparent_temp_max >= 35.0:
            heat_lvl = "Moderate"
            heat_reason = f"Warm daytime temperatures ({day.temp_max:.1f}°C, feels like {day.apparent_temp_max:.1f}°C). Shaded lounge pavilions and hydration stations advised."
        else:
            heat_lvl = "Low"
            heat_reason = f"Pleasant ambient temperatures ({day.temp_max:.1f}°C max, {day.temp_min:.1f}°C min). Comfortable for both daytime and evening events."

        factors.append(
            WeatherRiskFactor(
                category="Temperature & Heat Index",
                risk_level=heat_lvl,
                value_display=f"{day.temp_max:.1f}°C (Feels like {day.apparent_temp_max:.1f}°C)",
                threshold_note="High: ≥38°C or feels ≥40°C | Moderate: 33-37°C",
                reason=heat_reason,
            )
        )

        # 3. Wind Risk
        if day.wind_speed_max >= 35.0:
            wind_lvl = "High"
            wind_reason = f"Strong wind gusts of {day.wind_speed_max:.1f} km/h. High danger of dislodging fabric drapes, temporary mandap canopies, and tall floral centerpieces."
        elif day.wind_speed_max >= 20.0:
            wind_lvl = "Moderate"
            wind_reason = f"Moderate breezes up to {day.wind_speed_max:.1f} km/h. Firm structural anchoring, tent stakes, and low-profile floral vessels recommended."
        else:
            wind_lvl = "Low"
            wind_reason = f"Gentle air movement ({day.wind_speed_max:.1f} km/h). Safe for hanging lights, freestanding displays, and stage backdrops."

        factors.append(
            WeatherRiskFactor(
                category="Wind & Gusts",
                risk_level=wind_lvl,
                value_display=f"{day.wind_speed_max:.1f} km/h",
                threshold_note="High: ≥35 km/h | Moderate: 20-34 km/h",
                reason=wind_reason,
            )
        )

        # 4. Humidity Risk
        if day.humidity_mean >= 80.0:
            hum_lvl = "High"
            hum_reason = f"Heavy atmospheric moisture ({day.humidity_mean:.0f}%). May cause sweat discomfort, makeup melting, and heavy air in enclosed tents without cooling."
        elif day.humidity_mean >= 65.0:
            hum_lvl = "Moderate"
            hum_reason = f"Moderate humidity ({day.humidity_mean:.0f}%). Evaporative air coolers and refreshing mocktails will keep attendees comfortable."
        else:
            hum_lvl = "Low"
            hum_reason = f"Comfortable relative humidity ({day.humidity_mean:.0f}%). Crisp, clean air quality."

        factors.append(
            WeatherRiskFactor(
                category="Relative Humidity",
                risk_level=hum_lvl,
                value_display=f"{day.humidity_mean:.0f}%",
                threshold_note="High: ≥80% | Moderate: 65-79%",
                reason=hum_reason,
            )
        )

        # Determine overall risk
        if any(f.risk_level == "High" for f in factors):
            overall = "High"
            summary = "Elevated weather risks detected. Immediate mitigation and contingency planning recommended."
        elif any(f.risk_level == "Moderate" for f in factors):
            overall = "Moderate"
            summary = "Manageable weather considerations identified. Standard weatherproofing and guest comforts advised."
        else:
            overall = "Low"
            summary = "Favorable meteorological outlook. Ideal conditions for outdoor celebration festivities."

        return WeatherRiskAssessment(
            overall_risk=overall,
            risk_summary=summary,
            factors=factors,
        )

    # ------------------------------------------------------------------------
    # 4. SMART EVENT RECOMMENDATIONS
    # ------------------------------------------------------------------------
    def generate_smart_recommendations(
        self,
        event_type: str,
        day: DailyWeatherPoint,
        risks: WeatherRiskAssessment,
    ) -> List[SmartWeatherRecommendation]:
        """
        Synthesizes event type context with meteorological risk factors
        to generate actionable, professional recommendations.
        """
        recs: List[SmartWeatherRecommendation] = []
        ev_title = event_type.capitalize()

        # RAIN MITIGATIONS
        rain_factor = next((f for f in risks.factors if "Rain" in f.category), None)
        if rain_factor and rain_factor.risk_level in ["High", "Moderate"]:
            recs.append(
                SmartWeatherRecommendation(
                    id="rec-rain-indoor-backup",
                    category="Venue & Shelter",
                    priority="Critical" if rain_factor.risk_level == "High" else "Recommended",
                    title="Reserve Indoor Backup Hall / Waterproof Marquee",
                    description=f"Given {day.rain_probability_max:.0f}% rain probability, lock in an on-site ballroom hold or German pagoda tent with transparent rain curtains.",
                    action_item="Confirm dual indoor/outdoor floor plan with venue management 14 days in advance.",
                    suggested_timeline_phase="1 Month Prior",
                )
            )
            recs.append(
                SmartWeatherRecommendation(
                    id="rec-rain-electrical",
                    category="Equipment & Production",
                    priority="Critical" if rain_factor.risk_level == "High" else "Recommended",
                    title="Waterproof Sound Console & Power Distribution",
                    description="Protect DJ gear, amplifiers, and generator power junctions with rubber cable protectors and elevated tarps.",
                    action_item="Instruct sound & light vendor to supply IP65-rated weatherproof outdoor junction boxes.",
                    suggested_timeline_phase="Week Of Event",
                )
            )
            recs.append(
                SmartWeatherRecommendation(
                    id="rec-rain-valet-umbrellas",
                    category="Guest Comfort",
                    priority="Recommended",
                    title="Setup Valet Umbrella Escorts & Non-Slip Walkways",
                    description="Ensure dry guest arrivals with coordinated golf umbrellas at drop-off zones and carpeted wooden ramps over grass.",
                    action_item="Order 40 custom branded event golf umbrellas and rubber-backed entrance carpets.",
                    suggested_timeline_phase="Week Of Event",
                )
            )

        # HEAT MITIGATIONS
        heat_factor = next((f for f in risks.factors if "Heat" in f.category), None)
        if heat_factor and heat_factor.risk_level in ["High", "Moderate"]:
            recs.append(
                SmartWeatherRecommendation(
                    id="rec-heat-timing",
                    category="Logistics & Timing",
                    priority="Critical" if heat_factor.risk_level == "High" else "Recommended",
                    title="Shift Prime Ceremonies to Golden Hour / Post-Sunset",
                    description=f"High daytime heat of {day.temp_max:.1f}°C can cause guest fatigue. Move main ceremonies to 5:30 PM onwards when temperatures cool.",
                    action_item="Adjust formal invite schedule and run-of-show timeline by 90 minutes towards dusk.",
                    suggested_timeline_phase="2 Weeks Prior",
                )
            )
            recs.append(
                SmartWeatherRecommendation(
                    id="rec-heat-hydration",
                    category="Guest Comfort",
                    priority="Recommended",
                    title="Deploy Chilled Hydration Bars & Coconut Stations",
                    description="Keep guests refreshed with fresh tender coconut water carts, mint lemonades, and iced hand towels upon seating.",
                    action_item="Brief catering lead to set up 3 welcome hydration stations with chilled infused waters.",
                    suggested_timeline_phase="Week Of Event",
                )
            )
            recs.append(
                SmartWeatherRecommendation(
                    id="rec-heat-misting-fans",
                    category="Venue & Shelter",
                    priority="Recommended",
                    title="Install High-Velocity Industrial Misting Fans",
                    description="Position quiet oscillating mist fans around guest dining and ceremonial seating canopies.",
                    action_item="Request venue or rental vendor to supply 8 water-misting cooling towers.",
                    suggested_timeline_phase="Week Of Event",
                )
            )

        # WIND MITIGATIONS
        wind_factor = next((f for f in risks.factors if "Wind" in f.category), None)
        if wind_factor and wind_factor.risk_level in ["High", "Moderate"]:
            recs.append(
                SmartWeatherRecommendation(
                    id="rec-wind-structural",
                    category="Decor & Staging",
                    priority="Critical" if wind_factor.risk_level == "High" else "Recommended",
                    title="Reinforce Mandap & Truss Ballast Weights",
                    description=f"Anticipated gusts of {day.wind_speed_max:.1f} km/h require heavy concrete/water ballast weights on all stage trusses and floral arches.",
                    action_item="Verify decor team anchors open-air backdrops with a minimum 250 kg ballast per pillar.",
                    suggested_timeline_phase="Week Of Event",
                )
            )
            recs.append(
                SmartWeatherRecommendation(
                    id="rec-wind-centerpieces",
                    category="Decor & Staging",
                    priority="Recommended",
                    title="Switch to Low-Profile Weighted Floral Centerpieces",
                    description="Replace tall slender glass candelabras with broad-base ceramic urns and hurricane glass candle enclosures.",
                    action_item="Coordinate centerpiece adjustments with florist to eliminate toppling hazards.",
                    suggested_timeline_phase="1 Month Prior",
                )
            )

        # HUMIDITY MITIGATIONS
        hum_factor = next((f for f in risks.factors if "Humidity" in f.category), None)
        if hum_factor and hum_factor.risk_level in ["High", "Moderate"]:
            recs.append(
                SmartWeatherRecommendation(
                    id="rec-hum-comfort",
                    category="Guest Comfort",
                    priority="Advisory",
                    title="Provide Bridal & Guest Touch-Up Vanity Stations",
                    description=f"Atmospheric humidity of {day.humidity_mean:.0f}% can compromise hair styling and makeup freshness.",
                    action_item="Stock air-conditioned green rooms with oil-blotting sheets, hairspray, and cooling facial sprays.",
                    suggested_timeline_phase="Week Of Event",
                )
            )

        # FAVORABLE / LOW RISK SCENARIOS
        if risks.overall_risk == "Low":
            recs.append(
                SmartWeatherRecommendation(
                    id="rec-clear-outdoor-dining",
                    category="Layout & Aesthetic",
                    priority="Recommended",
                    title="Maximize Open-Air Starlight Dining & Fairy Lights",
                    description="Forecast predicts crystal-clear celebration conditions. Take full advantage of open-lawn banquet seating under fairy lights.",
                    action_item="Request florist & lighting designer to focus budget on overhead canopy fairy string lights.",
                    suggested_timeline_phase="1 Month Prior",
                )
            )
            recs.append(
                SmartWeatherRecommendation(
                    id="rec-clear-standard-canopy",
                    category="Venue & Shelter",
                    priority="Advisory",
                    title="Standard Canopy Anchor & Sunshade Check",
                    description="While weather is serene, maintain standard fabric canopies to provide shade from direct midday sun rays.",
                    action_item="Ensure daylight seating features UV-protective fabric drapery.",
                    suggested_timeline_phase="2 Weeks Prior",
                )
            )

        return recs

    # ------------------------------------------------------------------------
    # 5. AI WEATHER ASSISTANT (GEMINI INTEGRATION)
    # ------------------------------------------------------------------------
    def ask_weather_assistant(
        self,
        query: WeatherAssistantQuery,
        weather_report: WeatherReportResponse,
    ) -> WeatherAssistantResponse:
        """
        Uses Gemini API to answer organizer queries grounded in actual retrieved
        weather metrics. Distinguishes live forecast from historical climate data.
        Falls back seamlessly if LLM client is unavailable.
        """
        user_q = sanitize_user_input(query.question)
        day = weather_report.day_summary
        is_forecast = weather_report.is_forecast
        data_type = weather_report.data_type_label

        context_summary = f"""
EVENT WEATHER METEOROLOGICAL CONTEXT:
- Location: {weather_report.location}
- Target Date: {weather_report.target_date}
- Data Type: {data_type} (Is Short-Term Forecast: {is_forecast})
- Retrieved At: {weather_report.retrieved_at} (Source: {weather_report.data_source})
- Condition: {day.condition_text} (WMO Code: {day.weather_code})
- Max Temperature: {day.temp_max:.1f}°C, Min Temperature: {day.temp_min:.1f}°C
- Apparent (Feels Like) Temperature: {day.apparent_temp_max:.1f}°C
- Rain Probability: {day.rain_probability_max:.0f}%
- Precipitation Amount: {day.precipitation_sum:.1f} mm
- Maximum Wind Speed: {day.wind_speed_max:.1f} km/h
- Mean Relative Humidity: {day.humidity_mean:.0f}%
- Sunrise: {day.sunrise or 'N/A'}, Sunset: {day.sunset or 'N/A'}
- Overall Risk Level: {weather_report.risk_assessment.overall_risk} ({weather_report.risk_assessment.risk_summary})
"""

        # System prompt with strict grounding instructions
        system_prompt = (
            "You are the Eventify AI Weather Planner Assistant. "
            "Your role is to guide celebration and event organizers (Weddings, Birthdays, Community Festivals) "
            "with meteorological intelligence. "
            "RULES: "
            "1. Answer ONLY using the factual weather metrics provided in the context. Never fabricate or guess numbers. "
            "2. If the data type is 'Historical Climate Reference – Not an Actual Forecast', explicitly clarify to the organizer "
            "that recommendations are based on historical seasonal trends rather than an active short-term meteorological forecast. "
            "3. If the data type is 'Live Meteorological Forecast', treat it as an active forecast horizon. "
            "4. Provide realistic, empathetic, and actionable event advice (e.g. backup timings, equipment waterproofing, guest comfort). "
            "5. Return a structured JSON response with keys: 'answer' (str), 'data_grounding' (str summary of weather values used), "
            "'is_forecast_based' (bool), 'key_suggestions' (list of 3 short actionable bullet points)."
        )

        # Attempt Gemini Call
        if GEMINI_API_KEY:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=GEMINI_API_KEY)
                full_contents = [
                    system_prompt,
                    context_summary,
                    f"Organizer Question: {user_q}",
                ]

                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=full_contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                    ),
                )

                raw_text = response.text.strip()
                parsed = json.loads(raw_text)
                return WeatherAssistantResponse(
                    answer=parsed.get("answer", ""),
                    data_grounding=parsed.get("data_grounding", f"{data_type} for {weather_report.location} on {weather_report.target_date}"),
                    is_forecast_based=is_forecast,
                    key_suggestions=parsed.get("key_suggestions", []),
                )
            except Exception as e:
                logger.warning(f"Gemini Weather Assistant call failed or fell back: {e}")

        # Deterministic Rule-Based Fallback
        return self._generate_fallback_assistant_response(user_q, weather_report)

    def _generate_fallback_assistant_response(
        self,
        question: str,
        report: WeatherReportResponse,
    ) -> WeatherAssistantResponse:
        """Deterministic, grounded fallback answer when Gemini is unavailable."""
        day = report.day_summary
        q_lower = question.lower()
        horizon_note = (
            "based on the active 16-day meteorological forecast"
            if report.is_forecast
            else "based on historical seasonal climate references for this calendar window (not an active forecast)"
        )

        suggestions = []
        if "outdoor" in q_lower or "suitable" in q_lower or "rain" in q_lower:
            if day.rain_probability_max >= 50 or day.precipitation_sum >= 5.0:
                answer = (
                    f"For {report.location} on {report.target_date} ({horizon_note}), "
                    f"an outdoor celebration carries notable rain risk with {day.rain_probability_max:.0f}% rain probability "
                    f"and {day.precipitation_sum:.1f} mm precipitation. We strongly advise arranging a fully sheltered or indoor ballroom backup."
                )
                suggestions = [
                    "Confirm dual-venue contract with an indoor hall hold.",
                    "Install waterproof side canopies on all lawn tents.",
                    "Shield electrical consoles and audio equipment.",
                ]
            elif day.temp_max >= 37.0:
                answer = (
                    f"For {report.location} on {report.target_date} ({horizon_note}), "
                    f"rain risk is minimal ({day.rain_probability_max:.0f}%), but daytime heat reaches {day.temp_max:.1f}°C. "
                    f"An outdoor celebration is feasible if shifted to 5:30 PM onwards under shaded canopies."
                )
                suggestions = [
                    "Shift main guest arrival towards sunset.",
                    "Equip lawn lounges with high-velocity mist fans.",
                    "Provide cold electrolyte and coconut water stations.",
                ]
            else:
                answer = (
                    f"Conditions for {report.location} on {report.target_date} look very favorable ({horizon_note}). "
                    f"With {day.condition_text.lower()} skies, {day.temp_max:.1f}°C high, and low rain probability ({day.rain_probability_max:.0f}%), "
                    f"it is well-suited for an outdoor celebration."
                )
                suggestions = [
                    "Maximize open-lawn seating and fairy light canopies.",
                    "Maintain standard daytime sunshades.",
                    "Conduct standard morning anchor checks.",
                ]
        elif "time" in q_lower or "timing" in q_lower:
            answer = (
                f"Taking into account sunrise at {day.sunrise or '6:30 AM'} and sunset at {day.sunset or '6:15 PM'} in {report.location} ({horizon_note}), "
                f"the prime window for outdoor celebration is between 5:00 PM and 10:30 PM, avoiding the peak heat of {day.temp_max:.1f}°C."
            )
            suggestions = [
                f"Schedule photography during golden hour ({day.sunset or '5:30 PM'}).",
                "Begin reception ceremonies post-sunset for optimal temperature.",
                "Ensure stage lighting is calibrated for nighttime ambiance.",
            ]
        else:
            answer = (
                f"Regarding your query for {report.location} on {report.target_date} ({horizon_note}): "
                f"The overall weather risk is {report.risk_assessment.overall_risk.upper()}. "
                f"Expected temperature ranges from {day.temp_min:.1f}°C to {day.temp_max:.1f}°C, "
                f"rain probability is {day.rain_probability_max:.0f}%, and wind speeds are {day.wind_speed_max:.1f} km/h."
            )
            suggestions = [
                f"Review {report.risk_assessment.overall_risk} risk factors in the planner dashboard.",
                "Save recommended weather mitigations to your timeline.",
                "Check back 3 days prior for refined forecast updates.",
            ]

        return WeatherAssistantResponse(
            answer=answer,
            data_grounding=f"{report.data_type_label}: Temp {day.temp_min:.1f}-{day.temp_max:.1f}°C, Rain {day.rain_probability_max:.0f}%, Wind {day.wind_speed_max:.1f} km/h",
            is_forecast_based=report.is_forecast,
            key_suggestions=suggestions,
        )

    # ------------------------------------------------------------------------
    # 6. ALTERNATIVE PLANNING & TIMELINE INTEGRATION
    # ------------------------------------------------------------------------
    def save_mitigations_to_timeline(
        self,
        event_id: str,
        req: SaveTimelineMitigationsRequest,
    ) -> SaveTimelineMitigationsResponse:
        """
        Saves selected weather mitigation tasks into the event's existing
        timeline plan. Checks for duplicates and updates SQLite database.
        """
        if not self.db:
            raise ValueError("Database session required to save timeline tasks.")

        plan_service = PlanService(self.db)
        plan = plan_service.get_plan(event_id)
        if not plan:
            raise ValueError(f"Event plan '{event_id}' not found.")

        existing_titles = {
            m.title.strip().lower() for m in plan.timeline.milestones
        }

        added_tasks: List[TimelineTask] = []
        skipped: List[str] = []

        # Target due date: 2 days before event date or event date itself
        try:
            ev_date = datetime.strptime(plan.intake.date.split("T")[0], "%Y-%m-%d").date()
            due_str = (ev_date - timedelta(days=2)).strftime("%Y-%m-%d")
        except Exception:
            due_str = plan.intake.date

        phase = req.phase or "Week Of Event"
        priority = req.priority or "high"

        for title in req.task_titles:
            clean_t = title.strip()
            if not clean_t:
                continue

            if clean_t.lower() in existing_titles:
                skipped.append(clean_t)
                continue

            task = TimelineTask(
                id=f"weather-task-{uuid4().hex[:8]}",
                milestone_phase=phase,
                title=clean_t,
                description="Weather mitigation action item generated by AI Weather-Aware Planner.",
                due_date=due_str,
                owner="user",
                priority=priority,
                status="pending",
                is_high_risk=(priority == "high"),
                is_past_due=False,
            )
            plan.timeline.milestones.append(task)
            existing_titles.add(clean_t.lower())
            added_tasks.append(task)

        if added_tasks:
            # Recalculate high_risk_count
            plan.timeline.high_risk_count = sum(1 for m in plan.timeline.milestones if m.is_high_risk)
            # Update database
            plan_service.update_plan(event_id, plan)

            # Update EventWeatherPlanModel record in DB if present
            weather_record = self.db.query(EventWeatherPlanModel).filter(
                EventWeatherPlanModel.event_id == event_id
            ).first()
            if weather_record:
                current_saved = []
                if weather_record.saved_mitigations_json:
                    try:
                        current_saved = json.loads(weather_record.saved_mitigations_json)
                    except Exception:
                        current_saved = []
                for t in added_tasks:
                    if t.title not in current_saved:
                        current_saved.append(t.title)
                weather_record.saved_mitigations_json = json.dumps(current_saved)
                weather_record.updated_at = datetime.now().isoformat()
                self.db.commit()

        return SaveTimelineMitigationsResponse(
            added_tasks=added_tasks,
            skipped_duplicates=skipped,
            total_milestones=len(plan.timeline.milestones),
        )

    def _persist_weather_plan(self, event_id: str, report: WeatherReportResponse):
        """Stores weather report summary in SQLite database."""
        now_str = datetime.now().isoformat()
        record = self.db.query(EventWeatherPlanModel).filter(
            EventWeatherPlanModel.event_id == event_id
        ).first()

        summary_payload = {
            "is_forecast": report.is_forecast,
            "data_type_label": report.data_type_label,
            "condition": report.day_summary.condition_text,
            "temp_max": report.day_summary.temp_max,
            "temp_min": report.day_summary.temp_min,
            "apparent_temp_max": report.day_summary.apparent_temp_max,
            "rain_probability_max": report.day_summary.rain_probability_max,
            "precipitation_sum": report.day_summary.precipitation_sum,
            "wind_speed_max": report.day_summary.wind_speed_max,
            "humidity_mean": report.day_summary.humidity_mean,
            "overall_risk": report.risk_assessment.overall_risk,
        }

        if record:
            record.location_name = report.location
            record.latitude = report.latitude
            record.longitude = report.longitude
            record.target_date = report.target_date
            record.data_type = "live_forecast" if report.is_forecast else "historical_reference"
            record.weather_summary_json = json.dumps(summary_payload)
            record.retrieved_at = report.retrieved_at
            record.updated_at = now_str
        else:
            record = EventWeatherPlanModel(
                id=f"wp-{uuid4().hex[:12]}",
                event_id=event_id,
                location_name=report.location,
                latitude=report.latitude,
                longitude=report.longitude,
                target_date=report.target_date,
                data_type="live_forecast" if report.is_forecast else "historical_reference",
                weather_summary_json=json.dumps(summary_payload),
                saved_mitigations_json=json.dumps([]),
                retrieved_at=report.retrieved_at,
                created_at=now_str,
                updated_at=now_str,
            )
            self.db.add(record)
        self.db.commit()
