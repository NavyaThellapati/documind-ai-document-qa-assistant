import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Edit3, ExternalLink, MessageSquare, RefreshCw, Square, ThumbsDown, ThumbsUp, Trash2 } from "lucide-react";
import { api, ConversationSummary, DocumentItem, Message, Source } from "../api/client";
import { useToast } from "../contexts/ToastContext";

function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ className, children: codeChildren, ...props }) {
          const language = /language-([A-Za-z0-9_-]+)/.exec(className ?? "")?.[1];
          return <code className={className} data-language={language} {...props}>{codeChildren}</code>;
        },
      }}
    >
      {children}
    </ReactMarkdown>
  );
}

function SourceList({ sources }: { sources: Source[] }) {
  return <div className="sources">{sources.map((source, index) => <details key={`${source.document_id}-${source.chunk_number}-${index}`}><summary>{source.document_name} {source.page_number ? `page ${source.page_number}` : ""} chunk {source.chunk_number} {source.relevance_score ? `confidence ${source.relevance_score}` : ""} {source.document_id && <a className="source-link" href={`/documents/${source.document_id}?chunk=${source.chunk_number}#chunk-${source.chunk_number}`}><ExternalLink size={14} /> View source</a>}</summary><Markdown>{source.highlighted_excerpt || source.excerpt}</Markdown></details>)}</div>;
}

export function ChatPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [question, setQuestion] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loadingLists, setLoadingLists] = useState(true);
  const [draftAnswer, setDraftAnswer] = useState("");
  const lastQuestion = useRef("");
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const { notify } = useToast();
  function loadConversations() { api.conversations().then(setConversations).catch((err) => setError(err.message)); }
  useEffect(() => {
    setLoadingLists(true);
    Promise.all([
      api.documents("?status_filter=ready").then((r) => setDocuments(r.documents)),
      api.conversations().then(setConversations),
    ]).catch((err) => {
      const message = err instanceof Error ? err.message : "Unable to load chat data";
      setError(message);
      notify(message, "error");
    }).finally(() => setLoadingLists(false));
  }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, draftAnswer]);
  async function openConversation(id: string) {
    try {
      const conversation = await api.conversation(id);
      setConversationId(conversation.id);
      setMessages(conversation.messages);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to open conversation";
      setError(message);
      notify(message, "error");
    }
  }
  async function ask(event: FormEvent) {
    event.preventDefault();
    await submitQuestion(question);
  }
  async function submitQuestion(text: string) {
    if (!text.trim()) return;
    if (loading) return;
    setLoading(true);
    setError("");
    setDraftAnswer("");
    lastQuestion.current = text;
    abortRef.current = new AbortController();
    try {
      const result = await api.streamAsk({ question: text, conversation_id: conversationId, document_ids: selected }, (token) => setDraftAnswer((current) => current + token), abortRef.current.signal);
      setConversationId(result.conversation_id);
      setMessages((current) => [...current, { id: result.message_id, question: text, answer: result.answer, sources: result.sources, created_at: new Date().toISOString() }]);
      setQuestion("");
      setDraftAnswer("");
      loadConversations();
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setError("Generation stopped.");
        return;
      }
      const message = err instanceof Error ? err.message : "Question failed";
      setError(message);
      notify(message, "error");
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }
  async function renameConversation(id: string) {
    const title = window.prompt("Rename conversation");
    if (!title) return;
    try {
      await api.renameConversation(id, title);
      notify("Conversation renamed.", "success");
      loadConversations();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Rename failed";
      setError(message);
      notify(message, "error");
    }
  }
  async function deleteConversation(id: string) {
    if (!window.confirm("Delete this conversation? This cannot be undone.")) return;
    try {
      await api.deleteConversation(id);
      if (conversationId === id) {
        setConversationId(undefined);
        setMessages([]);
      }
      notify("Conversation deleted.", "success");
      loadConversations();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Delete failed";
      setError(message);
      notify(message, "error");
    }
  }
  function copyAnswer(answer: string) {
    navigator.clipboard.writeText(answer).then(() => notify("Answer copied.", "success"));
  }
  function toggle(id: string) {
    setSelected(selected.includes(id) ? selected.filter((item) => item !== id) : [...selected, id]);
  }
  function stopGeneration() {
    abortRef.current?.abort();
  }
  return (
    <section className="page chat-layout pro-chat">
      <aside className="conversation-sidebar">
        <button className="button full" onClick={() => { setConversationId(undefined); setMessages([]); }}><MessageSquare size={16} /> New chat</button>
        {loadingLists && <div className="empty compact-empty">Loading conversations...</div>}
        {conversations.map((conversation) => <div className={`conversation-row ${conversation.id === conversationId ? "active" : ""}`} key={conversation.id}><button onClick={() => openConversation(conversation.id)}>{conversation.title}</button><button title="Rename" onClick={() => renameConversation(conversation.id)}><Edit3 size={14} /></button><button title="Delete" onClick={() => deleteConversation(conversation.id)}><Trash2 size={14} /></button></div>)}
      </aside>
      <aside className="document-picker">
        <h2>Scope</h2>
        {loadingLists ? <div className="empty compact-empty">Loading documents...</div> : documents.length ? documents.map((doc) => <label key={doc.id}><input type="checkbox" checked={selected.includes(doc.id)} onChange={() => toggle(doc.id)} />{doc.original_filename}</label>) : <div className="empty">Upload ready documents before chatting.</div>}
        <span>{selected.length === 0 ? "All ready documents selected" : `${selected.length} selected`}</span>
      </aside>
      <div className="chat-panel">
        <div className="messages">
          {messages.length === 0 && !loading && <div className="empty chat-empty"><MessageSquare size={34} /> Ask a question grounded in your documents.</div>}
          {messages.map((message) => <article className="message" key={message.id}><h3>{message.question}</h3><div className="markdown"><Markdown>{message.answer}</Markdown></div><SourceList sources={message.sources} /><div className="feedback"><button title="Copy" onClick={() => copyAnswer(message.answer)}><Copy size={16} /></button><button title="Regenerate" onClick={() => submitQuestion(message.question)}><RefreshCw size={16} /></button><button title="Helpful" onClick={() => api.feedback({ message_id: message.id, helpful: true }).then(() => notify("Feedback saved.", "success"))}><ThumbsUp size={16} /></button><button title="Not helpful" onClick={() => api.feedback({ message_id: message.id, helpful: false }).then(() => notify("Feedback saved.", "success"))}><ThumbsDown size={16} /></button></div></article>)}
          {loading && <div className="message streaming"><div className="typing-dot" /><div className="markdown"><Markdown>{draftAnswer || "Retrieving sources and generating an answer..."}</Markdown></div></div>}
          <div ref={bottomRef} />
        </div>
        {error && <div className="error">{error}</div>}
        <form className="ask-box" onSubmit={ask}><textarea value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask a question about your uploaded documents" required />{loading ? <button type="button" onClick={stopGeneration}><Square size={16} /> Stop</button> : <button disabled={loadingLists}>Ask</button>}</form>
      </div>
    </section>
  );
}
