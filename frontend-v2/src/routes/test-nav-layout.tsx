import { Outlet } from 'react-router-dom';
import { HierarchicalNav } from '../features/nav-test/components/hierarchical-nav';

export const TestNavLayout = () => {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="flex min-h-screen">
        <HierarchicalNav />
        <main className="flex-1">
          <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/70 backdrop-blur">
            <div className="mx-auto max-w-6xl px-4 py-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">SmartVenue Control Center</h2>
                <p className="text-sm text-slate-500">
                  Testing new hierarchical navigation - manage IR controllers, discovery, and firmware generation.
                </p>
              </div>
            </div>
          </header>
          <div className="mx-auto max-w-6xl px-4 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
