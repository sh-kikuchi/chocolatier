import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';

// =====================================================
// GuestRoute（改修案件08）
// - 「ログインしていない人のための」ページを囲むためのルート（App.tsx で使用）
//   例：Welcome（/）・サインイン（/signin）
// - ログイン中なら、スナップ一覧（/snaps）へ移動させる
//   → ログイン中の人にとっての入口（エントリーポイント）は /snaps
// - 未ログインなら <Outlet />（囲んだ子ルートのページ）をそのまま表示する
// - ProtectedRoute（ログインが必要なページ用）の逆の働き
// =====================================================
function GuestRoute() {
  const { user } = useAuth();

  if (user) {
    // replace: ブラウザの「戻る」で、サインイン画面などに戻らないようにする
    return <Navigate to="/snaps" replace />;
  }
  return <Outlet />;
}

export default GuestRoute;
