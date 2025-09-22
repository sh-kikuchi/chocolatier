import Message from "../../commons/Message/Message";

function MessageTemplate() {
  return (
    <div>
      <div>
        <h2>Message</h2>
        <Message message ="warningメッセージ" mode="warning"/>
        <Message message ="infoメッセージ" mode="info" duration={3000}/>
        <Message message ="Errorメッセージ" mode="error"/>
      </div>
    </div>
  );
}

export default MessageTemplate;
