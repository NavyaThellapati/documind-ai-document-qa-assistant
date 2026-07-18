import { FormEvent, useEffect, useMemo, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, Copy, Download, FileText, MessageSquare, RotateCw, Search, Sparkles } from "lucide-react";
import { api, DocumentInsight, DocumentItem, DocumentPreview, Source } from "../api/client";
import { useToast } from "../contexts/ToastContext";

type Tab = "overview" | "ask" | "preview" | "chunks" | "search";
type SummaryLength = "brief" | "standard" | "detailed";

function wordCount(text: string) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function collapsedChunkText(text: string, limit = 420) {
  if (text.length <= limit) return text;
  const boundary = text.lastIndexOf(" ", limit);
  const end = boundary > Math.floor(limit * 0.6) ? boundary : limit;
  return `${text.slice(0, end).trimEnd()}...`;
}

function Markdown({ children }: { children: string }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>;
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
        <button type="button" className="link-button" onClick={() => setExpanded((current) => !current)}>{expanded ? "Collapse" : "Expand full chunk"}</button>
        <button type="button" className="link-button" onClick={() => navigator.clipboard.writeText(chunk.text)}><Copy size={14} /> Copy</button>
      </div>
    </article>
  );
}

function Sources({ sources }: { sources: Source[] }) {
  if (!sources.length) return null;
  return (
    <div className="source-card-grid">
      {sources.map((source, index) => (
        <a className="source-card" href={`/documents/${source.document_id}?chunk=${source.chunk_number}#chunk-${source.chunk_number}`} key={`${source.document_id}-${source.chunk_number}-${index}`}>
          <span>Source {index + 1}</span>
          <strong>{source.document_name}</strong>
          <small>{source.page_number ? `Page ${source.page_number}` : "Page unavailable"} · Chunk {source.chunk_number}</small>
        </a>
      ))}
    </div>
  );
}

