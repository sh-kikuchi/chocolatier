import type { Area } from 'react-easy-crop';  // 切り抜く範囲の型 { x, y, width, height }（ピクセル）

// =====================================================
// 画像の切り抜き（アップロード前にブラウザの中で行う）
// - react-easy-crop は「どこを切るか」を教えてくれるだけ
// - 実際に切り抜くのはこのファイル（canvas に描いて、画像ファイルに戻す）
// =====================================================

// 切り抜いた画像の 1 辺の最大サイズ（px）
// - これより大きい範囲を選んだときは縮小する（ファイルサイズを抑えるため）
export const MAX_CROP_SIZE = 1080;

// 拡張子 → 出力する画像の形式
// - gif は png にする（canvas はアニメーションを扱えず、1 コマ目の静止画になるため）
const OUTPUT_TYPES: Record<string, string> = {
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  webp: 'image/webp',
  gif: 'image/png',
};

// ファイル名から拡張子を小文字で取り出す（"photo.JPG" → "jpg"）
const getExtension = (fileName: string): string => fileName.split('.').pop()?.toLowerCase() ?? '';

// 出力する形式（MIME タイプ）を決める
export const getOutputType = (fileName: string): string =>
  OUTPUT_TYPES[getExtension(fileName)] ?? 'image/png';

// 出力するファイル名を決める（gif だけ拡張子を png に付け替える）
// - "anime.gif" → "anime.png"、"photo.jpeg" → "photo.jpeg"（そのまま）
export const getOutputName = (fileName: string): string =>
  fileName.replace(/\.gif$/i, '.png');

// =====================================================
// 画像を読み込む
// - new Image() の読み込みは「終わったら onload が呼ばれる」形なので、
//   await で待てるように Promise に包む
// =====================================================
const loadImage = (src: string): Promise<HTMLImageElement> =>
  new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('画像を読み込めませんでした'));
    image.src = src;
  });

// =====================================================
// 画像を切り抜いて、新しい File を返す
// - file：選んだ元の画像
// - area：切り抜く範囲（元画像のピクセルで。react-easy-crop の croppedAreaPixels）
// =====================================================
export const cropImage = async (file: File, area: Area, maxSize = MAX_CROP_SIZE): Promise<File> => {
  // ① 元の画像を読み込む
  //    - File は直接 <img> に渡せないので、一時的な URL を付ける（previewUrl と同じ仕組み）
  const url = URL.createObjectURL(file);
  try {
    const image = await loadImage(url);

    // ② 出力サイズを決める
    //    - 1:1 なので幅と高さは同じ。maxSize を超えるなら縮小する
    const size = Math.min(Math.round(area.width), maxSize);

    // ③ canvas に範囲を描く
    //    - canvas：JS で絵を描ける画面に出ない「キャンバス」
    //    - getContext('2d')：canvas に描くための道具箱（平面の描画用）を取り出す
    //      用意できないと null が返るので、if で弾く
    //    - drawImage の 9 個の引数：
    //        image,                                    何を
    //        area.x, area.y, area.width, area.height,  元画像の「どこ」を（切り抜く範囲）
    //        0, 0, size, size                          canvas の「どこ」に（この大きさに縮めて描く）
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const context = canvas.getContext('2d');
    if (!context) throw new Error('この環境では画像を加工できません');
    context.drawImage(image, area.x, area.y, area.width, area.height, 0, 0, size, size);

    // ④ canvas → Blob（画像のデータ）
    //    - toBlob も「終わったら関数が呼ばれる」形なので、Promise に包む
    //    - 0.9：jpeg / webp の画質（0〜1）。png では無視される
    const type = getOutputType(file.name);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, type, 0.9));
    if (!blob) throw new Error('画像を作れませんでした');

    // ⑤ Blob → File
    //    - FormData で送るときにファイル名が必要なので、File にする
    //    - File は「名前の付いた Blob」
    return new File([blob], getOutputName(file.name), { type });
  } finally {
    // ⑥ 一時的な URL を破棄する（成功しても失敗しても）
    URL.revokeObjectURL(url);
  }
};
