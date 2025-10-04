import { useEffect, useState } from 'react';
import type { User } from '@/lib/api/users';
import { useCreateUser, useUpdateUser, useAssignRole, useRemoveRole, useResetPassword } from '../hooks/use-users';

interface UserEditModalProps {
  user?: User | null;
  open: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

// Mock roles - these would come from a roles API in production
const AVAILABLE_ROLES = [
  { id: 1, name: 'Super Admin', description: 'Full system access' },
  { id: 2, name: 'Administrator', description: 'Administrative access' },
  { id: 3, name: 'Operator', description: 'Operational access' },
  { id: 4, name: 'Viewer', description: 'Read-only access' },
];

export const UserEditModal = ({ user, open, onClose, onSaved }: UserEditModalProps) => {
  const isEditing = !!user;

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [isSuperuser, setIsSuperuser] = useState(false);
  const [mustChangePassword, setMustChangePassword] = useState(true);
  const [selectedRoles, setSelectedRoles] = useState<number[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const createUser = useCreateUser();
  const updateUser = useUpdateUser();
  const assignRole = useAssignRole();
  const removeRole = useRemoveRole();
  const resetPassword = useResetPassword();

  useEffect(() => {
    if (!open) return;

    if (user) {
      setUsername(user.username);
      setEmail(user.email);
      setFullName(user.full_name ?? '');
      setIsActive(user.is_active);
      setIsSuperuser(user.is_superuser);
      setMustChangePassword(user.must_change_password);
      setSelectedRoles(user.roles.map((r) => r.id));
      setPassword('');
      setConfirmPassword('');
    } else {
      setUsername('');
      setEmail('');
      setFullName('');
      setPassword('');
      setConfirmPassword('');
      setIsActive(true);
      setIsSuperuser(false);
      setMustChangePassword(true);
      setSelectedRoles([]);
    }
    setErrorMessage(null);
  }, [user, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    // Validation
    if (!isEditing) {
      if (!username || !email || !password) {
        setErrorMessage('Username, email, and password are required');
        return;
      }
      if (password !== confirmPassword) {
        setErrorMessage('Passwords do not match');
        return;
      }
      if (password.length < 8) {
        setErrorMessage('Password must be at least 8 characters');
        return;
      }
    } else {
      if (!email) {
        setErrorMessage('Email is required');
        return;
      }
    }

    try {
      if (isEditing) {
        // Update existing user
        const updatedUser = await updateUser.mutateAsync({
          userId: user.id,
          data: {
            email,
            full_name: fullName || undefined,
            is_active: isActive,
            is_superuser: isSuperuser,
          },
        });

        // Update roles
        const currentRoleIds = user.roles.map((r) => r.id);
        const rolesToAdd = selectedRoles.filter((id) => !currentRoleIds.includes(id));
        const rolesToRemove = currentRoleIds.filter((id) => !selectedRoles.includes(id));

        for (const roleId of rolesToAdd) {
          await assignRole.mutateAsync({ userId: user.id, roleId });
        }

        for (const roleId of rolesToRemove) {
          await removeRole.mutateAsync({ userId: user.id, roleId });
        }

        // Reset password if provided
        if (password) {
          if (password !== confirmPassword) {
            setErrorMessage('Passwords do not match');
            return;
          }
          if (password.length < 8) {
            setErrorMessage('Password must be at least 8 characters');
            return;
          }
          await resetPassword.mutateAsync({
            userId: user.id,
            data: {
              new_password: password,
              must_change_password: mustChangePassword,
            },
          });
        }
      } else {
        // Create new user
        await createUser.mutateAsync({
          username,
          email,
          password,
          full_name: fullName || undefined,
          is_superuser: isSuperuser,
          must_change_password: mustChangePassword,
          role_ids: selectedRoles,
        });
      }

      onSaved?.();
      onClose();
    } catch (error: any) {
      setErrorMessage(error?.response?.data?.detail || 'Failed to save user');
    }
  };

  const toggleRole = (roleId: number) => {
    setSelectedRoles((prev) =>
      prev.includes(roleId) ? prev.filter((id) => id !== roleId) : [...prev, roleId]
    );
  };

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-slate-900">
          {isEditing ? 'Edit User' : 'Create New User'}
        </h3>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {/* Username (only for new users) */}
          {!isEditing && (
            <div>
              <label className="block text-sm font-medium text-slate-700">
                Username <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder="johndoe"
              />
            </div>
          )}

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Email <span className="text-rose-500">*</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="john.doe@example.com"
            />
          </div>

          {/* Full Name */}
          <div>
            <label className="block text-sm font-medium text-slate-700">Full Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="John Doe"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-medium text-slate-700">
              {isEditing ? 'New Password (leave blank to keep current)' : 'Password'}{' '}
              {!isEditing && <span className="text-rose-500">*</span>}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                // Auto-uncheck "must change password" when user sets a new password
                if (e.target.value) {
                  setMustChangePassword(false);
                }
              }}
              required={!isEditing}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="••••••••"
            />
            {password && password.length < 8 && (
              <p className="mt-1 text-xs text-rose-600">Password must be at least 8 characters</p>
            )}
          </div>

          {/* Confirm Password */}
          {password && (
            <div>
              <label className="block text-sm font-medium text-slate-700">Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder="••••••••"
              />
              {confirmPassword && password !== confirmPassword && (
                <p className="mt-1 text-xs text-rose-600">Passwords do not match</p>
              )}
            </div>
          )}

          {/* Roles */}
          <div>
            <label className="block text-sm font-medium text-slate-700">Roles</label>
            <div className="mt-2 space-y-2">
              {AVAILABLE_ROLES.map((role) => (
                <label key={role.id} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={selectedRoles.includes(role.id)}
                    onChange={() => toggleRole(role.id)}
                    className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  />
                  <span className="ml-2 text-sm text-slate-700">
                    {role.name}
                    <span className="ml-2 text-xs text-slate-500">({role.description})</span>
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Active */}
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              />
              <span className="ml-2 text-sm font-medium text-slate-700">Active</span>
              <span className="ml-2 text-xs text-slate-500">(User can log in and access the system)</span>
            </label>
          </div>

          {/* Superuser */}
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={isSuperuser}
                onChange={(e) => setIsSuperuser(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              />
              <span className="ml-2 text-sm font-medium text-slate-700">Superuser</span>
              <span className="ml-2 text-xs text-slate-500">(Full administrative access)</span>
            </label>
          </div>

          {/* Must Change Password */}
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={mustChangePassword}
                onChange={(e) => setMustChangePassword(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              />
              <span className="ml-2 text-sm font-medium text-slate-700">Must change password on next login</span>
            </label>
          </div>

          {/* Error Message */}
          {errorMessage && (
            <div className="rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createUser.isPending || updateUser.isPending}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-brand-300"
            >
              {createUser.isPending || updateUser.isPending
                ? isEditing
                  ? 'Saving…'
                  : 'Creating…'
                : isEditing
                  ? 'Save Changes'
                  : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
