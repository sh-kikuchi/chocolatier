import { useState, useEffect, useCallback, useRef } from 'react';
import '../SnapshotPage/SnapshotPage.css';
import SnapshotPanel from '../../components/snap/SnapshotPanel/SnapshotPanel';
import Container from '../../components/commons/Container/Container';
import BasicButton from '../../components/commons/BasicButton/BasicButton';
import Modal from '../../components/commons/Modal/Modal';
import LongText from '../../components/commons/LongText/LongText';
import FileInput from '../../components/commons/FileInput/FileInput';
import Message from '../../components/commons/Message/Message';
import TagInput from '../../components/commons/TagInput/TagInput';
import ImageCropper from '../../components/commons/ImageCropper/ImageCropper';
import client, { MEDIA_URL } from '../../api/client';  // API 呼び出しは共通の client を使う
import { getApiErrorMessages, getApiErrorMessagesFromBlob } from '../../utils/apiError';
import { MAX_COMMENT_LENGTH, MAX_ZIP_DOWNLOAD, validateComment, validateImageSize } from '../../utils/validators';
import { Snap, SnapPage } from '../../types/Snap';
import { useInfiniteScroll } from '../../hooks/useInfiniteScroll';

// Snapshotページのメインコンポーネント
function SnapshotPage() {
  // =====================================================
  // 状態管理
  // =====================================================
  const [snaps, setSnaps] = useState<Snap[]>([]);      // スナップ一覧
  const [snap, setSnap] = useState<Snap | null>();     // モーダルで選択中のスナップ
  const [showModal, setShowModal] = useState(false);   // モーダル開閉状態
  const [text, setText] = useState('');                // コメント入力
  // 新規作成の画像は 2 段階で持つ（改修案件6：アップロード前の 1:1 トリミング）
  // - sourceFile：選んだ元の画像（トリミング前）
  // - file：トリミングした後の画像（これを送る）
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [errorMessages, setErrorMessages] = useState<string[]>([]); // モーダルに出すエラー
  const [tags, setTags] = useState<string[]>([]);                   // モーダルで編集中のタグ
  const [tagOptions, setTagOptions] = useState<string[]>([]);       // 絞り込みの候補（自分が使っているタグ）
  const [selectedTag, setSelectedTag] = useState<string | null>(null); // 絞り込み中のタグ（null は「すべて」）
  const [nextUrl, setNextUrl] = useState<string | null>(null); // 続きを取る URL（null なら最後まで読んだ）
  const [loading, setLoading] = useState(false);               // 一覧を読み込み中か
  const [downloading, setDownloading] = useState(false);       // Zip をダウンロード中か（連打防止）
  // Zip ダウンロードの結果のお知らせ（モーダルの外なので、errorMessages とは別に持つ）
  // - mode：info（100 件を超えたお知らせ）／ error（失敗）
  const [downloadNotice, setDownloadNotice] = useState<{ messages: string[]; mode: 'info' | 'error' } | null>(null);

  // =====================================================
  // ファイルプレビューURLの生成とクリーンアップ
  // - file（トリミング後）が変わるたび、新しい previewUrl を作り、古い URL は破棄する（メモリリーク防止）
  // - 作る処理と破棄する処理を、同じ useEffect の中に書く
  //   以前は useMemo で作って useEffect で破棄していたが、StrictMode では開発中に
  //   useEffect が「実行 → 後片付け → 実行」と 2 回動くため、破棄済みの URL が残って
  //   プレビューが表示されなかった（ImageCropper の ② と同じ）
  // =====================================================
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // =====================================================
  // ファイル選択・モーダル操作
  // =====================================================
  // 画像を選んだとき：元画像として持ち、トリミング画面を出す（前のトリミング結果は消す）
  const handleFileUpload = useCallback((selectedFile: File) => {
    setSourceFile(selectedFile);
    setFile(null);
  }, []);

  // 画像を選び直す（トリミング画面の「選び直す」・プレビューの「画像を選び直す」）
  // - 2 つの状態を両方戻す（片方だけだと、古い画像が残る）
  const resetImage = useCallback(() => {
    setSourceFile(null);
    setFile(null);
  }, []);

  const openModal = (prmSnap?: Snap) => {
    if (prmSnap) {
      setSnap(prmSnap);
      setText(prmSnap.comment);
      setTags(prmSnap.tags);
    } else {
      setSnap(null);
      setTags([]);
    }
    setErrorMessages([]);  // 前回のエラーを残さない
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    resetImage();
    setText('');
    setTags([]);
    setErrorMessages([]);
  };

  // =====================================================
  // データ取得・初期化（12 件ずつ）
  // - 最初の 12 件：初回とタグを切り替えたときに取り直す
  // - 続き：一覧の一番下が見えたら、nextUrl の続きを取って後ろに足す
  // - 認証は Cookie で自動送信されるので、ヘッダーの指定は不要
  // =====================================================

  // ① 何回目のリクエストかを数える
  //    - 読み込み中にタグを切り替えると、古いタグの結果があとから届くことがある
  //    - 最後に出したリクエストの結果だけを使うために、番号で見分ける
  //    - useRef：値が変わっても再描画しない。画面に出さない値の保存に使う
  const requestIdRef = useRef(0);

  // ② 1 ページ分を取得して、一覧に反映する（③と④で使う共通の処理）
  //    - append=false：一覧を置き換える（最初の 12 件）
  //    - append=true ：一覧の後ろに足す（続き）
  const fetchPage = useCallback(
    async (url: string, params: Record<string, string>, append: boolean) => {
      // ②-1 このリクエストの番号を取る
      const requestId = ++requestIdRef.current;
      setLoading(true);
      try {
        // ②-2 取得する
        //      - params：axios が URL の ?tag=〇〇 を作ってくれる（日本語も自動でエンコードされる）
        const response = await client.get<SnapPage>(url, { params });

        // ②-3 待っている間に、新しいリクエストが出ていたら捨てる
        if (requestId !== requestIdRef.current) return;

        // ②-4 一覧と、続きの URL を反映する
        setSnaps((prev) => (append ? [...prev, ...response.data.results] : response.data.results));
        setNextUrl(response.data.next);
      } catch (error) {
        // ②-5 失敗したら、自動での読み込みを止める
        //      - nextUrl を残すと、目印が見えている間ずっと失敗をくり返してしまうため
        //      - 一覧の取得失敗はモーダルの外なので、ログだけ出す
        console.error('一覧の取得に失敗しました:', error);
        if (requestId === requestIdRef.current) setNextUrl(null);
      } finally {
        // ②-6 最後に出したリクエストのときだけ、読み込み中を解除する
        if (requestId === requestIdRef.current) setLoading(false);
      }
    },
    []
  );

  // ③ 最初の 12 件（初回と、タグを切り替えたとき）
  //    - 前のタグの一覧と続きの URL を消してから取り直す
  //    - 「すべて」のときは params を空にして、絞り込まない
  useEffect(() => {
    setSnaps([]);
    setNextUrl(null);
    fetchPage('/chocolatier_api/snap/', selectedTag ? { tag: selectedTag } : {}, false);
  }, [selectedTag, fetchPage]);

  // ④ 続きの 12 件（一覧の一番下が見えたとき）
  //    - nextUrl には cursor と tag がすでに入っているので、params は空でよい
  const loadMore = useCallback(() => {
    if (!nextUrl || loading) return;
    fetchPage(nextUrl, {}, true);
  }, [nextUrl, loading, fetchPage]);

  // ⑤ 一覧の一番下の目印を監視する（続きがあって、読み込み中でないときだけ）
  const sentinelRef = useInfiniteScroll(loadMore, nextUrl !== null && !loading);

  // 絞り込みの候補（自分の Snap に付いているタグ）を取得する
  // - 初回と、作成・更新・削除のあと（タグが増減するため）に呼ぶ
  const fetchTags = useCallback(async () => {
    try {
      const response = await client.get<string[]>('/chocolatier_api/tags/');
      setTagOptions(response.data);
      // 絞り込み中のタグが、どの Snap からも外れて候補から消えたら「すべて」に戻す
      // （そのままだと、0 件の一覧が表示されたままになるため）
      setSelectedTag((prev) => (prev && !response.data.includes(prev) ? null : prev));
    } catch (error) {
      console.error('タグの取得に失敗しました:', error);
    }
  }, []);

  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  // 作成・更新したスナップが、今の絞り込みに合うか
  // - 「すべて」のときは常に合う
  const matchesFilter = (target: Snap) => !selectedTag || target.tags.includes(selectedTag);

  // =====================================================
  // CRUD操作
  // =====================================================
  // 新規作成
  const handleCreateSubmit = async () => {
    // 送る前のチェック
    // - 形式（拡張子）は FileInput で、選んだときにチェック済み
    // - サイズは、トリミングした後の画像でここでチェックする（大きな写真も、切り抜けば投稿できるため）
    const errors = [
      !file ? (sourceFile ? '画像の範囲を「決定」してください' : '画像を選択してください') : null,
      file ? validateImageSize(file) : null,
      validateComment(text),
    ].filter((message): message is string => message !== null);
    if (errors.length > 0 || !file) return setErrorMessages(errors);

    // FormData を渡すと、axios が Content-Type（multipart/form-data）を自動で付ける
    const formData = new FormData();
    formData.append('comment', text);
    formData.append('upload', file);
    // tags は同じキーで繰り返し入れる（tags=旅行 & tags=カフェ）
    // - Backend の ListField が、同じキーの値をまとめて配列として受け取る
    // - タグがなければ何も入れない（Backend では「タグなし」になる）
    tags.forEach((tag) => formData.append('tags', tag));
    // user は送らない（サーバーがログインユーザーを設定する。なりすまし防止）

    try {
      const response = await client.post('/chocolatier_api/snap/create/', formData);
      // 一覧は新しい順なので先頭に追加（絞り込みに合わないときは追加しない）
      if (matchesFilter(response.data)) {
        setSnaps((prev) => [response.data, ...prev]);
      }
      fetchTags();  // 新しいタグが増えたかもしれないので、候補を取り直す
      closeModal();
    } catch (error) {
      handleApiError(error);
    }
  };

  // 更新
  const handleUpdateSubmit = async () => {
    if (!snap) return;

    // 送る前のチェック
    const commentError = validateComment(text);
    if (commentError) return setErrorMessages([commentError]);

    try {
      // 画像は変えないので JSON で送る
      // - tags は配列のまま送る。空の配列 [] なら、タグをすべて外す
      const response = await client.patch<Snap>(
        `/chocolatier_api/snap/${snap.id}/`,
        { comment: text, tags }
      );

      // レスポンスは一覧と同じ形（id・filePath・tags なども入っている）なので、そのまま置き換える
      // - 絞り込み中のタグを外したときは、一覧から取り除く
      const updated = response.data;
      setSnaps((prevSnaps) =>
        matchesFilter(updated)
          ? prevSnaps.map((s) => (s.id === updated.id ? updated : s))
          : prevSnaps.filter((s) => s.id !== updated.id)
      );
      fetchTags();  // タグが増減したかもしれないので、候補を取り直す
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
      fetchTags();  // そのタグを使っていた最後の Snap なら、候補から消える
      closeModal();
    } catch (error) {
      handleApiError(error);
    }
  };

  // =====================================================
  // Zip ダウンロード
  // - 表示中の Snap（絞り込み＋無限スクロールで読み込んだ分）の画像を Zip で保存する
  // - Zip を作るのは Backend。ここでは ID を送って、返ってきた Zip を保存させるだけ
  // =====================================================
  const handleDownload = async () => {
    // ① ダウンロード中・0 件なら何もしない（ボタンも押せなくしているが、念のため）
    if (downloading || snaps.length === 0) return;

    // ② 送る ID を集める
    //    - snaps は新しい順なので、先頭から 100 件 ＝ 新しい順に 100 件
    //    - Backend でも 101 件以上は 400 にしている（こちらは送る前に合わせるため）
    const ids = snaps.slice(0, MAX_ZIP_DOWNLOAD).map((s) => s.id);
    const folderName = selectedTag ?? 'すべて';

    setDownloading(true);
    setDownloadNotice(null);  // 前回のお知らせを消す
    try {
      // ③ Zip を受け取る
      //    - responseType: 'blob'：中身を文字ではなく、ファイル（Blob）のまま受け取る
      //      付けないと axios が文字として読もうとして、Zip が壊れる
      //    - 「すべて」のときは tag を送らない（Backend がフォルダ名を「すべて」にする）
      const response = await client.post<Blob>(
        '/chocolatier_api/snap/download/',
        selectedTag ? { ids, tag: selectedTag } : { ids },
        { responseType: 'blob' }
      );

      // ④ 保存させる
      //    - createObjectURL：Blob に一時的な URL を付ける（previewUrl と同じ仕組み）
      //    - <a download="名前"> をクリックすると、ブラウザがその名前で保存する
      //    - ファイル名はここで決める（サーバーの Content-Disposition は、
      //      CORS の設定を足さないと JS から読めないため）
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${folderName}.zip`;
      document.body.appendChild(link);  // ブラウザによっては、ページに置かないと click が効かない
      link.click();
      link.remove();

      // ⑤ 一時的な URL を破棄する（メモリリーク防止）
      URL.revokeObjectURL(url);

      // ⑥ 100 件を超えていたら、全部は入っていないことを知らせる
      if (snaps.length > MAX_ZIP_DOWNLOAD) {
        setDownloadNotice({
          messages: [`表示中の ${snaps.length} 枚のうち、新しい順に ${MAX_ZIP_DOWNLOAD} 枚をダウンロードしました`],
          mode: 'info',
        });
      }
    } catch (error) {
      // ⑦ 失敗したら、ボタンの下にエラーを出す
      //    - エラーの本文も Blob で届くので、読んでから変換する
      console.error('Zip のダウンロードに失敗しました:', error);
      setDownloadNotice({ messages: await getApiErrorMessagesFromBlob(error), mode: 'error' });
    } finally {
      setDownloading(false);
    }
  };

  // =====================================================
  // エラーハンドリング
  // - API のエラー（400 の入力チェックなど）をモーダル内に表示する
  //   例：{"upload": ["画像サイズは5MB以下にしてください"]} → 「画像：画像サイズは5MB以下にしてください」
  // - 401（ログイン切れ）は client.ts が refresh を試し、
  //   それでもダメなら ProtectedRoute がサインイン画面へ移動させる
  // =====================================================
  const handleApiError = (error: unknown) => {
    console.error('APIエラー:', error);
    setErrorMessages(getApiErrorMessages(error));
  };

  // =====================================================
  // JSXレンダリング
  // =====================================================
  return (
    <Container className="container">
      <div>
        {/* 1 段目：新規作成（左）と Zip ダウンロード（右）
            - Zip のボタンの文字に、選んでいるタグ名と枚数を入れて、「今の絞り込みで表示中の一覧」が
              対象だとわかるようにする（タグを切り替える・スクロールで読み込むと変わる）
            - 0 件・ダウンロード中は押せない */}
        <div className="snapActions">
          <BasicButton onclickAction={() => openModal()}>新規作成</BasicButton>
          <div className="downloadArea">
            {/* 100 件を超えたら、全部は入らないことを先に知らせる */}
            {snaps.length > MAX_ZIP_DOWNLOAD && (
              <span className="downloadNote">
                表示中の {snaps.length} 枚のうち、新しい {MAX_ZIP_DOWNLOAD} 枚まで
              </span>
            )}
            <BasicButton
              onclickAction={handleDownload}
              disabled={snaps.length === 0 || downloading}
            >
              {downloading
                ? 'Zip を作成中...'
                : `${selectedTag ? `「${selectedTag}」` : 'すべて'}の ${Math.min(snaps.length, MAX_ZIP_DOWNLOAD)} 枚を Zip でダウンロード`}
            </BasicButton>
          </div>
        </div>

        {/* Zip ダウンロードの結果（100 件を超えたお知らせは 5 秒で消す。エラーは残す） */}
        {downloadNotice?.messages.map((message) => (
          <Message
            key={message}
            message={message}
            mode={downloadNotice.mode}
            duration={downloadNotice.mode === 'info' ? 5000 : undefined}
          />
        ))}

        {/* 2 段目：タグの絞り込み：「すべて」＋自分が使っているタグをチップで並べる */}
        <div className="tagFilter">
          <button
            type="button"
            className={`tagFilterChip ${selectedTag === null ? 'tagFilterChipActive' : ''}`}
            onClick={() => setSelectedTag(null)}
          >
            すべて
          </button>
          {tagOptions.map((tag) => (
            <button
              key={tag}
              type="button"
              className={`tagFilterChip ${selectedTag === tag ? 'tagFilterChipActive' : ''}`}
              onClick={() => setSelectedTag(tag)}
            >
              {tag}
            </button>
          ))}
        </div>

        <div className="flexArea">
          {snaps.map((snap, index) => (
            <SnapshotPanel
              key={snap.id}
              prmPhoto={snap}
              indexNum={index}
              onclickAction={() => openModal(snap)}
            />
          ))}
        </div>

        {/* 無限スクロールの目印：これが画面に入ったら続きを読み込む */}
        <div ref={sentinelRef} className="scrollSentinel" />
        {loading && <p className="loadingText">読み込み中...</p>}
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

            {/* エラーメッセージ（送る前のチェック・API のエラー） */}
            {errorMessages.map((message) => (
              <Message key={message} message={message} mode="error" />
            ))}

            {/* 新規作成の画像：① 選ぶ → ② トリミング → ③ プレビュー の順に切り替える */}
            {!snap && !sourceFile && <FileInput onUploadFile={handleFileUpload} />}
            {!snap && sourceFile && !file && (
              <ImageCropper file={sourceFile} onConfirm={setFile} onCancel={resetImage} />
            )}
            {!snap && file && previewUrl && (
              <div>
                <img className="filePreview filePreviewLarge" src={previewUrl} alt="preview" />
                <div>
                  <button type="button" className="reselectImageButton" onClick={resetImage}>
                    画像を選び直す
                  </button>
                </div>
              </div>
            )}

            {/* 詳細（更新）：画像は変えられないので、登録済みの画像を表示するだけ */}
            {snap && (
              <img className="filePreview filePreviewLarge" src={`${MEDIA_URL}${snap.filePath}`} alt="preview" />
            )}

            <LongText
              placeholder="思い出話など自由に書いてください"
              value={text}
              onChangeText={setText}
              rows={5}
            />
            {/* 文字数カウンター：上限を超えたら赤くする */}
            <div
              className="commentCounter"
              style={text.length > MAX_COMMENT_LENGTH ? { color: '#c62828' } : undefined}
            >
              {text.length} / {MAX_COMMENT_LENGTH}
            </div>

            {/* タグ：Enter で追加・× で削除。値（tags）はこのページが持つ */}
            <div className="modalTagArea">
              <TagInput tags={tags} onChangeTags={setTags} />
            </div>
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
