import styles from './SnapshotPanel.module.css';

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
  const MEDIA_URL = "http://localhost:8000/media/";

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