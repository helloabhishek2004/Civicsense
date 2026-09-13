import { env } from '@/core/config/env';
import { IIssueRepository } from './IIssueRepository';
import { MockIssueRepository } from './MockIssueRepository';
import { ApiIssueRepository } from './ApiIssueRepository';

function createIssueRepository(): IIssueRepository {
  if (env.isApi) {
    return new ApiIssueRepository();
  }
  return new MockIssueRepository();
}

export const issueRepository: IIssueRepository = createIssueRepository();
