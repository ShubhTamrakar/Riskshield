'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AppLayout } from '@/components/AppLayout';
import { RiskBadge, DecisionBadge, ScoreDisplay, StatusBadge } from '@/components/Badges';
import { Spinner, ErrorBanner, EmptyState } from '@/components/States';
import { api, type DashboardSummary, type Transaction, type RiskLevel } from '@/lib/api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

const RISK_COLORS: Record<RiskLevel, string> = {
  LOW: '#16A34A', MEDIUM: '#D97706', HIGH: '#EA580C', CRITICAL: '#DC2626',
};

function fmt(n: number) {
  return new Intl.NumberFormat('en-US').format(n);
}

function fmtAmt(n: number, currency = 'USD') {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(n);
}

function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

// Dashboard summary derived from transactions
function buildSummary(txs: Transaction[], totalFromServer: number) {
  const dist: Record<RiskLevel, number> = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
  let high_risk = 0, blocked = 0, review = 0, approved = 0;
  let fraud_exposure = 0;

  const hourBuckets: Record<string, number> = {};
  txs.forEach(tx => {
    const lvl = tx.risk_evaluation?.risk_level;
    const dec = tx.risk_evaluation?.decision;
    if (lvl) dist[lvl] = (dist[lvl] ?? 0) + 1;
    
    if (dec === 'APPROVE') approved++;
    else if (dec === 'BLOCK') blocked++;
    else if (dec === 'REVIEW') review++;

    if (lvl === 'HIGH' || lvl === 'CRITICAL') {
      high_risk++;
      if (dec !== 'BLOCK') {
        fraud_exposure += tx.amount;
      }
    }

    // Build hourly chart data
    const h = new Date(tx.created_at).getHours();
    const key = `${h.toString().padStart(2,'0')}:00`;
    hourBuckets[key] = (hourBuckets[key] ?? 0) + 1;
  });

  const chartData = Object.entries(hourBuckets)
    .sort(([a],[b]) => a.localeCompare(b))
    .map(([time, count]) => ({ time, count }));

  const total = txs.length || 1; // avoid division by zero
  
  return {
    total_transactions: totalFromServer,
    high_risk,
    blocked,
    review,
    approved,
    approval_rate: (approved / total) * 100,
    review_rate: (review / total) * 100,
    blocked_rate: (blocked / total) * 100,
    fraud_exposure,
    risk_distribution: dist,
    chartData,
  };
}

export default function DashboardPage() {
  const router = useRouter();
  const [txs, setTxs] = useState<Transaction[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = () => {
      api.getTransactions({ size: 50 })
        .then(r => {
          setTxs(r.items);
          setTotal(r.total);
          setError(null);
        })
        .catch(e => setError(e.message))
        .finally(() => setLoading(false));
    };

    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  const summary = !loading && !error ? buildSummary(txs, total) : null;

  const recentAlerts = txs
    .filter(t => (t.risk_evaluation?.risk_level === 'HIGH' || t.risk_evaluation?.risk_level === 'CRITICAL'))
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 10);

  return (
    <AppLayout title="Dashboard">
      {loading && <Spinner />}
      {error  && <ErrorBanner message={`Failed to load dashboard data: ${error}`} />}

      {summary && (
        <>
          {/* Stat Cards */}
          <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
            {[
              { label: 'Transactions', value: fmt(summary.total_transactions), delta: 'Processed (All Time)' },
              { label: 'Approval Rate', value: `${summary.approval_rate.toFixed(1)}%`, delta: 'Total volume' },
              { label: 'Review Rate', value: `${summary.review_rate.toFixed(1)}%`, delta: 'Pending analyst review' },
              { label: 'Blocked', value: `${summary.blocked_rate.toFixed(1)}%`, delta: 'Intercepted threats' },
              { label: 'Fraud Exposure', value: fmtAmt(summary.fraud_exposure), delta: 'At-risk approved volume' },
            ].map(s => (
              <div key={s.label} className="stat-card">
                <div className="stat-label">{s.label}</div>
                <div className="stat-value">{s.value}</div>
                <div className="stat-delta">{s.delta}</div>
              </div>
            ))}
          </div>

          <div className="dashboard-bottom">
            {/* Transaction Volume Chart */}
            <div>
              <div className="card" style={{ marginBottom: 20 }}>
                <div className="card-header">
                  <div>
                    <div className="card-title">Transaction Volume</div>
                    <div className="card-subtitle">Transactions by hour</div>
                  </div>
                </div>
                <div className="card-body">
                  {summary.chartData.length === 0 ? (
                    <EmptyState title="No chart data" desc="Transactions will appear here." />
                  ) : (
                    <div className="chart-container">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={summary.chartData} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                          <XAxis dataKey="time" tick={{ fontSize: 11, fill: 'var(--color-text-3)' }} />
                          <YAxis tick={{ fontSize: 11, fill: 'var(--color-text-3)' }} />
                          <Tooltip
                            contentStyle={{ fontSize: 12, border: '1px solid var(--color-border)', borderRadius: 6, boxShadow: 'var(--shadow-md)' }}
                          />
                          <Line type="monotone" dataKey="count" stroke="var(--color-accent)" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>
              </div>

              {/* Risk Distribution */}
              <div className="card">
                <div className="card-header">
                  <div className="card-title">Risk Distribution</div>
                </div>
                <div className="card-body">
                  <div className="risk-dist-grid">
                    {(['LOW','MEDIUM','HIGH','CRITICAL'] as RiskLevel[]).map(lvl => (
                      <div key={lvl} className="risk-dist-item">
                        <div className="risk-dist-count" style={{ color: RISK_COLORS[lvl] }}>{fmt(summary.risk_distribution[lvl])}</div>
                        <div className="risk-dist-label" style={{ color: RISK_COLORS[lvl] }}>{lvl}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Alerts */}
            <div className="card">
              <div className="card-header">
                <div>
                  <div className="card-title">Recent Risk Alerts</div>
                  <div className="card-subtitle">Actionable high-risk events</div>
                </div>
              </div>
              <div className="card-body" style={{ padding: '8px 16px' }}>
                {recentAlerts.length === 0 ? (
                  <EmptyState title="No active risk alerts" desc="High-risk transactions will appear here." />
                ) : (
                  recentAlerts.map(tx => (
                    <div
                      key={tx.id}
                      className="alert-row"
                      onClick={() => router.push(`/transactions/${tx.id}`)}
                      style={{ cursor: 'pointer' }}
                    >
                      <div
                        className="alert-dot"
                        style={{ background: RISK_COLORS[tx.risk_evaluation?.risk_level ?? 'LOW'] }}
                      />
                      <div className="alert-meta">
                        <div className="alert-desc" style={{ fontWeight: 600 }}>{tx.risk_evaluation?.signals?.[0]?.name || 'Unusual Transaction Anomaly'}</div>
                        <div className="alert-time">Merchant: merch_{tx.merchant_id.slice(0, 4)}... · {fmtTime(tx.created_at)}</div>
                      </div>
                      <div className="alert-amount">{fmtAmt(tx.amount, tx.currency)}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </AppLayout>
  );
}
