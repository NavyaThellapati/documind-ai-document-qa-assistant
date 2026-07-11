import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { RotateCw } from "lucide-react";
import { api, DocumentItem } from "../api/client";

export function DocumentDetails() {
  const { id } = useParams();
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { if (id) api.document(id).then(setDocument).catch((err) => setError(err.message)); }, [id]);
  async function reprocess() {
    if (!id) return;
    setDocument(await api.reprocess(id));
  }
  if (error) return <section className="page"><div className="error">{error}</div></section>;
  if (!document) return <section className="page">Loading...</section>;
  return (
    <section className="page">
      <div className="page-title"><h1>{document.original_filename}</h1><button className="button" onClick={reprocess}><RotateCw size={16} /> Reprocess</button></div>
      <div className="detail-grid">
        <div><span>Status</span><strong>{document.status}</strong></div>
        <div><span>Chunks</span><strong>{document.chunk_count}</strong></div>
        <div><span>Size</span><strong>{Math.round(document.file_size / 1024)} KB</strong></div>
        <div><span>Uploaded</span><strong>{new Date(document.created_at).toLocaleString()}</strong></div>
      </div>
      {document.error_message && <div className="error">{document.error_message}</div>}
    </section>
  );
}
