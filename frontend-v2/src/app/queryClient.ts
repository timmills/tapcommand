import { QueryClient } from '@tanstack/react-query';

export const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          if (error instanceof Error && error.message.includes('404')) {
            return false;
          }
          return failureCount < 2;
        },
      },
    },
  });
