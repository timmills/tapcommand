import { Outlet, useLocation, Navigate } from 'react-router-dom';
import { HierarchicalNav } from '../components/hierarchical-nav';
import { useAuth } from '../features/auth/context/auth-context';

export const RootLayout = () => {
  const location = useLocation();
  const { isAuthenticated, isLoading } = useAuth();

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-rose-600 border-r-transparent"></div>
          <p className="mt-4 text-sm text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Queue diagnostics needs full width for the wide table
  const isFullWidth = location.pathname === '/queue-diagnostics';

  // Control pages are full-screen with no chrome
  const isControlPage = location.pathname === '/control-tv' || location.pathname === '/control-tv-old';

  if (isControlPage) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <div className="mx-auto max-w-7xl px-4 py-6">
          <Outlet />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="flex min-h-screen">
        <HierarchicalNav />
        <main className="flex-1">
          <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/70 backdrop-blur">
            <div className={`mx-auto flex items-center justify-between px-4 py-4 ${isFullWidth ? '' : 'max-w-6xl'}`}>
              <div>
                <h2 className="text-xl font-semibold text-slate-900">TapCommand control center</h2>
                <p className="text-sm text-slate-500">Manage IR controllers, discovery, and firmware generation from anywhere.</p>
              </div>
            </div>
          </header>
          <div className={`mx-auto px-4 py-6 ${isFullWidth ? '' : 'max-w-6xl'}`}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
