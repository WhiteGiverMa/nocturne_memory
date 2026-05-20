import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import TokenAuth from './TokenAuth';
import { getDomains } from '../lib/api';

vi.mock('../lib/api', () => ({
  getDomains: vi.fn()
}));

describe('TokenAuth', () => {
  beforeEach(() => {
    localStorage.clear();
    getDomains.mockReset();
  });

  it('keeps the submit button disabled until a token is entered', () => {
    render(<TokenAuth onAuthenticated={vi.fn()} />);

    expect(screen.getByRole('button', { name: '连接' })).toBeDisabled();
  });

  it('stores a valid token and calls onAuthenticated', async () => {
    const user = userEvent.setup();
    const onAuthenticated = vi.fn();
    getDomains.mockResolvedValue(['core']);

    render(<TokenAuth onAuthenticated={onAuthenticated} />);

    await user.type(screen.getByLabelText('请输入 API Token'), ' valid-token ');
    await user.click(screen.getByRole('button', { name: '连接' }));

    await waitFor(() => expect(onAuthenticated).toHaveBeenCalledTimes(1));
    expect(getDomains).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem('api_token')).toBe('valid-token');
  });

  it('removes an invalid token and shows the auth error', async () => {
    const user = userEvent.setup();
    getDomains.mockRejectedValue({ response: { status: 401 } });

    render(<TokenAuth onAuthenticated={vi.fn()} />);

    await user.type(screen.getByLabelText('请输入 API Token'), 'wrong-token');
    await user.click(screen.getByRole('button', { name: '连接' }));

    expect(await screen.findByText('Token 无效，请检查后重试')).toBeInTheDocument();
    expect(localStorage.getItem('api_token')).toBeNull();
  });

  it('removes the token and shows a connection error on network failure', async () => {
    const user = userEvent.setup();
    getDomains.mockRejectedValue(new Error('network down'));

    render(<TokenAuth onAuthenticated={vi.fn()} />);

    await user.type(screen.getByLabelText('请输入 API Token'), 'server-token');
    await user.click(screen.getByRole('button', { name: '连接' }));

    expect(await screen.findByText('连接失败，请检查服务器状态')).toBeInTheDocument();
    expect(localStorage.getItem('api_token')).toBeNull();
  });
});
