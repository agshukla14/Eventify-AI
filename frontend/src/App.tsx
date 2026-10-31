import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Wallet,
  Calendar,
  Users,
  Lightbulb,
  Bot,
  Plus,
  CreditCard,
  UserCheck,
  Mail,
  Store,
  CloudSun,
  LayoutDashboard,
} from 'lucide-react';
import { FullEventPlan, DashboardSummary, EventIntake, User } from './types';
import {
  listEvents,
  getEvent,
  createEvent,
  updateEvent,
  getCurrentUser,
  logoutUser,
  getStoredToken,
} from './api';
import { Navbar } from './components/Navbar';
import { IntakeModal } from './components/IntakeModal';
import { DashboardStats } from './components/DashboardStats';
import { ExecutiveDashboard } from './components/ExecutiveDashboard';
import { BudgetTab } from './components/BudgetTab';
import { ExpenseTab } from './components/ExpenseTab';
import { GuestsTab } from './components/GuestsTab';
import { InvitationsTab } from './components/InvitationsTab';
import { FindVendorsTab } from './components/FindVendorsTab';
import { WeatherPlannerTab } from './components/WeatherPlannerTab';
import { TimelineTab } from './components/TimelineTab';
import { VendorsTab } from './components/VendorsTab';
import { IdeasTab } from './components/IdeasTab';
import { ChatAssistantDrawer } from './components/ChatAssistantDrawer';
import { AuthModal } from './components/AuthModal';

