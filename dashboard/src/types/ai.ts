import { BackendSeverityLevel, BackendPriorityLevel } from './models';

export type AIJobStatus = 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export type AIProcessingStage =
  | 'INTAKE_VALIDATION'
  | 'PREPROCESSING'
  | 'VISION_ANALYSIS'
  | 'TEXT_ANALYSIS'
  | 'FUSION'
  | 'DECISION'
  | 'HUMAN_REVIEW'
  | 'COMPLETED';

export interface AIJobEvent {
  id: string;
  job_id: string;
  report_id: string;
  stage: AIProcessingStage;
  status: 'STARTED' | 'COMPLETED' | 'FAILED';
  message: string;
  metadata_json?: Record<string, any>;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  created_at: string;
}

export interface AIJob {
  id: string;
  report_id: string;
  status: AIJobStatus;
  current_stage: AIProcessingStage;
  review_required: boolean;
  review_completed: boolean;
  review_reason?: string;
  queued_at: string;
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  error_code?: string;
  error_message?: string;
  attempt_count: number;
  execution_mode: string;
  processor_name: string;
  worker_id?: string;
  created_at: string;
  updated_at: string;
  events?: AIJobEvent[];
}

export interface AIJobListResult {
  items: AIJob[];
  total: number;
  page: number;
  page_size: number;
}

export interface VisionPrediction {
  category?: string;
  severity?: BackendSeverityLevel;
  confidence: number;
  has_image: boolean;
  features?: Record<string, any>;
}

export interface TextPrediction {
  category: string;
  severity: BackendSeverityLevel;
  confidence: number;
  matched_terms?: string[];
  urgency_signals?: string[];
}

export interface FusionMetrics {
  modality_agreement: number;
  category_agreement?: boolean;
  severity_agreement?: boolean;
  conflict_reasons?: string[];
}

export interface ReportAIAnalysis {
  id: string;
  report_id: string;
  predicted_category?: string;
  confidence?: number;
  severity?: BackendSeverityLevel;
  priority?: BackendPriorityLevel;
  evidence_agreement?: number;
  review_required?: boolean;
  analysis_metadata?: {
    processor_name?: string;
    execution_mode?: string;
    disclaimer?: string;
    vision_prediction?: VisionPrediction;
    text_prediction?: TextPrediction;
    fusion_metrics?: FusionMetrics;
    decision_rationale?: string;
    job_id?: string;
    processing_duration_ms?: number;
    [key: string]: any;
  };
  created_at: string;
}

export interface ReportAIResult {
  report_id: string;
  tracking_id: string;
  report_status: string;
  latest_job?: AIJob;
  ai_analysis?: ReportAIAnalysis;
  verification?: {
    id: string;
    reviewer_id?: string;
    decision: string;
    verified_category?: string;
    verified_severity?: BackendSeverityLevel;
    notes?: string;
    created_at: string;
  };
  execution_mode: string;
  processor_name: string;
  disclaimer: string;
}

export interface MetricItem<T> {
  value: T | null;
  sample_size: number;
  display_state: 'AVAILABLE' | 'INSUFFICIENT_DATA';
}

export interface AIMetrics {
  total_jobs: MetricItem<number>;
  completed_jobs: MetricItem<number>;
  failed_jobs: MetricItem<number>;
  active_jobs: MetricItem<number>;
  awaiting_human_review: MetricItem<number>;
  avg_processing_latency_ms: MetricItem<number>;
  low_confidence_rate: MetricItem<number>;
  modality_disagreement_rate: MetricItem<number>;
  human_override_rate: MetricItem<number>;
  time_window: string;
  generated_at: string;
}

export interface AIHealthStatus {
  status: 'available' | 'degraded' | 'offline';
  execution_mode: string;
  processor_mode: string;
  processor_name: string;
  production_model_available: boolean;
  background_worker_available: boolean;
  supported_stages: string[];
  active_jobs_count: number;
  total_jobs_processed: number;
  disclaimer?: string;
  last_processed_at?: string;
  timestamp: string;
}
