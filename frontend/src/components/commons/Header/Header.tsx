import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';
import styles from './Header.module.css'; 

function Layout() {
  // AuthContextからユーザー情報とログアウト関数を取得
  const { logout } = useAuth();
  
  // ナビゲーション用のフック
  const navigate = useNavigate();

  //ホーム画面に戻る
  const handleGoHome = () => {
    navigate('/');
  }

  // ログイン状態を access_token の有無で判断
  const isLoggedIn = !!localStorage.getItem('access_token');

  // ログアウト処理
  const handleLogout = () => {
    logout();
    navigate('/signin');
  };

  return (
    // ヘッダー
    <header className={styles.siteHeader}>
      <div className={styles.headerContent}>
        <h1><span onClick={handleGoHome}>Chocolatier</span></h1>
          {isLoggedIn && (
          <span onClick={handleLogout}>ログアウト</span>
        )}
      </div>
    </header>
  );
}

export default Layout;
