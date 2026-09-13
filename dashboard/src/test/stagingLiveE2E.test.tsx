import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ReportsPage } from '@/features/reports/ReportsPage';
import { IssueDetailPage } from '@/features/issues/IssueDetailPage';
import { ReportDetailPage } from '@/features/report-detail/ReportDetailPage';
import { AIOperationsPage } from '@/features/ai-operations/AIOperationsPage';
import { AuthProvider } from '@/core/auth/AuthContext';
import { ThemeProvider } from '@/core/theme/ThemeContext';
import { apiClient } from '@/services/api/apiClient';

// Mock MapRenderer to avoid Leaflet / Google Maps DOM issues in jsdom
vi.mock('@/features/map/MapRenderer', () => ({
  MapRenderer: () => <div data-testid="mock-map-renderer">Mock Map Centroid</div>,
}));

// Mock ThemeContext to avoid window.matchMedia issues in jsdom
vi.mock('@/core/theme/ThemeContext', () => ({
  useTheme: () => ({ theme: 'light', resolvedTheme: 'light', setTheme: vi.fn() }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock repositories to use live Api implementations against local backend
vi.mock('@/services/repository/issueRepository', async () => {
  const { ApiIssueRepository } = await import('@/services/repository/ApiIssueRepository');
  return {
    issueRepository: new ApiIssueRepository(),
  };
});

vi.mock('@/services/repository/reportRepository', async () => {
  const { ApiReportRepository } = await import('@/services/repository/ApiReportRepository');
  return {
    reportRepository: new ApiReportRepository(),
  };
});

describe('Staging Live E2E Integration Suite', () => {
  let queryClient: QueryClient;

  beforeAll(() => {
    apiClient.setBaseUrl('http://127.0.0.1:8000/api/v1');
    localStorage.setItem(
      'civicsense_active_officer',
      JSON.stringify({
        id: 'off-001',
        name: 'Priya Sharma',
        email: 'priya.sharma@civicsense.gov.in',
        badgeNumber: 'CS-TRG-042',
        department: 'Roads & Bridges',
        role: 'TRIAGE_OFFICER',
      })
    );
  });

  const createWrapper = (initialEntries: string[]) => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });

    return ({ children }: { children: React.ReactNode }) => (
      <ThemeProvider>
        <AuthProvider>
          <QueryClientProvider client={queryClient}>
            <MemoryRouter initialEntries={initialEntries}>
              {children}
            </MemoryRouter>
          </QueryClientProvider>
        </AuthProvider>
      </ThemeProvider>
    );
  };

  it('Test A — loads live reports queue and filters by issue_id', async () => {
    const issueId = '11111111-1111-1111-1111-111111111111';
    const Wrapper = createWrapper(['/reports?issue_id=' + issueId]);

    render(
      <Wrapper>
        <Routes>
          <Route path="/reports" element={<ReportsPage />} />
        </Routes>
      </Wrapper>
    );

    await waitFor(
      () => {
        expect(screen.getByText('Reports Work Queue')).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Active Filter: Showing reports linked to Aggregated Issue/i)
      ).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getAllByText(/REP-202609-MG001/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/REP-202609-MG002/i).length).toBeGreaterThan(0);
    });
  });

  it('Test B — renders live Issue Detail with KPIs, breakdown, and evidence', async () => {
    const issueId = '11111111-1111-1111-1111-111111111111';
    const Wrapper = createWrapper(['/issues/' + issueId]);

    render(
      <Wrapper>
        <Routes>
          <Route path="/issues/:id" element={<IssueDetailPage />} />
        </Routes>
      </Wrapper>
    );

    await waitFor(
      () => {
        expect(
          screen.getByText(/Severe Road Damage & Pothole Hazard on MG Road/i)
        ).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    expect(screen.getByText('Aggregated Issue')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Priority Scorecard Breakdown/i)).toBeInTheDocument();
    });

    expect(screen.getAllByText(/REP-202609-MG001/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/REP-202609-MG002/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/abhishek@example.com/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/9876543210/i)).not.toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Citizen Evidence Gallery/i)).toBeInTheDocument();
    });
  });

  it('Test B2 — handles empty issue with 0 reports gracefully', async () => {
    const emptyIssueId = '33333333-3333-3333-3333-333333333333';
    const Wrapper = createWrapper(['/issues/' + emptyIssueId]);

    render(
      <Wrapper>
        <Routes>
          <Route path="/issues/:id" element={<IssueDetailPage />} />
        </Routes>
      </Wrapper>
    );

    await waitFor(
      () => {
        expect(
          screen.getByText(/Garbage Dump Overflow near Central Market/i)
        ).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    await waitFor(() => {
      expect(
        screen.getByText(/No Reports Linked/i)
      ).toBeInTheDocument();
    });
  });

  it('Test B3 — handles 404 non-existent issue gracefully', async () => {
    const nonexistentId = '00000000-0000-0000-0000-000000000000';
    const Wrapper = createWrapper(['/issues/' + nonexistentId]);

    render(
      <Wrapper>
        <Routes>
          <Route path="/issues/:id" element={<IssueDetailPage />} />
        </Routes>
      </Wrapper>
    );

    await waitFor(
      () => {
        expect(screen.getByText(/Aggregated Issue Not Found/i)).toBeInTheDocument();
      },
      { timeout: 5000 }
    );
  });

  it('Test C — renders Report Detail with Associated Issue card', async () => {
    const reportId = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';
    const Wrapper = createWrapper(['/reports/' + reportId]);

    render(
      <Wrapper>
        <Routes>
          <Route path="/reports/:id" element={<ReportDetailPage />} />
        </Routes>
      </Wrapper>
    );

    await waitFor(
      () => {
        expect(screen.getByText(/REP-202609-MG002/i)).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    await waitFor(() => {
      expect(screen.getByText(/Associated Issue/i)).toBeInTheDocument();
    });

    const issueBtn = screen.getByRole('button', { name: /View Aggregated Issue/i });
    expect(issueBtn).toBeInTheDocument();
  });

  it('Test D — loads pending candidate matches and validates modals', async () => {
    const Wrapper = createWrapper(['/ai-operations?tab=matches']);

    render(
      <Wrapper>
        <Routes>
          <Route path="/ai-operations" element={<AIOperationsPage />} />
        </Routes>
      </Wrapper>
    );

    await waitFor(
      () => {
        expect(screen.getByText(/Pending Duplicate Matches/i)).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    await waitFor(() => {
      expect(screen.getByText(/rep-dddddddd/i)).toBeInTheDocument();
    });

    const rejectBtn = screen.getByRole('button', { name: /Reject/i });
    fireEvent.click(rejectBtn);

    await waitFor(() => {
      expect(screen.getByText(/Reject Candidate Duplicate Match/i)).toBeInTheDocument();
    });

    const altInput = screen.getByLabelText(/Link to Alternate Issue UUID/i);
    fireEvent.change(altInput, { target: { value: 'not-a-valid-uuid' } });

    const confirmRejectBtn = screen.getByRole('button', { name: /Confirm Rejection/i });
    fireEvent.click(confirmRejectBtn);

    // Invalid UUID triggers action error
    await waitFor(() => {
      expect(
        screen.getByText(/Alternate issue ID must be a valid 36-character UUID string/i)
      ).toBeInTheDocument();
    });

    // Provide valid UUID and valid reason
    fireEvent.change(altInput, {
      target: { value: '22222222-2222-2222-2222-222222222222' },
    });

    const reasonInput = screen.getByLabelText(/Rejection Reason/i);
    fireEvent.change(reasonInput, { target: { value: 'Belongs to different street defect.' } });

    expect(confirmRejectBtn).not.toBeDisabled();
  });
});
