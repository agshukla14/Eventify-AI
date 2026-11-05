import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from .models import InvitationModel, GuestModel, EventModel
from .schemas import (
    InvitationGenerateRequest,
    InvitationGenerateResponse,
    InvitationVariation,
    InvitationTextComponents,
    InvitationDesignConfig,
    InvitationCreateRequest,
    InvitationResponse,
    InvitationPDFExportRequest,
)
from .config import GEMINI_API_KEY, GEMINI_MODEL
from .gemini_client import sanitize_user_input

logger = logging.getLogger(__name__)


# Built-in Template Configurations
BUILTIN_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "traditional_indian_wedding": {
        "id": "traditional_indian_wedding",
        "name": "Traditional Indian Wedding",
        "category": "Wedding",
        "bg_theme": "gold_vermilion",
        "bg_color": "#FFFDF9",
        "primary_color": "#991B1B",  # Deep vermilion / maroon
        "text_color": "#1F2937",
        "accent_color": "#D97706",   # Marigold / warm gold
        "font_family": "serif",
        "font_size": "medium",
        "border_style": "ornate_gold",
        "layout": "centered",
        "decorative_element": "mandala_diya",
    },
    "royal_wedding": {
        "id": "royal_wedding",
        "name": "Royal Wedding",
        "category": "Wedding",
        "bg_theme": "royal_navy",
        "bg_color": "#0F172A",      # Deep midnight navy
        "primary_color": "#F59E0B",  # Royal gold
        "text_color": "#F8FAFC",
        "accent_color": "#FDE68A",   # Shimmer gold
        "font_family": "display",
        "font_size": "medium",
        "border_style": "ornate_gold",
        "layout": "framed",
        "decorative_element": "royal_crest",
    },
    "floral_birthday": {
        "id": "floral_birthday",
        "name": "Floral Birthday",
        "category": "Birthday",
        "bg_theme": "floral_blush",
        "bg_color": "#FFF5F5",      # Soft blush rose
        "primary_color": "#DB2777",  # Deep rose
        "text_color": "#374151",
        "accent_color": "#F472B6",   # Peony pink
        "font_family": "cursive",
        "font_size": "medium",
        "border_style": "floral",
        "layout": "centered",
        "decorative_element": "floral_wreath",
    },
    "minimalist_birthday": {
        "id": "minimalist_birthday",
        "name": "Minimalist Birthday",
        "category": "Birthday",
        "bg_theme": "minimalist_slate",
        "bg_color": "#F8FAFC",
        "primary_color": "#2563EB",  # Crisp electric indigo
        "text_color": "#0F172A",
        "accent_color": "#64748B",
        "font_family": "sans",
        "font_size": "medium",
        "border_style": "minimal",
        "layout": "minimal",
        "decorative_element": "confetti_stars",
    },
    "college_fest": {
        "id": "college_fest",
        "name": "College Fest",
        "category": "Community",
        "bg_theme": "ultraviolet_teal",
        "bg_color": "#111827",      # Night black
        "primary_color": "#8B5CF6",  # Cyber purple
        "text_color": "#F9FAFB",
        "accent_color": "#06B6D4",   # Bright cyan
        "font_family": "sans",
        "font_size": "medium",
        "border_style": "dashed",
        "layout": "split",
        "decorative_element": "geometric_badge",
    },
    "corporate_event": {
        "id": "corporate_event",
        "name": "Corporate Event",
        "category": "Corporate",
        "bg_theme": "executive_platinum",
        "bg_color": "#F1F5F9",
        "primary_color": "#0F172A",  # Executive charcoal
        "text_color": "#334155",
        "accent_color": "#3B82F6",   # Corporate blue
        "font_family": "serif",
        "font_size": "medium",
        "border_style": "double",
        "layout": "framed",
        "decorative_element": "none",
    },
    "anniversary": {
        "id": "anniversary",
        "name": "Anniversary Celebration",
        "category": "Anniversary",
        "bg_theme": "champagne_burgundy",
        "bg_color": "#FFFBEB",      # Warm champagne
        "primary_color": "#831843",  # Velvet wine
        "text_color": "#292524",
        "accent_color": "#D97706",   # Warm amber
        "font_family": "cursive",
        "font_size": "medium",
        "border_style": "ornate_gold",
        "layout": "centered",
        "decorative_element": "royal_crest",
    },
}


def format_event_time(time_str: Optional[str], language: str = "English") -> str:
    """Dynamically parses and formats event start time with AM/PM and localized designations."""
    if not time_str or not time_str.strip():
        time_str = "19:00"

    t = time_str.strip()
    if "-" in t:
        parts = t.split("-")
        start_part = parts[0].strip()
    elif "to" in t.lower():
        parts = t.lower().split("to")
        start_part = parts[0].strip()
    else:
        start_part = t

    import re
    match = re.search(r"(\d{1,2}):(\d{2})", start_part)
    hour = None
    minute = 0
    is_pm = None

    if "pm" in start_part.lower():
        is_pm = True
    elif "am" in start_part.lower():
        is_pm = False

    if match:
        h = int(match.group(1))
        minute = int(match.group(2))
        if is_pm is True and h < 12:
            h += 12
        elif is_pm is False and h == 12:
            h = 0
        hour = h
    else:
        num_match = re.search(r"(\d{1,2})", start_part)
        if num_match:
            h = int(num_match.group(1))
            if is_pm is True and h < 12:
                h += 12
            elif is_pm is False and h == 12:
                h = 0
            hour = h

    if hour is None:
        return t

    period = "PM" if hour >= 12 else "AM"
    disp_hour = hour % 12
    if disp_hour == 0:
        disp_hour = 12

    time_12h = f"{disp_hour}:{minute:02d} {period}"

    lang_lower = (language or "English").lower()
    if "gujarati" in lang_lower:
        if 4 <= hour < 12:
            prefix = "સવારે"
        elif 12 <= hour < 16:
            prefix = "બપોરે"
        elif 16 <= hour < 20:
            prefix = "સાંજે"
        else:
            prefix = "રાત્રે"
        return f"{prefix} {disp_hour}:{minute:02d} કલાકે"
    elif "hindi" in lang_lower:
        if 4 <= hour < 12:
            prefix = "सुबह"
        elif 12 <= hour < 16:
            prefix = "दोपहर"
        elif 16 <= hour < 20:
            prefix = "शाम"
        else:
            prefix = "रात"
        return f"{prefix} {disp_hour}:{minute:02d} बजे से"
    else:
        return f"{time_12h} onwards"


