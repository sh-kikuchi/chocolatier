import { useState, useEffect, useMemo, useCallback } from 'react';
import '../SnapshotPage/SnapshotPage.css';
import SnapshotPanel from '../../components/snap/SnapshotPanel/SnapshotPanel';
import Container from '../../components/commons/Container/Container';
import BasicButton from '../../components/commons/BasicButton/BasicButton';
import Modal from '../../components/commons/Modal/Modal';
import LongText from '../../components/commons/LongText/LongText';
import FileInput from '../../components/commons/FileInput/FileInput';
import axios from 'axios';  // エラー判定（axios.isAxiosError）にだけ使う
import client, { MEDIA_URL } from '../../api/client';  // API 呼び出しは共通の client を使う

// スナップの型定義
interface Snap {
  id: number;
  comment: string;
  filePath: string;
}

// Snapshotページのメインコンポーネント
function SnapshotPage() {
  // =====================================================
  // 状態管理
  // =====================================================
  const [snaps, setSnaps] = useState<Snap[]>([]);      // スナップ一覧
  const [snap, setSnap] = useState<Snap | null>();     // モーダルで選択中のスナップ
  const [showModal, setShowModal] = useState(false);   // モーダル開閉状態
  const [text, setText] = useState('');                // コメント入力
  const [file, setFile] = useState<File | null>(null); // 新規作成用ファイル

  // =====================================================
  // ファイルプレビューURLの生成とクリーンアップ
  // - file が変わるたび新しい previewUrl を生成（useMemo）
  // - 古い URL は useEffect で破棄（メモリリーク防止）
  // - useState と違い、更新関数（setter）は不要
  // =====================================================
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

    useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // =====================================================
  // ファイル選択・モーダル操作
  // =====================================================
  const handleFileUpload = useCallback((selectedFile: File | null) => {
    setFile(selectedFile);
  }, []);

  const openModal = (prmSnap?: Snap) => {
    if (prmSnap) {
      setSnap(prmSnap);
      setText(prmSnap.comment);
    } else {
      setSnap(null);
    }
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setFile(null);
    setText('');
  };

  // =====================================================
  // データ取得・初期化
  // - fetchSnaps は useCallback でメモ化 → 不要な再生成を防ぐ
  // - useEffect で初回マウント時に実行 → スナップ一覧を取得
  // - 依存配列に fetchSnaps を指定することで、fetchSnaps が変わった場合のみ再実行
  // - 認証は Cookie で自動送信されるので、ヘッダーの指定は不要
  //   （以前は localStorage のトークンを Authorization ヘッダーに付けていた）
  // =====================================================
  const fetchSnaps = useCallback(async () => {
    try {
      const response = await client.get('/chocolatier_api/snap/');
      setSnaps(response.data);
    } catch (error) {
      handleApiError(error);
    }
  }, []);

  useEffect(() => {
    fetchSnaps();
  }, [fetchSnaps]);

  // =====================================================
  // CRUD操作
  // =====================================================
  // 新規作成
  const handleCreateSubmit = async () => {
    if (!file) return alert('ファイルは必須です');

    // FormData を渡すと、axios が Content-Type（multipart/form-data）を自動で付ける
    const formData = new FormData();
    formData.append('comment', text);
    formData.append('upload', file);
    // user は送らない（サーバーがログインユーザーを設定する。なりすまし防止）

    try {
      const response = await client.post('/chocolatier_api/snap/create/', formData);
      setSnaps((prev) => [response.data, ...prev]);  // 一覧は新しい順なので先頭に追加
      closeModal();
    } catch (error) {
      handleApiError(error);
    }
  };

  // 更新
  const handleUpdateSubmit = async () => {
    if (!snap) return;

    try {
      // コメントだけなので JSON で送る
      // （以前は FormData なのに Content-Type: application/json を付けていた）
      const response = await client.patch(
        `/chocolatier_api/snap/${snap.id}/`,
        { comment: text }
      );

      setSnaps((prevSnaps) =>
        prevSnaps.map((s) => (s.id === snap.id ? { ...s, ...response.data } : s))
      );
      closeModal();
    } catch (error) {
      handleApiError(error);
    }
  };

  // 削除
  const handleDeleteSubmit = async () => {
    if (!snap) return;

    if (!window.confirm('本当に削除しますか？')) return;

    try {
      await client.delete(`/chocolatier_api/snap/${snap.id}/`);
      setSnaps((prevSnaps) => prevSnaps.filter((s) => s.id !== snap.id));
      closeModal();
    } catch (error) {
      handleApiError(error);
    }
  };

  // =====================================================
  // エラーハンドリング
  // - 401（ログイン切れ）は client.ts が refresh を試し、
  //   それでもダメなら ProtectedRoute がサインイン画面へ移動させるので、ここでは扱わない
  // =====================================================
  const handleApiError = (error: unknown) => {
    if (axios.isAxiosError(error)) {
      console.error('APIエラー:', error.response?.data);
    } else {
      console.error('想定外のエラー:', error);
    }
  };

  // =====================================================
  // クリーンアップ（ファイルURLの解放）
  // - file が変わるたび新しい previewUrl を生成する。
  // =====================================================
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // =====================================================
  // JSXレンダリング
  // =====================================================
  return (
    <Container className="container">
      <div>
        <BasicButton onclickAction={() => openModal()}>新規作成</BasicButton>

        <div className="flexArea">
          {snaps.map((snap, index) => (
            <SnapshotPanel
              key={index}
              prmPhoto={snap}
              indexNum={index}
              onclickAction={() => openModal(snap)}
            />
          ))}
        </div>
      </div>

      <Modal show={showModal} setShow={closeModal}>
        <div className="modalFlexArea">
          <div className="modalContents">
            <div className="modalDeleteArea">
              {snap && (
                <div className="modalDeleteButton" onClick={handleDeleteSubmit}>
                  削除
                </div>
              )}
            </div>

            <h2>{snap ? 'スナップ詳細' : 'スナップ作成'}</h2>

            {!snap && <FileInput onUploadFile={handleFileUpload} />}

            {(file || snap) && (
              <img
                className="filePreview"
                src={previewUrl ? previewUrl : `${MEDIA_URL}${snap?.filePath}`}
                alt="preview"
              />
            )}

            <LongText
              placeholder="思い出話など自由に書いてください"
              value={text}
              onChangeText={setText}
              rows={5}
            />

            <div>
              <BasicButton
                type="submit"
                value="save"
                onclickAction={snap ? handleUpdateSubmit : handleCreateSubmit}
              >
                保存
              </BasicButton>
            </div>
          </div>
        </div>
      </Modal>
    </Container>
  );
}

export default SnapshotPage;
