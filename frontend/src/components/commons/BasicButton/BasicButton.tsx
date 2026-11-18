import { MouseEvent, ReactNode } from 'react';
import styles from './BasicButton.module.css';

type BasicButtonProps = {
  type?: "submit" | "reset" | "button" | undefined;
  value?: string;
  onclickAction?: (event: MouseEvent<HTMLButtonElement>) => void;
  disabled?: boolean;  // true のとき押せない（処理中の連打防止など）。省略時は押せる
  children: ReactNode;
};

function BasicButton({ type, value, onclickAction, disabled = false, children }: BasicButtonProps) {
  return (
    <button
      id="chocolatierBasicButton"
      className={styles.chocolatierBasicButton}
      type={type}
      value={value}
      onClick={onclickAction}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

export default BasicButton;
