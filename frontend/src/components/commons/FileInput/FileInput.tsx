import { useRef } from 'react';
import styles from './FileInput.module.css';

type FileInputProps = {
  onUploadFile: (file: File) => void;
};

function FileInput({ onUploadFile }: FileInputProps) {
  const dropAreaRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ファイル処理ロジック（ドロップ・選択両方で使用）
  const handleFileSelect = (file: File) => {
    onUploadFile(file);
  };

  // inputからの選択時
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  // ドロップ時の処理
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    dropAreaRef.current?.classList.remove('dragover');

    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  return (
    <div>
      <div className={styles.inputFile}>
        <div
          className={styles.dropArea}
          ref={dropAreaRef}
          onDragOver={(e) => {
            e.preventDefault();
            dropAreaRef.current?.classList.add(styles.dragover);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            dropAreaRef.current?.classList.remove(styles.dragover);
          }}
          onDrop={handleDrop}
        >
          <p>
            ここにファイルをドロップしてください
            <br />
            または
          </p>
          <div className={styles.inputFileWrap}>
            <input
              id="uploadFile"  
              type="file"
              className={styles.uploadFile}
              ref={fileInputRef}
              onChange={handleChange}
              style={{ display: 'none' }}
            />
            <label htmlFor="uploadFile" className={styles.btnInputFile}>
              <span>ファイルを選択する</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}

export default FileInput;