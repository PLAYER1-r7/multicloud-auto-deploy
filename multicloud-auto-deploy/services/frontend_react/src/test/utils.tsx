/**
 * Shared test utilities
 *
 * Wraps the component under test with the providers needed to mimic the real
 * app environment (React Query QueryClientProvider, etc.).
 */
import { type ReactElement } from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

/** Build a fresh QueryClient for each test (no shared cache between tests). */
function buildQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

/** Custom render that wraps children in all required providers. */
function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) {
  const queryClient = buildQueryClient();

  return render(ui, {
    wrapper: ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
    ...options,
  });
}

// Re-export everything from @testing-library/react so tests only need one import
export * from '@testing-library/react';
export { renderWithProviders as render };
