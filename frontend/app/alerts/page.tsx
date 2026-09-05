'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AppLayout } from '@/components/AppLayout';
import { RiskBadge, DecisionBadge, ScoreDisplay } from '@/components/Badges';
import { Spinner, ErrorBanner, EmptyState } from '@/components/States';
import { api, type Transaction } from '@/lib/api';

function fmtAmt(n: number, currency = 'USD') {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(n);
}
function fmtDate(iso: string) {
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function AlertsPage() {
  const router = useRouter();
  const [txs, setTxs] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'REVIEW' | 'BLOCK' | ''>('');

  useEffect(() => {
    // Fetch actionable alerts (Review queue or Blocked)
    api.getTransactions({ size: 100, decision: filter || undefined, order: 'desc', sort: 'created_at' })
      .then(r => setTxs(r.items.filter(t => t.risk_evaluation?.risk_level === 'HIGH' || t.risk_evaluation?.risk_level === 'CRITICAL')))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [filter]);

  return (
    <AppLayout title="Risk Alerts">
      <div className="page-header">
        <div>
          <div className="page-title">Risk Alerts Queue</div>
          <div className="page-desc">High and Critical risk events requiring analyst action</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {([
            { value: 'REVIEW' as const, label: 'Requires Review' },
            { value: 'BLOCK' as const, label: 'Auto-Blocked' },
            { value: '' as const, label: 'All Alerts' }
          ]).map(f => (
            <button
              key={f.value}
              className={`btn ${filter === f.value ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFilter(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        {loading ? <Spinner /> : error ? <ErrorBanner message={error} /> : (
          <>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Txn ID</th>
                    <th>Customer</th>
                    <th>Time</th>
                    <th>Amount</th>
                    <th>Signals</th>
                    <th>Risk Score</th>
                    <th>Risk Level</th>
                    <th>Decision</th>
                  </tr>
                </thead>
                <tbody>
                  {txs.length === 0 ? (
                    <tr><td colSpan={8}><EmptyState title="Queue clear" desc="No risk alerts match the current filter." /></td></tr>
                  ) : txs.map(tx => (
                    <tr key={tx.id} onClick={() => router.push(`/transactions/${tx.id}`)}>
                      <td><span className="tx-id">#{tx.external_transaction_id?.slice(-8) ?? tx.id.slice(-8)}</span></td>
                      <td><span className="tx-id">cust_{tx.customer_id.slice(0,6)}</span></td>
                      <td style={{ color: 'var(--color-text-2)', whiteSpace: 'nowrap' }}>{fmtDate(tx.created_at)}</td>
                      <td className="amount-cell">{fmtAmt(tx.amount, tx.currency)}</td>
                      <td style={{ minWidth: 160 }}>
                        {tx.risk_evaluation?.signals?.slice(0,2).map(s => (
                          <div key={s.name} style={{ fontSize: 10, background: 'var(--color-muted)', color: 'var(--color-text-2)', padding: '2px 4px', marginBottom: 2, borderRadius: 2, display: 'inline-block', marginRight: 4, whiteSpace: 'nowrap' }}>
                            {s.name.replace(/_/g, ' ')}
                          </div>
                        ))}
                        {tx.risk_evaluation?.signals && tx.risk_evaluation.signals.length > 2 && (
                          <span style={{ fontSize: 10, color: 'var(--color-text-3)' }}>+{tx.risk_evaluation.signals.length - 2}</span>
                        )}
                      </td>
                      <td style={{ minWidth: 100 }}>
                        {tx.risk_evaluation && <ScoreDisplay score={tx.risk_evaluation.score} level={tx.risk_evaluation.risk_level} />}
                      </td>
                      <td>{tx.risk_evaluation && <RiskBadge level={tx.risk_evaluation.risk_level} />}</td>
                      <td>{tx.risk_evaluation && <DecisionBadge decision={tx.risk_evaluation.decision} />}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ padding: '12px 20px', borderTop: '1px solid var(--color-border)', fontSize: 13, color: 'var(--color-text-2)' }}>
              {txs.length} alert{txs.length !== 1 ? 's' : ''} in queue
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
