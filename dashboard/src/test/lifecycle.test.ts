import { describe, it, expect, beforeEach } from 'vitest';
import { ALLOWED_TRANSITIONS } from '@/types/models';
import { MockReportRepository } from '@/services/repository/MockReportRepository';
import { RepositoryError } from '@/services/api/apiError';

describe('Report Lifecycle & Transitions', () => {
  let repo: MockReportRepository;

  beforeEach(() => {
    repo = new MockReportRepository();
  });

  it('verifies canonical transition map integrity', () => {
    expect(ALLOWED_TRANSITIONS.SUBMITTED).toContain('AI_PROCESSING');
    expect(ALLOWED_TRANSITIONS.SUBMITTED).toContain('CLOSED');
    expect(ALLOWED_TRANSITIONS.VERIFICATION_REQUIRED).toContain('VERIFIED');
    expect(ALLOWED_TRANSITIONS.VERIFICATION_REQUIRED).toContain('CLOSED');
    expect(ALLOWED_TRANSITIONS.PRIORITIZED).toContain('ASSIGNED');
    expect(ALLOWED_TRANSITIONS.PRIORITIZED).toContain('IN_PROGRESS');
    expect(ALLOWED_TRANSITIONS.IN_PROGRESS).toContain('RESOLVED');
    expect(ALLOWED_TRANSITIONS.RESOLVED).toContain('RESOLUTION_VERIFIED');
    expect(ALLOWED_TRANSITIONS.RESOLUTION_VERIFIED).toContain('CLOSED');
    expect(ALLOWED_TRANSITIONS.CLOSED).toHaveLength(0); // Terminal state
  });

  it('executes valid transition from VERIFICATION_REQUIRED to VERIFIED', async () => {
    // rep-uuid-001 is in VERIFICATION_REQUIRED
    const updated = await repo.transitionStatus(
      'rep-uuid-001',
      'VERIFIED',
      undefined,
      'Review confirmed',
      'Test Officer'
    );
    expect(updated.status).toBe('VERIFIED');
    expect(updated.auditTrail[0].action).toContain('Status transitioned to VERIFIED');
    expect(updated.auditTrail[0].actor).toBe('Test Officer');
  });

  it('rejects illegal transition and throws RepositoryError', async () => {
    // rep-uuid-001 is in VERIFICATION_REQUIRED; transitioning directly to RESOLVED is forbidden
    await expect(
      repo.transitionStatus('rep-uuid-001', 'RESOLVED')
    ).rejects.toThrow(RepositoryError);
  });

  it('rejects transition from terminal state CLOSED', async () => {
    // rep-uuid-005 is CLOSED
    await expect(
      repo.transitionStatus('rep-uuid-005', 'IN_PROGRESS')
    ).rejects.toThrow(RepositoryError);
  });

  it('executes verification verdict and records reviewer', async () => {
    const updated = await repo.verifyReport(
      'rep-uuid-001',
      'CONFIRMED',
      'Pothole',
      'CRITICAL',
      'Grave physical danger verified'
    );
    expect(updated.status).toBe('VERIFIED');
    expect(updated.severity).toBe('CRITICAL');
    expect(updated.verifications.length).toBeGreaterThan(0);
    expect(updated.verifications[0].decision).toBe('CONFIRMED');
  });

  it('executes rejection verdict and transitions directly to CLOSED', async () => {
    const updated = await repo.verifyReport(
      'rep-uuid-001',
      'REJECTED',
      undefined,
      undefined,
      'Image is unlocatable and blurry'
    );
    expect(updated.status).toBe('CLOSED');
    expect(updated.closureReason).toBe('INVALID_REPORT');
  });

  it('transitions report from SUBMITTED to AI_PROCESSING', async () => {
    // rep-uuid-006 is in SUBMITTED
    const updated = await repo.transitionStatus(
      'rep-uuid-006',
      'AI_PROCESSING',
      undefined,
      'Triggered AI Pipeline',
      'Triage Officer'
    );
    expect(updated.status).toBe('AI_PROCESSING');
    expect(updated.auditTrail[0].fromStatus).toBe('SUBMITTED');
    expect(updated.auditTrail[0].toStatus).toBe('AI_PROCESSING');
  });

  it('adds an internal staff note and appends to audit trail', async () => {
    const updated = await repo.addInternalNote(
      'rep-uuid-001',
      'Traffic police called about worsening conditions.',
      'Ramesh Officer',
      'TRIAGE_OFFICER'
    );
    expect(updated.internalNotes).toBeDefined();
    expect(updated.internalNotes![0].content).toBe('Traffic police called about worsening conditions.');
    expect(updated.internalNotes![0].author).toBe('Ramesh Officer');
    expect(updated.auditTrail[0].action).toBe('Added internal operational note');
  });
});
