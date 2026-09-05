'use client';
import { useState, useEffect } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { Spinner, ErrorBanner } from '@/components/States';
import { InvestigationPanel } from '@/components/InvestigationPanel';
import { api, type InvestigationReport, type Transaction } from '@/lib/api';

export default function InvestigationPage() {
  const [txId, setTxId] = useState('');
  const [report, setReport] = useState<InvestigationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentTx, setRecentTx] = useState<Transaction[]>([]);

  useEffect(() => {
    // Load a few high-risk transactions to serve as a queue
    api.getTransactions({ risk_level: 'HIGH', size: 10 })
      .then(r => setRecentTx(r.items))
      .catch(console.error);
  }, []);

  function fetchReport(id: string) {
    if (!id.trim()) return;
    setTxId(id);
    setLoading(true);
    setError(null);
    setReport(null);
    api.investigate(id.trim())
      .then(setReport)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    fetchReport(txId);
  }

  return (
    <AppLayout title="Investigation Workspace">
      <div className="page-header">
        <div>
          <div className="page-title">Investigation Workspace</div>
          <div className="page-desc">Run AI-powered analysis on suspicious transactions</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
        {/* Left Sidebar: Queue */}
        <div className="card" style={{ width: 320, flexShrink: 0 }}>
          <div className="card-header">
            <div className="card-title">Investigation Queue</div>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {recentTx.length === 0 ? (
              <div style={{ padding: 20, textAlign: 'center', color: 'var(--color-text-3)' }}>Queue is empty.</div>
            ) : (
              recentTx.map(tx => (
                <div 
                  key={tx.id} 
                  className="queue-item"
                  style={{ 
                    padding: '12px 16px', 
                    borderBottom: '1px solid var(--color-border)', 
                    cursor: 'pointer',
                    background: txId === tx.id ? 'var(--color-accent-bg)' : 'transparent',
                    borderLeft: txId === tx.id ? '3px solid var(--color-accent)' : '3px solid transparent'
                  }}
                  onClick={() => fetchReport(tx.id)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span className="mono" style={{ fontSize: 13, fontWeight: 600 }}>#{tx.external_transaction_id?.slice(-8) ?? tx.id.slice(-8)}</span>
                    <span style={{ fontSize: 13, color: 'var(--color-text-2)' }}>{new Date(tx.created_at).toLocaleDateString()}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 13 }}>{new Intl.NumberFormat('en-US', { style: 'currency', currency: tx.currency }).format(tx.amount)}</span>
                    <span style={{ fontSize: 11, background: 'var(--color-high-bg)', color: 'var(--color-high)', padding: '2px 6px', borderRadius: 4 }}>HIGH RISK</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Main Content: Lookup & Report */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div className="card">
            <div className="card-header"><div className="card-title">Lookup Transaction</div></div>
            <div className="card-body">
              <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 12 }}>
                <input
                  className="search-input"
                  style={{ flex: 1 }}
                  placeholder="Paste transaction UUID..."
                  value={txId}
                  onChange={e => setTxId(e.target.value)}
                />
                <button type="submit" className="btn btn-primary" disabled={loading || !txId.trim()}>
                  {loading ? 'Investigating…' : 'Investigate'}
                </button>
              </form>
            </div>
          </div>

          {(loading || error || report) && (
            <div className="card">
              <div className="card-header"><div className="card-title">Analyst Report</div></div>
              {loading && <div style={{ padding: 20 }}><Spinner /></div>}
              {error   && <div style={{ padding: '0 20px 20px' }}><ErrorBanner message={error} /></div>}
              {report  && (
                <div>
                  <InvestigationPanel report={report} loading={false} error={null} />
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
