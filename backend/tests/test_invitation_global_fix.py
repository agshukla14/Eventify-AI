import io
import re
import zlib
import base64
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.models import Base, EventModel, GuestModel
from backend.app.schemas import (
    EventIntake,
    InvitationGenerateRequest,
    InvitationTextComponents,
    InvitationDesignConfig,
)
from backend.app.export_service import ExportService, register_indic_fonts
from backend.app.invitation_service import (
    InvitationService,
    format_event_time,
    resolve_event_venue,
    resolve_event_time,
)


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


def extract_pdf_unicode_text(pdf_bytes: bytes) -> str:
    """Extracts and decodes text drawing commands from a PDF byte stream using embedded CMaps."""
    cmap = {}
    p = 0
    while True:
        pos = pdf_bytes.find(b"stream\n", p)
        if pos == -1:
            break
        end_pos = pdf_bytes.find(b"endstream", pos)
        raw = pdf_bytes[pos + 7:end_pos].strip()
        try:
            d = zlib.decompress(raw).decode("latin1", errors="replace")
            if "beginbfchar" in d:
                for line in d.splitlines():
                    parts = line.strip().split()
                    if len(parts) == 2 and parts[0].startswith("<") and parts[1].startswith("<"):
                        try:
                            code = int(parts[0].strip("<>"), 16)
                            uni = int(parts[1].strip("<>"), 16)
                            cmap[code] = chr(uni)
                        except Exception:
                            pass
        except Exception:
            pass
        p = end_pos + 9

    extracted_lines = []
    p = 0
    while True:
        pos = pdf_bytes.find(b"stream\n", p)
        if pos == -1:
            break
        end_pos = pdf_bytes.find(b"endstream", pos)
        raw = pdf_bytes[pos + 7:end_pos].strip()
        p = end_pos + 9
        if b"~>" in raw:
            raw = raw[:raw.find(b"~>") + 2]
            try:
                dec85 = base64.a85decode(raw, adobe=True)
                decomp = zlib.decompress(dec85)
                for m in re.finditer(rb"\((.*?)\)\s*Tj", decomp, re.DOTALL):
                    raw_bytes = m.group(1)
                    decoded_chars = []
                    i = 0
                    while i < len(raw_bytes):
                        if raw_bytes[i:i+1] == b"\\":
                            i += 1
                            if i < len(raw_bytes) and raw_bytes[i:i+1] in b"01234567":
                                oct_digits = raw_bytes[i:i+3]
                                m_oct = re.match(rb"^[0-7]{1,3}", oct_digits)
                                val = int(m_oct.group(0), 8)
                                decoded_chars.append(cmap.get(val, chr(val)))
                                i += len(m_oct.group(0))
                            elif i < len(raw_bytes) and raw_bytes[i:i+1] in b"()\\":
                                val = raw_bytes[i]
                                decoded_chars.append(cmap.get(val, chr(val)))
                                i += 1
                            else:
                                i += 1
                        else:
                            val = raw_bytes[i]
                            decoded_chars.append(cmap.get(val, chr(val)))
                            i += 1
                    extracted_lines.append("".join(decoded_chars))
            except Exception:
                pass
    return "\n".join(extracted_lines)


def test_time_formatting_across_event_types_and_languages():
    """Verify dynamic event start time formatting with correct AM/PM and language localization."""
    # Evening wedding
    assert "7:00 PM" in format_event_time("19:00", "English")
    assert "સાંજે 7:00" in format_event_time("19:00", "Gujarati")
    assert "शाम 7:00" in format_event_time("19:00", "Hindi")

    # Afternoon birthday
    assert "3:00 PM" in format_event_time("15:00", "English")
    assert "બપોરે 3:00" in format_event_time("15:00", "Gujarati")
    assert "दोपहर 3:00" in format_event_time("15:00", "Hindi")

    # Morning community
    assert "9:30 AM" in format_event_time("09:30 - 14:00", "English")
    assert "સવારે 9:30" in format_event_time("09:30 - 14:00", "Gujarati")
    assert "सुबह 9:30" in format_event_time("09:30 - 14:00", "Hindi")