def resolve_event_venue(db: Optional[Session], event_id: Optional[str], fallback_city: str = "") -> str:
    """Dynamically resolves the venue name for any selected event from database records."""
    if not db or not event_id:
        return fallback_city + " Heritage Hall" if fallback_city else "Grand Celebration Hall"

    event = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not event:
        return fallback_city + " Heritage Hall" if fallback_city else "Grand Celebration Hall"

    # 1. Check intake_json for explicit venue
    try:
        intake_data = json.loads(event.intake_json) if event.intake_json else {}
        if intake_data.get("venue") and intake_data["venue"].strip():
            return intake_data["venue"].strip()
    except Exception:
        pass

    # 2. Check EventVendorBookingModel for booked/shortlisted venue
    try:
        from .models import EventVendorBookingModel
        bookings = db.query(EventVendorBookingModel).filter(EventVendorBookingModel.event_id == event_id).all()
        for b in bookings:
            if b.vendor and "venue" in (b.vendor.category or "").lower():
                if b.vendor.name and b.vendor.name.strip():
                    return b.vendor.name.strip()
    except Exception:
        pass

    # 3. Check plan_json for venue vendor
    try:
        plan_data = json.loads(event.plan_json) if event.plan_json else {}
        vendors = plan_data.get("vendors", [])
        for v in vendors:
            cat = (v.get("category") or "").lower()
            if "venue" in cat:
                name = (v.get("vendor_name") or "").strip()
                if name and "specialist" not in name.lower() and "provider" not in name.lower():
                    return name
                elif name:
                    return name
    except Exception:
        pass

    city = event.city or fallback_city or "City"
    return f"{city} Grand Celebration Hall"


def resolve_event_time(db: Optional[Session], event_id: Optional[str], default_time: str = "7:00 PM onwards") -> str:
    """Dynamically resolves the start time for any selected event from intake or run-of-show."""
    if not db or not event_id:
        return default_time

    event = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not event:
        return default_time

    try:
        intake_data = json.loads(event.intake_json) if event.intake_json else {}
        t = intake_data.get("start_time") or intake_data.get("event_time")
        if t and str(t).strip():
            return str(t).strip()
    except Exception:
        pass

    try:
        plan_data = json.loads(event.plan_json) if event.plan_json else {}
        ros = plan_data.get("timeline", {}).get("run_of_show", [])
        for slot in ros:
            act = (slot.get("activity") or "").lower()
            if "pre-event setup" not in act and "vendor arrival" not in act:
                ts = slot.get("time_slot", "")
                if ts:
                    start_part = ts.split("-")[0].strip()
                    return start_part
    except Exception:
        pass

    ev_type = (event.event_type or "").lower()
    if "birthday" in ev_type:
        return "15:00"
    elif "community" in ev_type:
        return "09:00"
    return "19:00"


