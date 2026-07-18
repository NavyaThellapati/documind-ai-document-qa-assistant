import { useEffect, useState } from "react";
import { Search, Trash2 } from "lucide-react";
import { api, Conversation, ConversationSummary } from "../api/client";

export function HistoryPage() {
  const [items, setItems] = useState<ConversationSummary[]>([]);
  const [active, setActive] = useState<Conversation | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  function load() {
    setLoading(true);
    setError("");
    api.conversations(search ? `?search=${encodeURIComponent(search)}` : "")
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load chat history"))
      .finally(() => setLoading(false));
  }
  useEffect(load, []);
  useEffect(() => {
    const timeout = window.setTimeout(load, 250);
    return () => window.clearTimeout(timeout);
  }, [search]);
  async function remove(id: string) {
    await api.deleteConversation(id);
    setActive(null);
    load();
  }
  async function open(id: string) {
    try {
      setActive(await api.conversation(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to open conversation");
    }
  }
  return (
    <section className="page split history">
      <div className="history-list-panel">
        <div className="page-title"><h1>Chat history</h1></div>
        <label className="filters"><Search size={18} /><input aria-label="Search chat history" placeholder="Search conversations" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
        {error && <div className="error">{error}</div>}
        {loading ? <div className="skeleton" /> : items.length ? items.map((item) => <button className="list-row conversation-card" key={item.id} onClick={() => open(item.id)}><span>{item.title}</span><em>{item.message_count} messages</em></button>) : <div className="empty">No conversations match your search.</div>}
      </div>
      <div className="history-detail-panel">
        {active ? <><div className="page-title"><h2>{active.title}</h2><button aria-label="Delete conversation" className="icon-button" onClick={() => remove(active.id)}><Trash2 size={16} /></button></div>{active.messages.map((message) => <article className="message history-message" key={message.id}><h3>{message.question}</h3><p>{message.answer}</p></article>)}</> : <div className="empty">Select a conversation to review answers and sources.</div>}
      </div>
    </section>
  );
}