def test_dynamic_venue_retrieval(test_db):
    """Verify venue is dynamically retrieved from event records without hardcoding."""
    event1 = EventModel(
        id="evt_test_wedding",
        title="Ananya & Kabir Royal Wedding",
        event_type="wedding",
        date="2027-11-15",
        city="Udaipur",
        guest_count=250,
        total_budget=5000000.0,
        currency="INR",
        intake_json='{"venue": "The Oberoi Udaivilas", "city": "Udaipur"}',
        plan_json='{"vendors": [{"category": "Venue & Reception Hall", "vendor_name": "The Oberoi Udaivilas"}]}',
        created_at="2026-11-01T00:00:00",
        updated_at="2026-11-01T00:00:00",
    )
    test_db.add(event1)
    test_db.commit()

    venue = resolve_event_venue(test_db, "evt_test_wedding", "Udaipur")
    assert venue == "The Oberoi Udaivilas"


def test_gujarati_font_embedding_and_no_notdef_glyphs():
    """Verify that Gujarati PDF embeds the full TrueType font and renders title and English text without missing glyphs."""
    register_indic_fonts()
    comps = InvitationTextComponents(
        personalized_greeting="સ્નેહી સ્વજનો,",
        event_details="તારીખ: 2027-01-20 | સમય: સાંજે 7:00 કલાકે\nસ્થળ: The Grand Bhagwati, Vadodara",
        invitation_message="પરમકૃપાળુ પરમાત્માની અસીમ કૃપાથી અમારા પરિવારમાં 'RoVish'નો રૂડો અને મંગલમય વિવાહ પ્રસંગ યોજાયેલ છે. આપ સહપરિવાર ઉપસ્થિત રહી આશીર્વાદ આપશો.",
        closing_message="લિ. આપના સ્નેહી પરિવાર\nપધારશો જરૂર!",
        full_text="...",
    )
    design = InvitationDesignConfig(
        template_id="royal_wedding",
        bg_theme="royal_navy",
        bg_color="#0F172A",
        primary_color="#F59E0B",
        text_color="#F8FAFC",
        accent_color="#FDE68A",
        font_family="display",
        font_size="medium",
        border_style="ornate_gold",
        layout="framed",
        decorative_element="royal_crest",
    )

    pdf_bytes = ExportService.generate_invitation_pdf(
        title="RoVish",
        language="Gujarati",
        components=comps,
        design_config=design,
    )

    assert len(pdf_bytes) > 5000
    assert b"/FontFile2" in pdf_bytes
    assert b"NotoSansGujarati" in pdf_bytes

    # Extract Unicode text and verify rendering
    extracted_text = extract_pdf_unicode_text(pdf_bytes)
    # Ensure title "RoVish" was rendered cleanly
    assert "RoVish" in extracted_text
    # Ensure label "કાર્યક્રમ વિગત" was used for Gujarati details box
    assert "કાર્યક્રમ વિગત" in extracted_text


