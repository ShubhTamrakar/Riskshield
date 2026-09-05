'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { AppLayout } from '@/components/AppLayout';
import { RiskBadge, DecisionBadge, StatusBadge, RiskGauge } from '@/components/Badges';
import { Spinner, ErrorBanner } from '@/components/States';
import { InvestigationPanel } from '@/components/InvestigationPanel';
import { api, type Transaction, type InvestigationReport } from '@/lib/api';

function fmtAmt(n: number, currency = 'USD') {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(n);
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

export default function TransactionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [tx, setTx] = useState<Transaction | null>(null);
  const [txLoading, setTxLoading] = useState(true);
  const [txError, setTxError] = useState<string | null>(null);

  const [report, setReport] = useState<InvestigationReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const [reportRequested, setReportRequested] = useState(false);

  useEffect(() => {
    if (!id) return;
    api.getTransaction(id)
      .then(setTx)
      .catch(e => setTxError(e.message))
      .finally(() => setTxLoading(false));
  }, [id]);

  function runInvestigation() {
    if (!id) return;
    setReportRequested(true);
    setReportLoading(true);
    setReportError(null);
    api.investigate(id)
      .then(setReport)
      .catch(e => setReportError(e.message))
      .finally(() => setReportLoading(false));
  }

  const re = tx?.risk_evaluation;

  return (
    <AppLayout title="Transaction Detail">
      <div className="page-header">
        <div>
          <button
            className="btn btn-secondary"
            onClick={() => router.back()}
            style={{ marginBottom: 8 }}
          >
            ← Back
          </button>
          <div className="page-title">
            #{tx?.external_transaction_id?.slice(-12) ?? id?.slice(-12)}
          </div>
          {tx && <div className="page-desc">{fmtDate(tx.created_at)}</div>}
        </div>
        {re && (
          <div style={{ display: 'flex', gap: 8 }}>
            <DecisionBadge decision={re.decision} />
            <StatusBadge status={tx?.status ?? 'pending'} />
          </div>
        )}
      </div>

      {txLoading && <Spinner />}
      {txError   && <ErrorBanner message={txError} />}

      {tx && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
          {/* Left Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Transaction Info */}
            <div className="card">
              <div className="card-header"><div className="card-title">Transaction Info</div></div>
              <div className="card-body">
                <div className="detail-grid">
                  <div className="detail-field">
                    <div className="detail-label">Amount</div>
                    <div className="detail-value">{fmtAmt(tx.amount, tx.currency)}</div>
                  </div>
                  <div className="detail-field">
                    <div className="detail-label">Currency</div>
                    <div className="detail-value">{tx.currency}</div>
                  </div>
                  <div className="detail-field">
                    <div className="detail-label">Status</div>
                    <div className="detail-value"><StatusBadge status={tx.status} /></div>
                  </div>
                  <div className="detail-field">
                    <div className="detail-label">Payment Method</div>
                    <div className="detail-value" style={{ textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>{tx.payment_method || 'CARD'}</div>
                  </div>
                  <div className="detail-field">
                    <div className="detail-label">Transaction ID</div>
                    <div className="detail-value mono">{tx.external_transaction_id ?? tx.id}</div>
                  </div>
                  <div className="detail-field">
                    <div className="detail-label">Customer ID</div>
                    <div className="detail-value mono" style={{ color: 'var(--color-accent)', cursor: 'pointer' }}>cust_{tx.customer_id.slice(0,8)}...</div>
                  </div>
                  <div className="detail-field">
                    <div className="detail-label">Merchant ID</div>
                    <div className="detail-value mono" style={{ color: 'var(--color-accent)', cursor: 'pointer' }}>merch_{tx.merchant_id.slice(0,8)}...</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Device & Network */}
            <div className="card">
              <div className="card-header"><div className="card-title">Device &amp; Network</div></div>
              <div className="card-body">
                <div className="detail-grid">
                  <div className="detail-field">
                    <div className="detail-label">Device ID</div>
                    <div className="detail-value mono">{tx.device_id ?? 'N/A'}</div>
                  </div>
                  <div className="detail-field">
                    <div className="detail-label">IP Address</div>
                    <div className="detail-value mono">{tx.ip_address ?? 'N/A'}</div>
                  </div>
                  <div className="detail-field">
                    <div className="detail-label">City</div>
                    <div className="detail-value">{tx.city ?? 'N/A'}</div>
                  </div>
                  <div className="detail-field">
                    <div className="detail-label">Country</div>
                    <div className="detail-value">{tx.country ?? 'N/A'}</div>
                  </div>
                  {tx.latitude != null && (
                    <div className="detail-field">
                      <div className="detail-label">Coordinates</div>
                      <div className="detail-value mono">{tx.latitude.toFixed(4)}, {tx.longitude?.toFixed(4)}</div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* AI Investigation */}
            <div className="card">
              <div className="card-header">
                <div>
                  <div className="card-title">AI Investigation</div>
                  <div className="card-subtitle">LLM-generated analyst report</div>
                </div>
                {!reportRequested && (
                  <button className="btn btn-primary" onClick={runInvestigation}>
                    Run Investigation
                  </button>
                )}
              </div>
              <InvestigationPanel
                report={report}
                loading={reportLoading}
                error={reportError}
              />
              {!reportRequested && (
                <div style={{ padding: '20px', textAlign: 'center', color: 'var(--color-text-3)', fontSize: 13 }}>
                  Click "Run Investigation" to generate an AI-powered analyst report for this transaction.
                </div>
              )}
            </div>
          </div>

          {/* Right Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Risk Score */}
            {re && (
              <div className="card">
                <div className="card-header"><div className="card-title">Risk Assessment</div></div>
                <div className="card-body">
                  <div style={{ marginBottom: 20 }}>
                    <RiskGauge score={re.score} level={re.risk_level} />
                  </div>
                  <div className="detail-grid">
                    <div className="detail-field">
                      <div className="detail-label">Risk Level</div>
                      <div className="detail-value"><RiskBadge level={re.risk_level} /></div>
                    </div>
                    <div className="detail-field">
                      <div className="detail-label">Decision</div>
                      <div className="detail-value"><DecisionBadge decision={re.decision} /></div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Risk Signals */}
            {re && re.signals && re.signals.length > 0 && (
              <div className="card">
                <div className="card-header">
                  <div>
                    <div className="card-title">Risk Signals</div>
                    <div className="card-subtitle">{re.signals.length} signal{re.signals.length !== 1 ? 's' : ''} triggered</div>
                  </div>
                </div>
                <div className="table-container">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Signal</th>
                        <th>Severity</th>
                        <th>Explanation</th>
                      </tr>
                    </thead>
                    <tbody>
                      {re.signals.map((sig, i) => (
                        <tr key={i}>
                          <td><span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{sig.name}</span></td>
                          <td><RiskBadge level={sig.severity} /></td>
                          <td style={{ color: 'var(--color-text-2)', fontSize: 13 }}>{sig.explanation}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {!re && (
              <div className="card">
                <div className="card-body" style={{ textAlign: 'center', color: 'var(--color-text-3)', padding: 40 }}>
                  No risk evaluation on record for this transaction.
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </AppLayout>
  );
}
