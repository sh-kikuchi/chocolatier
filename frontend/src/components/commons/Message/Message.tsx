import { useEffect, useState } from 'react';
import styles from './Message.module.css';

type MessageProps = {
  message: string;
  mode: string;
  duration?: number;
};

function Message({ message, mode, duration }: MessageProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    setVisible(true);

    if(duration){
      const timer = setTimeout(() => {
        setVisible(false);
      }, duration);
      return () => clearTimeout(timer);
    }

  }, [message, duration]);

  return (
    <div className={`${styles.message} ${styles[mode]} ${visible ? '' : styles.fadeOut}`}>
      {message}
    </div>
  );
}

export default Message;