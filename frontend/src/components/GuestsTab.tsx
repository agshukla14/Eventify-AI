import React, { useState, useEffect, useMemo } from 'react';
import {
  Users,
  UserPlus,
  CheckCircle2,
  Clock,
  XCircle,
  Mail,
  Phone,
  Search,
  Filter,
  Download,
  Upload,
  Trash2,
  Edit2,
  X,
  Check,
  AlertCircle,
  AlertTriangle,
  FileSpreadsheet,
  FileText,
  UserCheck,
  PieChart as PieIcon,
  BarChart2,
  Send,
  Calendar,
  Sparkles,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  FullEventPlan,
  GuestItem,
  GuestFormData,
  GuestCategory,
  InvitationStatus,
  RSVPStatus,
  GuestRSVPSummary,
  CSVImportPreviewResponse,
  CSVImportPreviewRow,
} from '../types';
import {
  getGuests,
  getGuestSummary,
  createGuest,
  updateGuest,
  updateGuestStatus,
  deleteGuest,
  previewCSVImport,
  confirmCSVImport,
  getExportGuestsCsvUrl,
  getExportGuestsPdfUrl,
} from '../api';

interface GuestsTabProps {
  plan: FullEventPlan;
}

const CATEGORIES: GuestCategory[] = [
  'Family',
  'Friends',
  'Relatives',
  'Colleagues',
  'VIP',
  'Others',
];

const RSVP_COLORS: Record<string, string> = {
  Accepted: '#10b981', // Emerald
  Pending: '#f59e0b',  // Amber
  Declined: '#f43f5e', // Rose
};

const CATEGORY_COLORS: Record<string, string> = {
  Family: '#4f46e5',
  Friends: '#0284c7',
  Relatives: '#8b5cf6',
  Colleagues: '#ec4899',
  VIP: '#f59e0b',
  Others: '#64748b',
};

