import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Download, RotateCw, Search } from "lucide-react";
import { api, DocumentItem } from "../api/client";
import { useToast } from "../contexts/ToastContext";

export function DocumentDetails() {
  const { id } = useParams();
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Array<{ page_number?: number | null; excerpt: string }>>([]);
  const { notify } = useToast();
  useEffect(() => { if (id) api.document(id).then(setDocument).catch((err) => setError(err.message)); }, [id]);
  async function reprocess() {
    if (!id) return;
    setDocument(await api.reprocess(id));
    notify("Document reprocessed.", "success");
  }
  async function search() {
    if (!id || query.trim().length < 2) return;
    const response = await api.searchDocument(id, query);
    setResults(response.results);
  }
  if (error) return <section className="page"><div className="error">{error}</div></section>;
  if (!document) return <section className="page">Loading...</section>;
  return (
    <section className="page">
      <div className="page-title"><h1>{document.original_filename}</h1><div className="actions"><a className="button secondary" href={api.downloadUrl(document.id)}><Download size={16} /> Download</a><button className="button" onClick={reprocess}><RotateCw size={16} /> Reprocess</button></div></div>
      <div className="detail-grid">
        <div><span>Status</span><strong>{document.status}</strong></div>
        <div><span>Embedding</span><strong>{document.embedding_status}</strong></div>
        <div><span>Chunks</span><strong>{document.chunk_count}</strong></div>
        <div><span>Pages</span><strong>{document.page_count ?? "Unknown"}</strong></div>
        <div><span>Size</span><strong>{Math.round(document.file_size / 1024)} KB</strong></div>
        <div><span>Uploaded</span><strong>{new Date(document.created_at).toLocaleString()}</strong></div>
      </div>
      {document.error_message && <div className="error">{document.error_message}</div>}
      <section className="panel">
        <h2>Search inside document</h2>
        <div className="filters"><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find text in this document" /><button onClick={search}>Search</button></div>
        {results.length ? results.map((result, index) => <article className="search-hit" key={index}><strong>{result.page_number ? `Page ${result.page_number}` : "Document"}</strong><p>{result.excerpt}</p></article>) : <div className="empty">Search results will appear here.</div>}
      </section>
    </section>
  );
}
