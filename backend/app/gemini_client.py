import json
import logging
import re
from typing import Dict, Any, Optional, Tuple
from pydantic import ValidationError

from .config import GEMINI_API_KEY
from .schemas import EventIntake, FullEventPlan
from .repair_engine import DeterministicRepairEngine
from .fallback_engine import FallbackTemplateEngine

logger = logging.getLogger(__name__)

# Prompt injection sanitizer
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"you\s+are\s+now\s+a",
    r"system\s*:",
    r"<\s*system\s*>",
    r"<\s*/\s*system\s*>",
    r"assistant\s*:",
    r"human\s*:",
    r"developer\s*mode",
]


def sanitize_user_input(text: Optional[str]) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    for pattern in INJECTION_PATTERNS:
        cleaned = re.sub(pattern, "[sanitized_input]", cleaned, flags=re.IGNORECASE)
    # Remove excessive backticks or prompt delimiter tricks
    cleaned = cleaned.replace("```", "'''")
    return cleaned[:500]  # clamp length to prevent overflow


PLANNING_SYSTEM_PROMPT = """You are an elite, production-grade Celebration & Event Planner Assistant.
Generate a comprehensive, creative, culturally-attuned, and logistically sound event plan in valid JSON format.

RULES:
1. Return ONLY a single JSON object. No markdown fences, no explanatory text outside the JSON.
2. All arithmetic for budgets is deterministic: you provide categories and relative weight recommendations; do NOT worry about pennies because our post-processor normalizes them. Include 'Contingency' with ~8% weight.
3. Include mandatory vendor categories for the event type with at least 4 detailed checklist items each (contract, deposit date, questions, final payment).
4. In 'ideas', reference the user's specific city, cultural preferences, theme, and guest count. Adhere strictly to dietary preferences (e.g., if vegetarian, no meat or poultry whatsoever; if kids, no alcohol or adult themes). Provide a realistic 'budget_friendly_swap' for EVERY idea.
5. Timeline milestones must be chronological leading up to the event date, plus a complete day-of run-of-show schedule.

JSON Schema format:
{
  "budget": {
    "contingency_percentage": 8.0,
    "items": [
      {"category": "Venue & Lodging", "weight": 25.0, "notes": "..."},
      {"category": "Catering & Bar", "weight": 25.0, "notes": "..."},
      {"category": "Contingency", "weight": 8.0, "notes": "..."}
    ]
  },
  "timeline": {
    "milestones": [
      {
        "milestone_phase": "6 Months Before",
        "title": "...",
        "description": "...",
        "due_date": "YYYY-MM-DD",
        "owner": "user",
        "priority": "high",
        "is_high_risk": false
      }
    ],
    "run_of_show": [
      {
        "time_slot": "09:00 - 10:00",
        "activity": "...",
        "lead_person": "...",
        "location": "...",
        "notes": "..."
      }
    ]
  },
  "vendors": [
    {
      "category": "Venue & Reception Hall",
      "vendor_name": "...",
      "contact_info": "...",
      "quote_amount": 50000.0,
      "status": "not_contacted",
      "backup_vendor": "...",
      "checklist": [
        {"task_text": "...", "item_type": "document"},
        {"task_text": "...", "item_type": "deposit_date"},
        {"task_text": "...", "item_type": "question"},
        {"task_text": "...", "item_type": "final_payment_date"}
      ]
    }
  ],
  "ideas": {
    "themes": [{"title": "...", "description": "...", "rationale": "...", "budget_friendly_swap": "...", "tags": ["..."]}],
    "decor": [...],
    "food_menu": [...],
    "activities": [...],
    "entertainment": [...],
    "return_gifts": [...]
  }
}
"""


class GeminiClient:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai client: {e}")
                self.client = None

    def is_available(self) -> bool:
        return bool(self.client and self.api_key)

    def generate_event_plan(
        self,
        intake: EventIntake,
        existing_event_id: Optional[str] = None
    ) -> FullEventPlan:
        """
        Generates plan via Gemini with structured JSON output,
        retrying up to 3 times with error feedback on schema failures,
        and applying the deterministic post-processing repair layer.
        Falls back seamlessly if LLM fails or is unavailable.
        """
        # If client not available, immediately use fallback template engine
        if not self.is_available():
            logger.info("Gemini API key not configured or client unavailable. Using FallbackTemplateEngine.")
            return FallbackTemplateEngine.generate_plan(intake, existing_event_id)

        # Build user prompt with sanitized fields
        user_prompt = f"""
Event Planning Details:
- Event Type: {intake.event_type}
- Event Title: {sanitize_user_input(intake.title)}
- Event Date: {intake.date}
- City: {sanitize_user_input(intake.city)}
- Guest Count: {intake.guest_count}
- Total Budget: {intake.total_budget} {intake.currency}
- Theme / Aesthetic: {sanitize_user_input(intake.theme_style) or 'Not specified'}
- Cultural Customs: {sanitize_user_input(intake.cultural_preferences) or 'Standard celebratory customs'}
- Dietary Preferences: {', '.join([sanitize_user_input(d) for d in intake.dietary_preferences]) or 'No strict restrictions'}
- Must-Haves: {', '.join([sanitize_user_input(m) for m in intake.must_haves]) or 'None specified'}
- Age Group / Occasion Info: {sanitize_user_input(intake.age_group_details) or 'All ages'}
"""

        from google.genai import types

        max_retries = 3
        current_error_feedback = ""
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                full_contents = [PLANNING_SYSTEM_PROMPT, user_prompt]
                if current_error_feedback:
                    full_contents.append(
                        f"\nPREVIOUS ATTEMPT SCHEMA VALIDATION ERROR:\n{current_error_feedback}\nPlease fix the JSON structure strictly so it validates against the required schema."
                    )

                logger.info(f"Invoking Gemini (attempt {attempt}/{max_retries})...")
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=full_contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.4,
                    ),
                )

                raw_text = response.text.strip()
                # Clean any markdown block wrap if returned
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```(json)?\n", "", raw_text)
                    raw_text = re.sub(r"\n```$", "", raw_text)

                parsed_json = json.loads(raw_text)

                # Validate & repair deterministically
                repaired_plan = DeterministicRepairEngine.repair_full_plan(
                    raw_plan=parsed_json,
                    intake=intake,
                    existing_event_id=existing_event_id,
                )
                logger.info(f"Gemini plan generated and repaired successfully on attempt {attempt}.")
                return repaired_plan

            except json.JSONDecodeError as jde:
                logger.warning(f"JSON decode failed on attempt {attempt}: {jde}")
                current_error_feedback = f"JSONDecodeError: Your response was not valid JSON: {str(jde)}"
                last_exception = jde
            except ValidationError as ve:
                logger.warning(f"Pydantic validation failed on attempt {attempt}: {ve}")
                current_error_feedback = f"Pydantic ValidationError: {str(ve)}"
                last_exception = ve
            except Exception as e:
                logger.error(f"Gemini API invocation error on attempt {attempt}: {e}")
                last_exception = e
                break  # for network / auth errors, do not loop endlessly

        logger.warning(f"Gemini retries exhausted ({last_exception}). Falling back to deterministic template engine.")
        return FallbackTemplateEngine.generate_plan(intake, existing_event_id)
