// Centralised API client for RiskShield backend
// Base URL is read from env, defaulting to localhost:8000

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  let attempt = 0;
  const maxAttempts = 2;

  const headers = new Headers(options?.headers);
  headers.set('Accept', 'application/json');
  if (API_KEY) {
    headers.set('X-API-Key', API_KEY);
  }

  while (attempt < maxAttempts) {
    try {
      const res = await fetch(url, {
        ...options,
        headers,
      });
      if (!res.ok) {
        const body = await res.text();
        throw new ApiError(res.status, body || res.statusText);
      }
      return res.json() as Promise<T>;
    } catch (err) {
      attempt++;
      if (attempt >= maxAttempts) throw err;
      await new Promise(r => setTimeout(r, 500));
    }
  }
  throw new Error('Request failed');
}

// ── Types ─────────────────────────────────────────────────────────────────────

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type Decision  = 'APPROVE' | 'REVIEW' | 'BLOCK';
export type TxStatus  = 'pending' | 'completed' | 'failed' | 'blocked';

export interface RiskSignal {
  name: string;
  value: number | string;
  severity: RiskLevel;
  explanation: string;
  evidence?: Record<string, unknown>;
}

export interface RiskEvaluation {
  id: string;
  score: number;
  risk_level: RiskLevel;
  decision: Decision;
  signals: RiskSignal[];
  created_at: string;
}

export interface Transaction {
  id: string;
  external_transaction_id: string;
  amount: number;
  currency: string;
  status: TxStatus;
  created_at: string;
  customer_id: string;
  merchant_id: string;
  payment_method: string | null;
  device_id: string | null;
  ip_address: string | null;
  city: string | null;
  country: string | null;
  latitude: number | null;
  longitude: number | null;
  risk_evaluation: RiskEvaluation | null;
}

export interface PagedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface InvestigationReport {
  executive_summary: string;
  primary_risk_factors: string[];
  supporting_evidence: string[];
  behavioral_comparison: string;
  recommended_investigation_action: string;
  confidence_statement: string;
}

export interface DashboardSummary {
  total_transactions: number;
  high_risk: number;
  blocked: number;
  review: number;
  risk_distribution: Record<RiskLevel, number>;
}

// ── API Calls ─────────────────────────────────────────────────────────────────

export const api = {
  /** Generic request wrapper — use when no dedicated method exists */
  request<T = unknown>(method: string, path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  /** List transactions with optional paging, search, filter, sort */
  getTransactions(params: {
    page?: number;
    size?: number;
    search?: string;
    risk_level?: string;
    decision?: string;
    sort?: string;
    order?: 'asc' | 'desc';
  } = {}): Promise<PagedResponse<Transaction>> {
    const q = new URLSearchParams();
    if (params.page)      q.set('page',       String(params.page));
    if (params.size)      q.set('size',       String(params.size));
    if (params.search)    q.set('search',     params.search);
    if (params.risk_level)q.set('risk_level', params.risk_level);
    if (params.decision)  q.set('decision',   params.decision);
    if (params.sort)      q.set('sort',       params.sort);
    if (params.order)     q.set('order',      params.order);
    return request<PagedResponse<Transaction>>(`/payments?${q}`);
  },

  getTransaction(id: string): Promise<Transaction> {
    return request<Transaction>(`/payments/${id}`);
  },

  investigate(id: string): Promise<InvestigationReport> {
    return request<InvestigationReport>(`/payments/${id}/investigate`);
  },

  getDashboardSummary(): Promise<DashboardSummary> {
    return request<DashboardSummary>('/payments/summary');
  },

  // ── Simulation ────────────────────────────────────────────────────────────

  getScenarios(): Promise<{ key: string; label: string }[]> {
    return request('/api/v1/simulation/scenarios');
  },

  triggerSimulation(config: {
    scenario: string;
    n_transactions: number;
    fraud_pct: number;
    seed: number;
    mode: string;
  }): Promise<{ run_id: string; status: string }> {
    return request('/api/v1/simulation/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
  },

  listSimulationRuns(): Promise<SimulationRun[]> {
    return request('/api/v1/simulation/runs');
  },

  getSimulationRun(id: string): Promise<SimulationRun> {
    return request(`/api/v1/simulation/runs/${id}`);
  },
};

// ── Simulation types ──────────────────────────────────────────────────────────

export interface ConfusionMatrix { tp: number; fp: number; tn: number; fn: number; }

export interface SimulationMetrics {
  n_transactions: number;
  n_fraud: number;
  n_legitimate: number;
  fraud_rate: number;
  confusion_matrix: ConfusionMatrix;
  precision: number;
  recall: number;
  f1: number;
  fpr: number;
  fnr: number;
  roc_auc: number;
  pr_auc: number;
  latency_ms: { avg: number; p50: number; p95: number; p99: number };
}

export interface SimulationRun {
  id: string;
  created_at: string;
  completed_at: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed';
  config: {
    scenario: string;
    n_transactions: number;
    fraud_pct: number;
    seed: number;
    mode: string;
  };
  metrics: SimulationMetrics | null;
  model_version: string | null;
  dataset_version: string | null;
  run_duration_s: number | null;
  error: string | null;
}
