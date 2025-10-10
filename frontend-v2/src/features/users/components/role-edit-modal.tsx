import { useState, useEffect, useMemo } from 'react';
import { X, Save, Shield, Check } from 'lucide-react';
import type { Role } from '@/lib/api/users';
import type { Permission } from '@/lib/api/roles';
import { usePermissions, useRole, useUpdateRole, useCreateRole, useAssignPermission, useRemovePermission } from '../hooks/use-roles';

interface RoleEditModalProps {
  role: Role | null;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export const RoleEditModal = ({ role, open, onClose, onSaved }: RoleEditModalProps) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedPermissions, setSelectedPermissions] = useState<Set<number>>(new Set());

  const isEditing = !!role;
  const isSystemRole = role && ['Super Admin', 'Administrator', 'Operator', 'Viewer'].includes(role.name);

  // Fetch all permissions
  const { data: allPermissions = [] } = usePermissions();

  // Fetch role details with permissions if editing
  const { data: roleDetails } = useRole(role?.id || 0);

  const updateRole = useUpdateRole();
  const createRole = useCreateRole();
  const assignPermission = useAssignPermission();
  const removePermission = useRemovePermission();

  // Group permissions by resource
  const groupedPermissions = useMemo(() => {
    const groups: Record<string, Permission[]> = {};

    allPermissions.forEach(permission => {
      if (!groups[permission.resource]) {
        groups[permission.resource] = [];
      }
      groups[permission.resource].push(permission);
    });

    return groups;
  }, [allPermissions]);

  // Initialize form when role changes
  useEffect(() => {
    if (role) {
      setName(role.name);
      setDescription(role.description || '');
    } else {
      setName('');
      setDescription('');
    }

    if (roleDetails?.permissions) {
      setSelectedPermissions(new Set(roleDetails.permissions.map(p => p.id)));
    } else {
      setSelectedPermissions(new Set());
    }
  }, [role, roleDetails]);

  const handleSave = async () => {
    try {
      if (isEditing) {
        // Update existing role
        await updateRole.mutateAsync({
          roleId: role.id,
          data: {
            name: isSystemRole ? undefined : name, // Don't allow renaming system roles
            description,
          },
        });

        // Update permissions
        const currentPermissions = roleDetails?.permissions.map(p => p.id) || [];
        const toAdd = Array.from(selectedPermissions).filter(id => !currentPermissions.includes(id));
        const toRemove = currentPermissions.filter(id => !selectedPermissions.has(id));

        // Add new permissions
        for (const permissionId of toAdd) {
          await assignPermission.mutateAsync({ roleId: role.id, permissionId });
        }

        // Remove old permissions
        for (const permissionId of toRemove) {
          await removePermission.mutateAsync({ roleId: role.id, permissionId });
        }
      } else {
        // Create new role
        await createRole.mutateAsync({
          name,
          description,
          permission_ids: Array.from(selectedPermissions),
        });
      }

      onSaved();
    } catch (error) {
      console.error('Failed to save role:', error);
    }
  };

  const togglePermission = (permissionId: number) => {
    const newSelected = new Set(selectedPermissions);
    if (newSelected.has(permissionId)) {
      newSelected.delete(permissionId);
    } else {
      newSelected.add(permissionId);
    }
    setSelectedPermissions(newSelected);
  };

  const toggleResource = (resource: string) => {
    const resourcePermissions = groupedPermissions[resource] || [];
    const allSelected = resourcePermissions.every(p => selectedPermissions.has(p.id));

    const newSelected = new Set(selectedPermissions);
    resourcePermissions.forEach(p => {
      if (allSelected) {
        newSelected.delete(p.id);
      } else {
        newSelected.add(p.id);
      }
    });
    setSelectedPermissions(newSelected);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-lg bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <Shield className="h-6 w-6 text-brand-600" />
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                {isEditing ? `Edit Role: ${role.name}` : 'Create New Role'}
              </h2>
              <p className="text-sm text-slate-500">
                {isEditing ? 'Modify role permissions and settings' : 'Define a new role with specific permissions'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 hover:bg-slate-100"
          >
            <X className="h-5 w-5 text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto p-6" style={{ maxHeight: 'calc(90vh - 140px)' }}>
          <div className="space-y-6">
            {/* Basic Info */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700">
                  Role Name {isSystemRole && <span className="text-slate-500">(System role - cannot be changed)</span>}
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={!!isSystemRole}
                  className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:bg-slate-100 disabled:text-slate-500"
                  placeholder="e.g., Content Manager"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  placeholder="Brief description of this role's purpose"
                />
              </div>
            </div>

            {/* Permissions */}
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Permissions</h3>
              <p className="mt-1 text-sm text-slate-500">
                Select which actions this role can perform
              </p>

              <div className="mt-4 space-y-4">
                {Object.entries(groupedPermissions).map(([resource, permissions]) => {
                  const allSelected = permissions.every(p => selectedPermissions.has(p.id));
                  const someSelected = permissions.some(p => selectedPermissions.has(p.id));

                  return (
                    <div key={resource} className="rounded-lg border border-slate-200 bg-white">
                      {/* Resource Header */}
                      <div
                        className="flex items-center gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3 cursor-pointer hover:bg-slate-100"
                        onClick={() => toggleResource(resource)}
                      >
                        <div className="flex h-5 w-5 items-center justify-center rounded border-2 border-slate-300 bg-white">
                          {allSelected && <Check className="h-4 w-4 text-brand-600" />}
                          {someSelected && !allSelected && (
                            <div className="h-2.5 w-2.5 rounded-sm bg-brand-600" />
                          )}
                        </div>
                        <span className="font-semibold capitalize text-slate-900">
                          {resource.replace('_', ' ')}
                        </span>
                        <span className="text-sm text-slate-500">
                          ({permissions.filter(p => selectedPermissions.has(p.id)).length}/{permissions.length})
                        </span>
                      </div>

                      {/* Individual Permissions */}
                      <div className="grid gap-2 p-4 sm:grid-cols-2">
                        {permissions.map(permission => (
                          <label
                            key={permission.id}
                            className="flex items-start gap-3 cursor-pointer rounded-md p-2 hover:bg-slate-50"
                          >
                            <input
                              type="checkbox"
                              checked={selectedPermissions.has(permission.id)}
                              onChange={() => togglePermission(permission.id)}
                              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                            />
                            <div className="flex-1">
                              <div className="text-sm font-medium text-slate-900">
                                {permission.action}
                              </div>
                              <div className="text-xs text-slate-500">
                                {permission.description}
                              </div>
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
          <div className="text-sm text-slate-600">
            {selectedPermissions.size} permission{selectedPermissions.size !== 1 ? 's' : ''} selected
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!name.trim() || updateRole.isPending || createRole.isPending}
              className="inline-flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-brand-300"
            >
              <Save className="h-4 w-4" />
              {isEditing ? 'Save Changes' : 'Create Role'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
