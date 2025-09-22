import { useState } from 'react';
import '../SignInPage/SignInPage.css';
import BasicButton from '../../components/commons/BasicButton/BasicButton';
import TextInput from '../../components/commons/TextInput/TextInput';
import { useAuth } from '../../contexts/AuthContext';
import { Link, useNavigate } from 'react-router-dom';

function SignInPage() {
  // フォームの各項目値をuseStateで管理する。
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // AuthContextからlogin関数を取得
  const { login } = useAuth();
  
  // ナビゲーション用のフック
  const navigate = useNavigate();

  // ユーザー名の入力反映
  const handleUsernameChange = (newUsername: string) => {
    setUsername(newUsername);
  };

  // パスワードの入力反映
  const handlePasswordChange = (newPassword: string) => {
    setPassword(newPassword);
  };

  // 送信
  const handleSubmit = async() => {
     const success = await login(username, password);
     if (success) {
      navigate('/snaps');
    } else {
      console.error('Login failed');
    }
  };
  
  return (
    <div className='formArea'>
        <div>
          <h2>Sign In</h2>
          <div className = "formControl">
            <label>username</label>
            <TextInput value={username} onChangeText={handleUsernameChange} />
          </div>
          <div className = "formControl">
            <label>password</label>
            <TextInput type="password" value={password} onChangeText={handlePasswordChange} />
          </div>
          <div className = "formControl">
            <BasicButton type="submit" value="signin" onclickAction={()=>handleSubmit()}>Sign in</BasicButton>
          </div>
        </div>
    </div>
  );
}

export default SignInPage;
