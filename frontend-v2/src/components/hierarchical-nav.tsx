import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  ChevronDown,
  ChevronRight,
  LayoutDashboard,
  Radio,
  Wifi,
  Zap,
  Settings,
  Users,
  Activity,
} from 'lucide-react';

interface NavItem {
  label: string;
  to: string;
  badge?: number;
}

interface NavGroup {
  label: string;
  icon: React.ElementType;
  defaultOpen?: boolean;
  items: NavItem[];
  restricted?: boolean; // For role-based access control
}

const navigationGroups: NavGroup[] = [
  {
    label: 'Dashboard',
    icon: LayoutDashboard,
    defaultOpen: true,
    items: [
      { label: 'Control', to: '/control' },
      { label: 'Connected Devices', to: '/connected-devices' },
    ],
  },
  {
    label: 'Controllers',
    icon: Radio,
    defaultOpen: true,
    items: [
      { label: 'IR Controllers', to: '/controllers' },
      { label: 'TV Controllers', to: '/network-controllers' },
      { label: 'Audio Controllers', to: '/audio' },
    ],
  },
  {
    label: 'Discovery & Setup',
    icon: Wifi,
    defaultOpen: false,
    items: [
      { label: 'Discovery', to: '/discovery' },
    ],
  },
  {
    label: 'Infrared (IR)',
    icon: Zap,
    defaultOpen: false,
    items: [
      { label: 'IR Libraries', to: '/ir-libraries' },
      { label: 'IR Capture', to: '/ir-capture' },
      { label: 'IR Commands', to: '/ir-commands' },
      { label: 'IR Builder', to: '/templates' },
    ],
  },
  {
    label: 'Configuration',
    icon: Settings,
    defaultOpen: false,
    items: [
      { label: 'Schedules', to: '/schedules' },
      { label: 'Tags', to: '/tags' },
      { label: 'Channels', to: '/settings' },
    ],
  },
  {
    label: 'Administration',
    icon: Users,
    defaultOpen: false,
    restricted: true, // Could be hidden based on user role
    items: [
      { label: 'Users', to: '/users' },
      { label: 'Backups', to: '/backups' },
    ],
  },
  {
    label: 'Advanced',
    icon: Activity,
    defaultOpen: false,
    items: [
      { label: 'Queue Diagnostics', to: '/queue-diagnostics' },
      { label: 'Documentation', to: '/documentation' },
    ],
  },
];

export const HierarchicalNav = () => {
  const [openGroups, setOpenGroups] = useState<Set<string>>(
    new Set(navigationGroups.filter(g => g.defaultOpen).map(g => g.label))
  );

  const toggleGroup = (label: string) => {
    setOpenGroups(prev => {
      const next = new Set(prev);
      if (next.has(label)) {
        next.delete(label);
      } else {
        next.add(label);
      }
      return next;
    });
  };

  return (
    <aside className="w-64 flex-shrink-0 border-r border-slate-200 bg-white">
      <div className="px-6 py-4">
        <h1 className="text-lg font-semibold text-brand-600">SmartVenue</h1>
        <p className="mt-1 text-sm text-slate-500">Device management</p>
      </div>

      <nav className="mt-2 px-2 pb-4">
        {navigationGroups.map((group) => {
          const isOpen = openGroups.has(group.label);
          const Icon = group.icon;

          return (
            <div key={group.label} className="mb-1">
              <button
                onClick={() => toggleGroup(group.label)}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100"
              >
                <Icon className="h-4 w-4 flex-shrink-0 text-slate-500" />
                <span className="flex-1 text-left">{group.label}</span>
                {group.restricted && (
                  <span className="text-xs text-slate-400">🔒</span>
                )}
                {isOpen ? (
                  <ChevronDown className="h-4 w-4 text-slate-400" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-slate-400" />
                )}
              </button>

              {isOpen && (
                <div className="ml-6 mt-1 space-y-1 border-l-2 border-slate-100 pl-2">
                  {group.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={({ isActive }) =>
                        `flex items-center justify-between rounded-md px-3 py-1.5 text-sm transition-colors ${
                          isActive
                            ? 'bg-brand-50 font-medium text-brand-600'
                            : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                        }`
                      }
                    >
                      {item.label}
                      {item.badge && (
                        <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-600">
                          {item.badge}
                        </span>
                      )}
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      <div className="border-t border-slate-200 px-4 py-3">
        <div className="text-xs text-slate-500">
          <kbd className="rounded border border-slate-300 bg-slate-50 px-1.5 py-0.5 font-mono">
            ⌘K
          </kbd>{' '}
          Quick search
        </div>
      </div>
    </aside>
  );
};
