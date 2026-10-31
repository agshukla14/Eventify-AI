from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator


class EventIntake(BaseModel):
    event_type: Literal["wedding", "birthday", "community"] = Field(
        ..., description="Type of celebration event"
    )
    title: str = Field(..., min_length=1, max_length=120, description="Name or title of event")
    date: str = Field(..., description="Target date in YYYY-MM-DD format")
    city: str = Field(..., min_length=1, max_length=100, description="City / Location")
    guest_count: int = Field(..., ge=1, le=100000, description="Expected guest count")
    total_budget: float = Field(..., ge=0, description="Total budget in chosen currency")
    currency: str = Field("INR", description="Currency symbol or code, e.g. INR, USD, EUR")
    theme_style: Optional[str] = Field(None, max_length=200, description="Style or aesthetic theme")
    cultural_preferences: Optional[str] = Field(None, max_length=200, description="Cultural / traditional customs")
    dietary_preferences: List[str] = Field(default_factory=list, description="Dietary requirements")
    must_haves: List[str] = Field(default_factory=list, description="User must-have elements")
    age_group_details: Optional[str] = Field(None, max_length=200, description="Age group or special occasion info")


class BudgetItem(BaseModel):
    id: str
    category: str
    weight: float = Field(default=1.0, ge=0.0)
    percentage: float = Field(..., ge=0.0, le=100.0)
    allocated_amount: float = Field(..., ge=0.0)
    actual_spent: float = Field(default=0.0, ge=0.0)
    is_contingency: bool = False
    is_mandatory: bool = False
    notes: str = ""


class BudgetSummary(BaseModel):
    total_budget: float
    currency: str = "INR"
    contingency_percentage: float = Field(..., ge=5.0, le=15.0)
    items: List[BudgetItem]
    total_allocated: float
    total_actual_spent: float = 0.0
    is_over_budget: bool = False
    over_budget_amount: float = 0.0
    warnings: List[str] = Field(default_factory=list)


class TimelineTask(BaseModel):
    id: str
    milestone_phase: str
    title: str
    description: str = ""
    due_date: str
    owner: Literal["user", "vendor", "helper"] = "user"
    priority: Literal["high", "medium", "low"] = "medium"
    status: Literal["pending", "in_progress", "completed"] = "pending"
    is_high_risk: bool = False
    is_past_due: bool = False


class RunOfShowItem(BaseModel):
    id: str
    time_slot: str
    activity: str
    lead_person: str
    location: str
    notes: str = ""


class TimelinePlan(BaseModel):
    milestones: List[TimelineTask]
    run_of_show: List[RunOfShowItem]
    lead_time_days: int
    is_compressed: bool = False
    high_risk_count: int = 0


class VendorChecklistItem(BaseModel):
    id: str
    task_text: str
    item_type: Literal["question", "document", "deposit_date", "final_payment_date", "backup_plan"]
    is_completed: bool = False
    target_date: Optional[str] = None
    notes: str = ""


class VendorCategory(BaseModel):
    id: str
    category: str
    is_mandatory: bool
    vendor_name: str = ""
    contact_info: str = ""
    quote_amount: float = 0.0
    status: Literal["not_contacted", "quoted", "booked", "paid"] = "not_contacted"
    linked_budget_category: str
    checklist: List[VendorChecklistItem]
    backup_vendor: Optional[str] = None


class PersonalizedIdeaItem(BaseModel):
    id: str
    title: str
    description: str
    rationale: str
    budget_friendly_swap: str
    tags: List[str] = Field(default_factory=list)


class PersonalizedIdeasPlan(BaseModel):
    themes: List[PersonalizedIdeaItem] = Field(default_factory=list)
    decor: List[PersonalizedIdeaItem] = Field(default_factory=list)
    food_menu: List[PersonalizedIdeaItem] = Field(default_factory=list)
    activities: List[PersonalizedIdeaItem] = Field(default_factory=list)
    entertainment: List[PersonalizedIdeaItem] = Field(default_factory=list)
    return_gifts: List[PersonalizedIdeaItem] = Field(default_factory=list)


class FullEventPlan(BaseModel):
    event_id: str
    intake: EventIntake
    budget: BudgetSummary
    timeline: TimelinePlan
    vendors: List[VendorCategory]
    ideas: PersonalizedIdeasPlan
    created_at: str
    updated_at: str


