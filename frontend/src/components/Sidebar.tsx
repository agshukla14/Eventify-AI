import React from 'react';
import {
  Sparkles,
  LayoutDashboard,
  Wallet,
  CreditCard,
  UserCheck,
  Mail,
  Store,
  CloudSun,
  Calendar,
  Users,
  Lightbulb,
  Bot,
  Plus,
  LogOut,
  LogIn,
  X,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';
import { User } from '../types';

interface SidebarProps {
  activeTab: string;
  onNavigateTab: (tabId: string) => void;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
  currentUser: User | null;
  onLogout: () => void;
  onOpenAuth: () => void;
  onOpenNewPlan: () => void;
  onToggleChat: () => void;
  isChatOpen: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onNavigateTab,
  isOpenMobile,
  onCloseMobile,
  currentUser,
  onLogout,
  onOpenAuth,
  onOpenNewPlan,
  onToggleChat,
  isChatOpen,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Executive Dashboard', icon: LayoutDashboard },
    { id: 'budget', label: 'Budget Planner', icon: Wallet },
    { id: 'expenses', label: 'Expense Tracking', icon: CreditCard },
    { id: 'guests', label: 'Guest Management', icon: UserCheck },
    { id: 'invitations', label: 'AI Invitations', icon: Mail },
    { id: 'find_vendors', label: 'Find Vendors', icon: Store },
    { id: 'weather', label: 'Weather & Event Planning', icon: CloudSun },
    { id: 'timeline', label: 'Timeline & Schedule', icon: Calendar },
    { id: 'vendors', label: 'Vendor Checklist', icon: Users },
    { id: 'ideas', label: 'Personalized Ideas', icon: Lightbulb },
  ];

  const handleSelectTab = (tabId: string) => {
    onNavigateTab(tabId);
    if (isOpenMobile) {
      onCloseMobile();
    }
  };

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isOpenMobile && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-xs lg:hidden animate-in fade-in duration-200"
          aria-hidden="true"
        />
      )}

      {/* Sidebar Drawer */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-white border-r border-slate-200/80 flex flex-col justify-between transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isOpenMobile ? 'translate-x-0 shadow-2xl' : '-translate-x-full lg:static'
        }`}
      >
        {/* Top Header & Brand */}
        <div className="flex flex-col">
          <div className="h-16 px-5 border-b border-slate-200/80 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-700 via-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg text-slate-900 tracking-tight">Eventify</span>
                <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-md">
                  AI
                </span>
              </div>
            </div>

            {/* Mobile Close Button */}
            <button
              onClick={onCloseMobile}
              className="lg:hidden p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
              aria-label="Close menu"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Quick Action: New Plan Button */}
          <div className="p-3.5 pb-2">
            <button
              onClick={() => {
                onOpenNewPlan();
                if (isOpenMobile) onCloseMobile();
              }}
              className="w-full flex items-center justify-center gap-2 py-2 px-3.5 bg-indigo-600 hover:bg-indigo-700 active:scale-98 text-white text-xs font-bold rounded-xl shadow-sm shadow-indigo-600/20 transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>New Event Plan</span>
            </button>
          </div>

          {/* Navigation Links */}
          <div className="px-3 py-2 space-y-1 overflow-y-auto max-h-[calc(100vh-250px)] scrollbar-thin">
            <p className="px-3 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
              Navigation
            </p>

            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleSelectTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer group ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <Icon
                      className={`w-4 h-4 flex-shrink-0 transition-colors ${
                        isActive ? 'text-indigo-600' : 'text-slate-400 group-hover:text-slate-600'
                      }`}
                    />
                    <span className="truncate">{item.label}</span>
                  </div>
                  {isActive && (
                    <div className="w-1.5 h-1.5 rounded-full bg-indigo-600 flex-shrink-0" />
                  )}
                </button>
              );
            })}

            {/* AI Assistant Drawer Trigger */}
            <div className="pt-2">
              <button
                onClick={() => {
                  onToggleChat();
                  if (isOpenMobile) onCloseMobile();
                }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                  isChatOpen
                    ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                    : 'bg-indigo-50/60 hover:bg-indigo-50 text-indigo-900 border-indigo-200/80'
                }`}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <Bot className={`w-4 h-4 flex-shrink-0 ${isChatOpen ? 'text-white' : 'text-indigo-600'}`} />
                  <span className="truncate">Ask AI Assistant</span>
                </div>
                <Sparkles className={`w-3.5 h-3.5 ${isChatOpen ? 'text-white' : 'text-indigo-500'}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Bottom User Profile Section */}
        <div className="p-3 border-t border-slate-200/80 bg-slate-50/60">
          {currentUser ? (
            <div className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200/80 shadow-xs">
              <div className="flex items-center gap-2.5 min-w-0 pr-2">
                <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs flex-shrink-0">
                  {currentUser.full_name ? currentUser.full_name.charAt(0).toUpperCase() : 'U'}
                </div>
                <div className="min-w-0 truncate">
                  <p className="text-xs font-bold text-slate-800 truncate">
                    {currentUser.full_name || 'Event Organizer'}
                  </p>
                  <p className="text-[11px] text-slate-500 truncate">{currentUser.email}</p>
                </div>
              </div>
              <button
                onClick={onLogout}
                className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors flex-shrink-0 cursor-pointer"
                title="Log Out"
                aria-label="Log Out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => {
                onOpenAuth();
                if (isOpenMobile) onCloseMobile();
              }}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 text-xs font-bold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-xl transition-colors cursor-pointer"
            >
              <LogIn className="w-4 h-4" />
              <span>Sign In / Register</span>
            </button>
          )}
        </div>
      </aside>
    </>
  );
};

