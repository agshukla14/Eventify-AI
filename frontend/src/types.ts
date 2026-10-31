export type EventType = 'wedding' | 'birthday' | 'community';

export interface EventIntake {
  event_type: EventType;
  title: string;
  date: string;
  city: string;
  guest_count: number;
  total_budget: number;
  currency: string;
  theme_style?: string;
  cultural_preferences?: string;
  dietary_preferences: string[];
  must_haves: string[];
  age_group_details?: string;
}

export interface BudgetItem {
  id: string;
  category: string;
  weight: number;
  percentage: number;
  allocated_amount: number;
  actual_spent: number;
  is_contingency: boolean;
  is_mandatory: boolean;
  notes: string;
}

export interface BudgetSummary {
  total_budget: number;
  currency: string;
  contingency_percentage: number;
  items: BudgetItem[];
  total_allocated: number;
  total_actual_spent: number;
  is_over_budget: boolean;
  over_budget_amount: number;
  warnings: string[];
}

export interface TimelineTask {
  id: string;
  milestone_phase: string;
  title: string;
  description: string;
  due_date: string;
  owner: 'user' | 'vendor' | 'helper';
  priority: 'high' | 'medium' | 'low';
  status: 'pending' | 'in_progress' | 'completed';
  is_high_risk: boolean;
  is_past_due: boolean;
}

export interface RunOfShowItem {
  id: string;
  time_slot: string;
  activity: string;
  lead_person: string;
  location: string;
  notes: string;
}

export interface TimelinePlan {
  milestones: TimelineTask[];
  run_of_show: RunOfShowItem[];
  lead_time_days: number;
  is_compressed: boolean;
  high_risk_count: number;
}

export interface VendorChecklistItem {
  id: string;
  task_text: string;
  item_type: 'question' | 'document' | 'deposit_date' | 'final_payment_date' | 'backup_plan';
  is_completed: boolean;
  target_date?: string;
  notes?: string;
}

export interface VendorCategory {
  id: string;
  category: string;
  is_mandatory: boolean;
  vendor_name: string;
  contact_info: string;
  quote_amount: number;
  status: 'not_contacted' | 'quoted' | 'booked' | 'paid';
  linked_budget_category: string;
  checklist: VendorChecklistItem[];
  backup_vendor?: string;
}

export interface PersonalizedIdeaItem {
  id: string;
  title: string;
  description: string;
  rationale: string;
  budget_friendly_swap: string;
  tags: string[];
}

export interface PersonalizedIdeasPlan {
  themes: PersonalizedIdeaItem[];
  decor: PersonalizedIdeaItem[];
  food_menu: PersonalizedIdeaItem[];
  activities: PersonalizedIdeaItem[];
  entertainment: PersonalizedIdeaItem[];
  return_gifts: PersonalizedIdeaItem[];
}

export interface FullEventPlan {
  event_id: string;
  intake: EventIntake;
  budget: BudgetSummary;
  timeline: TimelinePlan;
  vendors: VendorCategory[];
  ideas: PersonalizedIdeasPlan;
  created_at: string;
  updated_at: string;
}

export interface DashboardSummary {
  event_id: string;
  title: string;
  event_type: EventType;
  days_left: number;
  total_budget: number;
  total_spent: number;
  budget_used_percentage: number;
  tasks_total: number;
  tasks_completed: number;
  tasks_completion_percentage: number;
  vendors_total: number;
  vendors_booked: number;
  high_risk_tasks_count: number;
  is_over_budget: boolean;
  currency: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  tool_calls_executed?: Record<string, any>[];
}

export interface ChatResponse {
  reply: string;
  updated_plan?: FullEventPlan;
  tools_executed: Record<string, any>[];
}

export interface CategoryDistributionItem {
  category: string;
  allocated_amount: number;
  percentage: number;
  actual_spent: number;
  is_contingency: boolean;
}

export interface BudgetAnalysis {
  total_budget: number;
  total_allocated: number;
  remaining_budget: number;
  total_actual_spent: number;
  highest_expense_category: string;
  highest_expense_amount: number;
  highest_expense_percentage: number;
  potential_savings_categories: string[];
  category_distribution: CategoryDistributionItem[];
}

export interface CategoryOptimization {
  category: string;
  original_amount: number;
  original_percentage: number;
  recommended_amount: number;
  recommended_percentage: number;
  savings: number;
  percentage_change: number;
  notes: string;
}

export interface OptimizationExplanation {
  where_money_saved: string[];
  why_recommended: string;
  expenses_preserved: string[];
  total_saved_summary: string;
}

