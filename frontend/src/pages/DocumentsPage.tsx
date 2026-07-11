import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, RefreshCw, Search, Trash2 } from "lucide-react";
import { api, DocumentItem } from "../api/client";
import { useToast } from "../contexts/ToastContext";

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const { notify } = useToast();
  function load() {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (status) params.set("status_filter", status);
    api.documents(params.toString() ? `?${params}` : "").then((r) => setDocuments(r.documents)).catch((err) => setError(err.message));
  }
  useEffect(load, [search, status]);
  async function remove(id: string) {
    await api.deleteDocument(id);
    notify("Document deleted.", "success");
    load();
  }
  async function reprocess(id: string) {
    await api.reprocess(id);
    notify("Document reprocessing completed.", "success");
    load();
  }
  return (
    <section className="page">
      <div className="page-title"><h1>Documents</h1><Link className="button" to="/upload">Upload</Link></div>
      <div className="filters"><Search size={18} /><input placeholder="Search by name" value={search} onChange={(e) => setSearch(e.target.value)} /><select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option><option value="ready">Ready</option><option value="uploaded">Uploaded</option><option value="failed">Failed</option><option value="processing">Processing</option></select></div>
      {error && <div className="error">{error}</div>}
      <div className="table">
        {documents.length ? documents.map((doc) => (
          <div className="table-row" key={doc.id}>
            <Link to={`/documents/${doc.id}`}>{doc.original_filename}</Link>
            <span>{doc.status}</span>
            <span>{doc.page_count ?? "?"} pages</span>
            <span>{doc.embedding_status}</span>
            <a className="icon-button" title="Download" href={api.downloadUrl(doc.id)}><Download size={16} /></a>
            <button className="icon-button" title="Reprocess" onClick={() => reprocess(doc.id)}><RefreshCw size={16} /></button>
            <button className="icon-button" title="Delete" onClick={() => remove(doc.id)}><Trash2 size={16} /></button>
          </div>
        )) : <div className="empty table-empty">No documents match your filters.</div>}
      </div>
    </section>
  );
}
