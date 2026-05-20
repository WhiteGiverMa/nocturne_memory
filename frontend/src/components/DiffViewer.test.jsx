import React from 'react';
import { render, screen } from '@testing-library/react';

import DiffViewer from './DiffViewer';

describe('DiffViewer', () => {
  it('shows an empty-state message when content is unchanged', () => {
    render(<DiffViewer oldText="same" newText="same" />);

    expect(screen.getByText('No changes detected in content.')).toBeInTheDocument();
  });

  it('marks added lines', () => {
    render(<DiffViewer oldText="" newText="added line" />);

    expect(screen.getByText('ADDED')).toBeInTheDocument();
    expect(screen.getByText('added line')).toBeInTheDocument();
    expect(screen.getByText('ADDED').closest('div')).toHaveClass('bg-emerald-950/20');
  });

  it('marks removed lines', () => {
    render(<DiffViewer oldText="removed line" newText="" />);

    expect(screen.getByText('REMOVED')).toBeInTheDocument();
    expect(screen.getByText('removed line')).toBeInTheDocument();
    expect(screen.getByText('REMOVED').closest('div')).toHaveClass('bg-red-950/20');
  });

  it('treats missing props as empty strings', () => {
    render(<DiffViewer />);

    expect(screen.getByText('No changes detected in content.')).toBeInTheDocument();
  });
});
