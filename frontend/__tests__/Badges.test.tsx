import React from 'react';
import { render, screen } from '@testing-library/react';
import { RiskBadge, DecisionBadge, StatusBadge, ScoreDisplay } from '@/components/Badges';

describe('RiskBadge', () => {
  it('renders LOW badge with correct text', () => {
    render(<RiskBadge level="LOW" />);
    expect(screen.getByText('LOW')).toBeInTheDocument();
    expect(screen.getByText('LOW')).toHaveClass('badge-low');
  });

  it('renders CRITICAL badge', () => {
    render(<RiskBadge level="CRITICAL" />);
    expect(screen.getByText('CRITICAL')).toHaveClass('badge-critical');
  });

  it('renders HIGH badge', () => {
    render(<RiskBadge level="HIGH" />);
    expect(screen.getByText('HIGH')).toHaveClass('badge-high');
  });

  it('renders MEDIUM badge', () => {
    render(<RiskBadge level="MEDIUM" />);
    expect(screen.getByText('MEDIUM')).toHaveClass('badge-medium');
  });
});

describe('DecisionBadge', () => {
  it('renders BLOCK as "Blocked"', () => {
    render(<DecisionBadge decision="BLOCK" />);
    expect(screen.getByText('Blocked')).toBeInTheDocument();
  });

  it('renders APPROVE as "Approved"', () => {
    render(<DecisionBadge decision="APPROVE" />);
    expect(screen.getByText('Approved')).toBeInTheDocument();
  });

  it('renders REVIEW as "Review"', () => {
    render(<DecisionBadge decision="REVIEW" />);
    expect(screen.getByText('Review')).toBeInTheDocument();
  });
});

describe('StatusBadge', () => {
  it('renders blocked status', () => {
    render(<StatusBadge status="blocked" />);
    expect(screen.getByText('Blocked')).toBeInTheDocument();
  });

  it('renders completed status', () => {
    render(<StatusBadge status="completed" />);
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });
});

describe('ScoreDisplay', () => {
  it('renders the score number', () => {
    render(<ScoreDisplay score={87} level="CRITICAL" />);
    expect(screen.getByText('87')).toBeInTheDocument();
  });

  it('renders score bar fill', () => {
    const { container } = render(<ScoreDisplay score={50} level="MEDIUM" />);
    const fill = container.querySelector('.risk-score-fill');
    expect(fill).toHaveStyle({ width: '50%' });
  });
});