class DashboardSummary(BaseModel):
    event_id: str
    title: str
    event_type: str
    days_left: int
    total_budget: float
    total_spent: float
    budget_used_percentage: float
    tasks_total: int
    tasks_completed: int
    tasks_completion_percentage: float
    vendors_total: int
    vendors_booked: int
    high_risk_tasks_count: int
    is_over_budget: bool
    currency: str


class ChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str
    tool_calls_executed: Optional[List[Dict[str, Any]]] = None


class ChatRequest(BaseModel):
    event_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    updated_plan: Optional[FullEventPlan] = None
    tools_executed: List[Dict[str, Any]] = Field(default_factory=list)


class BudgetAnalysis(BaseModel):
    total_budget: float
    total_allocated: float
    remaining_budget: float
    total_actual_spent: float
    highest_expense_category: str
    highest_expense_amount: float
    highest_expense_percentage: float
    potential_savings_categories: List[str]
    category_distribution: List[Dict[str, Any]]


class BudgetOptimizationRequest(BaseModel):
    user_prompt: str = Field(..., min_length=2, max_length=1000)


class CategoryOptimization(BaseModel):
    category: str
    original_amount: float
    original_percentage: float
    recommended_amount: float
    recommended_percentage: float
    savings: float
    percentage_change: float
    notes: str = ""


class OptimizationExplanation(BaseModel):
    where_money_saved: List[str]
    why_recommended: str
    expenses_preserved: List[str]
    total_saved_summary: str


class BudgetOptimizationResponse(BaseModel):
    event_id: str
    user_prompt: str
    engine_used: str  # "gemini" or "fallback_rule_engine"
    original_total_budget: float
    revised_total_budget: float
    total_savings: float
    currency: str
    categories: List[CategoryOptimization]
    explanation: OptimizationExplanation
    optimized_budget_summary: BudgetSummary


# =========================================================
# PHASE 2: SMART EXPENSE TRACKING SCHEMAS
# =========================================================

class ExpenseBase(BaseModel):
    expense_name: str = Field(..., min_length=1, max_length=150, description="Name or title of expense")
    category: str = Field(..., min_length=1, max_length=100, description="Budget category")
    amount: float = Field(..., gt=0.0, description="Amount spent, must be greater than zero")
    expense_date: str = Field(..., description="Date of expense in YYYY-MM-DD format")
    payment_status: Literal["Paid", "Pending"] = Field("Paid", description="Payment status")
    payment_method: Optional[str] = Field(None, max_length=50, description="Payment method: Credit Card, UPI, etc.")
    vendor_name: Optional[str] = Field(None, max_length=150, description="Associated vendor name")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes or receipt references")


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    expense_name: Optional[str] = Field(None, min_length=1, max_length=150)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    amount: Optional[float] = Field(None, gt=0.0)
    expense_date: Optional[str] = None
    payment_status: Optional[Literal["Paid", "Pending"]] = None
    payment_method: Optional[str] = None
    vendor_name: Optional[str] = None
    notes: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: str
    event_id: str
    expense_name: str
    category: str
    amount: float
    expense_date: str
    payment_status: Literal["Paid", "Pending"]
    payment_method: Optional[str] = None
    vendor_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class CategoryExpenseComparison(BaseModel):
    category: str
    planned_budget: float
    actual_spent: float
    remaining: float
    difference: float
    is_overspent: bool
    overspent_amount: float
    utilization_percentage: float


class BudgetAlert(BaseModel):
    level: Literal["warning", "danger", "info"]
    category: Optional[str] = None
    title: str
    message: str


class ExpenseTrackingSummary(BaseModel):
    event_id: str
    total_event_budget: float
    total_actual_spent: float
    remaining_budget: float
    budget_utilization_percentage: float
    is_over_budget: bool
    over_budget_amount: float
    currency: str
    categories: List[CategoryExpenseComparison]
    alerts: List[BudgetAlert]
    total_expenses_count: int
    paid_expenses_count: int
    pending_expenses_count: int
    highest_spending_category: str
    highest_spending_amount: float


# =========================================================
# PHASE 3: GUEST MANAGEMENT & RSVP SYSTEM SCHEMAS
# =========================================================

