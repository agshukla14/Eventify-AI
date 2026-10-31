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
from .config import GEMINI_API_KEY
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
    ) -> InvitationGenerateResponse:
        """
        Generates 3 personalized invitation variations in requested language (English/Hindi/Gujarati)
        using Gemini if available, or deterministic multilingual fallback engine.
        """
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
2. PRESERVE exact event dates, times, host names, venue, and location as provided. Do not invent missing facts.
3. For Hindi, use elegant Devanagari script (e.g. शुभ निमंत्रण, मांगलिक अवसर).
4. For Gujarati, use authentic Gujarati script (e.g. રૂડો અવસર, સ્નેહી સ્વજનો).
5. For English, use refined, evocative stationery phrasing.
6. Each object must have:
   - "variation_id": 1, 2, or 3
   - "variation_name": short descriptive title (e.g., "Warm & Gracious", "Regal & Traditional", "Poetic & Joyful")
   - "components": {{
       "personalized_greeting": "{greeting}",
       "event_details": "Date, Time, Venue, Location formatted neatly",
       "invitation_message": "Main evocative invitation paragraph",
       "closing_message": "Sign-off and host names",
       "full_text": "Complete assembled ready-to-share message"
   }}
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        data = json.loads(response.text)
        if isinstance(data, dict) and "variations" in data:
            data = data["variations"]

        variations = []
        for idx, item in enumerate(data[:3]):
            comps = item.get("components", {})
            full_text = comps.get("full_text") or (
                f"{comps.get('personalized_greeting', greeting)}\n\n"
                f"{comps.get('invitation_message', '')}\n\n"
                f"{comps.get('event_details', '')}\n\n"
                f"{comps.get('closing_message', '')}"
            )
            variations.append(
                InvitationVariation(
                    variation_id=idx + 1,
                    variation_name=item.get("variation_name", f"Variation {idx + 1}"),
                    components=InvitationTextComponents(
                        personalized_greeting=comps.get("personalized_greeting", greeting),
                        event_details=comps.get("event_details", f"{request.event_date} at {request.event_time} | {request.venue}, {request.location}"),
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
        hosts = request.host_names
        date = request.event_date
        time = request.event_time
        venue = request.venue
        loc = request.location
        notes = f"\nNote: {request.additional_instructions}" if request.additional_instructions else ""

        if lang == "Hindi":
            details_str = f"दिनांक: {date} | समय: {time}\nस्थान: {venue}, {loc}{notes}"
            var1 = InvitationVariation(
                variation_id=1,
                variation_name="पारम्परिक एवं आत्मीय (Traditional & Heartfelt)",
                components=InvitationTextComponents(
                    personalized_greeting=f"॥ श्री गणेशाय नमः ॥\n{greeting}",
                    event_details=details_str,
                    invitation_message=(
                        f"ईश्वर की असीम अनुकम्पा से हमारे यहाँ '{title}' का पावन एवं मांगलिक आयोजन संपन्न होने जा रहा है। "
                        f"इस मंगल बेला में आप सपरिवार सादर आमंत्रित हैं। आपकी गरिमामयी उपस्थिति हमारे इस पारिवारिक उत्सव को और भी पावन बनाएगी।"
                    ),
                    closing_message=f"दर्शनाभिलाषी एवं स्नेही स्वजन:\n{hosts}\nसप्रेम पधारिए!",
                    full_text=(
                        f"॥ श्री गणेशाय नमः ॥\n\n{greeting}\n\n"
                        f"ईश्वर की असीम अनुकम्पा से हमारे यहाँ '{title}' का पावन एवं मांगलिक आयोजन संपन्न होने जा रहा है। "
                        f"इस मंगल बेला में आप सपरिवार सादर आमंत्रित हैं। आपकी गरिमामयी उपस्थिति हमारे इस पारिवारिक उत्सव को और भी पावन बनाएगी।\n\n"
                        f"{details_str}\n\n"
                        f"दर्शनाभिलाषी एवं स्नेही स्वजन:\n{hosts}\nसप्रेम पधारिए!"
                    ),
                ),
            )
            var2 = InvitationVariation(
                variation_id=2,
                variation_name="शाही एवं भव्य (Royal & Grand)",
                components=InvitationTextComponents(
                    personalized_greeting=f"॥ ॐ श्री गणेशाय नमः ॥\nशुभ निमंत्रण,\n{greeting}",
                    event_details=details_str,
                    invitation_message=(
                        f"हर्ष और गौरव के इस अविस्मरणीय अवसर पर, {hosts} आपको '{title}' के भव्य उत्सव में सम्मिलित होने का सस्नेह न्योता देते हैं। "
                        f"यह दिन हमारे जीवन का एक अनमोल अध्याय है, और आपकी मंगलकारी शुभकामनाएं हमारे लिए सबसे बड़ा उपहार होंगी।"
                    ),
                    closing_message=f"विनीत एवं स्वागताकांक्षी:\n{hosts}\nकृपया पधारकर नव-उमंगों को अपना शुभाशीष प्रदान करें।",
                    full_text=(
                        f"॥ ॐ श्री गणेशाय नमः ॥\nशुभ निमंत्रण\n\n{greeting}\n\n"
                        f"हर्ष और गौरव के इस अविस्मरणीय अवसर पर, {hosts} आपको '{title}' के भव्य उत्सव में सम्मिलित होने का सस्नेह न्योता देते हैं। "
                        f"यह दिन हमारे जीवन का एक अनमोल अध्याय है, और आपकी मंगलकारी शुभकामनाएं हमारे लिए सबसे बड़ा उपहार होंगी।\n\n"
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
            details_str = f"તારીખ: {date} | સમય: {time}\nસ્થળ: {venue}, {loc}{notes}"
            var1 = InvitationVariation(
                variation_id=1,
                variation_name="પરંપરાગત અને સ્નેહપૂર્ણ (Traditional & Affectionate)",
                components=InvitationTextComponents(
                    personalized_greeting=f"॥ શ્રી ગણેશાય નમઃ ॥\n{greeting}",
                    event_details=details_str,
                    invitation_message=(
                        f"પરમકૃપાળુ પરમાત્માની અસીમ કૃપાથી અમારા આંગણે '{title}'નો રૂડો અને મંગલમય અવસર યોજાયેલ છે. "
                        f"આ સુભગ પ્રસંગે આપ સહપરિવાર ઉપસ્થિત રહી અમારા આનંદમાં સહભાગી થશો અને શુભ આશીર્વાદ આપશો એ જ ભાવભર્યું નિમંત્રણ છે."
                    ),
                    closing_message=f"લિ. આપના સ્નેહી:\n{hosts}\nદર્શનાભિલાષી સર્વે પરિવાર.",
                    full_text=(
                        f"॥ શ્રી ગણેશાય નમઃ ॥\n\n{greeting}\n\n"
                        f"પરમકૃપાળુ પરમાત્માની અસીમ કૃપાથી અમારા આંગણે '{title}'નો રૂડો અને મંગલમય અવસર યોજાયેલ છે. "
                        f"આ સુભગ પ્રસંગે આપ સહપરિવાર ઉપસ્થિત રહી અમારા આનંદમાં સહભાગી થશો અને શુભ આશીર્વાદ આપશો એ જ ભાવભર્યું નિમંત્રણ છે.\n\n"
                        f"{details_str}\n\n"
                        f"લિ. આપના સ્નેહી:\n{hosts}\nદર્શનાભિલાષી સર્વે પરિવાર."
                    ),
                ),
            )
            var2 = InvitationVariation(
                variation_id=2,
                variation_name="રાજવી અને ભવ્ય (Royal & Grand)",
                components=InvitationTextComponents(
                    personalized_greeting=f"॥ ૐ શ્રી ગણેશાય નમઃ ॥\nસાદર નિમંત્રણ,\n{greeting}",
                    event_details=details_str,
                    invitation_message=(
                        f"અત્યંત હર્ષ અને ગૌરવ સાથે, {hosts} આપને '{title}'ના ભવ્ય સમારોહમાં પધારવા હૃદયપૂર્વકનું નિમંત્રણ પાઠવે છે. "
                        f"આપની આદરણીય ઉપસ્થિતિ આ મંગલ અવસરની શોભામાં અભિવૃદ્ધિ કરશે."
                    ),
                    closing_message=f"વિનીત:\n{hosts}\nઆપના સ્નેહ અને આશીર્વાદની અભિલાષા સહ.",
                    full_text=(
                        f"॥ ૐ શ્રી ગણેશાય નમઃ ॥\nસાદર નિમંત્રણ\n\n{greeting}\n\n"
                        f"અત્યંત હર્ષ અને ગૌરવ સાથે, {hosts} આપને '{title}'ના ભવ્ય સમારોહમાં પધારવા હૃદયપૂર્વકનું નિમંત્રણ પાઠવે છે. "
                        f"આપની આદરણીય ઉપસ્થિતિ આ મંગલ અવસરની શોભામાં અભિવૃદ્ધિ કરશે.\n\n"
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
                        f"સુંદર યાદો અને ખુશીઓની ઉજવણી જ્યારે આપ સહુ સાથે હોય ત્યારે જ સાચી બને છે! "
                        f"{hosts} આપને '{title}'ની રોમાંચક ઉજવણીમાં સામેલ થવા દિલથી આવકારે છે. ચાલો સાથે મળીને આ સાંજને અવિસ્મરણીય બનાવીએ!"
                    ),
                    closing_message=f"સ્નેહપૂર્વક,\n{hosts}\nપધારશો જરૂર!",
                    full_text=(
                        f"{greeting}\n\n"
                        f"સુંદર યાદો અને ખુશીઓની ઉજવણી જ્યારે આપ સહુ સાથે હોય ત્યારે જ સાચી બને છે! "
                        f"{hosts} આપને '{title}'ની રોમાંચક ઉજવણીમાં સામેલ થવા દિલથી આવકારે છે. ચાલો સાથે મળીને આ સાંજને અવિસ્મરણીય બનાવીએ!\n\n"
                        f"{details_str}\n\n"
                        f"સ્નેહપૂર્વક,\n{hosts}\nપધારશો જરૂર!"
                    ),
                ),
            )
            return [var1, var2, var3]

        else:
            # English
            details_str = f"Date: {date} | Time: {time}\nVenue: {venue}, {loc}{notes}"
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
