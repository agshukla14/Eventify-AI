import React, { useState } from 'react';
import { Users, CheckCircle2, Shield, Phone, DollarSign, ChevronRight, Check } from 'lucide-react';
import { FullEventPlan, VendorCategory, VendorChecklistItem } from '../types';

interface VendorsTabProps {
  plan: FullEventPlan;
  onUpdatePlan: (updatedPlan: FullEventPlan) => void;
}

export const VendorsTab: React.FC<VendorsTabProps> = ({ plan, onUpdatePlan }) => {
  const [selectedVendorId, setSelectedVendorId] = useState<string>(plan.vendors[0]?.id || '');

  const vendors = plan.vendors;
  const currentVendor = vendors.find(v => v.id === selectedVendorId) || vendors[0];

  const handleUpdateStatus = (vendorId: string, status: any) => {
    const updated = vendors.map(v => (v.id === vendorId ? { ...v, status } : v));
    onUpdatePlan({ ...plan, vendors: updated });
  };

  const handleUpdateQuote = (vendorId: string, quote_amount: number) => {
    const updated = vendors.map(v => (v.id === vendorId ? { ...v, quote_amount } : v));
    onUpdatePlan({ ...plan, vendors: updated });
  };

  const handleToggleChecklistItem = (vendorId: string, itemId: string) => {
    const updated = vendors.map(v => {
      if (v.id !== vendorId) return v;
      const updatedChecklist = v.checklist.map(c =>
        c.id === itemId ? { ...c, is_completed: !c.is_completed } : c
      );
      return { ...v, checklist: updatedChecklist };
    });
    onUpdatePlan({ ...plan, vendors: updated });
  };

  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-slate-900">Vendor Checklist & Contract Management</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            100% mandatory coverage guaranteed. Track questions, deposits, contracts, and backup vendors.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 text-xs font-semibold bg-teal-50 text-teal-700 border border-teal-200 rounded-lg">
            {vendors.filter(v => v.status === 'booked' || v.status === 'paid').length} of {vendors.length} Booked
          </span>
        </div>
      </div>

      {/* Main Grid: Left Category Selector, Right Detail View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Left: Vendor Category Cards List */}
        <div className="lg:col-span-5 space-y-2.5">
          {vendors.map(v => {
            const isSelected = v.id === currentVendor?.id;
            const completedCount = v.checklist.filter(c => c.is_completed).length;
            const statusBadge =
              v.status === 'paid'
                ? 'bg-emerald-100 text-emerald-800'
                : v.status === 'booked'
                ? 'bg-teal-100 text-teal-800'
                : v.status === 'quoted'
                ? 'bg-amber-100 text-amber-800'
                : 'bg-slate-100 text-slate-600';

            return (
              <div
                key={v.id}
                onClick={() => setSelectedVendorId(v.id)}
                className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-white border-teal-500 shadow-sm ring-2 ring-teal-500/20'
                    : 'bg-white border-slate-200/80 hover:border-slate-300 hover:bg-slate-50/50'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-slate-900">{v.category}</span>
                    {v.is_mandatory && (
                      <span className="px-2 py-0.5 text-2xs font-semibold bg-rose-50 text-rose-700 border border-rose-200 rounded-full">
                        Mandatory
                      </span>
                    )}
                  </div>
                  <span className={`px-2 py-0.5 text-2xs font-bold uppercase rounded-full ${statusBadge}`}>
                    {v.status.replace('_', ' ')}
                  </span>
                </div>

                <div className="flex items-center justify-between mt-2.5 text-xs text-slate-500">
                  <span className="truncate max-w-[180px]">{v.vendor_name || 'Pending Provider'}</span>
                  <span className="font-semibold text-slate-800">
                    {v.quote_amount.toLocaleString()} {plan.budget.currency}
                  </span>
                </div>

                <div className="mt-2.5 flex items-center justify-between text-2xs text-slate-400">
                  <span>{completedCount} / {v.checklist.length} checklist tasks verified</span>
                  <ChevronRight className={`w-3.5 h-3.5 text-slate-400 ${isSelected ? 'text-teal-600' : ''}`} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: Vendor Details & Checklist */}
        {currentVendor && (
          <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-6">

            {/* Vendor Header & Meta */}
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-5">
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-lg font-bold text-slate-900">{currentVendor.category}</h4>
                  {currentVendor.is_mandatory && (
                    <span className="px-2 py-0.5 text-2xs font-bold bg-rose-100 text-rose-800 rounded-full">
                      Mandatory Coverage
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Assigned Vendor: <span className="font-semibold text-slate-800">{currentVendor.vendor_name}</span>
                </p>
                <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                  <Phone className="w-3.5 h-3.5 text-slate-400" />
                  <span>{currentVendor.contact_info || 'contact@celebrationvendor.com'}</span>
                </div>
              </div>

              {/* Status Selector */}
              <div className="space-y-1">
                <label className="block text-2xs font-bold text-slate-400 uppercase tracking-wider">Booking Status</label>
                <select
                  value={currentVendor.status}
                  onChange={e => handleUpdateStatus(currentVendor.id, e.target.value)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  <option value="not_contacted">Not Contacted</option>
                  <option value="quoted">Quoted</option>
                  <option value="booked">Booked</option>
                  <option value="paid">Paid in Full</option>
                </select>
              </div>
            </div>

            {/* Financial & Linked Budget Category */}
            <div className="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-100">
              <div>
                <span className="text-2xs font-semibold text-slate-400 uppercase">Quote Amount</span>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <input
                    type="number"
                    min="0"
                    value={currentVendor.quote_amount}
                    onChange={e => handleUpdateQuote(currentVendor.id, Number(e.target.value))}
                    className="w-32 px-2 py-1 text-xs font-bold text-slate-900 bg-white border border-slate-200 rounded focus:outline-none"
                  />
                  <span className="text-xs font-medium text-slate-500">{plan.budget.currency}</span>
                </div>
              </div>

              <div>
                <span className="text-2xs font-semibold text-slate-400 uppercase">Linked Budget Category</span>
                <p className="text-xs font-bold text-teal-800 mt-1.5">{currentVendor.linked_budget_category}</p>
              </div>
            </div>

            {/* 4+ Item Checklist */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Mandatory Verification Checklist ({currentVendor.checklist.length} items)
                </h5>
                <span className="text-2xs text-slate-400">Contracts, Deposits & Questions</span>
              </div>

              <div className="space-y-2.5">
                {currentVendor.checklist.map(item => (
                  <div
                    key={item.id}
                    onClick={() => handleToggleChecklistItem(currentVendor.id, item.id)}
                    className={`p-3 rounded-xl border flex items-start gap-3 cursor-pointer transition-colors ${
                      item.is_completed
                        ? 'bg-teal-50/40 border-teal-200'
                        : 'bg-white border-slate-200/80 hover:bg-slate-50'
                    }`}
                  >
                    <button
                      type="button"
                      className={`w-5 h-5 rounded-md border flex items-center justify-center flex-shrink-0 mt-0.5 transition-colors ${
                        item.is_completed
                          ? 'bg-teal-600 border-teal-600 text-white'
                          : 'border-slate-300 bg-white'
                      }`}
                    >
                      {item.is_completed && <Check className="w-3.5 h-3.5" />}
                    </button>

                    <div className="flex-1 min-w-0">
                      <p className={`text-xs font-medium leading-relaxed ${item.is_completed ? 'line-through text-slate-400' : 'text-slate-800'}`}>
                        {item.task_text}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-2xs font-semibold text-slate-400 uppercase bg-slate-100 px-1.5 py-0.5 rounded">
                          {item.item_type.replace('_', ' ')}
                        </span>
                        {item.target_date && (
                          <span className="text-2xs text-teal-600 font-medium">Due: {item.target_date}</span>
                        )}
                        {item.notes && (
                          <span className="text-2xs text-slate-400 italic truncate max-w-xs">{item.notes}</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Backup Vendor Recommendation */}
            <div className="p-3.5 bg-amber-50/70 border border-amber-200/60 rounded-xl flex items-start gap-3">
              <Shield className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs font-semibold text-amber-900">Backup Vendor Contingency</p>
                <p className="text-xs text-amber-800 mt-0.5">
                  Pre-screened secondary option: <span className="font-semibold">{currentVendor.backup_vendor || `Emergency ${currentVendor.category} On-Call Agency`}</span>
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