GuestCategoryType = Literal["Family", "Friends", "Relatives", "Colleagues", "VIP", "Others"]
InvitationStatusType = Literal["Not Sent", "Sent"]
RSVPStatusType = Literal["Pending", "Accepted", "Declined"]


class GuestBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=150, description="Full name of guest")
    email: Optional[str] = Field(None, max_length=150, description="Email address")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    category: GuestCategoryType = Field("Others", description="Guest category")
    plus_ones: int = Field(0, ge=0, le=50, description="Number of additional guests accompanying")
    invitation_status: InvitationStatusType = Field("Not Sent", description="Invitation sent status")
    rsvp_status: RSVPStatusType = Field("Pending", description="RSVP response status")
    special_requirements: Optional[str] = Field(None, max_length=255, description="Dietary or accessibility notes")
    notes: Optional[str] = Field(None, max_length=500, description="General organizer notes")


class GuestCreate(GuestBase):
    pass


class GuestUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=150)
    email: Optional[str] = None
    phone: Optional[str] = None
    category: Optional[GuestCategoryType] = None
    plus_ones: Optional[int] = Field(None, ge=0, le=50)
    invitation_status: Optional[InvitationStatusType] = None
    rsvp_status: Optional[RSVPStatusType] = None
    special_requirements: Optional[str] = None
    notes: Optional[str] = None


class GuestStatusUpdate(BaseModel):
    invitation_status: Optional[InvitationStatusType] = None
    rsvp_status: Optional[RSVPStatusType] = None


class GuestResponse(BaseModel):
    id: str
    event_id: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    category: str
    plus_ones: int
    invitation_status: str
    rsvp_status: str
    special_requirements: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class GuestRSVPSummary(BaseModel):
    event_id: str
    total_guests_invited: int
    total_invitations_sent: int
    total_invitations_pending: int
    confirmed_guests: int
    pending_responses: int
    declined_guests: int
    confirmed_plus_ones: int
    total_expected_attendance: int
    rsvp_response_rate: float
    acceptance_rate: float
    category_counts: Dict[str, int]
    rsvp_counts: Dict[str, int]
    invitation_counts: Dict[str, int]


class CSVImportPreviewRow(BaseModel):
    row_number: int
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    category: str = "Others"
    plus_ones: int = 0
    is_valid: bool = True
    is_duplicate: bool = False
    errors: List[str] = Field(default_factory=list)


class CSVImportPreviewRequest(BaseModel):
    csv_content: str = Field(..., description="Raw CSV string content")
    filename: Optional[str] = "guestlist.csv"


class CSVImportPreviewResponse(BaseModel):
    total_rows: int
    valid_rows_count: int
    duplicate_rows_count: int
    invalid_rows_count: int
    preview_rows: List[CSVImportPreviewRow]


class CSVImportConfirmRequest(BaseModel):
    rows: List[GuestCreate]


class CSVImportResult(BaseModel):
    imported_count: int
    skipped_count: int
    errors: List[str] = Field(default_factory=list)


# =========================================================
# PHASE 4: AI INVITATION GENERATOR SCHEMAS
# =========================================================

class InvitationTextComponents(BaseModel):
    personalized_greeting: str = Field(..., description="Salutation e.g. Dear Amit & Family / आदरणीय / સ્નેહી શ્રી")
    event_details: str = Field(..., description="Formatted date, time, venue, location")
    invitation_message: str = Field(..., description="Main celebration invitation body")
    closing_message: str = Field(..., description="Warm sign-off and host names")
    full_text: str = Field(..., description="Assembled complete text ready for copy or WhatsApp")


class InvitationVariation(BaseModel):
    variation_id: int
    variation_name: str
    components: InvitationTextComponents


class InvitationGenerateRequest(BaseModel):
    event_id: Optional[str] = None
    guest_id: Optional[str] = None
    event_type: str = Field("Wedding", description="Wedding, Birthday, Community, Corporate, Anniversary")
    event_name: str = Field(..., min_length=2, max_length=150, description="Title/name of the celebration")
    host_names: str = Field(..., min_length=2, max_length=150, description="Host or family names")
    event_date: str = Field(..., description="Date of the event")
    event_time: str = Field(..., description="Time of the event e.g. 7:00 PM onwards")
    venue: str = Field(..., min_length=2, max_length=150, description="Venue name")
    location: str = Field(..., min_length=2, max_length=150, description="City / address")
    additional_instructions: Optional[str] = Field(None, max_length=500, description="Dress code, theme, RSVP notes")
    language: Literal["English", "Hindi", "Gujarati"] = Field("English", description="Supported languages")
    style: Literal["Traditional", "Modern", "Elegant", "Minimalist", "Royal", "Fun and Casual"] = Field("Traditional", description="Invitation style")
    tone: Optional[str] = Field("Warm & Welcoming", max_length=100, description="Tone of voice")


