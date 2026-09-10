import { EvidenceItem, ReportStatus } from "../../../shared/types/common";

export interface ReportSubmissionPayload {
  location: {
    latitude: number;
    longitude: number;
    address_hint?: string;
  };
  description: string;
  citizen_id?: string;
  evidence?: EvidenceItem[];
  client_report_id?: string;
}

export interface ReportItem {
  id: string;
  tracking_id: string;
  status: ReportStatus;
  citizen_id?: string;
  latitude: number;
  longitude: number;
  address_hint?: string;
  description: string;
  issue_id?: string;
  evidences: EvidenceItem[];
  created_at: string;
  updated_at: string;
}

export interface ReportListResult {
  items: ReportItem[];
  total: number;
  page: number;
  page_size: number;
}
