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
      const list = Array.isArray(value) ? value : [value];  // 念のため配列でない場合にも対応
      const label = FIELD_LABELS[field];
      return list.map((message) => (label ? `${label}：${message}` : String(message)));
    });
    if (messages.length > 0) return messages;
  }

  return ['エラーが発生しました'];
};
