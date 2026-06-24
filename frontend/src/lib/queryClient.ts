import { QueryClient } from "@tanstack/react-query";

/** Shared React Query client (server-state cache). */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
