import { Outlet } from "react-router-dom";
import Header from "../Header/Header";
import styles from './Layout.module.css';  
import Container from "../Container/Container";

function Layout() {
  return (
    <div>
      {/* 共通ヘッダー */}
      <Header />
      <main className={styles.main}>
        {/* 各ページのコンテンツ */}
        <Container>
          <Outlet />     
        </Container>
      </main>
    </div>
  );
}

export default Layout;
