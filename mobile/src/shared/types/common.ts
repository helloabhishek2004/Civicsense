export type ReportStatus =
  | "SUBMITTED"
  | "AI_PROCESSING"
  | "AI_PROCESSED"
  | "VERIFICATION_REQUIRED"
  | "VERIFIED"
  | "PRIORITIZED"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "RESOLVED"
  | "RESOLUTION_VERIFIED"
  | "CLOSED";

export type EvidenceType = "IMAGE" | "TEXT" | "METADATA";

export interface LocationCoords {
  latitude: number;
  longitude: number;
  accuracyMeters?: number;
  addressHint?: string;
}

export interface EvidenceItem {
  evidence_type: EvidenceType;
  storage_uri: string;
  file_hash?: string;
  mime_type?: string;
  file_size_bytes?: number;
  metadata_json?: Record<string, unknown>;
}
