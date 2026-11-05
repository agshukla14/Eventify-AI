import React, { useState } from 'react';
import {
  Sparkles,
  Mail,
  Lock,
  User as UserIcon,
  Eye,
  EyeOff,
  AlertCircle,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  ArrowLeft,
} from 'lucide-react';
import { registerUser } from '../api';

interface RegisterPageProps {
  onRegisterSuccess: (email: string) => void;
  onNavigateLogin: () => void;
  onNavigateLanding: () => void;
}

export const RegisterPage: React.FC<RegisterPageProps> = ({
  onRegisterSuccess,
  onNavigateLogin,
  onNavigateLanding,
}) => {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Dynamic password validation checks
  const hasMinLength = password.length >= 6;
  const hasLetter = /[a-zA-Z]/.test(password);
  const hasNumberOrSymbol = /[0-9!@#$%^&*(),.?":{}|<>]/.test(password);
  const passwordsMatch = password.length > 0 && password === confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!fullName.trim() || !email.trim() || !password || !confirmPassword) {
      setError('Please fill in all required fields.');
      return;
    }

    if (!hasMinLength || !hasLetter || !hasNumberOrSymbol) {
      setError('Password must be at least 6 characters and contain letters and numbers.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match. Please ensure both fields are identical.');
      return;
    }

    if (!termsAccepted) {
      setError('You must accept the Terms and Conditions to create an account.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await registerUser({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        terms_accepted: termsAccepted,
      });
      onRegisterSuccess(res.email || email.trim());
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please check your information.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-8 sm:px-6 lg:px-8 selection:bg-indigo-600 selection:text-white">
      {/* Return button */}
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
          {/* Left Column: SaaS Value Proposition */}
          <div className="hidden md:flex md:w-5/12 bg-gradient-to-br from-indigo-950 via-indigo-900 to-slate-950 text-white p-8 flex-col justify-between relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none" />

            <div className="relative z-10 space-y-6">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center text-white shadow-md">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <span className="font-extrabold text-xl tracking-tight text-white block">Eventify</span>
                  <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-300">Intelligent SaaS</span>
                </div>
              </div>

              <div>
                <h2 className="text-xl font-extrabold tracking-tight text-white leading-snug">
                  Get Started with Eventify Today
                </h2>
                <p className="text-xs text-indigo-200/90 mt-2 leading-relaxed">
                  Join professional celebration directors orchestrating luxury weddings, birthdays, and community festivals.
                </p>
              </div>

              <div className="space-y-3 pt-2">
                <div className="flex items-start gap-2.5 text-xs text-indigo-100">
                  <div className="w-5 h-5 rounded-md bg-indigo-800/80 flex items-center justify-center flex-shrink-0 mt-0.5 border border-indigo-700/60">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  </div>
                  <span>Instant account activation with immediate dashboard access</span>
                </div>
                <div className="flex items-start gap-2.5 text-xs text-indigo-100">
                  <div className="w-5 h-5 rounded-md bg-indigo-800/80 flex items-center justify-center flex-shrink-0 mt-0.5 border border-indigo-700/60">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  </div>
                  <span>Deterministic financial calculations with zero AI hallucination</span>
                </div>
                <div className="flex items-start gap-2.5 text-xs text-indigo-100">
                  <div className="w-5 h-5 rounded-md bg-indigo-800/80 flex items-center justify-center flex-shrink-0 mt-0.5 border border-indigo-700/60">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  </div>
                  <span>Isolated event portfolios and enterprise privacy controls</span>
                </div>
              </div>
            </div>

            <div className="relative z-10 pt-6 border-t border-indigo-800/60 flex items-center justify-between text-[11px] text-indigo-300">
              <span>Cryptographically Secured Passwords</span>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
          </div>

          {/* Right Column: Registration Form */}
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
                New Organizer Registration
              </span>
              <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                Create your account
              </h1>
              <p className="text-xs text-slate-500 mt-1">
                Enter your details to create an account and access the event management SaaS suite.
              </p>
            </div>

            {error && (
              <div className="mb-4 p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-xs text-rose-700 animate-in fade-in">
                <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                <span className="font-medium">{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-3.5">
              {/* Full Name */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    type="text"
                    required
                    autoFocus
                    placeholder="e.g. Priya Sharma"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full pl-10 pr-3.5 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              {/* Email Address */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    type="email"
                    required
                    placeholder="organizer@eventify.ai"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10 pr-3.5 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
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
                    className="w-full pl-10 pr-10 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-2.5 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full pl-10 pr-10 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              {/* Password Strength Checklist */}
              {password && (
                <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-200/80 text-[11px] space-y-1">
                  <div className="flex items-center gap-1.5">
                    <span className={hasMinLength ? 'text-emerald-600 font-bold' : 'text-slate-400'}>
                      {hasMinLength ? '✓' : '•'} At least 6 characters
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={hasLetter && hasNumberOrSymbol ? 'text-emerald-600 font-bold' : 'text-slate-400'}>
                      {hasLetter && hasNumberOrSymbol ? '✓' : '•'} Letters and numbers/symbols
                    </span>
                  </div>
                  {confirmPassword && (
                    <div className="flex items-center gap-1.5">
                      <span className={passwordsMatch ? 'text-emerald-600 font-bold' : 'text-rose-500 font-bold'}>
                        {passwordsMatch ? '✓ Passwords match' : '✕ Passwords do not match'}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Terms and Conditions */}
              <div className="pt-1">
                <label className="flex items-start gap-2.5 text-xs text-slate-600 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={termsAccepted}
                    onChange={(e) => setTermsAccepted(e.target.checked)}
                    className="w-4 h-4 mt-0.5 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500 cursor-pointer"
                  />
                  <span>
                    I accept the{' '}
                    <span className="font-semibold text-indigo-600 hover:underline">Terms of Service</span>{' '}
                    and{' '}
                    <span className="font-semibold text-indigo-600 hover:underline">Privacy Policy</span>.
                  </span>
                </label>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 active:scale-[0.99] disabled:opacity-50 text-white font-bold text-xs sm:text-sm rounded-xl shadow-md shadow-indigo-600/20 transition-all flex items-center justify-center gap-2 cursor-pointer mt-3"
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Create Account</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 pt-4 border-t border-slate-100 text-center text-xs text-slate-500">
              Already have an account?{' '}
              <button
                type="button"
                onClick={onNavigateLogin}
                className="font-bold text-indigo-600 hover:text-indigo-800 transition-colors cursor-pointer ml-1"
              >
                Sign In
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