export const GuestsTab: React.FC<GuestsTabProps> = ({ plan }) => {
  const [guests, setGuests] = useState<GuestItem[]>([]);
  const [summary, setSummary] = useState<GuestRSVPSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedRSVP, setSelectedRSVP] = useState('all');
  const [selectedInvitation, setSelectedInvitation] = useState('all');
  const [sortBy, setSortBy] = useState<'name_asc' | 'name_desc' | 'date_desc' | 'category_asc'>('name_asc');

  // Add / Edit Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingGuest, setEditingGuest] = useState<GuestItem | null>(null);
  const [formData, setFormData] = useState<GuestFormData>({
    full_name: '',
    email: '',
    phone: '',
    category: 'Friends',
    plus_ones: 0,
    invitation_status: 'Not Sent',
    rsvp_status: 'Pending',
    special_requirements: '',
    notes: '',
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // CSV Import Modal State
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importPreview, setImportPreview] = useState<CSVImportPreviewResponse | null>(null);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [isImportPreviewing, setIsImportPreviewing] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importSuccessMessage, setImportSuccessMessage] = useState<string | null>(null);

  // Export Menu State
  const [showExportMenu, setShowExportMenu] = useState(false);

  useEffect(() => {
    loadData();
  }, [plan.event_id]);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [guestList, summaryData] = await Promise.all([
        getGuests(plan.event_id, {
          search: searchQuery,
          category: selectedCategory,
          rsvp_status: selectedRSVP,
          invitation_status: selectedInvitation,
          sort_by: sortBy,
        }),
        getGuestSummary(plan.event_id),
      ]);
      setGuests(guestList);
      setSummary(summaryData);
    } catch (err: any) {
      console.error('Failed to load guests:', err);
      setError(err.message || 'Failed to load guest records');
    } finally {
      setIsLoading(false);
    }
  };

  // Re-fetch guests when search/filters/sort change
  useEffect(() => {
    const timer = setTimeout(() => {
      loadGuestsOnly();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery, selectedCategory, selectedRSVP, selectedInvitation, sortBy]);

  const loadGuestsOnly = async () => {
    try {
      const list = await getGuests(plan.event_id, {
        search: searchQuery,
        category: selectedCategory,
        rsvp_status: selectedRSVP,
        invitation_status: selectedInvitation,
        sort_by: sortBy,
      });
      setGuests(list);
    } catch (err: any) {
      console.error('Error filtering guests:', err);
    }
  };

  const handleOpenAddModal = () => {
    setEditingGuest(null);
    setFormData({
      full_name: '',
      email: '',
      phone: '',
      category: 'Friends',
      plus_ones: 0,
      invitation_status: 'Not Sent',
      rsvp_status: 'Pending',
      special_requirements: '',
      notes: '',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (guest: GuestItem) => {
    setEditingGuest(guest);
    setFormData({
      full_name: guest.full_name,
      email: guest.email || '',
      phone: guest.phone || '',
      category: guest.category,
      plus_ones: guest.plus_ones,
      invitation_status: guest.invitation_status,
      rsvp_status: guest.rsvp_status,
      special_requirements: guest.special_requirements || '',
      notes: guest.notes || '',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSaveGuest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.full_name.trim()) {
      setFormError('Guest name is required.');
      return;
    }

    setIsSubmitting(true);
    setFormError(null);
    try {
      if (editingGuest) {
        await updateGuest(plan.event_id, editingGuest.id, {
          ...formData,
          plus_ones: Math.max(0, Number(formData.plus_ones) || 0),
        });
      } else {
        await createGuest(plan.event_id, {
          ...formData,
          plus_ones: Math.max(0, Number(formData.plus_ones) || 0),
        });
      }
      setIsModalOpen(false);
      await loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to save guest');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickStatusUpdate = async (
    guestId: string,
    updates: { invitation_status?: InvitationStatus; rsvp_status?: RSVPStatus }
  ) => {
    try {
      await updateGuestStatus(plan.event_id, guestId, updates);
      await loadData();
    } catch (err: any) {
      alert(`Failed to update status: ${err.message}`);
    }
  };

  const handleDeleteGuest = async (guestId: string, name: string) => {
    if (!window.confirm(`Are you sure you want to remove "${name}" from the guest list?`)) {
      return;
    }
    try {
      await deleteGuest(plan.event_id, guestId);
      await loadData();
    } catch (err: any) {
      alert(`Failed to delete guest: ${err.message}`);
    }
  };

  // CSV Import handlers
  const handleSelectCSVFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.csv')) {
      alert('Please select a valid CSV file (.csv).');
      return;
    }

    setImportFile(file);
    setIsImportPreviewing(true);
    setImportPreview(null);

    const reader = new FileReader();
    reader.onload = async event => {
      const content = event.target?.result as string;
      try {
        const preview = await previewCSVImport(plan.event_id, content, file.name);
        setImportPreview(preview);
      } catch (err: any) {
        alert(`Failed to preview CSV: ${err.message}`);
      } finally {
        setIsImportPreviewing(false);
      }
    };
    reader.onerror = () => {
      alert('Failed to read the file.');
      setIsImportPreviewing(false);
    };
    reader.readAsText(file);
  };

  const handleConfirmCSVImport = async () => {
    if (!importPreview) return;
    const validRows = importPreview.preview_rows
      .filter(r => r.is_valid && !r.is_duplicate)
      .map(r => ({
        full_name: r.full_name,
        email: r.email,
        phone: r.phone,
        category: r.category as GuestCategory,
        plus_ones: r.plus_ones,
        invitation_status: 'Not Sent' as InvitationStatus,
        rsvp_status: 'Pending' as RSVPStatus,
      }));

    if (validRows.length === 0) {
      alert('No valid non-duplicate rows found to import.');
      return;
    }

    setIsImporting(true);
    try {
      const res = await confirmCSVImport(plan.event_id, validRows);
      setImportSuccessMessage(
        `🎉 Successfully imported ${res.imported_count} guests! (${res.skipped_count} skipped/duplicates)`
      );
      setIsImportModalOpen(false);
      setImportPreview(null);
      setImportFile(null);
      await loadData();

      setTimeout(() => setImportSuccessMessage(null), 6000);
    } catch (err: any) {
      alert(`Import failed: ${err.message}`);
    } finally {
      setIsImporting(false);
    }
  };

  // Recharts Chart Data
  const rsvpPieData = useMemo(() => {
    if (!summary) return [];
    return [
      { name: 'Accepted', value: summary.confirmed_guests, color: RSVP_COLORS.Accepted },
      { name: 'Pending', value: summary.pending_responses, color: RSVP_COLORS.Pending },
      { name: 'Declined', value: summary.declined_guests, color: RSVP_COLORS.Declined },
    ].filter(d => d.value > 0);
  }, [summary]);

  const categoryBarData = useMemo(() => {
    if (!summary) return [];
    return Object.entries(summary.category_counts)
      .map(([cat, count]) => ({
        category: cat,
        count,
        fill: CATEGORY_COLORS[cat] || '#4f46e5',
      }))
      .filter(c => c.count > 0);
  }, [summary]);

  const invitationPieData = useMemo(() => {
    if (!summary) return [];
    return [
      { name: 'Sent', value: summary.total_invitations_sent, color: '#4f46e5' },
      { name: 'Not Sent', value: summary.total_invitations_pending, color: '#94a3b8' },
    ].filter(d => d.value > 0);
  }, [summary]);

  return (
    <div className="space-y-6">

      {/* Success Notification Banner */}
      {importSuccessMessage && (
        <div className="bg-emerald-50 border border-emerald-300 p-4 rounded-2xl flex items-center justify-between text-emerald-900 text-sm shadow-xs animate-in fade-in duration-300">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <span className="font-semibold">{importSuccessMessage}</span>
          </div>
          <button
            onClick={() => setImportSuccessMessage(null)}
            className="p-1 hover:bg-emerald-100 rounded-lg transition-colors"
          >
            <X className="w-4 h-4 text-emerald-700" />
          </button>
        </div>
      )}

      {/* ========================================================= */}
      {/* 1. TOP HEADER & ACTION CONTROLS */}
      {/* ========================================================= */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-900">Guest Management & RSVP Ledger</h3>
            <span className="px-2.5 py-0.5 text-2xs font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full">
              Live Tracker
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Organize invitations, monitor real-time RSVP responses, manage plus-ones, and import guest lists.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* CSV Import Button */}
          <button
            onClick={() => {
              setImportPreview(null);
              setImportFile(null);
              setIsImportModalOpen(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-all shadow-2xs"
          >
            <Upload className="w-3.5 h-3.5 text-indigo-600" />
            <span>Import CSV</span>
          </button>

          {/* Export Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-all shadow-2xs"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>Export Guests</span>
            </button>

            {showExportMenu && (
              <div
                className="absolute right-0 mt-2 w-52 bg-white border border-slate-200 rounded-xl shadow-lg py-1.5 z-20 animate-in fade-in duration-200"
                onMouseLeave={() => setShowExportMenu(false)}
              >
                <div className="px-3 py-1 text-3xs font-bold text-slate-400 uppercase tracking-wider">
                  CSV Exports
                </div>
                <a
                  href={getExportGuestsCsvUrl(plan.event_id, 'All')}
                  download
                  onClick={() => setShowExportMenu(false)}
                  className="flex items-center gap-2 px-3.5 py-1.5 text-xs text-slate-700 hover:bg-indigo-50 hover:text-indigo-900 transition-colors"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-indigo-600" />
                  <span>All Guests (CSV)</span>
                </a>
                <a
                  href={getExportGuestsCsvUrl(plan.event_id, 'Accepted')}
                  download
                  onClick={() => setShowExportMenu(false)}
                  className="flex items-center gap-2 px-3.5 py-1.5 text-xs text-slate-700 hover:bg-indigo-50 hover:text-indigo-900 transition-colors"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Accepted Guests (CSV)</span>
                </a>
                <a
                  href={getExportGuestsCsvUrl(plan.event_id, 'Pending')}
                  download
                  onClick={() => setShowExportMenu(false)}
                  className="flex items-center gap-2 px-3.5 py-1.5 text-xs text-slate-700 hover:bg-indigo-50 hover:text-indigo-900 transition-colors"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-amber-600" />
                  <span>Pending Guests (CSV)</span>
                </a>
                <a
                  href={getExportGuestsCsvUrl(plan.event_id, 'Declined')}
                  download
                  onClick={() => setShowExportMenu(false)}
                  className="flex items-center gap-2 px-3.5 py-1.5 text-xs text-slate-700 hover:bg-indigo-50 hover:text-indigo-900 transition-colors"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-rose-600" />
                  <span>Declined Guests (CSV)</span>
                </a>
                <div className="border-t border-slate-100 my-1" />
                <div className="px-3 py-1 text-3xs font-bold text-slate-400 uppercase tracking-wider">
                  PDF Documents
                </div>
                <a
                  href={getExportGuestsPdfUrl(plan.event_id)}
                  target="_blank"
                  rel="noreferrer"
                  onClick={() => setShowExportMenu(false)}
                  className="flex items-center gap-2 px-3.5 py-1.5 text-xs text-slate-700 hover:bg-indigo-50 hover:text-indigo-900 transition-colors"
                >
                  <FileText className="w-3.5 h-3.5 text-rose-600" />
                  <span>Complete Guest Report (PDF)</span>
                </a>
              </div>
            )}
          </div>

          {/* Add Guest Button */}
          <button
            onClick={handleOpenAddModal}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-gradient-to-r from-indigo-600 to-emerald-600 hover:from-indigo-700 hover:to-emerald-700 rounded-xl shadow-sm transition-all"
          >
            <UserPlus className="w-4 h-4" />
            <span>Add New Guest</span>
          </button>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 2. FOUR RSVP DASHBOARD SUMMARY CARDS */}
      {/* ========================================================= */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

          {/* Card 1: Total Invited */}
          <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs space-y-1">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-2xs font-bold uppercase tracking-wider">Total Invited</span>
              <Users className="w-4 h-4 text-slate-500" />
            </div>
            <p className="text-2xl font-extrabold text-slate-900">
              {summary.total_guests_invited} Guests
            </p>
            <span className="text-2xs text-slate-500 block">
              {summary.total_invitations_sent} sent • {summary.total_invitations_pending} pending send
            </span>
          </div>

          {/* Card 2: Confirmed Guests & Headcount */}
          <div className="p-4 bg-white rounded-2xl border border-emerald-200/70 shadow-xs space-y-1 bg-gradient-to-br from-white to-emerald-50/30">
            <div className="flex items-center justify-between text-emerald-600">
              <span className="text-2xs font-bold uppercase tracking-wider">Confirmed Attendance</span>
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <p className="text-2xl font-extrabold text-emerald-700">
              {summary.total_expected_attendance} Headcount
            </p>
            <span className="text-2xs text-emerald-600 font-medium block">
              {summary.confirmed_guests} primary + {summary.confirmed_plus_ones} plus-ones
            </span>
          </div>

          {/* Card 3: Pending Responses */}
          <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs space-y-1">
            <div className="flex items-center justify-between text-amber-500">
              <span className="text-2xs font-bold uppercase tracking-wider">Pending Responses</span>
              <Clock className="w-4 h-4" />
            </div>
            <p className="text-2xl font-extrabold text-amber-700">
              {summary.pending_responses}
            </p>
            <span className="text-2xs text-slate-500 block">
              Response Rate: {summary.rsvp_response_rate.toFixed(1)}%
            </span>
          </div>

          {/* Card 4: Declined Invitations */}
          <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs space-y-1">
            <div className="flex items-center justify-between text-rose-500">
              <span className="text-2xs font-bold uppercase tracking-wider">Declined Invitations</span>
              <XCircle className="w-4 h-4" />
            </div>
            <p className="text-2xl font-extrabold text-rose-700">
              {summary.declined_guests}
            </p>
            <span className="text-2xs text-slate-500 block">
              Acceptance Rate: {summary.acceptance_rate.toFixed(1)}%
            </span>
          </div>

        </div>
      )}

      {/* ========================================================= */}
      {/* 3. GUEST ANALYTICS CHARTS SECTION */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* A. RSVP Distribution Pie Chart */}
        <div className="lg:col-span-4 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <PieIcon className="w-4 h-4 text-indigo-600" />
              <span>RSVP Response Distribution</span>
            </h4>
          </div>
          <p className="text-2xs text-slate-400">Accepted vs. Pending vs. Declined</p>

          <div className="h-56">
            {rsvpPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={rsvpPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {rsvpPieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(val: number) => [`${val} Guests`, 'Count']} />
                  <Legend wrapperStyle={{ fontSize: '10px' }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <Users className="w-8 h-8 text-slate-300 mb-2" />
                <p className="text-xs text-slate-500 font-medium">No guest RSVP data yet.</p>
              </div>
            )}
          </div>
        </div>

        {/* B. Category Distribution Bar Chart */}
        <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <BarChart2 className="w-4 h-4 text-indigo-600" />
              <span>Category Breakdown</span>
            </h4>
          </div>
          <p className="text-2xs text-slate-400">Family, Friends, VIP, Colleagues & Others</p>

          <div className="h-56">
            {categoryBarData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryBarData} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="category" tick={{ fontSize: 10 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(val: number) => [`${val} Guests`, 'Invited']} />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]} fill="#0d9488" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <Users className="w-8 h-8 text-slate-300 mb-2" />
                <p className="text-xs text-slate-500 font-medium">No category data yet.</p>
              </div>
            )}
          </div>
        </div>

        {/* C. Invitation Pacing & Headcount Comparison */}
        <div className="lg:col-span-3 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
          <div>
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <Send className="w-4 h-4 text-indigo-600" />
              <span>Invitation Pacing</span>
            </h4>
            <p className="text-2xs text-slate-400">Sent vs Not Sent progress</p>
          </div>

          <div className="space-y-3 pt-1">
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="font-semibold text-slate-700">Invitations Dispatched</span>
                <span className="font-bold text-indigo-700">
                  {summary?.total_invitations_sent || 0} / {summary?.total_guests_invited || 0}
                </span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                <div
                  className="h-2 rounded-full bg-indigo-600 transition-all duration-500"
                  style={{
                    width: `${
                      summary && summary.total_guests_invited > 0
                        ? (summary.total_invitations_sent / summary.total_guests_invited) * 100
                        : 0
                    }%`,
                  }}
                />
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Planned Target:</span>
                <span className="font-bold text-slate-900">{plan.intake.guest_count} Guests</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Expected Headcount:</span>
                <span className="font-bold text-emerald-700">
                  {summary?.total_expected_attendance || 0} Guests
                </span>
              </div>
              <div className="flex items-center justify-between border-t border-slate-200/60 pt-1.5">
                <span className="text-slate-500">Attendance Pacing:</span>
                <span className="font-extrabold text-indigo-800">
                  {plan.intake.guest_count > 0 && summary
                    ? ((summary.total_expected_attendance / plan.intake.guest_count) * 100).toFixed(1)
                    : 0}
                  %
                </span>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* ========================================================= */}
      {/* 4. GUEST LEDGER TABLE & SEARCH/FILTERS */}
      {/* ========================================================= */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden space-y-4 p-5">

        {/* Controls Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Guest Registry & Attendance Table
            </h4>
            <p className="text-2xs text-slate-500">
              {guests.length} guest records match active filters
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search guest, email, phone..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500 w-44 sm:w-56"
              />
            </div>

            {/* Category Filter */}
            <select
              value={selectedCategory}
              onChange={e => setSelectedCategory(e.target.value)}
              className="px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-700"
            >
              <option value="all">All Categories</option>
              {CATEGORIES.map(c => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>

            {/* RSVP Status Filter */}
            <select
              value={selectedRSVP}
              onChange={e => setSelectedRSVP(e.target.value)}
              className="px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-700"
            >
              <option value="all">All RSVP Statuses</option>
              <option value="Accepted">Accepted</option>
              <option value="Pending">Pending</option>
              <option value="Declined">Declined</option>
            </select>

            {/* Invitation Status Filter */}
            <select
              value={selectedInvitation}
              onChange={e => setSelectedInvitation(e.target.value)}
              className="px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-700"
            >
              <option value="all">All Invitations</option>
              <option value="Sent">Sent</option>
              <option value="Not Sent">Not Sent</option>
            </select>

            {/* Sort Dropdown */}
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as any)}
              className="px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-700"
            >
              <option value="name_asc">Name: A to Z</option>
              <option value="name_desc">Name: Z to A</option>
              <option value="date_desc">Date Added: Newest First</option>
              <option value="category_asc">Category</option>
            </select>
          </div>
        </div>

        {/* Guest Table */}
        <div className="overflow-x-auto border border-slate-100 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider border-b border-slate-200 font-semibold text-2xs">
              <tr>
                <th className="px-4 py-3">Guest Name & Requirements</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Contact Information</th>
                <th className="px-4 py-3 text-center">+1s</th>
                <th className="px-4 py-3 text-center">Invitation</th>
                <th className="px-4 py-3 text-center">RSVP Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {guests.length > 0 ? (
                guests.map(guest => (
                  <tr key={guest.id} className="hover:bg-slate-50/70 transition-colors">
                    {/* Guest Name & Notes */}
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">{guest.full_name}</div>
                      {guest.special_requirements && (
                        <p className="text-2xs text-amber-700 font-medium mt-0.5 flex items-center gap-1">
                          <span>🍽️</span> {guest.special_requirements}
                        </p>
                      )}
                      {guest.notes && (
                        <p className="text-2xs text-slate-400 mt-0.5 line-clamp-1">{guest.notes}</p>
                      )}
                    </td>

                    {/* Category */}
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-md text-2xs font-semibold bg-slate-100 text-slate-700">
                        {guest.category}
                      </span>
                    </td>

                    {/* Contact */}
                    <td className="px-4 py-3">
                      <div className="space-y-0.5">
                        {guest.email ? (
                          <div className="flex items-center gap-1.5 text-slate-600">
                            <Mail className="w-3 h-3 text-slate-400" />
                            <span className="truncate max-w-[140px]">{guest.email}</span>
                          </div>
                        ) : (
                          <span className="text-slate-300">-</span>
                        )}
                        {guest.phone && (
                          <div className="flex items-center gap-1.5 text-slate-500 text-2xs">
                            <Phone className="w-2.5 h-2.5 text-slate-400" />
                            <span>{guest.phone}</span>
                          </div>
                        )}
                      </div>
                    </td>

                    {/* Plus Ones */}
                    <td className="px-4 py-3 text-center font-bold text-slate-800">
                      {guest.plus_ones > 0 ? `+${guest.plus_ones}` : '0'}
                    </td>

                    {/* Invitation Status Toggle */}
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() =>
                          handleQuickStatusUpdate(guest.id, {
                            invitation_status: guest.invitation_status === 'Sent' ? 'Not Sent' : 'Sent',
                          })
                        }
                        title="Click to toggle invitation sent status"
                        className={`px-2.5 py-1 text-2xs font-bold rounded-lg border transition-all ${
                          guest.invitation_status === 'Sent'
                            ? 'bg-indigo-50 text-indigo-800 border-indigo-200 hover:bg-indigo-100'
                            : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200'
                        }`}
                      >
                        {guest.invitation_status === 'Sent' ? '✓ Sent' : 'Not Sent'}
                      </button>
                    </td>

                    {/* RSVP Status Dropdown */}
                    <td className="px-4 py-3 text-center">
                      <select
                        value={guest.rsvp_status}
                        onChange={e =>
                          handleQuickStatusUpdate(guest.id, {
                            rsvp_status: e.target.value as RSVPStatus,
                          })
                        }
                        className={`px-2.5 py-1 text-2xs font-bold rounded-lg border focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer ${
                          guest.rsvp_status === 'Accepted'
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                            : guest.rsvp_status === 'Declined'
                            ? 'bg-rose-50 text-rose-800 border-rose-300'
                            : 'bg-amber-50 text-amber-800 border-amber-300'
                        }`}
                      >
                        <option value="Pending">Pending</option>
                        <option value="Accepted">Accepted</option>
                        <option value="Declined">Declined</option>
                      </select>
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenEditModal(guest)}
                          title="Edit Guest Details"
                          className="p-1 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteGuest(guest.id, guest.full_name)}
                          title="Delete Guest"
                          className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                    <p className="text-xs font-medium">No guests found matching current search or filters.</p>
                    <button
                      onClick={handleOpenAddModal}
                      className="mt-2 text-xs font-semibold text-indigo-600 hover:underline inline-flex items-center gap-1"
                    >
                      <UserPlus className="w-3.5 h-3.5" /> Add new guest
                    </button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 5. ADD / EDIT GUEST MODAL */}
      {/* ========================================================= */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in zoom-in-95 duration-200">

            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">
                  {editingGuest ? 'Edit Guest Information' : 'Add New Guest'}
                </h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSaveGuest} className="space-y-3.5 text-xs">

              {/* Full Name */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Rahul Sharma"
                  value={formData.full_name}
                  onChange={e => setFormData({ ...formData, full_name: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 font-medium"
                />
              </div>

              {/* Category & Plus Ones */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Guest Category <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={formData.category}
                    onChange={e => setFormData({ ...formData, category: e.target.value as GuestCategory })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900"
                  >
                    {CATEGORIES.map(c => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Additional Guests (+1s)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="20"
                    value={formData.plus_ones}
                    onChange={e => setFormData({ ...formData, plus_ones: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900"
                  />
                </div>
              </div>

              {/* Email & Phone */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Email Address (Optional)
                  </label>
                  <input
                    type="email"
                    placeholder="name@example.com"
                    value={formData.email || ''}
                    onChange={e => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Phone Number (Optional)
                  </label>
                  <input
                    type="tel"
                    placeholder="+91-9876543210"
                    value={formData.phone || ''}
                    onChange={e => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900"
                  />
                </div>
              </div>

              {/* Invitation & RSVP Status */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Invitation Status
                  </label>
                  <select
                    value={formData.invitation_status}
                    onChange={e =>
                      setFormData({ ...formData, invitation_status: e.target.value as InvitationStatus })
                    }
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900"
                  >
                    <option value="Not Sent">Not Sent</option>
                    <option value="Sent">Sent</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    RSVP Response Status
                  </label>
                  <select
                    value={formData.rsvp_status}
                    onChange={e => setFormData({ ...formData, rsvp_status: e.target.value as RSVPStatus })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900"
                  >
                    <option value="Pending">Pending</option>
                    <option value="Accepted">Accepted</option>
                    <option value="Declined">Declined</option>
                  </select>
                </div>
              </div>

              {/* Special Requirements */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Special Requirements (Dietary, Accessibility, etc.)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Jain vegetarian, Nut allergy, Wheelchair ramp needed"
                  value={formData.special_requirements || ''}
                  onChange={e => setFormData({ ...formData, special_requirements: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900"
                />
              </div>

              {/* Notes */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Notes (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="Table arrangement, family side, seating preference..."
                  value={formData.notes || ''}
                  onChange={e => setFormData({ ...formData, notes: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors shadow-2xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 active:scale-95 disabled:opacity-50 rounded-xl shadow-sm transition-all"
                >
                  <Check className="w-4 h-4" />
                  <span>{editingGuest ? 'Save Changes' : 'Save Guest Record'}</span>
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* 6. CSV IMPORT & PREVIEW MODAL */}
      {/* ========================================================= */}
      {isImportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in zoom-in-95 duration-200 max-h-[90vh] flex flex-col">

            <div className="flex items-center justify-between border-b border-slate-100 pb-3 flex-shrink-0">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">Import Guest List from CSV</h3>
              </div>
              <button
                onClick={() => setIsImportModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* File Upload Box */}
            <div className="p-4 border-2 border-dashed border-indigo-200 rounded-xl bg-indigo-50/30 text-center space-y-2 flex-shrink-0">
              <Upload className="w-7 h-7 text-indigo-600 mx-auto" />
              <div>
                <label className="text-xs font-bold text-indigo-900 cursor-pointer hover:underline">
                  Choose a CSV file
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleSelectCSVFile}
                    className="hidden"
                  />
                </label>
                <span className="text-2xs text-slate-500 block mt-0.5">
                  Expected columns: <code>name, email, phone, category, plus_ones</code>
                </span>
              </div>
              {importFile && (
                <span className="inline-block px-2.5 py-0.5 text-2xs font-semibold bg-white text-indigo-800 border border-indigo-200 rounded-md">
                  📄 {importFile.name} ({(importFile.size / 1024).toFixed(1)} KB)
                </span>
              )}
            </div>

            {/* Preview Statistics */}
            {importPreview && (
              <div className="flex flex-wrap items-center gap-3 text-2xs font-bold flex-shrink-0">
                <span className="px-2.5 py-1 bg-slate-100 text-slate-700 rounded-lg">
                  Total in File: {importPreview.total_rows}
                </span>
                <span className="px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-lg">
                  ✓ Valid to Import: {importPreview.valid_rows_count}
                </span>
                {importPreview.duplicate_rows_count > 0 && (
                  <span className="px-2.5 py-1 bg-amber-100 text-amber-800 rounded-lg">
                    ⚠️ Duplicates Detected: {importPreview.duplicate_rows_count}
                  </span>
                )}
                {importPreview.invalid_rows_count > 0 && (
                  <span className="px-2.5 py-1 bg-rose-100 text-rose-800 rounded-lg">
                    ✕ Invalid Records: {importPreview.invalid_rows_count}
                  </span>
                )}
              </div>
            )}

            {/* Preview Table */}
            {importPreview && (
              <div className="overflow-y-auto border border-slate-200 rounded-xl flex-1 max-h-60 text-xs">
                <table className="w-full text-left text-2xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase sticky top-0 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-3 py-2">Row</th>
                      <th className="px-3 py-2">Name</th>
                      <th className="px-3 py-2">Category</th>
                      <th className="px-3 py-2">Contact</th>
                      <th className="px-3 py-2">+1s</th>
                      <th className="px-3 py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {importPreview.preview_rows.map((row, idx) => (
                      <tr
                        key={idx}
                        className={
                          row.is_duplicate
                            ? 'bg-amber-50/50'
                            : !row.is_valid
                            ? 'bg-rose-50/50'
                            : 'hover:bg-slate-50'
                        }
                      >
                        <td className="px-3 py-2 font-mono text-slate-400">#{row.row_number}</td>
                        <td className="px-3 py-2 font-semibold text-slate-900">{row.full_name || '<Empty>'}</td>
                        <td className="px-3 py-2 text-slate-600">{row.category}</td>
                        <td className="px-3 py-2 text-slate-500">
                          {row.email || row.phone || <span className="text-slate-300">-</span>}
                        </td>
                        <td className="px-3 py-2">{row.plus_ones}</td>
                        <td className="px-3 py-2">
                          {row.is_valid && !row.is_duplicate ? (
                            <span className="text-emerald-700 font-bold">✓ Ready</span>
                          ) : row.is_duplicate ? (
                            <span className="text-amber-700 font-bold" title={row.errors.join('; ')}>
                              Duplicate
                            </span>
                          ) : (
                            <span className="text-rose-600 font-bold" title={row.errors.join('; ')}>
                              Invalid
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Modal Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-100 flex-shrink-0">
              <span className="text-2xs text-slate-400">
                Duplicates & invalid entries will be skipped safely.
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsImportModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmCSVImport}
                  disabled={!importPreview || importPreview.valid_rows_count === 0 || isImporting}
                  className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl shadow-sm transition-all"
                >
                  <Check className="w-4 h-4" />
                  <span>
                    {isImporting
                      ? 'Importing...'
                      : `Import ${importPreview?.valid_rows_count || 0} Valid Guests`}
                  </span>
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
