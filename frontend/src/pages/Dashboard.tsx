import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, Database, FileText, MessageSquare, UploadCloud } from "lucide-react";
import { api, DashboardSummary } from "../api/client";

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.dashboard().then(setSummary).finally(() => setLoading(false));
  }, []);
  if (loading) return <section className="page"><div className="skeleton hero-skeleton" /><div className="metric-grid">{[1, 2, 3, 4].map((item) => <div className="skeleton metric" key={item} />)}</div></section>;
  return (
    <section className="page">
      <div className="page-title"><h1>Dashboard</h1><Link className="button" to="/chat">Ask a question</Link></div>
      <div className="metric-grid">
        <div className="metric"><FileText size={20} /><span>Total documents</span><strong>{summary?.total_documents ?? 0}</strong></div>
        <div className="metric"><MessageSquare size={20} /><span>Total chats</span><strong>{summary?.total_chats ?? 0}</strong></div>
        <div className="metric"><Activity size={20} /><span>Questions asked</span><strong>{summary?.questions_asked ?? 0}</strong></div>
        <div className="metric"><Database size={20} /><span>Storage used</span><strong>{formatBytes(summary?.storage_used_bytes ?? 0)}</strong></div>
      </div>
      <div className="status-strip">
        <span>{summary?.ready_documents ?? summary?.processed_documents ?? 0} ready</span>
        <span>{summary?.processing_documents ?? 0} processing</span>
        <span>{summary?.failed_documents ?? 0} failed</span>
        <span>Top-K {summary?.ai_usage_summary.retrieval_top_k}</span>
        <span>{summary?.ai_usage_summary.llm_provider}</span>
      </div>
      <div className="split">
        <section><h2>Recently uploaded</h2>{summary?.recent_documents.length ? summary.recent_documents.map((doc) => <Link className="list-row" to={`/documents/${doc.id}`} key={doc.id}><span>{doc.name}</span><em>{doc.status} / {doc.embedding_status}</em></Link>) : <div className="empty"><UploadCloud size={28} /> Upload a document to start.</div>}</section>
        <section><h2>Recent conversations</h2>{summary?.recent_conversations.length ? summary.recent_conversations.map((chat) => <Link className="list-row" to="/history" key={chat.id}><span>{chat.title}</span><em>{new Date(chat.updated_at).toLocaleDateString()}</em></Link>) : <div className="empty"><MessageSquare size={28} /> Ask your first grounded question.</div>}</section>
      </div>
    </section>
  );
}
