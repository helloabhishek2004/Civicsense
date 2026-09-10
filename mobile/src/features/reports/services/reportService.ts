import { apiClient } from "../../../core/api/client";
import { ENDPOINTS } from "../../../core/api/endpoints";
import { ReportItem, ReportListResult, ReportSubmissionPayload } from "../types";

export const reportService = {
  /**
   * Submit a new citizen civic defect report to the backend.
   */
  async submitReport(payload: ReportSubmissionPayload): Promise<ReportItem> {
    return apiClient.post<ReportItem>(ENDPOINTS.REPORTS, payload);
  },

  /**
   * Retrieve report by UUID or tracking ID.
   */
  async getReport(identifier: string): Promise<ReportItem> {
    return apiClient.get<ReportItem>(ENDPOINTS.REPORT_BY_ID(identifier));
  },

  /**
   * Fetch paginated list of reports.
   */
  async listReports(page: number = 1, pageSize: number = 20): Promise<ReportListResult> {
    return apiClient.get<ReportListResult>(
      `${ENDPOINTS.REPORTS}?page=${page}&page_size=${pageSize}`
    );
  },
};
