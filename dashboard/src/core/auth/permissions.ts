import { OfficerUser, PermissionAction } from './authTypes';

const ROLE_PERMISSIONS: Record<OfficerUser['role'], readonly PermissionAction[]> = {
  SUPER_ADMIN: [
    'verify_report',
    'prioritize_report',
    'assign_department',
    'start_work',
    'resolve_report',
    'verify_resolution',
    'close_report',
    'manage_users',
    'export_data',
    'view_citizen_phone',
  ],
  TRIAGE_OFFICER: [
    'verify_report',
    'prioritize_report',
    'assign_department',
    'close_report',
    'export_data',
    'view_citizen_phone',
  ],
  DEPARTMENT_MANAGER: [
    'prioritize_report',
    'assign_department',
    'start_work',
    'resolve_report',
    'export_data',
  ],
  FIELD_INSPECTOR: [
    'start_work',
    'resolve_report',
    'verify_resolution',
  ],
};

/**
 * UI-only affordance check. Backend remains the authoritative permission validator.
 */
export function can(user: OfficerUser | null, action: PermissionAction): boolean {
  if (!user) return false;
  const permissions = ROLE_PERMISSIONS[user.role] || [];
  return permissions.includes(action);
}