class InvitationGenerateResponse(BaseModel):
    variations: List[InvitationVariation]
    language: str
    style: str
    model_used: str  # "gemini" or "fallback_multilingual_engine"


class InvitationDesignConfig(BaseModel):
    template_id: str = "traditional_indian_wedding"
    bg_theme: str = "gold_vermilion"
    bg_color: str = "#FFFDF9"
    primary_color: str = "#831843"
    text_color: str = "#1E293B"
    accent_color: str = "#D97706"
    font_family: Literal["serif", "sans", "cursive", "display"] = "serif"
    font_size: Literal["small", "medium", "large"] = "medium"
    border_style: Literal["ornate_gold", "double", "floral", "dashed", "minimal", "none"] = "ornate_gold"
    layout: Literal["centered", "split", "framed", "minimal"] = "centered"
    decorative_element: Literal["mandala_diya", "royal_crest", "floral_wreath", "confetti_stars", "geometric_badge", "none"] = "mandala_diya"


class InvitationCreateRequest(BaseModel):
    event_id: str
    guest_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=200)
    language: str = Field("English", description="English, Hindi, Gujarati")
    style: str = Field("Traditional")
    template_id: str = Field("traditional_indian_wedding")
    text_components: InvitationTextComponents
    design_config: InvitationDesignConfig


class InvitationResponse(BaseModel):
    id: str
    event_id: str
    guest_id: Optional[str] = None
    guest_name: Optional[str] = None
    title: str
    language: str
    style: str
    template_id: str
    text_components: InvitationTextComponents
    design_config: InvitationDesignConfig
    created_at: str
    updated_at: str


class InvitationPDFExportRequest(BaseModel):
    title: str
    language: str = "English"
    text_components: InvitationTextComponents
    design_config: InvitationDesignConfig
    event_details: Optional[Dict[str, Any]] = None


# =========================================================
# PHASE 5: AI-POWERED LOCAL VENDOR RECOMMENDATION & MANAGEMENT
# =========================================================

VendorCategoryType = Literal[
    "Photography",
    "Catering",
    "Decoration",
    "Venue",
    "Entertainment",
    "Makeup Artists",
    "Transportation",
    "Other Event Services",
]

BookingStatusType = Literal[
    "Shortlisted",
    "Contacted",
    "Negotiating",
    "Booked",
    "Cancelled",
]


class VendorBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Vendor business or professional name")
    category: str = Field(..., description="Service category")
    location: str = Field(..., min_length=2, max_length=100, description="City / Region in India")
    description: str = Field(..., min_length=10, description="Detailed profile and specialties")
    services_offered: List[str] = Field(default_factory=list, description="Specific service offerings")
    min_price: float = Field(0.0, ge=0.0, description="Starting package price")
    max_price: float = Field(0.0, ge=0.0, description="Comprehensive/Luxury package price")
    rating: float = Field(5.0, ge=1.0, le=5.0, description="Customer rating from 1.0 to 5.0")
    review_count: int = Field(0, ge=0, description="Number of customer reviews")
    experience_years: int = Field(1, ge=0, description="Years in industry")
    phone: str = Field(..., min_length=5, max_length=50, description="Contact phone / WhatsApp")
    email: str = Field(..., min_length=5, max_length=100, description="Business email")
    website: Optional[str] = Field(None, max_length=255, description="Portfolio or website link")
    portfolio_images: List[str] = Field(default_factory=list, description="Portfolio image URLs or showcases")
    is_verified: bool = Field(False, description="True for authentic directory entries, False for user-added")
    is_favorite: bool = Field(False, description="Favorited by user")


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    category: Optional[str] = None
    location: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, min_length=10)
    services_offered: Optional[List[str]] = None
    min_price: Optional[float] = Field(None, ge=0.0)
    max_price: Optional[float] = Field(None, ge=0.0)
    rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    review_count: Optional[int] = Field(None, ge=0)
    experience_years: Optional[int] = Field(None, ge=0)
    phone: Optional[str] = Field(None, min_length=5, max_length=50)
    email: Optional[str] = Field(None, min_length=5, max_length=100)
    website: Optional[str] = None
    portfolio_images: Optional[List[str]] = None
    is_favorite: Optional[bool] = None


