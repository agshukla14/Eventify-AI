import React from 'react';
import { Clock, Wallet, CheckSquare, Users, AlertTriangle, ShieldCheck } from 'lucide-react';
import { FullEventPlan } from '../types';

interface DashboardStatsProps {
  plan: FullEventPlan;
}

export const DashboardStats: React.FC<DashboardStatsProps> = ({ plan }) => {
  const today = new Date();
  const eventDate = new Date(plan.intake.date);
  const diffTime = eventDate.getTime() - today.getTime();
  const daysLeft = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  const totalBudget = plan.budget.total_budget;
  const totalSpent = plan.budget.total_actual_spent;
  const budgetUsedPct = totalBudget > 0 ? Math.min(100, Math.round((totalSpent / totalBudget) * 100)) : 0;

  const tasks = plan.timeline.milestones;
  const tasksDone = tasks.filter(t => t.status === 'completed').length;
  const tasksPct = tasks.length > 0 ? Math.round((tasksDone / tasks.length) * 100) : 0;

  const vendors = plan.vendors;
  const vendorsBooked = vendors.filter(v => v.status === 'booked' || v.status === 'paid').length;

  const highRiskCount = plan.timeline.high_risk_count;

  return (
    <div className="space-y-4">
      {/* Over-budget or High-risk Alerts */}
      {plan.budget.is_over_budget && (
        <div className="bg-rose-50 border-l-4 border-rose-500 p-3.5 rounded-r-2xl flex items-center gap-3 text-rose-800 text-xs sm:text-sm animate-pulse shadow-2xs">
          <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0" />
          <div>
            <span className="font-bold">Budget Warning:</span> Total spend exceeds budget by{' '}
            {plan.budget.over_budget_amount.toLocaleString('en-IN')} {plan.budget.currency}! Check the Budget tab to adjust allocations.
          </div>
        </div>
      )}

      {highRiskCount > 0 && (
        <div className="bg-amber-50 border-l-4 border-amber-500 p-3.5 rounded-r-2xl flex items-center gap-3 text-amber-900 text-xs sm:text-sm shadow-2xs">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <div>
            <span className="font-bold">{highRiskCount} High-Risk Milestone(s) Flagged:</span> Short lead-time requires expedited vendor contracts and booking.
          </div>
        </div>
      )}

      {/* 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Days Left */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/80 shadow-xs flex items-center gap-4 hover:border-indigo-300 transition-colors">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 flex-shrink-0">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Days Remaining</p>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-2xl font-extrabold text-slate-900">{daysLeft > 0 ? daysLeft : 0}</span>
              <span className="text-xs text-slate-400 font-medium">days left</span>
            </div>
            <p className="text-xs text-indigo-600 font-medium mt-0.5 truncate">{plan.intake.date}</p>
          </div>
        </div>

        {/* Budget Spent */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/80 shadow-xs flex items-center gap-4 hover:border-indigo-300 transition-colors">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 flex-shrink-0">
            <Wallet className="w-6 h-6" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Budget Utilized</p>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-2xl font-extrabold text-slate-900">{budgetUsedPct}%</span>
              <span className="text-xs text-slate-400 truncate">
                of {totalBudget.toLocaleString('en-IN')} {plan.budget.currency}
              </span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${plan.budget.is_over_budget ? 'bg-rose-500' : 'bg-emerald-500'}`}
                style={{ width: `${Math.min(100, budgetUsedPct)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Tasks Progress */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/80 shadow-xs flex items-center gap-4 hover:border-indigo-300 transition-colors">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 flex-shrink-0">
            <CheckSquare className="w-6 h-6" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Tasks Completed</p>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-2xl font-extrabold text-slate-900">{tasksDone}</span>
              <span className="text-xs text-slate-400 font-medium">/ {tasks.length} ({tasksPct}%)</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2 overflow-hidden">
              <div
                className="bg-indigo-600 h-full rounded-full transition-all duration-300"
                style={{ width: `${tasksPct}%` }}
              />
            </div>
          </div>
        </div>

        {/* Vendors Booked */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/80 shadow-xs flex items-center gap-4 hover:border-indigo-300 transition-colors">
          <div className="w-12 h-12 rounded-xl bg-violet-50 border border-violet-100 flex items-center justify-center text-violet-600 flex-shrink-0">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Vendors Booked</p>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-2xl font-extrabold text-slate-900">{vendorsBooked}</span>
              <span className="text-xs text-slate-400 font-medium">/ {vendors.length} booked</span>
            </div>
            <p className="text-xs text-violet-600 font-medium mt-0.5">
              {vendors.length - vendorsBooked} pending quotes
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
