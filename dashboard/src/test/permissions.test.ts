import { describe, it, expect } from 'vitest';
import { can } from '@/core/auth/permissions';
import { OfficerUser } from '@/core/auth/authTypes';

describe('Officer RBAC Permissions', () => {
  const superAdmin: OfficerUser = {
    id: 'off-admin',
    name: 'Super Admin',
    email: 'admin@civicsense.gov.in',
    badgeNumber: 'ADM-001',
    department: 'General Public Works',
    role: 'SUPER_ADMIN',
  };

  const triageOfficer: OfficerUser = {
    id: 'off-triage',
    name: 'Triage Officer',
    email: 'triage@civicsense.gov.in',
    badgeNumber: 'TRG-002',
    department: 'Roads & Bridges',
    role: 'TRIAGE_OFFICER',
  };

  const fieldInspector: OfficerUser = {
    id: 'off-field',
    name: 'Field Inspector',
    email: 'field@civicsense.gov.in',
    badgeNumber: 'FLD-003',
    department: 'Roads & Bridges',
    role: 'FIELD_INSPECTOR',
  };

  const departmentManager: OfficerUser = {
    id: 'off-dept',
    name: 'Department Manager',
    email: 'dept@civicsense.gov.in',
    badgeNumber: 'DPT-004',
    department: 'Roads & Bridges',
    role: 'DEPARTMENT_MANAGER',
  };

  it('allows Super Admin and Triage Officer to view citizen phone', () => {
    expect(can(superAdmin, 'view_citizen_phone')).toBe(true);
    expect(can(triageOfficer, 'view_citizen_phone')).toBe(true);
  });

  it('prohibits Field Inspector and Department Manager from viewing unmasked phone', () => {
    expect(can(fieldInspector, 'view_citizen_phone')).toBe(false);
    expect(can(departmentManager, 'view_citizen_phone')).toBe(false);
  });

  it('allows Super Admin and Triage Officer to review duplicate candidate matches', () => {
    expect(can(superAdmin, 'review_matches')).toBe(true);
    expect(can(triageOfficer, 'review_matches')).toBe(true);
    expect(can(fieldInspector, 'review_matches')).toBe(false);
    expect(can(departmentManager, 'review_matches')).toBe(false);
    expect(can(null, 'review_matches')).toBe(false);
  });

  it('handles null user safely', () => {
    expect(can(null, 'view_citizen_phone')).toBe(false);
  });
});
