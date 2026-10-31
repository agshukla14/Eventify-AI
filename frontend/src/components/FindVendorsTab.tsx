import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  Sparkles,
  Filter,
  CheckCircle2,
  Clock,
  XCircle,
  Plus,
  Trash2,
  Edit2,
  ExternalLink,
  Phone,
  Mail,
  MapPin,
  Star,
  ShieldCheck,
  ShieldAlert,
  Heart,
  Sliders,
  DollarSign,
  ChevronRight,
  X,
  Check,
  CreditCard,
  Briefcase,
  Layers,
  ArrowRightLeft,
  Calendar,
  AlertCircle,
  Bookmark,
  RefreshCw,
  Building,
  Camera,
  Utensils,
  Flower2,
  Music,
  Smile,
  Truck,
  Sparkle,
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
  VendorItem,
  VendorFormData,
  VendorCategoryType,
  BookingStatusType,
  EventVendorBookingItem,
  VendorAnalyticsSummary,
  VendorRecommendationResponse,
  VendorComparisonResponse,
} from '../types';
import {
  getVendors,
  createVendor,
  updateVendor,
  deleteVendor,
  toggleVendorFavorite,
  recommendVendors,
  compareVendors,
  getEventBookings,
  createOrUpdateBooking,
  updateBooking,
  deleteBooking,
  getEventVendorAnalytics,
  recordBookingAdvanceExpense,
} from '../api';

interface FindVendorsTabProps {
  plan: FullEventPlan | null;
  onRefreshPlan?: () => void;
}

const CATEGORIES: { label: string; value: string; icon: any }[] = [
  { label: 'All Categories', value: 'All', icon: Layers },
  { label: 'Photography', value: 'Photography', icon: Camera },
  { label: 'Catering', value: 'Catering', icon: Utensils },
  { label: 'Decoration', value: 'Decoration', icon: Flower2 },
  { label: 'Venue', value: 'Venue', icon: Building },
  { label: 'Entertainment', value: 'Entertainment', icon: Music },
  { label: 'Makeup Artists', value: 'Makeup Artists', icon: Smile },
  { label: 'Transportation', value: 'Transportation', icon: Truck },
  { label: 'Other Services', value: 'Other Event Services', icon: Sparkle },
];

const LOCATIONS = ['All', 'Ahmedabad', 'Mumbai', 'Jaipur', 'Delhi', 'Bengaluru', 'Udaipur'];

const CHART_COLORS = ['#0D9488', '#2563EB', '#D97706', '#E11D48', '#8B5CF6', '#10B981', '#6366F1'];

