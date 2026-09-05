'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AppLayout } from '@/components/AppLayout';
import { RiskBadge } from '@/components/Badges';
import { Spinner, ErrorBanner, EmptyState } from '@/components/States';
import { api, type Transaction } from '@/lib/api';

interface CustomerSummary {
  customer_id: string;
  tx_count: number;
  total_amount: number;
  avg_risk_score: number;
  top_risk_level: string;
  last_seen: string;
}

function fmtAmt(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
}
function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function CustomersPage() {
  const router = useRouter();
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getTransactions({ size: 200 })
      .then(r => {
        // Aggregate customers from transaction data
        const map: Record<string, CustomerSummary> = {};
        r.items.forEach(tx => {
          const cid = tx.customer_id;
          if (!map[cid]) {
            map[cid] = { customer_id: cid, tx_count: 0, total_amount: 0, avg_risk_score: 0, top_risk_level: 'LOW', last_seen: tx.created_at };
          }
          const c = map[cid];
          c.tx_count++;
          c.total_amount += tx.amount;
          if (tx.risk_evaluation) {
            c.avg_risk_score = (c.avg_risk_score * (c.tx_count - 1) + tx.risk_evaluation.score) / c.tx_count;
            const order = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
            if (order.indexOf(tx.risk_evaluation.risk_level) > order.indexOf(c.top_risk_level)) {
              c.top_risk_level = tx.risk_evaluation.risk_level;
            }
          }
          if (new Date(tx.created_at) > new Date(c.last_seen)) c.last_seen = tx.created_at;
        });
        setCustomers(Object.values(map).sort((a, b) => b.avg_risk_score - a.avg_risk_score));
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppLayout title="Customers">
      <div className="page-header">
        <div>
          <div className="page-title">Customers</div>
          <div className="page-desc">Aggregated customer risk profiles</div>
        </div>
      </div>

      <div className="card">
        {loading ? <Spinner /> : error ? <ErrorBanner message={error} /> : (
          <>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Customer ID</th>
                    <th>Transactions</th>
                    <th>Total Volume</th>
                    <th>Avg Risk Score</th>
                    <th>Top Risk Level</th>
                    <th>Last Seen</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.length === 0 ? (
                    <tr><td colSpan={6}><EmptyState title="No customer data" /></td></tr>
                  ) : customers.slice(0, 100).map(c => (
                    <tr key={c.customer_id} onClick={() => router.push(`/customers/${c.customer_id}`)} style={{ cursor: 'pointer' }}>
                      <td><span className="tx-id" style={{ color: 'var(--color-accent)' }}>cust_{c.customer_id.slice(0,8)}...</span></td>
                      <td>{c.tx_count}</td>
                      <td className="amount-cell">{fmtAmt(c.total_amount)}</td>
                      <td style={{ fontWeight: 600 }}>{Math.round(c.avg_risk_score)}</td>
                      <td><RiskBadge level={c.top_risk_level as any} /></td>
                      <td style={{ color: 'var(--color-text-2)' }}>{fmtDate(c.last_seen)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ padding: '12px 20px', borderTop: '1px solid var(--color-border)', fontSize: 13, color: 'var(--color-text-2)' }}>
              {customers.length} unique customers
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
