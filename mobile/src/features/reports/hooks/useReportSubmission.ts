import { useState } from "react";
import { reportService } from "../services/reportService";
import { ReportItem, ReportSubmissionPayload } from "../types";
import { logger } from "../../../core/utils/logger";

interface UseReportSubmissionResult {
  loading: boolean;
  error: string | null;
  report: ReportItem | null;
  submit: (payload: ReportSubmissionPayload) => Promise<ReportItem | null>;
  reset: () => void;
}

export function useReportSubmission(): UseReportSubmissionResult {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ReportItem | null>(null);

  const submit = async (payload: ReportSubmissionPayload): Promise<ReportItem | null> => {
    setLoading(true);
    setError(null);
    try {
      logger.info("Submitting citizen report from mobile client...");
      const result = await reportService.submitReport(payload);
      setReport(result);
      logger.info(`Report submitted successfully! Tracking ID: ${result.tracking_id}`);
      return result;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit report";
      setError(msg);
      logger.error("Submission failed:", msg);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const reset = (): void => {
    setLoading(false);
    setError(null);
    setReport(null);
  };

  return { loading, error, report, submit, reset };
}
