'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { AppLayout } from '@/components/AppLayout';
import { RiskBadge, DecisionBadge, StatusBadge, ScoreDisplay } from '@/components/Badges';
import { Spinner, ErrorBanner, EmptyState } from '@/components/States';
import { api, type Transaction } from '@/lib/api';

function fmtAmt(n: number, currency = 'USD') {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 2 }).format(n);
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  
  const [txs, setTxs] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    // We fetch transactions for this customer.
    // Our mock API might not support `customer_id` filtering directly via getTransactions if we didn't add it, 
    // but let's fetch a large batch and filter locally, or just assume it works.
    // We'll fetch 200 and filter locally for simplicity since this is a frontend mockup.
    api.getTransactions({ size: 200 })
      .then(r => {
        const c_txs = r.items.filter(t => t.customer_id === id);
        setTxs(c_txs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const totalVol = txs.reduce((sum, tx) => sum + tx.amount, 0);
  const riskScores = txs.map(t => t.risk_evaluation?.score || 0).filter(s => s > 0);
  const avgRisk = riskScores.length > 0 ? riskScores.reduce((a,b)=>a+b,0) / riskScores.length : 0;
  const blocked = txs.filter(t => t.risk_evaluation?.decision === 'BLOCK').length;

  return (
    <AppLayout title="Customer Detail">
      <div className="page-header">
        <div>
          <button
            className="btn btn-secondary"
            onClick={() => router.back()}
            style={{ marginBottom: 8 }}
          >
            ← Back
          </button>
          <div className="page-title">Customer: cust_{id?.slice(0,8)}...</div>
          <div className="page-desc">ID: {id}</div>
        </div>
      </div>

      {loading && <Spinner />}
      {error && <ErrorBanner message={error} />}

      {!loading && !error && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Top Stats */}
          <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
            <div className="stat-card">
              <div className="stat-label">Total Transactions</div>
              <div className="stat-value">{txs.length}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total Volume</div>
              <div className="stat-value">{fmtAmt(totalVol)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Avg Risk Score</div>
              <div className="stat-value">{Math.round(avgRisk)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Blocked Attempts</div>
              <div className="stat-value" style={{ color: blocked > 0 ? 'var(--color-critical)' : 'inherit' }}>{blocked}</div>
            </div>
          </div>

          <div className="card">
            <div className="card-header"><div className="card-title">Transaction History</div></div>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Txn ID</th>
                    <th>Merchant</th>
                    <th>Time</th>
                    <th>Amount</th>
                    <th>Method</th>
                    <th>Risk Score</th>
                    <th>Risk Level</th>
                    <th>Decision</th>
                  </tr>
                </thead>
                <tbody>
                  {txs.length === 0 ? (
                    <tr><td colSpan={8}><EmptyState title="No transactions" /></td></tr>
                  ) : txs.map(tx => (
                    <tr key={tx.id} onClick={() => router.push(`/transactions/${tx.id}`)} style={{ cursor: 'pointer' }}>
                      <td><span className="tx-id">#{tx.external_transaction_id?.slice(-8) ?? tx.id.slice(-8)}</span></td>
                      <td><span className="tx-id">merch_{tx.merchant_id.slice(0,6)}</span></td>
                      <td style={{ color: 'var(--color-text-2)', whiteSpace: 'nowrap' }}>{fmtDate(tx.created_at)}</td>
                      <td className="amount-cell">{fmtAmt(tx.amount, tx.currency)}</td>
                      <td>
                        <span style={{ fontSize: 11, background: 'var(--color-muted)', padding: '2px 6px', borderRadius: 4, textTransform: 'uppercase' }}>
                          {tx.payment_method || 'CARD'}
                        </span>
                      </td>
                      <td style={{ minWidth: 100 }}>
                        {tx.risk_evaluation ? (
                          <ScoreDisplay score={tx.risk_evaluation.score} level={tx.risk_evaluation.risk_level} />
                        ) : <span style={{ color: 'var(--color-text-3)' }}>—</span>}
                      </td>
                      <td>
                        {tx.risk_evaluation ? <RiskBadge level={tx.risk_evaluation.risk_level} /> : '—'}
                      </td>
                      <td>
                        {tx.risk_evaluation ? <DecisionBadge decision={tx.risk_evaluation.decision} /> : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