class VendorResponse(VendorBase):
    id: str
    created_at: str
    updated_at: str


class VendorRecommendationQuery(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language prompt e.g. Find wedding photographers in Ahmedabad under 30000")
    category: Optional[str] = None
    location: Optional[str] = None
    max_budget: Optional[float] = None
    event_id: Optional[str] = None


class VendorRecommendationItem(BaseModel):
    vendor: VendorResponse
    match_score: float = Field(..., description="Match relevance score 0-100")
    match_reason: str = Field(..., description="Explanation why this vendor matches requirements")
    is_within_budget: bool = True


class VendorRecommendationResponse(BaseModel):
    query: str
    parsed_criteria: Dict[str, Any]
    recommendations: List[VendorRecommendationItem]
    total_matching: int
    search_broadened_message: Optional[str] = None


class VendorComparisonRequest(BaseModel):
    vendor_ids: List[str] = Field(..., min_length=2, max_length=3, description="2 to 3 vendor IDs to compare")


class VendorProsCons(BaseModel):
    vendor_id: str
    vendor_name: str
    pros: List[str]
    cons: List[str]


class VendorComparisonResponse(BaseModel):
    vendors: List[VendorResponse]
    best_budget_option: str
    best_rated_option: str
    best_overall_match: str
    comparison_summary: str
    vendor_evaluations: List[VendorProsCons]


class EventVendorBookingCreate(BaseModel):
    event_id: str
    vendor_id: str
    booking_status: BookingStatusType = "Shortlisted"
    agreed_price: float = Field(0.0, ge=0.0)
    advance_payment: float = Field(0.0, ge=0.0)
    booking_date: Optional[str] = None
    notes: Optional[str] = None


class EventVendorBookingUpdate(BaseModel):
    booking_status: Optional[BookingStatusType] = None
    agreed_price: Optional[float] = Field(None, ge=0.0)
    advance_payment: Optional[float] = Field(None, ge=0.0)
    booking_date: Optional[str] = None
    notes: Optional[str] = None


class EventVendorBookingResponse(BaseModel):
    id: str
    event_id: str
    vendor_id: str
    vendor: VendorResponse
    booking_status: str
    agreed_price: float
    advance_payment: float
    remaining_payment: float
    booking_date: str
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class VendorCategorySpending(BaseModel):
    category: str
    planned_budget: float
    agreed_cost: float
    advance_paid: float
    remaining_payment: float


class VendorAnalyticsSummary(BaseModel):
    event_id: Optional[str] = None
    total_directory_vendors: int
    shortlisted_count: int
    booked_count: int
    negotiating_count: int
    total_agreed_cost: float
    total_advance_paid: float
    total_remaining_payment: float
    category_counts: Dict[str, int]
    booking_status_counts: Dict[str, int]
    category_spending: List[VendorCategorySpending]


class RecordAdvanceExpenseRequest(BaseModel):
    booking_id: str
    payment_method: Optional[str] = "UPI"
    notes: Optional[str] = None


# ============================================================================
# PHASE 6: AI WEATHER-AWARE EVENT PLANNER SCHEMAS
# ============================================================================

class LocationGeoResult(BaseModel):
    name: str
    latitude: float
    longitude: float
    country: Optional[str] = "India"
    admin1: Optional[str] = None
    timezone: Optional[str] = "Asia/Kolkata"


class HourlyWeatherPoint(BaseModel):
    time: str
    temperature: float
    apparent_temperature: float
    rain_probability: float
    precipitation: float
    wind_speed: float
    humidity: float
    weather_code: int
    condition_text: str


class DailyWeatherPoint(BaseModel):
    date: str
    temp_max: float
    temp_min: float
    apparent_temp_max: float
    apparent_temp_min: float
    rain_probability_max: float
    precipitation_sum: float
    wind_speed_max: float
    humidity_mean: float
    weather_code: int
    condition_text: str
    sunrise: Optional[str] = None
    sunset: Optional[str] = None


class WeatherRiskFactor(BaseModel):
    category: str
    risk_level: Literal["Low", "Moderate", "High"]
    value_display: str
    threshold_note: str
    reason: str


class WeatherRiskAssessment(BaseModel):
    overall_risk: Literal["Low", "Moderate", "High"]
    risk_summary: str
    factors: List[WeatherRiskFactor]


class SmartWeatherRecommendation(BaseModel):
    id: str
    category: str
    priority: Literal["Critical", "Recommended", "Advisory"]
    title: str
    description: str
    action_item: str
    suggested_timeline_phase: str


class WeatherReportResponse(BaseModel):
    event_id: Optional[str] = None
    location: str
    latitude: float
    longitude: float
    target_date: str
    is_forecast: bool
    data_type_label: str  # "Live Meteorological Forecast" or "Historical Climate Reference – Not an Actual Forecast"
    retrieved_at: str
    data_source: str = "Open-Meteo Weather API"
    day_summary: DailyWeatherPoint
    daily_forecast: List[DailyWeatherPoint] = []
    hourly_forecast: List[HourlyWeatherPoint] = []
    risk_assessment: WeatherRiskAssessment
    recommendations: List[SmartWeatherRecommendation] = []


class WeatherAssistantQuery(BaseModel):
    question: str = Field(..., min_length=2, description="Natural language question e.g. Is this date suitable for an outdoor wedding?")
    event_id: Optional[str] = None
    location: str
    target_date: str
    event_type: Optional[str] = "wedding"


class WeatherAssistantResponse(BaseModel):
    answer: str
    data_grounding: str
    is_forecast_based: bool
    key_suggestions: List[str] = []


class SaveTimelineMitigationsRequest(BaseModel):
    task_titles: List[str] = Field(..., min_length=1, description="List of mitigation task titles to append to timeline")
    phase: Optional[str] = "Week Of Event"
    priority: Optional[Literal["high", "medium", "low"]] = "high"


class SaveTimelineMitigationsResponse(BaseModel):
    added_tasks: List[TimelineTask]
    skipped_duplicates: List[str]
    total_milestones: int


# =============================================================
# Phase 7: Authentication & User Management Schemas
# =============================================================

class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=150, description="Valid user email address")
    password: str = Field(..., min_length=6, description="User password (min 6 characters)")
    full_name: str = Field(..., min_length=2, max_length=150, description="Full display name")


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# =============================================================
# Phase 7: Executive Command Center & Dashboard Schemas
# =============================================================

