'use client';
import { useEffect, useState, useCallback, useRef } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { Spinner, ErrorBanner, EmptyState } from '@/components/States';
import { api, type SimulationRun, type SimulationMetrics } from '@/lib/api';

// ── Helpers ───────────────────────────────────────────────────────────────────
const pct = (n?: number) => n != null ? `${(n * 100).toFixed(1)}%` : '—';
const num = (n?: number, d = 3) => n != null ? n.toFixed(d) : '—';
const ms  = (n?: number) => n != null ? `${n.toFixed(1)} ms` : '—';

const STATUS_COLORS: Record<string, string> = {
  pending:   'var(--color-text-3)',
  running:   'var(--color-medium)',
  completed: 'var(--color-low)',
  failed:    'var(--color-critical)',
};

const MODE_LABELS: Record<string, string> = {
  rules_only: 'Rules Only',
  ml_only:    'ML Only',
  rules_ml:   'Rules + ML',
  full:       'Rules + ML + Behavioral',
};

// ── Confusion Matrix ──────────────────────────────────────────────────────────
function ConfusionMatrix({ cm }: { cm: SimulationMetrics['confusion_matrix'] }) {
  const cells = [
    { label: 'TP', val: cm.tp, bg: '#F0FDF4', color: '#16A34A', desc: 'True Positive' },
    { label: 'FP', val: cm.fp, bg: '#FFF1F2', color: '#DC2626', desc: 'False Positive' },
    { label: 'FN', val: cm.fn, bg: '#FFF7ED', color: '#EA580C', desc: 'False Negative' },
    { label: 'TN', val: cm.tn, bg: '#F0FDF4', color: '#16A34A', desc: 'True Negative' },
  ];
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
        {cells.map(c => (
          <div key={c.label} style={{ background: c.bg, border: `1px solid ${c.color}30`, borderRadius: 6, padding: '12px 16px', textAlign: 'center' }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: c.color, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4 }}>{c.label} — {c.desc}</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: c.color, letterSpacing: '-1px' }}>{c.val}</div>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11, color: 'var(--color-text-3)', textAlign: 'center' }}>
        Fraud predicted as fraud (TP) · Legitimate predicted as fraud (FP) · Fraud predicted as legitimate (FN) · Legitimate as legitimate (TN)
      </div>
    </div>
  );
}

// ── Metric Row ────────────────────────────────────────────────────────────────
function MetricRow({ label, value, desc, color }: { label: string; value: string; desc?: string; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--color-border)' }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text)' }}>{label}</div>
        {desc && <div style={{ fontSize: 11, color: 'var(--color-text-3)', marginTop: 1 }}>{desc}</div>}
      </div>
      <div style={{ fontSize: 15, fontWeight: 700, fontVariantNumeric: 'tabular-nums', color: color ?? 'var(--color-text)' }}>{value}</div>
    </div>
  );
}

