import { useState } from 'react';
import LongText from '../../commons/LongText/LongText';

function LongTextTemplate() {
  const [text, setText] = useState("");

  return (
    <div>
      <div>
        <h2>LongText</h2>
        <LongText value={text} onChange={(e) => setText(e.target.value)} />
      </div>
      <div>
        <p>{text}</p>
      </div>
    </div>
  );
}

export default LongTextTemplate;
