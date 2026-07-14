import { useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { Download, RotateCw, Search } from "lucide-react";
import { api, DocumentItem, DocumentPreview } from "../api/client";
import { useToast } from "../contexts/ToastContext";

export function DocumentDetails() {
  const { id } = useParams();
  const location = useLocation();
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [preview, setPreview] = useState<DocumentPreview | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Array<{ page_number?: number | null; excerpt: string }>>([]);
  const { notify } = useToast();
  const sourceChunk = new URLSearchParams(location.search).get("chunk");
  useEffect(() => {
    if (!id) return;
    api.document(id).then(setDocument).catch((err) => setError(err.message));
    api.previewDocument(id).then(setPreview).catch(() => undefined);
  }, [id]);
  useEffect(() => {
    if (!preview || !sourceChunk) return;
    globalThis.document.getElementById(`chunk-${sourceChunk}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [preview, sourceChunk]);
  async function reprocess() {
    if (!id) return;
    try {
      setDocument(await api.reprocessBackground(id));
      notify("Document queued for reprocessing.", "success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reprocess failed");
    }
  }
  async function search() {
    if (!id || query.trim().length < 2) return;
    try {
      const response = await api.searchDocument(id, query);
      setResults(response.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    }
  }
  async function download() {
    if (!document) return;
    try {
      await api.downloadDocument(document.id, document.original_filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    }
  }
  if (error) return <section className="page"><div className="error">{error}</div></section>;
  if (!document) return <section className="page">Loading...</section>;
  return (
    <section className="page">
      <div className="page-title"><h1>{document.original_filename}</h1><div className="actions"><button className="button secondary" onClick={download}><Download size={16} /> Download</button><button className="button" onClick={reprocess}><RotateCw size={16} /> Reprocess</button></div></div>
      <div className="detail-grid">
        <div><span>Status</span><strong>{document.status}</strong></div>
        <div><span>Embedding</span><strong>{document.embedding_status}</strong></div>
        <div><span>Chunks</span><strong>{document.chunk_count}</strong></div>
        <div><span>Pages</span><strong>{document.page_count ?? "Unknown"}</strong></div>
        <div><span>Size</span><strong>{Math.round(document.file_size / 1024)} KB</strong></div>
        <div><span>Uploaded</span><strong>{new Date(document.created_at).toLocaleString()}</strong></div>
      </div>
      {document.error_message && <div className="error">{document.error_message}</div>}
      {sourceChunk && <div className="success">Showing cited chunk {sourceChunk}. The highlighted card is the source used by the answer.</div>}
      <section className="panel">
        <h2>Search inside document</h2>
        <div className="filters"><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find text in this document" /><button onClick={search}>Search</button></div>
        {results.length ? results.map((result, index) => <article className="search-hit" key={index}><strong>{result.page_number ? `Page ${result.page_number}` : "Document"}</strong><p>{result.excerpt}</p></article>) : <div className="empty">Search results will appear here.</div>}
      </section>
      <section className="panel">
        <h2>Extracted text preview</h2>
        {preview ? (
          <div className="preview-grid">
            <div>
              <h3>Pages / sections</h3>
              {preview.sections.map((section, index) => <article className="preview-section" key={index}><strong>{section.page_number ? `Page ${section.page_number}` : `Section ${index + 1}`}</strong><p>{section.text}</p></article>)}
            </div>
            <div>
              <h3>Chunk boundaries</h3>
              {preview.chunks.map((chunk) => <article className={`preview-section ${sourceChunk === String(chunk.chunk_number) ? "highlighted" : ""}`} id={`chunk-${chunk.chunk_number}`} key={chunk.chunk_number}><strong>{chunk.page_number ? `Page ${chunk.page_number}` : "Document"} · Chunk {chunk.chunk_number}</strong><p>{chunk.text}</p></article>)}
            </div>
          </div>
        ) : <div className="empty">Preview will appear after extraction succeeds.</div>}
      </section>
    </section>
  );
}
