import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import { getDomains, getNamespaces } from './lib/api';

vi.mock('./lib/api', () => ({
  AUTH_ERROR_EVENT: 'nocturne:auth-error',
  getDomains: vi.fn(),
  getNamespaces: vi.fn()
}));

vi.mock('./features/review/ReviewPage', () => ({
  default: () => <div data-testid="review-page">Review page stub</div>
}));

vi.mock('./features/memory/MemoryBrowser', () => ({
  default: () => <div data-testid="memory-page">Memory page stub</div>
}));

vi.mock('./features/maintenance/MaintenancePage', () => ({
  default: () => <div data-testid="maintenance-page">Maintenance page stub</div>
}));

vi.mock('./features/settings/SettingsDrawer', () => ({
  default: () => null
}));

describe('App', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    window.history.pushState({}, '', '/');
    getDomains.mockReset();
    getNamespaces.mockReset();
    getNamespaces.mockResolvedValue([]);
  });

  it('renders the authenticated shell and redirects the root route to review', async () => {
    getDomains.mockResolvedValue(['core']);

    render(<App />);

    expect(await screen.findByText('Nocturne Admin')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Review & Audit/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Memory Explorer/i })).toBeInTheDocument();
    expect(await screen.findByTestId('review-page')).toBeInTheDocument();
  });

  it('renders the token form when the auth check returns 401', async () => {
    getDomains.mockRejectedValue({ response: { status: 401 } });

    render(<App />);

    expect(await screen.findByLabelText('请输入 API Token')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '连接' })).toBeDisabled();
  });

  it('renders the backend error screen when the API is unreachable', async () => {
    getDomains.mockRejectedValue(new Error('connection refused'));

    render(<App />);

    expect(await screen.findByText('无法连接到后端服务 (Connection Refused)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重试' })).toBeInTheDocument();
  });

  it('consumes a token from the URL before checking auth', async () => {
    window.history.pushState({}, '', '/memory?token=url-token&domain=core');
    getDomains.mockResolvedValue(['core']);

    render(<App />);

    await waitFor(() => expect(localStorage.getItem('api_token')).toBe('url-token'));
    expect(window.location.search).toBe('?domain=core');
    expect(await screen.findByTestId('memory-page')).toBeInTheDocument();
  });
});
