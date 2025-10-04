import { createBrowserRouter, Navigate } from 'react-router-dom';

import { RootLayout } from '../routes/root-layout';
import { ControllersPage } from '../features/devices/pages/controllers-page';
import { ConnectedDevicesPage } from '../features/devices/pages/connected-devices-page';
import { DiscoveryPage } from '../features/discovery/pages/discovery-page';
import { TemplatesPage } from '../features/templates/pages/templates-page';
import { SettingsPage } from '../features/settings/pages/settings-page';
import { TagsPage } from '../features/settings/pages/tags-page';
import { IRCommandsPage } from '../features/ir/IRCommandsPage';
import { IRLibrariesPage } from '../features/ir/IRLibrariesPage';
import { IRCapturePage } from '../features/ir-capture/pages/IRCapturePage';
import { ControlPage } from '../features/control/pages/control-page';
import { ControlLayout } from '../features/control/pages/control-layout';
import { SchedulesPage } from '../features/scheduling/pages/schedules-page';
import { QueueDiagnosticsPage } from '../features/diagnostics/pages/queue-diagnostics-page';
import { UsersPage } from '../features/users/pages/users-page';
import { LoginPage } from '../features/auth/pages/login-page';
import { NetworkControllersPage } from '../features/network-controllers/pages/network-controllers-page';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    children: [
      { index: true, element: <Navigate to="controllers" replace /> },
      { path: 'controllers', element: <ControllersPage /> },
      { path: 'network-controllers', element: <NetworkControllersPage /> },
      { path: 'connected-devices', element: <ConnectedDevicesPage /> },
      { path: 'devices', element: <Navigate to="../controllers" replace /> },
      { path: 'discovery', element: <DiscoveryPage /> },
      { path: 'ir-libraries', element: <IRLibrariesPage /> },
      { path: 'ir-capture', element: <IRCapturePage /> },
      { path: 'templates', element: <TemplatesPage /> },
      { path: 'ir-commands', element: <IRCommandsPage /> },
      { path: 'schedules', element: <SchedulesPage /> },
      { path: 'tags', element: <TagsPage /> },
      { path: 'queue-diagnostics', element: <QueueDiagnosticsPage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'users', element: <UsersPage /> },
    ],
  },
  {
    path: '/control',
    element: <ControlLayout />,
    children: [{ index: true, element: <ControlPage /> }],
  },
  { path: '/login', element: <LoginPage /> },
  { path: '*', element: <Navigate to="/" replace /> },
]);
