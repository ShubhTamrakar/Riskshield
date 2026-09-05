'use client';
import { useEffect, useState } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { Spinner, ErrorBanner } from '@/components/States';
import { api, type Transaction } from '@/lib/api';
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface ModelMetrics {
  total: number;
  precision: number;
  recall: number;
  f1: number;
  blocked_pct: number;
  review_pct: number;
  approve_pct: number;
  decision_dist: { name: string; value: number }[];
  risk_dist: { name: string; value: number }[];
}

export default function ModelPage() {
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getTransactions({ size: 200 })
      .then(r => {
        const txs = r.items;
        let blocked = 0, review = 0, approve = 0;
        const riskCounts = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
        txs.forEach(tx => {
          const dec = tx.risk_evaluation?.decision;
          const lvl = tx.risk_evaluation?.risk_level;
          if (dec === 'BLOCK')    blocked++;
          if (dec === 'REVIEW')   review++;
          if (dec === 'APPROVE')  approve++;
          if (lvl) riskCounts[lvl] = (riskCounts[lvl] ?? 0) + 1;
        });
        const n = txs.length || 1;
        setMetrics({
          total: n,
          precision: 0, recall: 0, f1: 0,  // would come from metrics endpoint
          blocked_pct: (blocked / n) * 100,
          review_pct:  (review  / n) * 100,
          approve_pct: (approve / n) * 100,
          decision_dist: [
            { name: 'Approve', value: approve },
            { name: 'Review',  value: review  },
            { name: 'Block',   value: blocked },
          ],
          risk_dist: Object.entries(riskCounts).map(([name, value]) => ({ name, value })),
        });
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const pct = (n: number) => `${n.toFixed(1)}%`;

  return (
    <AppLayout title="Model Performance">
      <div className="page-header">
        <div>
          <div className="page-title">Model Performance</div>
          <div className="page-desc">Risk engine decision and ML model statistics</div>
        </div>
      </div>

      {loading ? <Spinner /> : error ? <ErrorBanner message={error} /> : metrics && (
        <>
          {/* Stat cards */}
          <div className="stats-grid" style={{ marginBottom: 24 }}>
            {[
              { label: 'Total Evaluated',   value: metrics.total.toLocaleString() },
              { label: 'Block Rate',         value: pct(metrics.blocked_pct), accent: 'var(--color-critical)' },
              { label: 'Review Rate',        value: pct(metrics.review_pct),  accent: 'var(--color-medium)' },
              { label: 'Approve Rate',       value: pct(metrics.approve_pct), accent: 'var(--color-low)' },
            ].map(s => (
              <div key={s.label} className="stat-card">
                <div className="stat-label">{s.label}</div>
                <div className="stat-value" style={{ color: s.accent }}>{s.value}</div>
              </div>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            {/* Decision distribution */}
            <div className="card">
              <div className="card-header"><div className="card-title">Decision Distribution</div></div>
              <div className="card-body">
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={metrics.decision_dist}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                      <XAxis dataKey="name" tick={{ fontSize: 12, fill: 'var(--color-text-2)' }} />
                      <YAxis tick={{ fontSize: 12, fill: 'var(--color-text-3)' }} />
                      <Tooltip contentStyle={{ fontSize: 12, borderRadius: 6 }} />
                      <Bar dataKey="value" fill="var(--color-accent)" radius={[3,3,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Risk level distribution */}
            <div className="card">
              <div className="card-header"><div className="card-title">Risk Level Distribution</div></div>
              <div className="card-body">
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={metrics.risk_dist}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                      <XAxis dataKey="name" tick={{ fontSize: 12, fill: 'var(--color-text-2)' }} />
                      <YAxis tick={{ fontSize: 12, fill: 'var(--color-text-3)' }} />
                      <Tooltip contentStyle={{ fontSize: 12, borderRadius: 6 }} />
                      <Bar dataKey="value" radius={[3,3,0,0]}>
                        {
                          metrics.risk_dist.map((entry, index) => {
                            const colors: any = { LOW: 'var(--color-low)', MEDIUM: 'var(--color-medium)', HIGH: 'var(--color-high)', CRITICAL: 'var(--color-critical)' };
                            return <Cell key={`cell-${index}`} fill={colors[entry.name] || '#475569'} />;
                          })
                        }
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: 24 }}>
            <div className="card-header">
              <div>
                <div className="card-title">ML Model Info</div>
                <div className="card-subtitle">XGBoost v1 — trained on synthetic dataset</div>
              </div>
            </div>
            <div className="card-body">
              <div className="detail-grid">
                <div className="detail-field"><div className="detail-label">Model</div><div className="detail-value">XGBoost Classifier</div></div>
                <div className="detail-field"><div className="detail-label">Serialized</div><div className="detail-value mono">models/fraud_model_v1.joblib</div></div>
                <div className="detail-field"><div className="detail-label">Training Set</div><div className="detail-value">80% chronological split</div></div>
                <div className="detail-field"><div className="detail-label">Test Set</div><div className="detail-value">20% holdout (temporal)</div></div>
                <div className="detail-field"><div className="detail-label">Baseline PR-AUC</div><div className="detail-value" style={{ color: 'var(--color-low)' }}>0.716</div></div>
                <div className="detail-field"><div className="detail-label">Baseline ROC-AUC</div><div className="detail-value" style={{ color: 'var(--color-low)' }}>0.844</div></div>
              </div>
            </div>
          </div>
        </>
      )}
    </AppLayout>
  );
}
