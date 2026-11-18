import axios from 'axios';

// =====================================================
// API エラーを、画面に表示するメッセージに変換する
// - Django（DRF）のエラーレスポンスは主に次の 2 つの形
//   ① 入力チェックのエラー（400）：{ "upload": ["画像サイズは..."], "comment": ["..."] }
//   ② それ以外のエラー            ：{ "detail": "見つかりませんでした。" }
// - ① はフィールド名を日本語の項目名に置き換えて「画像：画像サイズは...」の形にする
// =====================================================

// フィールド名 → 画面に出す項目名
// - ここにないフィールドは、メッセージだけを表示する
const FIELD_LABELS: Record<string, string> = {
  upload: '画像',
  comment: 'コメント',
  tags: 'タグ',
};

// エラーの値を、メッセージ（文字列）の配列にする
// - 普通は ["..."] の配列
// - tags のような配列の項目で、要素ごとのエラーになると { "0": ["..."] } のようなオブジェクトになる
//   （"0" は何番目のタグか）。中身を取り出して、ふつうの配列にそろえる
const flattenMessages = (value: unknown): string[] => {
  if (Array.isArray(value)) return value.flatMap(flattenMessages);
  if (value && typeof value === 'object') return Object.values(value).flatMap(flattenMessages);
  return [String(value)];
};

export const getApiErrorMessages = (error: unknown): string[] => {
  // axios 以外のエラー（プログラムのバグなど）
  if (!axios.isAxiosError(error)) {
    return ['想定外のエラーが発生しました'];
  }

  // レスポンスがない＝サーバーに届いていない（Django が起動していない・ネットワーク切断など）
  if (!error.response) {
    return ['サーバーに接続できませんでした。時間をおいて再度お試しください'];
  }

  // 500 番台：サーバー側のエラー
  if (error.response.status >= 500) {
    return ['サーバーでエラーが発生しました'];
  }

  const data = error.response.data;

  // ② { detail: "..." } の形
  if (data && typeof data === 'object' && typeof data.detail === 'string') {
    return [data.detail];
  }

  // ① { フィールド名: [メッセージ, ...] } の形
  if (data && typeof data === 'object') {
    const messages = Object.entries(data).flatMap(([field, value]) => {
      const list = flattenMessages(value);  // 配列でない・入れ子の場合にも対応
      const label = FIELD_LABELS[field];
      return list.map((message) => (label ? `${label}：${message}` : message));
    });
    if (messages.length > 0) return messages;
  }

  return ['エラーが発生しました'];
};

// =====================================================
// Blob で受け取る API のエラーを、メッセージに変換する
// - responseType: 'blob'（Zip のダウンロードなど）で呼ぶと、
//   エラーのときの本文（{ "detail": "..." } など）も Blob で届く
// - Blob のままだと中身を読めないので、① 文字にして ② JSON に戻してから
//   getApiErrorMessages に渡す
// - Blob を読むのは非同期なので、この関数も async（呼ぶ側は await する）
// =====================================================
export const getApiErrorMessagesFromBlob = async (error: unknown): Promise<string[]> => {
  if (axios.isAxiosError(error) && error.response?.data instanceof Blob) {
    try {
      // ① Blob → 文字列  ② 文字列 → オブジェクト
      error.response.data = JSON.parse(await error.response.data.text());
    } catch {
      // JSON でない本文（500 の HTML など）は読まずに捨てる
      // → getApiErrorMessages が、ステータスコードから決まったメッセージを返す
      error.response.data = null;
    }
  }
  return getApiErrorMessages(error);
};
