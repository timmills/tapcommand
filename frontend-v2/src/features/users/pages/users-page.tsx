import { useState, useMemo } from 'react';
import { Users as UsersIcon, Shield } from 'lucide-react';
import { useUsers, useDeleteUser } from '../hooks/use-users';
import { useRoles, useDeleteRole } from '../hooks/use-roles';
import { UsersTable } from '../components/users-table';
import { UserEditModal } from '../components/user-edit-modal';
import { RolesTable } from '../components/roles-table';
import { RoleEditModal } from '../components/role-edit-modal';
import type { User, Role } from '@/lib/api/users';

type TabType = 'users' | 'roles';

export const UsersPage = () => {
  const [activeTab, setActiveTab] = useState<TabType>('users');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined);

  // Users data
  const { data, isLoading, isError, error, refetch, isFetching } = useUsers({ q: searchQuery || undefined, is_active: activeFilter });
  const deleteUser = useDeleteUser();

  // Roles data
  const { data: rolesData, isLoading: rolesLoading, isError: rolesError, error: rolesErrorMsg, refetch: refetchRoles, isFetching: rolesFetching } = useRoles();
  const deleteRole = useDeleteRole();

  const users = useMemo(() => (Array.isArray(data) ? data : []), [data]);

  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [deletingUser, setDeletingUser] = useState<User | null>(null);
  const [creatingUser, setCreatingUser] = useState(false);

  const handleDelete = async () => {
    if (!deletingUser) return;

    try {
      await deleteUser.mutateAsync(deletingUser.id);
      setDeletingUser(null);
      refetch();
    } catch (error) {
      console.error('Failed to delete user:', error);
    }
  };

  const activeUsers = useMemo(() => (Array.isArray(users) ? users.filter((u) => u.is_active).length : 0), [users]);
  const adminUsers = useMemo(() => (Array.isArray(users) ? users.filter((u) => u.roles.some(r => r.name === 'Super Admin')).length : 0), [users]);

  const roles = useMemo(() => (Array.isArray(rolesData) ? rolesData : []), [rolesData]);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [deletingRole, setDeletingRole] = useState<Role | null>(null);
  const [creatingRole, setCreatingRole] = useState(false);

  const handleDeleteRole = async () => {
    if (!deletingRole) return;

    try {
      await deleteRole.mutateAsync(deletingRole.id);
      setDeletingRole(null);
      refetchRoles();
    } catch (error) {
      console.error('Failed to delete role:', error);
    }
  };

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">User Management</h2>
          <p className="text-sm text-slate-500">
            {activeTab === 'users'
              ? `Manage user accounts and permissions. ${users.length} total users (${activeUsers} active, ${adminUsers} admins).`
              : `Manage roles and permissions. ${roles.length} total roles.`}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => activeTab === 'users' ? refetch() : refetchRoles()}
            disabled={activeTab === 'users' ? isFetching : rolesFetching}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-100"
          >
            {(activeTab === 'users' ? isFetching : rolesFetching) ? 'Refreshing…' : 'Refresh'}
          </button>
          <button
            type="button"
            onClick={() => activeTab === 'users' ? setCreatingUser(true) : setCreatingRole(true)}
            className="inline-flex items-center gap-1 rounded-md bg-brand-500 px-3 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-brand-600"
          >
            {activeTab === 'users' ? 'Create User' : 'Create Role'}
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="-mb-px flex gap-6">
          <button
            onClick={() => setActiveTab('users')}
            className={`flex items-center gap-2 border-b-2 px-1 py-3 text-sm font-medium transition ${
              activeTab === 'users'
                ? 'border-brand-500 text-brand-600'
                : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'
            }`}
          >
            <UsersIcon className="h-4 w-4" />
            Users
          </button>
          <button
            onClick={() => setActiveTab('roles')}
            className={`flex items-center gap-2 border-b-2 px-1 py-3 text-sm font-medium transition ${
              activeTab === 'roles'
                ? 'border-brand-500 text-brand-600'
                : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700'
            }`}
          >
            <Shield className="h-4 w-4" />
            Roles & Permissions
          </button>
        </nav>
      </div>

      {/* Users Tab Content */}
      {activeTab === 'users' && (
        <>
          {/* Filters */}
          <div className="flex items-center gap-4 rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex-1">
              <input
                type="text"
                placeholder="Search users by username or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-slate-700">Status:</label>
              <select
                value={activeFilter === undefined ? 'all' : activeFilter ? 'active' : 'inactive'}
                onChange={(e) =>
                  setActiveFilter(e.target.value === 'all' ? undefined : e.target.value === 'active')
                }
                className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="all">All</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-500">
              Loading users…
            </div>
          ) : isError ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
              Failed to load users. {error instanceof Error ? error.message : 'Please try again.'}
            </div>
          ) : (
            <UsersTable users={users} onEdit={setEditingUser} onDelete={setDeletingUser} />
          )}
        </>
      )}

      {/* Roles Tab Content */}
      {activeTab === 'roles' && (
        <>
          {rolesLoading ? (
            <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-500">
              Loading roles…
            </div>
          ) : rolesError ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
              Failed to load roles. {rolesErrorMsg instanceof Error ? rolesErrorMsg.message : 'Please try again.'}
            </div>
          ) : (
            <RolesTable roles={roles} onEdit={setEditingRole} onDelete={setDeletingRole} />
          )}
        </>
      )}

      {/* User Edit Modal */}
      <UserEditModal
        user={editingUser}
        open={!!editingUser || creatingUser}
        onClose={() => {
          setEditingUser(null);
          setCreatingUser(false);
        }}
        onSaved={() => {
          setEditingUser(null);
          setCreatingUser(false);
          refetch();
        }}
      />

      {/* Delete User Confirmation Modal */}
      {deletingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900">Delete User</h3>
            <p className="mt-2 text-sm text-slate-600">
              Are you sure you want to delete user <strong>{deletingUser.username}</strong>? This action cannot be undone.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeletingUser(null)}
                className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleteUser.isPending}
                className="rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-rose-700 disabled:cursor-not-allowed disabled:bg-rose-300"
              >
                {deleteUser.isPending ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Role Edit Modal */}
      <RoleEditModal
        role={editingRole}
        open={!!editingRole || creatingRole}
        onClose={() => {
          setEditingRole(null);
          setCreatingRole(false);
        }}
        onSaved={() => {
          setEditingRole(null);
          setCreatingRole(false);
          refetchRoles();
        }}
      />

      {/* Delete Role Confirmation Modal */}
      {deletingRole && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900">Delete Role</h3>
            <p className="mt-2 text-sm text-slate-600">
              Are you sure you want to delete role <strong>{deletingRole.name}</strong>? This action cannot be undone.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeletingRole(null)}
                className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteRole}
                disabled={deleteRole.isPending}
                className="rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-rose-700 disabled:cursor-not-allowed disabled:bg-rose-300"
              >
                {deleteRole.isPending ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
