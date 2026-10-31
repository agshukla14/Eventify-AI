import json
import re
import uuid
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from .models import ChatMessageModel
from .schemas import FullEventPlan, ChatResponse, ChatMessage, TimelineTask, PersonalizedIdeaItem
from .repair_engine import DeterministicRepairEngine, parse_date_safe
from .plan_service import PlanService
from .config import GEMINI_API_KEY


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.plan_service = PlanService(db)

    def process_message(self, event_id: str, user_text: str) -> ChatResponse:
        plan = self.plan_service.get_plan(event_id)
        if not plan:
            return ChatResponse(
                reply="Event plan not found. Please select or create an event first.",
                tools_executed=[],
            )

        # Save user message to DB
        user_msg_id = str(uuid.uuid4())[:8]
        now_str = datetime.now().isoformat()
        user_record = ChatMessageModel(
            id=user_msg_id,
            event_id=event_id,
            role="user",
            content=user_text,
            timestamp=now_str,
        )
        self.db.add(user_record)
        self.db.commit()

        # Execute tools if the user requested a change
        tools_executed, modified_plan, execution_notes = self._execute_chat_tools(plan, user_text)

        reply_content = ""
        if tools_executed:
            # Plan was modified
            repaired_plan = self.plan_service.update_plan(event_id, modified_plan)
            reply_content = f"Plan updated successfully! " + " ".join(execution_notes)
            final_plan = repaired_plan
        else:
            # Informational / grounded Q&A
            final_plan = plan
            reply_content = self._answer_grounded_question(plan, user_text)

        # Save assistant message to DB
        asst_msg_id = str(uuid.uuid4())[:8]
        asst_record = ChatMessageModel(
            id=asst_msg_id,
            event_id=event_id,
            role="assistant",
            content=reply_content,
            tool_calls_json=json.dumps(tools_executed) if tools_executed else None,
            timestamp=datetime.now().isoformat(),
        )
        self.db.add(asst_record)
        self.db.commit()

        return ChatResponse(
            reply=reply_content,
            updated_plan=final_plan if tools_executed else None,
            tools_executed=tools_executed,
        )

    def _execute_chat_tools(
        self,
        plan: FullEventPlan,
        text: str
    ) -> Tuple[List[Dict[str, Any]], FullEventPlan, List[str]]:
        tools_run: List[Dict[str, Any]] = []
        notes: List[str] = []
        lower = text.lower()

        # 1. Budget Move: "move 5000 from Decor to Catering", "move 5% from venue to decor", "shift 2000 from decor to catering"
        move_match = re.search(
            r"(?:move|shift|transfer|reallocate)\s+(?:(\d+(?:\.\d+)?)\s*(%|inr|usd|eur|rupees)?\s+)?from\s+([a-z\s&/]+?)\s+to\s+([a-z\s&/]+)",
            lower
        )
        if move_match:
            amt_or_pct_str = move_match.group(1)
            unit = move_match.group(2) or ""
            source_cat = move_match.group(3).strip()
            target_cat = move_match.group(4).strip()

            val = float(amt_or_pct_str) if amt_or_pct_str else 5.0
            is_pct = "%" in unit or val <= 10.0

            # Locate categories in plan
            src_item = None
            tgt_item = None
            for item in plan.budget.items:
                if source_cat in item.category.lower():
                    src_item = item
                if target_cat in item.category.lower():
                    tgt_item = item

            if src_item and tgt_item and src_item.id != tgt_item.id:
                if is_pct:
                    shift_pct = min(src_item.percentage * 0.8, val)
                    src_item.weight = max(0.1, src_item.weight - shift_pct)
                    tgt_item.weight = tgt_item.weight + shift_pct
                else:
                    shift_amt = min(src_item.allocated_amount * 0.8, val)
                    pct_val = (shift_amt / plan.budget.total_budget * 100) if plan.budget.total_budget > 0 else 5.0
                    src_item.weight = max(0.1, src_item.weight - pct_val)
                    tgt_item.weight = tgt_item.weight + pct_val

                tools_run.append({
                    "tool": "move_budget",
                    "from_category": src_item.category,
                    "to_category": tgt_item.category,
                    "value": val,
                    "unit": "%" if is_pct else "amount",
                })
                notes.append(
                    f"Reallocated funds from '{src_item.category}' to '{tgt_item.category}'. The budget was deterministically balanced."
                )

        # 2. Date change: "change date to 2027-02-15", "move date to 2026-12-25", "postpone to 2027-04-10"
        date_match = re.search(r"(?:change|move|shift|postpone|set)\s+(?:event\s+)?date\s+to\s+(\d{4}-\d{2}-\d{2})", lower)
        if date_match:
            new_date = date_match.group(1)
            plan.intake.date = new_date
            tools_run.append({"tool": "adjust_event_date", "new_date": new_date})
            notes.append(f"Updated event date to {new_date}. Timeline milestones have been recalculated.")

        # 3. Vendor status update: "mark photography as booked", "set catering status to paid", "booked venue with quote 150000"
        vendor_match = re.search(
            r"(?:mark|set|update)\s+([a-z\s&/]+?)\s+(?:as|status\s+to)?\s*(booked|paid|quoted|not_contacted)",
            lower
        )
        if vendor_match:
            cat_query = vendor_match.group(1).strip()
            new_status = vendor_match.group(2).strip()
            for v in plan.vendors:
                if cat_query in v.category.lower() or cat_query in (v.vendor_name or "").lower():
                    v.status = new_status
                    tools_run.append({
                        "tool": "update_vendor_status",
                        "category": v.category,
                        "status": new_status,
                    })
                    notes.append(f"Updated vendor '{v.category}' status to '{new_status}'.")
                    break

        # 4. Vendor quote update: "vendor quote for catering is 80000", "update catering quote to 75000"
        quote_match = re.search(
            r"(?:update|set|vendor)\s+(?:quote\s+for\s+)?([a-z\s&/]+?)\s+(?:quote\s+(?:to|is)\s*|quote\s*=\s*)(\d+(?:\.\d+)?)",
            lower
        )
        if quote_match:
            v_cat = quote_match.group(1).strip()
            q_val = float(quote_match.group(2))
            for v in plan.vendors:
                if v_cat in v.category.lower():
                    v.quote_amount = q_val
                    tools_run.append({
                        "tool": "update_vendor_quote",
                        "category": v.category,
                        "quote_amount": q_val,
                    })
                    notes.append(f"Updated quote for '{v.category}' to {q_val} {plan.intake.currency}.")
                    break

        # 5. Task status update: "complete task Send Invitations", "finish task Finalize Venue", "mark task Catering as completed"
        task_match_direct = re.search(r"^(?:complete|finish)\s+(?:task\s+)?['\"]?([a-z0-9\s&/-]+?)['\"]?$", lower)
        task_match_mark = re.search(
            r"(?:complete|mark|finish|set)\s+(?:task\s+)?['\"]?([a-z0-9\s&/-]+?)['\"]?\s+(?:as|to)\s+(completed|done|in_progress|pending)",
            lower
        )
        task_match_trailing = re.search(
            r"(?:complete|mark|finish)\s+(?:task\s+)?['\"]?([a-z0-9\s&/-]+?)['\"]?\s+(completed|done|in_progress|pending)",
            lower
        )

        target_status = None
        query = None

        if task_match_direct:
            query = task_match_direct.group(1).strip()
            target_status = "completed"
        elif task_match_mark:
            query = task_match_mark.group(1).strip()
            raw_s = task_match_mark.group(2).strip()
            target_status = "completed" if raw_s in ["completed", "done"] else raw_s
        elif task_match_trailing:
            query = task_match_trailing.group(1).strip()
            raw_s = task_match_trailing.group(2).strip()
            target_status = "completed" if raw_s in ["completed", "done"] else raw_s

        if query and target_status:
            for t in plan.timeline.milestones:
                if query in t.title.lower() or query == t.id.lower() or any(w in t.title.lower() for w in query.split() if len(w) > 3):
                    t.status = target_status
                    tools_run.append({
                        "tool": "update_task_status",
                        "task_id": t.id,
                        "task_title": t.title,
                        "status": target_status,
                    })
                    notes.append(f"Marked task '{t.title}' as '{target_status}'.")
                    break

        # 6. Add Custom Task: "add task Book magician on 2026-11-20"
        add_task_match = re.search(r"add\s+task\s+['\"]?(.+?)['\"]?\s+on\s+(\d{4}-\d{2}-\d{2})", lower)
        if add_task_match:
            t_title = add_task_match.group(1).strip().title()
            t_date = add_task_match.group(2).strip()
            new_task = TimelineTask(
                id=str(uuid.uuid4())[:8],
                milestone_phase="Custom Phase",
                title=t_title,
                description="Custom task added via assistant",
                due_date=t_date,
                owner="user",
                priority="medium",
                status="pending",
                is_high_risk=False,
                is_past_due=parse_date_safe(t_date) < date.today(),
            )
            plan.timeline.milestones.append(new_task)
            plan.timeline.milestones.sort(key=lambda x: x.due_date)
            tools_run.append({
                "tool": "add_custom_task",
                "title": t_title,
                "due_date": t_date,
            })
            notes.append(f"Added new task '{t_title}' with due date {t_date}.")

        # 7. Add Personalized Idea: "add theme idea Royal Mughal Palace"
        add_idea_match = re.search(r"add\s+(theme|decor|food|activity|entertainment|gift)\s+idea\s+['\"]?(.+?)['\"]?$", lower)
        if add_idea_match:
            cat_type = add_idea_match.group(1)
            idea_title = add_idea_match.group(2).strip().title()
            new_idea = PersonalizedIdeaItem(
                id=str(uuid.uuid4())[:8],
                title=idea_title,
                description=f"Curated custom {cat_type} concept requested by host.",
                rationale=f"Enhances the event theme and guest experience in {plan.intake.city}.",
                budget_friendly_swap=f"Source materials locally in {plan.intake.city} or collaborate with local artisans.",
                tags=["Custom", cat_type.title()],
            )
            if cat_type == "theme":
                plan.ideas.themes.append(new_idea)
            elif cat_type == "decor":
                plan.ideas.decor.append(new_idea)
            elif cat_type == "food":
                plan.ideas.food_menu.append(new_idea)
            elif cat_type == "activity":
                plan.ideas.activities.append(new_idea)
            elif cat_type == "entertainment":
                plan.ideas.entertainment.append(new_idea)
            else:
                plan.ideas.return_gifts.append(new_idea)

            tools_run.append({
                "tool": "add_personalized_idea",
                "category": cat_type,
                "title": idea_title,
            })
            notes.append(f"Added custom {cat_type} idea: '{idea_title}'.")

        return tools_run, plan, notes

    def _answer_grounded_question(self, plan: FullEventPlan, text: str) -> str:
        """
        Answers questions grounded directly in the event plan data.
        """
        lower = text.lower()
        today = date.today()
        ev_date = parse_date_safe(plan.intake.date)
        days_left = (ev_date - today).days

        # Days left / date
        if any(w in lower for w in ["days left", "how many days", "when is", "date of the event"]):
            return (
                f"Your event '{plan.intake.title}' is scheduled for {plan.intake.date} in {plan.intake.city}. "
                f"There are {days_left} days remaining until celebration day!"
            )

        # Budget questions
        if "budget" in lower or "spend" in lower or "cost" in lower or "allocation" in lower:
            # Check if specific category mentioned
            for item in plan.budget.items:
                if item.category.lower() in lower:
                    return (
                        f"For '{item.category}', your allocated budget is {item.allocated_amount:,.2f} {plan.intake.currency} "
                        f"({item.percentage:.1f}% of total). Actual spend so far: {item.actual_spent:,.2f} {plan.intake.currency}. "
                        f"{'Note: ' + item.notes if item.notes else ''}"
                    )
            return (
                f"Your total budget is {plan.budget.total_budget:,.2f} {plan.budget.currency}. "
                f"Allocated: {plan.budget.total_allocated:,.2f} {plan.budget.currency} across {len(plan.budget.items)} categories, "
                f"including a {plan.budget.contingency_percentage:.1f}% contingency reserve. "
                f"Total actual spent so far: {plan.budget.total_actual_spent:,.2f} {plan.budget.currency}."
            )

        # Contingency questions
        if "contingency" in lower:
            con_item = next((i for i in plan.budget.items if i.is_contingency), None)
            amt = con_item.allocated_amount if con_item else 0.0
            return (
                f"You have a {plan.budget.contingency_percentage:.1f}% contingency reserve set aside, "
                f"amounting to {amt:,.2f} {plan.budget.currency} to safeguard against unexpected expenses."
            )

        # Vendor questions
        if "vendor" in lower or "booked" in lower or "quote" in lower:
            booked_v = [v for v in plan.vendors if v.status in ["booked", "paid"]]
            pending_v = [v for v in plan.vendors if v.status not in ["booked", "paid"]]
            return (
                f"You have {len(plan.vendors)} vendor categories in total. "
                f"{len(booked_v)} are currently booked/paid ({', '.join(v.category for v in booked_v) or 'none yet'}). "
                f"{len(pending_v)} categories are pending quotes or booking ({', '.join(v.category for v in pending_v)})."
            )

        # Timeline / high risk / tasks
        if "timeline" in lower or "task" in lower or "milestone" in lower or "risk" in lower:
            high_risk = [t for t in plan.timeline.milestones if t.is_high_risk]
            past_due = [t for t in plan.timeline.milestones if t.is_past_due]
            pending = [t for t in plan.timeline.milestones if t.status == "pending"]
            completed = [t for t in plan.timeline.milestones if t.status == "completed"]
            return (
                f"Timeline status: {len(completed)}/{len(plan.timeline.milestones)} tasks completed. "
                f"High-risk items flagged: {len(high_risk)} ({', '.join(t.title for t in high_risk[:3])}). "
                f"Past due tasks: {len(past_due)}. "
                f"Next upcoming task: '{pending[0].title}' due on {pending[0].due_date} if any."
            )

        # Ideas / food / menu / themes
        if "food" in lower or "menu" in lower or "diet" in lower or "catering" in lower:
            food_titles = [f.title for f in plan.ideas.food_menu]
            return (
                f"Curated menu ideas adhering to dietary preferences ({', '.join(plan.intake.dietary_preferences) or 'Standard'}): "
                f"{'; '.join(food_titles)}. Every item includes a budget-friendly swap option!"
            )

        if "theme" in lower or "decor" in lower:
            theme_titles = [t.title for t in plan.ideas.themes]
            return (
                f"Personalized themes for {plan.intake.title} in {plan.intake.city}: {'; '.join(theme_titles)}. "
                f"Designed to capture the {plan.intake.theme_style or 'celebration'} vibe."
            )

        # Default summary response
        return (
            f"Here is your plan snapshot for '{plan.intake.title}' ({plan.intake.event_type.title()}): "
            f"{days_left} days left | Budget: {plan.budget.total_budget:,.2f} {plan.budget.currency} "
            f"| Tasks: {len(plan.timeline.milestones)} ({plan.timeline.high_risk_count} high-risk) "
            f"| Vendors: {len(plan.vendors)}. How can I assist you with adjusting or expanding your plan?"
        )

    def get_history(self, event_id: str) -> List[ChatMessage]:
        records = (
            self.db.query(ChatMessageModel)
            .filter(ChatMessageModel.event_id == event_id)
            .order_by(ChatMessageModel.timestamp.asc())
            .all()
        )
        history: List[ChatMessage] = []
        for r in records:
            tools = json.loads(r.tool_calls_json) if r.tool_calls_json else None
            history.append(
                ChatMessage(
                    id=r.id,
                    role=r.role,
                    content=r.content,
                    timestamp=r.timestamp,
                    tool_calls_executed=tools,
                )
            )
        return history
