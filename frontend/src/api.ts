import {
  EventIntake,
  FullEventPlan,
  BudgetItem,
  DashboardSummary,
  ChatResponse,
  ChatMessage,
  BudgetAnalysis,
  BudgetOptimizationResponse,
  ExpenseItem,
  ExpenseFormData,
  ExpenseTrackingSummary,
  GuestItem,
  GuestFormData,
  GuestRSVPSummary,
  CSVImportPreviewResponse,
  CSVImportResult,
  InvitationGenerateRequest,
  InvitationGenerateResponse,
  InvitationCreateRequest,
  InvitationItem,
  InvitationTemplate,
  VendorItem,
  VendorFormData,
  VendorRecommendationResponse,
  VendorComparisonResponse,
  EventVendorBookingItem,
  VendorAnalyticsSummary,
  LocationGeoResult,
  WeatherReportResponse,
  WeatherAssistantQuery,
  WeatherAssistantResponse,
  SaveTimelineMitigationsRequest,
  SaveTimelineMitigationsResponse,
  User,
  TokenResponse,
  LoginRequest,
  RegisterRequest,
  RegisterResponse,
  ExecutiveDashboardResponse,
} from './types';

const API_BASE = '/api';

// =========================================================
// AUTHENTICATION UTILITIES & HTTP CLIENT INTERCEPTOR
// =========================================================

export function getStoredToken(): string | null {
  return localStorage.getItem('eventify_token');
}

export function setStoredToken(token: string): void {
  localStorage.setItem('eventify_token', token);
}

export function removeStoredToken(): void {
  localStorage.removeItem('eventify_token');
}

