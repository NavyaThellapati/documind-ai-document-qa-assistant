import { useEffect, useMemo, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Download, FileText, MessageSquare, RotateCw, Search } from "lucide-react";
import { api, DocumentItem, DocumentPreview } from "../api/client";
import { useToast } from "../contexts/ToastContext";

function wordCount(text: string) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function collapsedChunkText(text: string, limit = 420) {
  if (text.length <= limit) return text;
  const boundary = text.lastIndexOf(" ", limit);
  const end = boundary > Math.floor(limit * 0.6) ? boundary : limit;
  return `${text.slice(0, end).trimEnd()}...`;
}

function ChunkCard({ chunk, active }: { chunk: DocumentPreview["chunks"][number]; active: boolean }) {
  const [expanded, setExpanded] = useState(active);
  const words = wordCount(chunk.text);
  const displayText = expanded ? chunk.text : collapsedChunkText(chunk.text);
  return (
    <article className={`chunk-card ${active ? "highlighted" : ""}`} id={`chunk-${chunk.chunk_number}`}>
      <div className="chunk-meta">
        <span>{chunk.page_number ? `Page ${chunk.page_number}` : "Document"}</span>
        <span>Chunk {chunk.chunk_number}</span>
        <span>{words} words</span>
        <span>{Math.ceil(words * 1.3)} tokens</span>
      </div>
      <pre className="chunk-text" data-testid={`chunk-text-${chunk.chunk_number}`}>{displayText}</pre>
      <div className="chunk-actions">
        <button type="button" className="link-button" onClick={() => setExpanded((current) => !current)}>{expanded ? "Collapse" : "Expand"}</button>
        <button type="button" className="link-button" onClick={() => navigator.clipboard.writeText(chunk.text)}><Copy size={14} /> Copy</button>
      </div>
    </article>
  );
}

export function DocumentDetails() {
  const { id } = useParams();
  const location = useLocation();
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [preview, setPreview] = useState<DocumentPreview | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Array<{ page_number?: number | null; excerpt: string; highlighted_excerpt?: string | null }>>([]);
  const [pdfUrl, setPdfUrl] = useState("");
  const { notify } = useToast();
  const sourceChunk = new URLSearchParams(location.search).get("chunk");
  const suggestedQuestions = useMemo(() => [
    "Summarize this document.",
    "What are the most important sections?",
    "What requirements should I remember?",
    "Which topics should I ask about next?",
  ], []);
  useEffect(() => {
    if (!id) return;
    api.document(id).then(setDocument).catch((err) => setError(err.message));
    api.previewDocument(id).then(setPreview).catch(() => undefined);
  }, [id]);
  useEffect(() => {
    if (!id || document?.file_type !== "pdf") return;
    let currentUrl = "";
    api.documentObjectUrl(id).then((url) => {
      currentUrl = url;
      setPdfUrl(url);
    }).catch(() => undefined);
    return () => {
      if (currentUrl) URL.revokeObjectURL(currentUrl);
    };
  }, [document?.file_type, id]);
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
    <section className="page document-workspace">
      <div className="document-header"><div><span className="eyebrow">Document workspace</span><h1>{document.original_filename}</h1><p>{document.file_type.toUpperCase()} · uploaded {new Date(document.created_at).toLocaleString()}</p></div><div className="actions"><button className="button secondary" onClick={download}><Download size={16} /> Download</button><button className="button" onClick={reprocess}><RotateCw size={16} /> Reprocess</button></div></div>
      <div className="detail-grid">
        <div><span>Status</span><strong>{document.status}</strong></div>
        <div><span>Embedding</span><strong>{document.embedding_status}</strong></div>
        <div><span>Progress</span><strong>{document.processing_progress}%</strong></div>
        <div><span>Type</span><strong>{document.file_type.toUpperCase()}</strong></div>
        <div><span>Chunks</span><strong>{document.chunk_count}</strong></div>
        <div><span>Pages</span><strong>{document.page_count ?? "Unknown"}</strong></div>
        <div><span>Size</span><strong>{Math.round(document.file_size / 1024)} KB</strong></div>
        <div><span>Uploaded</span><strong>{new Date(document.created_at).toLocaleString()}</strong></div>
      </div>
      {document.error_message && <div className="error">{document.error_message}</div>}
      {sourceChunk && <div className="success">Showing cited chunk {sourceChunk}. The highlighted card is the source used by the answer.</div>}
      <div className="document-layout">
        <main className="document-main">
          <section className="panel viewer-panel">
            <div className="section-heading"><div><h2>{document.file_type === "pdf" ? "PDF preview" : "Extracted text preview"}</h2><p>Review the original document view or extracted sections used for retrieval.</p></div><FileText size={20} /></div>
            {document.file_type === "pdf" && pdfUrl ? <iframe className="pdf-frame" title={`Preview of ${document.original_filename}`} src={`${pdfUrl}#page=${sourceChunk || 1}`} /> : null}
            {preview ? preview.sections.map((section, index) => <article className="preview-section formatted-text" key={index}><strong>{section.page_number ? `Page ${section.page_number}` : `Section ${index + 1}`}</strong><p>{section.text}</p></article>) : <div className="empty">Preview will appear after extraction succeeds.</div>}
          </section>
          <section className="panel">
            <div className="section-heading"><div><h2>Chunk viewer</h2><p>Cards show the retrieval units used by DocuMind.</p></div></div>
            <div className="chunk-grid">{preview?.chunks.map((chunk) => <ChunkCard chunk={chunk} active={sourceChunk === String(chunk.chunk_number)} key={chunk.chunk_number} />) ?? <div className="empty">Chunks appear after processing.</div>}</div>
          </section>
        </main>
        <aside className="document-aside">
          <section className="panel">
            <h2>Search</h2>
            <div className="filters stacked"><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find text in this document" /><button onClick={search}>Search</button></div>
            {results.length ? results.map((result, index) => <article className="search-hit" key={index}><strong>{result.page_number ? `Page ${result.page_number}` : "Document"}</strong><ReactMarkdown remarkPlugins={[remarkGfm]}>{result.highlighted_excerpt || result.excerpt}</ReactMarkdown></article>) : <div className="empty compact-empty">Search results will appear here.</div>}
          </section>
          <section className="panel">
            <h2>Related questions</h2>
            <div className="question-stack">{suggestedQuestions.map((question) => <a href={`/chat`} className="suggestion-card" key={question}><MessageSquare size={15} /> {question}</a>)}</div>
          </section>
        </aside>
      </div>
    </section>
  );
}
