import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ConversationSummary, DocumentItem } from "../api/client";

export function Dashboard() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  useEffect(() => {
    api.documents().then((r) => setDocuments(r.documents));
    api.conversations().then(setConversations);
  }, []);
  const processed = documents.filter((doc) => doc.status === "processed").length;
  return (
    <section className="page">
      <div className="page-title"><h1>Dashboard</h1><Link className="button" to="/chat">Ask a question</Link></div>
      <div className="metric-grid">
        <div className="metric"><span>Documents</span><strong>{documents.length}</strong></div>
        <div className="metric"><span>Processed</span><strong>{processed}</strong></div>
        <div className="metric"><span>Conversations</span><strong>{conversations.length}</strong></div>
      </div>
      <div className="split">
        <section><h2>Recent documents</h2>{documents.slice(0, 5).map((doc) => <Link className="list-row" to={`/documents/${doc.id}`} key={doc.id}><span>{doc.original_filename}</span><em>{doc.status}</em></Link>)}</section>
        <section><h2>Recent chats</h2>{conversations.slice(0, 5).map((chat) => <Link className="list-row" to="/history" key={chat.id}><span>{chat.title}</span><em>{chat.message_count} messages</em></Link>)}</section>
      </div>
    </section>
  );
}