export function getAuthHeaders(): Record<string, string> {
  const token = getStoredToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export interface ApiFetchOptions extends RequestInit {
  skipAuth?: boolean;
}

/**
 * Centralized authenticated fetch wrapper.
 * Automatically attaches Authorization Bearer token to protected API requests,
 * defaults to Content-Type: application/json for JSON payload requests,
 * and preserves custom headers and request options.
 */
export async function apiFetch(
  endpoint: string,
  options: ApiFetchOptions = {}
): Promise<Response> {
  const { skipAuth, headers: optHeaders, ...restOptions } = options;
  const headers: Record<string, string> = {};

  if (restOptions.body && typeof restOptions.body === 'string') {
    headers['Content-Type'] = 'application/json';
  }

  if (!skipAuth) {
    const token = getStoredToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  if (optHeaders) {
    if (optHeaders instanceof Headers) {
      optHeaders.forEach((value, key) => {
        headers[key] = value;
      });
    } else if (Array.isArray(optHeaders)) {
      optHeaders.forEach(([key, value]) => {
        headers[key] = value;
      });
    } else {
      Object.assign(headers, optHeaders);
    }
  }

  const url =
    endpoint.startsWith('http://') || endpoint.startsWith('https://')
      ? endpoint
      : `${API_BASE}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  return fetch(url, {
    ...restOptions,
    headers,
  });
}

/**
 * Triggers an authenticated browser file download (e.g. For PDFs / CSVs)
 * via fetch and Blob URL, ensuring Authorization headers are transmitted.
 */
export async function downloadFileWithAuth(url: string, filename: string): Promise<void> {
  const res = await apiFetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to download file' }));
    throw new Error(err.detail || 'Failed to download file');
  }
  const blob = await res.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(blobUrl);
}

// =========================================================
// PHASE 1: CORE CELEBRATION PLANNER API CLIENT
// =========================================================

export async function fetchHealth() {
  const res = await apiFetch('/health', { skipAuth: true });
  return res.json();
}

export async function createEvent(intake: EventIntake): Promise<FullEventPlan> {
  const res = await apiFetch('/events', {
    method: 'POST',
    body: JSON.stringify(intake),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create plan' }));
    throw new Error(err.detail || 'Failed to create plan');
  }
  return res.json();
}

export async function listEvents(): Promise<DashboardSummary[]> {
  const res = await apiFetch('/events');
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch events' }));
    throw new Error(err.detail || 'Failed to fetch events');
  }
  return res.json();
}

export async function getEvent(eventId: string): Promise<FullEventPlan> {
  const res = await apiFetch(`/events/${eventId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch event plan' }));
    throw new Error(err.detail || 'Failed to fetch event plan');
  }
  return res.json();
}

export async function updateEvent(eventId: string, plan: FullEventPlan): Promise<FullEventPlan> {
  const res = await apiFetch(`/events/${eventId}`, {
    method: 'PUT',
    body: JSON.stringify(plan),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update event plan' }));
    throw new Error(err.detail || 'Failed to update event plan');
  }
  return res.json();
}

export async function deleteEvent(eventId: string): Promise<void> {
  const res = await apiFetch(`/events/${eventId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to delete event' }));
    throw new Error(err.detail || 'Failed to delete event');
  }
}

export async function sendChatMessage(eventId: string, message: string): Promise<ChatResponse> {
  const res = await apiFetch('/chat', {
    method: 'POST',
    body: JSON.stringify({ event_id: eventId, message }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to send chat message' }));
    throw new Error(err.detail || 'Failed to send chat message');
  }
  return res.json();
}

export async function getChatHistory(eventId: string): Promise<ChatMessage[]> {
  const res = await apiFetch(`/chat/${eventId}/history`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch chat history' }));
    throw new Error(err.detail || 'Failed to fetch chat history');
  }
  return res.json();
}

export function getExportCsvUrl(eventId: string): string {
  const token = getStoredToken();
  return token
    ? `${API_BASE}/events/${eventId}/export/csv?token=${encodeURIComponent(token)}`
    : `${API_BASE}/events/${eventId}/export/csv`;
}

export function getExportPdfUrl(eventId: string): string {
  const token = getStoredToken();
  return token
    ? `${API_BASE}/events/${eventId}/export/pdf?token=${encodeURIComponent(token)}`
    : `${API_BASE}/events/${eventId}/export/pdf`;
}

export async function getBudgetAnalysis(eventId: string): Promise<BudgetAnalysis> {
  const res = await apiFetch(`/events/${eventId}/budget-analysis`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch budget analysis' }));
    throw new Error(err.detail || 'Failed to fetch budget analysis');
  }
  return res.json();
}

export async function optimizeBudget(
  eventId: string,
  userPrompt: string,
  protectedCategories?: string[]
): Promise<BudgetOptimizationResponse> {
  const res = await apiFetch(`/events/${eventId}/optimize-budget`, {
    method: 'POST',
    body: JSON.stringify({ user_prompt: userPrompt, protected_categories: protectedCategories || [] }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to optimize budget' }));
    throw new Error(err.detail || 'Failed to optimize budget');
  }
  return res.json();
}

export async function getCategoryAnalysis(eventId: string): Promise<any> {
  const res = await apiFetch(`/events/${eventId}/category-analysis`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch category analysis' }));
    throw new Error(err.detail || 'Failed to fetch category analysis');
  }
  return res.json();
}

export async function normalizeCategories(
  eventId: string,
  approvedCanonicalMerges?: string[]
): Promise<FullEventPlan> {
  const res = await apiFetch(`/events/${eventId}/normalize-categories`, {
    method: 'POST',
    body: JSON.stringify({ approved_canonical_merges: approvedCanonicalMerges || null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to normalize categories' }));
    throw new Error(err.detail || 'Failed to normalize categories');
  }
  return res.json();
}

export async function adjustBudgetSpent(
  eventId: string,
  category: string,
  targetSpent: number,
  notes?: string
): Promise<FullEventPlan> {
  const res = await apiFetch(`/events/${eventId}/budget/adjust-spent`, {
    method: 'POST',
    body: JSON.stringify({
      category,
      target_spent: targetSpent,
      notes,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to adjust spending' }));
    throw new Error(err.detail || 'Failed to adjust spending');
  }
  return res.json();
}

export async function updateCategoryProtection(
  eventId: string,
  itemId: string,
  data: { is_protected?: boolean; classification?: string }
): Promise<BudgetItem> {
  const res = await apiFetch(`/events/${eventId}/categories/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update category protection' }));
    throw new Error(err.detail || 'Failed to update category protection');
  }
  return res.json();
}

// =========================================================
// PHASE 2: SMART EXPENSE TRACKING API CLIENT
// =========================================================

export async function createExpense(
  eventId: string,
  data: ExpenseFormData
): Promise<ExpenseItem> {
  const res = await apiFetch(`/events/${eventId}/expenses`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create expense' }));
    throw new Error(err.detail || 'Failed to create expense');
  }
  return res.json();
}

export async function getExpenses(
  eventId: string,
  filters?: {
    category?: string;
    payment_status?: string;
    search?: string;
    start_date?: string;
    end_date?: string;
  }
): Promise<ExpenseItem[]> {
  const params = new URLSearchParams();
  if (filters?.category && filters.category !== 'all') {
    params.append('category', filters.category);
  }
  if (filters?.payment_status && filters.payment_status !== 'all') {
    params.append('payment_status', filters.payment_status);
  }
  if (filters?.search) {
    params.append('search', filters.search);
  }
  if (filters?.start_date) {
    params.append('start_date', filters.start_date);
  }
  if (filters?.end_date) {
    params.append('end_date', filters.end_date);
  }

  const queryString = params.toString() ? `?${params.toString()}` : '';
  const res = await apiFetch(`/events/${eventId}/expenses${queryString}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch expenses' }));
    throw new Error(err.detail || 'Failed to fetch expenses');
  }
  return res.json();
}

export async function getExpenseSummary(
  eventId: string
): Promise<ExpenseTrackingSummary> {
  const res = await apiFetch(`/events/${eventId}/expenses/summary`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch expense summary' }));
    throw new Error(err.detail || 'Failed to fetch expense summary');
  }
  return res.json();
}

export async function updateExpense(
  eventId: string,
  expenseId: string,
  data: Partial<ExpenseFormData>
): Promise<ExpenseItem> {
  const res = await apiFetch(`/events/${eventId}/expenses/${expenseId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update expense' }));
    throw new Error(err.detail || 'Failed to update expense');
  }
  return res.json();
}

export async function deleteExpense(
  eventId: string,
  expenseId: string
): Promise<void> {
  const res = await apiFetch(`/events/${eventId}/expenses/${expenseId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to delete expense' }));
    throw new Error(err.detail || 'Failed to delete expense');
  }
}

export function getExportExpensesCsvUrl(eventId: string): string {
  const token = getStoredToken();
  return token
    ? `${API_BASE}/events/${eventId}/expenses/export/csv?token=${encodeURIComponent(token)}`
    : `${API_BASE}/events/${eventId}/expenses/export/csv`;
}

export function getExportExpensesPdfUrl(eventId: string): string {
  const token = getStoredToken();
  return token
    ? `${API_BASE}/events/${eventId}/expenses/export/pdf?token=${encodeURIComponent(token)}`
    : `${API_BASE}/events/${eventId}/expenses/export/pdf`;
}

// =========================================================
// PHASE 3: GUEST MANAGEMENT & RSVP SYSTEM API CLIENT
// =========================================================

export async function createGuest(
  eventId: string,
  data: GuestFormData
): Promise<GuestItem> {
  const res = await apiFetch(`/events/${eventId}/guests`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create guest' }));
    throw new Error(err.detail || 'Failed to create guest');
  }
  return res.json();
}

export async function getGuests(
  eventId: string,
  filters?: {
    search?: string;
    category?: string;
    rsvp_status?: string;
    invitation_status?: string;
    sort_by?: string;
  }
): Promise<GuestItem[]> {
  const params = new URLSearchParams();
  if (filters?.search) params.append('search', filters.search);
  if (filters?.category && filters.category !== 'all') params.append('category', filters.category);
  if (filters?.rsvp_status && filters.rsvp_status !== 'all') params.append('rsvp_status', filters.rsvp_status);
  if (filters?.invitation_status && filters.invitation_status !== 'all') params.append('invitation_status', filters.invitation_status);
  if (filters?.sort_by) params.append('sort_by', filters.sort_by);

  const queryString = params.toString() ? `?${params.toString()}` : '';
  const res = await apiFetch(`/events/${eventId}/guests${queryString}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch guests' }));
    throw new Error(err.detail || 'Failed to fetch guests');
  }
  return res.json();
}

export async function getGuestSummary(
  eventId: string
): Promise<GuestRSVPSummary> {
  const res = await apiFetch(`/events/${eventId}/guests/summary`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch guest RSVP summary' }));
    throw new Error(err.detail || 'Failed to fetch guest RSVP summary');
  }
  return res.json();
}

export async function updateGuest(
  eventId: string,
  guestId: string,
  data: Partial<GuestFormData>
): Promise<GuestItem> {
  const res = await apiFetch(`/events/${eventId}/guests/${guestId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update guest' }));
    throw new Error(err.detail || 'Failed to update guest');
  }
  return res.json();
}

export async function updateGuestStatus(
  eventId: string,
  guestId: string,
  statusData: { invitation_status?: string; rsvp_status?: string }
): Promise<GuestItem> {
  const res = await apiFetch(`/events/${eventId}/guests/${guestId}/status`, {
    method: 'PATCH',
    body: JSON.stringify(statusData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update guest status' }));
    throw new Error(err.detail || 'Failed to update guest status');
  }
  return res.json();
}

export async function deleteGuest(
  eventId: string,
  guestId: string
): Promise<void> {
  const res = await apiFetch(`/events/${eventId}/guests/${guestId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to delete guest' }));
    throw new Error(err.detail || 'Failed to delete guest');
  }
}

export async function previewCSVImport(
  eventId: string,
  csvContent: string,
  filename?: string
): Promise<CSVImportPreviewResponse> {
  const res = await apiFetch(`/events/${eventId}/guests/import/preview`, {
    method: 'POST',
    body: JSON.stringify({ csv_content: csvContent, filename: filename || 'guestlist.csv' }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to preview CSV import' }));
    throw new Error(err.detail || 'Failed to preview CSV import');
  }
  return res.json();
}

export async function confirmCSVImport(
  eventId: string,
  rows: GuestFormData[]
): Promise<CSVImportResult> {
  const res = await apiFetch(`/events/${eventId}/guests/import/confirm`, {
    method: 'POST',
    body: JSON.stringify({ rows }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to import guests' }));
    throw new Error(err.detail || 'Failed to import guests');
  }
  return res.json();
}

export function getExportGuestsCsvUrl(eventId: string, filterStatus: string = 'All'): string {
  const token = getStoredToken();
  const base = `${API_BASE}/events/${eventId}/guests/export/csv?filter_status=${encodeURIComponent(filterStatus)}`;
  return token ? `${base}&token=${encodeURIComponent(token)}` : base;
}

export function getExportGuestsPdfUrl(eventId: string): string {
  const token = getStoredToken();
  return token
    ? `${API_BASE}/events/${eventId}/guests/export/pdf?token=${encodeURIComponent(token)}`
    : `${API_BASE}/events/${eventId}/guests/export/pdf`;
}

// =========================================================
// PHASE 4: AI INVITATION GENERATOR API METHODS
// =========================================================

export async function getInvitationTemplates(): Promise<Record<string, InvitationTemplate>> {
  const res = await apiFetch('/invitations/templates');
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to load invitation templates' }));
    throw new Error(err.detail || 'Failed to load invitation templates');
  }
  return res.json();
}

export async function generateInvitations(
  req: InvitationGenerateRequest
): Promise<InvitationGenerateResponse> {
  const res = await apiFetch('/invitations/generate', {
    method: 'POST',
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to generate invitations' }));
    throw new Error(err.detail || 'Failed to generate invitations');
  }
  return res.json();
}

export async function saveInvitation(
  eventId: string,
  req: InvitationCreateRequest
): Promise<InvitationItem> {
  const res = await apiFetch(`/events/${eventId}/invitations`, {
    method: 'POST',
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to save invitation' }));
    throw new Error(err.detail || 'Failed to save invitation');
  }
  return res.json();
}

export async function getSavedInvitations(eventId: string): Promise<InvitationItem[]> {
  const res = await apiFetch(`/events/${eventId}/invitations`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch saved invitations' }));
    throw new Error(err.detail || 'Failed to fetch saved invitations');
  }
  return res.json();
}

export async function deleteSavedInvitation(invitationId: string): Promise<void> {
  const res = await apiFetch(`/invitations/${invitationId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to delete invitation' }));
    throw new Error(err.detail || 'Failed to delete invitation');
  }
}

export function getSavedInvitationPdfUrl(invitationId: string): string {
  const token = getStoredToken();
  return token
    ? `${API_BASE}/invitations/${invitationId}/export-pdf?token=${encodeURIComponent(token)}`
    : `${API_BASE}/invitations/${invitationId}/export-pdf`;
}

export async function exportDynamicInvitationPdf(
  title: string,
  language: string,
  text_components: any,
  design_config: any,
  event_details?: any
): Promise<Blob> {
  const res = await apiFetch('/invitations/export-pdf', {
    method: 'POST',
    body: JSON.stringify({
      title,
      language,
      text_components,
      design_config,
      event_details,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to generate PDF invitation' }));
    throw new Error(err.detail || 'Failed to generate PDF invitation');
  }
  return res.blob();
}

export async function markGuestInvitationSent(
  eventId: string,
  guestId: string
): Promise<GuestItem> {
  const res = await apiFetch(`/events/${eventId}/guests/${guestId}/mark-sent`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to mark guest invitation as sent' }));
    throw new Error(err.detail || 'Failed to mark guest invitation as sent');
  }
  return res.json();
}

// =========================================================
// PHASE 5: LOCAL VENDOR DISCOVERY & MANAGEMENT METHODS
// =========================================================

export async function getVendors(filters?: {
  category?: string;
  location?: string;
  min_price?: number;
  max_price?: number;
  min_rating?: number;
  search?: string;
  is_favorite?: boolean;
  is_verified?: boolean;
}): Promise<VendorItem[]> {
  const params = new URLSearchParams();
  if (filters?.category && filters.category !== 'All') params.append('category', filters.category);
  if (filters?.location && filters.location !== 'All') params.append('location', filters.location);
  if (filters?.min_price !== undefined) params.append('min_price', filters.min_price.toString());
  if (filters?.max_price !== undefined) params.append('max_price', filters.max_price.toString());
  if (filters?.min_rating !== undefined) params.append('min_rating', filters.min_rating.toString());
  if (filters?.search) params.append('search', filters.search);
  if (filters?.is_favorite !== undefined) params.append('is_favorite', filters.is_favorite.toString());
  if (filters?.is_verified !== undefined) params.append('is_verified', filters.is_verified.toString());

  const queryString = params.toString() ? `?${params.toString()}` : '';
  const res = await apiFetch(`/vendors${queryString}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch vendors from directory' }));
    throw new Error(err.detail || 'Failed to fetch vendors from directory');
  }
  return res.json();
}

export async function getVendor(vendorId: string): Promise<VendorItem> {
  const res = await apiFetch(`/vendors/${vendorId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch vendor details' }));
    throw new Error(err.detail || 'Failed to fetch vendor details');
  }
  return res.json();
}

export async function createVendor(data: VendorFormData): Promise<VendorItem> {
  const res = await apiFetch('/vendors', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create vendor' }));
    throw new Error(err.detail || 'Failed to create vendor');
  }
  return res.json();
}

export async function updateVendor(vendorId: string, data: Partial<VendorFormData>): Promise<VendorItem> {
  const res = await apiFetch(`/vendors/${vendorId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update vendor' }));
    throw new Error(err.detail || 'Failed to update vendor');
  }
  return res.json();
}

export async function deleteVendor(vendorId: string): Promise<void> {
  const res = await apiFetch(`/vendors/${vendorId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to delete vendor' }));
    throw new Error(err.detail || 'Failed to delete vendor');
  }
}

export async function toggleVendorFavorite(vendorId: string): Promise<VendorItem> {
  const res = await apiFetch(`/vendors/${vendorId}/favorite`, {
    method: 'PATCH',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to toggle favorite' }));
    throw new Error(err.detail || 'Failed to toggle favorite');
  }
  return res.json();
}

export async function recommendVendors(
  query: string,
  options?: { category?: string; location?: string; max_budget?: number; event_id?: string }
): Promise<VendorRecommendationResponse> {
  const res = await apiFetch('/vendors/recommend', {
    method: 'POST',
    body: JSON.stringify({
      query,
      category: options?.category,
      location: options?.location,
      max_budget: options?.max_budget,
      event_id: options?.event_id,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to get vendor recommendations' }));
    throw new Error(err.detail || 'Failed to get vendor recommendations');
  }
  return res.json();
}

export async function compareVendors(vendorIds: string[]): Promise<VendorComparisonResponse> {
  const res = await apiFetch('/vendors/compare', {
    method: 'POST',
    body: JSON.stringify({ vendor_ids: vendorIds }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to compare vendors' }));
    throw new Error(err.detail || 'Failed to compare vendors');
  }
  return res.json();
}

export async function getEventBookings(eventId: string): Promise<EventVendorBookingItem[]> {
  const res = await apiFetch(`/events/${eventId}/vendor-bookings`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch event vendor bookings' }));
    throw new Error(err.detail || 'Failed to fetch event vendor bookings');
  }
  return res.json();
}

export async function createOrUpdateBooking(
  eventId: string,
  data: {
    vendor_id: string;
    booking_status: string;
    agreed_price: number;
    advance_payment: number;
    booking_date?: string;
    notes?: string;
  }
): Promise<EventVendorBookingItem> {
  const res = await apiFetch(`/events/${eventId}/vendor-bookings`, {
    method: 'POST',
    body: JSON.stringify({ event_id: eventId, ...data }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to save booking' }));
    throw new Error(err.detail || 'Failed to save booking');
  }
  return res.json();
}

export async function updateBooking(
  bookingId: string,
  data: {
    booking_status?: string;
    agreed_price?: number;
    advance_payment?: number;
    booking_date?: string;
    notes?: string;
  }
): Promise<EventVendorBookingItem> {
  const res = await apiFetch(`/vendor-bookings/${bookingId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update booking' }));
    throw new Error(err.detail || 'Failed to update booking');
  }
  return res.json();
}

export async function deleteBooking(bookingId: string): Promise<void> {
  const res = await apiFetch(`/vendor-bookings/${bookingId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to delete booking' }));
    throw new Error(err.detail || 'Failed to delete booking');
  }
}

export async function getEventVendorAnalytics(eventId?: string): Promise<VendorAnalyticsSummary> {
  const url = eventId ? `/events/${eventId}/vendor-analytics` : `/vendor-analytics`;
  const res = await apiFetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch vendor analytics' }));
    throw new Error(err.detail || 'Failed to fetch vendor analytics');
  }
  return res.json();
}

export async function recordBookingAdvanceExpense(
  eventId: string,
  bookingId: string,
  paymentMethod: string = 'UPI',
  notes?: string
): Promise<ExpenseItem> {
  const res = await apiFetch(`/events/${eventId}/vendor-bookings/${bookingId}/record-expense`, {
    method: 'POST',
    body: JSON.stringify({ booking_id: bookingId, payment_method: paymentMethod, notes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to record expense' }));
    throw new Error(err.detail || 'Failed to record advance payment as expense');
  }
  return res.json();
}

// =========================================================
// PHASE 6: AI WEATHER-AWARE EVENT PLANNER API
// =========================================================

export async function geocodeLocation(city: string): Promise<LocationGeoResult> {
  const res = await apiFetch(`/weather/geocode?city=${encodeURIComponent(city)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to geocode location' }));
    throw new Error(err.detail || 'Failed to geocode location');
  }
  return res.json();
}

export async function getWeatherReport(
  city: string,
  date: string,
  eventType: string = 'wedding',
  eventId?: string
): Promise<WeatherReportResponse> {
  const params = new URLSearchParams({
    city,
    date,
    event_type: eventType,
  });
  if (eventId) params.append('event_id', eventId);

  const res = await apiFetch(`/weather/report?${params.toString()}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to retrieve weather report' }));
    throw new Error(err.detail || 'Failed to retrieve weather report');
  }
  return res.json();
}

export async function getEventWeather(
  eventId: string,
  cityOverride?: string,
  dateOverride?: string
): Promise<WeatherReportResponse> {
  const params = new URLSearchParams();
  if (cityOverride) params.append('city_override', cityOverride);
  if (dateOverride) params.append('date_override', dateOverride);

  const queryStr = params.toString() ? `?${params.toString()}` : '';
  const res = await apiFetch(`/events/${eventId}/weather${queryStr}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to retrieve event weather' }));
    throw new Error(err.detail || 'Failed to retrieve event weather');
  }
  return res.json();
}

export async function askWeatherAssistant(query: WeatherAssistantQuery): Promise<WeatherAssistantResponse> {
  const res = await apiFetch('/weather/ask-ai', {
    method: 'POST',
    body: JSON.stringify(query),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Weather Assistant request failed' }));
    throw new Error(err.detail || 'Weather Assistant request failed');
  }
  return res.json();
}

export async function saveWeatherTimelineTasks(
  eventId: string,
  req: SaveTimelineMitigationsRequest
): Promise<SaveTimelineMitigationsResponse> {
  const res = await apiFetch(`/events/${eventId}/weather/save-timeline-tasks`, {
    method: 'POST',
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to save weather tasks to timeline' }));
    throw new Error(err.detail || 'Failed to save weather tasks to timeline');
  }
  return res.json();
}

// =========================================================
// PHASE 7: AUTHENTICATION & EXECUTIVE DASHBOARD API
// =========================================================

export async function registerUser(req: RegisterRequest): Promise<RegisterResponse> {
  const res = await apiFetch('/auth/register', {
    method: 'POST',
    body: JSON.stringify(req),
    skipAuth: true,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
    throw new Error(err.detail || 'Registration failed');
  }
  return res.json();
}

export async function loginUser(req: LoginRequest): Promise<TokenResponse> {
  const res = await apiFetch('/auth/login', {
    method: 'POST',
    body: JSON.stringify(req),
    skipAuth: true,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Invalid credentials' }));
    throw new Error(err.detail || 'Invalid credentials');
  }
  const data: TokenResponse = await res.json();
  if (data.access_token) {
    setStoredToken(data.access_token);
  }
  return data;
}

export async function getCurrentUser(): Promise<User> {
  const res = await apiFetch('/auth/me');
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch user session' }));
    throw new Error(err.detail || 'Failed to fetch user session');
  }
  return res.json();
}

export function logoutUser(): void {
  try {
    apiFetch('/auth/logout', { method: 'POST' }).catch(() => {});
  } catch {}
  removeStoredToken();
}

export async function getExecutiveSummary(eventId?: string): Promise<ExecutiveDashboardResponse> {
  const url = eventId
    ? `/dashboard/executive-summary?event_id=${encodeURIComponent(eventId)}`
    : `/dashboard/executive-summary`;
  const res = await apiFetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to retrieve executive summary' }));
    throw new Error(err.detail || 'Failed to retrieve executive summary');
  }
  return res.json();
}
