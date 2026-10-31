import React, { useState } from 'react';
import {
  Calendar,
  Sparkles,
  Download,
  Plus,
  Bot,
  ChevronDown,
  Check,
  FileText,
  Table,
  User as UserIcon,
  LogOut,
  LogIn,
} from 'lucide-react';
import { DashboardSummary, FullEventPlan, User } from '../types';
import { getExportCsvUrl, getExportPdfUrl } from '../api';

interface NavbarProps {
  currentPlan: FullEventPlan | null;
  eventsList: DashboardSummary[];
  currentUser: User | null;
  onSelectEvent: (eventId: string) => void;
  onOpenNewModal: () => void;
  onToggleChat: () => void;
  isChatOpen: boolean;
  onOpenAuthModal: () => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentPlan,
  eventsList,
  currentUser,
  onSelectEvent,
  onOpenNewModal,
  onToggleChat,
  isChatOpen,
  onOpenAuthModal,
  onLogout,
}) => {
  const [showEventDropdown, setShowEventDropdown] = useState(false);
  const [showExportDropdown, setShowExportDropdown] = useState(false);
  const [showUserDropdown, setShowUserDropdown] = useState(false);

  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand Logo & Name */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-600 to-emerald-400 flex items-center justify-center text-white shadow-md shadow-teal-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-slate-900 tracking-tight">CelebrationAI</span>
              <span className="px-2 py-0.5 text-xs font-semibold bg-teal-50 text-teal-700 border border-teal-200 rounded-full">
                GenAI Planner
              </span>
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">Weddings • Birthdays • Community Events</p>
          </div>
        </div>

        {/* Center: Event Switcher Dropdown */}
        {eventsList.length > 0 && (
          <div className="relative">
            <button
              onClick={() => setShowEventDropdown(!showEventDropdown)}
              className="flex items-center gap-2.5 px-3 py-1.5 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors border border-slate-200 max-w-xs truncate"
            >
              <Calendar className="w-4 h-4 text-teal-600 flex-shrink-0" />
              <span className="truncate">{currentPlan ? currentPlan.intake.title : 'Select Celebration'}</span>
              <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
            </button>

            {showEventDropdown && (
              <div className="absolute left-0 mt-2 w-72 bg-white rounded-xl shadow-xl border border-slate-200 py-1.5 z-50">
                <div className="px-3 py-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Saved Celebrations ({eventsList.length})
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {eventsList.map((ev) => (
                    <button
                      key={ev.event_id}
                      onClick={() => {
                        onSelectEvent(ev.event_id);
                        setShowEventDropdown(false);
                      }}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-teal-50 flex items-center justify-between group transition-colors"
                    >
                      <div className="truncate pr-2">
                        <p className="font-medium text-slate-800 truncate">{ev.title}</p>
                        <p className="text-xs text-slate-500 capitalize">
                          {ev.event_type} • {ev.days_left}d left
                        </p>
                      </div>
                      {currentPlan?.event_id === ev.event_id && (
                        <Check className="w-4 h-4 text-teal-600 flex-shrink-0" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {/* New Event Button */}
          <button
            onClick={onOpenNewModal}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 active:scale-95 rounded-lg shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">New Plan</span>
          </button>

          {/* Export Dropdown */}
          {currentPlan && (
            <div className="relative">
              <button
                onClick={() => setShowExportDropdown(!showExportDropdown)}
                className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg shadow-sm transition-colors"
              >
                <Download className="w-4 h-4 text-slate-500" />
                <span className="hidden md:inline">Export</span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {showExportDropdown && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-xl border border-slate-200 py-1.5 z-50">
                  <a
                    href={getExportPdfUrl(currentPlan.event_id)}
                    download
                    onClick={() => setShowExportDropdown(false)}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-teal-50 hover:text-teal-900 transition-colors"
                  >
                    <FileText className="w-4 h-4 text-rose-500" />
                    <span>Download as PDF</span>
                  </a>
                  <a
                    href={getExportCsvUrl(currentPlan.event_id)}
                    download
                    onClick={() => setShowExportDropdown(false)}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-teal-50 hover:text-teal-900 transition-colors"
                  >
                    <Table className="w-4 h-4 text-emerald-600" />
                    <span>Download as CSV</span>
                  </a>
                </div>
              )}
            </div>
          )}

          {/* AI Assistant Chat Toggle */}
          {currentPlan && (
            <button
              onClick={onToggleChat}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border transition-all ${
                isChatOpen
                  ? 'bg-teal-50 text-teal-800 border-teal-300 shadow-inner'
                  : 'bg-white text-slate-700 hover:bg-slate-50 border-slate-200 shadow-sm'
              }`}
            >
              <Bot className="w-4 h-4 text-teal-600" />
              <span className="hidden sm:inline">AI Assistant</span>
            </button>
          )}

          {/* User Profile / Authentication Menu */}
          {currentUser ? (
            <div className="relative">
              <button
                onClick={() => setShowUserDropdown(!showUserDropdown)}
                className="flex items-center gap-2 pl-2 pr-3 py-1 bg-slate-100 hover:bg-slate-200 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 transition-colors"
              >
                <div className="w-7 h-7 rounded-lg bg-teal-600 text-white flex items-center justify-center font-bold text-xs uppercase shadow-xs">
                  {currentUser.full_name ? currentUser.full_name.charAt(0) : 'U'}
                </div>
                <span className="hidden md:inline max-w-[100px] truncate">{currentUser.full_name}</span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {showUserDropdown && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-2xl shadow-xl border border-slate-200 py-2 z-50 animate-in fade-in">
                  <div className="px-4 py-2 border-b border-slate-100">
                    <p className="font-bold text-xs text-slate-900 truncate">{currentUser.full_name}</p>
                    <p className="text-2xs text-slate-500 truncate">{currentUser.email}</p>
                    <span className="inline-block mt-1 px-1.5 py-0.2 bg-teal-50 text-teal-700 text-2xs font-semibold rounded">
                      Verified Organizer
                    </span>
                  </div>
                  <button
                    onClick={() => {
                      setShowUserDropdown(false);
                      onLogout();
                    }}
                    className="w-full text-left px-4 py-2 text-xs text-rose-600 hover:bg-rose-50 flex items-center gap-2 transition-colors"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={onOpenAuthModal}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-teal-700 hover:text-teal-900 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded-xl transition-colors"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

export default Navbar;