export const FindVendorsTab: React.FC<FindVendorsTabProps> = ({ plan, onRefreshPlan }) => {
  // Directory & Bookings State
  const [vendors, setVendors] = useState<VendorItem[]>([]);
  const [bookings, setBookings] = useState<EventVendorBookingItem[]>([]);
  const [analytics, setAnalytics] = useState<VendorAnalyticsSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Filters State
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [selectedLocation, setSelectedLocation] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [maxPriceFilter, setMaxPriceFilter] = useState<number | ''>('');
  const [minRatingFilter, setMinRatingFilter] = useState<number>(0);
  const [verifiedOnly, setVerifiedOnly] = useState<boolean>(false);
  const [favoritesOnly, setFavoritesOnly] = useState<boolean>(false);

  // AI Recommendation State
  const [aiPrompt, setAiPrompt] = useState<string>('');
  const [isAiSearching, setIsAiSearching] = useState<boolean>(false);
  const [aiResults, setAiResults] = useState<VendorRecommendationResponse | null>(null);

  // Comparison State
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [comparisonData, setComparisonData] = useState<VendorComparisonResponse | null>(null);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState<boolean>(false);

  // Booking Modal State
  const [bookingModalVendor, setBookingModalVendor] = useState<VendorItem | null>(null);
  const [bookingStatus, setBookingStatus] = useState<BookingStatusType>('Shortlisted');
  const [agreedPrice, setAgreedPrice] = useState<number>(0);
  const [advancePayment, setAdvancePayment] = useState<number>(0);
  const [bookingDate, setBookingDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [bookingNotes, setBookingNotes] = useState<string>('');
  const [bookingError, setBookingError] = useState<string | null>(null);
  const [isSavingBooking, setIsSavingBooking] = useState<boolean>(false);
  const [bookingSuccessNotice, setBookingSuccessNotice] = useState<string | null>(null);

  // Record Expense State
  const [recordingExpenseId, setRecordingExpenseId] = useState<string | null>(null);
  const [recordedExpenseNotice, setRecordedExpenseNotice] = useState<string | null>(null);

  // Add / Edit Custom Vendor Modal State
  const [isVendorModalOpen, setIsVendorModalOpen] = useState<boolean>(false);
  const [editingVendorId, setEditingVendorId] = useState<string | null>(null);
  const [vendorForm, setVendorForm] = useState<VendorFormData>({
    name: '',
    category: 'Photography',
    location: plan?.intake?.city || 'Ahmedabad',
    description: '',
    services_offered: [],
    min_price: 25000,
    max_price: 60000,
    rating: 4.8,
    review_count: 10,
    experience_years: 5,
    phone: '',
    email: '',
    website: '',
    portfolio_images: [],
  });
  const [servicesInput, setServicesInput] = useState<string>('');
  const [vendorFormError, setVendorFormError] = useState<string | null>(null);

  // Active View Tab: 'directory' | 'bookings' | 'analytics'
  const [viewTab, setViewTab] = useState<'directory' | 'bookings' | 'analytics'>('directory');

  // Load Data on Mount & Plan Change
  useEffect(() => {
    loadAllData();
  }, [plan?.event_id]);

  const loadAllData = async () => {
    setIsLoading(true);
    try {
      const vList = await getVendors();
      setVendors(vList);

      if (plan?.event_id) {
        const bList = await getEventBookings(plan.event_id);
        setBookings(bList);
        const aSummary = await getEventVendorAnalytics(plan.event_id);
        setAnalytics(aSummary);
      } else {
        const aSummary = await getEventVendorAnalytics();
        setAnalytics(aSummary);
      }
    } catch (e) {
      console.error('Failed to load vendor data:', e);
    } finally {
      setIsLoading(false);
    }
  };

  // Filtered Vendors
  const filteredVendors = useMemo(() => {
    return vendors.filter((v) => {
      if (selectedCategory !== 'All' && v.category !== selectedCategory) return false;
      if (selectedLocation !== 'All' && !v.location.toLowerCase().includes(selectedLocation.toLowerCase())) return false;
      if (maxPriceFilter !== '' && v.min_price > Number(maxPriceFilter)) return false;
      if (minRatingFilter > 0 && v.rating < minRatingFilter) return false;
      if (verifiedOnly && !v.is_verified) return false;
      if (favoritesOnly && !v.is_favorite) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = v.name.toLowerCase().includes(q);
        const matchDesc = v.description.toLowerCase().includes(q);
        const matchLoc = v.location.toLowerCase().includes(q);
        const matchServ = v.services_offered.some((s) => s.toLowerCase().includes(q));
        if (!matchName && !matchDesc && !matchLoc && !matchServ) return false;
      }
      return true;
    });
  }, [vendors, selectedCategory, selectedLocation, maxPriceFilter, minRatingFilter, verifiedOnly, favoritesOnly, searchQuery]);

  // Toggle Favorite
  const handleToggleFavorite = async (vendorId: string) => {
    try {
      const updated = await toggleVendorFavorite(vendorId);
      setVendors(vendors.map((v) => (v.id === updated.id ? updated : v)));
    } catch (e) {
      console.error('Failed to toggle favorite:', e);
    }
  };

  // AI-Powered Vendor Recommendation
  const handleAiSearch = async () => {
    if (!aiPrompt.trim()) return;
    setIsAiSearching(true);
    try {
      const res = await recommendVendors(aiPrompt, {
        event_id: plan?.event_id,
        location: selectedLocation !== 'All' ? selectedLocation : undefined,
        category: selectedCategory !== 'All' ? selectedCategory : undefined,
      });
      setAiResults(res);
    } catch (e: any) {
      alert(`AI Search failed: ${e.message}`);
    } finally {
      setIsAiSearching(false);
    }
  };

  // Clear AI Search
  const handleClearAiSearch = () => {
    setAiResults(null);
    setAiPrompt('');
  };

  // Compare Selection
  const handleToggleCompare = (vendorId: string) => {
    if (selectedForCompare.includes(vendorId)) {
      setSelectedForCompare(selectedForCompare.filter((id) => id !== vendorId));
    } else {
      if (selectedForCompare.length >= 3) {
        alert('You can compare a maximum of 3 vendors simultaneously.');
        return;
      }
      setSelectedForCompare([...selectedForCompare, vendorId]);
    }
  };

  const handleRunComparison = async () => {
    if (selectedForCompare.length < 2) {
      alert('Please select at least 2 vendors to compare.');
      return;
    }
    setIsComparing(true);
    try {
      const comp = await compareVendors(selectedForCompare);
      setComparisonData(comp);
      setIsCompareModalOpen(true);
    } catch (e: any) {
      alert(`Comparison failed: ${e.message}`);
    } finally {
      setIsComparing(false);
    }
  };

  // Open Booking Modal for a Vendor
  const handleOpenBookingModal = (vendor: VendorItem) => {
    setBookingModalVendor(vendor);
    const existing = bookings.find((b) => b.vendor_id === vendor.id);
    if (existing) {
      setBookingStatus(existing.booking_status);
      setAgreedPrice(existing.agreed_price);
      setAdvancePayment(existing.advance_payment);
      setBookingDate(existing.booking_date || new Date().toISOString().split('T')[0]);
      setBookingNotes(existing.notes || '');
    } else {
      setBookingStatus('Shortlisted');
      setAgreedPrice(vendor.min_price);
      setAdvancePayment(Math.round(vendor.min_price * 0.25));
      setBookingDate(new Date().toISOString().split('T')[0]);
      setBookingNotes('');
    }
    setBookingError(null);
  };

  // Save Event Booking
  const handleSaveBooking = async () => {
    if (!plan || !bookingModalVendor) return;
    if (agreedPrice < 0 || advancePayment < 0) {
      setBookingError('Amounts cannot be negative.');
      return;
    }
    if (advancePayment > agreedPrice) {
      setBookingError(`Advance payment (₹${advancePayment.toLocaleString()}) cannot exceed the agreed price (₹${agreedPrice.toLocaleString()}).`);
      return;
    }

    setIsSavingBooking(true);
    setBookingError(null);
    try {
      const saved = await createOrUpdateBooking(plan.event_id, {
        vendor_id: bookingModalVendor.id,
        booking_status: bookingStatus,
        agreed_price: agreedPrice,
        advance_payment: advancePayment,
        booking_date: bookingDate,
        notes: bookingNotes || undefined,
      });

      const updatedBookings = bookings.some((b) => b.id === saved.id)
        ? bookings.map((b) => (b.id === saved.id ? saved : b))
        : [saved, ...bookings];
      setBookings(updatedBookings);

      // Refresh analytics
      const updatedAnalytics = await getEventVendorAnalytics(plan.event_id);
      setAnalytics(updatedAnalytics);

      setBookingSuccessNotice(`Booking saved for ${bookingModalVendor.name}! Remaining payment: ₹${saved.remaining_payment.toLocaleString()}`);
      setTimeout(() => {
        setBookingSuccessNotice(null);
        setBookingModalVendor(null);
      }, 1800);
    } catch (e: any) {
      setBookingError(e.message || 'Failed to save booking');
    } finally {
      setIsSavingBooking(false);
    }
  };

  // Delete Booking
  const handleDeleteBooking = async (bookingId: string) => {
    if (!confirm('Are you sure you want to remove this vendor booking?')) return;
    try {
      await deleteBooking(bookingId);
      const remaining = bookings.filter((b) => b.id !== bookingId);
      setBookings(remaining);
      if (plan?.event_id) {
        const updatedAnalytics = await getEventVendorAnalytics(plan.event_id);
        setAnalytics(updatedAnalytics);
      }
    } catch (e: any) {
      alert(`Failed to delete booking: ${e.message}`);
    }
  };

  // Record Advance as an actual Expense in Phase 2
  const handleRecordAdvanceExpense = async (booking: EventVendorBookingItem) => {
    if (!plan) return;
    if (booking.advance_payment <= 0) {
      alert('This booking has zero advance payment recorded. Update the advance payment first.');
      return;
    }
    setRecordingExpenseId(booking.id);
    try {
      await recordBookingAdvanceExpense(
        plan.event_id,
        booking.id,
        'UPI / Bank Transfer',
        `Advance payment for ${booking.vendor.name} (${booking.booking_status})`
      );
      onRefreshPlan?.();
      setRecordedExpenseNotice(`Advance payment of ₹${booking.advance_payment.toLocaleString()} for ${booking.vendor.name} has been recorded in Phase 2 Smart Expense Tracking!`);
      setTimeout(() => setRecordedExpenseNotice(null), 4000);
    } catch (e: any) {
      alert(`Failed to record expense: ${e.message}`);
    } finally {
      setRecordingExpenseId(null);
    }
  };

  // Add / Edit Custom Vendor Handlers
  const handleOpenAddVendorModal = () => {
    setEditingVendorId(null);
    setVendorForm({
      name: '',
      category: 'Photography',
      location: plan?.intake?.city || 'Ahmedabad',
      description: '',
      services_offered: [],
      min_price: 25000,
      max_price: 60000,
      rating: 4.8,
      review_count: 5,
      experience_years: 4,
      phone: '',
      email: '',
      website: '',
      portfolio_images: [],
    });
    setServicesInput('Full Coverage, Drone Shoots, High-Resolution Albums');
    setVendorFormError(null);
    setIsVendorModalOpen(true);
  };

  const handleOpenEditVendorModal = (vendor: VendorItem) => {
    if (vendor.is_verified) {
      alert('Verified directory listings cannot be modified. You can add your own custom vendor.');
      return;
    }
    setEditingVendorId(vendor.id);
    setVendorForm({
      name: vendor.name,
      category: vendor.category,
      location: vendor.location,
      description: vendor.description,
      services_offered: vendor.services_offered,
      min_price: vendor.min_price,
      max_price: vendor.max_price,
      rating: vendor.rating,
      review_count: vendor.review_count,
      experience_years: vendor.experience_years,
      phone: vendor.phone,
      email: vendor.email,
      website: vendor.website || '',
      portfolio_images: vendor.portfolio_images,
    });
    setServicesInput(vendor.services_offered.join(', '));
    setVendorFormError(null);
    setIsVendorModalOpen(true);
  };

  const handleSaveVendorForm = async () => {
    if (!vendorForm.name.trim() || !vendorForm.description.trim() || !vendorForm.phone.trim()) {
      setVendorFormError('Please fill in Name, Description, and Contact Phone.');
      return;
    }
    const services = servicesInput
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      if (editingVendorId) {
        const updated = await updateVendor(editingVendorId, {
          ...vendorForm,
          services_offered: services,
        });
        setVendors(vendors.map((v) => (v.id === updated.id ? updated : v)));
      } else {
        const created = await createVendor({
          ...vendorForm,
          services_offered: services,
        });
        setVendors([created, ...vendors]);
      }
      setIsVendorModalOpen(false);
    } catch (e: any) {
      setVendorFormError(e.message || 'Failed to save vendor');
    }
  };

  const handleDeleteVendor = async (vendorId: string) => {
    if (!confirm('Are you sure you want to delete this user-created vendor?')) return;
    try {
      await deleteVendor(vendorId);
      setVendors(vendors.filter((v) => v.id !== vendorId));
    } catch (e: any) {
      alert(`Failed to delete vendor: ${e.message}`);
    }
  };

  // Recharts Data Mapping
  const categoryChartData = useMemo(() => {
    if (!analytics?.category_counts) return [];
    return Object.entries(analytics.category_counts).map(([cat, count]) => ({
      name: cat,
      count,
    }));
  }, [analytics?.category_counts]);

  const bookingStatusChartData = useMemo(() => {
    if (!analytics?.booking_status_counts) return [];
    return Object.entries(analytics.booking_status_counts).map(([status, count]) => ({
      name: status,
      value: count,
    }));
  }, [analytics?.booking_status_counts]);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-teal-700 via-indigo-700 to-slate-900 rounded-2xl p-6 sm:p-8 text-white shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/20 backdrop-blur-md text-xs font-semibold mb-3">
            <Sparkles className="w-4 h-4 text-amber-300" />
            <span>Phase 5: Local Vendor Discovery & Management</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Find Vendors & Local Event Management
          </h1>
          <p className="mt-2 text-teal-100 text-sm sm:text-base max-w-2xl leading-relaxed">
            Discover verified celebration vendors across India with Gemini AI recommendations.
            Compare prices & reviews side-by-side, manage contracts & advance payments, and sync directly with your budget.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {selectedForCompare.length > 0 && (
            <button
              onClick={handleRunComparison}
              disabled={isComparing}
              className="px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-900 font-bold text-xs flex items-center gap-1.5 shadow-lg transition"
            >
              <ArrowRightLeft className="w-4 h-4" />
              <span>Compare ({selectedForCompare.length})</span>
            </button>
          )}

          <button
            onClick={handleOpenAddVendorModal}
            className="px-4 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-900 font-bold text-xs flex items-center gap-1.5 shadow-lg transition"
          >
            <Plus className="w-4 h-4" />
            <span>Add Custom Vendor</span>
          </button>
        </div>
      </div>

      {/* View Switcher Tabs: Directory | Event Bookings | Analytics */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setViewTab('directory')}
          className={`pb-3 px-4 font-bold text-sm flex items-center gap-2 border-b-2 transition ${
            viewTab === 'directory'
              ? 'border-teal-600 text-teal-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Vendor Directory ({filteredVendors.length})</span>
        </button>

        <button
          onClick={() => setViewTab('bookings')}
          className={`pb-3 px-4 font-bold text-sm flex items-center gap-2 border-b-2 transition ${
            viewTab === 'bookings'
              ? 'border-teal-600 text-teal-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Briefcase className="w-4 h-4" />
          <span>Event Bookings ({bookings.length})</span>
        </button>

        <button
          onClick={() => setViewTab('analytics')}
          className={`pb-3 px-4 font-bold text-sm flex items-center gap-2 border-b-2 transition ${
            viewTab === 'analytics'
              ? 'border-teal-600 text-teal-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>Vendor Analytics & Spending</span>
        </button>
      </div>

      {/* Notification Toast for Expense sync */}
      {recordedExpenseNotice && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-semibold flex items-center gap-2.5 shadow-sm">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{recordedExpenseNotice}</span>
        </div>
      )}

      {/* ========================================================= */}
      {/* 1. VENDOR DIRECTORY VIEW */}
      {/* ========================================================= */}
      {viewTab === 'directory' && (
        <div className="space-y-6">
          {/* AI Search Box */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-3">
            <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              <span>AI-Powered Vendor Recommendation</span>
            </div>

            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="text"
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAiSearch()}
                  placeholder='Ask in plain English: "Find wedding photographers in Ahmedabad under ₹30,000" or "Royal caterers in Jaipur"'
                  className="w-full pl-10 pr-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-teal-500 focus:bg-white transition"
                />
              </div>
              <button
                onClick={handleAiSearch}
                disabled={isAiSearching || !aiPrompt.trim()}
                className="px-5 py-2.5 bg-gradient-to-r from-teal-600 to-indigo-600 hover:from-teal-700 hover:to-indigo-700 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition disabled:opacity-50"
              >
                {isAiSearching ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Analyzing Directory...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 text-amber-300" />
                    <span>Search with AI</span>
                  </>
                )}
              </button>
            </div>

            {/* Quick Prompt Chips */}
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 pt-1">
              <span className="font-semibold text-slate-600">Try asking:</span>
              {[
                'Find wedding photographers in Ahmedabad under ₹30,000',
                'Affordable traditional Gujarati caterers',
                'Royal Rajasthani decor in Jaipur under ₹1,00,000',
                'Live Bollywood acoustic bands in Mumbai',
              ].map((chip) => (
                <button
                  key={chip}
                  onClick={() => {
                    setAiPrompt(chip);
                  }}
                  className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-[11px] transition"
                >
                  {chip}
                </button>
              ))}
            </div>

            {/* AI Results Box */}
            {aiResults && (
              <div className="mt-4 p-4 rounded-xl bg-indigo-50/60 border border-indigo-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-indigo-600" />
                    <span className="text-xs font-bold text-indigo-900">
                      AI Found {aiResults.total_matching} Matching Verified Vendors
                    </span>
                  </div>
                  <button
                    onClick={handleClearAiSearch}
                    className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold"
                  >
                    Clear AI Search
                  </button>
                </div>

                {aiResults.search_broadened_message && (
                  <p className="text-xs text-amber-800 bg-amber-50 p-2 rounded-lg border border-amber-200">
                    {aiResults.search_broadened_message}
                  </p>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {aiResults.recommendations.map((rec) => (
                    <div
                      key={rec.vendor.id}
                      className="p-3.5 bg-white rounded-xl border border-indigo-100 shadow-xs space-y-2 flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-900 text-sm">{rec.vendor.name}</span>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">
                            {rec.match_score}% Match
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {rec.vendor.category} • {rec.vendor.location} • ₹{rec.vendor.min_price.toLocaleString()} onwards
                        </p>
                        <p className="text-xs text-indigo-950 mt-1.5 leading-relaxed bg-indigo-50/70 p-2 rounded-lg">
                          💡 {rec.match_reason}
                        </p>
                      </div>

                      <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                        <button
                          onClick={() => handleOpenBookingModal(rec.vendor)}
                          className="px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1 transition"
                        >
                          <Briefcase className="w-3.5 h-3.5" />
                          <span>Book / Manage</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Directory Search & Filters Bar */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
            {/* Category Badges */}
            <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin">
              {CATEGORIES.map((cat) => {
                const Icon = cat.icon;
                const isSelected = selectedCategory === cat.value;
                return (
                  <button
                    key={cat.value}
                    onClick={() => setSelectedCategory(cat.value)}
                    className={`px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap flex items-center gap-1.5 transition ${
                      isSelected
                        ? 'bg-teal-600 text-white shadow-sm'
                        : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{cat.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Filter Controls Row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 pt-2 border-t border-slate-100 text-xs">
              {/* Text Search */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter name or service..."
                  className="w-full pl-8 pr-3 py-1.5 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white"
                />
              </div>

              {/* Location */}
              <div>
                <select
                  value={selectedLocation}
                  onChange={(e) => setSelectedLocation(e.target.value)}
                  className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white"
                >
                  {LOCATIONS.map((loc) => (
                    <option key={loc} value={loc}>
                      Location: {loc}
                    </option>
                  ))}
                </select>
              </div>

              {/* Max Budget */}
              <div>
                <input
                  type="number"
                  value={maxPriceFilter}
                  onChange={(e) => setMaxPriceFilter(e.target.value ? Number(e.target.value) : '')}
                  placeholder="Max Price (e.g. 50000)"
                  className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white"
                />
              </div>

              {/* Minimum Rating */}
              <div>
                <select
                  value={minRatingFilter}
                  onChange={(e) => setMinRatingFilter(Number(e.target.value))}
                  className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white"
                >
                  <option value={0}>Any Rating</option>
                  <option value={4.5}>4.5 ★ & above</option>
                  <option value={4.8}>4.8 ★ & above</option>
                </select>
              </div>

              {/* Toggles */}
              <div className="flex items-center gap-3">
                <label className="inline-flex items-center gap-1.5 cursor-pointer font-medium text-slate-700">
                  <input
                    type="checkbox"
                    checked={verifiedOnly}
                    onChange={(e) => setVerifiedOnly(e.target.checked)}
                    className="rounded text-teal-600 focus:ring-teal-500"
                  />
                  <span>Verified Only</span>
                </label>

                <label className="inline-flex items-center gap-1.5 cursor-pointer font-medium text-slate-700">
                  <input
                    type="checkbox"
                    checked={favoritesOnly}
                    onChange={(e) => setFavoritesOnly(e.target.checked)}
                    className="rounded text-rose-500 focus:ring-rose-500"
                  />
                  <span>Favorites</span>
                </label>
              </div>
            </div>
          </div>

          {/* Vendor Cards Grid */}
          {filteredVendors.length === 0 ? (
            <div className="text-center py-16 bg-white rounded-2xl border border-slate-200 p-8 space-y-3">
              <Building className="w-12 h-12 mx-auto text-slate-300 stroke-[1.5]" />
              <h3 className="text-base font-bold text-slate-700">No vendors match your search criteria</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Try clearing your location or price filters, or add a custom vendor using the "Add Custom Vendor" button.
              </p>
              <button
                onClick={() => {
                  setSelectedCategory('All');
                  setSelectedLocation('All');
                  setMaxPriceFilter('');
                  setMinRatingFilter(0);
                  setSearchQuery('');
                  setVerifiedOnly(false);
                  setFavoritesOnly(false);
                }}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition"
              >
                Reset All Filters
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {filteredVendors.map((vendor) => {
                const isCompared = selectedForCompare.includes(vendor.id);
                const bookedItem = bookings.find((b) => b.vendor_id === vendor.id);

                return (
                  <div
                    key={vendor.id}
                    className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 hover:shadow-md transition flex flex-col justify-between space-y-4 relative group"
                  >
                    <div>
                      {/* Top Header: Verification Badge & Favorite Toggle */}
                      <div className="flex items-center justify-between">
                        {vendor.is_verified ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                            <span>Verified Listing</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                            <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                            <span>User Added</span>
                          </span>
                        )}

                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => handleToggleFavorite(vendor.id)}
                            className="p-1 text-slate-400 hover:text-rose-500 transition"
                            title={vendor.is_favorite ? 'Remove Favorite' : 'Save Favorite'}
                          >
                            <Heart
                              className={`w-4 h-4 ${
                                vendor.is_favorite ? 'fill-rose-500 text-rose-500' : ''
                              }`}
                            />
                          </button>
                        </div>
                      </div>

                      {/* Vendor Name & Rating */}
                      <div className="mt-2.5">
                        <div className="flex items-start justify-between gap-2">
                          <h3 className="font-extrabold text-slate-900 text-base leading-snug">
                            {vendor.name}
                          </h3>
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-50 text-amber-800 rounded font-bold text-xs">
                            <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                            <span>{vendor.rating.toFixed(1)}</span>
                          </span>
                          <span className="text-xs text-slate-500">
                            ({vendor.review_count} reviews) • {vendor.experience_years} yrs exp
                          </span>
                        </div>
                      </div>

                      {/* Category & Location */}
                      <div className="flex items-center gap-3 mt-2 text-xs text-slate-600">
                        <span className="font-semibold text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
                          {vendor.category}
                        </span>
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5 text-slate-400" />
                          <span>{vendor.location}</span>
                        </span>
                      </div>

                      {/* Description */}
                      <p className="text-xs text-slate-600 mt-2.5 line-clamp-2 leading-relaxed">
                        {vendor.description}
                      </p>

                      {/* Services Pills */}
                      <div className="flex flex-wrap gap-1 mt-3">
                        {vendor.services_offered.slice(0, 3).map((s, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] font-medium bg-slate-100 text-slate-700 px-2 py-0.5 rounded"
                          >
                            {s}
                          </span>
                        ))}
                        {vendor.services_offered.length > 3 && (
                          <span className="text-[10px] font-medium text-slate-400 px-1 py-0.5">
                            +{vendor.services_offered.length - 3} more
                          </span>
                        )}
                      </div>

                      {/* Price Range */}
                      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400 block">
                            Pricing
                          </span>
                          <span className="text-sm font-extrabold text-slate-900">
                            ₹{vendor.min_price.toLocaleString()}
                            {vendor.max_price > vendor.min_price && (
                              <span className="text-slate-500 text-xs font-normal">
                                {' '}
                                - ₹{vendor.max_price.toLocaleString()}
                              </span>
                            )}
                          </span>
                        </div>

                        {bookedItem && (
                          <span className="text-[11px] font-bold px-2.5 py-1 bg-teal-50 text-teal-700 rounded-lg border border-teal-200">
                            Status: {bookedItem.booking_status}
                          </span>
                        )}
                      </div>

                      {/* Contact Links */}
                      <div className="flex items-center gap-3 mt-2.5 text-xs text-slate-500">
                        <a
                          href={`tel:${vendor.phone}`}
                          className="hover:text-teal-700 flex items-center gap-1"
                        >
                          <Phone className="w-3 h-3 text-slate-400" />
                          <span>{vendor.phone}</span>
                        </a>
                        {vendor.website && (
                          <a
                            href={vendor.website}
                            target="_blank"
                            rel="noreferrer"
                            className="hover:text-indigo-600 flex items-center gap-1 ml-auto"
                          >
                            <span>Portfolio</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    </div>

                    {/* Bottom Actions */}
                    <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                      {/* Compare Checkbox */}
                      <label className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-600 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={isCompared}
                          onChange={() => handleToggleCompare(vendor.id)}
                          className="rounded text-teal-600 focus:ring-teal-500"
                        />
                        <span>Compare</span>
                      </label>

                      {/* Edit / Delete (user-created) & Book / Manage */}
                      <div className="flex items-center gap-1.5">
                        {!vendor.is_verified && (
                          <>
                            <button
                              onClick={() => handleOpenEditVendorModal(vendor)}
                              className="p-1.5 text-slate-400 hover:text-indigo-600 rounded-lg hover:bg-slate-100 transition"
                              title="Edit Vendor"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleDeleteVendor(vendor.id)}
                              className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-slate-100 transition"
                              title="Delete Vendor"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}

                        <button
                          onClick={() => handleOpenBookingModal(vendor)}
                          className="px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-bold flex items-center gap-1 transition shadow-xs"
                        >
                          <Briefcase className="w-3.5 h-3.5" />
                          <span>{bookedItem ? 'Manage Booking' : 'Book for Event'}</span>
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* 2. EVENT BOOKINGS VIEW */}
      {/* ========================================================= */}
      {viewTab === 'bookings' && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div>
                <h3 className="font-extrabold text-slate-900 text-lg">
                  Event Vendor Bookings ({bookings.length})
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Manage negotiated prices, advance deposits, and sync payments with Phase 2 Smart Expense Tracking.
                </p>
              </div>

              {analytics && (
                <div className="flex items-center gap-3 text-xs">
                  <span className="px-3 py-1 bg-slate-100 text-slate-700 rounded-lg font-semibold">
                    Total Agreed: ₹{analytics.total_agreed_cost.toLocaleString()}
                  </span>
                  <span className="px-3 py-1 bg-emerald-50 text-emerald-800 rounded-lg font-semibold border border-emerald-200">
                    Advance Paid: ₹{analytics.total_advance_paid.toLocaleString()}
                  </span>
                  <span className="px-3 py-1 bg-amber-50 text-amber-800 rounded-lg font-semibold border border-amber-200">
                    Remaining: ₹{analytics.total_remaining_payment.toLocaleString()}
                  </span>
                </div>
              )}
            </div>

            {bookings.length === 0 ? (
              <div className="text-center py-16 text-slate-400 space-y-2">
                <Briefcase className="w-12 h-12 mx-auto text-slate-300 stroke-[1.5]" />
                <p className="text-sm font-medium text-slate-700">No vendors booked for this event yet</p>
                <p className="text-xs text-slate-400">
                  Switch to the "Vendor Directory" tab to browse vendors and click "Book for Event" on any vendor card.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                      <th className="py-3 px-3">Vendor</th>
                      <th className="py-3 px-3">Category</th>
                      <th className="py-3 px-3">Status</th>
                      <th className="py-3 px-3">Agreed Price</th>
                      <th className="py-3 px-3">Advance Paid</th>
                      <th className="py-3 px-3">Remaining</th>
                      <th className="py-3 px-3">Booking Date</th>
                      <th className="py-3 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {bookings.map((b) => (
                      <tr key={b.id} className="hover:bg-slate-50/80 transition">
                        <td className="py-3.5 px-3">
                          <span className="font-bold text-slate-900 block">{b.vendor.name}</span>
                          <span className="text-[10px] text-slate-500">{b.vendor.phone}</span>
                        </td>
                        <td className="py-3.5 px-3 font-medium text-slate-700">
                          {b.vendor.category}
                        </td>
                        <td className="py-3.5 px-3">
                          <span
                            className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${
                              b.booking_status === 'Booked'
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : b.booking_status === 'Negotiating'
                                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                : b.booking_status === 'Shortlisted'
                                ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                                : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {b.booking_status}
                          </span>
                        </td>
                        <td className="py-3.5 px-3 font-bold text-slate-900">
                          ₹{b.agreed_price.toLocaleString()}
                        </td>
                        <td className="py-3.5 px-3 font-semibold text-emerald-700">
                          ₹{b.advance_payment.toLocaleString()}
                        </td>
                        <td className="py-3.5 px-3 font-semibold text-amber-700">
                          ₹{b.remaining_payment.toLocaleString()}
                        </td>
                        <td className="py-3.5 px-3 text-slate-600">
                          {b.booking_date}
                        </td>
                        <td className="py-3.5 px-3 text-right space-x-1">
                          {b.advance_payment > 0 && (
                            <button
                              onClick={() => handleRecordAdvanceExpense(b)}
                              disabled={recordingExpenseId === b.id}
                              className="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded-lg font-bold text-[10px] inline-flex items-center gap-1 transition"
                              title="Sync Advance Payment to Phase 2 Smart Expense Tracking"
                            >
                              <CreditCard className="w-3 h-3 text-emerald-600" />
                              <span>{recordingExpenseId === b.id ? 'Recording...' : 'Record as Expense'}</span>
                            </button>
                          )}

                          <button
                            onClick={() => handleOpenBookingModal(b.vendor)}
                            className="p-1.5 text-slate-500 hover:text-indigo-600 rounded-lg hover:bg-slate-100 transition"
                            title="Edit Booking"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => handleDeleteBooking(b.id)}
                            className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-slate-100 transition"
                            title="Remove Booking"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* 3. VENDOR ANALYTICS VIEW */}
      {/* ========================================================= */}
      {viewTab === 'analytics' && (
        <div className="space-y-6">
          {/* 6 KPI Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total Directory</span>
              <p className="text-xl font-extrabold text-slate-900 mt-1">{analytics?.total_directory_vendors || vendors.length}</p>
              <span className="text-[10px] text-teal-600 font-medium">Verified local suppliers</span>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Shortlisted</span>
              <p className="text-xl font-extrabold text-indigo-700 mt-1">{analytics?.shortlisted_count || 0}</p>
              <span className="text-[10px] text-slate-500">Under consideration</span>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Booked Vendors</span>
              <p className="text-xl font-extrabold text-emerald-700 mt-1">{analytics?.booked_count || 0}</p>
              <span className="text-[10px] text-emerald-600 font-medium">Contracts secured</span>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Total Agreed Cost</span>
              <p className="text-lg font-extrabold text-slate-900 mt-1">₹{(analytics?.total_agreed_cost || 0).toLocaleString()}</p>
              <span className="text-[10px] text-slate-500">Contracted commitment</span>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Advance Paid</span>
              <p className="text-lg font-extrabold text-emerald-700 mt-1">₹{(analytics?.total_advance_paid || 0).toLocaleString()}</p>
              <span className="text-[10px] text-emerald-600 font-medium">Deposited to vendors</span>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Remaining Due</span>
              <p className="text-lg font-extrabold text-amber-700 mt-1">₹{(analytics?.total_remaining_payment || 0).toLocaleString()}</p>
              <span className="text-[10px] text-amber-600 font-medium">Pending completion</span>
            </div>
          </div>

          {/* Recharts Visualizations */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Category Spending Bar Chart */}
            <div className="lg:col-span-8 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h4 className="font-bold text-slate-800 text-sm">Vendor Spending Analysis by Category</h4>
                <span className="text-xs text-slate-500">Agreed Cost vs Advance Paid</span>
              </div>

              {analytics && analytics.category_spending.length > 0 ? (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={analytics.category_spending}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                      <XAxis dataKey="category" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} tickFormatter={(val) => `₹${val / 1000}k`} />
                      <Tooltip formatter={(value: any) => `₹${Number(value).toLocaleString()}`} />
                      <Legend />
                      <Bar dataKey="agreed_cost" fill="#0D9488" name="Agreed Cost" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="advance_paid" fill="#10B981" name="Advance Paid" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="remaining_payment" fill="#F59E0B" name="Remaining Payment" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-64 flex flex-col items-center justify-center text-slate-400 space-y-2">
                  <Sliders className="w-8 h-8 stroke-[1.5]" />
                  <p className="text-xs">No vendor bookings recorded yet to visualize spending.</p>
                </div>
              )}
            </div>

            {/* Booking Status Distribution Donut */}
            <div className="lg:col-span-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h4 className="font-bold text-slate-800 text-sm">Booking Status Distribution</h4>
              </div>

              {bookingStatusChartData.length > 0 ? (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={bookingStatusChartData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={80}
                        paddingAngle={4}
                      >
                        {bookingStatusChartData.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-64 flex flex-col items-center justify-center text-slate-400 space-y-2">
                  <Briefcase className="w-8 h-8 stroke-[1.5]" />
                  <p className="text-xs">No booking statuses recorded yet.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* 4. VENDOR BOOKING MODAL */}
      {/* ========================================================= */}
      {bookingModalVendor && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="font-extrabold text-slate-900 text-base">
                  Manage Booking: {bookingModalVendor.name}
                </h3>
                <p className="text-xs text-slate-500">
                  {bookingModalVendor.category} • {bookingModalVendor.location}
                </p>
              </div>
              <button
                onClick={() => setBookingModalVendor(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {bookingError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{bookingError}</span>
              </div>
            )}

            {bookingSuccessNotice && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-xl text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{bookingSuccessNotice}</span>
              </div>
            )}

            <div className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Booking Status</label>
                <select
                  value={bookingStatus}
                  onChange={(e) => setBookingStatus(e.target.value as BookingStatusType)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl bg-slate-50 font-medium"
                >
                  <option value="Shortlisted">Shortlisted</option>
                  <option value="Contacted">Contacted</option>
                  <option value="Negotiating">Negotiating</option>
                  <option value="Booked">Booked</option>
                  <option value="Cancelled">Cancelled</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Agreed Price (₹) *</label>
                  <input
                    type="number"
                    min={0}
                    value={agreedPrice}
                    onChange={(e) => setAgreedPrice(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl font-bold"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Advance Payment (₹) *</label>
                  <input
                    type="number"
                    min={0}
                    max={agreedPrice}
                    value={advancePayment}
                    onChange={(e) => setAdvancePayment(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl font-bold text-emerald-700"
                  />
                </div>
              </div>

              {/* Dynamic Remaining Balance Badge */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
                <span className="font-semibold text-slate-600">Remaining Balance:</span>
                <span className="font-extrabold text-sm text-slate-900">
                  ₹{Math.max(0, agreedPrice - advancePayment).toLocaleString()}
                </span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Booking Date</label>
                <input
                  type="date"
                  value={bookingDate}
                  onChange={(e) => setBookingDate(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Contract Notes / Scope</label>
                <textarea
                  rows={3}
                  value={bookingNotes}
                  onChange={(e) => setBookingNotes(e.target.value)}
                  placeholder="e.g. Package includes 2 candid shooters + 1 drone operator. Final balance due on wedding day."
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl resize-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setBookingModalVendor(null)}
                className="px-4 py-2 border border-slate-200 text-slate-700 hover:bg-slate-100 rounded-xl font-semibold text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveBooking}
                disabled={isSavingBooking}
                className="px-5 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl font-bold text-xs flex items-center gap-1.5 shadow-sm disabled:opacity-50"
              >
                {isSavingBooking ? 'Saving...' : 'Save Booking'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* 5. SIDE-BY-SIDE VENDOR COMPARISON MODAL */}
      {/* ========================================================= */}
      {isCompareModalOpen && comparisonData && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-4xl w-full p-6 shadow-2xl border border-slate-200 space-y-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <ArrowRightLeft className="w-5 h-5 text-indigo-600" />
                <h3 className="font-extrabold text-slate-900 text-base">
                  Side-by-Side Vendor Comparison ({comparisonData.vendors.length} Vendors)
                </h3>
              </div>
              <button
                onClick={() => setIsCompareModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* AI Comparison Summary Box */}
            <div className="p-4 bg-indigo-50/70 border border-indigo-200 rounded-xl space-y-3">
              <div className="flex items-center gap-2 text-indigo-900 font-bold text-xs">
                <Sparkles className="w-4 h-4 text-indigo-600" />
                <span>AI Evaluation Summary</span>
              </div>
              <p className="text-xs text-indigo-950 leading-relaxed">
                {comparisonData.comparison_summary}
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1 text-xs">
                <div className="p-2.5 bg-white rounded-lg border border-indigo-100">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Best Budget</span>
                  <span className="font-bold text-teal-700">{comparisonData.best_budget_option}</span>
                </div>
                <div className="p-2.5 bg-white rounded-lg border border-indigo-100">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Best Rated</span>
                  <span className="font-bold text-amber-700">{comparisonData.best_rated_option}</span>
                </div>
                <div className="p-2.5 bg-white rounded-lg border border-indigo-100">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Best Overall</span>
                  <span className="font-bold text-indigo-700">{comparisonData.best_overall_match}</span>
                </div>
              </div>
            </div>

            {/* Side-by-Side Table Matrix */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border border-slate-200 rounded-xl">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold">
                    <th className="p-3 w-36">Criteria</th>
                    {comparisonData.vendors.map((v) => (
                      <th key={v.id} className="p-3">
                        <span className="text-sm font-extrabold text-slate-900 block">{v.name}</span>
                        <span className="text-[10px] text-slate-500 font-normal">{v.location}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr>
                    <td className="p-3 font-bold text-slate-500 bg-slate-50/50">Price Range</td>
                    {comparisonData.vendors.map((v) => (
                      <td key={v.id} className="p-3 font-extrabold text-slate-900">
                        ₹{v.min_price.toLocaleString()} - ₹{v.max_price.toLocaleString()}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-slate-500 bg-slate-50/50">Rating & Reviews</td>
                    {comparisonData.vendors.map((v) => (
                      <td key={v.id} className="p-3">
                        <span className="font-bold text-amber-600">★ {v.rating.toFixed(1)}</span>
                        <span className="text-slate-500 ml-1">({v.review_count} verified)</span>
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-slate-500 bg-slate-50/50">Experience</td>
                    {comparisonData.vendors.map((v) => (
                      <td key={v.id} className="p-3 font-medium text-slate-800">
                        {v.experience_years} years in business
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-slate-500 bg-slate-50/50">Services</td>
                    {comparisonData.vendors.map((v) => (
                      <td key={v.id} className="p-3">
                        <div className="flex flex-wrap gap-1">
                          {v.services_offered.map((s, idx) => (
                            <span key={idx} className="text-[10px] bg-slate-100 px-1.5 py-0.5 rounded">
                              {s}
                            </span>
                          ))}
                        </div>
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-slate-500 bg-slate-50/50">Pros & Advantages</td>
                    {comparisonData.vendor_evaluations.map((ev) => (
                      <td key={ev.vendor_id} className="p-3">
                        <ul className="space-y-1">
                          {ev.pros.map((p, idx) => (
                            <li key={idx} className="text-[11px] text-emerald-800 flex items-start gap-1">
                              <Check className="w-3 h-3 text-emerald-600 shrink-0 mt-0.5" />
                              <span>{p}</span>
                            </li>
                          ))}
                        </ul>
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="p-3 font-bold text-slate-500 bg-slate-50/50">Tradeoffs / Cons</td>
                    {comparisonData.vendor_evaluations.map((ev) => (
                      <td key={ev.vendor_id} className="p-3">
                        <ul className="space-y-1">
                          {ev.cons.map((c, idx) => (
                            <li key={idx} className="text-[11px] text-slate-600 flex items-start gap-1">
                              <span className="text-slate-400 font-bold">•</span>
                              <span>{c}</span>
                            </li>
                          ))}
                        </ul>
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setIsCompareModalOpen(false)}
                className="px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold"
              >
                Close Comparison
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* 6. ADD / EDIT CUSTOM VENDOR MODAL */}
      {/* ========================================================= */}
      {isVendorModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-extrabold text-slate-900 text-base">
                {editingVendorId ? 'Edit Custom Vendor' : 'Add New Custom Vendor'}
              </h3>
              <button
                onClick={() => setIsVendorModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {vendorFormError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{vendorFormError}</span>
              </div>
            )}

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Business Name *</label>
                <input
                  type="text"
                  value={vendorForm.name}
                  onChange={(e) => setVendorForm({ ...vendorForm, name: e.target.value })}
                  placeholder="e.g. Royal Shahi Caterers"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Category *</label>
                  <select
                    value={vendorForm.category}
                    onChange={(e) => setVendorForm({ ...vendorForm, category: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl bg-slate-50"
                  >
                    {CATEGORIES.filter((c) => c.value !== 'All').map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Location / City *</label>
                  <input
                    type="text"
                    value={vendorForm.location}
                    onChange={(e) => setVendorForm({ ...vendorForm, location: e.target.value })}
                    placeholder="e.g. Ahmedabad, Gujarat"
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Description *</label>
                <textarea
                  rows={2}
                  value={vendorForm.description}
                  onChange={(e) => setVendorForm({ ...vendorForm, description: e.target.value })}
                  placeholder="Describe specialties, equipment, and packages..."
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl resize-none"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Services Offered (comma-separated)</label>
                <input
                  type="text"
                  value={servicesInput}
                  onChange={(e) => setServicesInput(e.target.value)}
                  placeholder="Candid Photography, Drone Shoots, Pre-wedding Video"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Min Price (₹)</label>
                  <input
                    type="number"
                    min={0}
                    value={vendorForm.min_price}
                    onChange={(e) => setVendorForm({ ...vendorForm, min_price: Number(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl font-bold"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Max Price (₹)</label>
                  <input
                    type="number"
                    min={0}
                    value={vendorForm.max_price}
                    onChange={(e) => setVendorForm({ ...vendorForm, max_price: Number(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl font-bold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Rating (1-5)</label>
                  <input
                    type="number"
                    step="0.1"
                    min={1}
                    max={5}
                    value={vendorForm.rating}
                    onChange={(e) => setVendorForm({ ...vendorForm, rating: Number(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Review Count</label>
                  <input
                    type="number"
                    min={0}
                    value={vendorForm.review_count}
                    onChange={(e) => setVendorForm({ ...vendorForm, review_count: Number(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Experience (Yrs)</label>
                  <input
                    type="number"
                    min={0}
                    value={vendorForm.experience_years}
                    onChange={(e) => setVendorForm({ ...vendorForm, experience_years: Number(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Contact Phone *</label>
                  <input
                    type="text"
                    value={vendorForm.phone}
                    onChange={(e) => setVendorForm({ ...vendorForm, phone: e.target.value })}
                    placeholder="+91 98765 43210"
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Contact Email *</label>
                  <input
                    type="email"
                    value={vendorForm.email}
                    onChange={(e) => setVendorForm({ ...vendorForm, email: e.target.value })}
                    placeholder="contact@vendor.in"
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Website / Portfolio Link</label>
                <input
                  type="url"
                  value={vendorForm.website}
                  onChange={(e) => setVendorForm({ ...vendorForm, website: e.target.value })}
                  placeholder="https://vendorportfolio.com"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setIsVendorModalOpen(false)}
                className="px-4 py-2 border border-slate-200 text-slate-700 hover:bg-slate-100 rounded-xl font-semibold text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveVendorForm}
                className="px-5 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl font-bold text-xs"
              >
                {editingVendorId ? 'Update Vendor' : 'Add to Directory'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default FindVendorsTab;
