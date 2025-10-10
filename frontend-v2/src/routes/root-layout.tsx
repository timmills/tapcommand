import { Outlet, useLocation } from 'react-router-dom';
import { HierarchicalNav } from '../components/hierarchical-nav';

export const RootLayout = () => {
  const location = useLocation();

  // Queue diagnostics needs full width for the wide table
  const isFullWidth = location.pathname === '/queue-diagnostics';

  // Control page is full-screen with no chrome
  const isControlPage = location.pathname === '/control';

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
                <h2 className="text-xl font-semibold text-slate-900">SmartVenue control center</h2>
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
