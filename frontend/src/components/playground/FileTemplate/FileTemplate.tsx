import { useState, useEffect } from 'react';
import FileInput from '../../commons/FileInput/FileInput';


function FileTemplate() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const uploadFile = (selectedFile: File | null) => {
    setFile(selectedFile);
  };

  // プレビューURLを更新・破棄する
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [file]);

  return (
    <div>
      <div>
        <h2>FileInput(DnD)</h2>
        <FileInput onUploadFile={uploadFile} />
        {file && (
          <div>
            <p>選択されたファイル: {file.name}</p>
            {previewUrl && <img src={previewUrl} alt="preview" />}
          </div>
        )}
      </div>
    </div>
  );
}

export default FileTemplate;
