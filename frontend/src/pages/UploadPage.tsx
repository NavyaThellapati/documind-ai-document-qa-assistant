import { DragEvent, useState } from "react";
import { Upload } from "lucide-react";
import { api } from "../api/client";
import { useToast } from "../contexts/ToastContext";

export function UploadPage() {
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [dragging, setDragging] = useState(false);
  const { notify } = useToast();
  async function upload(file?: File) {
    if (!file) return;
    if (!["application/pdf", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"].includes(file.type) && !/\.(pdf|txt|docx)$/i.test(file.name)) {
      const message = "Please upload a PDF, TXT, or DOCX file.";
      setStatus(message);
      notify(message, "error");
      return;
    }
    setBusy(true);
    setProgress(0);
    setStatus("Processing document...");
    try {
      const result = await api.uploadWithProgress(file, setProgress);
      setStatus(`${result.message} Status: ${result.document.status}. Chunks: ${result.document.chunk_count}.`);
      notify(result.duplicate ? "Duplicate document found." : "Document uploaded. Processing has started.", "success");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setStatus(message);
      notify(message, "error");
    } finally {
      setBusy(false);
      setProgress(100);
    }
  }
  function drop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    upload(event.dataTransfer.files?.[0]);
  }
  return (
    <section className="page">
      <div className="page-title"><h1>Upload document</h1></div>
      <label className={`dropzone ${dragging ? "dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={drop}>
        <Upload size={38} />
        <strong>{busy ? "Working..." : "Choose a PDF, TXT, or DOCX file"}</strong>
        <span>Drag a document here or click to browse.</span>
        <input type="file" accept=".pdf,.txt,.docx" onChange={(event) => upload(event.target.files?.[0])} disabled={busy} />
      </label>
      {busy && <div className="progress"><span style={{ width: `${progress}%` }} /></div>}
      {busy && <div className="processing-pulse">Extracting text, chunking, embedding, and indexing...</div>}
      {status && <div className={status.includes("failed") || status.includes("Unsupported") ? "error" : "success"}>{status}</div>}
    </section>
  );
}
