import { apiClient } from '../axios';

export interface Role {
  id: number;
  name: string;
  description?: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  must_change_password: boolean;
  roles: Role[];
  last_login?: string;
  created_at: string;
}

export interface CreateUserRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  is_superuser?: boolean;
  must_change_password?: boolean;
  role_ids?: number[];
}

export interface UpdateUserRequest {
  email?: string;
  full_name?: string;
  is_active?: boolean;
  is_superuser?: boolean;
}

export interface UserSearchParams {
  q?: string;
  is_active?: boolean;
  is_superuser?: boolean;
  role_id?: number;
  skip?: number;
  limit?: number;
}

export interface PasswordResetRequest {
  new_password: string;
  must_change_password?: boolean;
}

// User management API
export const usersApi = {
  // List users with optional filters
  async listUsers(params?: UserSearchParams): Promise<User[]> {
    const response = await apiClient.get('/api/v1/users', { params });
    return response.data.users || [];
  },

  // Get single user by ID
  async getUser(userId: number): Promise<User> {
    const response = await apiClient.get(`/api/v1/users/${userId}`);
    return response.data;
  },

  // Create new user
  async createUser(data: CreateUserRequest): Promise<User> {
    const response = await apiClient.post('/api/v1/users', data);
    return response.data;
  },

  // Update user
  async updateUser(userId: number, data: UpdateUserRequest): Promise<User> {
    const response = await apiClient.patch(`/api/v1/users/${userId}`, data);
    return response.data;
  },

  // Delete user
  async deleteUser(userId: number): Promise<void> {
    await apiClient.delete(`/api/v1/users/${userId}`);
  },

  // Reset user password
  async resetPassword(userId: number, data: PasswordResetRequest): Promise<void> {
    await apiClient.post(`/api/v1/users/${userId}/reset-password`, data);
  },

  // Activate user
  async activateUser(userId: number): Promise<User> {
    const response = await apiClient.post(`/api/v1/users/${userId}/activate`);
    return response.data;
  },

  // Deactivate user
  async deactivateUser(userId: number): Promise<User> {
    const response = await apiClient.post(`/api/v1/users/${userId}/deactivate`);
    return response.data;
  },

  // Assign role to user
  async assignRole(userId: number, roleId: number): Promise<User> {
    const response = await apiClient.post(`/api/v1/users/${userId}/roles/${roleId}`);
    return response.data;
  },

  // Remove role from user
  async removeRole(userId: number, roleId: number): Promise<User> {
    const response = await apiClient.delete(`/api/v1/users/${userId}/roles/${roleId}`);
    return response.data;
  },
};
