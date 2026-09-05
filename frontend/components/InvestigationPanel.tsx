import type { InvestigationReport } from '@/lib/api';
import { Spinner, ErrorBanner } from './States';

export function InvestigationPanel({
  report,
  loading,
  error,
}: {
  report: InvestigationReport | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <Spinner />;
  if (error)   return <ErrorBanner message={error} />;
  if (!report) return null;

  return (
    <div className="investigation-panel">
      <div className="investigation-section">
        <div className="investigation-section-title">Executive Summary</div>
        <p className="investigation-summary">{report.executive_summary}</p>
      </div>

      <div className="investigation-section">
        <div className="investigation-section-title">Primary Risk Factors</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {report.primary_risk_factors.map(f => (
            <span key={f} className="badge badge-high" style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{f}</span>
          ))}
        </div>
      </div>

      <div className="investigation-section">
        <div className="investigation-section-title">Supporting Evidence</div>
        <ul className="evidence-list">
          {report.supporting_evidence.map((e, i) => (
            <li key={i} className="evidence-item">{e}</li>
          ))}
        </ul>
      </div>

      <div className="investigation-section">
        <div className="investigation-section-title">Behavioral Comparison</div>
        <p className="investigation-summary">{report.behavioral_comparison}</p>
      </div>

      <div className="investigation-section">
        <div className="investigation-section-title">Recommended Action</div>
        <p className="investigation-summary" style={{ fontWeight: 600 }}>{report.recommended_investigation_action}</p>
      </div>

      <div className="investigation-section">
        <div className="investigation-section-title">Confidence</div>
        <span className="confidence-chip">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
          {report.confidence_statement}
        </span>
      </div>
    </div>
  );
}
