import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, Copy, Edit3, MessageSquare, RefreshCw, Search, Square, ThumbsDown, ThumbsUp, Trash2, UserCircle } from "lucide-react";
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
  return (
    <div className="source-card-grid">
      {sources.map((source, index) => {
        const content = <><span>Source {index + 1}</span><strong>{source.document_name}</strong><small>{source.page_number ? `Page ${source.page_number}` : "Page unavailable"} · Chunk {source.chunk_number} · View source</small>{source.relevance_score ? <em>{Math.round(source.relevance_score * 100)}% match</em> : null}</>;
        return source.document_id ? (
          <a className="source-card" key={`${source.document_id}-${source.chunk_number}-${index}`} href={`/documents/${source.document_id}?chunk=${source.chunk_number}#chunk-${source.chunk_number}`}>{content}</a>
        ) : (
          <div className="source-card" key={`${source.document_name}-${source.chunk_number}-${index}`}>{content}</div>
        );
      })}
    </div>
  );
}

const suggestedQuestions = [
  "Summarize this document.",
  "What are the key requirements?",
  "What decisions or policies are mentioned?",
  "Which sections should I review first?",
];

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
  const [historySearch, setHistorySearch] = useState("");
  const lastQuestion = useRef("");
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const { notify } = useToast();
  const latestSources = useMemo(() => [...messages].reverse().find((message) => message.sources.length)?.sources ?? [], [messages]);
  const filteredConversations = useMemo(
    () => conversations.filter((conversation) => conversation.title.toLowerCase().includes(historySearch.toLowerCase())),
    [conversations, historySearch],
  );
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
        <label className="compact-search"><Search size={15} /><input aria-label="Search chat history" placeholder="Search history" value={historySearch} onChange={(event) => setHistorySearch(event.target.value)} /></label>
        {loadingLists && <div className="empty compact-empty">Loading conversations...</div>}
        {filteredConversations.map((conversation) => <div className={`conversation-row ${conversation.id === conversationId ? "active" : ""}`} key={conversation.id}><button onClick={() => openConversation(conversation.id)}>{conversation.title}</button><button aria-label={`Rename ${conversation.title}`} title="Rename" onClick={() => renameConversation(conversation.id)}><Edit3 size={14} /></button><button aria-label={`Delete ${conversation.title}`} title="Delete" onClick={() => deleteConversation(conversation.id)}><Trash2 size={14} /></button></div>)}
        {!loadingLists && !filteredConversations.length && <div className="empty compact-empty">No conversations found.</div>}
      </aside>
      <div className="chat-panel">
        <div className="chat-hero">
          <div><span className="eyebrow">Grounded AI assistant</span><h1>Ask your documents anything.</h1><p>Answers are constrained to uploaded content and linked back to source chunks.</p></div>
        </div>
        <div className="messages">
          {messages.length === 0 && !loading && <div className="empty chat-empty"><MessageSquare size={34} /> Ask a question grounded in your documents.</div>}
          {messages.map((message) => <article className="message-thread" key={message.id}><div className="bubble user-bubble"><span className="avatar user-avatar"><UserCircle size={18} /></span><div><h3>{message.question}</h3></div></div><div className="bubble assistant-bubble"><span className="avatar assistant-avatar"><Bot size={18} /></span><div><div className="markdown"><Markdown>{message.answer}</Markdown></div><SourceList sources={message.sources} /><div className="feedback"><button aria-label="Copy answer" title="Copy" onClick={() => copyAnswer(message.answer)}><Copy size={16} /></button><button aria-label="Regenerate answer" title="Regenerate" onClick={() => submitQuestion(message.question)}><RefreshCw size={16} /></button><button aria-label="Mark helpful" title="Helpful" onClick={() => api.feedback({ message_id: message.id, helpful: true }).then(() => notify("Feedback saved.", "success"))}><ThumbsUp size={16} /></button><button aria-label="Mark not helpful" title="Not helpful" onClick={() => api.feedback({ message_id: message.id, helpful: false }).then(() => notify("Feedback saved.", "success"))}><ThumbsDown size={16} /></button></div></div></div></article>)}
          {loading && <div className="bubble assistant-bubble streaming"><span className="avatar assistant-avatar"><Bot size={18} /></span><div><div className="typing-line"><span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" /></div><div className="markdown"><Markdown>{draftAnswer || "Retrieving sources and generating an answer..."}</Markdown></div></div></div>}
          <div ref={bottomRef} />
        </div>
        {error && <div className="error">{error}</div>}
        {!messages.length && <div className="suggestion-row">{suggestedQuestions.map((suggestion) => <button type="button" className="suggestion-chip" key={suggestion} onClick={() => setQuestion(suggestion)}>{suggestion}</button>)}</div>}
        <form className="ask-box" onSubmit={ask}><textarea value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask a question about your uploaded documents" required />{loading ? <button type="button" onClick={stopGeneration}><Square size={16} /> Stop</button> : <button disabled={loadingLists}>Ask</button>}</form>
      </div>
      <aside className="document-picker research-panel">
        <h2>Research panel</h2>
        <section>
          <h3>Document scope</h3>
          {loadingLists ? <div className="empty compact-empty">Loading documents...</div> : documents.length ? documents.map((doc) => <label key={doc.id}><input type="checkbox" checked={selected.includes(doc.id)} onChange={() => toggle(doc.id)} /> <span>{doc.original_filename}<small>{doc.file_type?.toUpperCase?.() || "DOC"} · {doc.chunk_count ?? 0} chunks</small></span></label>) : <div className="empty">Upload ready documents before chatting.</div>}
          <span>{selected.length === 0 ? "All ready documents selected" : `${selected.length} selected`}</span>
        </section>
        <section>
          <h3>Latest sources</h3>
          {latestSources.length ? <SourceList sources={latestSources} /> : <div className="empty compact-empty">Sources appear after an answer.</div>}
        </section>
      </aside>
    </section>
  );
}
