import { DepartmentName } from '@/types/models';

export type UserRole =
  | 'TRIAGE_OFFICER'
  | 'DEPARTMENT_MANAGER'
  | 'FIELD_INSPECTOR'
  | 'SUPER_ADMIN';

export interface OfficerUser {
  id: string;
  name: string;
  email: string;
  badgeNumber: string;
  department: DepartmentName;
  role: UserRole;
  avatarUrl?: string;
}

export type PermissionAction =
  | 'verify_report'
  | 'prioritize_report'
  | 'assign_department'
  | 'start_work'
  | 'resolve_report'
  | 'verify_resolution'
  | 'close_report'
  | 'manage_users'
  | 'export_data'
  | 'view_citizen_phone'
  | 'review_matches';
