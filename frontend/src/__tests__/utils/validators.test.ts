// =====================================================
// validators.ts / cropImage.ts のテスト（改修案件6）
// - 実行：frontend フォルダで npm test
// - canvas の描画（cropImage 本体）は jsdom にないので、ブラウザで確認する
//   ここでは「名前・形式を決める関数」と「チェックの関数」だけを確かめる
// =====================================================
import { MAX_UPLOAD_SIZE, validateImageExtension, validateImageSize } from '../../utils/validators';
import { getOutputName, getOutputType } from '../../utils/cropImage';

// 指定したバイト数の File を作る（中身は 0 で埋める）
const makeFile = (name: string, size = 1) => new File([new Uint8Array(size)], name);

describe('validateImageExtension（A1）', () => {
  test.each(['photo.jpg', 'photo.JPG', 'photo.jpeg', 'photo.png', 'anime.gif', 'photo.webp'])(
    '%s は通る',
    (name) => {
      expect(validateImageExtension(makeFile(name))).toBeNull();
    }
  );

  test.each(['photo.bmp', 'memo.txt', 'noextension'])('%s はエラー', (name) => {
    expect(validateImageExtension(makeFile(name))).toContain('アップロードできるのは');
  });
});

describe('validateImageSize（A2）', () => {
  test('5MB ちょうどは通る', () => {
    expect(validateImageSize(makeFile('a.png', MAX_UPLOAD_SIZE))).toBeNull();
  });

  test('5MB を 1 バイトでも超えたらエラー', () => {
    expect(validateImageSize(makeFile('a.png', MAX_UPLOAD_SIZE + 1))).toBe('画像サイズは 5MB 以下にしてください');
  });
});

describe('切り抜いた画像の名前と形式（A3）', () => {
  test.each([
    ['photo.jpeg', 'photo.jpeg', 'image/jpeg'],
    ['photo.JPG', 'photo.JPG', 'image/jpeg'],
    ['photo.png', 'photo.png', 'image/png'],
    ['photo.webp', 'photo.webp', 'image/webp'],
    ['anime.gif', 'anime.png', 'image/png'],   // gif は静止画の png になる
    ['ANIME.GIF', 'ANIME.png', 'image/png'],   // 大文字の拡張子も
    ['my.gif.jpg', 'my.gif.jpg', 'image/jpeg'], // 途中の「.gif」は付け替えない
  ])('%s → %s（%s）', (name, outputName, outputType) => {
    expect(getOutputName(name)).toBe(outputName);
    expect(getOutputType(name)).toBe(outputType);
  });
});
