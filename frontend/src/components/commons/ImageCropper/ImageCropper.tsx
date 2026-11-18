import { useCallback, useEffect, useState } from 'react';
import Cropper from 'react-easy-crop';                  // 範囲を選ぶ画面（ドラッグ・拡大縮小）
import type { Area, Point } from 'react-easy-crop';     // 型：Area は範囲 { x, y, width, height }、Point は位置 { x, y }
import styles from './ImageCropper.module.css';
import BasicButton from '../BasicButton/BasicButton';
import Message from '../Message/Message';
import { cropImage } from '../../../utils/cropImage';

// =====================================================
// ImageCropper：画像を 1:1 で切り抜く部品
// - ドラッグで位置、スライダーで拡大縮小を決めて、「決定」で切り抜く
// - 範囲を選ぶ画面は react-easy-crop、切り抜く処理は utils/cropImage.ts
// - 値（crop / zoom）は react-easy-crop の外（この部品）が持ち、
//   変わったら関数で知らせてもらう（TagInput の tags / onChangeTags と同じ考え方）
// =====================================================

type ImageCropperProps = {
  file: File;                          // 切り抜く元の画像
  onConfirm: (file: File) => void;     // 「決定」で、切り抜いた File を親に渡す
                                       // ※ react-easy-crop の onCropComplete と名前がかぶらないように onConfirm にする
  onCancel: () => void;                // 「選び直す」を押したとき
};

function ImageCropper({ file, onConfirm, onCancel }: ImageCropperProps) {
  // ① 状態
  //    - crop：画像をドラッグした位置
  //    - zoom：拡大率（1 = 等倍）
  //    - croppedAreaPixels：切り抜く範囲（元画像のピクセル）。最初はまだ決まっていないので null
  //    - cropping：切り抜き中か（「決定」の連打防止）
  //    - error：切り抜きに失敗したときのメッセージ
  const [crop, setCrop] = useState<Point>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null);
  const [cropping, setCropping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ② 元画像の一時的な URL
  //    - <Cropper> に渡すには URL が必要（File は直接渡せない）
  //    - 作る処理と破棄する処理を、同じ useEffect の中に書く（file が変わったら作り直す）
  //    - useMemo で作って useEffect で破棄する形にしないのは、StrictMode のため
  //      （開発中は useEffect が「実行 → 後片付け → 実行」と 2 回動く。useMemo は作り直さないので、
  //        破棄済みの URL が残って画像が表示されなくなる）
  const [imageUrl, setImageUrl] = useState<string | undefined>(undefined);
  useEffect(() => {
    const url = URL.createObjectURL(file);
    setImageUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // ③ 範囲が決まるたびに react-easy-crop から呼ばれる関数
  //    - 引数は (croppedArea, croppedAreaPixels) の 2 つ。使うのは 2 つ目（ピクセル）だけ
  //      1 つ目は割合（%）なので使わない。使わない引数は「_」から始まる名前にする
  //    - useCallback：描画のたびに関数が作り直されないようにする
  const handleCropComplete = useCallback((_croppedArea: Area, pixels: Area) => {
    setCroppedAreaPixels(pixels);
  }, []);

  // ④ 「決定」を押したとき
  //    - croppedAreaPixels がまだない・切り抜き中なら何もしない
  //    - cropImage で切り抜いて、onConfirm で親に渡す
  //    - finally：成功しても失敗しても、切り抜き中を解除する
  const handleConfirm = async () => {
    if (!croppedAreaPixels || cropping) return;
    setCropping(true);
    setError(null);
    try {
      onConfirm(await cropImage(file, croppedAreaPixels));
    } catch (e) {
      console.error('切り抜きに失敗しました:', e);
      setError('画像の切り抜きに失敗しました。別の画像でお試しください');
    } finally {
      setCropping(false);
    }
  };

  // ⑤ 画面
  return (
    <div>
      {error && <Message message={error} mode="error" />}

      {/* 範囲を選ぶ枠：<Cropper> は親いっぱいに広がるので、親（cropArea）に高さが必要 */}
      <div className={styles.cropArea}>
        <Cropper
          image={imageUrl}
          crop={crop}
          zoom={zoom}
          aspect={1}                          // 1:1 に固定
          onCropChange={setCrop}              // ドラッグしたら位置を更新
          onZoomChange={setZoom}              // ホイール・ピンチで拡大率を更新
          onCropComplete={handleCropComplete} // 動かし終わったら、切り抜く範囲を受け取る
        />
      </div>

      {/* 拡大縮小のスライダー（1〜3 倍） */}
      <input
        type="range"
        className={styles.zoomSlider}
        min={1}
        max={3}
        step={0.1}
        value={zoom}
        onChange={(e) => setZoom(Number(e.target.value))}  // value は文字列で来るので数値にする
        aria-label="拡大率"
      />

      <div className={styles.cropActions}>
        <BasicButton type="button" onclickAction={onCancel}>選び直す</BasicButton>
        <BasicButton type="button" onclickAction={handleConfirm} disabled={cropping || !croppedAreaPixels}>
          {cropping ? '切り抜き中...' : '決定'}
        </BasicButton>
      </div>
    </div>
  );
}

export default ImageCropper;
