import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Tv2, Lock, User, Loader2, Sparkles } from 'lucide-react';
import { authApi, tokenStorage } from '@/lib/api/auth';

export const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const response = await authApi.login({ username, password });
      tokenStorage.setTokens(response.access_token, response.refresh_token);

      // Redirect to home page after successful login
      navigate('/');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to login. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left Side - Branding & Info */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-brand-600 via-brand-700 to-brand-900 p-12 flex-col justify-between relative overflow-hidden">
        {/* Decorative background elements */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-brand-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-brand-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" style={{ animationDelay: '1s' }}></div>

        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-8">
            <div className="rounded-xl bg-white/10 backdrop-blur-sm p-3">
              <Tv2 className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-white">SmartVenue</h1>
          </div>

          <div className="space-y-6 text-white/90">
            <div>
              <h2 className="text-4xl font-bold leading-tight mb-4">
                Commercial Hospitality<br />Display Management
              </h2>
              <p className="text-lg text-white/80">
                Centralized control for your venue's entertainment systems
              </p>
            </div>

            <div className="space-y-4 pt-6">
              <div className="flex items-start gap-3">
                <div className="rounded-lg bg-white/10 backdrop-blur-sm p-2 mt-1">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Unified Control</h3>
                  <p className="text-sm text-white/70">Manage all displays from a single interface</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="rounded-lg bg-white/10 backdrop-blur-sm p-2 mt-1">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Automated Scheduling</h3>
                  <p className="text-sm text-white/70">Set up templates and schedules for hands-free operation</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="rounded-lg bg-white/10 backdrop-blur-sm p-2 mt-1">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Role-Based Access</h3>
                  <p className="text-sm text-white/70">Secure permissions for staff and administrators</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="relative z-10 text-white/60 text-sm">
          <p>© 2025 SmartVenue. All rights reserved.</p>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="flex-1 flex items-center justify-center bg-white px-4 py-12 sm:px-6 lg:px-8">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-8">
            <div className="rounded-xl bg-brand-100 p-3">
              <Tv2 className="h-8 w-8 text-brand-600" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900">SmartVenue</h1>
          </div>

          <div className="space-y-8">
            <div className="text-center lg:text-left">
              <h2 className="text-3xl font-bold text-slate-900">Welcome back</h2>
              <p className="mt-2 text-sm text-slate-600">
                Sign in to access your venue management dashboard
              </p>
            </div>

            <form className="space-y-6" onSubmit={handleSubmit}>
              <div className="space-y-4">
                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-slate-700 mb-2">
                    Username
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-slate-400" />
                    </div>
                    <input
                      id="username"
                      name="username"
                      type="text"
                      autoComplete="username"
                      required
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="block w-full pl-10 pr-3 py-2.5 border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 transition"
                      placeholder="Enter your username"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-2">
                    Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Lock className="h-5 w-5 text-slate-400" />
                    </div>
                    <input
                      id="password"
                      name="password"
                      type="password"
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="block w-full pl-10 pr-3 py-2.5 border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 transition"
                      placeholder="Enter your password"
                    />
                  </div>
                </div>
              </div>

              {error && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 p-4">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-0.5">
                      <svg className="h-5 w-5 text-rose-500" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-rose-800">{error}</p>
                    </div>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-brand-300 transition"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Signing in…
                  </>
                ) : (
                  'Sign in'
                )}
              </button>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-200"></div>
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-white px-3 text-slate-500">Default credentials</span>
                </div>
              </div>

              <div className="rounded-lg bg-slate-50 border border-slate-200 p-4 text-center">
                <p className="text-sm text-slate-600">
                  <span className="font-medium">Username:</span> admin
                  <span className="mx-2 text-slate-400">|</span>
                  <span className="font-medium">Password:</span> admin
                </p>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
