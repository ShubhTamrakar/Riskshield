'use client';
import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { AppLayout } from '@/components/AppLayout';
import { RiskBadge, DecisionBadge, StatusBadge, ScoreDisplay } from '@/components/Badges';
import { Spinner, ErrorBanner, EmptyState } from '@/components/States';
import { api, type Transaction, type PagedResponse } from '@/lib/api';

function fmtAmt(n: number, currency = 'USD') {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 2 }).format(n);
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

const COLS = [
  { key: 'external_transaction_id', label: 'Txn ID',         sortable: false },
  { key: 'customer_id',             label: 'Customer',       sortable: false },
  { key: 'merchant_id',             label: 'Merchant',       sortable: false },
  { key: 'created_at',              label: 'Time',           sortable: true  },
  { key: 'amount',                  label: 'Amount',         sortable: true  },
  { key: 'payment_method',          label: 'Method',         sortable: false },
  { key: 'risk_signals',            label: 'Signals',        sortable: false },
  { key: 'risk_score',              label: 'Risk Score',     sortable: true  },
  { key: 'decision',                label: 'Decision',       sortable: false },
];

export default function TransactionsPage() {
  const router = useRouter();
  const [data, setData] = useState<PagedResponse<Transaction> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [search, setSearch]       = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [decisionFilter, setDecisionFilter] = useState('');
  const [paymentFilter, setPaymentFilter] = useState('');
  const [sort, setSort]           = useState('created_at');
  const [order, setOrder]         = useState<'asc'|'desc'>('desc');
  const [page, setPage]           = useState(1);

  const load = useCallback((showSpinner = true) => {
    if (showSpinner) setLoading(true);
    api.getTransactions({
      page, size: 20,
      search: search || undefined,
      risk_level: riskFilter || undefined,
      decision: decisionFilter || undefined,
      // If the backend doesn't support payment_method filter natively, we just send it (it will be ignored if not implemented in the API)
      sort, order,
    })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => {
        if (showSpinner) setLoading(false);
      });
  }, [page, search, riskFilter, decisionFilter, paymentFilter, sort, order]);

  useEffect(() => {
    load(true);
    const interval = setInterval(() => load(false), 2000);
    return () => clearInterval(interval);
  }, [load]);

  function toggleSort(key: string) {
    if (sort === key) setOrder(o => o === 'asc' ? 'desc' : 'asc');
    else { setSort(key); setOrder('desc'); }
    setPage(1);
  }

  function handleSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPage(1);
    load();
  }

  const totalPages = data?.pages ?? 1;

  return (
    <AppLayout title="Transactions">
      <div className="page-header">
        <div>
          <div className="page-title">Transactions</div>
          <div className="page-desc">Browse, filter and inspect evaluated payments</div>
        </div>
      </div>

      <div className="card">
        {/* Search & Filter Bar */}
        <form onSubmit={handleSearch} className="search-bar" style={{ flexWrap: 'wrap' }}>
          <div className="search-input-wrapper">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              className="search-input"
              placeholder="Search ID, customer, merchant..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>

          <select className="filter-select" value={riskFilter} onChange={e => { setRiskFilter(e.target.value); setPage(1); }}>
            <option value="">All Risk</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="CRITICAL">Critical</option>
          </select>

          <select className="filter-select" value={decisionFilter} onChange={e => { setDecisionFilter(e.target.value); setPage(1); }}>
            <option value="">All Decisions</option>
            <option value="APPROVE">Approved</option>
            <option value="REVIEW">Review</option>
            <option value="BLOCK">Blocked</option>
          </select>
          
          <select className="filter-select" value={paymentFilter} onChange={e => { setPaymentFilter(e.target.value); setPage(1); }}>
            <option value="">All Methods</option>
            <option value="card">Card</option>
            <option value="upi">UPI</option>
            <option value="wallet">Wallet</option>
            <option value="bank_transfer">Bank Transfer</option>
          </select>

          <button type="submit" className="btn btn-primary">Search</button>
        </form>

        {/* Table */}
        {loading ? <Spinner /> : error ? <ErrorBanner message={error} /> : (
          <>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    {COLS.map(col => (
                      <th
                        key={col.key}
                        onClick={() => col.sortable && toggleSort(col.key)}
                        aria-sort={sort === col.key ? (order === 'asc' ? 'ascending' : 'descending') : 'none'}
                        style={col.sortable ? { cursor: 'pointer' } : {}}
                      >
                        {col.label}
                        {col.sortable && sort === col.key && (
                          <span style={{ marginLeft: 4 }}>{order === 'asc' ? '↑' : '↓'}</span>
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data?.items.length === 0 ? (
                    <tr><td colSpan={COLS.length}>
                      <EmptyState title="No transactions found" desc="Adjust your filters or search query." />
                    </td></tr>
                  ) : data?.items.filter(tx => {
                    // Local fallback filter if backend doesn't support payment filtering
                    if (paymentFilter && tx.payment_method !== paymentFilter) return false;
                    return true;
                  }).map(tx => (
                    <tr key={tx.id} onClick={() => router.push(`/transactions/${tx.id}`)}>
                      <td><span className="tx-id">{tx.external_transaction_id?.slice(-8) ?? tx.id.slice(-8)}</span></td>
                      <td><span className="tx-id">cust_{tx.customer_id.slice(0,6)}</span></td>
                      <td><span className="tx-id">merch_{tx.merchant_id.slice(0,6)}</span></td>
                      <td style={{ color: 'var(--color-text-2)', whiteSpace: 'nowrap' }}>{fmtDate(tx.created_at)}</td>
                      <td className="amount-cell">{fmtAmt(tx.amount, tx.currency)}</td>
                      <td>
                        <span style={{ fontSize: 11, background: 'var(--color-muted)', padding: '2px 6px', borderRadius: 4, textTransform: 'uppercase' }}>
                          {tx.payment_method || 'CARD'}
                        </span>
                      </td>
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
                        {tx.risk_evaluation ? (
                          <ScoreDisplay score={tx.risk_evaluation.score} level={tx.risk_evaluation.risk_level} />
                        ) : <span style={{ color: 'var(--color-text-3)' }}>—</span>}
                      </td>
                      <td>
                        {tx.risk_evaluation ? <DecisionBadge decision={tx.risk_evaluation.decision} /> : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="pagination">
              <span>
                Showing {((page - 1) * 20) + 1}–{Math.min(page * 20, data?.total ?? 0)} of {data?.total ?? 0} transactions
              </span>
              <div className="pagination-controls">
                <button className="page-btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</button>
                {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                  const p = i + 1;
                  return (
                    <button key={p} className={`page-btn ${p === page ? 'active' : ''}`} onClick={() => setPage(p)}>{p}</button>
                  );
                })}
                {totalPages > 7 && <span style={{ padding: '5px 6px', fontSize: 13, color: 'var(--color-text-3)' }}>…{totalPages}</span>}
                <button className="page-btn" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</button>
              </div>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