export function App() {
  const [eventsList, setEventsList] = useState<DashboardSummary[]>([]);
  const [currentPlan, setCurrentPlan] = useState<FullEventPlan | null>(null);
  const [activeTab, setActiveTab] = useState<
    | 'dashboard'
    | 'budget'
    | 'expenses'
    | 'guests'
    | 'invitations'
    | 'find_vendors'
    | 'weather'
    | 'timeline'
    | 'vendors'
    | 'ideas'
  >('budget');
  const [isIntakeOpen, setIsIntakeOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setIsLoading(true);
    try {
      // 1. Check current authenticated user session if token exists
      const token = getStoredToken();
      if (token) {
        try {
          const user = await getCurrentUser();
          setCurrentUser(user);
        } catch {
          setCurrentUser(null);
        }
      } else {
        setCurrentUser(null);
      }

      // 2. Fetch event summaries
      const summaries = await listEvents();
      setEventsList(summaries);
      if (summaries.length > 0) {
        const full = await getEvent(summaries[0].event_id);
        setCurrentPlan(full);
      } else {
        // Automatically seed with a demo wedding so user immediately sees an active plan
        await handleSeedDemoWedding();
      }
    } catch (e) {
      console.error('Failed to load initial data:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSeedDemoWedding = async () => {
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 180);
    const demoIntake: EventIntake = {
      event_type: 'wedding',
      title: 'Priya & Rohan Royal Heritage Wedding',
      date: futureDate.toISOString().split('T')[0],
      city: 'Jaipur',
      guest_count: 350,
      total_budget: 2500000,
      currency: 'INR',
      theme_style: 'Royal Rajasthani Heritage & Marigolds',
      cultural_preferences: 'Traditional Marwari Customs & Sangeet Night',
      dietary_preferences: ['Vegetarian', 'Jain Options'],
      must_haves: ['Bespoke Floral Mandap', 'Vintage Car Baraat Procession', 'Live Folk Sitar Troupe'],
      age_group_details: 'Multi-generational families, elders, and young friends',
    };
    try {
      const created = await createEvent(demoIntake);
      setCurrentPlan(created);
      const updatedList = await listEvents();
      setEventsList(updatedList);
    } catch (err) {
      console.error('Demo seeding error:', err);
    }
  };

  const handleSelectEvent = async (eventId: string) => {
    try {
      const full = await getEvent(eventId);
      setCurrentPlan(full);
    } catch (err) {
      console.error('Error fetching event plan:', err);
    }
  };

  const handleCreatePlan = async (intake: EventIntake) => {
    setIsCreating(true);
    try {
      const created = await createEvent(intake);
      setCurrentPlan(created);
      const updatedList = await listEvents();
      setEventsList(updatedList);
      setIsIntakeOpen(false);
    } catch (err: any) {
      alert(`Failed to create plan: ${err.message}`);
    } finally {
      setIsCreating(false);
    }
  };

  const handleUpdatePlan = async (updatedPlan: FullEventPlan) => {
    setCurrentPlan(updatedPlan);
    try {
      const saved = await updateEvent(updatedPlan.event_id, updatedPlan);
      setCurrentPlan(saved);
      const updatedList = await listEvents();
      setEventsList(updatedList);
    } catch (err) {
      console.error('Error updating plan:', err);
    }
  };

  const handleRefreshCurrentPlan = async () => {
    if (!currentPlan) return;
    try {
      const refreshed = await getEvent(currentPlan.event_id);
      setCurrentPlan(refreshed);
      const updatedList = await listEvents();
      setEventsList(updatedList);
    } catch (err) {
      console.error('Error refreshing current plan:', err);
    }
  };

  const handleLogout = () => {
    logoutUser();
    setCurrentUser(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Top Navbar with Auth & Navigation */}
      <Navbar
        currentPlan={currentPlan}
        eventsList={eventsList}
        currentUser={currentUser}
        onSelectEvent={handleSelectEvent}
        onOpenNewModal={() => setIsIntakeOpen(true)}
        onToggleChat={() => setIsChatOpen(!isChatOpen)}
        isChatOpen={isChatOpen}
        onOpenAuthModal={() => setIsAuthOpen(true)}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-96 space-y-3">
            <div className="w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm font-medium text-slate-500">Loading Celebration Planner...</p>
          </div>
        ) : currentPlan ? (
          <>
            {/* Event Header Banner */}
            <div className="bg-gradient-to-r from-teal-800 via-teal-700 to-emerald-700 rounded-3xl p-6 sm:p-7 text-white shadow-md">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider bg-white/20 backdrop-blur-md rounded-full">
                      {currentPlan.intake.event_type}
                    </span>
                    <span className="text-xs text-teal-200">
                      📍 {currentPlan.intake.city} • 👥 {currentPlan.intake.guest_count} Guests
                    </span>
                  </div>
                  <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-1">
                    {currentPlan.intake.title}
                  </h1>
                  <p className="text-xs text-teal-100 mt-1 max-w-2xl">
                    Theme: <span className="font-semibold text-white">{currentPlan.intake.theme_style || 'Curated Aesthetic'}</span>
                    {currentPlan.intake.cultural_preferences ? ` • ${currentPlan.intake.cultural_preferences}` : ''}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setIsChatOpen(true)}
                    className="flex items-center gap-2 px-4 py-2 text-xs font-bold text-teal-950 bg-teal-200 hover:bg-white rounded-xl shadow-sm transition-all"
                  >
                    <Bot className="w-4 h-4 text-teal-700" />
                    <span>Ask AI Assistant</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Overview Stats Bar */}
            <DashboardStats plan={currentPlan} />

            {/* Tab Navigation with horizontal scrolling support */}
            <div className="border-b border-slate-200 overflow-x-auto pb-1 scrollbar-thin">
              <nav className="flex space-x-4 sm:space-x-6 min-w-max">
                {[
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
                ].map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as any)}
                      className={`pb-3 px-1 border-b-2 font-semibold text-xs sm:text-sm flex items-center gap-2 transition-all ${
                        isActive
                          ? 'border-teal-600 text-teal-700'
                          : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${isActive ? 'text-teal-600' : 'text-slate-400'}`} />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </nav>
            </div>

            {/* Active Tab View */}
            <div className="pt-2">
              {activeTab === 'dashboard' && (
                <ExecutiveDashboard
                  currentPlan={currentPlan}
                  onSelectEvent={handleSelectEvent}
                  onNavigateTab={(tab) => setActiveTab(tab as any)}
                  onOpenNewModal={() => setIsIntakeOpen(true)}
                  onToggleChat={() => setIsChatOpen(true)}
                />
              )}
              {activeTab === 'budget' && (
                <BudgetTab plan={currentPlan} onUpdatePlan={handleUpdatePlan} />
              )}
              {activeTab === 'expenses' && (
                <ExpenseTab plan={currentPlan} onRefreshPlan={handleRefreshCurrentPlan} />
              )}
              {activeTab === 'guests' && <GuestsTab plan={currentPlan} />}
              {activeTab === 'invitations' && <InvitationsTab plan={currentPlan} />}
              {activeTab === 'find_vendors' && (
                <FindVendorsTab plan={currentPlan} onRefreshPlan={handleRefreshCurrentPlan} />
              )}
              {activeTab === 'weather' && (
                <WeatherPlannerTab plan={currentPlan} onRefreshPlan={handleRefreshCurrentPlan} />
              )}
              {activeTab === 'timeline' && (
                <TimelineTab plan={currentPlan} onUpdatePlan={handleUpdatePlan} />
              )}
              {activeTab === 'vendors' && (
                <VendorsTab plan={currentPlan} onUpdatePlan={handleUpdatePlan} />
              )}
              {activeTab === 'ideas' && <IdeasTab plan={currentPlan} />}
            </div>
          </>
        ) : (
          /* Empty State */
          <div className="bg-white rounded-3xl border border-slate-200/80 p-12 text-center max-w-lg mx-auto shadow-xs space-y-4 my-12">
            <div className="w-16 h-16 rounded-2xl bg-teal-50 border border-teal-100 flex items-center justify-center text-teal-600 mx-auto">
              <Sparkles className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-bold text-slate-900">Start Planning Your Celebration</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Create your tailored event plan for a Wedding, Birthday, or Community Festival complete with budget allocations, timelines, vendor contracts, and personalized ideas.
            </p>
            <button
              onClick={() => setIsIntakeOpen(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-teal-600 hover:bg-teal-700 rounded-xl shadow-md transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Create Event Plan</span>
            </button>
          </div>
        )}
      </main>

      {/* Intake Modal */}
      <IntakeModal
        isOpen={isIntakeOpen}
        onClose={() => setIsIntakeOpen(false)}
        onSubmit={handleCreatePlan}
        isLoading={isCreating}
      />

      {/* Authentication Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onAuthSuccess={(user) => {
          setCurrentUser(user);
          loadInitialData();
        }}
      />

      {/* AI Assistant Chat Drawer */}
      {currentPlan && (
        <ChatAssistantDrawer
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
          currentPlan={currentPlan}
          onPlanUpdated={handleUpdatePlan}
        />
      )}
    </div>
  );
}

export default App;