// ── Results Panel ─────────────────────────────────────────────────────────────
function ResultsPanel({ run }: { run: SimulationRun }) {
  const m = run.metrics;
  if (!m) return null;

  const getF1Color = (f: number) => f >= 0.7 ? 'var(--color-low)' : f >= 0.4 ? 'var(--color-medium)' : 'var(--color-critical)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Core metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {[
          { label: 'Precision', value: pct(m.precision), color: m.precision >= 0.7 ? 'var(--color-low)' : 'var(--color-medium)' },
          { label: 'Recall',    value: pct(m.recall),    color: m.recall >= 0.7    ? 'var(--color-low)' : 'var(--color-medium)' },
          { label: 'F1 Score',  value: num(m.f1),        color: getF1Color(m.f1) },
          { label: 'ROC-AUC',   value: num(m.roc_auc),   color: m.roc_auc >= 0.7 ? 'var(--color-low)' : 'var(--color-medium)' },
        ].map(s => (
          <div key={s.label} className="stat-card">
            <div className="stat-label">{s.label}</div>
            <div className="stat-value" style={{ fontSize: 20, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Error rates + PR-AUC */}
        <div className="card">
          <div className="card-header"><div className="card-title">Detection Quality</div></div>
          <div className="card-body" style={{ padding: '0 20px' }}>
            <MetricRow label="False Positive Rate" value={pct(m.fpr)} desc="Legitimate flagged as fraud" color={m.fpr < 0.1 ? 'var(--color-low)' : 'var(--color-high)'} />
            <MetricRow label="False Negative Rate" value={pct(m.fnr)} desc="Fraud missed by engine" color={m.fnr < 0.2 ? 'var(--color-low)' : 'var(--color-critical)'} />
            <MetricRow label="PR-AUC"              value={num(m.pr_auc)} desc="Precision-Recall AUC" color="var(--color-accent)" />
            <MetricRow label="Fraud Rate in Dataset" value={pct(m.fraud_rate)} desc={`${m.n_fraud} fraud / ${m.n_transactions} total`} />
          </div>
        </div>

        {/* Latency */}
        <div className="card">
          <div className="card-header"><div className="card-title">Engine Latency</div></div>
          <div className="card-body" style={{ padding: '0 20px' }}>
            <MetricRow label="Average" value={ms(m.latency_ms.avg)} />
            <MetricRow label="P50 (Median)" value={ms(m.latency_ms.p50)} />
            <MetricRow label="P95" value={ms(m.latency_ms.p95)} color={m.latency_ms.p95 > 200 ? 'var(--color-high)' : undefined} />
            <MetricRow label="P99" value={ms(m.latency_ms.p99)} color={m.latency_ms.p99 > 500 ? 'var(--color-critical)' : undefined} />
          </div>
        </div>
      </div>

      {/* Confusion matrix */}
      <div className="card">
        <div className="card-header"><div className="card-title">Confusion Matrix</div></div>
        <div className="card-body"><ConfusionMatrix cm={m.confusion_matrix} /></div>
      </div>

      {/* Run metadata */}
      <div className="card">
        <div className="card-header"><div className="card-title">Run Metadata</div></div>
        <div className="card-body">
          <div className="detail-grid">
            <div className="detail-field"><div className="detail-label">Model Version</div><div className="detail-value mono">{run.model_version ?? '—'}</div></div>
            <div className="detail-field"><div className="detail-label">Dataset Version</div><div className="detail-value mono">{run.dataset_version ?? '—'}</div></div>
            <div className="detail-field"><div className="detail-label">Engine Mode</div><div className="detail-value">{MODE_LABELS[run.config.mode] ?? run.config.mode}</div></div>
            <div className="detail-field"><div className="detail-label">Wall Time</div><div className="detail-value">{run.run_duration_s?.toFixed(2)}s</div></div>
            <div className="detail-field"><div className="detail-label">Transactions</div><div className="detail-value">{run.config.n_transactions}</div></div>
            <div className="detail-field"><div className="detail-label">Random Seed</div><div className="detail-value mono">{run.config.seed}</div></div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function SimulationPage() {
  const [scenarios, setScenarios] = useState<{ key: string; label: string }[]>([]);
  const [runs, setRuns] = useState<SimulationRun[]>([]);
  const [activeRun, setActiveRun] = useState<SimulationRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Config state
  const [scenario, setScenario] = useState('mixed_fraud');
  const [nTransactions, setNTransactions] = useState(50);
  const [fraudPct, setFraudPct] = useState(0.20);
  const [seed, setSeed] = useState(42);
  const [mode, setMode] = useState('full');

  // Load scenarios + run history on mount
  useEffect(() => {
    api.getScenarios().then(setScenarios).catch(() => {});
    refreshRuns();
  }, []);

  const refreshRuns = useCallback(() => {
    api.listSimulationRuns().then(setRuns).catch(() => {});
  }, []);

  // Poll active run until complete
  const pollRun = useCallback((runId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const r = await api.getSimulationRun(runId);
        setActiveRun(r);
        if (r.status === 'completed' || r.status === 'failed') {
          clearInterval(pollRef.current!);
          setLoading(false);
          refreshRuns();
        }
      } catch {}
    }, 1500);
  }, [refreshRuns]);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  async function handleRun(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setActiveRun(null);
    try {
      const { run_id } = await api.triggerSimulation({
        scenario, n_transactions: nTransactions, fraud_pct: fraudPct, seed, mode,
      });
      pollRun(run_id);
    } catch (err: any) {
      setError(err.message ?? 'Failed to trigger simulation');
      setLoading(false);
    }
  }

  const scenarioLabel = scenarios.find(s => s.key === scenario)?.label ?? scenario;

  return (
    <AppLayout title="Simulation Lab">
      {/* ── SIMULATION RESULT BANNER ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        background: '#FFF7ED', border: '1px solid #FED7AA',
        borderRadius: 6, padding: '10px 16px', marginBottom: 20, fontSize: 13,
      }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#EA580C" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        <span style={{ fontWeight: 700, color: '#EA580C' }}>SIMULATION ENVIRONMENT</span>
        <span style={{ color: '#92400E' }}>
          — Results are produced from synthetic data with known ground-truth labels. These are NOT live production metrics.
          The production risk engine is used without modification.
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 24, alignItems: 'start' }}>
        {/* ── Config Panel ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="card-header"><div className="card-title">Simulation Controls</div></div>
            <div className="card-body">
              <form onSubmit={handleRun} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {/* Scenario */}
                <div className="detail-field">
                  <label className="detail-label" htmlFor="scenario-select">Scenario</label>
                  <select
                    id="scenario-select"
                    className="filter-select"
                    style={{ width: '100%', marginTop: 4 }}
                    value={scenario}
                    onChange={e => setScenario(e.target.value)}
                  >
                    {scenarios.map(s => (
                      <option key={s.key} value={s.key}>{s.label}</option>
                    ))}
                  </select>
                </div>

                {/* Engine mode */}
                <div className="detail-field">
                  <label className="detail-label" htmlFor="mode-select">Engine Mode</label>
                  <select
                    id="mode-select"
                    className="filter-select"
                    style={{ width: '100%', marginTop: 4 }}
                    value={mode}
                    onChange={e => setMode(e.target.value)}
                  >
                    <option value="rules_only">Rules Only</option>
                    <option value="ml_only">ML Only</option>
                    <option value="rules_ml">Rules + ML</option>
                    <option value="full">Rules + ML + Behavioral (Full)</option>
                  </select>
                </div>

                {/* N transactions */}
                <div className="detail-field">
                  <label className="detail-label" htmlFor="n-slider">
                    Transactions: <strong>{nTransactions}</strong>
                  </label>
                  <input
                    id="n-slider" type="range" min={10} max={500} step={10}
                    value={nTransactions}
                    onChange={e => setNTransactions(Number(e.target.value))}
                    style={{ width: '100%', marginTop: 4, accentColor: 'var(--color-accent)' }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--color-text-3)' }}>
                    <span>10</span><span>500</span>
                  </div>
                </div>

                {/* Fraud pct */}
                <div className="detail-field">
                  <label className="detail-label" htmlFor="fraud-slider">
                    Fraud Percentage: <strong>{(fraudPct * 100).toFixed(0)}%</strong>
                  </label>
                  <input
                    id="fraud-slider" type="range" min={1} max={80} step={1}
                    value={Math.round(fraudPct * 100)}
                    onChange={e => setFraudPct(Number(e.target.value) / 100)}
                    style={{ width: '100%', marginTop: 4, accentColor: 'var(--color-critical)' }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--color-text-3)' }}>
                    <span>1%</span><span>80%</span>
                  </div>
                </div>

                {/* Seed */}
                <div className="detail-field">
                  <label className="detail-label" htmlFor="seed-input">Random Seed</label>
                  <input
                    id="seed-input" type="number" min={0} max={99999}
                    value={seed}
                    onChange={e => setSeed(Number(e.target.value))}
                    className="search-input"
                    style={{ width: '100%', marginTop: 4, paddingLeft: 10 }}
                  />
                </div>

                {error && <ErrorBanner message={error} />}

                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ justifyContent: 'center' }}
                  disabled={loading || scenarios.length === 0}
                >
                  {loading ? (
                    <>
                      <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                      Running…
                    </>
                  ) : '▶ Run Simulation'}
                </button>
              </form>
            </div>
          </div>

          {/* Quick scenario descriptions */}
          <div className="card">
            <div className="card-header"><div className="card-title">Scenario Guide</div></div>
            <div className="card-body" style={{ padding: '0 20px 8px' }}>
              {[
                ['Normal Traffic',     'Baseline with natural fraud rate'],
                ['High-Value Anomaly', 'Fraud via 10–25× amount spikes'],
                ['Velocity Attack',    'Rapid burst from small customer pool'],
                ['Account Takeover',   'New device + geo shift + high amount'],
                ['Card Testing',       'Many micro-transactions to verify card'],
                ['Device Network',     'Single device shared across customers'],
                ['Location Anomaly',   'Transactions from high-risk geographies'],
                ['Mixed Fraud',        'Blend of all scenarios'],
              ].map(([name, desc]) => (
                <div key={name} style={{ padding: '8px 0', borderBottom: '1px solid var(--color-border)' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text)' }}>{name}</div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-3)', marginTop: 2 }}>{desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Results Panel ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Active run status */}
          {activeRun && (
            <>
              {/* Status card */}
              <div className="card">
                <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  {(activeRun.status === 'pending' || activeRun.status === 'running') && (
                    <div className="spinner" />
                  )}
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text)' }}>
                      {activeRun.status === 'pending'   && 'Queued — waiting to start…'}
                      {activeRun.status === 'running'   && `Running ${scenarioLabel} scenario…`}
                      {activeRun.status === 'completed' && `✓ Completed in ${activeRun.run_duration_s?.toFixed(2)}s`}
                      {activeRun.status === 'failed'    && '✕ Run failed'}
                    </div>
                    
                    {activeRun.status === 'running' && (activeRun.metrics as any)?.progress && (
                      <div style={{ marginTop: 12, width: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--color-text-2)', marginBottom: 4, fontWeight: 500 }}>
                          <span>{(activeRun.metrics as any).progress.completed} / {(activeRun.metrics as any).progress.total} evaluated</span>
                          <span style={{ color: 'var(--color-medium)' }}>ETA: {(activeRun.metrics as any).progress.estimated_time_remaining_s.toFixed(1)}s</span>
                        </div>
                        <div style={{ width: '100%', height: 6, background: 'var(--color-border)', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ 
                            width: `${((activeRun.metrics as any).progress.completed / Math.max(1, (activeRun.metrics as any).progress.total)) * 100}%`,
                            height: '100%', 
                            background: 'var(--color-accent)',
                            transition: 'width 0.5s ease-out'
                          }} />
                        </div>
                      </div>
                    )}

                    <div style={{ fontSize: 11, color: 'var(--color-text-3)', marginTop: 8 }}>
                      Run ID: <span style={{ fontFamily: 'var(--font-mono)' }}>{activeRun.id.slice(-12)}</span>
                      {' · '}Mode: {MODE_LABELS[activeRun.config.mode]}
                      {' · '}{activeRun.config.n_transactions} transactions
                      {' · '}{(activeRun.config.fraud_pct * 100).toFixed(0)}% fraud
                    </div>
                  </div>
                  <div style={{ marginLeft: 'auto', alignSelf: 'flex-start' }}>
                    <span className={`badge ${
                      activeRun.status === 'completed' ? 'badge-low' :
                      activeRun.status === 'failed'    ? 'badge-critical' : 'badge-medium'
                    }`}>{activeRun.status.toUpperCase()}</span>
                  </div>
                </div>
                {activeRun.error && (
                  <div style={{ padding: '0 20px 16px' }}>
                    <ErrorBanner message={activeRun.error} />
                  </div>
                )}
              </div>

              {activeRun.status === 'completed' && activeRun.metrics && (
                <ResultsPanel run={activeRun} />
              )}
            </>
          )}

          {!activeRun && !loading && (
            <div className="card">
              <div className="card-body">
                <EmptyState
                  title="No simulation running"
                  desc="Configure a scenario on the left and click Run Simulation to see results."
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Run History ── */}
      <div className="card" style={{ marginTop: 28 }}>
        <div className="card-header">
          <div>
            <div className="card-title">Simulation Run History</div>
            <div className="card-subtitle">Click a row to load results</div>
          </div>
          <button className="btn btn-secondary" onClick={refreshRuns}>Refresh</button>
        </div>
        {runs.length === 0 ? (
          <EmptyState title="No runs yet" desc="Completed simulation runs will appear here." />
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Scenario</th>
                  <th>Mode</th>
                  <th>N</th>
                  <th>Fraud %</th>
                  <th>Status</th>
                  <th>F1</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>ROC-AUC</th>
                  <th>Duration</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {runs.map(r => (
                  <tr
                    key={r.id}
                    onClick={() => setActiveRun(r)}
                    style={{ cursor: 'pointer', background: activeRun?.id === r.id ? 'var(--color-accent-bg)' : undefined }}
                  >
                    <td><span className="tx-id">{r.id.slice(-10)}</span></td>
                    <td>{scenarios.find(s => s.key === r.config.scenario)?.label ?? r.config.scenario}</td>
                    <td style={{ fontSize: 11, color: 'var(--color-text-2)' }}>{MODE_LABELS[r.config.mode] ?? r.config.mode}</td>
                    <td>{r.config.n_transactions}</td>
                    <td>{(r.config.fraud_pct * 100).toFixed(0)}%</td>
                    <td>
                      <span className={`badge ${
                        r.status === 'completed' ? 'badge-low' :
                        r.status === 'failed'    ? 'badge-critical' : 'badge-medium'
                      }`}>{r.status}</span>
                    </td>
                    <td style={{ fontWeight: 600, color: r.metrics?.f1 != null ? (r.metrics.f1 >= 0.5 ? 'var(--color-low)' : 'var(--color-high)') : undefined }}>
                      {num(r.metrics?.f1)}
                    </td>
                    <td>{pct(r.metrics?.precision)}</td>
                    <td>{pct(r.metrics?.recall)}</td>
                    <td>{num(r.metrics?.roc_auc)}</td>
                    <td style={{ color: 'var(--color-text-2)' }}>{r.run_duration_s ? `${r.run_duration_s.toFixed(2)}s` : '—'}</td>
                    <td style={{ color: 'var(--color-text-3)', whiteSpace: 'nowrap', fontSize: 12 }}>
                      {new Date(r.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
