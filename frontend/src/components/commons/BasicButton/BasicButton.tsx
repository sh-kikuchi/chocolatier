import { MouseEvent, ReactNode } from 'react';
import styles from './BasicButton.module.css'; 

type BasicButtonProps = {
  type?: "submit" | "reset" | "button" | undefined;
  value?: string;
  onclickAction?: (event: MouseEvent<HTMLButtonElement>) => void;
  children: ReactNode; 
};

function BasicButton({ type, value, onclickAction, children }: BasicButtonProps) {
  return (
    <button
      id="chocolatierBasicButton"
      className={styles.chocolatierBasicButton}
      type={type}
      value={value}
      onClick={onclickAction}
    >
      {children}
    </button>
  );
}

export default BasicButton;
