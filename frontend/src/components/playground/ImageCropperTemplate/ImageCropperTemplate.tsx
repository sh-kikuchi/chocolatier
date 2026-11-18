import { useEffect, useState } from 'react';
import FileInput from '../../commons/FileInput/FileInput';
import ImageCropper from '../../commons/ImageCropper/ImageCropper';
import BasicButton from '../../commons/BasicButton/BasicButton';

// =====================================================
// ImageCropperTemplate：playground で ImageCropper を試す画面
// - ① 画像を選ぶ → ② ImageCropper で切り抜く → ③ 結果を表示する
// - 投稿画面（SnapshotPage）につなぐ前に、ここで操作感と結果を確かめる
// =====================================================
function ImageCropperTemplate() {
  // ① 状態
  //    - sourceFile：選んだ元の画像（null なら未選択）
  //    - croppedFile：切り抜いた画像（null ならまだ）
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [croppedFile, setCroppedFile] = useState<File | null>(null);

  // ② 切り抜いた画像の表示用 URL
  //    - 作る処理と破棄する処理を、同じ useEffect の中に書く（ImageCropper の ② と同じ理由：StrictMode 対策）
  const [croppedUrl, setCroppedUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!croppedFile) {
      setCroppedUrl(null);
      return;
    }
    const url = URL.createObjectURL(croppedFile);
    setCroppedUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [croppedFile]);

  // 最初からやり直す（両方の状態を戻す）
  const reset = () => {
    setSourceFile(null);
    setCroppedFile(null);
  };

  // ③ 画面（状態によって出すものを切り替える）
  return (
    <div>
      <h2>ImageCropper</h2>

      {/* 未選択 → 画像を選ぶ */}
      {!sourceFile && (
        <FileInput
          onUploadFile={(file) => {
            setSourceFile(file);
            setCroppedFile(null);
          }}
        />
      )}

      {/* 選んだがまだ切り抜いていない → 範囲を選ぶ */}
      {sourceFile && !croppedFile && (
        <ImageCropper file={sourceFile} onConfirm={setCroppedFile} onCancel={reset} />
      )}

      {/* 切り抜いた → 結果を表示する */}
      {croppedFile && croppedUrl && (
        <div>
          <img src={croppedUrl} alt="切り抜いた画像" style={{ width: 200 }} />
          <p>ファイル名：{croppedFile.name}</p>
          <p>形式：{croppedFile.type}</p>
          <p>サイズ：{(croppedFile.size / 1024).toFixed(1)} KB</p>
          <BasicButton type="button" onclickAction={reset}>もう一度試す</BasicButton>
        </div>
      )}
    </div>
  );
}

export default ImageCropperTemplate;
