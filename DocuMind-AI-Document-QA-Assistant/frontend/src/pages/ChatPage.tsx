import { FormEvent, useEffect, useState } from "react";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { api, DocumentItem, Message, Source } from "../api/client";

function SourceList({ sources }: { sources: Source[] }) {
  return <div className="sources">{sources.map((source, index) => <details key={`${source.document_id}-${source.chunk_number}-${index}`}><summary>{source.document_name} {source.page_number ? `page ${source.page_number}` : ""} chunk {source.chunk_number} {source.relevance_score ? `score ${source.relevance_score}` : ""}</summary><p>{source.excerpt}</p></details>)}</div>;
}

export function ChatPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [question, setQuestion] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { api.documents("?status_filter=processed").then((r) => setDocuments(r.documents)); }, []);
  async function ask(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await api.ask({ question, conversation_id: conversationId, document_ids: selected });
      setConversationId(result.conversation_id);
      setMessages([...messages, { id: result.message_id, question, answer: result.answer, sources: result.sources, created_at: new Date().toISOString() }]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Question failed");
    } finally {
      setLoading(false);
    }
  }
  function toggle(id: string) {
    setSelected(selected.includes(id) ? selected.filter((item) => item !== id) : [...selected, id]);
  }
  return (
    <section className="page chat-layout">
      <aside className="document-picker">
        <h2>Scope</h2>
        {documents.map((doc) => <label key={doc.id}><input type="checkbox" checked={selected.includes(doc.id)} onChange={() => toggle(doc.id)} />{doc.original_filename}</label>)}
        <span>{selected.length === 0 ? "All processed documents selected" : `${selected.length} selected`}</span>
      </aside>
      <div className="chat-panel">
        <div className="messages">
          {messages.map((message) => <article className="message" key={message.id}><h3>{message.question}</h3><p>{message.answer}</p><SourceList sources={message.sources} /><div className="feedback"><button title="Helpful" onClick={() => api.feedback({ message_id: message.id, helpful: true })}><ThumbsUp size={16} /></button><button title="Not helpful" onClick={() => api.feedback({ message_id: message.id, helpful: false })}><ThumbsDown size={16} /></button></div></article>)}
          {loading && <div className="message">Retrieving sources and generating an answer...</div>}
        </div>
        {error && <div className="error">{error}</div>}
        <form className="ask-box" onSubmit={ask}><textarea value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask a question about your uploaded documents" required /><button disabled={loading}>Ask</button></form>
      </div>
    </section>
  );
}
