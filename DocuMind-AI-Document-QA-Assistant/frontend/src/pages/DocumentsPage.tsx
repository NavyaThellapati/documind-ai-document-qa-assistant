import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Trash2 } from "lucide-react";
import { api, DocumentItem } from "../api/client";

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  function load() {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (status) params.set("status_filter", status);
    api.documents(params.toString() ? `?${params}` : "").then((r) => setDocuments(r.documents)).catch((err) => setError(err.message));
  }
  useEffect(load, [search, status]);
  async function remove(id: string) {
    await api.deleteDocument(id);
    load();
  }
  return (
    <section className="page">
      <div className="page-title"><h1>Documents</h1><Link className="button" to="/upload">Upload</Link></div>
      <div className="filters"><Search size={18} /><input placeholder="Search by name" value={search} onChange={(e) => setSearch(e.target.value)} /><select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option><option value="processed">Processed</option><option value="failed">Failed</option><option value="processing">Processing</option></select></div>
      {error && <div className="error">{error}</div>}
      <div className="table">
        {documents.map((doc) => (
          <div className="table-row" key={doc.id}>
            <Link to={`/documents/${doc.id}`}>{doc.original_filename}</Link>
            <span>{doc.status}</span>
            <span>{doc.chunk_count} chunks</span>
            <button className="icon-button" title="Delete" onClick={() => remove(doc.id)}><Trash2 size={16} /></button>
          </div>
        ))}
      </div>
    </section>
  );
}
