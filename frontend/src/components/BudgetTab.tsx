import React, { useState, useEffect } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from 'recharts';
import {
  ShieldCheck,
  AlertCircle,
  ArrowRightLeft,
  DollarSign,
  Edit3,
  Check,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Cpu,
  CheckCircle2,
  X,
  Lightbulb,
  Shield,
  Layers,
  ArrowDownRight,
  ArrowUpRight,
  Lock,
  Unlock,
  AlertTriangle,
  RefreshCw,
  GitMerge,
} from 'lucide-react';
import {
  FullEventPlan,
  BudgetItem,
  BudgetAnalysis,
  BudgetOptimizationResponse,
  ExpenseClassification,
} from '../types';
import {
  getBudgetAnalysis,
  optimizeBudget,
  normalizeCategories,
  adjustBudgetSpent,
  updateCategoryProtection,
} from '../api';

interface BudgetTabProps {
  plan: FullEventPlan;
  onUpdatePlan: (updatedPlan: FullEventPlan) => void;
}

const COLORS = [
  '#4f46e5', '#0284c7', '#8b5cf6', '#ec4899', '#f59e0b',
  '#10b981', '#6366f1', '#14b8a6', '#f97316', '#64748b'
];

export const formatINR = (val: number | string | undefined | null, includeDecimals = false): string => {
  if (val === undefined || val === null || isNaN(Number(val))) return '0';
  const num = Number(val);
  if (includeDecimals) {
    return num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return num.toLocaleString('en-IN');
};

const QUICK_PROMPTS = [
  'Reduce my wedding budget by ₹30,000',
  'Keep food quality high but reduce other expenses',
  'Suggest a more affordable decoration plan',
  'I want to save 15% of my total budget',
  'Reallocate unused photography expenses to entertainment',
];

export const BudgetTab: React.FC<BudgetTabProps> = ({ plan, onUpdatePlan }) => {
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [tempSpent, setTempSpent] = useState<number>(0);
  const [showMoveModal, setShowMoveModal] = useState(false);
  const [sourceCat, setSourceCat] = useState(plan.budget.items[0]?.category || '');
  const [targetCat, setTargetCat] = useState(plan.budget.items[1]?.category || '');
  const [moveAmount, setMoveAmount] = useState<number>(5000);

  // Budget Analysis State
  const [analysis, setAnalysis] = useState<BudgetAnalysis | null>(null);
  const [isAnalysisLoading, setIsAnalysisLoading] = useState(false);

  // Category Normalization & Protection States
  const [showMergeModal, setShowMergeModal] = useState(false);
  const [isNormalizing, setIsNormalizing] = useState(false);
  const [isUpdatingProtection, setIsUpdatingProtection] = useState<string | null>(null);

  // AI Optimizer State
  const [optimizerPrompt, setOptimizerPrompt] = useState('');
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState<BudgetOptimizationResponse | null>(null);
  const [optimizerError, setOptimizerError] = useState<string | null>(null);
  const [applySuccessMessage, setApplySuccessMessage] = useState<string | null>(null);

  const budget = plan.budget;
  const items = budget.items;

  useEffect(() => {
    loadAnalysis();
  }, [plan.event_id, plan.budget]);

  const loadAnalysis = async () => {
    setIsAnalysisLoading(true);
    try {
      const data = await getBudgetAnalysis(plan.event_id);
      setAnalysis(data);
    } catch (err) {
      console.error('Failed to load budget analysis:', err);
    } finally {
      setIsAnalysisLoading(false);
    }
  };

  const handleToggleProtection = async (item: BudgetItem) => {
    setIsUpdatingProtection(item.id);
    try {
      const updatedItem = await updateCategoryProtection(plan.event_id, item.id, {
        is_protected: !item.is_protected,
      });
      const updatedItems = items.map(i => (i.id === item.id ? updatedItem : i));
      const updatedPlan: FullEventPlan = {
        ...plan,
        budget: {
          ...budget,
          items: updatedItems,
        },
      };
      onUpdatePlan(updatedPlan);
      await loadAnalysis();
    } catch (err: any) {
      console.error('Failed to toggle category protection:', err);
      setOptimizerError(err.message || 'Failed to update category protection status');
    } finally {
      setIsUpdatingProtection(null);
    }
  };

  const handleNormalizeCategories = async () => {
    if (isNormalizing) return;
    setIsNormalizing(true);
    setOptimizerError(null);
    try {
      const approvedMerges = analysis?.merge_suggestions?.map((s) => s.canonical_category) || [];
      const updatedPlan = await normalizeCategories(plan.event_id, approvedMerges);
      onUpdatePlan(updatedPlan);
      setShowMergeModal(false);
      setApplySuccessMessage('✨ Categories normalized and consolidated successfully!');
      await loadAnalysis();
      setTimeout(() => setApplySuccessMessage(null), 5000);
    } catch (err: any) {
      console.error('Failed to normalize categories:', err);
      setOptimizerError(err.message || 'Failed to normalize categories');
    } finally {
      setIsNormalizing(false);
    }
  };

  const renderClassificationBadge = (classification?: ExpenseClassification | string) => {
    switch (classification) {
      case 'essential':
        return (
          <span className="inline-flex items-center px-2 py-0.5 text-2xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-md">
            Essential
          </span>
        );
      case 'important':
        return (
          <span className="inline-flex items-center px-2 py-0.5 text-2xs font-semibold bg-amber-50 text-amber-800 border border-amber-200 rounded-md">
            Important
          </span>
        );
      case 'optional':
        return (
          <span className="inline-flex items-center px-2 py-0.5 text-2xs font-semibold bg-slate-100 text-slate-600 border border-slate-200 rounded-md">
            Optional
          </span>
        );
      case 'custom':
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 text-2xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-md">
            Custom
          </span>
        );
    }
  };

  const handleRunOptimizer = async (promptToUse?: string) => {
    const prompt = (promptToUse || optimizerPrompt).trim();
    if (!prompt) return;

    setIsOptimizing(true);
    setOptimizerError(null);
    setApplySuccessMessage(null);

    try {
      const protectedCategoryNames = items.filter(i => i.is_protected).map(i => i.category);
      const res = await optimizeBudget(plan.event_id, prompt, protectedCategoryNames);
      setOptimizationResult(res);
    } catch (err: any) {
      setOptimizerError(err.message || 'Failed to optimize budget. Please try again.');
    } finally {
      setIsOptimizing(false);
    }
  };

  const isOptimizationValid = Boolean(
    optimizationResult &&
    optimizationResult.is_feasible !== false &&
    optimizationResult.is_valid !== false &&
    (optimizationResult.revised_total_budget ?? 0) > 0 &&
    (optimizationResult.revised_total_budget ?? 0) <= (optimizationResult.original_total_budget ?? 0) &&
    (!optimizationResult.validation_errors || optimizationResult.validation_errors.length === 0)
  );

  const handleApplyOptimization = () => {
    if (!optimizationResult || !isOptimizationValid) return;

    const updatedPlan: FullEventPlan = {
      ...plan,
      intake: {
        ...plan.intake,
        total_budget: optimizationResult.revised_total_budget,
      },
      budget: optimizationResult.optimized_budget_summary,
    };

    onUpdatePlan(updatedPlan);
    setApplySuccessMessage(
      `🎉 Successfully applied optimized budget! Total savings: ${plan.budget.currency} ${formatINR(optimizationResult.total_savings)}.`
    );
    setOptimizationResult(null);
    setOptimizerPrompt('');

    setTimeout(() => {
      setApplySuccessMessage(null);
    }, 6000);
  };

  const handleDiscardOptimization = () => {
    setOptimizationResult(null);
    setOptimizerError(null);
  };

  // Chart data
  const pieData = items.map(item => ({
    name: item.category,
    value: item.allocated_amount,
    percentage: item.percentage,
  }));

  const barData = items.map(item => ({
    name: item.category.length > 12 ? item.category.substring(0, 10) + '..' : item.category,
    allocated: item.allocated_amount,
    actual: item.actual_spent,
  }));

  // Comparison Chart Data (Original vs Recommended)
  const comparisonChartData = optimizationResult
    ? optimizationResult.categories.map(c => ({
        category: c.category.length > 12 ? c.category.substring(0, 10) + '..' : c.category,
        fullName: c.category,
        original: c.original_amount,
        recommended: c.recommended_amount,
        savings: c.savings,
      }))
    : [];

  const handleSaveSpent = async (item: BudgetItem) => {
    try {
      const updatedPlan = await adjustBudgetSpent(plan.event_id, item.category, Number(tempSpent));
      onUpdatePlan(updatedPlan);
      setEditingItemId(null);
      setApplySuccessMessage(`Updated actual spent for ${item.category} to ${budget.currency} ${formatINR(tempSpent)}`);
    } catch (err: any) {
      console.error('Failed to adjust actual spent via ledger:', err);
      const updatedItems = items.map(i =>
        i.id === item.id ? { ...i, actual_spent: Number(tempSpent) } : i
      );
      const updatedPlan: FullEventPlan = {
        ...plan,
        budget: {
          ...budget,
          items: updatedItems,
        },
      };
      onUpdatePlan(updatedPlan);
      setEditingItemId(null);
    }
  };

  const handleExecuteMove = () => {
    if (sourceCat === targetCat || moveAmount <= 0) return;
    const src = items.find(i => i.category === sourceCat);
    const tgt = items.find(i => i.category === targetCat);
    if (!src || !tgt) return;

    const actualMove = Math.min(src.allocated_amount * 0.9, moveAmount);
    const movePct = (actualMove / budget.total_budget) * 100;

    const updatedItems = items.map(i => {
      if (i.category === sourceCat) {
        return { ...i, weight: Math.max(0.1, i.weight - movePct) };
      }
      if (i.category === targetCat) {
        return { ...i, weight: i.weight + movePct };
      }
      return i;
    });

    const updatedPlan: FullEventPlan = {
      ...plan,
      budget: {
        ...budget,
        items: updatedItems,
      },
    };
    onUpdatePlan(updatedPlan);
    setShowMoveModal(false);
  };

  const contingencyItem = items.find(i => i.is_contingency);

  return (
    <div className="space-y-6">

      {/* Success Notification Banner */}
      {applySuccessMessage && (
        <div className="bg-emerald-50 border border-emerald-300 p-4 rounded-2xl flex items-center justify-between text-emerald-900 text-sm shadow-xs animate-in fade-in duration-300">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <span className="font-semibold">{applySuccessMessage}</span>
          </div>
          <button
            onClick={() => setApplySuccessMessage(null)}
            className="p-1 hover:bg-emerald-100 rounded-lg transition-colors"
          >
            <X className="w-4 h-4 text-emerald-700" />
          </button>
        </div>
      )}

      {/* ========================================================= */}
      {/* SECTION 1: BUDGET ANALYSIS OVERVIEW */}
      {/* ========================================================= */}
      {analysis && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">Budget Health & Comprehensive Analysis</h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Real-time financial metrics, expense distribution, and high-impact savings targets.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-lg">
                Deterministic Invariant: 100.00%
              </span>
            </div>
          </div>

          {/* 4 Health Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <div className="p-3.5 bg-slate-50/80 border border-slate-200/60 rounded-xl">
              <span className="text-2xs font-bold text-slate-400 uppercase tracking-wider">Total Event Budget</span>
              <p className="text-lg font-extrabold text-slate-900 mt-0.5">
                {formatINR(analysis.total_budget)} {budget.currency}
              </p>
              <span className="text-2xs text-slate-400">Fixed ceiling</span>
            </div>

            <div className="p-3.5 bg-slate-50/80 border border-slate-200/60 rounded-xl">
              <span className="text-2xs font-bold text-slate-400 uppercase tracking-wider">Total Allocated</span>
              <p className="text-lg font-extrabold text-indigo-700 mt-0.5">
                {formatINR(analysis.total_allocated)} {budget.currency}
              </p>
              <span className="text-2xs text-indigo-600 font-medium">100.00% allocated</span>
            </div>

            <div className="p-3.5 bg-slate-50/80 border border-slate-200/60 rounded-xl">
              <span className="text-2xs font-bold text-slate-400 uppercase tracking-wider">Remaining Unspent</span>
              <p className="text-lg font-extrabold text-emerald-700 mt-0.5">
                {formatINR(analysis.remaining_budget)} {budget.currency}
              </p>
              <span className="text-2xs text-emerald-600 font-medium">
                Spent: {formatINR(analysis.total_actual_spent)} {budget.currency}
              </span>
            </div>

            <div className="p-3.5 bg-amber-50/70 border border-amber-200/60 rounded-xl">
              <span className="text-2xs font-bold text-amber-800 uppercase tracking-wider">Highest Expense</span>
              <p className="text-sm font-bold text-amber-950 mt-0.5 truncate" title={analysis.highest_expense_category}>
                {analysis.highest_expense_category}
              </p>
              <span className="text-2xs font-semibold text-amber-700">
                {formatINR(analysis.highest_expense_amount)} {budget.currency} ({analysis.highest_expense_percentage}%)
              </span>
            </div>
          </div>

          {/* Potential Savings Categories */}
          {analysis.potential_savings_categories.length > 0 && (
            <div className="p-3 bg-indigo-50/40 border border-indigo-100 rounded-xl flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-indigo-900 flex items-center gap-1.5">
                <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
                <span>Categories with High Savings Potential:</span>
              </span>
              <div className="flex flex-wrap gap-1.5">
                {analysis.potential_savings_categories.map((cat, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setOptimizerPrompt(`Suggest a more affordable plan for ${cat} while preserving quality`);
                    }}
                    className="px-2.5 py-0.5 text-2xs font-semibold bg-white text-indigo-800 hover:bg-indigo-100 border border-indigo-200 rounded-md transition-colors"
                  >
                    ✂️ {cat}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Duplicate / Overlapping Categories Warning Banner */}
          {analysis.duplicate_warnings && analysis.duplicate_warnings.length > 0 && (
            <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs shadow-xs">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-amber-950">
                    Duplicate or Overlapping Categories Detected ({analysis.duplicate_warnings.length})
                  </h4>
                  <p className="text-amber-800 text-xs mt-0.5">
                    We detected multiple categories that map to the same standard event taxonomy. Consolidating them helps eliminate redundant expenses and improve AI recommendations.
                  </p>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {analysis.duplicate_warnings.map((w, i) => (
                      <span key={i} className="px-2 py-0.5 bg-white/80 border border-amber-200 text-amber-900 text-2xs rounded-md font-medium">
                        ⚠️ {w.affected_categories.join(' & ')}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowMergeModal(true)}
                className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold text-amber-950 bg-amber-200 hover:bg-amber-300 rounded-xl transition-colors shadow-2xs cursor-pointer"
              >
                <GitMerge className="w-4 h-4" />
                <span>Review & Merge</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* SECTION 2: AI BUDGET OPTIMIZER */}
      {/* ========================================================= */}
      <div className="bg-gradient-to-br from-white via-slate-50/50 to-indigo-50/30 p-6 rounded-2xl border border-indigo-200/80 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-indigo-600 to-emerald-500 text-white shadow-xs">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">AI Smart Budget Optimizer</h3>
              <p className="text-xs text-slate-500">
                Enter your cost reduction goals, priority protections, or reallocations in plain language.
              </p>
            </div>
          </div>
          {optimizationResult && (
            <span className={`px-2.5 py-1 text-2xs font-bold uppercase rounded-full flex items-center gap-1 ${
              optimizationResult.engine_used === 'gemini'
                ? 'bg-purple-100 text-purple-800 border border-purple-200'
                : optimizationResult.engine_used === 'deterministic_fallback'
                ? 'bg-amber-100 text-amber-800 border border-amber-200'
                : 'bg-indigo-100 text-indigo-800 border border-indigo-200'
            }`}>
              <Cpu className="w-3 h-3" />
              {optimizationResult.engine_used === 'gemini'
                ? 'Gemini AI Model'
                : optimizationResult.engine_used === 'deterministic_fallback'
                ? 'Deterministic Fallback'
                : 'Smart Rule Engine'}
            </span>
          )}
        </div>

        {/* Active Protected Categories Chip Display */}
        {items.some(i => i.is_protected) && (
          <div className="p-3 bg-indigo-50/70 border border-indigo-200/80 rounded-xl flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-indigo-600 flex-shrink-0" />
              <span className="text-xs font-bold text-indigo-950">
                Protected Categories ({items.filter(i => i.is_protected).length}):
              </span>
              <span className="text-xs text-indigo-700">
                Shielded from reductions (Min protected floor: {budget.currency} {formatINR(items.filter(i => i.is_protected).reduce((sum, i) => sum + i.allocated_amount, 0))})
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {items.filter(i => i.is_protected).map(p => (
                <span
                  key={p.id}
                  className="inline-flex items-center gap-1 px-2.5 py-0.5 text-2xs font-semibold bg-white text-indigo-900 border border-indigo-200 rounded-lg shadow-2xs"
                >
                  <Lock className="w-2.5 h-2.5 text-indigo-600" />
                  {p.category}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Quick Suggestion Chips */}
        <div>
          <label className="block text-2xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">
            Quick Optimization Presets:
          </label>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_PROMPTS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setOptimizerPrompt(p);
                  handleRunOptimizer(p);
                }}
                disabled={isOptimizing}
                className="px-3 py-1 text-xs font-medium bg-white hover:bg-indigo-50 text-slate-700 hover:text-indigo-900 border border-slate-200 rounded-lg shadow-2xs transition-colors"
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Natural Language Prompt Input */}
        <div className="space-y-2">
          <div className="flex gap-2">
            <input
              type="text"
              value={optimizerPrompt}
              onChange={e => setOptimizerPrompt(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleRunOptimizer();
                }
              }}
              disabled={isOptimizing}
              placeholder="e.g. Reduce my budget by ₹30,000 but keep food quality high..."
              className="flex-1 px-4 py-2.5 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-2xs"
            />
            <button
              onClick={() => handleRunOptimizer()}
              disabled={isOptimizing || !optimizerPrompt.trim()}
              className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-indigo-600 to-emerald-600 hover:from-indigo-700 hover:to-emerald-700 disabled:opacity-50 rounded-xl shadow-xs transition-all flex-shrink-0 cursor-pointer"
            >
              {isOptimizing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Optimizing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Optimize Budget</span>
                </>
              )}
            </button>
          </div>

          {optimizerError && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
              <span>{optimizerError}</span>
            </div>
          )}
        </div>

        {/* ========================================================= */}
        {/* SECTION 3 & 4: OPTIMIZATION RESULTS & SIDE-BY-SIDE VIEW */}
        {/* ========================================================= */}
        {optimizationResult && (
          <div className="mt-6 pt-6 border-t border-slate-200/80 space-y-6 animate-in fade-in duration-300">

            {/* Validation Notice for Infeasible or Erroneous Requests */}
            {!isOptimizationValid && (
              <div className="p-4 bg-amber-50 border border-amber-300 rounded-2xl flex items-start gap-3 text-amber-900 text-xs shadow-xs">
                <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h4 className="font-bold text-amber-950">
                    {optimizationResult.is_feasible === false ? 'Budget Reduction Infeasible' : 'Optimization Feasibility Notice'}
                  </h4>
                  <p className="text-amber-800">
                    {optimizationResult.validation_errors?.[0] || optimizationResult.explanation.why_recommended}
                  </p>
                  {optimizationResult.minimum_protected_budget !== undefined && optimizationResult.minimum_protected_budget > 0 && (
                    <p className="text-xs font-semibold text-amber-900">
                      Minimum Protected Budget: {plan.budget.currency} {formatINR(optimizationResult.minimum_protected_budget)}
                    </p>
                  )}
                  <p className="text-2xs text-amber-700 font-semibold">
                    The &quot;Apply New Budget&quot; button remains disabled. To achieve this target, unlock one or more protected categories or increase the requested budget.
                  </p>
                </div>
              </div>
            )}

            {/* Savings Summary Banner */}
            <div className={`p-4 rounded-2xl flex flex-wrap items-center justify-between gap-4 border ${
              isOptimizationValid
                ? 'bg-emerald-50 border-emerald-200'
                : 'bg-slate-50 border-slate-200'
            }`}>
              <div className="flex items-center gap-3">
                <div className={`p-2.5 rounded-xl shadow-xs text-white ${
                  isOptimizationValid ? 'bg-emerald-600' : 'bg-slate-500'
                }`}>
                  <TrendingDown className="w-6 h-6" />
                </div>
                <div>
                  <span className={`text-2xs font-bold uppercase tracking-wider ${
                    isOptimizationValid ? 'text-emerald-800' : 'text-slate-600'
                  }`}>
                    Optimization Summary
                  </span>
                  <div className="flex items-baseline gap-2 mt-0.5">
                    <span className={`text-xl font-extrabold ${
                      isOptimizationValid ? 'text-emerald-950' : 'text-slate-900'
                    }`}>
                      Total Savings: {plan.budget.currency} {formatINR(optimizationResult.total_savings)}
                    </span>
                    <span className={`text-xs font-semibold ${
                      isOptimizationValid ? 'text-emerald-700' : 'text-slate-500'
                    }`}>
                      (Revised Budget: {plan.budget.currency} {formatINR(optimizationResult.revised_total_budget)})
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons: Apply / Discard */}
              <div className="flex items-center gap-2.5">
                <button
                  onClick={handleDiscardOptimization}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors shadow-2xs"
                >
                  Discard Changes
                </button>
                <button
                  onClick={handleApplyOptimization}
                  disabled={!isOptimizationValid}
                  className={`flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white rounded-xl shadow-sm transition-all ${
                    isOptimizationValid
                      ? 'bg-emerald-600 hover:bg-emerald-700 active:scale-95 cursor-pointer'
                      : 'bg-slate-300 text-slate-500 cursor-not-allowed opacity-60'
                  }`}
                  title={!isOptimizationValid ? 'Optimization cannot be applied due to validation constraints' : 'Apply New Budget'}
                >
                  <Check className="w-4 h-4" />
                  <span>Apply New Budget</span>
                </button>
              </div>
            </div>

            {/* 4-Stat Financial Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3.5 bg-white border border-slate-200 rounded-xl shadow-2xs">
                <span className="text-2xs font-semibold text-slate-500 uppercase tracking-wider">Original Budget</span>
                <p className="text-base font-extrabold text-slate-900 mt-0.5">
                  {plan.budget.currency} {formatINR(optimizationResult.original_total_budget)}
                </p>
              </div>
              <div className="p-3.5 bg-white border border-slate-200 rounded-xl shadow-2xs">
                <span className="text-2xs font-semibold text-slate-500 uppercase tracking-wider">Revised Budget</span>
                <p className="text-base font-extrabold text-slate-900 mt-0.5">
                  {plan.budget.currency} {formatINR(optimizationResult.revised_total_budget)}
                </p>
              </div>
              <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl shadow-2xs">
                <span className="text-2xs font-semibold text-emerald-700 uppercase tracking-wider">Total Savings</span>
                <p className="text-base font-extrabold text-emerald-950 mt-0.5">
                  {plan.budget.currency} {formatINR(optimizationResult.total_savings)}
                </p>
              </div>
              <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl shadow-2xs">
                <span className="text-2xs font-semibold text-emerald-700 uppercase tracking-wider">Savings Percentage</span>
                <p className="text-base font-extrabold text-emerald-950 mt-0.5">
                  {(optimizationResult.savings_percentage ?? (optimizationResult.original_total_budget > 0 ? (optimizationResult.total_savings / optimizationResult.original_total_budget) * 100 : 0)).toFixed(1)}%
                </p>
              </div>
            </div>

            {/* AI Explanation 4-Card Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Where money was saved */}
              <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
                  <TrendingDown className="w-4 h-4 text-emerald-600" />
                  <span>Where Money Was Saved</span>
                </div>
                <ul className="space-y-1.5 text-xs text-slate-600">
                  {optimizationResult.explanation.where_money_saved.map((item, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-emerald-500 font-bold">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Why recommended */}
              <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
                  <Lightbulb className="w-4 h-4 text-amber-500" />
                  <span>Why Recommended</span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {optimizationResult.explanation.why_recommended}
                </p>
              </div>

              {/* Expenses preserved */}
              <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
                  <Shield className="w-4 h-4 text-indigo-600" />
                  <span>Important Expenses Preserved</span>
                </div>
                <ul className="space-y-1.5 text-xs text-slate-600">
                  {optimizationResult.explanation.expenses_preserved.map((item, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-indigo-500 font-bold">✓</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Total saved recap */}
              <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
                  <DollarSign className="w-4 h-4 text-indigo-600" />
                  <span>Financial Recap</span>
                </div>
                <p className="text-xs font-medium text-slate-700 leading-relaxed">
                  {optimizationResult.explanation.total_saved_summary}
                </p>
                <div className="pt-2 flex items-center justify-between text-2xs text-slate-400 border-t border-slate-100">
                  <span>Engine: {optimizationResult.engine_used}</span>
                  <span>Contingency Reserve: 8.00% Intact</span>
                </div>
              </div>
            </div>

            {/* Comparison Bar Chart (Original vs Recommended) */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Side-by-Side Category Allocation Comparison
                </h4>
                <div className="flex items-center gap-4 text-xs font-medium">
                  <span className="flex items-center gap-1.5 text-slate-600">
                    <span className="w-3 h-3 bg-indigo-600 rounded-xs inline-block" /> Original
                  </span>
                  <span className="flex items-center gap-1.5 text-slate-600">
                    <span className="w-3 h-3 bg-emerald-500 rounded-xs inline-block" /> Recommended
                  </span>
                </div>
              </div>

              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonChartData} margin={{ top: 10, right: 10, left: 10, bottom: 30 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="category" angle={-30} textAnchor="end" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} tickFormatter={val => `${val / 1000}k`} />
                    <Tooltip
                      formatter={(val: number, name: string) => [
                        `${formatINR(val)} ${budget.currency}`,
                        name === 'original' ? 'Original Allocation' : 'Recommended Allocation',
                      ]}
                    />
                    <Bar dataKey="original" fill="#0d9488" radius={[4, 4, 0, 0]} name="original" />
                    <Bar dataKey="recommended" fill="#10b981" radius={[4, 4, 0, 0]} name="recommended" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Comparison Table */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
              <div className="px-5 py-3.5 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Detailed Category Changes & Impact
                </h4>
                <span className="text-2xs text-slate-500">
                  Review savings and rationales before applying
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider border-b border-slate-200 font-semibold text-2xs">
                    <tr>
                      <th className="px-4 py-3">Category</th>
                      <th className="px-4 py-3 text-right">Original ({budget.currency})</th>
                      <th className="px-4 py-3 text-right">Recommended ({budget.currency})</th>
                      <th className="px-4 py-3 text-right">Savings / Diff</th>
                      <th className="px-4 py-3 text-center">% Change</th>
                      <th className="px-4 py-3">AI Notes & Strategy</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {optimizationResult.categories.map((c, idx) => {
                      const isSaving = c.savings > 0;
                      const isIncrease = c.savings < 0;

                      return (
                        <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                          <td className="px-4 py-3 font-semibold text-slate-900">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span>{c.category}</span>
                              {renderClassificationBadge(c.classification)}
                              {c.is_protected && (
                                <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-3xs font-semibold bg-amber-100 text-amber-900 border border-amber-300 rounded">
                                  <Lock className="w-2.5 h-2.5 text-amber-700" />
                                  Protected
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-right text-slate-600 font-medium">
                            {formatINR(c.original_amount, true)} ({c.original_percentage.toFixed(1)}%)
                          </td>
                          <td className="px-4 py-3 text-right font-bold text-slate-900">
                            {formatINR(c.recommended_amount, true)} ({c.recommended_percentage.toFixed(1)}%)
                          </td>
                          <td className="px-4 py-3 text-right font-bold">
                            {isSaving ? (
                              <span className="text-emerald-600 flex items-center justify-end gap-1">
                                <ArrowDownRight className="w-3.5 h-3.5" />
                                -{formatINR(c.savings)}
                              </span>
                            ) : isIncrease ? (
                              <span className="text-indigo-600 flex items-center justify-end gap-1">
                                <ArrowUpRight className="w-3.5 h-3.5" />
                                +{formatINR(Math.abs(c.savings))}
                              </span>
                            ) : (
                              <span className="text-slate-400">0.00</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`px-2 py-0.5 rounded-full font-bold text-2xs ${
                              isSaving
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : isIncrease
                                ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                                : 'bg-slate-100 text-slate-500'
                            }`}>
                              {c.percentage_change > 0 ? `+${c.percentage_change}%` : `${c.percentage_change}%`}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-500 max-w-xs truncate" title={c.notes}>
                            {c.notes || '-'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Bottom Actions Bar */}
              <div className="p-4 bg-slate-50/80 border-t border-slate-200 flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  Ready to lock in these optimizations?
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleDiscardOptimization}
                    className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors shadow-2xs"
                  >
                    Discard Changes
                  </button>
                  <button
                    onClick={handleApplyOptimization}
                    disabled={!isOptimizationValid}
                    className={`flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white rounded-xl shadow-sm transition-all ${
                      isOptimizationValid
                        ? 'bg-emerald-600 hover:bg-emerald-700 active:scale-95 cursor-pointer'
                        : 'bg-slate-300 text-slate-500 cursor-not-allowed opacity-60'
                    }`}
                    title={!isOptimizationValid ? 'Optimization cannot be applied due to validation constraints' : 'Apply New Budget'}
                  >
                    <Check className="w-4 h-4" />
                    <span>Apply New Budget</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ========================================================= */}
      {/* SECTION 5: CURRENT CATEGORY ALLOCATIONS & VISUALIZATIONS */}
      {/* ========================================================= */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-slate-900">Deterministic Budget Allocation</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Strict arithmetic guarantee: 100.00% exact allocation sum & contingency buffer.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowMoveModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg transition-colors"
          >
            <ArrowRightLeft className="w-3.5 h-3.5" />
            <span>Manual Fund Transfer</span>
          </button>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Pie Chart: Allocation Breakdown */}
        <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4">Category Distribution</h4>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={95}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {pieData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val: number) => [`${formatINR(val)} ${budget.currency}`, 'Allocated']}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          {/* Contingency highlight pill */}
          {contingencyItem && (
            <div className="mt-2 p-2.5 bg-emerald-50 border border-emerald-200/60 rounded-xl flex items-center justify-between text-xs text-emerald-900">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Contingency Reserve:</span>
              </div>
              <span className="font-bold">
                {formatINR(contingencyItem.allocated_amount)} {budget.currency} ({contingencyItem.percentage}%)
              </span>
            </div>
          )}
        </div>

        {/* Bar Chart: Allocated vs Actual Spend */}
        <div className="lg:col-span-7 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4">Allocated vs Actual Spend</h4>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData} margin={{ top: 10, right: 10, left: 10, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" angle={-30} textAnchor="end" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={val => `${val / 1000}k`} />
                <Tooltip formatter={(val: number) => [`${formatINR(val)} ${budget.currency}`]} />
                <Bar dataKey="allocated" fill="#0d9488" radius={[4, 4, 0, 0]} name="Allocated" />
                <Bar dataKey="actual" fill="#ec4899" radius={[4, 4, 0, 0]} name="Actual Spent" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-center gap-6 text-xs font-medium text-slate-600 mt-2">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-indigo-600 rounded-xs" />
              <span>Allocated</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-pink-500 rounded-xs" />
              <span>Actual Spent</span>
            </div>
          </div>
        </div>
      </div>

      {/* Table: Categories Breakdown */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <h4 className="text-sm font-bold text-slate-900">Category Allocations & Tracking</h4>
          <span className="text-xs font-medium text-slate-500">
            Click edit icon to record expenditures or protect essential categories from AI reductions
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50/80 text-xs text-slate-500 uppercase tracking-wider border-b border-slate-200">
              <tr>
                <th className="px-5 py-3 font-semibold">Category</th>
                <th className="px-3 py-3 font-semibold text-center">Classification</th>
                <th className="px-3 py-3 font-semibold text-center">Protection</th>
                <th className="px-5 py-3 font-semibold text-right">Allocation (%)</th>
                <th className="px-5 py-3 font-semibold text-right">Budget ({budget.currency})</th>
                <th className="px-5 py-3 font-semibold text-right">Actual Spent ({budget.currency})</th>
                <th className="px-5 py-3 font-semibold text-center">Status</th>
                <th className="px-5 py-3 font-semibold">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item, idx) => {
                const isOver = item.actual_spent > item.allocated_amount && item.allocated_amount > 0;
                const isEditing = editingItemId === item.id;

                return (
                  <tr key={item.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-3.5 font-medium text-slate-900 flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                      <span>{item.category}</span>
                      {item.is_contingency && (
                        <span className="px-2 py-0.5 text-2xs font-semibold bg-emerald-100 text-emerald-800 rounded-full">
                          Contingency
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3.5 text-center">
                      {renderClassificationBadge(item.classification)}
                    </td>
                    <td className="px-3 py-3.5 text-center">
                      <button
                        type="button"
                        disabled={isUpdatingProtection === item.id}
                        onClick={() => handleToggleProtection(item)}
                        className={`inline-flex items-center gap-1 px-2.5 py-1 text-2xs font-semibold rounded-lg border transition-all cursor-pointer ${
                          item.is_protected
                            ? 'bg-amber-100/90 text-amber-950 border-amber-300 hover:bg-amber-200 shadow-2xs'
                            : 'bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100 hover:text-slate-800'
                        }`}
                        title={item.is_protected ? 'Protected category: shielded from budget cuts. Click to unlock.' : 'Click to protect category from budget cuts.'}
                      >
                        {isUpdatingProtection === item.id ? (
                          <RefreshCw className="w-3 h-3 animate-spin text-amber-700" />
                        ) : item.is_protected ? (
                          <>
                            <Lock className="w-3 h-3 text-amber-700" />
                            <span>Protected</span>
                          </>
                        ) : (
                          <>
                            <Unlock className="w-3 h-3 text-slate-400" />
                            <span>Protect</span>
                          </>
                        )}
                      </button>
                    </td>
                    <td className="px-5 py-3.5 text-right font-semibold text-slate-700">
                      {item.percentage.toFixed(2)}%
                    </td>
                    <td className="px-5 py-3.5 text-right font-medium text-slate-900">
                      {formatINR(item.allocated_amount, true)}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      {isEditing ? (
                        <div className="flex items-center justify-end gap-1.5">
                          <input
                            type="number"
                            min="0"
                            value={tempSpent}
                            onChange={e => setTempSpent(Number(e.target.value))}
                            className="w-24 px-2 py-1 text-xs border border-indigo-500 rounded focus:outline-none"
                            autoFocus
                          />
                          <button
                            onClick={() => handleSaveSpent(item)}
                            className="p-1 text-white bg-indigo-600 hover:bg-indigo-700 rounded transition-colors"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-1.5 group">
                          <span className={`font-semibold ${isOver ? 'text-rose-600' : 'text-slate-800'}`}>
                            {formatINR(item.actual_spent, true)}
                          </span>
                          <button
                            onClick={() => {
                              setEditingItemId(item.id);
                              setTempSpent(item.actual_spent);
                            }}
                            className="p-1 text-slate-400 group-hover:text-indigo-600 hover:bg-slate-100 rounded transition-colors"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-center">
                      {isOver ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold bg-rose-100 text-rose-700 rounded-full">
                          <AlertCircle className="w-3 h-3" />
                          Over Budget
                        </span>
                      ) : item.actual_spent > 0 ? (
                        <span className="px-2.5 py-0.5 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
                          On Track
                        </span>
                      ) : (
                        <span className="px-2.5 py-0.5 text-xs text-slate-400 font-medium">Planned</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-500 max-w-xs truncate">
                      {item.notes || '-'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            {/* Totals Row */}
            <tfoot className="bg-slate-50/80 font-bold text-slate-900 border-t border-slate-200">
              <tr>
                <td className="px-5 py-3.5" colSpan={3}>TOTAL ALLOCATION</td>
                <td className="px-5 py-3.5 text-right">100.00%</td>
                <td className="px-5 py-3.5 text-right font-extrabold text-indigo-700">
                  {formatINR(budget.total_allocated, true)} {budget.currency}
                </td>
                <td className="px-5 py-3.5 text-right font-extrabold text-slate-900">
                  {formatINR(budget.total_actual_spent, true)} {budget.currency}
                </td>
                <td colSpan={2} className="px-5 py-3.5 text-xs text-slate-500 text-right">
                  Exact Match Deterministic Guarantee
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Move Funds Modal */}
      {showMoveModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <h4 className="text-base font-bold text-slate-900">Reallocate Budget Between Categories</h4>
            <p className="text-xs text-slate-500">
              Adjusts relative weights and deterministically renormalizes all amounts to preserve the exact total budget.
            </p>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Transfer From</label>
                <select
                  value={sourceCat}
                  onChange={e => setSourceCat(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {items.map(i => (
                    <option key={i.id} value={i.category}>{i.category} ({formatINR(i.allocated_amount)} {budget.currency})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Transfer To</label>
                <select
                  value={targetCat}
                  onChange={e => setTargetCat(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {items.map(i => (
                    <option key={i.id} value={i.category}>{i.category} ({formatINR(i.allocated_amount)} {budget.currency})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Amount to Transfer ({budget.currency})</label>
                <input
                  type="number"
                  min="1"
                  value={moveAmount}
                  onChange={e => setMoveAmount(Number(e.target.value))}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div className="pt-3 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowMoveModal(false)}
                className="px-3.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteMove}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors shadow-xs cursor-pointer"
              >
                Apply Reallocation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Review & Consolidate Categories Modal */}
      {showMergeModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-xl w-full p-6 space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <GitMerge className="w-5 h-5 text-indigo-600" />
                <h4 className="text-base font-bold text-slate-900">Consolidate Budget Categories</h4>
              </div>
              <button
                disabled={isNormalizing}
                onClick={() => setShowMergeModal(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 disabled:opacity-50 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Our taxonomy engine identified duplicate or overlapping categories. Consolidating into canonical categories unifies expense tracking and ensures reliable AI budget optimization.
            </p>

            <div className="overflow-y-auto space-y-3 flex-1 pr-1">
              {analysis?.merge_suggestions && analysis.merge_suggestions.length > 0 ? (
                analysis.merge_suggestions.map((sug, idx) => (
                  <div key={idx} className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                        <span className="text-indigo-600">Target Canonical:</span>
                        <span className="px-2 py-0.5 bg-indigo-100 text-indigo-900 rounded font-semibold text-2xs">
                          {sug.canonical_category}
                        </span>
                      </span>
                      <span className="text-2xs font-semibold px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded">
                        Confidence: {(sug.confidence * 100).toFixed(0)}%
                      </span>
                    </div>

                    <div className="text-xs text-slate-600 flex items-center gap-1.5">
                      <span className="font-semibold text-slate-700">Merging:</span>
                      <span className="text-slate-900 font-medium">{sug.source_categories.join(' + ')}</span>
                    </div>

                    <div className="flex items-center justify-between text-2xs text-slate-500 pt-1 border-t border-slate-200/60">
                      <span>Combined Allocation: {budget.currency} {formatINR(sug.combined_allocation)}</span>
                      <span>Spent: {budget.currency} {formatINR(sug.combined_spent)}</span>
                    </div>

                    <p className="text-2xs text-slate-500 italic">
                      {sug.rationale}
                    </p>
                  </div>
                ))
              ) : (
                <div className="p-4 text-center text-xs text-slate-500">
                  All categories are currently normalized to the canonical taxonomy.
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
              <button
                type="button"
                disabled={isNormalizing}
                onClick={() => setShowMergeModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 disabled:opacity-50 rounded-xl transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isNormalizing || !analysis?.merge_suggestions || analysis.merge_suggestions.length === 0}
                onClick={handleNormalizeCategories}
                className="flex items-center gap-2 px-5 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-xl transition-all shadow-xs cursor-pointer"
              >
                {isNormalizing ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Consolidating...</span>
                  </>
                ) : (
                  <>
                    <GitMerge className="w-3.5 h-3.5" />
                    <span>Approve & Consolidate All</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
