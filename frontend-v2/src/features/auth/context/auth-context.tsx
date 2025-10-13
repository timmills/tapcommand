import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { authApi, tokenStorage } from '@/lib/api/auth';
import type { User } from '@/lib/api/users';

// Map database role names to simplified app roles
export type UserRole = 'viewer' | 'operator' | 'administrator' | 'superadmin';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  role: UserRole;
  hasRole: (requiredRole: UserRole) => boolean;
  isSuperuser: boolean;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [isAuthChecked, setIsAuthChecked] = useState(false);

  // Fetch current user if authenticated
  const { data: user, isLoading } = useQuery({
    queryKey: ['auth', 'currentUser'],
    queryFn: () => authApi.getCurrentUser(),
    enabled: tokenStorage.isAuthenticated() && isAuthChecked,
    retry: false,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  // Check auth status on mount
  useEffect(() => {
    setIsAuthChecked(true);
  }, []);

  // Determine user role based on roles array and is_superuser flag
  const getUserRole = (user: User | null): UserRole => {
    if (!user) return 'viewer';

    // Superusers are always superadmin
    if (user.is_superuser) return 'superadmin';

    // Check role names from database: Super Admin, Administrator, Operator, Viewer
    const roleNames = user.roles.map(r => r.name.toLowerCase());

    // Map database roles to app roles
    if (roleNames.includes('super admin') || roleNames.includes('superadmin')) {
      return 'superadmin';
    }

    if (roleNames.includes('administrator') || roleNames.includes('admin')) {
      return 'administrator';
    }

    if (roleNames.includes('operator')) {
      return 'operator';
    }

    return 'viewer';
  };

  const role = getUserRole(user || null);

  // Check if user has required role (or higher)
  const hasRole = (requiredRole: UserRole): boolean => {
    const roleHierarchy: Record<UserRole, number> = {
      viewer: 1,       // Can only view and control devices
      operator: 2,     // Can manage schedules and basic config
      administrator: 3, // Can manage IR libraries, controllers, advanced features
      superadmin: 4,   // Full access to everything
    };

    return roleHierarchy[role] >= roleHierarchy[requiredRole];
  };

  const login = () => {
    queryClient.invalidateQueries({ queryKey: ['auth', 'currentUser'] });
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      tokenStorage.clearTokens();
      queryClient.clear();
      window.location.href = '/login';
    }
  };

  const value: AuthContextType = {
    user: user || null,
    isLoading: !isAuthChecked || (tokenStorage.isAuthenticated() && isLoading),
    isAuthenticated: tokenStorage.isAuthenticated(),
    role,
    hasRole,
    isSuperuser: user?.is_superuser || false,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Helper component to restrict content by role
interface RestrictedProps {
  children: ReactNode;
  to: UserRole;
}

export function Restricted({ children, to }: RestrictedProps) {
  const { hasRole } = useAuth();

  if (!hasRole(to)) {
    return null;
  }

  return <>{children}</>;
}