class InvitationService:

    @classmethod
    def get_greeting_text(cls, language: str, guest: Optional[GuestModel] = None) -> str:
        lang = (language or "English").title()
        if guest:
            name = guest.full_name
            plus_ones = guest.plus_ones or 0
            if lang == "Hindi":
                return f"आदरणीय {name} जी एवं सपरिवार," if plus_ones > 0 else f"आदरणीय {name} जी,"
            elif lang == "Gujarati":
                return f"સ્નેહી શ્રી {name} સહપરિવાર," if plus_ones > 0 else f"સ્નેહી શ્રી {name},"
            else:
                return f"Dear {name} & Family," if plus_ones > 0 else f"Dear {name},"
        else:
            if lang == "Hindi":
                return "आदरणीय आत्मीय स्वजन,"
            elif lang == "Gujarati":
                return "સ્નેહી સ્વજનો,"
            else:
                return "Dear Family & Friends,"

    @classmethod
    def generate_invitations(
        cls,
        request: InvitationGenerateRequest,
        guest: Optional[GuestModel] = None,
        db: Optional[Session] = None,
    ) -> InvitationGenerateResponse:
        """
        Generates 3 personalized invitation variations in requested language (English/Hindi/Gujarati)
        using Gemini if available, or deterministic multilingual fallback engine.
        Dynamically retrieves venue and start time from the selected event if missing or generic.
        """
        # Dynamically resolve venue and start time from database event record if provided
        if db and request.event_id:
            if not request.venue or request.venue.strip() in ("", "Celebration Hall", "Royal Banquet", "Grand Venue"):
                resolved_venue = resolve_event_venue(db, request.event_id, request.location)
                if resolved_venue:
                    request.venue = resolved_venue
            if not request.event_time or request.event_time.strip() in ("", "7:00 PM", "7:00 PM onwards"):
                resolved_time = resolve_event_time(db, request.event_id)
                if resolved_time:
                    request.event_time = resolved_time

        greeting = cls.get_greeting_text(request.language, guest)

        # Attempt Gemini call if API key available
        gemini_variations = None
        if GEMINI_API_KEY:
            try:
                gemini_variations = cls._generate_via_gemini(request, greeting)
            except Exception as e:
                logger.warning(f"Gemini invitation generation failed, falling back to deterministic templates: {e}")

        if gemini_variations and len(gemini_variations) == 3:
            return InvitationGenerateResponse(
                variations=gemini_variations,
                language=request.language,
                style=request.style,
                model_used="gemini",
            )

        # High-fidelity deterministic multilingual fallback engine
        fallback_variations = cls._generate_multilingual_fallback(request, greeting)
        return InvitationGenerateResponse(
            variations=fallback_variations,
            language=request.language,
            style=request.style,
            model_used="fallback_multilingual_engine",
        )

    @classmethod
    def _generate_via_gemini(
        cls,
        request: InvitationGenerateRequest,
        greeting: str,
    ) -> Optional[List[InvitationVariation]]:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)

        prompt = f"""You are an elite, culturally fluent invitation copywriter specializing in luxury event stationery.
Generate exactly 3 distinctly styled invitation text variations for the following event.

EVENT INFORMATION:
- Event Type: {request.event_type}
- Event Title: {request.event_name}
- Hosts: {request.host_names}
- Date: {request.event_date}
- Time: {request.event_time}
- Venue: {request.venue}
- Location: {request.location}
- Instructions: {request.additional_instructions or "None"}
- Target Language: {request.language} (CRITICAL: Must write entirely in {request.language} script)
- Style: {request.style}
- Tone: {request.tone or "Warm & Welcoming"}
- Recipient Greeting: {greeting}

RULES:
1. Return ONLY a valid JSON array of 3 variation objects.
2. PRESERVE exact event title (keep '{request.event_name}' verbatim), dates (keep '{request.event_date}' verbatim), times, host names ('{request.host_names}'), venue ('{request.venue}'), and location as provided. Do not invent missing facts.
3. For Hindi, use elegant Devanagari script (e.g. शुभ निमंत्रण, मांगलिक अवसर).
4. For Gujarati, use authentic Gujarati script (e.g. રૂડો અવસર, સ્નેહી સ્વજનો).
5. For English, use refined, evocative stationery phrasing.
6. Each object must have:
   - "variation_id": 1, 2, or 3
   - "variation_name": short descriptive title (e.g., "Warm & Gracious", "Regal & Traditional", "Poetic & Joyful")
   - "components": {{
       "personalized_greeting": "{greeting}",
       "event_details": "Date ({request.event_date}), Time, Venue, Location formatted neatly",
       "invitation_message": "Main evocative invitation paragraph",
       "closing_message": "Sign-off and host names",
       "full_text": "Complete assembled ready-to-share message"
   }}
"""
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        data = json.loads(response.text)
        if isinstance(data, dict) and "variations" in data:
            data = data["variations"]

        variations = []
        for idx, item in enumerate(data[:3]):
            comps = item.get("components", {})
            event_details = comps.get("event_details") or f"{request.event_date} at {request.event_time} | {request.venue}, {request.location}"
            if request.event_date and request.event_date not in event_details:
                event_details = f"{request.event_date} | {event_details}"

            full_text = comps.get("full_text") or (
                f"{comps.get('personalized_greeting', greeting)}\n\n"
                f"{comps.get('invitation_message', '')}\n\n"
                f"{event_details}\n\n"
                f"{comps.get('closing_message', '')}"
            )
            if request.event_date and request.event_date not in full_text:
                full_text = f"{full_text}\nDate: {request.event_date}"
            if request.event_name and request.event_name not in full_text and request.event_name not in event_details:
                full_text = f"{full_text}\nEvent: {request.event_name}"

            variations.append(
                InvitationVariation(
                    variation_id=idx + 1,
                    variation_name=item.get("variation_name", f"Variation {idx + 1}"),
                    components=InvitationTextComponents(
                        personalized_greeting=comps.get("personalized_greeting", greeting),
                        event_details=event_details,
                        invitation_message=comps.get("invitation_message", ""),
                        closing_message=comps.get("closing_message", f"Warmly,\n{request.host_names}"),
                        full_text=full_text,
                    ),
                )
            )
        return variations if len(variations) == 3 else None

    @classmethod
    def _generate_multilingual_fallback(
        cls,
        request: InvitationGenerateRequest,
        greeting: str,
    ) -> List[InvitationVariation]:
        lang = (request.language or "English").title()
        title = request.event_name
        hosts = request.host_names or "The Host Family"
        date = request.event_date
        raw_time = request.event_time
        venue = request.venue or "Grand Celebration Hall"
        loc = request.location or "City"
        notes = f"\nNote: {request.additional_instructions}" if request.additional_instructions else ""
        ev_type = (request.event_type or "").lower()

        # Format time with AM/PM and language localization
        formatted_time = format_event_time(raw_time, lang)

        if lang == "Hindi":
            details_str = f"दिनांक: {date} | समय: {formatted_time}\nस्थान: {venue}, {loc}{notes}"

            if "birthday" in ev_type:
                var1 = InvitationVariation(
                    variation_id=1,
                    variation_name="पारम्परिक एवं आत्मीय (Traditional & Heartfelt)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"ईश्वर के असीम शुभाशीष से '{title}' के आनंदमय अवसर पर आप सपरिवार सादर आमंत्रित हैं। "
                            f"आपकी उपस्थिति और शुभाशीर्वाद इस विशेष दिन को और भी यादगार बनाएंगे।"
                        ),
                        closing_message=f"स्नेही स्वजन:\n{hosts}\nसप्रेम पधारिए!",
                        full_text=(
                            f"{greeting}\n\n"
                            f"ईश्वर के असीम शुभाशीष से '{title}' के आनंदमय अवसर पर आप सपरिवार सादर आमंत्रित हैं। "
                            f"आपकी उपस्थिति और शुभाशीर्वाद इस विशेष दिन को और भी यादगार बनाएंगे।\n\n"
                            f"{details_str}\n\n"
                            f"स्नेही स्वजन:\n{hosts}\nसप्रेम पधारिए!"
                        ),
                    ),
                )
                var2 = InvitationVariation(
                    variation_id=2,
                    variation_name="शाही एवं भव्य (Royal & Grand)",
                    components=InvitationTextComponents(
                        personalized_greeting=f"शुभ निमंत्रण,\n{greeting}",
                        event_details=details_str,
                        invitation_message=(
                            f"उमंग और उल्लास के इस दिन, {hosts} आपको '{title}' के जन्मदिन समारोह में शामिल होने का हार्दिक न्योता देते हैं। "
                            f"आइए, खुशियों से भरी इस महफ़िल में शामिल होकर इस दिन को अविस्मरणीय बनाएं।"
                        ),
                        closing_message=f"विनीत एवं स्वागताकांक्षी:\n{hosts}",
                        full_text=(
                            f"शुभ निमंत्रण\n\n{greeting}\n\n"
                            f"उमंग और उल्लास के इस दिन, {hosts} आपको '{title}' के जन्मदिन समारोह में शामिल होने का हार्दिक न्योता देते हैं। "
                            f"आइए, खुशियों से भरी इस महफ़िल में शामिल होकर इस दिन को अविस्मरणीय बनाएं।\n\n"
                            f"{details_str}\n\n"
                            f"विनीत एवं स्वागताकांक्षी:\n{hosts}"
                        ),
                    ),
                )
                var3 = InvitationVariation(
                    variation_id=3,
                    variation_name="उल्लसित एवं आधुनिक (Joyous & Modern)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"मस्ती, संगीत और ढेरों खुशियों से भरी शाम! {hosts} आपको '{title}' के शानदार जश्न में आमंत्रित करते हैं। "
                            f"आइए, मिलकर केक काटें और यादगार पल बनाएं!"
                        ),
                        closing_message=f"सस्नेह आपकी प्रतीक्षा में,\n{hosts}",
                        full_text=(
                            f"{greeting}\n\n"
                            f"मस्ती, संगीत और ढेरों खुशियों से भरी शाम! {hosts} आपको '{title}' के शानदार जश्न में आमंत्रित करते हैं। "
                            f"आइए, मिलकर केक काटें और यादगार पल बनाएं!\n\n"
                            f"{details_str}\n\n"
                            f"सस्नेह आपकी प्रतीक्षा में,\n{hosts}"
                        ),
                    ),
                )
            elif "community" in ev_type:
                var1 = InvitationVariation(
                    variation_id=1,
                    variation_name="सकारात्मक एवं प्रेरक (Community & Inspiring)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"सामाजिक सौहार्द एवं जन-सहयोग से आयोजित '{title}' के पावन अवसर पर आप सभी गणमान्य नागरिक सादर आमंत्रित हैं। "
                            f"आपकी गरिमामयी उपस्थिति इस आयोजन को सफल एवं प्रेरणादायी बनाएगी।"
                        ),
                        closing_message=f"आयोजक मंडल:\n{hosts}\nसादर आमंत्रित",
                        full_text=(
                            f"{greeting}\n\n"
                            f"सामाजिक सौहार्द एवं जन-सहयोग से आयोजित '{title}' के पावन अवसर पर आप सभी गणमान्य नागरिक सादर आमंत्रित हैं। "
                            f"आपकी गरिमामयी उपस्थिति इस आयोजन को सफल एवं प्रेरणादायी बनाएगी।\n\n"
                            f"{details_str}\n\n"
                            f"आयोजक मंडल:\n{hosts}\nसादर आमंत्रित"
                        ),
                    ),
                )
                var2 = InvitationVariation(
                    variation_id=2,
                    variation_name="भव्य एवं संगठित (Grand & Formal)",
                    components=InvitationTextComponents(
                        personalized_greeting=f"सादर निमंत्रण,\n{greeting}",
                        event_details=details_str,
                        invitation_message=(
                            f"एकता, ऊर्जा और सामाजिक सहभागिता के इस विशेष उत्सव पर {hosts} आपको '{title}' में पधारने का सस्नेह निमंत्रण देते हैं। "
                            f"आपकी उपस्थिति हम सभी के लिए गौरव की बात है।"
                        ),
                        closing_message=f"विनीत:\n{hosts}",
                        full_text=(
                            f"सादर निमंत्रण\n\n{greeting}\n\n"
                            f"एकता, ऊर्जा और सामाजिक सहभागिता के इस विशेष उत्सव पर {hosts} आपको '{title}' में पधारने का सस्नेह निमंत्रण देते हैं। "
                            f"आपकी उपस्थिति हम सभी के लिए गौरव की बात है।\n\n"
                            f"{details_str}\n\n"
                            f"विनीत:\n{hosts}"
                        ),
                    ),
                )
                var3 = InvitationVariation(
                    variation_id=3,
                    variation_name="उत्साही एवं आधुनिक (Vibrant & Inclusive)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"आइए मिलकर मनाएं! {hosts} आप सभी को '{title}' के इस भव्य उत्सव में सम्मिलित होने के लिए हार्दिक आमंत्रित करते हैं। "
                            f"आइए, साथ मिलकर नई उमंगों और प्रेरणा का स्वागत करें।"
                        ),
                        closing_message=f"सादर,\n{hosts}",
                        full_text=(
                            f"{greeting}\n\n"
                            f"आइए मिलकर मनाएं! {hosts} आप सभी को '{title}' के इस भव्य उत्सव में सम्मिलित होने के लिए हार्दिक आमंत्रित करते हैं। "
                            f"आइए, साथ मिलकर नई उमंगों और प्रेरणा का स्वागत करें।\n\n"
                            f"{details_str}\n\n"
                            f"सादर,\n{hosts}"
                        ),
                    ),
                )
            else:
                # Wedding & Milestone
                var1 = InvitationVariation(
                    variation_id=1,
                    variation_name="पारम्परिक एवं आत्मीय (Traditional & Heartfelt)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"ईश्वर की असीम अनुकम्पा से हमारे यहाँ '{title}' का पावन एवं मांगलिक वैवाहिक आयोजन संपन्न होने जा रहा है। "
                            f"इस मंगल बेला में आप सपरिवार सादर आमंत्रित हैं। आपकी गरिमामयी उपस्थिति नवयुगल को शुभाशीष प्रदान करेगी।"
                        ),
                        closing_message=f"दर्शनाभिलाषी एवं स्नेही स्वजन:\n{hosts}\nसप्रेम पधारिए!",
                        full_text=(
                            f"॥ ॐ श्री गणेशाय नमः ॥\n\n{greeting}\n\n"
                            f"ईश्वर की असीम अनुकम्पा से हमारे यहाँ '{title}' का पावन एवं मांगलिक वैवाहिक आयोजन संपन्न होने जा रहा है। "
                            f"इस मंगल बेला में आप सपरिवार सादर आमंत्रित हैं। आपकी गरिमामयी उपस्थिति नवयुगल को शुभाशीष प्रदान करेगी।\n\n"
                            f"{details_str}\n\n"
                            f"दर्शनाभिलाषी एवं स्नेही स्वजन:\n{hosts}\nसप्रेम पधारिए!"
                        ),
                    ),
                )
                var2 = InvitationVariation(
                    variation_id=2,
                    variation_name="शाही एवं भव्य (Royal & Grand)",
                    components=InvitationTextComponents(
                        personalized_greeting=f"शुभ निमंत्रण,\n{greeting}",
                        event_details=details_str,
                        invitation_message=(
                            f"हर्ष और गौरव के इस अविस्मरणीय अवसर पर, {hosts} आपको '{title}' के भव्य उत्सव में सम्मिलित होने का सस्नेह न्योता देते हैं। "
                            f"यह दिन हमारे परिवार का एक अनमोल अध्याय है, और आपकी उपस्थिति हमारे लिए सबसे बड़ा उपहार होगी।"
                        ),
                        closing_message=f"विनीत एवं स्वागताकांक्षी:\n{hosts}\nकृपया पधारकर नव-उमंगों को अपना शुभाशीष प्रदान करें।",
                        full_text=(
                            f"॥ ॐ श्री गणेशाय नमः ॥\nशुभ निमंत्रण\n\n{greeting}\n\n"
                            f"हर्ष और गौरव के इस अविस्मरणीय अवसर पर, {hosts} आपको '{title}' के भव्य उत्सव में सम्मिलित होने का सस्नेह न्योता देते हैं। "
                            f"यह दिन हमारे परिवार का एक अनमोल अध्याय है, और आपकी उपस्थिति हमारे लिए सबसे बड़ा उपहार होगी।\n\n"
                            f"{details_str}\n\n"
                            f"विनीत एवं स्वागताकांक्षी:\n{hosts}\nकृपया पधारकर नव-उमंगों को अपना शुभाशीष प्रदान करें।"
                        ),
                    ),
                )
                var3 = InvitationVariation(
                    variation_id=3,
                    variation_name="उल्लसित एवं आधुनिक (Joyous & Modern)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"खुशियों के पल अपनों के संग ही खास बनते हैं! {hosts} आपको '{title}' की इस यादगार शाम में शामिल होने का सप्रेम निमंत्रण देते हैं। "
                            f"आइए, खुशियों, संगीत और बेहतरीन यादों से भरी इस शाम को एक साथ मिलकर मनाएं!"
                        ),
                        closing_message=f"सस्नेह आपकी प्रतीक्षा में,\n{hosts}",
                        full_text=(
                            f"{greeting}\n\n"
                            f"खुशियों के पल अपनों के संग ही खास बनते हैं! {hosts} आपको '{title}' की इस यादगार शाम में शामिल होने का सप्रेम निमंत्रण देते हैं। "
                            f"आइए, खुशियों, संगीत और बेहतरीन यादों से भरी इस शाम को एक साथ मिलकर मनाएं!\n\n"
                            f"{details_str}\n\n"
                            f"सस्नेह आपकी प्रतीक्षा में,\n{hosts}"
                        ),
                    ),
                )
            return [var1, var2, var3]

        elif lang == "Gujarati":
            details_str = f"તારીખ: {date} | સમય: {formatted_time}\nસ્થળ: {venue}, {loc}{notes}"

            if "birthday" in ev_type:
                var1 = InvitationVariation(
                    variation_id=1,
                    variation_name="પરંપરાગત અને સ્નેહપૂર્ણ (Traditional & Affectionate)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"પરમકૃપાળુ પરમાત્માના આશીર્વાદથી '{title}'ની મંગલ ઉજવણી નિમિત્તે આપ સહપરિવાર સ્નેહપૂર્વક આમંત્રિત છો. "
                            f"આપના પ્રેમ અને આશીર્વાદથી આ દિવસ વધુ યાદગાર અને આનંદમય બનશે."
                        ),
                        closing_message=f"સ્નેહી સ્વજનો:\n{hosts}\nપધારશો જરૂર!",
                        full_text=(
                            f"{greeting}\n\n"
                            f"પરમકૃપાળુ પરમાત્માના આશીર્વાદથી '{title}'ની મંગલ ઉજવણી નિમિત્તે આપ સહપરિવાર સ્નેહપૂર્વક આમંત્રિત છો. "
                            f"આપના પ્રેમ અને આશીર્વાદથી આ દિવસ વધુ યાદગાર અને આનંદમય બનશે.\n\n"
                            f"{details_str}\n\n"
                            f"સ્નેહી સ્વજનો:\n{hosts}\nપધારશો જરૂર!"
                        ),
                    ),
                )
                var2 = InvitationVariation(
                    variation_id=2,
                    variation_name="રાજવી અને ભવ્ય (Royal & Grand)",
                    components=InvitationTextComponents(
                        personalized_greeting=f"સાદર નિમંત્રણ,\n{greeting}",
                        event_details=details_str,
                        invitation_message=(
                            f"ખુશીઓ, ઉત્સાહ અને આનંદના આ રૂડા અવસરે, {hosts} આપને '{title}'ના જન્મદિવસના ભવ્ય સમારોહમાં પધારવા હૃદયપૂર્વકનું નિમંત્રણ પાઠવે છે. "
                            f"આપની સ્નેહભરી ઉપસ્થિતિ બાળકના આનંદમાં અભિવૃદ્ધિ કરશે."
                        ),
                        closing_message=f"વિનીત:\n{hosts}\nઆપના સ્નેહ અને આશીર્વાદ સહ.",
                        full_text=(
                            f"સાદર નિમંત્રણ\n\n{greeting}\n\n"
                            f"ખુશીઓ, ઉત્સાહ અને આનંદના આ રૂડા અવસરે, {hosts} આપને '{title}'ના જન્મદિવસના ભવ્ય સમારોહમાં પધારવા હૃદયપૂર્વકનું નિમંત્રણ પાઠવે છે. "
                            f"આપની સ્નેહભરી ઉપસ્થિતિ બાળકના આનંદમાં અભિવૃદ્ધિ કરશે.\n\n"
                            f"{details_str}\n\n"
                            f"વિનીત:\n{hosts}\nઆપના સ્નેહ અને આશીર્વાદ સહ."
                        ),
                    ),
                )
                var3 = InvitationVariation(
                    variation_id=3,
                    variation_name="આધુનિક અને ઉત્સાહભર્યું (Joyful & Modern)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"મસ્તી, સંગીત, રમતો અને સ્વાદિષ્ટ કેક કટિંગની ધમાકેદાર ઉજવણી! {hosts} આપને '{title}'માં સામેલ થવા દિલથી આવકારે છે. "
                            f"ચાલો સાથે મળીને આ સાંજને અવિસ્મરણીય અને ઉત્સાહભરી બનાવીએ!"
                        ),
                        closing_message=f"સ્નેહપૂર્વક,\n{hosts}\nપધારશો જરૂર!",
                        full_text=(
                            f"{greeting}\n\n"
                            f"મસ્તી, સંગીત, રમતો અને સ્વાદિષ્ટ કેક કટિંગની ધમાકેદાર ઉજવણી! {hosts} આપને '{title}'માં સામેલ થવા દિલથી આવકારે છે. "
                            f"ચાલો સાથે મળીને આ સાંજને અવિસ્મરણીય અને ઉત્સાહભરી બનાવીએ!\n\n"
                            f"{details_str}\n\n"
                            f"સ્નેહપૂર્વક,\n{hosts}\nપધારશો જરૂર!"
                        ),
                    ),
                )
            elif "community" in ev_type:
                var1 = InvitationVariation(
                    variation_id=1,
                    variation_name="પરંપરાગત અને સામુદાયિક (Community & Inspiring)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"આપણા વિસ્તારના સર્વે સ્નેહીજનો અને પરિવારો માટે આયોજિત '{title}'ના પાવન અવસરે આપ સર્વે સહપરિવાર પધારવા ભાવભર્યું નિમંત્રણ છે. "
                            f"આપની ઉપસ્થિતિ આપણા સમાજની શોભા અને ઉત્સાહમાં વધારો કરશે."
                        ),
                        closing_message=f"નિમંત્રક:\n{hosts}\nસાદર આમંત્રણ સહ.",
                        full_text=(
                            f"{greeting}\n\n"
                            f"આપણા વિસ્તારના સર્વે સ્નેહીજનો અને પરિવારો માટે આયોજિત '{title}'ના પાવન અવસરે આપ સર્વે સહપરિવાર પધારવા ભાવભર્યું નિમંત્રણ છે. "
                            f"આપની ઉપસ્થિતિ આપણા સમાજની શોભા અને ઉત્સાહમાં વધારો કરશે.\n\n"
                            f"{details_str}\n\n"
                            f"નિમંત્રક:\n{hosts}\nસાદર આમંત્રણ સહ."
                        ),
                    ),
                )
                var2 = InvitationVariation(
                    variation_id=2,
                    variation_name="ભવ્ય મહોત્સવ (Grand & Formal)",
                    components=InvitationTextComponents(
                        personalized_greeting=f"સાદર નિમંત્રણ,\n{greeting}",
                        event_details=details_str,
                        invitation_message=(
                            f"સામાજિક એકતા, સાંસ્કૃતિક વારસો અને પ્રેરણાદાયી વિચારોના આ પાવન સંગમ '{title}'માં {hosts} આપને ગૌરવપૂર્વક આમંત્રે છે. "
                            f"આપની ગરિમામય ઉપસ્થિતિ આ મહોત્સવની શોભા વધારશે."
                        ),
                        closing_message=f"વિનીત:\n{hosts}\nઆપ સૌનું હાર્દિક સ્વાગત છે.",
                        full_text=(
                            f"સાદર નિમંત્રણ\n\n{greeting}\n\n"
                            f"સામાજિક એકતા, સાંસ્કૃતિક વારસો અને પ્રેરણાદાયી વિચારોના આ પાવન સંગમ '{title}'માં {hosts} આપને ગૌરવપૂર્વક આમંત્રે છે. "
                            f"આપની ગરિમામય ઉપસ્થિતિ આ મહોત્સવની શોભા વધારશે.\n\n"
                            f"{details_str}\n\n"
                            f"વિનીત:\n{hosts}\nઆપ સૌનું હાર્દિક સ્વાગત છે."
                        ),
                    ),
                )
                var3 = InvitationVariation(
                    variation_id=3,
                    variation_name="ઉલ્લાસમય અને સક્રિય (Vibrant & Inclusive)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"નવીન ઉમંગો, પ્રેરણા અને સામુદાયિક ઉત્સાહનો ભવ્ય સમારોહ! {hosts} આપ સર્વેને '{title}'માં સહભાગી થવા હૃદયપૂર્વક આવકારે છે. "
                            f"પધારીને કાર્યક્રમને સફળ અને યાદગાર બનાવો."
                        ),
                        closing_message=f"સ્નેહપૂર્વક,\n{hosts}",
                        full_text=(
                            f"{greeting}\n\n"
                            f"નવીન ઉમંગો, પ્રેરણા અને સામુદાયિક ઉત્સાહનો ભવ્ય સમારોહ! {hosts} આપ સર્વેને '{title}'માં સહભાગી થવા હૃદયપૂર્વક આવકારે છે. "
                            f"પધારીને કાર્યક્રમને સફળ અને યાદગાર બનાવો.\n\n"
                            f"{details_str}\n\n"
                            f"સ્નેહપૂર્વક,\n{hosts}"
                        ),
                    ),
                )
            else:
                # Wedding & Traditional Celebrations
                var1 = InvitationVariation(
                    variation_id=1,
                    variation_name="પરંપરાગત અને સ્નેહપૂર્ણ (Traditional & Affectionate)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"પરમકૃપાળુ પરમાત્માની અસીમ કૃપાથી અમારા પરિવારમાં '{title}'નો રૂડો અને મંગલમય વિવાહ પ્રસંગ યોજાયેલ છે. "
                            f"આ પાવન વેળાએ આપ સહપરિવાર ઉપસ્થિત રહી નવદંપતીને સ્નેહભર્યા શુભાશિષ આપશો અને અમારા આનંદમાં સહભાગી થશો એ જ ભાવભર્યું નિમંત્રણ છે."
                        ),
                        closing_message=f"લિ. આપના સ્નેહી:\n{hosts}\nદર્શનાભિલાષી સર્વે પરિવાર.",
                        full_text=(
                            f"॥ ૐ શ્રી ગણેશાય નમઃ ॥\n\n{greeting}\n\n"
                            f"પરમકૃપાળુ પરમાત્માની અસીમ કૃપાથી અમારા પરિવારમાં '{title}'નો રૂડો અને મંગલમય વિવાહ પ્રસંગ યોજાયેલ છે. "
                            f"આ પાવન વેળાએ આપ સહપરિવાર ઉપસ્થિત રહી નવદંપતીને સ્નેહભર્યા શુભાશિષ આપશો અને અમારા આનંદમાં સહભાગી થશો એ જ ભાવભર્યું નિમંત્રણ છે.\n\n"
                            f"{details_str}\n\n"
                            f"લિ. આપના સ્નેહી:\n{hosts}\nદર્શનાભિલાષી સર્વે પરિવાર."
                        ),
                    ),
                )
                var2 = InvitationVariation(
                    variation_id=2,
                    variation_name="રાજવી અને ભવ્ય (Royal & Grand)",
                    components=InvitationTextComponents(
                        personalized_greeting=f"સાદર નિમંત્રણ,\n{greeting}",
                        event_details=details_str,
                        invitation_message=(
                            f"અત્યંત હર્ષ અને ગૌરવ સાથે, {hosts} આપને '{title}'ના ભવ્ય અને માંગલિક મહોત્સવમાં પધારવા હૃદયપૂર્વકનું સાદર નિમંત્રણ પાઠવે છે. "
                            f"આપની ગરિમામય ઉપસ્થિતિ આ મંગલ અવસરની શોભામાં અભિવૃદ્ધિ કરશે."
                        ),
                        closing_message=f"વિનીત:\n{hosts}\nઆપના સ્નેહ અને આશીર્વાદની અભિલાષા સહ.",
                        full_text=(
                            f"॥ ૐ શ્રી ગણેશાય નમઃ ॥\nસાદર નિમંત્રણ\n\n{greeting}\n\n"
                            f"અત્યંત હર્ષ અને ગૌરવ સાથે, {hosts} આપને '{title}'ના ભવ્ય અને માંગલિક મહોત્સવમાં પધારવા હૃદયપૂર્વકનું સાદર નિમંત્રણ પાઠવે છે. "
                            f"આપની ગરિમામય ઉપસ્થિતિ આ મંગલ અવસરની શોભામાં અભિવૃદ્ધિ કરશે.\n\n"
                            f"{details_str}\n\n"
                            f"વિનીત:\n{hosts}\nઆપના સ્નેહ અને આશીર્વાદની અભિલાષા સહ."
                        ),
                    ),
                )
                var3 = InvitationVariation(
                    variation_id=3,
                    variation_name="આધુનિક અને ઉત્સાહભર્યું (Joyful & Modern)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"સુંદર યાદો અને ખુશીઓની ઉજવણી જ્યારે આપ સહુ સ્નેહીજનો સાથે હોય ત્યારે જ યાદગાર બને છે! "
                            f"{hosts} આપને '{title}'ની રોમાંચક ઉજવણીમાં સામેલ થવા દિલથી આવકારે છે. ચાલો સાથે મળીને આ સાંજને અવિસ્મરણીય બનાવીએ!"
                        ),
                        closing_message=f"સ્નેહપૂર્વક,\n{hosts}\nપધારશો જરૂર!",
                        full_text=(
                            f"{greeting}\n\n"
                            f"સુંદર યાદો અને ખુશીઓની ઉજવણી જ્યારે આપ સહુ સ્નેહીજનો સાથે હોય ત્યારે જ યાદગાર બને છે! "
                            f"{hosts} આપને '{title}'ની રોમાંચક ઉજવણીમાં સામેલ થવા દિલથી આવકારે છે. ચાલો સાથે મળીને આ સાંજને અવિસ્મરણીય બનાવીએ!\n\n"
                            f"{details_str}\n\n"
                            f"સ્નેહપૂર્વક,\n{hosts}\nપધારશો જરૂર!"
                        ),
                    ),
                )
            return [var1, var2, var3]

        else:
            # English
            details_str = f"Date: {date} | Time: {formatted_time}\nVenue: {venue}, {loc}{notes}"

            if "birthday" in ev_type:
                var1 = InvitationVariation(
                    variation_id=1,
                    variation_name="Warm & Heartfelt (Birthday Celebration)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"Another wonderful year of joy and milestones! {hosts} cordially invite you to join us in celebrating '{title}'. "
                            f"Your gracious presence and warm blessings will make this birthday celebration truly special."
                        ),
                        closing_message=f"With warm regards,\n{hosts}",
                        full_text=(
                            f"{greeting}\n\n"
                            f"Another wonderful year of joy and milestones! {hosts} cordially invite you to join us in celebrating '{title}'. "
                            f"Your gracious presence and warm blessings will make this birthday celebration truly special.\n\n"
                            f"{details_str}\n\n"
                            f"With warm regards,\n{hosts}"
                        ),
                    ),
                )
                var2 = InvitationVariation(
                    variation_id=2,
                    variation_name="Grand & Joyful (Birthday Gala)",
                    components=InvitationTextComponents(
                        personalized_greeting=f"In Celebration of a Wonderful Milestone,\n{greeting}",
                        event_details=details_str,
                        invitation_message=(
                            f"{hosts} request the pleasure of your company at the birthday celebration of '{title}'. "
                            f"We look forward to an evening of music, celebration, and delightful memories together."
                        ),
                        closing_message=f"Warmly,\n{hosts}",
                        full_text=(
                            f"In Celebration of a Wonderful Milestone\n\n{greeting}\n\n"
                            f"{hosts} request the pleasure of your company at the birthday celebration of '{title}'. "
                            f"We look forward to an evening of music, celebration, and delightful memories together.\n\n"
                            f"{details_str}\n\n"
                            f"Warmly,\n{hosts}"
                        ),
                    ),
                )
                var3 = InvitationVariation(
                    variation_id=3,
                    variation_name="Fun & Modern (Party Edition)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"Get ready for laughter, great games, and sweet celebration! {hosts} invite you to join us for '{title}'. "
                            f"Come ready for fabulous cake, fun beats, and good times!"
                        ),
                        closing_message=f"Can't wait to celebrate together!\n{hosts}",
                        full_text=(
                            f"{greeting}\n\n"
                            f"Get ready for laughter, great games, and sweet celebration! {hosts} invite you to join us for '{title}'. "
                            f"Come ready for fabulous cake, fun beats, and good times!\n\n"
                            f"{details_str}\n\n"
                            f"Can't wait to celebrate together!\n{hosts}"
                        ),
                    ),
                )
            elif "community" in ev_type:
                var1 = InvitationVariation(
                    variation_id=1,
                    variation_name="Community & Civic (Warm Traditional)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"Bringing our community together in friendship and celebration! {hosts} cordially invite you and your family to '{title}'. "
                            f"Your active participation and presence enrich our neighborhood spirit."
                        ),
                        closing_message=f"Organizing Committee:\n{hosts}",
                        full_text=(
                            f"{greeting}\n\n"
                            f"Bringing our community together in friendship and celebration! {hosts} cordially invite you and your family to '{title}'. "
                            f"Your active participation and presence enrich our neighborhood spirit.\n\n"
                            f"{details_str}\n\n"
                            f"Organizing Committee:\n{hosts}"
                        ),
                    ),
                )
                var2 = InvitationVariation(
                    variation_id=2,
                    variation_name="Grand & Inspiring (Formal Gathering)",
                    components=InvitationTextComponents(
                        personalized_greeting=f"Cordial Invitation,\n{greeting}",
                        event_details=details_str,
                        invitation_message=(
                            f"{hosts} request the honour of your presence at '{title}'. "
                            f"Join us for an inspiring session of collaboration, cultural showcases, and shared community vision."
                        ),
                        closing_message=f"Warm regards,\n{hosts}",
                        full_text=(
                            f"Cordial Invitation\n\n{greeting}\n\n"
                            f"{hosts} request the honour of your presence at '{title}'. "
                            f"Join us for an inspiring session of collaboration, cultural showcases, and shared community vision.\n\n"
                            f"{details_str}\n\n"
                            f"Warm regards,\n{hosts}"
                        ),
                    ),
                )
                var3 = InvitationVariation(
                    variation_id=3,
                    variation_name="Vibrant & Interactive (Modern Fest)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"Exciting ideas, vibrant energy, and wonderful conversations await! {hosts} welcome you to '{title}'. "
                            f"Let's celebrate our shared journey and make lasting connections!"
                        ),
                        closing_message=f"See you there!\n{hosts}",
                        full_text=(
                            f"{greeting}\n\n"
                            f"Exciting ideas, vibrant energy, and wonderful conversations await! {hosts} welcome you to '{title}'. "
                            f"Let's celebrate our shared journey and make lasting connections!\n\n"
                            f"{details_str}\n\n"
                            f"See you there!\n{hosts}"
                        ),
                    ),
                )
            else:
                # Wedding & Milestones
                var1 = InvitationVariation(
                    variation_id=1,
                    variation_name="Warm & Gracious (Heartfelt Traditional)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"Together with our families, {hosts} cordially invite you to join us in celebrating '{title}'. "
                            f"This joyous milestone holds a deeply special place in our hearts, and your gracious presence and blessings would mean the world to us."
                        ),
                        closing_message=f"With warmest regards,\n{hosts}",
                        full_text=(
                            f"{greeting}\n\n"
                            f"Together with our families, {hosts} cordially invite you to join us in celebrating '{title}'. "
                            f"This joyous milestone holds a deeply special place in our hearts, and your gracious presence and blessings would mean the world to us.\n\n"
                            f"{details_str}\n\n"
                            f"With warmest regards,\n{hosts}"
                        ),
                    ),
                )
                var2 = InvitationVariation(
                    variation_id=2,
                    variation_name="Royal & Grand (Formal Elegance)",
                    components=InvitationTextComponents(
                        personalized_greeting=f"In Celebration of Grand Milestones,\n{greeting}",
                        event_details=details_str,
                        invitation_message=(
                            f"{hosts} request the honour of your company at the celebration of '{title}'. "
                            f"We look forward to welcoming you for an evening of warmth, celebration, and exquisite memories as we commemorate this momentous occasion."
                        ),
                        closing_message=f"Cordially,\n{hosts}",
                        full_text=(
                            f"In Celebration of Grand Milestones\n\n{greeting}\n\n"
                            f"{hosts} request the honour of your company at the celebration of '{title}'. "
                            f"We look forward to welcoming you for an evening of warmth, celebration, and exquisite memories as we commemorate this momentous occasion.\n\n"
                            f"{details_str}\n\n"
                            f"Cordially,\n{hosts}"
                        ),
                    ),
                )
                var3 = InvitationVariation(
                    variation_id=3,
                    variation_name="Joyful & Celebratory (Modern Casual)",
                    components=InvitationTextComponents(
                        personalized_greeting=greeting,
                        event_details=details_str,
                        invitation_message=(
                            f"The celebration wouldn't be complete without you! {hosts} are delighted to invite you to join us for '{title}'. "
                            f"Get ready for wonderful moments, lively conversations, and memories to cherish forever!"
                        ),
                        closing_message=f"Can't wait to celebrate together!\n{hosts}",
                        full_text=(
                            f"{greeting}\n\n"
                            f"The celebration wouldn't be complete without you! {hosts} are delighted to invite you to join us for '{title}'. "
                            f"Get ready for wonderful moments, lively conversations, and memories to cherish forever!\n\n"
                            f"{details_str}\n\n"
                            f"Can't wait to celebrate together!\n{hosts}"
                        ),
                    ),
                )
            return [var1, var2, var3]

    @classmethod
    def save_invitation(cls, db: Session, req: InvitationCreateRequest) -> InvitationResponse:
        # Verify event exists
        event = db.query(EventModel).filter(EventModel.id == req.event_id).first()
        if not event:
            raise ValueError(f"Event {req.event_id} not found")

        guest_name = None
        if req.guest_id:
            guest = db.query(GuestModel).filter(GuestModel.id == req.guest_id).first()
            if guest:
                guest_name = guest.full_name

        inv_id = str(uuid.uuid4())
        now_str = datetime.now().isoformat()

        inv = InvitationModel(
            id=inv_id,
            event_id=req.event_id,
            guest_id=req.guest_id,
            title=req.title,
            language=req.language,
            style=req.style,
            template_id=req.template_id,
            invitation_text_json=req.text_components.model_dump_json(),
            design_config_json=req.design_config.model_dump_json(),
            created_at=now_str,
            updated_at=now_str,
        )
        db.add(inv)
        db.commit()
        db.refresh(inv)

        return cls._to_response(inv, guest_name=guest_name)

    @classmethod
    def get_event_invitations(cls, db: Session, event_id: str) -> List[InvitationResponse]:
        records = (
            db.query(InvitationModel)
            .filter(InvitationModel.event_id == event_id)
            .order_by(InvitationModel.created_at.desc())
            .all()
        )
        results = []
        for inv in records:
            guest_name = inv.guest.full_name if inv.guest else None
            results.append(cls._to_response(inv, guest_name=guest_name))
        return results

    @classmethod
    def get_invitation(cls, db: Session, invitation_id: str) -> Optional[InvitationResponse]:
        inv = db.query(InvitationModel).filter(InvitationModel.id == invitation_id).first()
        if not inv:
            return None
        guest_name = inv.guest.full_name if inv.guest else None
        return cls._to_response(inv, guest_name=guest_name)

    @classmethod
    def delete_invitation(cls, db: Session, invitation_id: str) -> bool:
        inv = db.query(InvitationModel).filter(InvitationModel.id == invitation_id).first()
        if not inv:
            return False
        db.delete(inv)
        db.commit()
        return True

    @classmethod
    def mark_guest_invitation_sent(cls, db: Session, event_id: str, guest_id: str) -> GuestModel:
        """
        Explicitly marks a guest's invitation as Sent only upon manual confirmation.
        Preserves existing RSVP records without changing RSVP status.
        """
        guest = db.query(GuestModel).filter(
            GuestModel.id == guest_id,
            GuestModel.event_id == event_id,
        ).first()
        if not guest:
            raise ValueError(f"Guest {guest_id} not found for event {event_id}")

        guest.invitation_status = "Sent"
        guest.updated_at = datetime.now().isoformat()
        db.commit()
        db.refresh(guest)
        return guest

    @classmethod
    def _to_response(cls, inv: InvitationModel, guest_name: Optional[str] = None) -> InvitationResponse:
        text_data = json.loads(inv.invitation_text_json)
        design_data = json.loads(inv.design_config_json)
        return InvitationResponse(
            id=inv.id,
            event_id=inv.event_id,
            guest_id=inv.guest_id,
            guest_name=guest_name,
            title=inv.title,
            language=inv.language,
            style=inv.style,
            template_id=inv.template_id,
            text_components=InvitationTextComponents(**text_data),
            design_config=InvitationDesignConfig(**design_data),
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )
