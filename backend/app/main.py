import os
import json
from decimal import Decimal
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Response, Request, Query, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import io

from .database import engine, Base, get_db, SessionLocal, init_db_schema_and_migrations
from .schemas import (
    EventIntake,
    FullEventPlan,
    DashboardSummary,
    ChatRequest,
    ChatResponse,
    ChatMessage,
    BudgetAnalysis,
    BudgetOptimizationRequest,
    BudgetOptimizationResponse,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseTrackingSummary,
    GuestCreate,
    GuestUpdate,
    GuestStatusUpdate,
    GuestResponse,
    GuestRSVPSummary,
    CSVImportPreviewRequest,
    CSVImportPreviewResponse,
    CSVImportConfirmRequest,
    CSVImportResult,
    InvitationTextComponents,
    InvitationVariation,
    InvitationGenerateRequest,
    InvitationGenerateResponse,
    InvitationDesignConfig,
    InvitationCreateRequest,
    InvitationResponse,
    InvitationPDFExportRequest,
    VendorCreate,
    VendorUpdate,
    VendorResponse,
    VendorRecommendationQuery,
    VendorRecommendationResponse,
    VendorComparisonRequest,
    VendorComparisonResponse,
    EventVendorBookingCreate,
    EventVendorBookingUpdate,
    EventVendorBookingResponse,
    VendorAnalyticsSummary,
    RecordAdvanceExpenseRequest,
    LocationGeoResult,
    WeatherReportResponse,
    WeatherAssistantQuery,
    WeatherAssistantResponse,
    SaveTimelineMitigationsRequest,
    SaveTimelineMitigationsResponse,
    BudgetItem,
    CategoryTaxonomyAnalysis,
    NormalizeCategoriesRequest,
    BudgetSpentAdjustRequest,
    UpdateCategoryProtectionRequest,
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    ExecutiveDashboardResponse,
)
from .models import (
    GuestModel,
    UserModel,
    EventModel,
    ExpenseModel,
    InvitationModel,
    EventVendorBookingModel,
)
from .plan_service import PlanService
from .chat_service import ChatService
from .export_service import ExportService
from .gemini_client import GeminiClient
from .budget_optimizer import (
    analyze_budget,
    SmartBudgetOptimizer,
    STANDARD_CATEGORIES,
    map_category_to_canonical,
    detect_duplicate_and_overlapping_categories,
    normalize_budget_categories,
    to_decimal,
)
from .expense_service import ExpenseService
from .guest_service import GuestService
from .invitation_service import (
    InvitationService,
    BUILTIN_TEMPLATES,
    resolve_event_venue,
    resolve_event_time,
)
from .vendor_service import VendorService
from .weather_service import WeatherService
from .auth_service import (
    AuthService,
    get_current_user,
    get_current_user_optional,
    get_current_user_required,
    verify_event_ownership,
)
from .executive_service import ExecutiveDashboardService

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

# In local development, auto-initialize SQLite tables for smooth developer experience.
# In production, database tables and migrations are strictly governed by Alembic (`alembic upgrade head`).
if APP_ENV != "production":
    Base.metadata.create_all(bind=engine)

    def _ensure_schema_migrations():
        try:
            from sqlalchemy import inspect, text
            with engine.connect() as conn:
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                if "events" in tables:
                    columns = [col["name"] for col in inspector.get_columns("events")]
                    if "owner_id" not in columns:
                        conn.execute(text("ALTER TABLE events ADD COLUMN owner_id VARCHAR(64)"))
                        conn.commit()
        except Exception:
            pass

    _ensure_schema_migrations()
    try:
        init_db_schema_and_migrations()
    except Exception:
        pass

# Seed verified vendor directory if empty
try:
    with SessionLocal() as _seed_db:
        VendorService.init_seed_directory(_seed_db)
except Exception:
    pass

app = FastAPI(
    title="Celebration & Event Planner API",
    description="GenAI-powered planning assistant for weddings, birthdays, and community events",
    version="1.0.0",
)

logger = logging.getLogger("eventify_security")

# Phase 3: Environment-driven secure CORS configuration
cors_origins_env = os.getenv("ALLOWED_ORIGINS", os.getenv("CORS_ORIGINS", "")).strip()

if cors_origins_env:
    allowed_origins = [orig.strip() for orig in cors_origins_env.split(",") if orig.strip()]
elif APP_ENV == "production":
    deployed_origin = os.getenv("DEPLOYED_ORIGIN", os.getenv("RENDER_EXTERNAL_URL", "")).strip()
    allowed_origins = [deployed_origin] if deployed_origin else []
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

# Never combine wildcard origins with credentials
allow_creds = "*" not in allowed_origins and len(allowed_origins) > 0
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_creds,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With", "X-Disable-Dev-Demo"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Request validation error", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Graceful error boundary ensuring client never receives an unhandled crash or leaked stack trace."""
    logger.error("Unhandled internal server error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


@app.get("/api/health")
def health_check():
    gemini = GeminiClient()
    return {
        "status": "healthy",
        "gemini_configured": gemini.is_available(),
        "database": "connected",
    }


# =============================================================
# Authentication & User Management Endpoints
# =============================================================

@app.post("/api/auth/register", response_model=UserRegisterResponse)
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    auth = AuthService(db)
    return auth.register(req)


@app.post("/api/auth/login", response_model=TokenResponse)
def login_user(req: UserLoginRequest, db: Session = Depends(get_db)):
    auth = AuthService(db)
    return auth.login(req)


@app.get("/api/auth/me", response_model=UserResponse)
def get_current_user_profile(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        email_verified=user.email_verified,
        email_verified_at=user.email_verified_at,
        created_at=user.created_at,
    )


@app.post("/api/auth/logout")
def logout_user():
    return {"message": "Logged out successfully."}


# =============================================================
# Executive Command Center / Dashboard Endpoint
# =============================================================

@app.get("/api/dashboard/executive-summary", response_model=ExecutiveDashboardResponse)
def get_executive_summary(
    event_id: Optional[str] = None,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if event_id:
        verify_event_ownership(event_id, user, db)
    exec_service = ExecutiveDashboardService(db, user)
    return exec_service.get_executive_summary(event_id=event_id)


@app.post("/api/events", response_model=FullEventPlan)
def create_event(
    intake: EventIntake,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan_service = PlanService(db)
    return plan_service.create_plan(intake, owner_id=user.id)


@app.get("/api/events", response_model=list[DashboardSummary])
def list_events(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan_service = PlanService(db)
    return plan_service.list_events(user_id=user.id)


@app.get("/api/events/{event_id}", response_model=FullEventPlan)
def get_event(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    plan_service = PlanService(db)
    plan = plan_service.get_plan(event_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Event not found")
    return plan


@app.put("/api/events/{event_id}", response_model=FullEventPlan)
def update_event(
    event_id: str,
    plan_update: FullEventPlan,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    plan_service = PlanService(db)
    existing = plan_service.get_plan(event_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Event not found")
    return plan_service.update_plan(event_id, plan_update)


@app.get("/api/events/{event_id}/budget-analysis", response_model=BudgetAnalysis)
def get_budget_analysis(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    plan_service = PlanService(db)
    plan = plan_service.get_plan(event_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Event not found")
    return analyze_budget(plan.budget)


@app.post("/api/events/{event_id}/optimize-budget", response_model=BudgetOptimizationResponse)
def optimize_event_budget(
    event_id: str,
    req: BudgetOptimizationRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    plan_service = PlanService(db)
    plan = plan_service.get_plan(event_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Event not found")
    optimizer = SmartBudgetOptimizer()
    return optimizer.optimize(plan, req.user_prompt, req.protected_categories)


@app.get("/api/events/{event_id}/category-analysis", response_model=CategoryTaxonomyAnalysis)
def get_category_analysis(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    plan_service = PlanService(db)
    plan = plan_service.get_plan(event_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Event not found")

    warnings, suggestions = detect_duplicate_and_overlapping_categories(plan.budget.items, plan.budget.currency)
    items_analysis = []
    for it in plan.budget.items:
        mapped, conf, is_comp = map_category_to_canonical(it.category)
        items_analysis.append({
            "id": it.id,
            "category": it.category,
            "canonical_category": mapped,
            "is_compound": is_comp,
            "confidence": conf,
            "classification": it.classification or "important",
            "is_protected": it.is_protected or it.is_contingency,
            "allocated_amount": it.allocated_amount,
            "percentage": it.percentage,
        })
    min_protected = sum(to_decimal(i.allocated_amount) for i in plan.budget.items if i.is_protected or i.is_contingency)
    return CategoryTaxonomyAnalysis(
        event_id=event_id,
        standard_categories=STANDARD_CATEGORIES,
        items_analysis=items_analysis,
        duplicate_warnings=warnings,
        merge_suggestions=suggestions,
        minimum_protected_budget=float(min_protected),
        total_budget=plan.budget.total_budget,
        currency=plan.budget.currency,
    )


@app.post("/api/events/{event_id}/normalize-categories", response_model=FullEventPlan)
def normalize_event_categories(
    event_id: str,
    req: NormalizeCategoriesRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    record = db.query(EventModel).filter(EventModel.id == event_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Event not found")

    try:
        plan_data = json.loads(record.plan_json)
        plan = FullEventPlan(**plan_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse event plan: {str(e)}")

    normalized_items, rename_map = normalize_budget_categories(
        items=plan.budget.items,
        total_budget=plan.budget.total_budget,
        approved_canonical_merges=req.approved_canonical_merges,
        currency=plan.budget.currency,
        return_rename_map=True,
    )

    try:
        # 1. Update ExpenseModel records in SQLite in atomic transaction
        if rename_map:
            expenses = db.query(ExpenseModel).filter(ExpenseModel.event_id == event_id).all()
            for exp in expenses:
                exp_cat_norm = exp.category.strip().lower()
                if exp_cat_norm in rename_map:
                    exp.category = rename_map[exp_cat_norm]
                    exp.updated_at = datetime.utcnow().isoformat()

        # 2. Sync actual_spent from SQLite expenses table if expenses exist
        expenses = db.query(ExpenseModel).filter(ExpenseModel.event_id == event_id).all()
        if expenses:
            cat_spent: Dict[str, float] = {}
            total_spent = Decimal("0.00")
            for exp in expenses:
                c_norm = exp.category.strip().lower()
                amt_d = to_decimal(exp.amount)
                cat_spent[c_norm] = float(to_decimal(cat_spent.get(c_norm, 0.0)) + amt_d)
                total_spent += amt_d

            for it in normalized_items:
                c_norm = it.category.strip().lower()
                it.actual_spent = round(cat_spent.get(c_norm, 0.0), 2)

            plan.budget.total_actual_spent = float(total_spent)
            plan.budget.is_over_budget = float(total_spent) > plan.budget.total_budget
            plan.budget.over_budget_amount = max(0.0, float(total_spent) - plan.budget.total_budget)

        # 3. Update plan budget items
        plan.budget.items = normalized_items
        plan.budget.total_allocated = round(sum(i.allocated_amount for i in normalized_items), 2)
        plan.updated_at = datetime.utcnow().isoformat()

        record.plan_json = json.dumps(plan.model_dump())
        record.updated_at = plan.updated_at

        db.commit()
        db.refresh(record)
        return plan
    except Exception as e:
        db.rollback()
        logger.error(f"Consolidation transaction failed for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database consolidation transaction failed: {str(e)}")


@app.post("/api/events/{event_id}/budget/adjust-spent", response_model=FullEventPlan)
def adjust_budget_spent_endpoint(
    event_id: str,
    req: BudgetSpentAdjustRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Adjusts actual spent for a category from Budget Planner, creating or updating
    auditable ExpenseModel ledger records in SQLite to keep both modules in 100% sync.
    """
    verify_event_ownership(event_id, user, db)
    service = ExpenseService(db)
    try:
        return service.adjust_budget_spent(
            event_id=event_id,
            category=req.category,
            target_spent=req.target_spent,
            notes=req.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to adjust budget spent for {event_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/events/{event_id}/categories/{item_id}", response_model=BudgetItem)
def update_category_protection(
    event_id: str,
    item_id: str,
    req: UpdateCategoryProtectionRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    plan_service = PlanService(db)
    plan = plan_service.get_plan(event_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Event not found")

    target_item = next((i for i in plan.budget.items if i.id == item_id), None)
    if not target_item:
        raise HTTPException(status_code=404, detail="Category item not found")

    if req.is_protected is not None:
        target_item.is_protected = req.is_protected
    if req.classification is not None:
        target_item.classification = req.classification

    plan_service.update_plan(event_id, plan)
    return target_item


@app.delete("/api/events/{event_id}")
def delete_event(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    plan_service = PlanService(db)
    success = plan_service.delete_event(event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted successfully"}


@app.post("/api/chat", response_model=ChatResponse)
def chat_with_assistant(
    req: ChatRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(req.event_id, user, db)
    chat_service = ChatService(db)
    return chat_service.process_message(req.event_id, req.message)


@app.get("/api/chat/{event_id}/history", response_model=list[ChatMessage])
def get_chat_history(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    chat_service = ChatService(db)
    return chat_service.get_history(event_id)


@app.get("/api/events/{event_id}/export/csv")
def export_csv(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    plan_service = PlanService(db)
    plan = plan_service.get_plan(event_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Event not found")
    csv_data = ExportService.generate_csv(plan)
    filename = f"{plan.intake.title.replace(' ', '_')}_Plan.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/events/{event_id}/export/pdf")
def export_pdf(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    plan_service = PlanService(db)
    plan = plan_service.get_plan(event_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Event not found")
    pdf_bytes = ExportService.generate_pdf(plan)
    filename = f"{plan.intake.title.replace(' ', '_')}_Plan.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# =========================================================
# PHASE 2: SMART EXPENSE TRACKING ROUTES
# =========================================================

@app.post("/api/events/{event_id}/expenses", response_model=ExpenseResponse)
def create_expense(
    event_id: str,
    expense_in: ExpenseCreate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = ExpenseService(db)
    return service.create_expense(event_id, expense_in)


@app.get("/api/events/{event_id}/expenses", response_model=List[ExpenseResponse])
def list_expenses(
    event_id: str,
    category: Optional[str] = Query(None, description="Filter by category"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status (Paid/Pending)"),
    search: Optional[str] = Query(None, description="Search keyword in name, vendor, or notes"),
    start_date: Optional[str] = Query(None, description="Filter expenses on or after YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Filter expenses on or before YYYY-MM-DD"),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = ExpenseService(db)
    return service.list_expenses(
        event_id,
        category=category,
        payment_status=payment_status,
        search=search,
        start_date=start_date,
        end_date=end_date,
    )


@app.get("/api/events/{event_id}/expenses/summary", response_model=ExpenseTrackingSummary)
def get_expense_summary(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = ExpenseService(db)
    return service.get_expense_summary(event_id)


@app.get("/api/events/{event_id}/expenses/{expense_id}", response_model=ExpenseResponse)
def get_single_expense(
    event_id: str,
    expense_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = ExpenseService(db)
    exp = service.get_expense(event_id, expense_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Expense not found")
    return exp


@app.put("/api/events/{event_id}/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    event_id: str,
    expense_id: str,
    expense_in: ExpenseUpdate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = ExpenseService(db)
    updated = service.update_expense(event_id, expense_id, expense_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Expense not found")
    return updated


@app.delete("/api/events/{event_id}/expenses/{expense_id}")
def delete_expense(
    event_id: str,
    expense_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = ExpenseService(db)
    success = service.delete_expense(event_id, expense_id)
    if not success:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"message": "Expense deleted successfully"}


@app.get("/api/events/{event_id}/expenses/export/csv")
def export_expenses_csv(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = verify_event_ownership(event_id, user, db)
    service = ExpenseService(db)
    summary = service.get_expense_summary(event_id)
    expenses = service.list_expenses(event_id)

    title = plan.title or "Celebration"
    csv_data = ExportService.generate_expenses_csv(title, summary, expenses)
    filename = f"{title.replace(' ', '_')}_Expenses.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/events/{event_id}/expenses/export/pdf")
def export_expenses_pdf(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = verify_event_ownership(event_id, user, db)
    service = ExpenseService(db)
    summary = service.get_expense_summary(event_id)
    expenses = service.list_expenses(event_id)

    title = plan.title or "Celebration"
    pdf_bytes = ExportService.generate_expenses_pdf(
        event_title=title,
        event_date=plan.date or "",
        event_city=plan.city or "",
        summary=summary,
        expenses=expenses,
    )
    filename = f"{title.replace(' ', '_')}_Expenses.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# =========================================================
# PHASE 3: GUEST MANAGEMENT & RSVP SYSTEM ROUTES
# =========================================================

@app.post("/api/events/{event_id}/guests", response_model=GuestResponse)
def create_guest(
    event_id: str,
    guest_in: GuestCreate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = GuestService(db)
    try:
        return service.create_guest(event_id, guest_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/events/{event_id}/guests", response_model=List[GuestResponse])
def list_guests(
    event_id: str,
    search: Optional[str] = Query(None, description="Search guest name, email, phone, or notes"),
    category: Optional[str] = Query(None, description="Filter by guest category"),
    rsvp_status: Optional[str] = Query(None, description="Filter by RSVP status (Pending/Accepted/Declined)"),
    invitation_status: Optional[str] = Query(None, description="Filter by invitation status (Not Sent/Sent)"),
    sort_by: Optional[str] = Query("name_asc", description="Sort order: name_asc, name_desc, date_desc, category_asc"),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = GuestService(db)
    return service.list_guests(
        event_id,
        search=search,
        category=category,
        rsvp_status=rsvp_status,
        invitation_status=invitation_status,
        sort_by=sort_by or "name_asc",
    )


@app.get("/api/events/{event_id}/guests/summary", response_model=GuestRSVPSummary)
def get_guest_rsvp_summary(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = GuestService(db)
    return service.get_rsvp_summary(event_id)


@app.get("/api/events/{event_id}/guests/{guest_id}", response_model=GuestResponse)
def get_single_guest(
    event_id: str,
    guest_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = GuestService(db)
    guest = service.get_guest(event_id, guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    return guest


@app.put("/api/events/{event_id}/guests/{guest_id}", response_model=GuestResponse)
def update_guest(
    event_id: str,
    guest_id: str,
    guest_in: GuestUpdate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = GuestService(db)
    try:
        updated = service.update_guest(event_id, guest_id, guest_in)
        if not updated:
            raise HTTPException(status_code=404, detail="Guest not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/api/events/{event_id}/guests/{guest_id}/status", response_model=GuestResponse)
def update_guest_status(
    event_id: str,
    guest_id: str,
    status_in: GuestStatusUpdate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = GuestService(db)
    updated = service.update_guest_status(event_id, guest_id, status_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Guest not found")
    return updated


@app.delete("/api/events/{event_id}/guests/{guest_id}")
def delete_guest(
    event_id: str,
    guest_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = GuestService(db)
    success = service.delete_guest(event_id, guest_id)
    if not success:
        raise HTTPException(status_code=404, detail="Guest not found")
    return {"message": "Guest deleted successfully"}


@app.post("/api/events/{event_id}/guests/import/preview", response_model=CSVImportPreviewResponse)
def preview_csv_import(
    event_id: str,
    req: CSVImportPreviewRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    if not req.csv_content or not req.csv_content.strip():
        raise HTTPException(status_code=400, detail="CSV content is empty.")

    service = GuestService(db)
    return service.preview_csv_import(event_id, req.csv_content)


@app.post("/api/events/{event_id}/guests/import/confirm", response_model=CSVImportResult)
def confirm_csv_import(
    event_id: str,
    req: CSVImportConfirmRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_event_ownership(event_id, user, db)
    service = GuestService(db)
    return service.confirm_csv_import(event_id, req.rows)


@app.get("/api/events/{event_id}/guests/export/csv")
def export_guests_csv(
    event_id: str,
    filter_status: Optional[str] = Query("All", description="Filter: All, Accepted, Pending, Declined"),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = verify_event_ownership(event_id, user, db)
    service = GuestService(db)
    rsvp_filter = filter_status if filter_status and filter_status != "All" else None
    guests = service.list_guests(event_id, rsvp_status=rsvp_filter)

    title = plan.title or "Celebration"
    csv_data = ExportService.generate_guests_csv(title, guests, filter_status or "All")
    filename = f"{title.replace(' ', '_')}_{filter_status or 'All'}_Guests.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/events/{event_id}/guests/export/pdf")
def export_guests_pdf(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = verify_event_ownership(event_id, user, db)
    service = GuestService(db)
    summary = service.get_rsvp_summary(event_id)
    guests = service.list_guests(event_id)

    title = plan.title or "Celebration"
    pdf_bytes = ExportService.generate_guests_pdf(
        event_title=title,
        event_date=plan.date or "",
        event_city=plan.city or "",
        summary=summary,
        guests=guests,
    )
    filename = f"{title.replace(' ', '_')}_Guests_Report.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# =========================================================
# PHASE 4: AI INVITATION GENERATOR ENDPOINTS
# =========================================================

@app.get("/api/invitations/templates")
def get_invitation_templates():
    """Returns available professional invitation card design templates."""
    return BUILTIN_TEMPLATES


@app.post("/api/invitations/generate", response_model=InvitationGenerateResponse)
def generate_invitation_texts(
    req: InvitationGenerateRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates 3 personalized invitation variations in English, Hindi, or Gujarati.
    Preserves all provided facts (names, dates, times, venue) accurately.
    """
    guest = None
    if req.guest_id:
        guest = db.query(GuestModel).filter(GuestModel.id == req.guest_id).first()
        if guest:
            verify_event_ownership(guest.event_id, user, db)

    return InvitationService.generate_invitations(req, guest=guest, db=db)


@app.post("/api/events/{event_id}/invitations", response_model=InvitationResponse)
def create_saved_invitation(
    event_id: str,
    req: InvitationCreateRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Saves a designed invitation card for an event."""
    verify_event_ownership(event_id, user, db)
    if req.event_id != event_id:
        req.event_id = event_id
    try:
        return InvitationService.save_invitation(db, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/events/{event_id}/invitations", response_model=List[InvitationResponse])
def get_saved_invitations(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves all saved invitations for an event."""
    verify_event_ownership(event_id, user, db)
    return InvitationService.get_event_invitations(db, event_id)


@app.get("/api/invitations/{invitation_id}", response_model=InvitationResponse)
def get_invitation_by_id(
    invitation_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves a specific invitation by its ID with ownership check."""
    inv = InvitationService.get_invitation(db, invitation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    verify_event_ownership(inv.event_id, user, db)
    return inv


@app.delete("/api/invitations/{invitation_id}")
def delete_saved_invitation(
    invitation_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a saved invitation with ownership check."""
    inv = InvitationService.get_invitation(db, invitation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    verify_event_ownership(inv.event_id, user, db)
    success = InvitationService.delete_invitation(db, invitation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return {"message": "Invitation deleted successfully", "id": invitation_id}


@app.post("/api/invitations/export-pdf")
def export_invitation_pdf(
    req: InvitationPDFExportRequest,
    user: UserModel = Depends(get_current_user),
):
    """Generates a luxury 5x7 printable PDF invitation card dynamically."""
    pdf_bytes = ExportService.generate_invitation_pdf(
        title=req.title,
        language=req.language,
        components=req.text_components,
        design_config=req.design_config,
        event_info=req.event_details,
    )
    safe_slug = "".join(c for c in req.title if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_") or "Invitation"
    filename = f"{safe_slug}_Card.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/invitations/{invitation_id}/export-pdf")
def export_saved_invitation_pdf(
    invitation_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exports a saved invitation card as a 5x7 printable PDF with ownership check."""
    inv = InvitationService.get_invitation(db, invitation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    verify_event_ownership(inv.event_id, user, db)

    event = db.query(EventModel).filter(EventModel.id == inv.event_id).first()
    event_info = None
    if event:
        intake_data = json.loads(event.intake_json) if event.intake_json else {}
        event_info = {
            "event_name": event.title,
            "event_type": event.event_type,
            "event_date": event.date,
            "event_time": resolve_event_time(db, event.id),
            "venue": resolve_event_venue(db, event.id, event.city or ""),
            "location": event.city,
            "host_names": intake_data.get("host_names") or "The Host Family",
        }

    pdf_bytes = ExportService.generate_invitation_pdf(
        title=inv.title,
        language=inv.language,
        components=inv.text_components,
        design_config=inv.design_config,
        event_info=event_info,
    )
    safe_slug = "".join(c for c in inv.title if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_") or "Invitation"
    filename = f"{safe_slug}_Card.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/api/events/{event_id}/guests/{guest_id}/mark-sent", response_model=GuestResponse)
def mark_guest_invitation_sent(
    event_id: str,
    guest_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Explicitly marks guest invitation as Sent upon manual confirmation.
    Preserves existing RSVP records without changing RSVP status.
    """
    verify_event_ownership(event_id, user, db)
    try:
        guest = InvitationService.mark_guest_invitation_sent(db, event_id, guest_id)
        service = GuestService(db)
        return service._to_response(guest)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))





# =========================================================
# PHASE 5: LOCAL VENDOR DISCOVERY, RECOMMENDATION & BOOKINGS
# =========================================================

@app.get("/api/vendors", response_model=List[VendorResponse])
def get_vendors(
    category: Optional[str] = None,
    location: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    search: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """Retrieves vendors from directory matching filters."""
    return VendorService.get_vendors(
        db=db,
        category=category,
        location=location,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        search=search,
        is_favorite=is_favorite,
        is_verified=is_verified,
    )


@app.get("/api/vendors/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves a specific vendor profile by ID."""
    vendor = VendorService.get_vendor_by_id(db, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@app.post("/api/vendors", response_model=VendorResponse)
def create_vendor(
    data: VendorCreate,
    db: Session = Depends(get_db),
):
    """Creates a user-added vendor in the directory."""
    return VendorService.create_vendor(db, data)


@app.put("/api/vendors/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: str,
    data: VendorUpdate,
    db: Session = Depends(get_db),
):
    """Updates a user-created vendor. Verified directory listings cannot be modified."""
    try:
        return VendorService.update_vendor(db, vendor_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/vendors/{vendor_id}")
def delete_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
):
    """Deletes a user-created vendor. Verified directory listings cannot be deleted."""
    try:
        success = VendorService.delete_vendor(db, vendor_id)
        if not success:
            raise HTTPException(status_code=404, detail="Vendor not found")
        return {"message": "Vendor deleted successfully", "id": vendor_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/api/vendors/{vendor_id}/favorite", response_model=VendorResponse)
def toggle_vendor_favorite(
    vendor_id: str,
    db: Session = Depends(get_db),
):
    """Toggles bookmark/favorite status on a vendor."""
    try:
        return VendorService.toggle_favorite(db, vendor_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/vendors/recommend", response_model=VendorRecommendationResponse)
def recommend_vendors(
    query_req: VendorRecommendationQuery,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    AI-powered vendor recommendation grounded strictly in actual database records.
    Never invents businesses, prices, ratings, phone numbers, or addresses.
    """
    if query_req.event_id:
        verify_event_ownership(query_req.event_id, user, db)
    return VendorService.recommend_vendors(db, query_req)


@app.post("/api/vendors/compare", response_model=VendorComparisonResponse)
def compare_vendors(
    compare_req: VendorComparisonRequest,
    db: Session = Depends(get_db),
):
    """Compares up to 3 database vendors side-by-side with AI evaluation."""
    try:
        return VendorService.compare_vendors(db, compare_req.vendor_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/events/{event_id}/vendor-bookings", response_model=EventVendorBookingResponse)
def create_or_update_event_booking(
    event_id: str,
    data: EventVendorBookingCreate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Creates or updates a vendor booking associated with an event."""
    verify_event_ownership(event_id, user, db)
    if data.event_id != event_id:
        data.event_id = event_id
    try:
        return VendorService.create_or_update_booking(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/events/{event_id}/vendor-bookings", response_model=List[EventVendorBookingResponse])
def get_event_bookings(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves all vendor bookings for an event."""
    verify_event_ownership(event_id, user, db)
    return VendorService.get_event_bookings(db, event_id)


@app.put("/api/vendor-bookings/{booking_id}", response_model=EventVendorBookingResponse)
def update_event_booking(
    booking_id: str,
    data: EventVendorBookingUpdate,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates a vendor booking status, agreed price, or advance payment."""
    booking = db.query(EventVendorBookingModel).filter(EventVendorBookingModel.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    verify_event_ownership(booking.event_id, user, db)
    try:
        return VendorService.update_booking(db, booking_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/vendor-bookings/{booking_id}")
def delete_event_booking(
    booking_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Removes a vendor booking association from an event."""
    booking = db.query(EventVendorBookingModel).filter(EventVendorBookingModel.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    verify_event_ownership(booking.event_id, user, db)
    success = VendorService.delete_booking(db, booking_id)
    if not success:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"message": "Booking deleted successfully", "id": booking_id}


@app.get("/api/events/{event_id}/vendor-analytics", response_model=VendorAnalyticsSummary)
def get_event_vendor_analytics(
    event_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Computes vendor analytics, category distribution, and spending for an event."""
    verify_event_ownership(event_id, user, db)
    return VendorService.get_vendor_analytics(db, event_id)


@app.get("/api/vendor-analytics", response_model=VendorAnalyticsSummary)
def get_directory_vendor_analytics(
    db: Session = Depends(get_db),
):
    """Computes overall vendor directory analytics."""
    return VendorService.get_vendor_analytics(db, None)


@app.post("/api/events/{event_id}/vendor-bookings/{booking_id}/record-expense", response_model=ExpenseResponse)
def record_booking_advance_expense(
    event_id: str,
    booking_id: str,
    req: RecordAdvanceExpenseRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Integrates with Phase 2 Smart Expense Tracking.
    Records advance payment as an actual expense in the event budget ledger.
    """
    verify_event_ownership(event_id, user, db)
    booking = db.query(EventVendorBookingModel).filter(EventVendorBookingModel.id == booking_id).first()
    if not booking or booking.event_id != event_id:
        raise HTTPException(status_code=404, detail="Booking not found for this event")
    try:
        return VendorService.record_advance_as_expense(
            db=db,
            event_id=event_id,
            booking_id=booking_id,
            payment_method=req.payment_method or "UPI",
            notes=req.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



# ============================================================================
# PHASE 6: AI WEATHER-AWARE EVENT PLANNER ENDPOINTS
# ============================================================================

@app.get("/api/weather/geocode", response_model=LocationGeoResult)
def geocode_weather_location(city: str = Query(..., min_length=1)):
    """Geocodes a celebration city using Open-Meteo Geocoding API."""
    service = WeatherService()
    try:
        return service.geocode_location(city)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/weather/report", response_model=WeatherReportResponse)
def get_weather_report(
    city: str = Query(..., min_length=1),
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}"),
    event_type: str = Query("wedding"),
    event_id: Optional[str] = Query(None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves weather report for city and date:
    - Within 15 days: live meteorological forecast.
    - Beyond 15 days / in past: historical climate reference.
    - Includes risk assessment and smart event recommendations.
    """
    if event_id:
        verify_event_ownership(event_id, user, db)
    service = WeatherService(db=db)
    try:
        return service.get_weather_report(
            city=city,
            target_date_str=date,
            event_type=event_type,
            event_id=event_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/events/{event_id}/weather", response_model=WeatherReportResponse)
def get_event_weather(
    event_id: str,
    city_override: Optional[str] = Query(None),
    date_override: Optional[str] = Query(None),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves weather report automatically using the event's saved city and date.
    Supports location/date overrides from user input.
    """
    event = verify_event_ownership(event_id, user, db)
    city = city_override or event.city or "Jaipur"
    target_date = date_override or event.date

    service = WeatherService(db=db)
    try:
        return service.get_weather_report(
            city=city,
            target_date_str=target_date,
            event_type=event.event_type,
            event_id=event_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/weather/ask-ai", response_model=WeatherAssistantResponse)
def ask_weather_ai(
    req: WeatherAssistantQuery,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    AI Weather Assistant grounded strictly in retrieved meteorological data.
    """
    if req.event_id:
        verify_event_ownership(req.event_id, user, db)
    service = WeatherService(db=db)
    try:
        report = service.get_weather_report(
            city=req.location,
            target_date_str=req.target_date,
            event_type=req.event_type or "wedding",
            event_id=req.event_id,
        )
        return service.ask_weather_assistant(query=req, weather_report=report)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/events/{event_id}/weather/save-timeline-tasks", response_model=SaveTimelineMitigationsResponse)
def save_weather_timeline_tasks(
    event_id: str,
    req: SaveTimelineMitigationsRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Saves weather mitigation actions directly to the event's timeline.
    Prevents duplicate task creation.
    """
    verify_event_ownership(event_id, user, db)
    service = WeatherService(db=db)
    try:
        return service.save_mitigations_to_timeline(
            event_id=event_id,
            req=req,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Serve frontend static assets and Single Page Application (SPA) routes
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
ASSETS_DIR = FRONTEND_DIST / "assets"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/{full_path:path}", response_class=FileResponse)
async def serve_spa_frontend(full_path: str):
    """
    Serves static frontend assets or falls back to index.html for client-side routing.
    If frontend/dist is not built yet, returns a clear, helpful setup page.
    """
    if FRONTEND_DIST.exists():
        candidate_file = FRONTEND_DIST / full_path
        if full_path and candidate_file.is_file():
            return FileResponse(str(candidate_file))

        index_file = FRONTEND_DIST / "index.html"
        if index_file.is_file():
            return FileResponse(str(index_file))

    # Fallback notice when dist is missing
    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Celebration & Event Planner - Backend Active</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; color: #1e293b; padding: 40px; text-align: center; }
                .card { max-width: 540px; margin: 40px auto; background: white; padding: 32px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #e2e8f0; }
                h1 { color: #0f766e; font-size: 24px; margin-bottom: 12px; }
                p { color: #64748b; font-size: 14px; line-height: 1.6; }
                code { background: #f1f5f9; padding: 3px 8px; border-radius: 6px; font-size: 13px; color: #0f172a; }
                .btn { display: inline-block; margin-top: 16px; padding: 10px 20px; background: #0d9488; color: white; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 13px; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Celebration & Event Planner</h1>
                <p>The backend API is running, but the frontend production build was not found in <code>frontend/dist</code>.</p>
                <p>To generate the frontend build, run:</p>
                <p><code>cd frontend && npm run build</code></p>
                <p>Or start the application using <code>start_app.py</code> or <code>run_dev.bat</code> which builds the frontend automatically.</p>
                <a class="btn" href="/api/health">Check API Health (/api/health)</a>
            </div>
        </body>
        </html>
        """,
        status_code=200 if not full_path else 404,
    )
