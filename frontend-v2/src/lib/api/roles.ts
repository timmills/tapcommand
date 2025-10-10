import { apiClient } from '../axios';
import type { Role } from './users';

export interface Permission {
  id: number;
  resource: string;
  action: string;
  description: string;
}

export interface RoleWithPermissions extends Role {
  permissions: Permission[];
  is_system_role: boolean;
}

export interface CreateRoleRequest {
  name: string;
  description?: string;
  permission_ids?: number[];
}

export interface UpdateRoleRequest {
  name?: string;
  description?: string;
}

// Roles API
export const rolesApi = {
  // List all roles
  async listRoles(): Promise<Role[]> {
    const response = await apiClient.get('/api/v1/auth/roles');
    return response.data.roles || [];
  },

  // Get single role with permissions
  async getRole(roleId: number): Promise<RoleWithPermissions> {
    const response = await apiClient.get(`/api/v1/auth/roles/${roleId}`);
    return response.data;
  },

  // Create new role
  async createRole(data: CreateRoleRequest): Promise<Role> {
    const response = await apiClient.post('/api/v1/auth/roles', data);
    return response.data;
  },

  // Update role
  async updateRole(roleId: number, data: UpdateRoleRequest): Promise<Role> {
    const response = await apiClient.patch(`/api/v1/auth/roles/${roleId}`, data);
    return response.data;
  },

  // Delete role
  async deleteRole(roleId: number): Promise<void> {
    await apiClient.delete(`/api/v1/auth/roles/${roleId}`);
  },

  // Assign permission to role
  async assignPermission(roleId: number, permissionId: number): Promise<RoleWithPermissions> {
    const response = await apiClient.post(`/api/v1/auth/roles/${roleId}/permissions/${permissionId}`);
    return response.data;
  },

  // Remove permission from role
  async removePermission(roleId: number, permissionId: number): Promise<RoleWithPermissions> {
    const response = await apiClient.delete(`/api/v1/auth/roles/${roleId}/permissions/${permissionId}`);
    return response.data;
  },

  // List all permissions
  async listPermissions(): Promise<Permission[]> {
    const response = await apiClient.get('/api/v1/auth/permissions');
    return response.data.permissions || [];
  },
};
