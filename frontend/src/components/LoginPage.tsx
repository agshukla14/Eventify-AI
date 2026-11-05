import React, { useState } from 'react';
import {
  Sparkles,
  Mail,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Calendar,
  Layers,
  ArrowLeft,
} from 'lucide-react';
import { loginUser } from '../api';
import { User } from '../types';

interface LoginPageProps {
  onLoginSuccess: (user: User) => void;
  onNavigateRegister: () => void;
  onNavigateLanding: () => void;
  initialEmail?: string;
  successMessage?: string | null;
}

export const LoginPage: React.FC<LoginPageProps> = ({
  onLoginSuccess,
  onNavigateRegister,
  onNavigateLanding,
  initialEmail = '',
  successMessage = null,
}) => {
  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError('Please provide both your email address and password.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await loginUser({ email: email.trim(), password });
      onLoginSuccess(res.user);
    } catch (err: any) {
      setError(err.message || 'Invalid email or password.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 selection:bg-indigo-600 selection:text-white">
      {/* Top Bar Return Button */}
      <div className="max-w-4xl w-full mx-auto px-4 mb-4">
        <button
          onClick={onNavigateLanding}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-indigo-600 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Eventify Home</span>
        </button>
      </div>

      <div className="max-w-4xl w-full mx-auto px-4">
        <div className="bg-white rounded-3xl shadow-xl border border-slate-200/90 overflow-hidden flex flex-col md:flex-row">
          {/* Left Column: Eventify SaaS Identity & Pillars (Desktop) */}
          <div className="hidden md:flex md:w-5/12 bg-gradient-to-br from-indigo-950 via-indigo-900 to-slate-950 text-white p-8 flex-col justify-between relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none" />

            <div className="relative z-10 space-y-6">
              {/* Brand Logo */}
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center text-white shadow-md">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <span className="font-extrabold text-xl tracking-tight text-white block">Eventify</span>
                  <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-300">Intelligent SaaS</span>
                </div>
              </div>

              {/* Tagline */}
              <div>
                <h2 className="text-xl font-extrabold tracking-tight text-white leading-snug">
                  Plan Every Celebration. Perfect Every Detail.
                </h2>
                <p className="text-xs text-indigo-200/90 mt-2 leading-relaxed">
                  The mission-critical celebration operating system trusted by modern event directors and hosts.
                </p>
              </div>

              {/* Feature Highlights */}
              <div className="space-y-3 pt-2">
                <div className="flex items-start gap-2.5 text-xs text-indigo-100">
                  <div className="w-5 h-5 rounded-md bg-indigo-800/80 flex items-center justify-center flex-shrink-0 mt-0.5 border border-indigo-700/60">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  </div>
                  <span>Deterministic financial optimization with strict contingency safety</span>
                </div>
                <div className="flex items-start gap-2.5 text-xs text-indigo-100">
                  <div className="w-5 h-5 rounded-md bg-indigo-800/80 flex items-center justify-center flex-shrink-0 mt-0.5 border border-indigo-700/60">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  </div>
                  <span>Bespoke multilingual typography in English, Hindi & Gujarati</span>
                </div>
                <div className="flex items-start gap-2.5 text-xs text-indigo-100">
                  <div className="w-5 h-5 rounded-md bg-indigo-800/80 flex items-center justify-center flex-shrink-0 mt-0.5 border border-indigo-700/60">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  </div>
                  <span>14-day hyperlocal meteorological radar and outdoor contingency</span>
                </div>
              </div>
            </div>

            <div className="relative z-10 pt-6 border-t border-indigo-800/60 flex items-center justify-between text-[11px] text-indigo-300">
              <span>Enterprise Account Isolation</span>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
          </div>

          {/* Right Column: Clean SaaS Login Form */}
          <div className="flex-1 p-6 sm:p-10 flex flex-col justify-center">
            {/* Mobile Header */}
            <div className="md:hidden flex items-center gap-2 mb-6">
              <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center text-white">
                <Sparkles className="w-4 h-4" />
              </div>
              <span className="font-extrabold text-lg text-slate-900">Eventify</span>
            </div>

            <div className="mb-6">
              <span className="text-[11px] font-bold text-indigo-600 uppercase tracking-wider block mb-1">
                Eventify SaaS Portal
              </span>
              <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                Sign in to your account
              </h1>
              <p className="text-xs text-slate-500 mt-1">
                Enter your credentials to access your event portfolios, budgets, and guest rosters.
              </p>
            </div>

            {/* Success Notification Banner */}
            {successMessage && (
              <div className="mb-4 p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start gap-2.5 text-xs text-emerald-800 animate-in fade-in">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                <span>{successMessage}</span>
              </div>
            )}

            {/* Error Notification Banner */}
            {error && (
              <div className="mb-4 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 animate-in fade-in space-y-2">
                <div className="flex items-start gap-2.5">
                  <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                  <span className="font-medium">{error}</span>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email Address */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    type="email"
                    required
                    autoFocus
                    placeholder="organizer@eventify.ai"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10 pr-3.5 py-2.5 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-10 pr-10 py-2.5 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-3 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Remember Me */}
              <div className="flex items-center justify-between text-xs pt-0.5">
                <label className="flex items-center gap-2 text-slate-600 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500 cursor-pointer"
                  />
                  <span>Remember my session on this device</span>
                </label>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 active:scale-[0.99] disabled:opacity-50 text-white font-bold text-xs sm:text-sm rounded-xl shadow-md shadow-indigo-600/20 transition-all flex items-center justify-center gap-2 cursor-pointer mt-2"
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Sign In to Eventify</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Registration Switcher Link */}
            <div className="mt-8 pt-5 border-t border-slate-100 text-center text-xs text-slate-500">
              Don't have an account yet?{' '}
              <button
                type="button"
                onClick={onNavigateRegister}
                className="font-bold text-indigo-600 hover:text-indigo-800 transition-colors cursor-pointer ml-1"
              >
                Create Account Free
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

