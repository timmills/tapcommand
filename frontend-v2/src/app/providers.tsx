import { useState } from 'react';
import type { ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';

import { createQueryClient } from './queryClient';
import { router } from './router';
import { AuthProvider } from '../features/auth/context/auth-context';

interface AppProvidersProps {
  children?: ReactNode;
}

export const AppProviders = ({ children }: AppProvidersProps) => {
  const [queryClient] = useState(() => createQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
        {children}
      </AuthProvider>
    </QueryClientProvider>
  );
};
