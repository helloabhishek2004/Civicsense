import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CivicButton } from '@/core/components/CivicButton';
import { StatusBadge } from '@/core/components/StatusBadge';
import { SeverityBadge } from '@/core/components/SeverityBadge';
import { PriorityBadge } from '@/core/components/PriorityBadge';
import { StatCard } from '@/core/components/StatCard';
import { EmptyState } from '@/core/components/EmptyState';

describe('Shared UI Components', () => {
  it('renders CivicButton with children and variant', () => {
    render(<CivicButton variant="primary">Verify Issue</CivicButton>);
    const btn = screen.getByRole('button', { name: /verify issue/i });
    expect(btn).toBeInTheDocument();
    expect(btn).not.toBeDisabled();
  });

  it('renders CivicButton in loading state as disabled', () => {
    render(<CivicButton isLoading>Saving</CivicButton>);
    const btn = screen.getByRole('button');
    expect(btn).toBeDisabled();
  });

  it('renders StatusBadge correctly for all phases', () => {
    const { rerender } = render(<StatusBadge status="VERIFICATION_REQUIRED" />);
    expect(screen.getByText('Needs Review')).toBeInTheDocument();

    rerender(<StatusBadge status="IN_PROGRESS" />);
    expect(screen.getByText('In Progress')).toBeInTheDocument();

    rerender(<StatusBadge status="CLOSED" />);
    expect(screen.getByText('Closed')).toBeInTheDocument();
  });

  it('renders SeverityBadge with correct severity level', () => {
    render(<SeverityBadge severity="CRITICAL" />);
    expect(screen.getByText('Critical')).toBeInTheDocument();
  });

  it('renders PriorityBadge with code and label', () => {
    render(<PriorityBadge priority="HIGH" />);
    expect(screen.getByText('P2')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('renders StatCard with title and value', () => {
    render(
      <StatCard
        title="Pending Reports"
        value={42}
        subtitle="Requires immediate review"
      />
    );
    expect(screen.getByText('Pending Reports')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('Requires immediate review')).toBeInTheDocument();
  });

  it('renders EmptyState with message', () => {
    render(
      <EmptyState
        title="No Reports Found"
        description="Try adjusting your filter criteria."
      />
    );
    expect(screen.getByText('No Reports Found')).toBeInTheDocument();
    expect(screen.getByText('Try adjusting your filter criteria.')).toBeInTheDocument();
  });
});
