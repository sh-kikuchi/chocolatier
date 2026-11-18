# CORS と CSRF の設定（画面と API が別のポートで動くとき）

- 最終更新：2026-11-19（今の実装に合わせて書き直した。以前の「全部許可」の記録は git の履歴にある）
- 関連：[03_認証.md](03_認証.md)（Cookie と CSRF トークンの流れ）

## 1. なぜ設定が必要か
- 画面（React）は `http://localhost:3000`、API（Django）は `http://localhost:8000`。**ポートが違うと別のオリジン** になる。
- ブラウザは、別のオリジンの API のレスポンスを、相手（Django）が許可しない限り JS に渡さない（CORS：オリジン間リソース共有）。
- Chocolatier は Cookie で認証するので、さらに「Cookie を送ってよい」ことも許可する必要がある。

## 2. Backend（settings.py）

```python
INSTALLED_APPS = [
    ...
    'corsheaders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CommonMiddleware より前に置く
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    ...
]

CORS_ALLOWED_ORIGINS = ['http://localhost:3000']  # 許可する画面のオリジン（これ以外は拒否）
CORS_ALLOW_CREDENTIALS = True                     # Cookie の送受信を許可
CSRF_TRUSTED_ORIGINS = ['http://localhost:3000']  # CSRF チェックで信頼するオリジン
```

| 設定 | 意味 | 外すとどうなるか |
|---|---|---|
| `CorsMiddleware` を上の方に置く | レスポンスに `Access-Control-Allow-*` を付ける | 下に置くと、ほかのミドルウェアが先に返したレスポンス（リダイレクトなど）に CORS ヘッダーが付かず、ブラウザでエラーになる |
| `CORS_ALLOWED_ORIGINS` | 許可するオリジンの一覧 | Cookie を使うときは「全部許可（`*`）」が使えない（ブラウザの決まり）ので、オリジンを書く |
| `CORS_ALLOW_CREDENTIALS = True` | `Access-Control-Allow-Credentials: true` を返す | Cookie 付きのリクエストのレスポンスを、ブラウザが JS に渡さない |
| `CSRF_TRUSTED_ORIGINS` | 更新系のリクエストの `Origin` ヘッダーを信頼する | CSRF トークンが正しくても 403（`CSRF Failed: Origin checking failed`） |

## 3. Frontend（api/client.ts）

```ts
const client = axios.create({
  baseURL: API_BASE_URL,          // 既定は http://localhost:8000（REACT_APP_API_BASE_URL で変えられる）
  withCredentials: true,          // 別オリジンでも Cookie を送受信する
  withXSRFToken: true,            // csrftoken Cookie を読んで…
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',  // …このヘッダーに付ける
});
```
- API は必ずこの `client` で呼ぶ（`axios` を直接使わない）。`withCredentials` を付け忘れると Cookie が送られず、401 になる。
- `withXSRFToken: true` は、別オリジンでも CSRF ヘッダーを付けるための設定（axios 1.6 以降）。

## 4. 画像（img タグ）と Cookie
- `<img src="http://localhost:8000/media/...">` は CORS の対象外（画像は表示するだけで、JS が中身を読まない）。
- `localhost:3000` と `localhost:8000` は **ポートが違っても「同じサイト」** 扱いなので、`SameSite=Lax` の Cookie（access_token）も `<img>` の取得に付いて送られる。
  → 画像の配信（`/media/`）でも、ログインしている持ち主かを確かめられる（[05_スナップAPIと画像.md](05_スナップAPIと画像.md)）。

## 5. つまずきやすいところ
| 症状 | 原因 | 対処 |
|---|---|---|
| ブラウザのコンソールに `blocked by CORS policy` | 画面のオリジンが `CORS_ALLOWED_ORIGINS` にない（`127.0.0.1:3000` で開いた、など） | `localhost:3000` で開く。別のオリジンを使うなら 3 つの設定すべてに足す |
| ログインしたのに 401 | `withCredentials` がない（`axios` を直接使った） | `client` を使う |
| POST だけ 403 `Origin checking failed` | `CSRF_TRUSTED_ORIGINS` にない | 足す |
| POST だけ 403 `CSRF token missing` | 先に `GET /csrf/` を呼んでいない／`X-CSRFToken` がない | 画面は起動時に `/csrf/` を呼んでいる（`AuthContext`）。Postman は [03_認証.md](03_認証.md) の手順 |
