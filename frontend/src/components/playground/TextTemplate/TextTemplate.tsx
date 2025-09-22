import  { useState } from 'react';
import TextInput from '../../commons/TextInput/TextInput';


function TextPage() {
  const [text, setText] = useState('こんにちは');

  const handleTextChange = (newText: string) => {
    setText(newText);
  };

  return (
    <div>
      <h2>TextInput</h2>
      <p>現在のテキスト: {text}</p>
      <TextInput value={text} onChangeText={handleTextChange} />
    </div>
  );
}

export default TextPage;