export function DocumentDetails() {
  const { id } = useParams();
  const location = useLocation();
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [preview, setPreview] = useState<DocumentPreview | null>(null);
  const [insight, setInsight] = useState<DocumentInsight | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Array<{ page_number?: number | null; excerpt: string; highlighted_excerpt?: string | null }>>([]);
  const [pdfUrl, setPdfUrl] = useState("");
  const [insightLoading, setInsightLoading] = useState(false);
  const [summaryLength, setSummaryLength] = useState<SummaryLength>("standard");
  const [askQuestion, setAskQuestion] = useState("");
  const [askLoading, setAskLoading] = useState(false);
  const [askAnswer, setAskAnswer] = useState<{ answer: string; sources: Source[] } | null>(null);
  const { notify } = useToast();
  const sourceChunk = new URLSearchParams(location.search).get("chunk");
  const tabs: Array<{ id: Tab; label: string }> = [
    { id: "overview", label: "Overview" },
    { id: "ask", label: "Ask AI" },
    { id: "preview", label: "Document preview" },
    { id: "chunks", label: "Chunks" },
    { id: "search", label: "Search" },
  ];
  const fallbackQuestions = useMemo(() => [
    "What is this document mainly about?",
    "What are the most important details?",
    "Which sections should I review first?",
    "What facts are supported by the document?",
  ], []);
  const suggestedQuestions = insight?.suggested_questions.length ? insight.suggested_questions : fallbackQuestions;

  useEffect(() => {
    if (!id) return;
    setError("");
    api.document(id).then(setDocument).catch((err) => setError(err.message));
    api.previewDocument(id).then(setPreview).catch(() => undefined);
    api.documentInsight(id, summaryLength).then(setInsight).catch(() => undefined);
  }, [id, summaryLength]);
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
    setActiveTab("chunks");
    globalThis.document.getElementById(`chunk-${sourceChunk}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [preview, sourceChunk]);

  async function explain() {
    if (!id) return;
    setInsightLoading(true);
    setError("");
    try {
      setInsight(await api.explainDocument(id, summaryLength));
      setActiveTab("overview");
      notify("Document explanation ready.", "success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Summary unavailable.");
    } finally {
      setInsightLoading(false);
    }
  }
  async function reprocess() {
    if (!id) return;
    try {
      setDocument(await api.reprocessBackground(id));
      setInsight(null);
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
  async function askAboutDocument(event: FormEvent) {
    event.preventDefault();
    if (!document || !askQuestion.trim()) return;
    setAskLoading(true);
    setError("");
    try {
      const response = await api.ask({ question: askQuestion, document_ids: [document.id] });
      setAskAnswer({ answer: response.answer, sources: response.sources });
      setActiveTab("ask");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Question failed");
    } finally {
      setAskLoading(false);
    }
  }

  if (error) return <section className="page"><div className="error">{error}</div></section>;
  if (!document) return <section className="page">Loading...</section>;
  const processed = ["ready", "processed"].includes(document.status);

  return (
    <section className="page document-workspace">
      <div className="document-header">
        <div>
          <span className="eyebrow">Document intelligence</span>
          <h1>{document.original_filename}</h1>
          <p>{document.file_type.toUpperCase()} · uploaded {new Date(document.created_at).toLocaleString()}</p>
        </div>
        <div className="actions">
          <button className="button secondary" onClick={download}><Download size={16} /> Download</button>
          <button className="button secondary" onClick={reprocess}><RotateCw size={16} /> Reprocess</button>
          <button className="button" onClick={explain} disabled={!processed || insightLoading}><Sparkles size={16} /> {insightLoading ? "Generating summary" : "Explain this document"}</button>
        </div>
      </div>

      <div className="detail-grid">
        <div><span>Status</span><strong>{document.status}</strong></div>
        <div><span>Embedding</span><strong>{document.embedding_status}</strong></div>
        <div><span>Progress</span><strong>{document.processing_progress}%</strong></div>
        <div><span>Type</span><strong>{document.file_type.toUpperCase()}</strong></div>
        <div><span>Chunks</span><strong>{document.chunk_count}</strong></div>
        <div><span>Pages</span><strong>{document.page_count ?? "Unknown"}</strong></div>
        <div><span>Size</span><strong>{Math.round(document.file_size / 1024)} KB</strong></div>
        <div><span>Summary</span><strong>{insightLoading ? "Generating summary" : insight ? "Ready" : processed ? "Summary unavailable" : "Processing document"}</strong></div>
      </div>

      {document.error_message && <div className="error">{document.error_message}</div>}
      {sourceChunk && <div className="success">Showing cited chunk {sourceChunk}. The highlighted card is the source used by the answer.</div>}
      {!processed && <div className="success">Processing document. Chunk viewing and explanation will be available when processing finishes.</div>}
      {insight?.notice && <div className="success">{insight.notice}</div>}

      <form className="inline-ask" onSubmit={askAboutDocument}>
        <MessageSquare size={18} />
        <input value={askQuestion} onChange={(event) => setAskQuestion(event.target.value)} placeholder="Ask a question about this document" aria-label="Ask a question about this document" />
        <button disabled={!processed || askLoading}>{askLoading ? "Asking..." : "Ask AI"}</button>
      </form>

      <div className="tabs" role="tablist" aria-label="Document details">
        {tabs.map((tab) => <button type="button" role="tab" aria-selected={activeTab === tab.id} className={activeTab === tab.id ? "active" : ""} key={tab.id} onClick={() => setActiveTab(tab.id)}>{tab.label}</button>)}
      </div>

      {activeTab === "overview" && (
        <div className="document-layout">
          <main className="document-main">
            <section className="panel">
              <div className="section-heading"><div><h2>Overview</h2><p>Grounded summary generated from the uploaded document text without showing raw chunks.</p></div><Sparkles size={20} /></div>
              <div className="summary-controls">
                <label>Summary length<select value={summaryLength} onChange={(event) => setSummaryLength(event.target.value as SummaryLength)}><option value="brief">Brief</option><option value="standard">Standard</option><option value="detailed">Detailed</option></select></label>
                <button type="button" className="button secondary" onClick={explain} disabled={!processed || insightLoading}><RotateCw size={16} /> Regenerate summary</button>
              </div>
              {insightLoading ? <div className="skeleton" /> : insight ? <div className="insight-stack"><div className="tag-cloud"><span>{insight.document_type}</span><span>{insight.summary_length}</span></div><h3>One-sentence overview</h3><p>{insight.overview}</p><h3>Concise summary</h3><p>{insight.summary}</p><h3>Key points</h3><ul>{insight.key_points.map((point) => <li key={point}>{point}</li>)}</ul></div> : <div className="empty">Click Explain this document to generate a grounded overview.</div>}
            </section>
            <section className="panel">
              <h2>Main sections</h2>
              {insight?.main_sections.length ? <div className="section-list">{insight.main_sections.map((section) => <article key={section.title}><strong>{section.title}</strong><p>{section.description}</p></article>)}</div> : <div className="empty compact-empty">Detected sections will appear here.</div>}
            </section>
          </main>
          <aside className="document-aside">
            <section className="panel">
              <h2>Key entities and topics</h2>
              {insight?.key_entities.length ? <div className="tag-cloud">{insight.key_entities.map((entity) => <span key={entity}>{entity}</span>)}</div> : <div className="empty compact-empty">Important topics will appear after explanation.</div>}
            </section>
            <section className="panel">
              <h2>Suggested questions</h2>
              <div className="question-stack">{suggestedQuestions.map((question) => <button type="button" className="suggestion-card" key={question} onClick={() => { setAskQuestion(question); setActiveTab("ask"); }}><MessageSquare size={15} /> {question}</button>)}</div>
            </section>
            <section className="panel">
              <h2>Source references</h2>
              {insight?.sources.length ? <div className="source-card-grid">{insight.sources.map((source) => <a className="source-card" href={`/documents/${document.id}?chunk=${source.chunk_number}#chunk-${source.chunk_number}`} key={source.chunk_number}><span>Chunk {source.chunk_number}</span><strong>{source.page_number ? `Page ${source.page_number}` : "Document"}</strong><small>{source.excerpt}</small></a>)}</div> : <div className="empty compact-empty">Sources appear with the explanation.</div>}
            </section>
          </aside>
        </div>
      )}

      {activeTab === "ask" && (
        <section className="panel">
          <div className="section-heading"><div><h2>Ask AI</h2><p>Answers are grounded only in this document.</p></div><Bot size={20} /></div>
          {askAnswer ? <article className="message"><div className="markdown"><Markdown>{askAnswer.answer}</Markdown></div><Sources sources={askAnswer.sources} /></article> : <div className="empty">Ask a question above to get a cited answer from this document.</div>}
        </section>
      )}

      {activeTab === "preview" && (
        <section className="panel viewer-panel">
          <div className="section-heading"><div><h2>{document.file_type === "pdf" ? "PDF preview" : "Extracted text preview"}</h2><p>Review the original document view or extracted text used for retrieval.</p></div><FileText size={20} /></div>
          {document.file_type === "pdf" && pdfUrl ? <iframe className="pdf-frame" title={`Preview of ${document.original_filename}`} src={`${pdfUrl}#page=${sourceChunk || 1}`} /> : null}
          {preview ? preview.sections.map((section, index) => <article className="preview-section formatted-text" key={index}><strong>{section.page_number ? `Page ${section.page_number}` : `Section ${index + 1}`}</strong><pre className="chunk-text">{section.text}</pre></article>) : <div className="empty">Preview will appear after extraction succeeds.</div>}
        </section>
      )}

      {activeTab === "chunks" && (
        <section className="panel">
          <div className="section-heading"><div><h2>Chunk viewer</h2><p>Collapsed cards show a preview. Expand shows the exact full chunk text returned by the backend.</p></div></div>
          <div className="chunk-grid">{preview?.chunks.map((chunk) => <ChunkCard chunk={chunk} active={sourceChunk === String(chunk.chunk_number)} key={chunk.chunk_number} />) ?? <div className="empty">Chunks appear after processing.</div>}</div>
        </section>
      )}

      {activeTab === "search" && (
        <section className="panel">
          <h2>Search</h2>
          <div className="filters stacked"><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find text in this document" /><button onClick={search}>Search</button></div>
          {results.length ? results.map((result, index) => <article className="search-hit" key={index}><strong>{result.page_number ? `Page ${result.page_number}` : "Document"}</strong><Markdown>{result.highlighted_excerpt || result.excerpt}</Markdown></article>) : <div className="empty compact-empty">Search results will appear here.</div>}
        </section>
      )}
    </section>
  );
}
