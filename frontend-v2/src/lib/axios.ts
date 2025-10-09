import axios from 'axios';
import { API_BASE_URL } from './env';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error('API error response', error.response.status, error.response.data);
    } else if (error.request) {
      console.error('API request made but no response received', error.config?.url);
    } else {
      console.error('Unexpected axios error', error.message);
    }
    return Promise.reject(error);
  },
);
