import {
  BackendDepartmentRead,
  BackendDepartmentWorkloadStats,
  BackendReportListResponse,
} from '@/types/api/backendContracts';
import { ReportListResult } from '@/types/models';
import { apiClient } from '../api/apiClient';
import { ENDPOINTS } from '../api/endpoints';
import { mapBackendToReportItem } from './ApiReportRepository';

export interface IDepartmentRepository {
  getDepartments(activeOnly?: boolean): Promise<BackendDepartmentRead[]>;
  getDepartmentById(identifier: string): Promise<BackendDepartmentRead>;
  getDepartmentStats(identifier: string): Promise<BackendDepartmentWorkloadStats>;
  getDepartmentReports(
    identifier: string,
    params?: { status?: string; priority?: string; page?: number; pageSize?: number }
  ): Promise<ReportListResult>;
}

export class DepartmentRepository implements IDepartmentRepository {
  async getDepartments(activeOnly = true): Promise<BackendDepartmentRead[]> {
    return apiClient.get<BackendDepartmentRead[]>(ENDPOINTS.DEPARTMENTS, {
      params: { active_only: activeOnly },
    });
  }

  async getDepartmentById(identifier: string): Promise<BackendDepartmentRead> {
    return apiClient.get<BackendDepartmentRead>(ENDPOINTS.DEPARTMENT_BY_ID(identifier));
  }

  async getDepartmentStats(identifier: string): Promise<BackendDepartmentWorkloadStats> {
    return apiClient.get<BackendDepartmentWorkloadStats>(
      ENDPOINTS.DEPARTMENT_STATS(identifier)
    );
  }

  async getDepartmentReports(
    identifier: string,
    params: { status?: string; priority?: string; page?: number; pageSize?: number } = {}
  ): Promise<ReportListResult> {
    const queryParams: Record<string, string | number | undefined> = {
      page: params.page || 1,
      page_size: params.pageSize || 10,
    };
    if (params.status) queryParams.status = params.status;
    if (params.priority) queryParams.priority = params.priority;

    const response = await apiClient.get<BackendReportListResponse>(
      ENDPOINTS.DEPARTMENT_REPORTS(identifier),
      { params: queryParams }
    );

    const items = (response.items || []).map(mapBackendToReportItem);
    const total = response.total;
    const page = response.page;
    const pageSize = response.page_size;
    const totalPages = Math.ceil(total / pageSize) || 1;

    return {
      items,
      total,
      page,
      pageSize,
      totalPages,
    };
  }
}

export const departmentRepository = new DepartmentRepository();
