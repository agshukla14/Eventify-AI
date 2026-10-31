import csv
import io
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Set
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from .models import EventModel, GuestModel
from .schemas import (
    GuestCreate,
    GuestUpdate,
    GuestStatusUpdate,
    GuestResponse,
    GuestRSVPSummary,
    CSVImportPreviewRow,
    CSVImportPreviewResponse,
    CSVImportResult,
)

VALID_CATEGORIES = {"Family", "Friends", "Relatives", "Colleagues", "VIP", "Others"}


class GuestService:
    def __init__(self, db: Session):
        self.db = db

    def _normalize_category(self, cat: Optional[str]) -> str:
        if not cat:
            return "Others"
        cleaned = cat.strip().title()
        for valid in VALID_CATEGORIES:
            if valid.lower() == cleaned.lower():
                return valid
        return "Others"

    def create_guest(self, event_id: str, guest_in: GuestCreate) -> GuestResponse:
        event = self.db.query(EventModel).filter(EventModel.id == event_id).first()
        if not event:
            raise ValueError(f"Event '{event_id}' not found")

        name = guest_in.full_name.strip()
        email = guest_in.email.strip().lower() if guest_in.email and guest_in.email.strip() else None
        phone = guest_in.phone.strip() if guest_in.phone and guest_in.phone.strip() else None

        # Check duplicates within the same event
        if email:
            existing_email = (
                self.db.query(GuestModel)
                .filter(GuestModel.event_id == event_id, func.lower(GuestModel.email) == email)
                .first()
            )
            if existing_email:
                raise ValueError(f"A guest with email '{email}' already exists in this event.")

        if phone:
            existing_phone = (
                self.db.query(GuestModel)
                .filter(GuestModel.event_id == event_id, GuestModel.phone == phone)
                .first()
            )
            if existing_phone:
                raise ValueError(f"A guest with phone number '{phone}' already exists in this event.")

        now = datetime.utcnow().isoformat()
        guest = GuestModel(
            id=f"gst_{uuid.uuid4().hex[:12]}",
            event_id=event_id,
            full_name=name,
            email=email,
            phone=phone,
            category=self._normalize_category(guest_in.category),
            plus_ones=max(0, guest_in.plus_ones),
            invitation_status=guest_in.invitation_status or "Not Sent",
            rsvp_status=guest_in.rsvp_status or "Pending",
            special_requirements=guest_in.special_requirements.strip() if guest_in.special_requirements else None,
            notes=guest_in.notes.strip() if guest_in.notes else None,
            created_at=now,
            updated_at=now,
        )

        self.db.add(guest)
        self.db.commit()
        self.db.refresh(guest)

        return self._to_response(guest)

    def get_guest(self, event_id: str, guest_id: str) -> Optional[GuestResponse]:
        guest = (
            self.db.query(GuestModel)
            .filter(GuestModel.event_id == event_id, GuestModel.id == guest_id)
            .first()
        )
        return self._to_response(guest) if guest else None

    def list_guests(
        self,
        event_id: str,
        search: Optional[str] = None,
        category: Optional[str] = None,
        rsvp_status: Optional[str] = None,
        invitation_status: Optional[str] = None,
        sort_by: str = "name_asc",
    ) -> List[GuestResponse]:
        query = self.db.query(GuestModel).filter(GuestModel.event_id == event_id)

        if category and category.lower() != "all":
            query = query.filter(func.lower(GuestModel.category) == category.strip().lower())

        if rsvp_status and rsvp_status.lower() != "all":
            query = query.filter(func.lower(GuestModel.rsvp_status) == rsvp_status.strip().lower())

        if invitation_status and invitation_status.lower() != "all":
            query = query.filter(func.lower(GuestModel.invitation_status) == invitation_status.strip().lower())

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    GuestModel.full_name.ilike(term),
                    GuestModel.email.ilike(term),
                    GuestModel.phone.ilike(term),
                    GuestModel.notes.ilike(term),
                    GuestModel.special_requirements.ilike(term),
                )
            )

        if sort_by == "name_desc":
            query = query.order_by(GuestModel.full_name.desc())
        elif sort_by == "date_desc":
            query = query.order_by(GuestModel.created_at.desc())
        elif sort_by == "category_asc":
            query = query.order_by(GuestModel.category.asc(), GuestModel.full_name.asc())
        else:
            query = query.order_by(GuestModel.full_name.asc())

        guests = query.all()
        return [self._to_response(g) for g in guests]

    def update_guest(
        self, event_id: str, guest_id: str, guest_in: GuestUpdate
    ) -> Optional[GuestResponse]:
        guest = (
            self.db.query(GuestModel)
            .filter(GuestModel.event_id == event_id, GuestModel.id == guest_id)
            .first()
        )
        if not guest:
            return None

        # Check duplicate if email is being updated to a different one
        if guest_in.email is not None:
            new_email = guest_in.email.strip().lower() if guest_in.email.strip() else None
            if new_email and new_email != (guest.email or "").lower():
                dup = (
                    self.db.query(GuestModel)
                    .filter(
                        GuestModel.event_id == event_id,
                        GuestModel.id != guest_id,
                        func.lower(GuestModel.email) == new_email,
                    )
                    .first()
                )
                if dup:
                    raise ValueError(f"Another guest with email '{new_email}' already exists in this event.")
            guest.email = new_email

        # Check duplicate if phone is being updated
        if guest_in.phone is not None:
            new_phone = guest_in.phone.strip() if guest_in.phone.strip() else None
            if new_phone and new_phone != (guest.phone or ""):
                dup = (
                    self.db.query(GuestModel)
                    .filter(
                        GuestModel.event_id == event_id,
                        GuestModel.id != guest_id,
                        GuestModel.phone == new_phone,
                    )
                    .first()
                )
                if dup:
                    raise ValueError(f"Another guest with phone number '{new_phone}' already exists in this event.")
            guest.phone = new_phone

        if guest_in.full_name is not None:
            guest.full_name = guest_in.full_name.strip()
        if guest_in.category is not None:
            guest.category = self._normalize_category(guest_in.category)
        if guest_in.plus_ones is not None:
            guest.plus_ones = max(0, guest_in.plus_ones)
        if guest_in.invitation_status is not None:
            guest.invitation_status = guest_in.invitation_status
        if guest_in.rsvp_status is not None:
            guest.rsvp_status = guest_in.rsvp_status
        if guest_in.special_requirements is not None:
            guest.special_requirements = (
                guest_in.special_requirements.strip() if guest_in.special_requirements else None
            )
        if guest_in.notes is not None:
            guest.notes = guest_in.notes.strip() if guest_in.notes else None

        guest.updated_at = datetime.utcnow().isoformat()
        self.db.commit()
        self.db.refresh(guest)
        return self._to_response(guest)

    def update_guest_status(
        self, event_id: str, guest_id: str, status_in: GuestStatusUpdate
    ) -> Optional[GuestResponse]:
        guest = (
            self.db.query(GuestModel)
            .filter(GuestModel.event_id == event_id, GuestModel.id == guest_id)
            .first()
        )
        if not guest:
            return None

        if status_in.invitation_status is not None:
            guest.invitation_status = status_in.invitation_status
        if status_in.rsvp_status is not None:
            guest.rsvp_status = status_in.rsvp_status

        guest.updated_at = datetime.utcnow().isoformat()
        self.db.commit()
        self.db.refresh(guest)
        return self._to_response(guest)

    def delete_guest(self, event_id: str, guest_id: str) -> bool:
        guest = (
            self.db.query(GuestModel)
            .filter(GuestModel.event_id == event_id, GuestModel.id == guest_id)
            .first()
        )
        if not guest:
            return False
        self.db.delete(guest)
        self.db.commit()
        return True

    def get_rsvp_summary(self, event_id: str) -> GuestRSVPSummary:
        event = self.db.query(EventModel).filter(EventModel.id == event_id).first()
        if not event:
            raise ValueError(f"Event '{event_id}' not found")

        guests = self.db.query(GuestModel).filter(GuestModel.event_id == event_id).all()

        total_guests = len(guests)
        sent_count = 0
        not_sent_count = 0
        accepted_count = 0
        pending_count = 0
        declined_count = 0
        confirmed_plus_ones = 0

        cat_counts = {c: 0 for c in VALID_CATEGORIES}

        for g in guests:
            # Invitation
            if g.invitation_status == "Sent":
                sent_count += 1
            else:
                not_sent_count += 1

            # RSVP
            if g.rsvp_status == "Accepted":
                accepted_count += 1
                confirmed_plus_ones += g.plus_ones
            elif g.rsvp_status == "Declined":
                declined_count += 1
            else:
                pending_count += 1

            # Category
            c = self._normalize_category(g.category)
            cat_counts[c] = cat_counts.get(c, 0) + 1

        total_expected_attendance = accepted_count + confirmed_plus_ones
        responded = accepted_count + declined_count
        response_rate = round((responded / total_guests * 100), 1) if total_guests > 0 else 0.0
        acceptance_rate = round((accepted_count / responded * 100), 1) if responded > 0 else 0.0

        return GuestRSVPSummary(
            event_id=event_id,
            total_guests_invited=total_guests,
            total_invitations_sent=sent_count,
            total_invitations_pending=not_sent_count,
            confirmed_guests=accepted_count,
            pending_responses=pending_count,
            declined_guests=declined_count,
            confirmed_plus_ones=confirmed_plus_ones,
            total_expected_attendance=total_expected_attendance,
            rsvp_response_rate=response_rate,
            acceptance_rate=acceptance_rate,
            category_counts=cat_counts,
            rsvp_counts={
                "Accepted": accepted_count,
                "Declined": declined_count,
                "Pending": pending_count,
            },
            invitation_counts={
                "Sent": sent_count,
                "Not Sent": not_sent_count,
            },
        )

    def preview_csv_import(self, event_id: str, csv_content: str) -> CSVImportPreviewResponse:
        """
        Validates uploaded CSV file (expected columns: name, email, phone, category, plus_ones).
        Checks for required names, validates numbers, and detects duplicates.
        """
        existing_guests = self.db.query(GuestModel).filter(GuestModel.event_id == event_id).all()
        existing_emails: Set[str] = {
            g.email.lower() for g in existing_guests if g.email and g.email.strip()
        }
        existing_phones: Set[str] = {
            g.phone.strip() for g in existing_guests if g.phone and g.phone.strip()
        }

        seen_emails_in_csv: Set[str] = set()
        seen_phones_in_csv: Set[str] = set()

        preview_rows: List[CSVImportPreviewRow] = []
        valid_count = 0
        dup_count = 0
        invalid_count = 0

        # Read CSV lines
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        if not rows:
            return CSVImportPreviewResponse(
                total_rows=0,
                valid_rows_count=0,
                duplicate_rows_count=0,
                invalid_rows_count=0,
                preview_rows=[],
            )

        # Check headers (first row)
        headers = [h.strip().lower() for h in rows[0]]
        # Map common header aliases
        name_idx = next((i for i, h in enumerate(headers) if h in ["name", "full_name", "guest_name"]), -1)
        email_idx = next((i for i, h in enumerate(headers) if h in ["email", "email_address", "mail"]), -1)
        phone_idx = next((i for i, h in enumerate(headers) if h in ["phone", "phone_number", "mobile", "tel"]), -1)
        cat_idx = next((i for i, h in enumerate(headers) if h in ["category", "guest_category", "group"]), -1)
        plus_idx = next((i for i, h in enumerate(headers) if h in ["plus_ones", "plus_one", "plusones", "additional_guests"]), -1)

        # If headers couldn't be parsed, assume standard order: name, email, phone, category, plus_ones
        has_headers = name_idx != -1
        data_rows = rows[1:] if has_headers else rows
        if not has_headers:
            name_idx = 0
            email_idx = 1 if len(headers) > 1 else -1
            phone_idx = 2 if len(headers) > 2 else -1
            cat_idx = 3 if len(headers) > 3 else -1
            plus_idx = 4 if len(headers) > 4 else -1

        for row_idx, row in enumerate(data_rows, start=1 if not has_headers else 2):
            if not any(cell.strip() for cell in row):
                continue

            errors: List[str] = []
            is_duplicate = False

            # Name
            raw_name = row[name_idx].strip() if 0 <= name_idx < len(row) else ""
            if not raw_name:
                errors.append("Guest name is missing or empty.")

            # Email
            raw_email = row[email_idx].strip().lower() if 0 <= email_idx < len(row) and row[email_idx].strip() else None

            # Phone
            raw_phone = row[phone_idx].strip() if 0 <= phone_idx < len(row) and row[phone_idx].strip() else None

            # Category
            raw_cat = row[cat_idx].strip() if 0 <= cat_idx < len(row) and row[cat_idx].strip() else "Others"
            normalized_cat = self._normalize_category(raw_cat)

            # Plus Ones
            raw_plus = 0
            if 0 <= plus_idx < len(row) and row[plus_idx].strip():
                try:
                    raw_plus = max(0, int(row[plus_idx].strip()))
                except ValueError:
                    errors.append(f"Invalid plus_ones count '{row[plus_idx].strip()}'. Must be a number.")

            # Check Duplicates against existing DB records and current batch
            if raw_email:
                if raw_email in existing_emails:
                    is_duplicate = True
                    errors.append(f"Duplicate email '{raw_email}' already exists in this event.")
                elif raw_email in seen_emails_in_csv:
                    is_duplicate = True
                    errors.append(f"Duplicate email '{raw_email}' appears multiple times in this CSV.")
                else:
                    seen_emails_in_csv.add(raw_email)

            if raw_phone:
                if raw_phone in existing_phones:
                    is_duplicate = True
                    errors.append(f"Duplicate phone '{raw_phone}' already exists in this event.")
                elif raw_phone in seen_phones_in_csv:
                    is_duplicate = True
                    errors.append(f"Duplicate phone '{raw_phone}' appears multiple times in this CSV.")
                else:
                    seen_phones_in_csv.add(raw_phone)

            is_valid = len(errors) == 0

            if is_duplicate:
                dup_count += 1
            elif not is_valid:
                invalid_count += 1
            else:
                valid_count += 1

            preview_rows.append(
                CSVImportPreviewRow(
                    row_number=row_idx,
                    full_name=raw_name,
                    email=raw_email,
                    phone=raw_phone,
                    category=normalized_cat,
                    plus_ones=raw_plus,
                    is_valid=is_valid,
                    is_duplicate=is_duplicate,
                    errors=errors,
                )
            )

        return CSVImportPreviewResponse(
            total_rows=len(preview_rows),
            valid_rows_count=valid_count,
            duplicate_rows_count=dup_count,
            invalid_rows_count=invalid_count,
            preview_rows=preview_rows,
        )

    def confirm_csv_import(
        self, event_id: str, rows_to_import: List[GuestCreate]
    ) -> CSVImportResult:
        event = self.db.query(EventModel).filter(EventModel.id == event_id).first()
        if not event:
            raise ValueError(f"Event '{event_id}' not found")

        imported = 0
        skipped = 0
        errors: List[str] = []

        now = datetime.utcnow().isoformat()

        for g in rows_to_import:
            try:
                # Re-validate duplicate check
                email = g.email.strip().lower() if g.email and g.email.strip() else None
                phone = g.phone.strip() if g.phone and g.phone.strip() else None

                if email:
                    existing = (
                        self.db.query(GuestModel)
                        .filter(GuestModel.event_id == event_id, func.lower(GuestModel.email) == email)
                        .first()
                    )
                    if existing:
                        skipped += 1
                        errors.append(f"Skipped '{g.full_name}': Email '{email}' already registered.")
                        continue

                if phone:
                    existing = (
                        self.db.query(GuestModel)
                        .filter(GuestModel.event_id == event_id, GuestModel.phone == phone)
                        .first()
                    )
                    if existing:
                        skipped += 1
                        errors.append(f"Skipped '{g.full_name}': Phone '{phone}' already registered.")
                        continue

                guest = GuestModel(
                    id=f"gst_{uuid.uuid4().hex[:12]}",
                    event_id=event_id,
                    full_name=g.full_name.strip(),
                    email=email,
                    phone=phone,
                    category=self._normalize_category(g.category),
                    plus_ones=max(0, g.plus_ones),
                    invitation_status="Not Sent",
                    rsvp_status="Pending",
                    special_requirements=g.special_requirements.strip() if g.special_requirements else None,
                    notes=g.notes.strip() if g.notes else None,
                    created_at=now,
                    updated_at=now,
                )
                self.db.add(guest)
                imported += 1
            except Exception as e:
                skipped += 1
                errors.append(f"Failed to import '{g.full_name}': {str(e)}")

        self.db.commit()
        return CSVImportResult(
            imported_count=imported,
            skipped_count=skipped,
            errors=errors,
        )

    def _to_response(self, guest: GuestModel) -> GuestResponse:
        return GuestResponse(
            id=guest.id,
            event_id=guest.event_id,
            full_name=guest.full_name,
            email=guest.email,
            phone=guest.phone,
            category=guest.category,
            plus_ones=guest.plus_ones,
            invitation_status=guest.invitation_status,
            rsvp_status=guest.rsvp_status,
            special_requirements=guest.special_requirements,
            notes=guest.notes,
            created_at=guest.created_at,
            updated_at=guest.updated_at,
        )
