import { Shield, Edit, Trash2, Lock } from 'lucide-react';
import type { Role } from '@/lib/api/users';

interface RolesTableProps {
  roles: Role[];
  onEdit: (role: Role) => void;
  onDelete: (role: Role) => void;
}

export const RolesTable = ({ roles, onEdit, onDelete }: RolesTableProps) => {
  if (roles.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center">
        <Shield className="mx-auto h-12 w-12 text-slate-400" />
        <p className="mt-2 text-sm text-slate-500">No roles found</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
              Role Name
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
              Description
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
              Type
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-500">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white">
          {roles.map((role) => {
            // Determine if this is a system role (based on common role names)
            const isSystemRole = ['Super Admin', 'Administrator', 'Operator', 'Viewer'].includes(role.name);

            return (
              <tr key={role.id} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-6 py-4">
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-brand-500" />
                    <span className="font-medium text-slate-900">{role.name}</span>
                    {isSystemRole && (
                      <span title="System role">
                        <Lock className="h-3 w-3 text-slate-400" />
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <p className="text-sm text-slate-600">{role.description || 'No description'}</p>
                </td>
                <td className="whitespace-nowrap px-6 py-4">
                  <span
                    className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                      isSystemRole
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-slate-100 text-slate-800'
                    }`}
                  >
                    {isSystemRole ? 'System' : 'Custom'}
                  </span>
                </td>
                <td className="whitespace-nowrap px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => onEdit(role)}
                      className="inline-flex items-center gap-1 rounded-md bg-brand-50 px-3 py-1.5 text-sm font-medium text-brand-700 hover:bg-brand-100"
                      title="Edit role permissions"
                    >
                      <Edit className="h-3.5 w-3.5" />
                      Edit
                    </button>
                    {!isSystemRole && (
                      <button
                        onClick={() => onDelete(role)}
                        className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-3 py-1.5 text-sm font-medium text-rose-700 hover:bg-rose-100"
                        title="Delete role"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
