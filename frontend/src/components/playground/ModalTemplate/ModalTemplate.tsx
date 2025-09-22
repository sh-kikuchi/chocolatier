import { useState } from 'react';
import Modal from '../../commons/Modal/Modal';

function ModalTemplate() {
  const [show, setShow] = useState(false);
  return (
    <div>
      <div>
        <h2>Modal</h2>
        <button onClick={() => setShow(true)}>Click</button>
        <Modal show={show} setShow={setShow}>
          <div>
            <input />
            <button>登録</button>
          </div>
        </Modal>
      </div>
    </div>
  );
}

export default ModalTemplate;
 