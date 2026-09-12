import { describe, it, expect } from 'vitest';
import { BackendReportRead } from '@/types/api/backendContracts';
import { mapBackendToReportItem } from '@/services/repository/ApiReportRepository';

describe('ApiReportRepository Citizen Contact Mapping', () => {
  it('correctly maps citizen_name, citizen_phone, citizen_email, and citizen_postal_code', () => {
    const rawBackendReport: BackendReportRead = {
      id: 'rep-uuid-1',
      tracking_id: 'REP-202609-ABC123',
      status: 'SUBMITTED',
      citizen_id: 'citizen-99',
      citizen_name: 'CivicSense Test User',
      citizen_phone: '9874563210',
      citizen_email: 'civicsense.test@example.com',
      citizen_postal_code: '695001',
      latitude: 8.5241,
      longitude: 76.9366,
      address_hint: 'Palayam, Thiruvananthapuram',
      description: 'Dangerous pothole on main road',
      issue_id: null,
      evidences: [],
      ai_analyses: [],
      verifications: [],
      edge_metadata: null,
      created_at: '2026-09-12T13:40:00Z',
      updated_at: '2026-09-12T13:40:00Z',
    };

    const mapped = mapBackendToReportItem(rawBackendReport);

    expect(mapped.citizenName).toBe('CivicSense Test User');
    expect(mapped.citizenPhone).toBe('9874563210');
    expect(mapped.citizenEmail).toBe('civicsense.test@example.com');
    expect(mapped.citizenPostalCode).toBe('695001');
  });

  it('safely treats empty/null email and postal code as undefined for clean fallbacks', () => {
    const rawBackendReport: BackendReportRead = {
      id: 'rep-uuid-2',
      tracking_id: 'REP-202609-DEF456',
      status: 'SUBMITTED',
      citizen_id: null,
      citizen_name: null,
      citizen_phone: null,
      citizen_email: null,
      citizen_postal_code: null,
      latitude: 8.5241,
      longitude: 76.9366,
      address_hint: null,
      description: 'Water pipe leaking',
      issue_id: null,
      evidences: [],
      ai_analyses: [],
      verifications: [],
      edge_metadata: null,
      created_at: '2026-09-12T13:40:00Z',
      updated_at: '2026-09-12T13:40:00Z',
    };

    const mapped = mapBackendToReportItem(rawBackendReport);

    expect(mapped.citizenName).toBeUndefined();
    expect(mapped.citizenPhone).toBeUndefined();
    expect(mapped.citizenEmail).toBeUndefined();
    expect(mapped.citizenPostalCode).toBeUndefined();
  });

  it('correctly maps raw backend category and falls back to edge category_hint', () => {
    const reportWithCategory: BackendReportRead = {
      id: 'rep-uuid-3',
      tracking_id: 'REP-202609-CAT123',
      status: 'SUBMITTED',
      category: 'Road Damage',
      latitude: 8.5241,
      longitude: 76.9366,
      description: 'Pothole cluster on tarmac',
      evidences: [],
      ai_analyses: [],
      verifications: [],
      edge_metadata: null,
      created_at: '2026-09-12T13:40:00Z',
      updated_at: '2026-09-12T13:40:00Z',
    };

    const mapped1 = mapBackendToReportItem(reportWithCategory);
    expect(mapped1.category).toBe('Road Damage');
    expect(mapped1.department).toBe('Roads & Bridges');

    const reportWithEdgeCategoryHint: BackendReportRead = {
      id: 'rep-uuid-4',
      tracking_id: 'REP-202609-CAT456',
      status: 'SUBMITTED',
      category: null,
      latitude: 8.5241,
      longitude: 76.9366,
      description: 'Overflowing dumpster',
      evidences: [],
      ai_analyses: [],
      verifications: [],
      edge_metadata: {
        category_hint: 'Waste & Garbage',
      },
      created_at: '2026-09-12T13:40:00Z',
      updated_at: '2026-09-12T13:40:00Z',
    };

    const mapped2 = mapBackendToReportItem(reportWithEdgeCategoryHint);
    expect(mapped2.category).toBe('Garbage');
    expect(mapped2.department).toBe('Solid Waste Management');

    const reportWithInfrastructure: BackendReportRead = {
      id: 'rep-uuid-5',
      tracking_id: 'REP-202609-CAT789',
      status: 'SUBMITTED',
      category: 'Infrastructure',
      latitude: 8.5241,
      longitude: 76.9366,
      description: 'Damaged footbridge railing',
      evidences: [],
      ai_analyses: [],
      verifications: [],
      created_at: '2026-09-12T13:40:00Z',
      updated_at: '2026-09-12T13:40:00Z',
    };

    const mapped3 = mapBackendToReportItem(reportWithInfrastructure);
    expect(mapped3.category).toBe('Infrastructure');
    expect(mapped3.department).toBe('Town Planning & Enforcement');
  });
});