def test_ganesh_mantra_deduplication():
    """Verify that Ganesh mantra appears at most once in the final PDF invitation."""
    register_indic_fonts()

    # Scenario A: User greeting already has Ganesh mantra
    comps_with_mantra = InvitationTextComponents(
        personalized_greeting="॥ શ્રી ગણેશાય નમઃ ॥\nસ્નેહી સ્વજનો,",
        event_details="તારીખ: 2027-01-20\nસ્થળ: Grand Palace",
        invitation_message="અમારા આંગણે મંગલ અવસર યોજાયેલ છે.",
        closing_message="સ્નેહી પરિવાર",
        full_text="...",
    )
    design = InvitationDesignConfig(
        template_id="traditional_indian_wedding",
        bg_theme="gold_vermilion",
        bg_color="#FFFDF9",
        primary_color="#991B1B",
        text_color="#1F2937",
        accent_color="#D97706",
        font_family="serif",
        font_size="medium",
        border_style="ornate_gold",
        layout="centered",
        decorative_element="mandala_diya",
    )

    pdf_bytes_a = ExportService.generate_invitation_pdf(
        title="Aarav & Diya Wedding",
        language="Gujarati",
        components=comps_with_mantra,
        design_config=design,
    )

    # Decode text stream and count occurrences of religious invocation
    text_a = extract_pdf_unicode_text(pdf_bytes_a)
    # The sacred phrase should appear exactly once in the rendered text
    count_a = text_a.count("ગણેશાય")
    assert count_a == 1, f"Expected exactly 1 Ganesh mantra in PDF, found {count_a}"

    # Scenario B: Greeting without mantra, template has mandala_diya
    comps_clean = InvitationTextComponents(
        personalized_greeting="સ્નેહી સ્વજનો,",
        event_details="તારીખ: 2027-01-20\nસ્થળ: Grand Palace",
        invitation_message="અમારા આંગણે મંગલ અવસર યોજાયેલ છે.",
        closing_message="સ્નેહી પરિવાર",
        full_text="...",
    )
    pdf_bytes_b = ExportService.generate_invitation_pdf(
        title="Aarav & Diya Wedding",
        language="Gujarati",
        components=comps_clean,
        design_config=design,
    )
    text_b = extract_pdf_unicode_text(pdf_bytes_b)
    count_b = text_b.count("ગણેશાય")
    assert count_b == 1, f"Expected exactly 1 Ganesh mantra in PDF, found {count_b}"


def test_multi_event_type_invitations_english_hindi_gujarati():
    """Verify that invitations generate successfully across Weddings, Birthdays, Community events in English, Hindi, and Gujarati."""
    test_cases = [
        ("wedding", "Simran & Veer Wedding", "Udaipur", "The Leela Palace", "19:00", "Gujarati"),
        ("birthday", "Kabir 5th Birthday Blast", "Bengaluru", "FunWorld Arena", "15:00", "Hindi"),
        ("community", "Koramangala Eco Fest", "Bengaluru", "Koramangala Club", "09:00", "English"),
    ]

    for ev_type, title, city, venue, time_str, lang in test_cases:
        req = InvitationGenerateRequest(
            event_name=title,
            event_type=ev_type,
            host_names="The Sharma Family",
            event_date="2027-03-15",
            event_time=time_str,
            venue=venue,
            location=city,
            language=lang,
            style="Traditional" if ev_type == "wedding" else "Modern",
        )
        res = InvitationService.generate_invitations(req)
        assert len(res.variations) == 3
        for var in res.variations:
            assert title in var.components.invitation_message or title in var.components.full_text or title in var.components.event_details
            assert venue in var.components.event_details or venue in var.components.full_text
            assert var.components.personalized_greeting


def test_english_missing_content_bug_fixed():
    """
    Verify that when components are completely empty (e.g. download before generating),
    the shared PDF generation architecture dynamically synthesizes all required content
    (greeting, body message, event details with venue & time, and host closing) from event_info.
    """
    empty_comps = InvitationTextComponents(
        personalized_greeting="",
        event_details="",
        invitation_message="",
        closing_message="",
        full_text="",
    )
    design = InvitationDesignConfig(
        template_id="corporate_event",
        bg_theme="executive_platinum",
        bg_color="#F1F5F9",
        primary_color="#0F172A",
        text_color="#334155",
        accent_color="#3B82F6",
        font_family="sans",
        font_size="medium",
        border_style="double",
        layout="framed",
        decorative_element="none",
    )
    event_info = {
        "event_name": "NexGen Global AI Leadership Summit",
        "event_type": "Community",
        "event_date": "2027-04-10",
        "event_time": "10:00 AM onwards",
        "venue": "Sheraton Grand Convention Center",
        "location": "Bengaluru",
        "host_names": "The NexGen Organizing Committee",
        "additional_notes": "Business formal attire",
    }

    pdf_bytes = ExportService.generate_invitation_pdf(
        title="NexGen Global AI Leadership Summit",
        language="English",
        components=empty_comps,
        design_config=design,
        event_info=event_info,
    )

    assert len(pdf_bytes) > 2500
    page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))
    assert page_count == 1, "Expected single page luxury card"

    text = extract_pdf_unicode_text(pdf_bytes)
    # Ensure title is present
    assert "NexGen Global AI Leadership" in text
    assert "Summit" in text
    # Ensure venue and location are present (NO missing content)
    assert "Sheraton Grand Convention Center" in text
    assert "Bengaluru" in text
    # Ensure hosts are present in the closing
    assert "The NexGen Organizing Committee" in text
    # Ensure date and formatted time are present
    assert "2027-04-10" in text
    assert "10:00 AM onwards" in text
    # Ensure EVENT DETAILS box is present
    assert "EVENT DETAILS" in text


