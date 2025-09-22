import { ChangeEvent } from 'react';
import styles from './LongText.module.css'; 

type LongTextProps = {
  value?: string;
  onChange?: (event: ChangeEvent<HTMLTextAreaElement>) => void; // イベントごと渡す
  onChangeText?: (text: string) => void; // テキストだけ渡す
  placeholder?: string;
  rows?: number;
  cols?: number;
  disabled?: boolean;
};

function LongText({ value, onChange, onChangeText, placeholder, rows, cols, disabled }: LongTextProps) {
  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    onChange?.(e);               // イベントをそのまま返す
    onChangeText?.(e.target.value); // テキストだけ返す
  };

  return (
    <textarea
      id="chocolatierLongText"
      className={styles.chocolatierLongText}
      value={value}
      onChange={handleChange}
      placeholder={placeholder}
      rows={rows}
      cols={cols}
      disabled={disabled}
    />
  );
}

export default LongText;
