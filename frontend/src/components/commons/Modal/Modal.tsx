import React from 'react';
import styles from './Modal.module.css';

type ModalProps = {
  show: boolean;
  setShow: React.Dispatch<React.SetStateAction<boolean>>;
  children: React.ReactNode;
};

function Modal({ show, setShow, children }: ModalProps): JSX.Element | null {
  const closeModal = () => {
    setShow(false);
  };

  if (show) {
    return (
      <div className={styles.overlay} onClick={closeModal}>
        <div className={styles.content} onClick={(e) => e.stopPropagation()}>
          {children}
          <div className={styles.textRight} onClick={closeModal}>Close</div>
        </div>
      </div>
    );
  } else {
    return null;
  }
}

export default Modal;
