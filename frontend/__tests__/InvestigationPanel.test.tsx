import React from 'react';
import { render, screen } from '@testing-library/react';
import { InvestigationPanel } from '@/components/InvestigationPanel';

const mockReport = {
  executive_summary: 'High probability of fraud.',
  primary_risk_factors: ['velocity', 'amount_anomaly'],
  supporting_evidence: ['12 transactions in 5 minutes', 'Amount 18x baseline'],
  behavioral_comparison: 'Customer average is $50; this transaction is $900.',
  recommended_investigation_action: 'Contact customer immediately.',
  confidence_statement: 'HIGH confidence based on 3 signals.',
};

describe('InvestigationPanel', () => {
  it('shows spinner when loading', () => {
    render(<InvestigationPanel report={null} loading={true} error={null} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows error when provided', () => {
    render(<InvestigationPanel report={null} loading={false} error="LLM timed out" />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/LLM timed out/)).toBeInTheDocument();
  });

  it('renders executive summary', () => {
    render(<InvestigationPanel report={mockReport} loading={false} error={null} />);
    expect(screen.getByText('High probability of fraud.')).toBeInTheDocument();
  });

  it('renders all primary risk factors as badges', () => {
    render(<InvestigationPanel report={mockReport} loading={false} error={null} />);
    expect(screen.getByText('velocity')).toBeInTheDocument();
    expect(screen.getByText('amount_anomaly')).toBeInTheDocument();
  });

  it('renders all supporting evidence items', () => {
    render(<InvestigationPanel report={mockReport} loading={false} error={null} />);
    expect(screen.getByText('12 transactions in 5 minutes')).toBeInTheDocument();
    expect(screen.getByText('Amount 18x baseline')).toBeInTheDocument();
  });

  it('renders the recommended action', () => {
    render(<InvestigationPanel report={mockReport} loading={false} error={null} />);
    expect(screen.getByText('Contact customer immediately.')).toBeInTheDocument();
  });

  it('renders the confidence statement', () => {
    render(<InvestigationPanel report={mockReport} loading={false} error={null} />);
    expect(screen.getByText(/HIGH confidence/)).toBeInTheDocument();
  });

  it('renders nothing when no report and not loading', () => {
    const { container } = render(<InvestigationPanel report={null} loading={false} error={null} />);
    expect(container.firstChild).toBeNull();
  });
});
