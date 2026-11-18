import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import GuestRoute from '../../../../components/commons/GuestRoute/GuestRoute';
import { useAuth } from '../../../../contexts/AuthContext';

// =====================================================
// GuestRoute のテスト（改修案件08）
// - useAuth を差し替えて、「ログイン中」「未ログイン」を作る
//   （本物の AuthProvider は起動時に API を呼ぶので、テストでは使わない）
// =====================================================
jest.mock('../../../../contexts/AuthContext', () => ({ useAuth: jest.fn() }));
const mockedUseAuth = useAuth as jest.Mock;

// ① /signin を開いた状態で、GuestRoute に囲まれたサインイン画面と、/snaps を用意する
const renderAt = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<GuestRoute />}>
          <Route path="/signin" element={<p>サインイン画面</p>} />
          <Route path="/" element={<p>Welcome 画面</p>} />
        </Route>
        <Route path="/snaps" element={<p>スナップ一覧</p>} />
      </Routes>
    </MemoryRouter>
  );

test.each(['/signin', '/'])('ログイン中に %s を開くと /snaps へ移動する', (path) => {
  mockedUseAuth.mockReturnValue({ user: { id: 1, username: 'alice', email: '' } });
  renderAt(path);
  expect(screen.getByText('スナップ一覧')).toBeInTheDocument();
});

test('未ログインなら、サインイン画面をそのまま表示する', () => {
  mockedUseAuth.mockReturnValue({ user: null });
  renderAt('/signin');
  expect(screen.getByText('サインイン画面')).toBeInTheDocument();
});
