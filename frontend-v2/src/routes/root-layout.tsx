import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useMemo } from 'react';

const navigation = [
  { label: 'Control', to: '/control' },
  { label: 'IR Controllers', to: '/controllers' },
  { label: 'Connected Devices', to: '/connected-devices' },
  { label: 'Discovery', to: '/discovery' },
  { label: 'IR Libraries', to: '/ir-libraries' },
  { label: 'IR Capture', to: '/ir-capture' },
  { label: 'IR Commands', to: '/ir-commands' },
  { label: 'Templates', to: '/templates' },
  { label: 'Schedules', to: '/schedules' },
  { label: 'Queue Diagnostics', to: '/queue-diagnostics' },
  { label: 'Tags', to: '/tags' },
  { label: 'Channels', to: '/settings' },
  { label: 'Users', to: '/users' },
];

export const RootLayout = () => {
  const navItems = useMemo(() => navigation, []);
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
        <aside className="hidden w-64 flex-shrink-0 border-r border-slate-200 bg-white/80 backdrop-blur md:block">
          <div className="px-6 py-4">
            <h1 className="text-lg font-semibold text-brand-600">SmartVenue</h1>
            <p className="mt-1 text-sm text-slate-500">Device management portal</p>
          </div>
          <nav className="mt-6 flex flex-col gap-1 px-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-50 text-brand-600'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>
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
