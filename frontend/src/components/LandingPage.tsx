import React from 'react';
import {
  Sparkles,
  Wallet,
  Users,
  Mail,
  CloudSun,
  Store,
  ShieldCheck,
  ArrowRight,
  CheckCircle2,
  Calendar,
  Clock,
  TrendingDown,
  Layers,
  ChevronRight,
  Heart,
  PartyPopper,
  Building2,
  Plus,
  LogIn,
  UserPlus,
} from 'lucide-react';

interface LandingPageProps {
  onOpenLogin: () => void;
  onOpenRegister: () => void;
  onOpenIntake: () => void;
  onExploreDemo?: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onOpenLogin,
  onOpenRegister,
  onOpenIntake,
  onExploreDemo,
}) => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900 selection:bg-indigo-600 selection:text-white">
      {/* Top Navigation */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Logo & Brand */}
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-700 via-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-xl tracking-tight text-slate-900">Eventify</span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/80">
                SaaS
              </span>
            </div>
          </div>

          {/* Center Links (Desktop) */}
          <nav className="hidden md:flex items-center gap-7 text-xs font-semibold text-slate-600">
            <a href="#features" className="hover:text-indigo-600 transition-colors">Features</a>
            <a href="#solutions" className="hover:text-indigo-600 transition-colors">Solutions</a>
            <a href="#budget" className="hover:text-indigo-600 transition-colors">Smart Budget AI</a>
            <a href="#invitations" className="hover:text-indigo-600 transition-colors">Invitation Studio</a>
          </nav>

          {/* Action CTAs */}
          <div className="flex items-center gap-2.5 sm:gap-3">
            <button
              onClick={onOpenIntake}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-lg transition-colors cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5 text-indigo-600" />
              <span>New Plan</span>
            </button>

            <button
              onClick={onOpenLogin}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:text-indigo-600 bg-transparent hover:bg-indigo-50/50 rounded-lg transition-colors cursor-pointer"
            >
              <LogIn className="w-3.5 h-3.5 text-slate-500" />
              <span>Sign In</span>
            </button>

            <button
              onClick={onOpenRegister}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 active:scale-95 rounded-lg shadow-sm shadow-indigo-600/25 transition-all cursor-pointer"
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>Get Started Free</span>
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-12 pb-20 sm:pt-16 sm:pb-28 overflow-hidden bg-gradient-to-b from-white via-indigo-50/20 to-slate-50 border-b border-slate-200/60">
        {/* Subtle decorative glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-indigo-50 border border-indigo-200/80 text-indigo-800 text-xs font-semibold mb-6 shadow-xs">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>Next-Generation AI Event Planning Platform</span>
          </div>

          {/* Main Headline */}
          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 max-w-4xl mx-auto leading-[1.12]">
            Plan Every Celebration.{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-700 via-indigo-600 to-indigo-500">
              Perfect Every Detail.
            </span>
          </h1>

          {/* Supporting Text */}
          <p className="mt-5 text-sm sm:text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
            Your intelligent event-planning companion. Manage budgets, guests, vendors and invitations in one place.
          </p>

          {/* Primary CTA Buttons */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3 sm:gap-4">
            <button
              onClick={onOpenRegister}
              className="inline-flex items-center gap-2 px-6 py-3 text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 active:scale-95 rounded-xl shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
            >
              <span>Get Started Free</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              onClick={onOpenIntake}
              className="inline-flex items-center gap-2 px-6 py-3 text-sm font-semibold text-slate-800 bg-white hover:bg-slate-100 border border-slate-300 rounded-xl shadow-xs transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4 text-indigo-600" />
              <span>Create Event Plan</span>
            </button>

            {onExploreDemo && (
              <button
                onClick={onExploreDemo}
                className="inline-flex items-center gap-2 px-5 py-3 text-sm font-semibold text-indigo-700 hover:text-indigo-800 bg-indigo-50/90 hover:bg-indigo-100 border border-indigo-200 rounded-xl transition-all cursor-pointer"
              >
                <Sparkles className="w-4 h-4 text-indigo-600" />
                <span>Explore Live Demo</span>
              </button>
            )}

            <button
              onClick={onOpenLogin}
              className="inline-flex items-center gap-1.5 px-5 py-3 text-sm font-semibold text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-300 rounded-xl transition-all cursor-pointer"
            >
              <span>Sign In</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Trust badges */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-500">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Deterministic Financial Safety</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>English, Hindi & Gujarati Studio</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>14-Day Hyperlocal Weather Radar</span>
            </div>
          </div>

          {/* SaaS Mockup / Product Showcase Visual */}
          <div className="mt-12 sm:mt-16 max-w-5xl mx-auto rounded-3xl bg-white border border-slate-200/80 shadow-2xl p-4 sm:p-6 text-left relative overflow-hidden">
            {/* Top Mockup Bar */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 text-xs">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-rose-400" />
                  <div className="w-3 h-3 rounded-full bg-amber-400" />
                  <div className="w-3 h-3 rounded-full bg-emerald-400" />
                </div>
                <span className="text-slate-400 font-mono text-[11px] ml-2">eventify.ai/app/dashboard</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200 text-[11px]">
                  ● Live Sync
                </span>
              </div>
            </div>

            {/* Mockup Dashboard Content */}
            <div className="pt-5 space-y-5">
              {/* Event Header Banner */}
              <div className="bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 rounded-2xl p-5 sm:p-6 text-white shadow-sm flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-white/15 backdrop-blur-md rounded-full">
                      Wedding Celebration
                    </span>
                    <span className="text-xs text-indigo-200">📍 Jaipur • 👥 350 Guests</span>
                  </div>
                  <h3 className="text-xl sm:text-2xl font-black tracking-tight mt-1">
                    Priya & Rohan Royal Palace Wedding
                  </h3>
                  <p className="text-xs text-indigo-200 mt-0.5">
                    Theme: Royal Rajasthani Heritage & Marigolds • Traditional Vedic Rituals
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <div className="px-3.5 py-2 bg-white/10 rounded-xl text-center backdrop-blur-md border border-white/10">
                    <p className="text-xs text-indigo-200">Countdown</p>
                    <p className="text-base font-extrabold text-white">180 Days</p>
                  </div>
                </div>
              </div>

              {/* 4 Metric Cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200/60">
                  <div className="flex items-center justify-between text-slate-500 mb-1">
                    <span className="text-xs font-semibold">Planned Budget</span>
                    <Wallet className="w-4 h-4 text-indigo-600" />
                  </div>
                  <p className="text-lg sm:text-xl font-bold text-slate-900">₹25,00,000</p>
                  <p className="text-[11px] text-emerald-600 font-medium mt-0.5">13 Categories Balanced</p>
                </div>

                <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200/60">
                  <div className="flex items-center justify-between text-slate-500 mb-1">
                    <span className="text-xs font-semibold">Smart Savings</span>
                    <TrendingDown className="w-4 h-4 text-emerald-600" />
                  </div>
                  <p className="text-lg sm:text-xl font-bold text-emerald-600">₹3,50,000</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">AI Optimizer Reallocated</p>
                </div>

                <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200/60">
                  <div className="flex items-center justify-between text-slate-500 mb-1">
                    <span className="text-xs font-semibold">Confirmed RSVPs</span>
                    <Users className="w-4 h-4 text-indigo-600" />
                  </div>
                  <p className="text-lg sm:text-xl font-bold text-slate-900">328 / 350</p>
                  <p className="text-[11px] text-indigo-600 font-medium mt-0.5">94% Confirmation Rate</p>
                </div>

                <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200/60">
                  <div className="flex items-center justify-between text-slate-500 mb-1">
                    <span className="text-xs font-semibold">Weather Radar</span>
                    <CloudSun className="w-4 h-4 text-amber-500" />
                  </div>
                  <p className="text-lg sm:text-xl font-bold text-slate-900">28°C Clear</p>
                  <p className="text-[11px] text-emerald-600 font-medium mt-0.5">0% Rain Probability</p>
                </div>
              </div>

              {/* Micro feature pills */}
              <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-indigo-50/60 rounded-xl border border-indigo-100 text-xs">
                <div className="flex items-center gap-2 text-indigo-900 font-medium">
                  <Sparkles className="w-4 h-4 text-indigo-600 flex-shrink-0" />
                  <span>AI Smart Budget Assistant: "Protected Venue & Catering while optimizing Decor by 14%."</span>
                </div>
                <button
                  onClick={onOpenRegister}
                  className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-xs transition-colors cursor-pointer"
                >
                  Explore Platform
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Highlights Grid */}
      <section id="features" className="py-16 sm:py-24 bg-white border-b border-slate-200/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-14">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">Unified Architecture</span>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-slate-900 mt-2 tracking-tight">
              Four Core Pillars Built for Flawless Events
            </h2>
            <p className="text-sm sm:text-base text-slate-500 mt-3">
              Eventify eliminates fragmented spreadsheets by combining deterministic financial calculations with cutting-edge Gemini AI intelligence.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Feature 1 */}
            <div className="p-6 rounded-2xl bg-slate-50/60 border border-slate-200/80 hover:border-indigo-300 hover:shadow-card-hover transition-all">
              <div className="w-12 h-12 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center mb-4">
                <Wallet className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">AI Smart Budget Optimizer</h3>
              <p className="text-xs sm:text-sm text-slate-600 mt-2 leading-relaxed">
                Deterministic 13-category financial balancing, expense protection, and conversational reallocations without numerical LLM hallucinations.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-6 rounded-2xl bg-slate-50/60 border border-slate-200/80 hover:border-indigo-300 hover:shadow-card-hover transition-all">
              <div className="w-12 h-12 rounded-xl bg-rose-100 text-rose-700 flex items-center justify-center mb-4">
                <Mail className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Multilingual Invitation Studio</h3>
              <p className="text-xs sm:text-sm text-slate-600 mt-2 leading-relaxed">
                Generate bespoke invitations in English, Hindi, and Gujarati with print-ready ReportLab PDF exports and 800×1120 luxury PNG cards.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-6 rounded-2xl bg-slate-50/60 border border-slate-200/80 hover:border-indigo-300 hover:shadow-card-hover transition-all">
              <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center mb-4">
                <Users className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Guest RSVP & Dietary Tracking</h3>
              <p className="text-xs sm:text-sm text-slate-600 mt-2 leading-relaxed">
                Manage guest rosters, track Jain/Halal/Vegan dietary preferences, family party sizes, and RSVP statuses with instant WhatsApp sharing.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="p-6 rounded-2xl bg-slate-50/60 border border-slate-200/80 hover:border-indigo-300 hover:shadow-card-hover transition-all">
              <div className="w-12 h-12 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center mb-4">
                <CloudSun className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Atmospheric Radar & Vendors</h3>
              <p className="text-xs sm:text-sm text-slate-600 mt-2 leading-relaxed">
                14-day Open-Meteo weather forecasting, automated precipitation contingency warnings, and verified vendor contract rosters.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Solutions Section (Weddings, Birthdays, Community) */}
      <section id="solutions" className="py-16 sm:py-20 bg-slate-50 border-b border-slate-200/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">Tailored Archetypes</span>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-1">
              Engineered for Every Milestone
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mb-4">
                  <Heart className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-bold text-slate-900">Luxury Weddings</h3>
                <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                  Baraat logistics, Vedic rituals, floral mandap budget protections, sangeet gala schedules, and bilingual Indic stationery.
                </p>
              </div>
              <button
                onClick={onOpenIntake}
                className="mt-6 inline-flex items-center gap-1.5 text-xs font-bold text-indigo-600 hover:text-indigo-800"
              >
                <span>Plan a Wedding</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mb-4">
                  <PartyPopper className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-bold text-slate-900">Milestone Birthdays</h3>
                <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                  Superhero themes, custom cake planning, interactive entertainment schedules, kid dietary tracking, and fun digital cards.
                </p>
              </div>
              <button
                onClick={onOpenIntake}
                className="mt-6 inline-flex items-center gap-1.5 text-xs font-bold text-indigo-600 hover:text-indigo-800"
              >
                <span>Plan a Birthday</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4">
                  <Building2 className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-bold text-slate-900">Community Festivals</h3>
                <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                  Civic green melas, civic committee coordination, solar staging, crowd flow milestones, and neighborhood volunteer rosters.
                </p>
              </div>
              <button
                onClick={onOpenIntake}
                className="mt-6 inline-flex items-center gap-1.5 text-xs font-bold text-indigo-600 hover:text-indigo-800"
              >
                <span>Plan a Festival</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action Section */}
      <section className="py-16 sm:py-20 bg-gradient-to-tr from-indigo-900 via-indigo-800 to-slate-900 text-white relative overflow-hidden">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          <h2 className="text-2xl sm:text-4xl font-extrabold tracking-tight">
            Ready to Transform Your Event Management?
          </h2>
          <p className="mt-3 text-sm sm:text-base text-indigo-200 max-w-xl mx-auto">
            Join thousands of professional organizers, families, and communities planning flawless celebrations with Eventify AI.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <button
              onClick={onOpenRegister}
              className="px-6 py-3 text-sm font-bold text-indigo-950 bg-white hover:bg-slate-100 rounded-xl shadow-lg transition-all cursor-pointer"
            >
              Create Account Free
            </button>
            <button
              onClick={onOpenLogin}
              className="px-6 py-3 text-sm font-semibold text-white bg-indigo-700/60 hover:bg-indigo-700 border border-indigo-500/50 rounded-xl transition-all cursor-pointer"
            >
              Sign In to Your Events
            </button>
          </div>
        </div>
      </section>

      {/* Professional Footer */}
      <footer className="bg-slate-900 text-slate-400 py-12 border-t border-slate-800 text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-6 pb-8 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white">
                <Sparkles className="w-4 h-4" />
              </div>
              <span className="font-extrabold text-lg text-white tracking-tight">Eventify</span>
              <span className="text-[10px] text-slate-400 ml-2">Intelligent Event Management SaaS</span>
            </div>
            <div className="flex items-center gap-6">
              <button onClick={onOpenLogin} className="hover:text-white transition-colors">Sign In</button>
              <button onClick={onOpenRegister} className="hover:text-white transition-colors">Create Account</button>
              <button onClick={onOpenIntake} className="hover:text-white transition-colors">New Event Plan</button>
            </div>
          </div>
          <div className="pt-8 flex flex-wrap items-center justify-between gap-4">
            <p>© 2026 Eventify AI. All rights reserved.</p>
            <p>Designed for Weddings, Birthdays, and Community Celebrations.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};
