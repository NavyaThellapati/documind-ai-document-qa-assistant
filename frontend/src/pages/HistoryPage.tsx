import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { api, Conversation, ConversationSummary } from "../api/client";

export function HistoryPage() {
  const [items, setItems] = useState<ConversationSummary[]>([]);
  const [active, setActive] = useState<Conversation | null>(null);
  function load() { api.conversations().then(setItems); }
  useEffect(load, []);
  async function remove(id: string) {
    await api.deleteConversation(id);
    setActive(null);
    load();
  }
  return (
    <section className="page split history">
      <div>
        <h1>Chat history</h1>
        {items.map((item) => <button className="list-row" key={item.id} onClick={() => api.conversation(item.id).then(setActive)}><span>{item.title}</span><em>{item.message_count}</em></button>)}
      </div>
      <div>
        {active ? <><div className="page-title"><h2>{active.title}</h2><button className="icon-button" onClick={() => remove(active.id)}><Trash2 size={16} /></button></div>{active.messages.map((message) => <article className="message" key={message.id}><h3>{message.question}</h3><p>{message.answer}</p></article>)}</> : <p>Select a conversation.</p>}
      </div>
    </section>
  );
}