class ExecutiveKpiMetrics(BaseModel):
    total_events: int
    upcoming_events: int
    total_planned_budget: float
    total_actual_expenses: float
    remaining_budget: float
    total_confirmed_guests: int
    pending_rsvps: int
    booked_vendors: int


class UpcomingEventItem(BaseModel):
    event_id: str
    title: str
    event_type: str
    date: str
    city: str
    days_left: int
    total_budget: float
    actual_spent: float
    guest_count: int
    weather_risk_level: str = "Low"


class RecentActivityItem(BaseModel):
    id: str
    activity_type: str  # "expense", "rsvp", "booking", "weather", "event"
    title: str
    description: str
    timestamp: str
    badge: str


class BudgetUtilizationCategory(BaseModel):
    category: str
    allocated: float
    spent: float
    percentage_used: float


class GuestRsvpBreakdown(BaseModel):
    confirmed: int
    declined: int
    pending: int
    total_invited: int
    total_attending: int  # confirmed + plus ones


class VendorSummaryStats(BaseModel):
    booked_count: int
    shortlisted_count: int
    total_contracted_amount: float
    advance_paid_amount: float


class ExecutiveWeatherAlert(BaseModel):
    event_id: str
    event_title: str
    location: str
    date: str
    overall_risk_level: str
    primary_concern: str
    recommended_action: str


class ExecutiveDashboardResponse(BaseModel):
    kpis: ExecutiveKpiMetrics
    upcoming_events: List[UpcomingEventItem]
    recent_activities: List[RecentActivityItem]
    budget_utilization: List[BudgetUtilizationCategory]
    guest_rsvp_breakdown: GuestRsvpBreakdown
    vendor_summary: VendorSummaryStats
    next_event_weather_alert: Optional[ExecutiveWeatherAlert] = None
