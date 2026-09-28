import styles from './SnapshotPanel.module.css';
import { MEDIA_URL } from '../../../api/client';  // 画像の URL は client.ts で一元管理

interface Photo {
  id: number;
  comment: string;
  filePath: string;
}

interface SnapshotPanelProps {
  prmPhoto: Photo;      // 個別スナップ情報
  indexNum: number;     // 配列インデックスなど
  onclickAction?: () => void; // クリック時のハンドラ
}

function SnapshotPanel({ prmPhoto, indexNum, onclickAction }: SnapshotPanelProps) {
  return (
    <div className={styles.snapshotPanel} onClick={onclickAction}>
      <img
        src={`${MEDIA_URL}${prmPhoto.filePath}`}
        className={styles.snapshotPanelImg}
        alt={`snap-${indexNum}`}
      />
    </div>
  );
}

export default SnapshotPanel;