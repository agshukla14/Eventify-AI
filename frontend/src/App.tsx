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
import { Sidebar } from './components/Sidebar';
import { LandingPage } from './components/LandingPage';
import { LoginPage } from './components/LoginPage';
import { RegisterPage } from './components/RegisterPage';
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

type AuthView = 'landing' | 'login' | 'register';

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
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  // Authentication routing & transitions
  const [authView, setAuthView] = useState<AuthView>('landing');
  const [pendingEmail, setPendingEmail] = useState<string>('');
  const [loginSuccessMessage, setLoginSuccessMessage] = useState<string | null>(null);

  const getEventStorageKey = (user: User | null) => {
    return user?.id ? `eventify_selected_event_${user.id}` : 'eventify_selected_event_anon';
  };

  const getSavedEventId = (user: User | null): string | null => {
    try {
      return localStorage.getItem(getEventStorageKey(user));
    } catch {
      return null;
    }
  };

  const setSavedEventId = (user: User | null, eventId: string) => {
    try {
      localStorage.setItem(getEventStorageKey(user), eventId);
    } catch (e) {
      console.error('Failed to save selected event ID:', e);
    }
  };

  const clearSavedEventId = (user: User | null) => {
    try {
      localStorage.removeItem(getEventStorageKey(user));
    } catch (e) {
      console.error('Failed to clear selected event ID:', e);
    }
  };

  // URL parsing helper for deep links and browser navigation
  const parseAuthViewFromUrl = (): AuthView => {
    const path = window.location.pathname.toLowerCase();
    const search = new URLSearchParams(window.location.search);
    if (path.includes('login') || search.get('auth') === 'login') return 'login';
    if (path.includes('register') || search.get('auth') === 'register') return 'register';
    return 'landing';
  };

  const navigateAuth = (view: AuthView, email?: string) => {
    setAuthView(view);
    if (email !== undefined) {
      setPendingEmail(email);
    }
    const targetPath = view === 'landing' ? '/' : `/${view}`;
    if (window.location.pathname !== targetPath) {
      window.history.pushState({ authView: view }, '', targetPath);
    }
  };

  // Handle browser back and forward buttons
  useEffect(() => {
    const handlePopState = () => {
      setAuthView(parseAuthViewFromUrl());
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Check initial authentication and load data
  useEffect(() => {
    const initialView = parseAuthViewFromUrl();
    setAuthView(initialView);
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setIsLoading(true);
    try {
      const isLoggedOut = sessionStorage.getItem('eventify_logged_out') === 'true';
      const token = getStoredToken();

      if (isLoggedOut || !token) {
        setCurrentUser(null);
        setCurrentPlan(null);
        setEventsList([]);
        setIsLoading(false);
        return;
      }

      // Check current authenticated user session
      let activeUser: User | null = null;
      try {
        activeUser = await getCurrentUser();
        if (activeUser && activeUser.is_active) {
          setCurrentUser(activeUser);
        } else {
          setCurrentUser(null);
          setCurrentPlan(null);
          setEventsList([]);
          setIsLoading(false);
          return;
        }
      } catch {
        setCurrentUser(null);
        setCurrentPlan(null);
        setEventsList([]);
        setIsLoading(false);
        return;
      }

      // Authenticated and email-verified user: fetch their events
      const summaries = await listEvents();
      setEventsList(summaries);
      if (summaries.length > 0) {
        const savedId = getSavedEventId(activeUser);
        const targetEvent =
          savedId && summaries.some((s) => s.event_id === savedId)
            ? summaries.find((s) => s.event_id === savedId)!
            : summaries[0];

        setSavedEventId(activeUser, targetEvent.event_id);
        const full = await getEvent(targetEvent.event_id);
        setCurrentPlan(full);
      } else {
        setCurrentPlan(null);
      }
    } catch (e) {
      console.error('Failed to load initial data:', e);
      setCurrentPlan(null);
      setEventsList([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoginSuccess = async (user: User) => {
    sessionStorage.removeItem('eventify_logged_out');
    setCurrentUser(user);
    setAuthView('landing');
    if (window.location.pathname !== '/') {
      window.history.pushState({}, '', '/');
    }

    try {
      setIsLoading(true);
      const summaries = await listEvents();
      setEventsList(summaries);
      if (summaries.length > 0) {
        const savedId = getSavedEventId(user);
        const targetEvent =
          savedId && summaries.some((s) => s.event_id === savedId)
            ? summaries.find((s) => s.event_id === savedId)!
            : summaries[0];
        setSavedEventId(user, targetEvent.event_id);
        const full = await getEvent(targetEvent.event_id);
        setCurrentPlan(full);
      } else {
        setCurrentPlan(null);
      }
    } catch (err) {
      console.error('Error fetching user events after login:', err);
      setCurrentPlan(null);
      setEventsList([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectEvent = async (eventId: string) => {
    try {
      const full = await getEvent(eventId);
      setCurrentPlan(full);
      setSavedEventId(currentUser, eventId);
    } catch (err) {
      console.error('Error fetching event plan:', err);
    }
  };

  const handleCreatePlan = async (intake: EventIntake) => {
    setIsCreating(true);
    try {
      const created = await createEvent(intake);
      setCurrentPlan(created);
      setSavedEventId(currentUser, created.event_id);
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

  const handleLogout = async () => {
    sessionStorage.setItem('eventify_logged_out', 'true');
    clearSavedEventId(currentUser);
    logoutUser();
    setCurrentUser(null);
    setCurrentPlan(null);
    setEventsList([]);
    navigateAuth('login');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900 selection:bg-indigo-600 selection:text-white">
      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-screen space-y-3 bg-slate-50">
          <div className="w-9 h-9 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-semibold text-slate-600">Loading Eventify...</p>
        </div>
      ) : !currentUser && !currentPlan ? (
        /* =========================================================================
           PUBLIC UNTOUCHED EXPERIENCES FOR UNAUTHENTICATED VISITORS
           ========================================================================= */
        authView === 'login' ? (
          <LoginPage
            onLoginSuccess={handleLoginSuccess}
            onNavigateRegister={() => navigateAuth('register')}
            onNavigateLanding={() => navigateAuth('landing')}
            initialEmail={pendingEmail}
            successMessage={loginSuccessMessage}
          />
        ) : authView === 'register' ? (
          <RegisterPage
            onRegisterSuccess={(email) => {
              setPendingEmail(email);
              setLoginSuccessMessage('Account created successfully! Please sign in to continue.');
              navigateAuth('login', email);
            }}
            onNavigateLogin={() => navigateAuth('login')}
            onNavigateLanding={() => navigateAuth('landing')}
          />
        ) : (
          /* Public Landing Page */
          <LandingPage
            onOpenLogin={() => navigateAuth('login')}
            onOpenRegister={() => navigateAuth('register')}
            onOpenIntake={() => setIsIntakeOpen(true)}
          />
        )
      ) : (
        /* =========================================================================
           AUTHENTICATED SAAS DASHBOARD (STRICTLY FOR VERIFIED USERS)
           ========================================================================= */
        <div className="flex min-h-screen w-full">
          {/* Left Sidebar */}
          <Sidebar
            activeTab={activeTab}
            onNavigateTab={(tab) => setActiveTab(tab as any)}
            isOpenMobile={isMobileMenuOpen}
            onCloseMobile={() => setIsMobileMenuOpen(false)}
            currentUser={currentUser}
            onLogout={handleLogout}
            onOpenAuth={() => navigateAuth('login')}
            onOpenNewPlan={() => setIsIntakeOpen(true)}
            onToggleChat={() => setIsChatOpen(!isChatOpen)}
            isChatOpen={isChatOpen}
          />

          {/* Right Main Container */}
          <div className="flex-1 flex flex-col min-w-0 min-h-screen">
            {/* Top Navbar */}
            <Navbar
              currentPlan={currentPlan}
              eventsList={eventsList}
              currentUser={currentUser}
              onSelectEvent={handleSelectEvent}
              onOpenNewModal={() => setIsIntakeOpen(true)}
              onToggleChat={() => setIsChatOpen(!isChatOpen)}
              isChatOpen={isChatOpen}
              onOpenAuthModal={() => navigateAuth('login')}
              onLogout={handleLogout}
              onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            />

            {/* Main Content Area */}
            <main className="flex-1 max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 py-5 sm:py-6 space-y-5 sm:space-y-6">
              {currentPlan ? (
                <>
                  {/* Event Header Banner in Deep Indigo */}
                  <div className="bg-gradient-to-r from-indigo-950 via-indigo-900 to-slate-900 rounded-3xl p-5 sm:p-7 text-white shadow-md relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
                    <div className="relative z-10 flex flex-wrap items-center justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-white/15 backdrop-blur-md rounded-full text-indigo-100">
                            {currentPlan.intake.event_type}
                          </span>
                          <span className="text-xs text-indigo-200">
                            📍 {currentPlan.intake.city} • 👥 {currentPlan.intake.guest_count} Guests
                          </span>
                        </div>
                        <h1 className="text-xl sm:text-3xl font-extrabold tracking-tight mt-1.5">
                          {currentPlan.intake.title}
                        </h1>
                        <p className="text-xs text-indigo-200 mt-1 max-w-2xl leading-relaxed">
                          Theme:{' '}
                          <span className="font-semibold text-white">
                            {currentPlan.intake.theme_style || 'Curated Aesthetic'}
                          </span>
                          {currentPlan.intake.cultural_preferences
                            ? ` • ${currentPlan.intake.cultural_preferences}`
                            : ''}
                        </p>
                      </div>

                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => setIsChatOpen(true)}
                          className="flex items-center gap-2 px-4 py-2 text-xs font-bold text-indigo-950 bg-indigo-200 hover:bg-white rounded-xl shadow-xs transition-all cursor-pointer"
                        >
                          <Bot className="w-4 h-4 text-indigo-700" />
                          <span>Ask AI Assistant</span>
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Overview Stats Bar */}
                  <DashboardStats plan={currentPlan} />

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
                      <FindVendorsTab
                        plan={currentPlan}
                        onRefreshPlan={handleRefreshCurrentPlan}
                      />
                    )}
                    {activeTab === 'weather' && (
                      <WeatherPlannerTab
                        plan={currentPlan}
                        onRefreshPlan={handleRefreshCurrentPlan}
                      />
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
                /* Authenticated User without Events */
                <div className="bg-white rounded-3xl border border-slate-200/80 p-8 sm:p-12 text-center max-w-lg mx-auto shadow-xs space-y-4 my-12">
                  <div className="w-16 h-16 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mx-auto">
                    <Sparkles className="w-8 h-8" />
                  </div>
                  <h3 className="text-xl font-bold text-slate-900">Start Planning Your Celebration</h3>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Create your tailored event plan for a Wedding, Birthday, or Community Festival complete with budget allocations, timelines, vendor contracts, and personalized ideas.
                  </p>
                  <button
                    onClick={() => setIsIntakeOpen(true)}
                    className="inline-flex items-center gap-2 px-5 py-2.5 text-xs sm:text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-md transition-all cursor-pointer"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Create Event Plan</span>
                  </button>
                </div>
              )}
            </main>
          </div>
        </div>
      )}

      {/* Intake Modal for Event Creation */}
      <IntakeModal
        isOpen={isIntakeOpen}
        onClose={() => setIsIntakeOpen(false)}
        onSubmit={handleCreatePlan}
        isLoading={isCreating}
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
