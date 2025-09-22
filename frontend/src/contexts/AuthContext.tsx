import { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import axios from 'axios';
import { AuthContextType, User } from '../types/AuthContextType';

// AuthContextの作成
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// カスタムフック
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}

// AuthProvider の props 型
interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps): JSX.Element {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      fetchUserInfo(token);
    } else {
      setLoading(false);
    }
  }, []);

  // ユーザー情報取得
  const fetchUserInfo = async (token: string): Promise<void> => {
    try {
      const response = await axios.get<User>('http://localhost:8000/chocolatier_api/user-info/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user info', error);
    } finally {
      setLoading(false);
    }
  };

  // ログイン
  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const response = await axios.post<{ access: string; refresh: string }>(
        'http://localhost:8000/token/',
        { username, password }
      );
      localStorage.setItem('access_token', response.data.access);
      localStorage.setItem('refresh_token', response.data.refresh);
      await fetchUserInfo(response.data.access);
      return true;
    } catch (error) {
      console.error('Login failed', error);
      return false;
    }
  };

  // ログアウト
  const logout = (): void => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  const value: AuthContextType = { user, setUser, login, logout };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}
