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
} from 'lucide-react';
import {
  FullEventPlan,
  BudgetItem,
  BudgetAnalysis,
  BudgetOptimizationResponse,
} from '../types';
import { getBudgetAnalysis, optimizeBudget } from '../api';

interface BudgetTabProps {
  plan: FullEventPlan;
  onUpdatePlan: (updatedPlan: FullEventPlan) => void;
}

const COLORS = [
  '#0d9488', '#0284c7', '#8b5cf6', '#ec4899', '#f59e0b',
  '#10b981', '#6366f1', '#14b8a6', '#f97316', '#64748b'
];

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

  const handleRunOptimizer = async (promptToUse?: string) => {
    const prompt = (promptToUse || optimizerPrompt).trim();
    if (!prompt) return;

    setIsOptimizing(true);
    setOptimizerError(null);
    setApplySuccessMessage(null);

    try {
      const res = await optimizeBudget(plan.event_id, prompt);
      setOptimizationResult(res);
    } catch (err: any) {
      setOptimizerError(err.message || 'Failed to optimize budget. Please try again.');
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleApplyOptimization = () => {
    if (!optimizationResult) return;

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
      `🎉 Successfully applied optimized budget! Total savings: ${plan.budget.currency} ${optimizationResult.total_savings.toLocaleString()}.`
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

  const handleSaveSpent = (item: BudgetItem) => {
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
                <Layers className="w-5 h-5 text-teal-600" />
                <h3 className="text-base font-bold text-slate-900">Budget Health & Comprehensive Analysis</h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Real-time financial metrics, expense distribution, and high-impact savings targets.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 text-xs font-semibold bg-teal-50 text-teal-700 border border-teal-200 rounded-lg">
                Deterministic Invariant: 100.00%
              </span>
            </div>
          </div>

          {/* 4 Health Metric Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-3.5 bg-slate-50/80 border border-slate-200/60 rounded-xl">
              <span className="text-2xs font-bold text-slate-400 uppercase tracking-wider">Total Event Budget</span>
              <p className="text-lg font-extrabold text-slate-900 mt-0.5">
                {analysis.total_budget.toLocaleString()} {budget.currency}
              </p>
              <span className="text-2xs text-slate-400">Fixed ceiling</span>
            </div>

            <div className="p-3.5 bg-slate-50/80 border border-slate-200/60 rounded-xl">
              <span className="text-2xs font-bold text-slate-400 uppercase tracking-wider">Total Allocated</span>
              <p className="text-lg font-extrabold text-teal-700 mt-0.5">
                {analysis.total_allocated.toLocaleString()} {budget.currency}
              </p>
              <span className="text-2xs text-teal-600 font-medium">100.00% allocated</span>
            </div>

            <div className="p-3.5 bg-slate-50/80 border border-slate-200/60 rounded-xl">
              <span className="text-2xs font-bold text-slate-400 uppercase tracking-wider">Remaining Unspent</span>
              <p className="text-lg font-extrabold text-emerald-700 mt-0.5">
                {analysis.remaining_budget.toLocaleString()} {budget.currency}
              </p>
              <span className="text-2xs text-emerald-600 font-medium">
                Spent: {analysis.total_actual_spent.toLocaleString()} {budget.currency}
              </span>
            </div>

            <div className="p-3.5 bg-amber-50/70 border border-amber-200/60 rounded-xl">
              <span className="text-2xs font-bold text-amber-800 uppercase tracking-wider">Highest Expense</span>
              <p className="text-sm font-bold text-amber-950 mt-0.5 truncate" title={analysis.highest_expense_category}>
                {analysis.highest_expense_category}
              </p>
              <span className="text-2xs font-semibold text-amber-700">
                {analysis.highest_expense_amount.toLocaleString()} {budget.currency} ({analysis.highest_expense_percentage}%)
              </span>
            </div>
          </div>

          {/* Potential Savings Categories */}
          {analysis.potential_savings_categories.length > 0 && (
            <div className="p-3 bg-teal-50/40 border border-teal-100 rounded-xl flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-teal-900 flex items-center gap-1.5">
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
                    className="px-2.5 py-0.5 text-2xs font-semibold bg-white text-teal-800 hover:bg-teal-100 border border-teal-200 rounded-md transition-colors"
                  >
                    ✂️ {cat}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* SECTION 2: AI BUDGET OPTIMIZER */}
      {/* ========================================================= */}
      <div className="bg-gradient-to-br from-white via-slate-50/50 to-teal-50/30 p-6 rounded-2xl border border-teal-200/80 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-teal-600 to-emerald-500 text-white shadow-xs">
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
                : 'bg-teal-100 text-teal-800 border border-teal-200'
            }`}>
              <Cpu className="w-3 h-3" />
              {optimizationResult.engine_used === 'gemini' ? 'Gemini AI Model' : 'Smart Rule Engine'}
            </span>
          )}
        </div>

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
                className="px-3 py-1 text-xs font-medium bg-white hover:bg-teal-50 text-slate-700 hover:text-teal-900 border border-slate-200 rounded-lg shadow-2xs transition-colors"
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
              className="flex-1 px-4 py-2.5 text-sm bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 shadow-2xs"
            />
            <button
              onClick={() => handleRunOptimizer()}
              disabled={isOptimizing || !optimizerPrompt.trim()}
              className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 disabled:opacity-50 rounded-xl shadow-xs transition-all flex-shrink-0"
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

            {/* Savings Summary Banner */}
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-emerald-600 text-white rounded-xl shadow-xs">
                  <TrendingDown className="w-6 h-6" />
                </div>
                <div>
                  <span className="text-2xs font-bold text-emerald-800 uppercase tracking-wider">Optimization Summary</span>
                  <div className="flex items-baseline gap-2 mt-0.5">
                    <span className="text-xl font-extrabold text-emerald-950">
                      Total Savings: {plan.budget.currency} {optimizationResult.total_savings.toLocaleString()}
                    </span>
                    <span className="text-xs text-emerald-700 font-semibold">
                      (Revised Budget: {plan.budget.currency} {optimizationResult.revised_total_budget.toLocaleString()})
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
                  className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 active:scale-95 rounded-xl shadow-sm transition-all"
                >
                  <Check className="w-4 h-4" />
                  <span>Apply New Budget</span>
                </button>
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
                  <Shield className="w-4 h-4 text-teal-600" />
                  <span>Important Expenses Preserved</span>
                </div>
                <ul className="space-y-1.5 text-xs text-slate-600">
                  {optimizationResult.explanation.expenses_preserved.map((item, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-teal-500 font-bold">✓</span>
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
                    <span className="w-3 h-3 bg-teal-600 rounded-xs inline-block" /> Original
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
                        `${val.toLocaleString()} ${budget.currency}`,
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
                            {c.category}
                          </td>
                          <td className="px-4 py-3 text-right text-slate-600 font-medium">
                            {c.original_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })} ({c.original_percentage.toFixed(1)}%)
                          </td>
                          <td className="px-4 py-3 text-right font-bold text-slate-900">
                            {c.recommended_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })} ({c.recommended_percentage.toFixed(1)}%)
                          </td>
                          <td className="px-4 py-3 text-right font-bold">
                            {isSaving ? (
                              <span className="text-emerald-600 flex items-center justify-end gap-1">
                                <ArrowDownRight className="w-3.5 h-3.5" />
                                -{c.savings.toLocaleString()}
                              </span>
                            ) : isIncrease ? (
                              <span className="text-indigo-600 flex items-center justify-end gap-1">
                                <ArrowUpRight className="w-3.5 h-3.5" />
                                +{Math.abs(c.savings).toLocaleString()}
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
                    className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 active:scale-95 rounded-xl shadow-sm transition-all"
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
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-teal-700 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded-lg transition-colors"
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
                  formatter={(val: number) => [`${val.toLocaleString()} ${budget.currency}`, 'Allocated']}
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
                {contingencyItem.allocated_amount.toLocaleString()} {budget.currency} ({contingencyItem.percentage}%)
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
                <Tooltip formatter={(val: number) => [`${val.toLocaleString()} ${budget.currency}`]} />
                <Bar dataKey="allocated" fill="#0d9488" radius={[4, 4, 0, 0]} name="Allocated" />
                <Bar dataKey="actual" fill="#ec4899" radius={[4, 4, 0, 0]} name="Actual Spent" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-center gap-6 text-xs font-medium text-slate-600 mt-2">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-teal-600 rounded-xs" />
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
            Click edit icon to record actual expenditures
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50/80 text-xs text-slate-500 uppercase tracking-wider border-b border-slate-200">
              <tr>
                <th className="px-5 py-3 font-semibold">Category</th>
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
                    <td className="px-5 py-3.5 text-right font-semibold text-slate-700">
                      {item.percentage.toFixed(2)}%
                    </td>
                    <td className="px-5 py-3.5 text-right font-medium text-slate-900">
                      {item.allocated_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      {isEditing ? (
                        <div className="flex items-center justify-end gap-1.5">
                          <input
                            type="number"
                            min="0"
                            value={tempSpent}
                            onChange={e => setTempSpent(Number(e.target.value))}
                            className="w-24 px-2 py-1 text-xs border border-teal-500 rounded focus:outline-none"
                            autoFocus
                          />
                          <button
                            onClick={() => handleSaveSpent(item)}
                            className="p-1 text-white bg-teal-600 hover:bg-teal-700 rounded transition-colors"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-1.5 group">
                          <span className={`font-semibold ${isOver ? 'text-rose-600' : 'text-slate-800'}`}>
                            {item.actual_spent.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </span>
                          <button
                            onClick={() => {
                              setEditingItemId(item.id);
                              setTempSpent(item.actual_spent);
                            }}
                            className="p-1 text-slate-400 group-hover:text-teal-600 hover:bg-slate-100 rounded transition-colors"
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
                <td className="px-5 py-3.5">TOTAL ALLOCATION</td>
                <td className="px-5 py-3.5 text-right">100.00%</td>
                <td className="px-5 py-3.5 text-right font-extrabold text-teal-700">
                  {budget.total_allocated.toLocaleString(undefined, { minimumFractionDigits: 2 })} {budget.currency}
                </td>
                <td className="px-5 py-3.5 text-right font-extrabold text-slate-900">
                  {budget.total_actual_spent.toLocaleString(undefined, { minimumFractionDigits: 2 })} {budget.currency}
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
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  {items.map(i => (
                    <option key={i.id} value={i.category}>{i.category} ({i.allocated_amount.toLocaleString()} {budget.currency})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Transfer To</label>
                <select
                  value={targetCat}
                  onChange={e => setTargetCat(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  {items.map(i => (
                    <option key={i.id} value={i.category}>{i.category} ({i.allocated_amount.toLocaleString()} {budget.currency})</option>
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
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>
            </div>

            <div className="pt-3 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowMoveModal(false)}
                className="px-3.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteMove}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-teal-600 hover:bg-teal-700 rounded-lg transition-colors shadow-xs"
              >
                Apply Reallocation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
