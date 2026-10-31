import React, { useState, useEffect, useMemo } from 'react';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Plus,
  Search,
  Filter,
  Download,
  Trash2,
  Edit2,
  Calendar,
  CreditCard,
  Building2,
  PieChart as PieIcon,
  BarChart2,
  X,
  Check,
  FileSpreadsheet,
  FileText,
  Layers,
  ArrowUpDown,
  Tag,
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
  ExpenseItem,
  ExpenseFormData,
  ExpenseTrackingSummary,
  PaymentStatus,
} from '../types';
import {
  getExpenses,
  getExpenseSummary,
  createExpense,
  updateExpense,
  deleteExpense,
  getExportExpensesCsvUrl,
  getExportExpensesPdfUrl,
} from '../api';

interface ExpenseTabProps {
  plan: FullEventPlan;
  onRefreshPlan?: () => void;
}

const PIE_COLORS = [
  '#0d9488', '#0284c7', '#8b5cf6', '#ec4899', '#f59e0b',
  '#10b981', '#6366f1', '#14b8a6', '#f97316', '#64748b',
  '#84cc16', '#06b6d4', '#d946ef', '#e11d48'
];

const PAYMENT_METHODS = [
  'Bank Transfer / NEFT / RTGS',
  'UPI / GPay / PhonePe',
  'Credit Card',
  'Debit Card',
  'Cash',
  'Cheque',
  'Other',
];

