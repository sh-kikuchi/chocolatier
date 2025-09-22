import '../WelcomePage/WelcomePage.css';
import logo from '../../assets/images/logo.png'; // ロゴ画像
import { Link, useNavigate } from 'react-router-dom';
import BasicButton from '../../components/commons/BasicButton/BasicButton';

function WelcomePage() {
  const navigate = useNavigate();

  const handleMoveToSignInPage = () => {
    navigate('/signin');
  }

  return (
    <div className="welcomeContainer">
      {/* ロゴ */}
      <div className="welcomeLogo">
        <img src={logo} alt="App Logo" />
      </div>

      {/* キャッチコピー */}
      <h1 className="welcome-title">Chocolatier</h1>
      <p>
        自分の思い出や日常の瞬間を写真として投稿し、コメントを添えて個人アルバムのように保存できます。
        写真のアップロードやコメント入力など、さまざまな便利な機能を簡単に使えます。
      </p>
      {/* サインインボタン */}
      <div className="welcome-buttons">
        <BasicButton
          type="button"
          onclickAction={handleMoveToSignInPage}
        >
          サインインページはこちら
        </BasicButton>
      </div>
      <hr />
      <div>
        <h2>UI コンポーネント集 <br /> Chocolate Factory</h2>
        <div className="component-cards">
          <Link to="/playground" className="component-link">
            詳しくはこちら
          </Link>
        </div>
      </div>
    </div>
  );
}

export default WelcomePage;