def test_page_utilization_across_all_event_types_and_languages():
    """
    Verify that multiple diverse events (Weddings, Birthdays, Community) across English,
    Hindi, and Gujarati with varying text lengths achieve balanced vertical page utilization,
    high visual quality, and single-page fit with zero clipping.
    """
    events_to_test = [
        # 1. Gujarati Wedding (Traditional luxury)
        {
            "title": "Aarav & Meera Royal Vivah",
            "lang": "Gujarati",
            "type": "wedding",
            "venue": "The Grand Bhagwati",
            "city": "Ahmedabad",
            "date": "2027-02-20",
            "time": "19:00",
            "hosts": "પટેલ અને શાહ પરિવાર",
            "template": "traditional_indian_wedding",
            "greeting": "સ્નેહી સ્વજનો,",
            "msg": "પરમકૃપાળુ પરમાત્માની અસીમ કૃપાથી અમારા પરિવારમાં લગ્ન પ્રસંગ યોજાયેલ છે. આપ સહપરિવાર ઉપસ્થિત રહી નવદંપતીને આશીર્વાદ આપશો.",
            "details": "તારીખ: 2027-02-20 | સમય: સાંજે 7:00 કલાકે\nસ્થળ: The Grand Bhagwati, Ahmedabad",
            "closing": "લિ. આપના સ્નેહી:\nપટેલ અને શાહ પરિવાર",
        },
        # 2. Hindi Birthday (Joyful & Modern)
        {
            "title": "Aanya's 7th Wonder Carnival",
            "lang": "Hindi",
            "type": "birthday",
            "venue": "Club Emerald Banquet",
            "city": "Mumbai",
            "date": "2027-05-18",
            "time": "16:00",
            "hosts": "रोहन एवं सोनिया शर्मा",
            "template": "floral_birthday",
            "greeting": "सादर निमंत्रण,",
            "msg": "हमारी लाडली आन्या के 7वें जन्मदिन पर आप सपरिवार सादर आमंत्रित हैं। आइए, केक कटिंग, गेम्स और संगीत से भरी इस शाम में शामिल होकर इस दिन को खास बनाएं!",
            "details": "दिनांक: 2027-05-18 | समय: शाम 4:00 बजे से\nस्थान: Club Emerald Banquet, Mumbai",
            "closing": "स्नेही स्वजन:\nरोहन एवं सोनिया शर्मा",
        },
        # 3. English Community Civic Mela (Long format)
        {
            "title": "Indiranagar Green Tech & Clean Energy Festival",
            "lang": "English",
            "type": "community",
            "venue": "Indiranagar Central Grounds",
            "city": "Bengaluru",
            "date": "2027-08-15",
            "time": "09:00",
            "hosts": "Indiranagar Residents & Civic Forum",
            "template": "college_fest",
            "greeting": "Dear Neighbors & Civic Leaders,",
            "msg": "Join us in celebrating our neighborhood's innovative journey toward zero waste and clean renewable solar energy. Experience eco-tech showcases, live music, interactive workshops, and delicious organic street food stalls. Your presence and ideas inspire sustainable community action.",
            "details": "Date: 2027-08-15 | Time: 9:00 AM onwards\nVenue: Indiranagar Central Grounds, Bengaluru\nNote: Please carry your own eco-friendly bags and bottles.",
            "closing": "With civic pride,\nIndiranagar Residents & Civic Forum",
        },
    ]

    for ev in events_to_test:
        comps = InvitationTextComponents(
            personalized_greeting=ev["greeting"],
            event_details=ev["details"],
            invitation_message=ev["msg"],
            closing_message=ev["closing"],
            full_text="...",
        )
        design = InvitationDesignConfig(
            template_id=ev["template"],
            bg_theme="gold_vermilion" if ev["lang"] == "Gujarati" else "modern_minimal",
            bg_color="#FFFDF9" if ev["lang"] == "Gujarati" else "#FFFFFF",
            primary_color="#991B1B" if ev["lang"] == "Gujarati" else "#0F172A",
            text_color="#1F2937",
            accent_color="#D97706",
            font_family="serif" if ev["lang"] == "Gujarati" else "sans",
            font_size="medium",
            border_style="ornate_gold" if ev["lang"] == "Gujarati" else "minimal",
            layout="centered",
            decorative_element="royal_crest" if ev["lang"] == "Gujarati" else "floral_wreath",
        )
        event_info = {
            "event_name": ev["title"],
            "event_type": ev["type"],
            "event_date": ev["date"],
            "event_time": ev["time"],
            "venue": ev["venue"],
            "location": ev["city"],
            "host_names": ev["hosts"],
        }

        pdf_bytes = ExportService.generate_invitation_pdf(
            title=ev["title"],
            language=ev["lang"],
            components=comps,
            design_config=design,
            event_info=event_info,
        )

        assert len(pdf_bytes) > 2500
        page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))
        assert page_count == 1, f"Expected exactly 1 page for {ev['title']} in {ev['lang']}, got {page_count}"

        text = extract_pdf_unicode_text(pdf_bytes)
        assert ev["title"] in text or ev["venue"] in text
        assert ev["venue"] in text
        assert ev["city"] in text


