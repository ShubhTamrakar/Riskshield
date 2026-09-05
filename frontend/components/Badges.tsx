import type { RiskLevel, Decision, TxStatus } from '@/lib/api';

type BadgeVariant = RiskLevel | Decision | TxStatus | 'pending';

const MAP: Record<string, string> = {
  LOW:      'badge badge-low',
  MEDIUM:   'badge badge-medium',
  HIGH:     'badge badge-high',
  CRITICAL: 'badge badge-critical',
  BLOCK:    'badge badge-blocked',
  APPROVE:  'badge badge-approved',
  REVIEW:   'badge badge-review',
  blocked:  'badge badge-blocked',
  completed:'badge badge-approved',
  failed:   'badge badge-critical',
  pending:  'badge badge-pending',
};

const LABELS: Record<string, string> = {
  BLOCK:    'Blocked',
  APPROVE:  'Approved',
  REVIEW:   'Review',
  blocked:  'Blocked',
  completed:'Completed',
  failed:   'Failed',
  pending:  'Pending',
};

export function RiskBadge({ level }: { level: RiskLevel }) {
  return <span className={MAP[level] ?? 'badge badge-pending'}>{level}</span>;
}

export function DecisionBadge({ decision }: { decision: Decision }) {
  return <span className={MAP[decision] ?? 'badge badge-pending'}>{LABELS[decision] ?? decision}</span>;
}

export function StatusBadge({ status }: { status: TxStatus }) {
  return <span className={MAP[status] ?? 'badge badge-pending'}>{LABELS[status] ?? status}</span>;
}

export function ScoreDisplay({ score, level }: { score: number; level: RiskLevel }) {
  const colorMap: Record<RiskLevel, string> = {
    LOW:      '#16A34A',
    MEDIUM:   '#D97706',
    HIGH:     '#EA580C',
    CRITICAL: '#DC2626',
  };
  const color = colorMap[level] ?? '#94A3B8';
  return (
    <div className="score-display">
      <span className="score-number" style={{ color }}>{score}</span>
      <div className="score-bar-container">
        <div className="risk-score-bar">
          <div className="risk-score-fill" style={{ width: `${score}%`, background: color }} />
        </div>
      </div>
    </div>
  );
}

export function RiskGauge({ score, level }: { score: number; level: RiskLevel }) {
  const colorMap: Record<RiskLevel, string> = {
    LOW:      '#16A34A',
    MEDIUM:   '#D97706',
    HIGH:     '#EA580C',
    CRITICAL: '#DC2626',
  };
  const color = colorMap[level] ?? '#94A3B8';
  return (
    <div className="risk-gauge-wrap">
      <div className="risk-gauge-number" style={{ color }}>{score}</div>
      <RiskBadge level={level} />
      <div style={{ width: '100%', marginTop: 8 }}>
        <div className="risk-score-bar" style={{ height: 8 }}>
          <div className="risk-score-fill" style={{ width: `${score}%`, background: color }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--color-text-3)', marginTop: 4 }}>
          <span>0 LOW</span><span>31 MED</span><span>61 HIGH</span><span>86 CRITICAL 100</span>
        </div>
      </div>
    </div>
  );
}
