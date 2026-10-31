import React, { useState, useEffect } from 'react';
import {
  Calendar,
  Wallet,
  CreditCard,
  PiggyBank,
  Users,
  UserCheck,
  Clock,
  Store,
  Sparkles,
  CloudSun,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  Plus,
  FileText,
  Bot,
  ExternalLink,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { ExecutiveDashboardResponse, FullEventPlan } from '../types';
import { getExecutiveSummary, getExportPdfUrl } from '../api';

interface ExecutiveDashboardProps {
  currentPlan: FullEventPlan | null;
  onSelectEvent: (eventId: string) => void;
  onNavigateTab: (tabId: string) => void;
  onOpenNewModal: () => void;
  onToggleChat: () => void;
}

const COLORS = ['#0d9488', '#059669', '#f59e0b', '#e11d48', '#6366f1', '#ec4899'];

export const ExecutiveDashboard: React.FC<ExecutiveDashboardProps> = ({
  currentPlan,
  onSelectEvent,
  onNavigateTab,
  onOpenNewModal,
  onToggleChat,
}) => {
  const [data, setData] = useState<ExecutiveDashboardResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);
    try {
      const summary = await getExecutiveSummary(currentPlan?.event_id);
      setData(summary);
    } catch (err: any) {
      console.error('Failed to load executive summary:', err);
      setError('Unable to load executive command metrics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, [currentPlan?.event_id]);

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-3 bg-white rounded-3xl border border-slate-200">
        <div className="w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-semibold text-slate-600">Loading Executive Command Center...</p>
      </div>
    );
  }

  const kpis = data?.kpis;
  const upcoming = data?.upcoming_events || [];
  const activities = data?.recent_activities || [];
  const budgetUtil = data?.budget_utilization || [];
  const rsvp = data?.guest_rsvp_breakdown;
  const vendorStats = data?.vendor_summary;
  const weatherAlert = data?.next_event_weather_alert;

  const rsvpPieData = rsvp
    ? [
        { name: 'Confirmed', value: rsvp.confirmed, color: '#0d9488' },
        { name: 'Pending', value: rsvp.pending, color: '#f59e0b' },
        { name: 'Declined', value: rsvp.declined, color: '#94a3b8' },
      ].filter((d) => d.value > 0)
    : [];

  return (
    <div className="space-y-6">
      {/* Header & Quick Action Shortcuts */}
      <div className="bg-gradient-to-r from-slate-900 via-teal-950 to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden">
        <div className="absolute -right-10 -bottom-10 w-64 h-64 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-wrap items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-3 py-0.5 text-xs font-bold uppercase tracking-wider bg-teal-500/20 text-teal-300 border border-teal-500/30 rounded-full">
                SaaS Command Center
              </span>
              <span className="text-xs text-slate-400">Live Executive Overview</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Executive Celebration Operations
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-xl">
              Real-time portfolio intelligence, automated budget reconciliation, vendor contracts, and atmospheric risk detection.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={onOpenNewModal}
              className="flex items-center gap-2 px-4 py-2.5 text-xs font-bold bg-teal-500 hover:bg-teal-400 text-teal-950 rounded-xl shadow-md transition-all active:scale-95"
            >
              <Plus className="w-4 h-4" />
              <span>New Celebration</span>
            </button>
            <button
              onClick={() => onNavigateTab('expenses')}
              className="flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold bg-white/10 hover:bg-white/20 text-white rounded-xl backdrop-blur-md transition-colors"
            >
              <CreditCard className="w-4 h-4 text-emerald-400" />
              <span>Log Expense</span>
            </button>
            <button
              onClick={() => onNavigateTab('weather')}
              className="flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold bg-white/10 hover:bg-white/20 text-white rounded-xl backdrop-blur-md transition-colors"
            >
              <CloudSun className="w-4 h-4 text-amber-400" />
              <span>Weather Radar</span>
            </button>
            {currentPlan && (
              <a
                href={getExportPdfUrl(currentPlan.event_id)}
                download
                className="flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold bg-white/10 hover:bg-white/20 text-white rounded-xl backdrop-blur-md transition-colors"
              >
                <FileText className="w-4 h-4 text-rose-400" />
                <span>PDF Report</span>
              </a>
            )}
            <button
              onClick={fetchSummary}
              className="p-2.5 text-slate-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-xl transition-colors"
              title="Refresh Data"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 8 Primary Executive KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* KPI 1: Total Events */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/90 shadow-xs flex items-center gap-4 hover:border-teal-300 transition-colors">
          <div className="w-12 h-12 rounded-2xl bg-teal-50 border border-teal-100 flex items-center justify-center text-teal-600 flex-shrink-0">
            <Calendar className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Events</p>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-2xl font-black text-slate-900">{kpis?.total_events || 0}</span>
              <span className="text-2xs text-teal-600 font-bold">Planned</span>
            </div>
            <p className="text-2xs text-slate-500 mt-0.5">In organizer directory</p>
          </div>
        </div>

        {/* KPI 2: Upcoming Events */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/90 shadow-xs flex items-center gap-4 hover:border-teal-300 transition-colors">
          <div className="w-12 h-12 rounded-2xl bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-600 flex-shrink-0">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Upcoming Events</p>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-2xl font-black text-slate-900">{kpis?.upcoming_events || 0}</span>
              <span className="text-2xs text-amber-600 font-bold">Active</span>
            </div>
            <p className="text-2xs text-slate-500 mt-0.5">Due in pipeline</p>
          </div>
        </div>

        {/* KPI 3: Total Planned Budget */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/90 shadow-xs flex items-center gap-4 hover:border-teal-300 transition-colors">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 flex-shrink-0">
            <Wallet className="w-6 h-6" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Planned Budget</p>
            <div className="flex items-baseline gap-1 mt-0.5 truncate">
              <span className="text-xl sm:text-2xl font-black text-slate-900 truncate">
                ₹{(kpis?.total_planned_budget || 0).toLocaleString()}
              </span>
            </div>
            <p className="text-2xs text-slate-500 mt-0.5">Total event allocations</p>
          </div>
        </div>

        {/* KPI 4: Actual Expenses */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/90 shadow-xs flex items-center gap-4 hover:border-teal-300 transition-colors">
          <div className="w-12 h-12 rounded-2xl bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-600 flex-shrink-0">
            <CreditCard className="w-6 h-6" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Actual Expenses</p>
            <div className="flex items-baseline gap-1 mt-0.5 truncate">
              <span className="text-xl sm:text-2xl font-black text-rose-600 truncate">
                ₹{(kpis?.total_actual_expenses || 0).toLocaleString()}
              </span>
            </div>
            <p className="text-2xs text-slate-500 mt-0.5">Disbursed & verified</p>
          </div>
        </div>

        {/* KPI 5: Remaining Budget */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/90 shadow-xs flex items-center gap-4 hover:border-teal-300 transition-colors">
          <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 flex-shrink-0">
            <PiggyBank className="w-6 h-6" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Remaining Budget</p>
            <div className="flex items-baseline gap-1 mt-0.5 truncate">
              <span
                className={`text-xl sm:text-2xl font-black truncate ${
                  (kpis?.remaining_budget || 0) < 0 ? 'text-rose-600' : 'text-slate-900'
                }`}
              >
                ₹{(kpis?.remaining_budget || 0).toLocaleString()}
              </span>
            </div>
            <p className="text-2xs text-slate-500 mt-0.5">Unallocated reserves</p>
          </div>
        </div>

        {/* KPI 6: Confirmed Guests */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/90 shadow-xs flex items-center gap-4 hover:border-teal-300 transition-colors">
          <div className="w-12 h-12 rounded-2xl bg-teal-50 border border-teal-100 flex items-center justify-center text-teal-600 flex-shrink-0">
            <UserCheck className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Confirmed Guests</p>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-2xl font-black text-slate-900">{kpis?.total_confirmed_guests || 0}</span>
              <span className="text-2xs text-teal-600 font-bold">Attending</span>
            </div>
            <p className="text-2xs text-slate-500 mt-0.5">Includes confirmed plus-ones</p>
          </div>
        </div>

        {/* KPI 7: Pending RSVPs */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/90 shadow-xs flex items-center gap-4 hover:border-teal-300 transition-colors">
          <div className="w-12 h-12 rounded-2xl bg-orange-50 border border-orange-100 flex items-center justify-center text-orange-600 flex-shrink-0">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Pending RSVPs</p>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-2xl font-black text-slate-900">{kpis?.pending_rsvps || 0}</span>
              <span className="text-2xs text-orange-600 font-bold">Awaiting</span>
            </div>
            <p className="text-2xs text-slate-500 mt-0.5">Responses pending</p>
          </div>
        </div>

        {/* KPI 8: Booked Vendors */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/90 shadow-xs flex items-center gap-4 hover:border-teal-300 transition-colors">
          <div className="w-12 h-12 rounded-2xl bg-purple-50 border border-purple-100 flex items-center justify-center text-purple-600 flex-shrink-0">
            <Store className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Booked Vendors</p>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-2xl font-black text-slate-900">{kpis?.booked_vendors || 0}</span>
              <span className="text-2xs text-purple-600 font-bold">Contracted</span>
            </div>
            <p className="text-2xs text-slate-500 mt-0.5">Partners secured</p>
          </div>
        </div>
      </div>

      {/* Atmospheric Weather Risk Banner for Nearest Event */}
      {weatherAlert && (
        <div
          className={`p-5 rounded-3xl border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 transition-all ${
            weatherAlert.overall_risk_level === 'High'
              ? 'bg-rose-50/80 border-rose-200 text-rose-900'
              : weatherAlert.overall_risk_level === 'Moderate'
              ? 'bg-amber-50/80 border-amber-200 text-amber-900'
              : 'bg-emerald-50/80 border-emerald-200 text-emerald-950'
          }`}
        >
          <div className="flex items-center gap-3.5">
            <div
              className={`w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-xs ${
                weatherAlert.overall_risk_level === 'High'
                  ? 'bg-rose-100 text-rose-600'
                  : weatherAlert.overall_risk_level === 'Moderate'
                  ? 'bg-amber-100 text-amber-600'
                  : 'bg-emerald-100 text-emerald-600'
              }`}
            >
              <CloudSun className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider">Atmospheric Risk Intelligence</span>
                <span
                  className={`px-2 py-0.5 text-2xs font-bold rounded-full ${
                    weatherAlert.overall_risk_level === 'High'
                      ? 'bg-rose-200 text-rose-900'
                      : weatherAlert.overall_risk_level === 'Moderate'
                      ? 'bg-amber-200 text-amber-900'
                      : 'bg-emerald-200 text-emerald-900'
                  }`}
                >
                  {weatherAlert.overall_risk_level} Risk
                </span>
                <span className="text-2xs text-slate-500 hidden sm:inline">
                  • {weatherAlert.event_title} ({weatherAlert.location}, {weatherAlert.date})
                </span>
              </div>
              <p className="text-xs font-semibold mt-0.5">{weatherAlert.primary_concern}</p>
              <p className="text-2xs text-slate-600 mt-0.5">
                <span className="font-bold">Mitigation Strategy:</span> {weatherAlert.recommended_action}
              </p>
            </div>
          </div>

          <button
            onClick={() => onNavigateTab('weather')}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-slate-800 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl shadow-xs transition-colors flex-shrink-0"
          >
            <span>Open Weather Radar</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Grid: Visual Analytics & Operational Lists */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Budget Utilization + Upcoming Events */}
        <div className="lg:col-span-2 space-y-6">
          {/* Budget Utilization Breakdown */}
          <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Budget Allocation vs Actual Spend</h3>
                <p className="text-xs text-slate-500">Departmental breakdown and disbursement velocity</p>
              </div>
              <button
                onClick={() => onNavigateTab('budget')}
                className="text-xs font-bold text-teal-600 hover:text-teal-700 flex items-center gap-1"
              >
                <span>AI Optimizer</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {budgetUtil.length > 0 ? (
              <div className="space-y-3.5 pt-2">
                {budgetUtil.map((b, idx) => (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-bold text-slate-700">{b.category}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500">₹{b.spent.toLocaleString()} spent</span>
                        <span className="text-slate-400">/ ₹{b.allocated.toLocaleString()}</span>
                        <span
                          className={`font-bold px-1.5 py-0.2 rounded-md text-2xs ${
                            b.percentage_used > 100
                              ? 'bg-rose-100 text-rose-700'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {b.percentage_used}%
                        </span>
                      </div>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          b.percentage_used > 100 ? 'bg-rose-500' : 'bg-teal-600'
                        }`}
                        style={{ width: `${Math.min(100, b.percentage_used)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-xs text-slate-400">No budget data available.</div>
            )}
          </div>

          {/* Upcoming Events Countdown List */}
          <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-xs">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Upcoming Event Schedule</h3>
                <p className="text-xs text-slate-500">Active celebrations in pipeline sorted by proximity</p>
              </div>
              <button
                onClick={onOpenNewModal}
                className="text-xs font-bold text-teal-600 hover:text-teal-700 flex items-center gap-1"
              >
                <span>+ Add Event</span>
              </button>
            </div>

            <div className="space-y-3">
              {upcoming.map((ev) => {
                const isSelected = currentPlan?.event_id === ev.event_id;
                return (
                  <div
                    key={ev.event_id}
                    onClick={() => onSelectEvent(ev.event_id)}
                    className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-wrap items-center justify-between gap-4 ${
                      isSelected
                        ? 'border-teal-500 bg-teal-50/40 shadow-xs'
                        : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/60'
                    }`}
                  >
                    <div className="flex items-center gap-3.5">
                      <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-700 font-bold text-xs flex-shrink-0">
                        {ev.days_left >= 0 ? `${ev.days_left}d` : 'Past'}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900 text-sm">{ev.title}</span>
                          <span className="px-2 py-0.5 text-2xs font-semibold capitalize bg-slate-100 text-slate-600 rounded-md">
                            {ev.event_type}
                          </span>
                        </div>
                        <p className="text-2xs text-slate-500 mt-0.5">
                          📍 {ev.city} • 📅 {ev.date} • 👥 {ev.guest_count} Guests • Budget: ₹{ev.total_budget.toLocaleString()}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="text-right hidden sm:block">
                        <span className="text-xs font-bold text-slate-800">
                          ₹{ev.actual_spent.toLocaleString()}
                        </span>
                        <p className="text-2xs text-slate-400">Spent</p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectEvent(ev.event_id);
                        }}
                        className="px-3 py-1.5 text-xs font-bold text-teal-700 hover:bg-teal-100/70 rounded-lg transition-colors"
                      >
                        {isSelected ? 'Active Plan' : 'Select'}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right 1 Col: Guest RSVP Donut + Recent Activities */}
        <div className="space-y-6">
          {/* Guest RSVP Breakdown Donut */}
          <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-xs">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Guest RSVP Attendance</h3>
                <p className="text-xs text-slate-500">Confirmed headcount and plus-ones</p>
              </div>
              <button
                onClick={() => onNavigateTab('guests')}
                className="text-xs font-bold text-teal-600 hover:text-teal-700 flex items-center gap-1"
              >
                <span>Guest Roster</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {rsvp && rsvp.total_invited > 0 ? (
              <div>
                <div className="h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={rsvpPieData}
                        innerRadius={45}
                        outerRadius={65}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {rsvpPieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center pt-2 border-t border-slate-100">
                  <div className="p-2 rounded-xl bg-teal-50">
                    <p className="text-xs font-bold text-teal-900">{rsvp.confirmed}</p>
                    <p className="text-2xs text-teal-600 font-medium">Confirmed</p>
                  </div>
                  <div className="p-2 rounded-xl bg-amber-50">
                    <p className="text-xs font-bold text-amber-900">{rsvp.pending}</p>
                    <p className="text-2xs text-amber-600 font-medium">Pending</p>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-100">
                    <p className="text-xs font-bold text-slate-800">{rsvp.total_attending}</p>
                    <p className="text-2xs text-slate-500 font-medium">Total Attending</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-10 text-xs text-slate-400">No guest RSVP data recorded yet.</div>
            )}
          </div>

          {/* Vendor Booking Summary */}
          {vendorStats && (
            <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-slate-900 text-sm">Vendor Contracts Summary</h3>
                <button
                  onClick={() => onNavigateTab('find_vendors')}
                  className="text-xs font-bold text-teal-600 hover:text-teal-700 flex items-center gap-1"
                >
                  <span>Directory</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100">
                  <p className="text-2xs text-slate-400 font-bold uppercase">Contracted Value</p>
                  <p className="text-base font-extrabold text-slate-900 mt-0.5">
                    ₹{vendorStats.total_contracted_amount.toLocaleString()}
                  </p>
                  <p className="text-2xs text-slate-500 mt-0.5">{vendorStats.booked_count} Booked</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100">
                  <p className="text-2xs text-slate-400 font-bold uppercase">Advance Paid</p>
                  <p className="text-base font-extrabold text-emerald-600 mt-0.5">
                    ₹{vendorStats.advance_paid_amount.toLocaleString()}
                  </p>
                  <p className="text-2xs text-slate-500 mt-0.5">{vendorStats.shortlisted_count} In Talks</p>
                </div>
              </div>
            </div>
          )}

          {/* Recent Operations Activity Feed */}
          <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-xs">
            <h3 className="font-bold text-slate-900 text-sm mb-3">Recent Operational Activity</h3>
            {activities.length > 0 ? (
              <div className="space-y-3.5">
                {activities.map((act) => (
                  <div key={act.id} className="flex items-start gap-3 text-xs">
                    <span
                      className={`px-2 py-0.5 rounded-md font-bold text-2xs uppercase mt-0.5 ${
                        act.activity_type === 'expense'
                          ? 'bg-rose-100 text-rose-700'
                          : act.activity_type === 'rsvp'
                          ? 'bg-teal-100 text-teal-700'
                          : 'bg-purple-100 text-purple-700'
                      }`}
                    >
                      {act.badge}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="font-bold text-slate-800 truncate">{act.title}</p>
                      <p className="text-2xs text-slate-500 truncate">{act.description}</p>
                      <span className="text-2xs text-slate-400">{act.timestamp}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-xs text-slate-400">No activity recorded yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExecutiveDashboard;
