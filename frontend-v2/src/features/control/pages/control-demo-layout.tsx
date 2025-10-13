import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../auth/context/auth-context';

export const ControlDemoLayout = () => {
  const location = useLocation();
  const { isAuthenticated, isLoading } = useAuth();

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-900">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-rose-600 border-r-transparent"></div>
          <p className="mt-4 text-sm text-slate-300">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Just render the outlet with no wrapper - the demo page handles its own styling
  return <Outlet />;
};