export interface BudgetOptimizationResponse {
  event_id: string;
  user_prompt: string;
  engine_used: 'gemini' | 'fallback_rule_engine' | string;
  original_total_budget: number;
  revised_total_budget: number;
  total_savings: number;
  currency: string;
  categories: CategoryOptimization[];
  explanation: OptimizationExplanation;
  optimized_budget_summary: BudgetSummary;
}

// =========================================================
// PHASE 2: SMART EXPENSE TRACKING TYPES
// =========================================================

export type PaymentStatus = 'Paid' | 'Pending';

export interface ExpenseItem {
  id: string;
  event_id: string;
  expense_name: string;
  category: string;
  amount: number;
  expense_date: string;
  payment_status: PaymentStatus;
  payment_method?: string;
  vendor_name?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ExpenseFormData {
  expense_name: string;
  category: string;
  amount: number;
  expense_date: string;
  payment_status: PaymentStatus;
  payment_method?: string;
  vendor_name?: string;
  notes?: string;
}

export interface CategoryExpenseComparison {
  category: string;
  planned_budget: number;
  actual_spent: number;
  remaining: number;
  difference: number;
  is_overspent: boolean;
  overspent_amount: number;
  utilization_percentage: number;
}

export interface BudgetAlert {
  level: 'warning' | 'danger' | 'info';
  category?: string;
  title: string;
  message: string;
}

export interface ExpenseTrackingSummary {
  event_id: string;
  total_event_budget: number;
  total_actual_spent: number;
  remaining_budget: number;
  budget_utilization_percentage: number;
  is_over_budget: boolean;
  over_budget_amount: number;
  currency: string;
  categories: CategoryExpenseComparison[];
  alerts: BudgetAlert[];
  total_expenses_count: number;
  paid_expenses_count: number;
  pending_expenses_count: number;
  highest_spending_category: string;
  highest_spending_amount: number;
}

// =========================================================
// PHASE 3: GUEST MANAGEMENT & RSVP SYSTEM TYPES
// =========================================================

export type GuestCategory = 'Family' | 'Friends' | 'Relatives' | 'Colleagues' | 'VIP' | 'Others';
export type InvitationStatus = 'Not Sent' | 'Sent';
export type RSVPStatus = 'Pending' | 'Accepted' | 'Declined';

export interface GuestItem {
  id: string;
  event_id: string;
  full_name: string;
  email?: string;
  phone?: string;
  category: GuestCategory;
  plus_ones: number;
  invitation_status: InvitationStatus;
  rsvp_status: RSVPStatus;
  special_requirements?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface GuestFormData {
  full_name: string;
  email?: string;
  phone?: string;
  category: GuestCategory;
  plus_ones: number;
  invitation_status: InvitationStatus;
  rsvp_status: RSVPStatus;
  special_requirements?: string;
  notes?: string;
}

export interface GuestRSVPSummary {
  event_id: string;
  total_guests_invited: number;
  total_invitations_sent: number;
  total_invitations_pending: number;
  confirmed_guests: number;
  pending_responses: number;
  declined_guests: number;
  confirmed_plus_ones: number;
  total_expected_attendance: number;
  rsvp_response_rate: number;
  acceptance_rate: number;
  category_counts: Record<string, number>;
  rsvp_counts: Record<string, number>;
  invitation_counts: Record<string, number>;
}

export interface CSVImportPreviewRow {
  row_number: number;
  full_name: string;
  email?: string;
  phone?: string;
  category: GuestCategory;
  plus_ones: number;
  is_valid: boolean;
  is_duplicate: boolean;
  errors: string[];
}

export interface CSVImportPreviewResponse {
  total_rows: number;
  valid_rows_count: number;
  duplicate_rows_count: number;
  invalid_rows_count: number;
  preview_rows: CSVImportPreviewRow[];
}

export interface CSVImportResult {
  imported_count: number;
  skipped_count: number;
  errors: string[];
}

// =========================================================
// PHASE 4: AI INVITATION GENERATOR TYPES
// =========================================================

export type InvitationLanguage = 'English' | 'Hindi' | 'Gujarati';
export type InvitationStyle = 'Traditional' | 'Modern' | 'Elegant' | 'Minimalist' | 'Royal' | 'Fun and Casual';

export interface InvitationTextComponents {
  personalized_greeting: string;
  event_details: string;
  invitation_message: string;
  closing_message: string;
  full_text: string;
}

export interface InvitationVariation {
  variation_id: number;
  variation_name: string;
  components: InvitationTextComponents;
}

export interface InvitationGenerateRequest {
  event_id?: string;
  guest_id?: string;
  event_type: string;
  event_name: string;
  host_names: string;
  event_date: string;
  event_time: string;
  venue: string;
  location: string;
  additional_instructions?: string;
  language: InvitationLanguage;
  style: InvitationStyle;
  tone?: string;
}

export interface InvitationGenerateResponse {
  variations: InvitationVariation[];
  language: string;
  style: string;
  model_used: string;
}

export interface InvitationDesignConfig {
  template_id: string;
  bg_theme: string;
  bg_color: string;
  primary_color: string;
  text_color: string;
  accent_color: string;
  font_family: 'serif' | 'sans' | 'cursive' | 'display';
  font_size: 'small' | 'medium' | 'large';
  border_style: 'ornate_gold' | 'double' | 'floral' | 'dashed' | 'minimal' | 'none';
  layout: 'centered' | 'split' | 'framed' | 'minimal';
  decorative_element: 'mandala_diya' | 'royal_crest' | 'floral_wreath' | 'confetti_stars' | 'geometric_badge' | 'none';
}

export interface InvitationCreateRequest {
  event_id: string;
  guest_id?: string;
  title: string;
  language: string;
  style: string;
  template_id: string;
  text_components: InvitationTextComponents;
  design_config: InvitationDesignConfig;
}

export interface InvitationItem {
  id: string;
  event_id: string;
  guest_id?: string;
  guest_name?: string;
  title: string;
  language: string;
  style: string;
  template_id: string;
  text_components: InvitationTextComponents;
  design_config: InvitationDesignConfig;
  created_at: string;
  updated_at: string;
}

export interface InvitationTemplate {
  id: string;
  template_id: string;
  name: string;
  category: string;
  bg_theme: string;
  bg_color: string;
  primary_color: string;
  text_color: string;
  accent_color: string;
  font_family: 'serif' | 'sans' | 'cursive' | 'display';
  font_size: 'small' | 'medium' | 'large';
  border_style: 'ornate_gold' | 'double' | 'floral' | 'dashed' | 'minimal' | 'none';
  layout: 'centered' | 'split' | 'framed' | 'minimal';
  decorative_element: 'mandala_diya' | 'royal_crest' | 'floral_wreath' | 'confetti_stars' | 'geometric_badge' | 'none';
}

// =========================================================
// PHASE 5: LOCAL VENDOR DISCOVERY & MANAGEMENT TYPES
// =========================================================

export type VendorCategoryType =
  | 'Photography'
  | 'Catering'
  | 'Decoration'
  | 'Venue'
  | 'Entertainment'
  | 'Makeup Artists'
  | 'Transportation'
  | 'Other Event Services';

export type BookingStatusType =
  | 'Shortlisted'
  | 'Contacted'
  | 'Negotiating'
  | 'Booked'
  | 'Cancelled';

export interface VendorItem {
  id: string;
  name: string;
  category: VendorCategoryType | string;
  location: string;
  description: string;
  services_offered: string[];
  min_price: number;
  max_price: number;
  rating: number;
  review_count: number;
  experience_years: number;
  phone: string;
  email: string;
  website?: string;
  portfolio_images: string[];
  is_verified: boolean;
  is_favorite: boolean;
  created_at: string;
  updated_at: string;
}

export interface VendorFormData {
  name: string;
  category: string;
  location: string;
  description: string;
  services_offered: string[];
  min_price: number;
  max_price: number;
  rating: number;
  review_count: number;
  experience_years: number;
  phone: string;
  email: string;
  website?: string;
  portfolio_images: string[];
}

export interface VendorRecommendationItem {
  vendor: VendorItem;
  match_score: number;
  match_reason: string;
  is_within_budget: boolean;
}

export interface VendorRecommendationResponse {
  query: string;
  parsed_criteria: {
    category?: string;
    location?: string;
    max_budget?: number;
  };
  recommendations: VendorRecommendationItem[];
  total_matching: number;
  search_broadened_message?: string;
}

export interface VendorProsCons {
  vendor_id: string;
  vendor_name: string;
  pros: string[];
  cons: string[];
}

export interface VendorComparisonResponse {
  vendors: VendorItem[];
  best_budget_option: string;
  best_rated_option: string;
  best_overall_match: string;
  comparison_summary: string;
  vendor_evaluations: VendorProsCons[];
}

export interface EventVendorBookingItem {
  id: string;
  event_id: string;
  vendor_id: string;
  vendor: VendorItem;
  booking_status: BookingStatusType;
  agreed_price: number;
  advance_payment: number;
  remaining_payment: number;
  booking_date: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface VendorCategorySpending {
  category: string;
  planned_budget: number;
  agreed_cost: number;
  advance_paid: number;
  remaining_payment: number;
}

export interface VendorAnalyticsSummary {
  event_id?: string;
  total_directory_vendors: number;
  shortlisted_count: number;
  booked_count: number;
  negotiating_count: number;
  total_agreed_cost: number;
  total_advance_paid: number;
  total_remaining_payment: number;
  category_counts: Record<string, number>;
  booking_status_counts: Record<string, number>;
  category_spending: VendorCategorySpending[];
}

// =========================================================
// PHASE 6: AI WEATHER-AWARE EVENT PLANNER TYPES
// =========================================================

export type WeatherRiskLevel = 'Low' | 'Moderate' | 'High';

export interface LocationGeoResult {
  name: string;
  latitude: number;
  longitude: number;
  country?: string;
  admin1?: string;
  timezone?: string;
}

export interface HourlyWeatherPoint {
  time: string;
  temperature: number;
  apparent_temperature: number;
  rain_probability: number;
  precipitation: number;
  wind_speed: number;
  humidity: number;
  weather_code: number;
  condition_text: string;
}

export interface DailyWeatherPoint {
  date: string;
  temp_max: number;
  temp_min: number;
  apparent_temp_max: number;
  apparent_temp_min: number;
  rain_probability_max: number;
  precipitation_sum: number;
  wind_speed_max: number;
  humidity_mean: number;
  weather_code: number;
  condition_text: string;
  sunrise?: string;
  sunset?: string;
}

export interface WeatherRiskFactor {
  category: string;
  risk_level: WeatherRiskLevel;
  value_display: string;
  threshold_note: string;
  reason: string;
}

export interface WeatherRiskAssessment {
  overall_risk: WeatherRiskLevel;
  risk_summary: string;
  factors: WeatherRiskFactor[];
}

export interface SmartWeatherRecommendation {
  id: string;
  category: string;
  priority: 'Critical' | 'Recommended' | 'Advisory';
  title: string;
  description: string;
  action_item: string;
  suggested_timeline_phase: string;
}

export interface WeatherReportResponse {
  event_id?: string;
  location: string;
  latitude: number;
  longitude: number;
  target_date: string;
  is_forecast: boolean;
  data_type_label: string;
  retrieved_at: string;
  data_source: string;
  day_summary: DailyWeatherPoint;
  daily_forecast: DailyWeatherPoint[];
  hourly_forecast: HourlyWeatherPoint[];
  risk_assessment: WeatherRiskAssessment;
  recommendations: SmartWeatherRecommendation[];
}

export interface WeatherAssistantQuery {
  question: string;
  event_id?: string;
  location: string;
  target_date: string;
  event_type?: string;
}

export interface WeatherAssistantResponse {
  answer: string;
  data_grounding: string;
  is_forecast_based: boolean;
  key_suggestions: string[];
}

export interface SaveTimelineMitigationsRequest {
  task_titles: string[];
  phase?: string;
  priority?: 'high' | 'medium' | 'low';
}

export interface SaveTimelineMitigationsResponse {
  added_tasks: TimelineTask[];
  skipped_duplicates: string[];
  total_milestones: number;
}

// =========================================================
// PHASE 7: AUTHENTICATION & USER MANAGEMENT
// =========================================================

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

// =========================================================
// PHASE 7: EXECUTIVE DASHBOARD & SAAS COMMAND CENTER
// =========================================================

export interface ExecutiveKpiMetrics {
  total_events: number;
  upcoming_events: number;
  total_planned_budget: number;
  total_actual_expenses: number;
  remaining_budget: number;
  total_confirmed_guests: number;
  pending_rsvps: number;
  booked_vendors: number;
}

export interface UpcomingEventItem {
  event_id: string;
  title: string;
  event_type: string;
  date: string;
  city: string;
  days_left: number;
  total_budget: number;
  actual_spent: number;
  guest_count: number;
  weather_risk_level: string;
}

export interface RecentActivityItem {
  id: string;
  activity_type: 'expense' | 'rsvp' | 'booking' | 'weather' | 'event' | string;
  title: string;
  description: string;
  timestamp: string;
  badge: string;
}

export interface BudgetUtilizationCategory {
  category: string;
  allocated: number;
  spent: number;
  percentage_used: number;
}

export interface GuestRsvpBreakdown {
  confirmed: number;
  declined: number;
  pending: number;
  total_invited: number;
  total_attending: number;
}

export interface VendorSummaryStats {
  booked_count: number;
  shortlisted_count: number;
  total_contracted_amount: number;
  advance_paid_amount: number;
}

export interface ExecutiveWeatherAlert {
  event_id: string;
  event_title: string;
  location: string;
  date: string;
  overall_risk_level: string;
  primary_concern: string;
  recommended_action: string;
}

export interface ExecutiveDashboardResponse {
  kpis: ExecutiveKpiMetrics;
  upcoming_events: UpcomingEventItem[];
  recent_activities: RecentActivityItem[];
  budget_utilization: BudgetUtilizationCategory[];
  guest_rsvp_breakdown: GuestRsvpBreakdown;
  vendor_summary: VendorSummaryStats;
  next_event_weather_alert?: ExecutiveWeatherAlert | null;
}
