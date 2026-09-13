import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { IssueDetailPage } from '@/features/issues/IssueDetailPage';
import { AuthProvider } from '@/core/auth/AuthContext';
import { ThemeProvider } from '@/core/theme/ThemeContext';

// Mock MapRenderer to avoid Leaflet / Google Maps DOM issues in jsdom
vi.mock('@/features/map/MapRenderer', () => ({
  MapRenderer: () => <div data-testid="mock-map-renderer">Mock Map</div>,
}));

// Mock ThemeContext to avoid window.matchMedia issues in jsdom
vi.mock('@/core/theme/ThemeContext', () => ({
  useTheme: () => ({ theme: 'light', resolvedTheme: 'light', setTheme: vi.fn() }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock issueRepository with MockIssueRepository for deterministic unit tests
vi.mock('@/services/repository/issueRepository', async () => {
  const { MockIssueRepository } = await import('@/services/repository/MockIssueRepository');
  return {
    issueRepository: new MockIssueRepository(),
  };
});

describe('IssueDetailPage Component', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  const renderComponent = (issueId: string = 'iss-001') => {
    return render(
      <ThemeProvider>
        <AuthProvider>
          <QueryClientProvider client={queryClient}>
            <MemoryRouter initialEntries={[`/issues/${issueId}`]}>
              <Routes>
                <Route path="/issues/:id" element={<IssueDetailPage />} />
              </Routes>
            </MemoryRouter>
          </QueryClientProvider>
        </AuthProvider>
      </ThemeProvider>
    );
  };

  it('renders issue detail header, KPIs, and domain banner for valid issue', async () => {
    renderComponent('iss-001');

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('Aggregated Issue')).toBeInTheDocument();
    });

    // Verify issue ID is shown
    expect(screen.getByText(/iss-001/)).toBeInTheDocument();

    // Verify domain model notice
    expect(
      screen.getByText(/Defect Cluster Workspace/i)
    ).toBeInTheDocument();

    // Verify KPI stats rendered
    expect(screen.getAllByText(/Linked Citizen Reports/i).length).toBeGreaterThan(0);
    expect(screen.getByText('Priority Score')).toBeInTheDocument();
    expect(screen.getByText('Centroid Coordinates')).toBeInTheDocument();

    // Verify priority breakdown section
    expect(screen.getByText(/Priority Scorecard Breakdown/i)).toBeInTheDocument();

    // Verify linked reports section
    expect(screen.getByText(/Linked Citizen Reports/i)).toBeInTheDocument();
  });

  it('renders not found empty state when issue does not exist', async () => {
    renderComponent('non-existent-issue-999');

    await waitFor(() => {
      expect(screen.getByText('Aggregated Issue Not Found')).toBeInTheDocument();
    });

    expect(screen.getByText('Return to Reports Queue')).toBeInTheDocument();
  });

  it('safely handles issue with null priority score and unranked level', async () => {
    // Override getIssueById and getIssuePriority for an unranked issue
    const { issueRepository } = await import('@/services/repository/issueRepository');
    vi.spyOn(issueRepository, 'getIssueById').mockResolvedValueOnce({
      id: 'iss-unranked-99',
      title: 'Unranked Water Problem',
      category: 'Water Leakage',
      status: 'OPEN',
      latitude: 12.98,
      longitude: 77.59,
      reportCount: 1,
      priorityScore: null,
      priorityLevel: null,
      priorityComputedAt: null,
      createdAt: '2026-03-31T10:00:00Z',
      updatedAt: '2026-03-31T10:00:00Z',
    });
    vi.spyOn(issueRepository, 'getIssuePriority').mockResolvedValueOnce({
      issueId: 'iss-unranked-99',
      priorityScore: null,
      priorityLevel: null,
      priorityComputedAt: null,
      breakdown: null,
    });

    renderComponent('iss-unranked-99');

    await waitFor(() => {
      expect(screen.getByText('Unranked Water Problem')).toBeInTheDocument();
    });

    // Verify unranked priority badge is rendered safely
    expect(screen.getByText('UNRANKED')).toBeInTheDocument();
    // Verify uncalculated metric stat
    expect(screen.getByText('Uncalculated')).toBeInTheDocument();
    expect(screen.getByText('Pending calculation')).toBeInTheDocument();
  });
});
