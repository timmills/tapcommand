import { useManagedDevices } from '@/features/devices/hooks/use-managed-devices';
import { PlayCircle, Radio, Tv, Volume2, Calendar, Zap, HelpCircle, Users, Shield } from 'lucide-react';
import { useAuth } from '@/features/auth/context/auth-context';

export const OverviewPage = () => {
  const { data: devices } = useManagedDevices();
  const { hasRole } = useAuth();

  // Calculate stats
  const irControllers = devices?.filter(d => !d.hostname.startsWith('nw-')) || [];
  const tvControllers = devices?.filter(d => d.hostname.startsWith('nw-')) || [];
  const totalPorts = irControllers.reduce((acc, d) => acc + d.ir_ports.filter(p => p.is_active).length, 0);

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="rounded-lg bg-gradient-to-r from-brand-600 to-brand-700 p-8 text-white">
        <h1 className="text-3xl font-bold">Welcome to TapCommand</h1>
        <p className="mt-2 text-lg text-brand-100">
          Control your venue's entertainment systems from anywhere
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-100 p-3">
              <Radio className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">IR Controllers</p>
              <p className="text-2xl font-semibold text-slate-900">{irControllers.length}</p>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-purple-100 p-3">
              <Tv className="h-6 w-6 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">TV Controllers</p>
              <p className="text-2xl font-semibold text-slate-900">{tvControllers.length}</p>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-emerald-100 p-3">
              <Zap className="h-6 w-6 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Active IR Ports</p>
              <p className="text-2xl font-semibold text-slate-900">{totalPorts}</p>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-amber-100 p-3">
              <Volume2 className="h-6 w-6 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Audio Zones</p>
              <p className="text-2xl font-semibold text-slate-900">0</p>
            </div>
          </div>
        </div>
      </div>

      {/* How It Works - For All Users */}
      <div className="rounded-lg border border-slate-200 bg-white p-8">
        <h2 className="text-xl font-semibold text-slate-900">How TapCommand Works</h2>
        <p className="mt-2 text-sm text-slate-600">
          A simple guide to controlling your venue's entertainment systems
        </p>

        <div className="mt-6 grid gap-6 md:grid-cols-3">
          <div className="space-y-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-100 text-xl font-bold text-brand-600">
              1
            </div>
            <h3 className="font-semibold text-slate-900">Find Your Device</h3>
            <p className="text-sm text-slate-600">
              Navigate to <strong>Connected Devices</strong> to see all TVs, set-top boxes, and audio equipment in your venue.
            </p>
          </div>

          <div className="space-y-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-100 text-xl font-bold text-brand-600">
              2
            </div>
            <h3 className="font-semibold text-slate-900">Send Commands</h3>
            <p className="text-sm text-slate-600">
              Use the <strong>Control</strong> page to change channels, adjust volume, or power devices on/off. Commands are sent instantly.
            </p>
          </div>

          <div className="space-y-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-100 text-xl font-bold text-brand-600">
              3
            </div>
            <h3 className="font-semibold text-slate-900">Automate</h3>
            <p className="text-sm text-slate-600">
              Set up <strong>Schedules</strong> to automatically change channels at specific times (e.g., sports events, news).
            </p>
          </div>
        </div>
      </div>

      {/* Quick Actions - For All Users */}
      <div className="rounded-lg border border-slate-200 bg-white p-8">
        <h2 className="text-xl font-semibold text-slate-900">Quick Actions</h2>
        <p className="mt-2 text-sm text-slate-600">Common tasks to get started</p>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <a
            href="/control"
            className="flex items-center gap-4 rounded-lg border border-slate-200 p-4 transition-colors hover:border-brand-300 hover:bg-brand-50"
          >
            <div className="rounded-lg bg-brand-100 p-3">
              <PlayCircle className="h-6 w-6 text-brand-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-slate-900">Control Devices</h3>
              <p className="text-sm text-slate-500">Change channels, volume, or power</p>
            </div>
          </a>

          <a
            href="/schedules"
            className="flex items-center gap-4 rounded-lg border border-slate-200 p-4 transition-colors hover:border-brand-300 hover:bg-brand-50"
          >
            <div className="rounded-lg bg-purple-100 p-3">
              <Calendar className="h-6 w-6 text-purple-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-slate-900">Manage Schedules</h3>
              <p className="text-sm text-slate-500">Set up automated channel changes</p>
            </div>
          </a>

          <a
            href="/connected-devices"
            className="flex items-center gap-4 rounded-lg border border-slate-200 p-4 transition-colors hover:border-brand-300 hover:bg-brand-50"
          >
            <div className="rounded-lg bg-emerald-100 p-3">
              <Tv className="h-6 w-6 text-emerald-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-slate-900">View All Devices</h3>
              <p className="text-sm text-slate-500">See all connected equipment</p>
            </div>
          </a>

          <a
            href="/documentation"
            className="flex items-center gap-4 rounded-lg border border-slate-200 p-4 transition-colors hover:border-brand-300 hover:bg-brand-50"
          >
            <div className="rounded-lg bg-amber-100 p-3">
              <HelpCircle className="h-6 w-6 text-amber-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-slate-900">Documentation</h3>
              <p className="text-sm text-slate-500">Learn more about the system</p>
            </div>
          </a>
        </div>
      </div>

      {/* Operator+ Sections */}
      {hasRole('operator') && (
        <>
          {/* System Architecture - Operator+ */}
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-8">
            <div className="flex items-start gap-3">
              <div className="rounded-lg bg-blue-600 px-2 py-1 text-xs font-semibold text-white">
                OPERATOR+
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-semibold text-blue-900">System Architecture</h2>
                <p className="mt-2 text-sm text-blue-700">
                  Understanding how TapCommand components work together
                </p>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div className="rounded-lg bg-white p-4">
                <h3 className="font-semibold text-slate-900">IR Controllers (Hardware)</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Physical devices (ESP8266/ESP32) installed in your venue. Each controller has multiple IR transmitters
                  that send infrared signals to TVs, set-top boxes, and other equipment. They connect to your network
                  via WiFi and receive commands from this web interface.
                </p>
              </div>

              <div className="rounded-lg bg-white p-4">
                <h3 className="font-semibold text-slate-900">Virtual Devices</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Each physical device (TV, STB, etc.) is represented as a "virtual device" in the system. Virtual devices
                  know which IR controller port they're connected to and what commands they support. When you send a command,
                  it's routed to the correct controller and IR port.
                </p>
              </div>

              <div className="rounded-lg bg-white p-4">
                <h3 className="font-semibold text-slate-900">Command Flow</h3>
                <p className="mt-2 text-sm text-slate-600">
                  <strong>Web Interface → Backend Server → IR Controller → IR Signal → Device</strong>
                  <br />
                  Commands are sent via HTTP/MQTT to the backend, queued for delivery, and forwarded to the appropriate
                  IR controller which transmits the infrared signal.
                </p>
              </div>

              <div className="rounded-lg bg-white p-4">
                <h3 className="font-semibold text-slate-900">Network Controllers</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Some TVs (Samsung, LG) can be controlled over the network without IR. These use IP-based protocols
                  and don't require physical IR controllers.
                </p>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Administrator+ Technical Details */}
      {hasRole('administrator') && (
        <>
          {/* Technical Configuration - Administrator+ */}
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-8">
            <div className="flex items-start gap-3">
              <div className="rounded-lg bg-rose-600 px-2 py-1 text-xs font-semibold text-white">
                ADMINISTRATOR+
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-semibold text-rose-900">Technical Details</h2>
                <p className="mt-2 text-sm text-rose-700">
                  Advanced configuration and troubleshooting information
                </p>
              </div>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-lg bg-white p-4">
                <h3 className="font-semibold text-slate-900">IR Libraries</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Collections of infrared command codes for different device brands/models. Commands are stored as
                  timing patterns (Pronto hex format) or protocol definitions.
                </p>
                <a href="/ir-libraries" className="mt-2 inline-block text-sm font-medium text-brand-600 hover:text-brand-700">
                  Manage IR Libraries →
                </a>
              </div>

              <div className="rounded-lg bg-white p-4">
                <h3 className="font-semibold text-slate-900">IR Capture</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Use an IR receiver to capture commands from existing remotes. This is useful for adding support
                  for new devices or troubleshooting signal issues.
                </p>
                <a href="/ir-capture" className="mt-2 inline-block text-sm font-medium text-brand-600 hover:text-brand-700">
                  Open IR Capture →
                </a>
              </div>

              <div className="rounded-lg bg-white p-4">
                <h3 className="font-semibold text-slate-900">Discovery</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Automatically detect IR controllers on your network. Controllers broadcast mDNS announcements
                  which are picked up by the discovery system.
                </p>
                <a href="/discovery" className="mt-2 inline-block text-sm font-medium text-brand-600 hover:text-brand-700">
                  Run Discovery →
                </a>
              </div>

              <div className="rounded-lg bg-white p-4">
                <h3 className="font-semibold text-slate-900">Queue Diagnostics</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Monitor the command queue to troubleshoot delivery issues. See pending commands, failed deliveries,
                  and retry attempts in real-time.
                </p>
                <a href="/queue-diagnostics" className="mt-2 inline-block text-sm font-medium text-brand-600 hover:text-brand-700">
                  View Queue →
                </a>
              </div>

              <div className="rounded-lg bg-white p-4">
                <h3 className="font-semibold text-slate-900">Firmware Updates</h3>
                <p className="mt-2 text-sm text-slate-600">
                  IR controllers run ESPHome firmware. Generate custom firmware configs with device-specific
                  IR codes and deploy OTA (Over-The-Air) updates.
                </p>
                <a href="/controllers" className="mt-2 inline-block text-sm font-medium text-brand-600 hover:text-brand-700">
                  Manage Controllers →
                </a>
              </div>

              <div className="rounded-lg bg-white p-4">
                <h3 className="font-semibold text-slate-900">Database Backups</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Automated backups of all configuration data including devices, IR codes, schedules, and user settings.
                  Restore from backup if needed.
                </p>
                <a href="/backups" className="mt-2 inline-block text-sm font-medium text-brand-600 hover:text-brand-700">
                  Manage Backups →
                </a>
              </div>
            </div>
          </div>

          {/* User Management - Administrator+ */}
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-8">
            <div className="flex items-start gap-3">
              <div className="rounded-lg bg-rose-600 px-2 py-1 text-xs font-semibold text-white">
                ADMINISTRATOR+
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-semibold text-rose-900">User Management</h2>
                <p className="mt-2 text-sm text-rose-700">
                  Managing users, roles, and permissions in TapCommand
                </p>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div className="rounded-lg bg-white p-4">
                <div className="flex items-center gap-3">
                  <Users className="h-5 w-5 text-brand-600" />
                  <h3 className="font-semibold text-slate-900">Creating Users</h3>
                </div>
                <p className="mt-2 text-sm text-slate-600">
                  Navigate to <strong>Users</strong> in the sidebar and click <strong>Create User</strong>. You'll need to provide:
                </p>
                <ul className="mt-2 space-y-1 text-sm text-slate-600">
                  <li>• <strong>Username:</strong> Unique identifier for login (cannot be changed later)</li>
                  <li>• <strong>Email:</strong> User's email address</li>
                  <li>• <strong>Password:</strong> Must be at least 8 characters</li>
                  <li>• <strong>Full Name:</strong> Optional display name</li>
                </ul>
                <p className="mt-2 text-sm text-slate-600">
                  By default, new users are marked to change their password on first login for security.
                </p>
              </div>

              <div className="rounded-lg bg-white p-4">
                <div className="flex items-center gap-3">
                  <Shield className="h-5 w-5 text-brand-600" />
                  <h3 className="font-semibold text-slate-900">Roles & Permissions</h3>
                </div>
                <p className="mt-2 text-sm text-slate-600">
                  TapCommand uses role-based access control with four system roles:
                </p>
                <div className="mt-3 space-y-2">
                  <div className="flex items-start gap-2">
                    <div className="mt-0.5 h-2 w-2 rounded-full bg-red-500"></div>
                    <div>
                      <strong className="text-sm text-slate-900">Super Admin</strong>
                      <p className="text-sm text-slate-600">Full system access including user management, system settings, and all features</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="mt-0.5 h-2 w-2 rounded-full bg-orange-500"></div>
                    <div>
                      <strong className="text-sm text-slate-900">Administrator</strong>
                      <p className="text-sm text-slate-600">Can manage devices, IR libraries, schedules, and view technical details</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="mt-0.5 h-2 w-2 rounded-full bg-blue-500"></div>
                    <div>
                      <strong className="text-sm text-slate-900">Operator</strong>
                      <p className="text-sm text-slate-600">Can control devices, manage schedules, and view system architecture</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="mt-0.5 h-2 w-2 rounded-full bg-green-500"></div>
                    <div>
                      <strong className="text-sm text-slate-900">Viewer</strong>
                      <p className="text-sm text-slate-600">Read-only access to view devices and schedules</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-lg bg-white p-4">
                <h3 className="font-semibold text-slate-900">Assigning Roles</h3>
                <p className="mt-2 text-sm text-slate-600">
                  When creating or editing a user, select one or more roles to grant permissions. Users can have multiple
                  roles, and their effective permissions are the union of all assigned roles. For administrators, assign the
                  <strong> Super Admin</strong> role.
                </p>
              </div>

              <div className="rounded-lg bg-white p-4">
                <h3 className="font-semibold text-slate-900">Custom Roles</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Switch to the <strong>Roles & Permissions</strong> tab on the Users page to create custom roles with
                  specific permissions. This allows fine-grained access control for specialized workflows.
                </p>
              </div>

              <div className="rounded-lg bg-white p-4">
                <h3 className="font-semibold text-slate-900">Password Recovery</h3>
                <p className="mt-2 text-sm text-slate-600">
                  If a user is locked out, administrators can reset their password from the user edit modal. For emergency
                  access recovery, system administrators can use the command-line password reset tool:
                </p>
                <pre className="mt-2 rounded bg-slate-900 px-3 py-2 text-xs text-slate-100">./reset-password.sh username</pre>
                <p className="mt-2 text-sm text-slate-600">
                  See <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">PASSWORD_RECOVERY.md</code> for details.
                </p>
              </div>
            </div>
          </div>

          {/* Troubleshooting Tips */}
          <div className="rounded-lg border border-slate-200 bg-white p-8">
            <h2 className="text-xl font-semibold text-slate-900">Troubleshooting</h2>
            <p className="mt-2 text-sm text-slate-600">Common issues and solutions</p>

            <div className="mt-6 space-y-4">
              <div className="rounded-lg border border-slate-200 p-4">
                <h3 className="font-semibold text-slate-900">Device not responding to commands</h3>
                <ul className="mt-2 space-y-1 text-sm text-slate-600">
                  <li>• Check that the IR controller is online (Connected Devices page)</li>
                  <li>• Verify the IR emitter is pointed at the device</li>
                  <li>• Ensure the correct IR library is assigned to the device</li>
                  <li>• Check Queue Diagnostics for failed delivery attempts</li>
                </ul>
              </div>

              <div className="rounded-lg border border-slate-200 p-4">
                <h3 className="font-semibold text-slate-900">IR controller offline</h3>
                <ul className="mt-2 space-y-1 text-sm text-slate-600">
                  <li>• Check WiFi connection and network connectivity</li>
                  <li>• Verify power supply to the controller</li>
                  <li>• Run Discovery to detect if it's reconnected</li>
                  <li>• Check controller logs in Queue Diagnostics</li>
                </ul>
              </div>

              <div className="rounded-lg border border-slate-200 p-4">
                <h3 className="font-semibold text-slate-900">Schedule not triggering</h3>
                <ul className="mt-2 space-y-1 text-sm text-slate-600">
                  <li>• Verify schedule is enabled in Schedules page</li>
                  <li>• Check timezone settings match your location</li>
                  <li>• Ensure target device is online</li>
                  <li>• Review schedule cron expression syntax</li>
                </ul>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Need Help? - For All Users */}
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-8">
        <h2 className="text-xl font-semibold text-slate-900">Need Help?</h2>
        <p className="mt-2 text-sm text-slate-600">
          Check out the <a href="/documentation" className="font-medium text-brand-600 hover:text-brand-700">documentation</a> for
          detailed guides, or contact your system administrator for assistance.
        </p>
      </div>
    </div>
  );
};