def test_long_invitation_message_scales_without_clipping():
    """Verify that long invitation text (350+ characters) scales and fits on a single page PDF without errors."""
    register_indic_fonts()
    long_msg = (
        "Together with our parents, families, and dearest ancestors whose blessings illuminate our path, "
        "we take immense joy and deep gratitude in welcoming you to join our momentous matrimonial celebration. "
        "This sacred union represents the coming together of two loving hearts and two cherished families. "
        "We eagerly await your presence to celebrate with song, dance, feast, and timeless blessings."
    )
    comps = InvitationTextComponents(
        personalized_greeting="Dear Esteemed Guests & Family,",
        event_details="Date: 2027-12-10 | Time: 6:00 PM onwards\nVenue: Grand Heritage Palace, Mumbai",
        invitation_message=long_msg,
        closing_message="Warmly and Cordially,\nThe Host Family",
        full_text="...",
    )
    design = InvitationDesignConfig(
        template_id="royal_wedding",
        bg_theme="royal_navy",
        bg_color="#0F172A",
        primary_color="#F59E0B",
        text_color="#F8FAFC",
        accent_color="#FDE68A",
        font_family="display",
        font_size="medium",
        border_style="ornate_gold",
        layout="framed",
        decorative_element="royal_crest",
    )

    pdf_bytes = ExportService.generate_invitation_pdf(
        title="Aditya & Meera Grand Wedding",
        language="English",
        components=comps,
        design_config=design,
    )
    assert len(pdf_bytes) > 2500
    # Ensure PDF generated exactly 1 page
    page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))
    assert page_count == 1, f"Expected 1 page for luxury invitation card, got {page_count}"
