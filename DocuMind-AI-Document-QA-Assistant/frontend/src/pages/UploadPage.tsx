import { ChangeEvent, useState } from "react";
import { Upload } from "lucide-react";
import { api } from "../api/client";

export function UploadPage() {
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setStatus("Processing document...");
    try {
      const result = await api.upload(file);
      setStatus(`${result.message} Status: ${result.document.status}. Chunks: ${result.document.chunk_count}.`);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="page">
      <div className="page-title"><h1>Upload document</h1></div>
      <label className="dropzone">
        <Upload size={38} />
        <strong>{busy ? "Working..." : "Choose a PDF, TXT, or DOCX file"}</strong>
        <span>Files are stored locally for development and indexed into ChromaDB.</span>
        <input type="file" accept=".pdf,.txt,.docx" onChange={upload} disabled={busy} />
      </label>
      {status && <div className={status.includes("failed") || status.includes("Unsupported") ? "error" : "success"}>{status}</div>}
    </section>
  );
}
