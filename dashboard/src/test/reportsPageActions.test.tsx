import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { ReportsPage } from '@/features/reports/ReportsPage';
import { AuthProvider } from '@/core/auth/AuthContext';
import { ThemeProvider } from '@/core/theme/ThemeContext';
import { reportRepository } from '@/services/repository/reportRepository';
import { ReportItem } from '@/types/models';

vi.mock('@/core/theme/ThemeContext', () => ({
  useTheme: () => ({ theme: 'light', resolvedTheme: 'light', setTheme: vi.fn() }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const mockReports: ReportItem[] = [
  {
    id: 'rep-test-001',
    trackingId: 'REP-202609-000001',
    category: 'Pothole',
    description: 'Deep hazardous crater on main road near junction',
    latitude: 12.9716,
    longitude: 77.5946,
    addressHint: 'MG Road, Bengaluru',
    severity: 'HIGH',
    priority: 'HIGH',
    status: 'SUBMITTED',
    createdAt: '2026-09-12T10:00:00Z',
    updatedAt: '2026-09-12T10:00:00Z',
    reviewRequired: true,
    evidences: [],
    aiAnalyses: [],
    verifications: [],
    internalNotes: [],
    auditTrail: [],
  },
  {
    id: 'rep-test-002',
    trackingId: 'REP-202609-000002',
    category: 'Garbage',
    description: 'Overflowing commercial waste container on pavement',
    latitude: 12.972,
    longitude: 77.595,
    addressHint: 'Brigade Road, Bengaluru',
    severity: 'MEDIUM',
    priority: 'MEDIUM',
    status: 'AI_PROCESSED',
    createdAt: '2026-09-12T09:30:00Z',
    updatedAt: '2026-09-12T09:35:00Z',
    reviewRequired: false,
    evidences: [],
    aiAnalyses: [],
    verifications: [],
    internalNotes: [],
    auditTrail: [],
  },
  {
    id: 'rep-test-003',
    trackingId: 'REP-202609-000003',
    category: 'Water Leakage',
    description: 'Continuous drinking water line rupture',
    latitude: 12.973,
    longitude: 77.596,
    addressHint: 'Residency Road, Bengaluru',
    severity: 'HIGH',
    priority: 'HIGH',
    status: 'VERIFIED',
    createdAt: '2026-09-12T08:30:00Z',
    updatedAt: '2026-09-12T08:45:00Z',
    reviewRequired: false,
    evidences: [],
    aiAnalyses: [],
    verifications: [],
    internalNotes: [],
    auditTrail: [],
  },
];

describe('ReportsPage Admin Actions', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    vi.spyOn(reportRepository, 'getReports').mockResolvedValue({
      items: mockReports,
      total: mockReports.length,
      page: 1,
      pageSize: 10,
      totalPages: 1,
    });
  });

  const renderComponent = () => {
    return render(
      <ThemeProvider>
        <AuthProvider>
          <QueryClientProvider client={queryClient}>
            <MemoryRouter>
              <ReportsPage />
            </MemoryRouter>
          </QueryClientProvider>
        </AuthProvider>
      </ThemeProvider>
    );
  };

  it('renders reports work queue with action buttons and dropdown trigger', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('REP-202609-000001')).toBeInTheDocument();
      expect(screen.getByText('REP-202609-000002')).toBeInTheDocument();
      expect(screen.getByText('REP-202609-000003')).toBeInTheDocument();
    });

    // SUBMITTED report shows Run AI button
    expect(screen.getByTitle('Manually Start AI Multimodal Analysis')).toBeInTheDocument();

    // AI_PROCESSED report shows Verify button
    expect(screen.getByTitle('Verify Report & Set Severity')).toBeInTheDocument();

    // VERIFIED report shows Assign button
    expect(screen.getByTitle('Assign Department & Crew')).toBeInTheDocument();

    // More actions triggers exist
    const menuButtons = screen.getAllByTitle('More Administrative Actions');
    expect(menuButtons.length).toBe(3);
  });

  it('manually triggers AI analysis when Run AI button is clicked', async () => {
    const triggerAISpy = vi.spyOn(reportRepository, 'triggerAIProcess').mockResolvedValue({
      id: 'job-test-12345678',
      report_id: 'rep-test-001',
      status: 'COMPLETED',
      current_stage: 'COMPLETED',
      execution_mode: 'synchronous_demo',
      processor_name: 'Deterministic Demo Processor',
      review_required: false,
      review_completed: false,
      queued_at: new Date().toISOString(),
      attempt_count: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('REP-202609-000001')).toBeInTheDocument();
    });

    const runAiBtn = screen.getByTitle('Manually Start AI Multimodal Analysis');
    fireEvent.click(runAiBtn);

    await waitFor(() => {
      expect(triggerAISpy).toHaveBeenCalledWith('rep-test-001');
    });

    // Feedback banner displayed
    await waitFor(() => {
      expect(screen.getByText(/AI analysis successfully triggered/i)).toBeInTheDocument();
    });
  });

  it('opens Verify & Set Severity modal and submits verification', async () => {
    const verifySpy = vi.spyOn(reportRepository, 'verifyReport').mockResolvedValue({
      ...mockReports[1],
      status: 'VERIFIED',
      severity: 'CRITICAL',
      category: 'Garbage',
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('REP-202609-000002')).toBeInTheDocument();
    });

    // Click Verify button on AI_PROCESSED report
    const verifyBtn = screen.getByTitle('Verify Report & Set Severity');
    fireEvent.click(verifyBtn);

    // Modal opens
    await waitFor(() => {
      expect(
        screen.getByText(/Verify Report & Set Severity \(REP-202609-000002\)/i)
      ).toBeInTheDocument();
    });

    // Select CRITICAL severity
    const criticalOption = screen.getByRole('button', { name: /CRITICAL/i });
    fireEvent.click(criticalOption);

    // Click Confirm Verification
    const confirmBtn = screen.getByRole('button', { name: /Confirm Verification/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(verifySpy).toHaveBeenCalledWith(
        'rep-test-002',
        'CONFIRMED',
        'Garbage',
        'CRITICAL',
        '',
        expect.any(String)
      );
    });
  });

  it('opens Assign Department modal and submits departmental dispatch', async () => {
    const assignSpy = vi.spyOn(reportRepository, 'assignDepartment').mockResolvedValue({
      ...mockReports[2],
      status: 'ASSIGNED',
      department: 'Water Supply & Sewerage',
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('REP-202609-000003')).toBeInTheDocument();
    });

    // Click Assign button on VERIFIED report
    const assignBtn = screen.getByTitle('Assign Department & Crew');
    fireEvent.click(assignBtn);

    // Modal opens
    await waitFor(() => {
      expect(
        screen.getByText(/Assign Department \(REP-202609-000003\)/i)
      ).toBeInTheDocument();
    });

    // Click Assign Department in modal footer
    const confirmAssignBtn = screen.getByRole('button', { name: /^Assign Department$/i });
    fireEvent.click(confirmAssignBtn);

    await waitFor(() => {
      expect(assignSpy).toHaveBeenCalledWith(
        'rep-test-003',
        'Roads & Bridges',
        undefined,
        expect.any(String)
      );
    });
  });

  it('opens action dropdown and triggers report rejection', async () => {
    const rejectSpy = vi.spyOn(reportRepository, 'verifyReport').mockResolvedValue({
      ...mockReports[0],
      status: 'CLOSED',
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('REP-202609-000001')).toBeInTheDocument();
    });

    // Open More Actions menu for first report
    const menuBtn = screen.getByTestId('actions-menu-rep-test-001');
    fireEvent.click(menuBtn);

    // Dropdown contains Reject Report option
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Reject Report/i })).toBeInTheDocument();
    });

    // Click Reject Report
    fireEvent.click(screen.getByRole('button', { name: /Reject Report/i }));

    // Reject modal opens
    await waitFor(() => {
      expect(
        screen.getByText(/Reject \/ Close Report \(REP-202609-000001\)/i)
      ).toBeInTheDocument();
    });

    // Click Confirm Rejection
    const confirmRejectBtn = screen.getByRole('button', { name: /Confirm Rejection/i });
    fireEvent.click(confirmRejectBtn);

    await waitFor(() => {
      expect(rejectSpy).toHaveBeenCalledWith(
        'rep-test-001',
        'REJECTED',
        undefined,
        undefined,
        '',
        expect.any(String)
      );
    });
  });

  it('opens action dropdown and triggers priority update', async () => {
    const prioritizeSpy = vi.spyOn(reportRepository, 'prioritizeReport').mockResolvedValue({
      ...mockReports[0],
      priority: 'CRITICAL',
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('REP-202609-000001')).toBeInTheDocument();
    });

    // Open More Actions menu
    const menuBtn = screen.getByTestId('actions-menu-rep-test-001');
    fireEvent.click(menuBtn);

    // Click Set Priority (SLA)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Set Priority \(SLA\)/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /Set Priority \(SLA\)/i }));

    // Priority modal opens
    await waitFor(() => {
      expect(
        screen.getByText(/Set Operational Priority \(REP-202609-000001\)/i)
      ).toBeInTheDocument();
    });

    // Click Update Priority
    const confirmPrioritizeBtn = screen.getByRole('button', { name: /Update Priority/i });
    fireEvent.click(confirmPrioritizeBtn);

    await waitFor(() => {
      expect(prioritizeSpy).toHaveBeenCalledWith(
        'rep-test-001',
        'HIGH',
        expect.any(String)
      );
    });
  });
});
