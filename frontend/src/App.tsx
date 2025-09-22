import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
// 本アプリの画面
import SignInPage from './pages/SignInPage/SignInPage';
import SnapshotPage from './pages/SnapshotPage/SnapshotPage';
import Layout from './components/commons/Layout/Layout';
import PlayGroundPage from './pages/PlayGroundPage/PlayGroundPage';
import WelcomePage from './pages/WelcomePage/WelcomePage';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/snaps" element={<SnapshotPage />} />
            <Route path="/signin" element={<SignInPage />} />
            <Route path="/playground" element={<PlayGroundPage />} />
            <Route path="/" element={<WelcomePage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
