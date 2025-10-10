import type { User } from '@/lib/api/users';
import { formatDistanceToNow } from 'date-fns';

interface UsersTableProps {
  users: User[];
  onEdit: (user: User) => void;
  onDelete: (user: User) => void;
}

export const UsersTable = ({ users, onEdit, onDelete }: UsersTableProps) => {
  if (users.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white p-12 text-center">
        <p className="text-sm font-medium text-slate-900">No users found</p>
        <p className="mt-1 text-sm text-slate-500">Get started by creating a new user.</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">
              User
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">
              Email
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">
              Roles
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">
              Status
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-700">
              Last Login
            </th>
            <th scope="col" className="relative px-6 py-3">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white">
          {users.map((user) => (
            <tr key={user.id} className="hover:bg-slate-50">
              <td className="whitespace-nowrap px-6 py-4">
                <div className="flex items-center">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-medium text-brand-700">
                    {user.username.substring(0, 2).toUpperCase()}
                  </div>
                  <div className="ml-4">
                    <div className="text-sm font-medium text-slate-900">{user.username}</div>
                    {user.full_name && <div className="text-sm text-slate-500">{user.full_name}</div>}
                  </div>
                </div>
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-700">{user.email}</td>
              <td className="whitespace-nowrap px-6 py-4">
                <div className="flex flex-wrap gap-1">
                  {user.roles.length > 0 ? (
                    user.roles.map((role) => (
                      <span
                        key={role.id}
                        className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-800"
                      >
                        {role.name}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-400">No roles</span>
                  )}
                </div>
              </td>
              <td className="whitespace-nowrap px-6 py-4">
                <div className="flex flex-col gap-1">
                  {user.is_active ? (
                    <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                      Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
                      Inactive
                    </span>
                  )}
                  {user.must_change_password && (
                    <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
                      Must change password
                    </span>
                  )}
                </div>
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-500">
                {user.last_login ? formatDistanceToNow(new Date(user.last_login), { addSuffix: true }) : 'Never'}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
                <button
                  type="button"
                  onClick={() => onEdit(user)}
                  className="text-brand-600 hover:text-brand-900"
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => onDelete(user)}
                  className="ml-4 text-rose-600 hover:text-rose-900"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
