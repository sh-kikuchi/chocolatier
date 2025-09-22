import { MouseEvent, useState } from 'react';
import BasicButton from '../../commons/BasicButton/BasicButton';

function BasicButtonTemplate() {
  const [clickedValue, setClickedValue] = useState<string | null>(null);

  //ボタンアクション
  const handleTextChange = (event: MouseEvent<HTMLButtonElement>) => {
    const button = event.target as HTMLButtonElement;
    console.log(button.value);
    setClickedValue(button.value);
    alert("Clicked");
  };

  return (
    <div>
      <div>
        <h2>BasicButton</h2>
        <BasicButton type="submit" value="TEST" onclickAction={handleTextChange}>送信</BasicButton>
      </div>
      <div>
        <p>{clickedValue}</p>
      </div>
    </div>
  );
}

export default BasicButtonTemplate;
