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
  Menu,
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
  onToggleMobileMenu?: () => void;
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
  onToggleMobileMenu,
}) => {
  const [showEventDropdown, setShowEventDropdown] = useState(false);
  const [showExportDropdown, setShowExportDropdown] = useState(false);
  const [showUserDropdown, setShowUserDropdown] = useState(false);

  return (
    <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200/80">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-2 sm:gap-4">
        {/* Left: Mobile Menu Toggle & Brand Logo */}
        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          {onToggleMobileMenu && (
            <button
              onClick={onToggleMobileMenu}
              className="lg:hidden p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
              aria-label="Toggle navigation menu"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}

          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-700 via-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Sparkles className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div>
              <div className="flex items-center gap-1.5 sm:gap-2">
                <span className="font-extrabold text-base sm:text-lg text-slate-900 tracking-tight">Eventify</span>
                <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full">
                  AI Planner
                </span>
              </div>
              <p className="text-[11px] text-slate-500 hidden md:block">Weddings • Birthdays • Community Events</p>
            </div>
          </div>
        </div>

        {/* Center: Event Switcher Dropdown */}
        {eventsList.length > 0 && (
          <div className="relative min-w-0">
            <button
              onClick={() => setShowEventDropdown(!showEventDropdown)}
              className="flex items-center gap-1.5 sm:gap-2.5 px-3 py-1.5 text-xs sm:text-sm font-semibold text-slate-800 bg-slate-100/80 hover:bg-slate-200/80 rounded-xl transition-colors border border-slate-200 max-w-[130px] sm:max-w-xs truncate cursor-pointer shadow-2xs"
            >
              <Calendar className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-indigo-600 flex-shrink-0" />
              <span className="truncate">{currentPlan ? currentPlan.intake.title : 'Select Event'}</span>
              <ChevronDown className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-slate-400 flex-shrink-0" />
            </button>

            {showEventDropdown && (
              <div className="absolute left-0 mt-2 w-72 sm:w-80 bg-white rounded-2xl shadow-xl border border-slate-200/90 py-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="px-3.5 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Saved Celebrations ({eventsList.length})
                </div>
                <div className="max-h-64 overflow-y-auto divide-y divide-slate-100">
                  {eventsList.map((ev) => (
                    <button
                      key={ev.event_id}
                      onClick={() => {
                        onSelectEvent(ev.event_id);
                        setShowEventDropdown(false);
                      }}
                      className="w-full text-left px-3.5 py-2.5 text-sm hover:bg-indigo-50/60 flex items-center justify-between group transition-colors cursor-pointer"
                    >
                      <div className="truncate pr-2">
                        <p className="font-semibold text-slate-800 truncate text-xs sm:text-sm">{ev.title}</p>
                        <p className="text-[11px] text-slate-500 capitalize">
                          {ev.event_type} • {ev.days_left}d left
                        </p>
                      </div>
                      {currentPlan?.event_id === ev.event_id && (
                        <Check className="w-4 h-4 text-indigo-600 flex-shrink-0" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Right Action Buttons */}
        <div className="flex items-center gap-1.5 sm:gap-2.5">
          {/* New Event Button */}
          <button
            onClick={onOpenNewModal}
            className="flex items-center gap-1.5 px-3 sm:px-3.5 py-1.5 text-xs sm:text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 active:scale-95 rounded-xl shadow-sm shadow-indigo-600/20 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">New Plan</span>
          </button>

          {/* Export Dropdown */}
          {currentPlan && (
            <div className="relative">
              <button
                onClick={() => setShowExportDropdown(!showExportDropdown)}
                className="flex items-center gap-1 px-2.5 sm:px-3 py-1.5 text-xs sm:text-sm font-semibold text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200/90 rounded-xl shadow-xs transition-colors cursor-pointer"
              >
                <Download className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-slate-500" />
                <span className="hidden md:inline">Export</span>
                <ChevronDown className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-slate-400" />
              </button>

              {showExportDropdown && (
                <div className="absolute right-0 mt-2 w-52 bg-white rounded-2xl shadow-xl border border-slate-200/90 py-1.5 z-50 animate-in fade-in zoom-in-95 duration-150">
                  <a
                    href={getExportPdfUrl(currentPlan.event_id)}
                    download
                    onClick={() => setShowExportDropdown(false)}
                    className="flex items-center gap-2.5 px-3.5 py-2 text-xs sm:text-sm text-slate-700 hover:bg-indigo-50 hover:text-indigo-900 transition-colors"
                  >
                    <FileText className="w-4 h-4 text-rose-500" />
                    <span className="font-medium">Download as PDF</span>
                  </a>
                  <a
                    href={getExportCsvUrl(currentPlan.event_id)}
                    download
                    onClick={() => setShowExportDropdown(false)}
                    className="flex items-center gap-2.5 px-3.5 py-2 text-xs sm:text-sm text-slate-700 hover:bg-indigo-50 hover:text-indigo-900 transition-colors"
                  >
                    <Table className="w-4 h-4 text-emerald-600" />
                    <span className="font-medium">Download as CSV</span>
                  </a>
                </div>
              )}
            </div>
          )}

          {/* AI Assistant Chat Trigger */}
          {currentPlan && (
            <button
              onClick={onToggleChat}
              className={`p-1.5 sm:px-3 sm:py-1.5 text-xs sm:text-sm font-semibold rounded-xl border transition-all cursor-pointer flex items-center gap-1.5 ${
                isChatOpen
                  ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                  : 'bg-indigo-50/70 hover:bg-indigo-100 text-indigo-900 border-indigo-200'
              }`}
              title="Toggle AI Assistant"
            >
              <Bot className="w-4 h-4" />
              <span className="hidden lg:inline">Ask AI</span>
            </button>
          )}

          {/* User Auth Profile Dropdown */}
          <div className="relative">
            {currentUser ? (
              <div>
                <button
                  onClick={() => setShowUserDropdown(!showUserDropdown)}
                  className="flex items-center gap-1.5 p-1 sm:px-2.5 sm:py-1 rounded-xl hover:bg-slate-100 border border-transparent hover:border-slate-200 transition-colors cursor-pointer"
                >
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-indigo-100 border border-indigo-200 text-indigo-700 flex items-center justify-center font-bold text-xs">
                    {currentUser.full_name ? currentUser.full_name.charAt(0).toUpperCase() : 'U'}
                  </div>
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden sm:block" />
                </button>

                {showUserDropdown && (
                  <div className="absolute right-0 mt-2 w-56 bg-white rounded-2xl shadow-xl border border-slate-200/90 py-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                    <div className="px-4 py-2 border-b border-slate-100">
                      <p className="text-xs font-bold text-slate-900 truncate">
                        {currentUser.full_name || 'Event Organizer'}
                      </p>
                      <p className="text-[11px] text-slate-500 truncate">{currentUser.email}</p>
                    </div>
                    <button
                      onClick={() => {
                        setShowUserDropdown(false);
                        onLogout();
                      }}
                      className="w-full text-left px-4 py-2.5 text-xs font-semibold text-rose-600 hover:bg-rose-50 flex items-center gap-2 transition-colors cursor-pointer"
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
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-xl transition-colors cursor-pointer"
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
