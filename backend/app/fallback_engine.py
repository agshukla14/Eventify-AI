from typing import Dict, Any, Optional
from .schemas import EventIntake, FullEventPlan
from .repair_engine import DeterministicRepairEngine


class FallbackTemplateEngine:
    """
    Guarantees deterministic, production-quality, personalized event plan generation
    when Gemini API is offline, unconfigured, or fails schema validation.
    """

    @classmethod
    def generate_plan(cls, intake: EventIntake, event_id: Optional[str] = None) -> FullEventPlan:
        # Pass empty raw structures into the DeterministicRepairEngine,
        # which activates its tailored domain templates for Wedding, Birthday, or Community.
        return DeterministicRepairEngine.repair_full_plan(
            raw_plan=None,
            intake=intake,
            existing_event_id=event_id,
        )
