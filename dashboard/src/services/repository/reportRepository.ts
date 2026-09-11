import { env } from '@/core/config/env';
import { IReportRepository } from './IReportRepository';
import { MockReportRepository } from './MockReportRepository';
import { ApiReportRepository } from './ApiReportRepository';

function createReportRepository(): IReportRepository {
  if (env.isApi) {
    return new ApiReportRepository();
  }
  return new MockReportRepository();
}

export const reportRepository: IReportRepository = createReportRepository();