export const ExpenseTab: React.FC<ExpenseTabProps> = ({ plan, onRefreshPlan }) => {
  const [expenses, setExpenses] = useState<ExpenseItem[]>([]);
  const [summary, setSummary] = useState<ExpenseTrackingSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [sortBy, setSortBy] = useState<'date_desc' | 'date_asc' | 'amount_desc' | 'amount_asc'>('date_desc');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState<ExpenseItem | null>(null);
  const [formData, setFormData] = useState<ExpenseFormData>({
    expense_name: '',
    category: plan.budget.items[0]?.category || 'General',
    amount: 0,
    expense_date: new Date().toISOString().split('T')[0],
    payment_status: 'Paid',
    payment_method: 'Bank Transfer / NEFT / RTGS',
    vendor_name: '',
    notes: '',
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Export dropdown state
  const [showExportMenu, setShowExportMenu] = useState(false);

  useEffect(() => {
    loadData();
  }, [plan.event_id, plan.budget]);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [expList, sumData] = await Promise.all([
        getExpenses(plan.event_id),
        getExpenseSummary(plan.event_id),
      ]);
      setExpenses(expList);
      setSummary(sumData);
    } catch (err: any) {
      console.error('Failed to load expense tracking data:', err);
      setError(err.message || 'Failed to load expense tracking data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenAddModal = () => {
    setEditingExpense(null);
    setFormData({
      expense_name: '',
      category: plan.budget.items[0]?.category || 'General',
      amount: 0,
      expense_date: new Date().toISOString().split('T')[0],
      payment_status: 'Paid',
      payment_method: 'Bank Transfer / NEFT / RTGS',
      vendor_name: '',
      notes: '',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (expense: ExpenseItem) => {
    setEditingExpense(expense);
    setFormData({
      expense_name: expense.expense_name,
      category: expense.category,
      amount: expense.amount,
      expense_date: expense.expense_date,
      payment_status: expense.payment_status,
      payment_method: expense.payment_method || 'Bank Transfer / NEFT / RTGS',
      vendor_name: expense.vendor_name || '',
      notes: expense.notes || '',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSaveExpense = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.expense_name.trim()) {
      setFormError('Expense name is required.');
      return;
    }
    if (!formData.category.trim()) {
      setFormError('Category is required.');
      return;
    }
    if (isNaN(Number(formData.amount)) || Number(formData.amount) <= 0) {
      setFormError('Amount must be a positive number greater than zero.');
      return;
    }
    if (!formData.expense_date) {
      setFormError('Expense date is required.');
      return;
    }

    setIsSubmitting(true);
    setFormError(null);
    try {
      if (editingExpense) {
        await updateExpense(plan.event_id, editingExpense.id, {
          ...formData,
          amount: Number(formData.amount),
        });
      } else {
        await createExpense(plan.event_id, {
          ...formData,
          amount: Number(formData.amount),
        });
      }
      setIsModalOpen(false);
      await loadData();
      if (onRefreshPlan) {
        onRefreshPlan();
      }
    } catch (err: any) {
      setFormError(err.message || 'Failed to save expense');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteExpense = async (expenseId: string, expenseName: string) => {
    if (!window.confirm(`Are you sure you want to delete "${expenseName}"?`)) {
      return;
    }
    try {
      await deleteExpense(plan.event_id, expenseId);
      await loadData();
      if (onRefreshPlan) {
        onRefreshPlan();
      }
    } catch (err: any) {
      alert(`Failed to delete expense: ${err.message}`);
    }
  };

  // Filtered and Sorted Expenses
  const filteredExpenses = useMemo(() => {
    return expenses
      .filter(exp => {
        const matchesCategory =
          selectedCategory === 'all' ||
          exp.category.toLowerCase() === selectedCategory.toLowerCase();

        const matchesStatus =
          selectedStatus === 'all' ||
          exp.payment_status.toLowerCase() === selectedStatus.toLowerCase();

        const query = searchQuery.toLowerCase().trim();
        const matchesSearch =
          !query ||
          exp.expense_name.toLowerCase().includes(query) ||
          exp.category.toLowerCase().includes(query) ||
          (exp.vendor_name && exp.vendor_name.toLowerCase().includes(query)) ||
          (exp.notes && exp.notes.toLowerCase().includes(query));

        return matchesCategory && matchesStatus && matchesSearch;
      })
      .sort((a, b) => {
        if (sortBy === 'date_desc') {
          return new Date(b.expense_date).getTime() - new Date(a.expense_date).getTime();
        }
        if (sortBy === 'date_asc') {
          return new Date(a.expense_date).getTime() - new Date(b.expense_date).getTime();
        }
        if (sortBy === 'amount_desc') {
          return b.amount - a.amount;
        }
        if (sortBy === 'amount_asc') {
          return a.amount - b.amount;
        }
        return 0;
      });
  }, [expenses, selectedCategory, selectedStatus, searchQuery, sortBy]);

  // Chart Data: Planned vs Actual
  const barChartData = useMemo(() => {
    if (!summary) return [];
    return summary.categories.map(c => ({
      category: c.category.length > 12 ? c.category.substring(0, 10) + '..' : c.category,
      fullName: c.category,
      planned: c.planned_budget,
      actual: c.actual_spent,
      difference: c.difference,
      isOverspent: c.is_overspent,
    }));
  }, [summary]);

  // Chart Data: Expense Distribution Pie Chart
  const pieChartData = useMemo(() => {
    if (!summary) return [];
    return summary.categories
      .filter(c => c.actual_spent > 0)
      .map(c => ({
        name: c.category,
        value: c.actual_spent,
      }));
  }, [summary]);

  // Category options for dropdown
  const categoryOptions = useMemo(() => {
    const set = new Set<string>();
    plan.budget.items.forEach(i => set.add(i.category));
    expenses.forEach(e => set.add(e.category));
    return Array.from(set);
  }, [plan.budget.items, expenses]);

  // Vendor options for dropdown
  const vendorOptions = useMemo(() => {
    const list: string[] = [];
    plan.vendors.forEach(v => {
      if (v.vendor_name && v.vendor_name.trim()) list.push(v.vendor_name.trim());
    });
    return Array.from(new Set(list));
  }, [plan.vendors]);

  return (
    <div className="space-y-6">

      {/* ========================================================= */}
      {/* 1. TOP HEADER & ACTION BUTTONS */}
      {/* ========================================================= */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-teal-600" />
            <h3 className="text-base font-bold text-slate-900">Smart Expense Tracking</h3>
            <span className="px-2.5 py-0.5 text-2xs font-bold uppercase tracking-wider bg-teal-50 text-teal-700 border border-teal-200 rounded-full">
              Real-time Ledger
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Log actual expenses, compare category spending against planned allocations, and track fiscal health.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Export Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-all shadow-2xs"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>Export Records</span>
            </button>

            {showExportMenu && (
              <div
                className="absolute right-0 mt-2 w-48 bg-white border border-slate-200 rounded-xl shadow-lg py-1.5 z-20 animate-in fade-in duration-200"
                onMouseLeave={() => setShowExportMenu(false)}
              >
                <a
                  href={getExportExpensesCsvUrl(plan.event_id)}
                  download
                  onClick={() => setShowExportMenu(false)}
                  className="flex items-center gap-2 px-3.5 py-2 text-xs text-slate-700 hover:bg-teal-50 hover:text-teal-900 transition-colors"
                >
                  <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                  <span>Download as CSV</span>
                </a>
                <a
                  href={getExportExpensesPdfUrl(plan.event_id)}
                  target="_blank"
                  rel="noreferrer"
                  onClick={() => setShowExportMenu(false)}
                  className="flex items-center gap-2 px-3.5 py-2 text-xs text-slate-700 hover:bg-teal-50 hover:text-teal-900 transition-colors"
                >
                  <FileText className="w-4 h-4 text-rose-600" />
                  <span>Download as PDF Report</span>
                </a>
              </div>
            )}
          </div>

          {/* Add Expense Button */}
          <button
            onClick={handleOpenAddModal}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 rounded-xl shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add New Expense</span>
          </button>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 2. FOUR SUMMARY CARDS */}
      {/* ========================================================= */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Total Event Budget */}
          <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs space-y-1">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-2xs font-bold uppercase tracking-wider">Total Event Budget</span>
              <DollarSign className="w-4 h-4 text-slate-500" />
            </div>
            <p className="text-2xl font-extrabold text-slate-900">
              {summary.total_event_budget.toLocaleString()} {summary.currency}
            </p>
            <span className="text-2xs text-slate-500 block">
              Ceiling from active plan
            </span>
          </div>

          {/* Card 2: Total Actual Expenses */}
          <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs space-y-1">
            <div className="flex items-center justify-between text-teal-600">
              <span className="text-2xs font-bold uppercase tracking-wider">Total Actual Expenses</span>
              <CreditCard className="w-4 h-4" />
            </div>
            <p className="text-2xl font-extrabold text-teal-700">
              {summary.total_actual_spent.toLocaleString()} {summary.currency}
            </p>
            <span className="text-2xs text-slate-500 block">
              {summary.paid_expenses_count} paid • {summary.pending_expenses_count} pending
            </span>
          </div>

          {/* Card 3: Remaining Budget */}
          <div className={`p-4 rounded-2xl border shadow-xs space-y-1 ${
            summary.is_over_budget
              ? 'bg-rose-50/70 border-rose-200 text-rose-950'
              : 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-2xs font-bold uppercase tracking-wider">
                {summary.is_over_budget ? 'Budget Deficit / Overspent' : 'Remaining Budget / Savings'}
              </span>
              {summary.is_over_budget ? (
                <TrendingUp className="w-4 h-4 text-rose-600" />
              ) : (
                <TrendingDown className="w-4 h-4 text-emerald-600" />
              )}
            </div>
            <p className="text-2xl font-extrabold">
              {summary.remaining_budget >= 0 ? '+' : ''}
              {summary.remaining_budget.toLocaleString()} {summary.currency}
            </p>
            <span className="text-2xs font-semibold block opacity-80">
              {summary.is_over_budget
                ? `Exceeded planned budget by ${summary.over_budget_amount.toLocaleString()} ${summary.currency}`
                : `Surplus reserve available for contingencies`}
            </span>
          </div>

          {/* Card 4: Budget Utilization Percentage */}
          <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs space-y-2">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-2xs font-bold uppercase tracking-wider">Budget Utilization</span>
              <span className={`text-xs font-bold ${
                summary.is_over_budget
                  ? 'text-rose-600'
                  : summary.budget_utilization_percentage >= 80
                  ? 'text-amber-600'
                  : 'text-teal-700'
              }`}>
                {summary.budget_utilization_percentage.toFixed(1)}%
              </span>
            </div>
            {/* Progress Bar */}
            <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
              <div
                className={`h-2.5 rounded-full transition-all duration-500 ${
                  summary.is_over_budget
                    ? 'bg-rose-600'
                    : summary.budget_utilization_percentage >= 80
                    ? 'bg-amber-500'
                    : 'bg-teal-600'
                }`}
                style={{ width: `${Math.min(100, summary.budget_utilization_percentage)}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-2xs text-slate-400">
              <span>0%</span>
              <span className="text-amber-600 font-semibold">80% Threshold</span>
              <span>100%</span>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* 3. INTELLIGENT BUDGET ALERTS */}
      {/* ========================================================= */}
      {summary && summary.alerts.length > 0 && (
        <div className="space-y-2">
          {summary.alerts.map((alert, idx) => (
            <div
              key={idx}
              className={`p-3.5 rounded-xl border flex items-start gap-3 text-xs shadow-2xs animate-in fade-in duration-300 ${
                alert.level === 'danger'
                  ? 'bg-rose-50/90 border-rose-200 text-rose-900'
                  : alert.level === 'warning'
                  ? 'bg-amber-50/90 border-amber-200 text-amber-900'
                  : 'bg-teal-50/90 border-teal-200 text-teal-900'
              }`}
            >
              {alert.level === 'danger' ? (
                <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
              ) : alert.level === 'warning' ? (
                <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-teal-600 flex-shrink-0 mt-0.5" />
              )}
              <div className="flex-1">
                <span className="font-bold block">{alert.title}</span>
                <span className="opacity-90">{alert.message}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ========================================================= */}
      {/* 4. DATA VISUALIZATION SECTION */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* A. Planned vs Actual Bar Chart */}
        <div className="lg:col-span-7 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <BarChart2 className="w-4 h-4 text-teal-600" />
                <span>Planned vs Actual Category Spending</span>
              </h4>
              <p className="text-2xs text-slate-400">Direct comparison across allocated categories</p>
            </div>
            <div className="flex items-center gap-3 text-xs font-medium">
              <span className="flex items-center gap-1 text-slate-600">
                <span className="w-2.5 h-2.5 bg-teal-600 rounded-xs inline-block" /> Planned
              </span>
              <span className="flex items-center gap-1 text-slate-600">
                <span className="w-2.5 h-2.5 bg-indigo-500 rounded-xs inline-block" /> Actual Spent
              </span>
            </div>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barChartData} margin={{ top: 10, right: 10, left: 10, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="category" angle={-25} textAnchor="end" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={val => `${val / 1000}k`} />
                <Tooltip
                  formatter={(val: number, name: string) => [
                    `${val.toLocaleString()} ${plan.budget.currency}`,
                    name === 'planned' ? 'Planned Budget' : 'Actual Spent',
                  ]}
                />
                <Bar dataKey="planned" fill="#0d9488" radius={[4, 4, 0, 0]} name="planned" />
                <Bar dataKey="actual" fill="#6366f1" radius={[4, 4, 0, 0]} name="actual" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* B. Actual Expense Distribution Pie Chart */}
        <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-3">
          <div>
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <PieIcon className="w-4 h-4 text-indigo-600" />
              <span>Actual Expense Distribution</span>
            </h4>
            <p className="text-2xs text-slate-400">Breakdown of recorded expenditures</p>
          </div>

          <div className="h-64">
            {pieChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieChartData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(val: number) => [`${val.toLocaleString()} ${plan.budget.currency}`, 'Spent']}
                  />
                  <Legend wrapperStyle={{ fontSize: '10px' }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-4">
                <CreditCard className="w-8 h-8 text-slate-300 mb-2" />
                <p className="text-xs font-medium text-slate-500">No actual expenses logged yet.</p>
                <p className="text-2xs text-slate-400 mt-0.5">Click "Add New Expense" to begin tracking.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 5. CATEGORY-WISE PLANNED VS ACTUAL TABLE */}
      {/* ========================================================= */}
      {summary && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="px-5 py-3.5 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Category-wise Planned vs Actual Analysis
              </h4>
              <p className="text-2xs text-slate-500">
                Detailed variance, remaining funds, and overspending breakdown
              </p>
            </div>
            <span className="text-2xs font-semibold text-slate-400">
              {summary.categories.length} Categories Monitored
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider border-b border-slate-200 font-semibold text-2xs">
                <tr>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3 text-right">Planned ({summary.currency})</th>
                  <th className="px-4 py-3 text-right">Actual Spent ({summary.currency})</th>
                  <th className="px-4 py-3 text-right">Remaining ({summary.currency})</th>
                  <th className="px-4 py-3 text-right">Variance / Savings</th>
                  <th className="px-4 py-3 text-center">Utilization</th>
                  <th className="px-4 py-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {summary.categories.map((c, idx) => {
                  return (
                    <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-4 py-3 font-semibold text-slate-900">
                        {c.category}
                      </td>
                      <td className="px-4 py-3 text-right text-slate-600 font-medium">
                        {c.planned_budget.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="px-4 py-3 text-right font-bold text-slate-900">
                        {c.actual_spent.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="px-4 py-3 text-right text-slate-600 font-medium">
                        {c.remaining.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="px-4 py-3 text-right font-bold">
                        {c.is_overspent ? (
                          <span className="text-rose-600 flex items-center justify-end gap-1">
                            <TrendingUp className="w-3.5 h-3.5" />
                            +{c.overspent_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </span>
                        ) : (
                          <span className="text-emerald-600 flex items-center justify-end gap-1">
                            <TrendingDown className="w-3.5 h-3.5" />
                            {c.difference >= 0 ? '-' : ''}
                            {c.difference.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-2xs font-bold ${
                          c.is_overspent
                            ? 'bg-rose-100 text-rose-800'
                            : c.utilization_percentage >= 85
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-teal-50 text-teal-800'
                        }`}>
                          {c.utilization_percentage.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {c.is_overspent ? (
                          <span className="inline-flex items-center gap-1 text-2xs font-bold text-rose-600">
                            <AlertCircle className="w-3 h-3" />
                            Overspent
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-2xs font-semibold text-emerald-700">
                            <Check className="w-3 h-3" />
                            On Track
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* 6. EXPENSE TRANSACTION HISTORY & MANAGEMENT */}
      {/* ========================================================= */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden space-y-4 p-5">

        {/* Table Controls (Search, Filters, Sort) */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Expense Transaction History
            </h4>
            <p className="text-2xs text-slate-500">
              {filteredExpenses.length} of {expenses.length} transactions displayed
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search expense, vendor..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-teal-500 w-44 sm:w-56"
              />
            </div>

            {/* Category Filter */}
            <select
              value={selectedCategory}
              onChange={e => setSelectedCategory(e.target.value)}
              className="px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-teal-500 text-slate-700"
            >
              <option value="all">All Categories</option>
              {categoryOptions.map((c, i) => (
                <option key={i} value={c}>
                  {c}
                </option>
              ))}
            </select>

            {/* Status Filter */}
            <select
              value={selectedStatus}
              onChange={e => setSelectedStatus(e.target.value)}
              className="px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-teal-500 text-slate-700"
            >
              <option value="all">All Statuses</option>
              <option value="Paid">Paid</option>
              <option value="Pending">Pending</option>
            </select>

            {/* Sort Dropdown */}
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as any)}
              className="px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-teal-500 text-slate-700"
            >
              <option value="date_desc">Date: Newest First</option>
              <option value="date_asc">Date: Oldest First</option>
              <option value="amount_desc">Amount: Highest First</option>
              <option value="amount_asc">Amount: Lowest First</option>
            </select>
          </div>
        </div>

        {/* Transactions Table */}
        <div className="overflow-x-auto border border-slate-100 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider border-b border-slate-200 font-semibold text-2xs">
              <tr>
                <th className="px-4 py-3">Expense Name & Details</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Vendor</th>
                <th className="px-4 py-3 text-right">Amount ({plan.budget.currency})</th>
                <th className="px-4 py-3 text-center">Payment Status</th>
                <th className="px-4 py-3 text-center">Method</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredExpenses.length > 0 ? (
                filteredExpenses.map(exp => (
                  <tr key={exp.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">{exp.expense_name}</div>
                      {exp.notes && (
                        <p className="text-2xs text-slate-400 mt-0.5 line-clamp-1">{exp.notes}</p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md font-medium text-2xs">
                        {exp.category}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600 font-mono text-2xs">
                      {exp.expense_date}
                    </td>
                    <td className="px-4 py-3 text-slate-700 font-medium">
                      {exp.vendor_name || <span className="text-slate-300">-</span>}
                    </td>
                    <td className="px-4 py-3 text-right font-bold text-slate-900">
                      {exp.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 text-2xs font-bold rounded-full ${
                        exp.payment_status === 'Paid'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {exp.payment_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-2xs text-slate-500">
                      {exp.payment_method || '-'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenEditModal(exp)}
                          title="Edit Expense"
                          className="p-1 text-slate-400 hover:text-teal-600 hover:bg-teal-50 rounded-lg transition-colors"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteExpense(exp.id, exp.expense_name)}
                          title="Delete Expense"
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
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                    <p className="text-xs font-medium">No expenses found matching current filters.</p>
                    <button
                      onClick={handleOpenAddModal}
                      className="mt-2 text-xs font-semibold text-teal-600 hover:underline inline-flex items-center gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" /> Log first expense
                    </button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 7. ADD / EDIT EXPENSE MODAL */}
      {/* ========================================================= */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in zoom-in-95 duration-200">

            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-teal-600" />
                <h3 className="text-base font-bold text-slate-900">
                  {editingExpense ? 'Edit Expense Record' : 'Add New Expense Record'}
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

            <form onSubmit={handleSaveExpense} className="space-y-3.5 text-xs">

              {/* Expense Name */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Expense Name / Description <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Venue Advance Deposit, DJ Setup Fee"
                  value={formData.expense_name}
                  onChange={e => setFormData({ ...formData, expense_name: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900"
                />
              </div>

              {/* Category & Amount Row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Category <span className="text-rose-500">*</span>
                  </label>
                  <select
                    value={formData.category}
                    onChange={e => setFormData({ ...formData, category: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900"
                  >
                    {categoryOptions.map((c, i) => (
                      <option key={i} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Amount ({plan.budget.currency}) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    placeholder="0.00"
                    value={formData.amount === 0 ? '' : formData.amount}
                    onChange={e => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900 font-bold"
                  />
                </div>
              </div>

              {/* Date & Payment Status */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Expense Date <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={formData.expense_date}
                    onChange={e => setFormData({ ...formData, expense_date: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Payment Status <span className="text-rose-500">*</span>
                  </label>
                  <div className="flex gap-2 mt-1">
                    {(['Paid', 'Pending'] as PaymentStatus[]).map(status => (
                      <button
                        key={status}
                        type="button"
                        onClick={() => setFormData({ ...formData, payment_status: status })}
                        className={`flex-1 py-1.5 rounded-lg font-bold border transition-all ${
                          formData.payment_status === status
                            ? status === 'Paid'
                              ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                              : 'bg-amber-500 text-white border-amber-500 shadow-xs'
                            : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                        }`}
                      >
                        {status}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Payment Method & Vendor */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Payment Method
                  </label>
                  <select
                    value={formData.payment_method || ''}
                    onChange={e => setFormData({ ...formData, payment_method: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900"
                  >
                    {PAYMENT_METHODS.map((m, i) => (
                      <option key={i} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Vendor / Payee
                  </label>
                  <input
                    type="text"
                    list="vendor-datalist"
                    placeholder="e.g. Royal Palace Caterers"
                    value={formData.vendor_name || ''}
                    onChange={e => setFormData({ ...formData, vendor_name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900"
                  />
                  <datalist id="vendor-datalist">
                    {vendorOptions.map((v, i) => (
                      <option key={i} value={v} />
                    ))}
                  </datalist>
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Notes / Receipt Reference (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="Receipt number, invoice reference, contract terms, etc."
                  value={formData.notes || ''}
                  onChange={e => setFormData({ ...formData, notes: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900"
                />
              </div>

              {/* Modal Action Buttons */}
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
                  className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-teal-600 hover:bg-teal-700 active:scale-95 disabled:opacity-50 rounded-xl shadow-sm transition-all"
                >
                  <Check className="w-4 h-4" />
                  <span>{editingExpense ? 'Save Changes' : 'Record Expense'}</span>
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

    </div>
  );
};
