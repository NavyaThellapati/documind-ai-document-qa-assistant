export type User = { id: string; email: string; full_name?: string | null; created_at: string };
export type DocumentItem = {
  id: string;
  filename: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  status: string;
  error_message?: string | null;
  chunk_count: number;
  page_count?: number | null;
  embedding_status: string;
  processed_at?: string | null;
  created_at: string;
  updated_at: string;
  file_type: string;
  processing_progress: number;
};
export type Source = {
  id?: string | null;
  document_id?: string | null;
  document_name: string;
  page_number?: number | null;
  chunk_number: number;
  excerpt: string;
  relevance_score?: number | null;
  highlighted_excerpt?: string | null;
};
export type Message = { id: string; question: string; answer: string; sources: Source[]; created_at: string };
export type Conversation = { id: string; title: string; created_at: string; updated_at: string; messages: Message[] };
export type ConversationSummary = Omit<Conversation, "messages"> & { message_count: number };
export type DashboardSummary = {
  total_documents: number;
  ready_documents: number;
  processed_documents: number;
  processing_documents: number;
  failed_documents: number;
  total_chats: number;
  questions_asked: number;
  storage_used_bytes: number;
  recent_documents: Array<{ id: string; name: string; status: string; embedding_status: string; created_at: string }>;
  recent_conversations: Array<{ id: string; title: string; updated_at: string }>;
  ai_usage_summary: { questions_asked: number; retrieval_top_k: number; llm_provider: string };
};
export type DocumentPreview = {
  document: DocumentItem;
  sections: Array<{ page_number?: number | null; text: string }>;
  chunks: Array<{ page_number?: number | null; chunk_number: number; text: string }>;
};

const API_URL = import.meta.env.VITE_API_URL ?? "/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function errorMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) return String((item as { msg: unknown }).msg);
        return String(item);
      })
      .join("; ");
  }
  return "Request failed";
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("documind_token");
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new ApiError(response.status, errorMessage(payload.detail));
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export const api = {
  register: (payload: { email: string; password: string; full_name?: string }) =>
    request<{ access_token: string; refresh_token: string; user: User }>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: { email: string; password: string }) =>
    request<{ access_token: string; refresh_token: string; user: User }>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  logout: (refreshToken: string) => request<void>("/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) }),
  forgotPassword: (email: string) => request<{ message: string }>("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) }),
  me: () => request<User>("/auth/me"),
  dashboard: () => request<DashboardSummary>("/dashboard/summary"),
  documents: (params = "") => request<{ documents: DocumentItem[] }>(`/documents${params}`),
  document: (id: string) => request<DocumentItem>(`/documents/${id}`),
  upload: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<{ document: DocumentItem; duplicate: boolean; message: string }>("/documents/upload", { method: "POST", body });
  },
  uploadWithProgress: (file: File, onProgress: (percent: number) => void) =>
    new Promise<{ document: DocumentItem; duplicate: boolean; message: string }>((resolve, reject) => {
      const token = localStorage.getItem("documind_token");
      const body = new FormData();
      body.append("file", file);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_URL}/documents/upload`);
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
      };
      xhr.onload = () => {
        const payload = JSON.parse(xhr.responseText || "{}");
        if (xhr.status >= 200 && xhr.status < 300) resolve(payload);
        else reject(new ApiError(xhr.status, errorMessage(payload.detail)));
      };
      xhr.onerror = () => reject(new ApiError(0, "Network error during upload"));
      xhr.send(body);
    }),
  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),
  reprocess: (id: string) => request<DocumentItem>(`/documents/${id}/reprocess`, { method: "POST" }),
  reprocessBackground: (id: string) => request<DocumentItem>(`/documents/${id}/reprocess/background`, { method: "POST" }),
  searchDocument: (id: string, query: string) => request<{ query: string; results: Array<{ page_number?: number | null; excerpt: string; highlighted_excerpt?: string | null }> }>(`/documents/${id}/search?query=${encodeURIComponent(query)}`),
  previewDocument: (id: string) => request<DocumentPreview>(`/documents/${id}/preview`),
  async downloadDocument(id: string, filename: string) {
    const token = localStorage.getItem("documind_token");
    const response = await fetch(`${API_URL}/documents/${id}/download`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: "Download failed" }));
      throw new ApiError(response.status, errorMessage(payload.detail));
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  },
  conversations: () => request<ConversationSummary[]>("/chat/conversations"),
  conversation: (id: string) => request<Conversation>(`/chat/conversations/${id}`),
  createConversation: (title: string) => request<Conversation>("/chat/conversations", { method: "POST", body: JSON.stringify({ title }) }),
  renameConversation: (id: string, title: string) =>
    request<Conversation>(`/chat/conversations/${id}`, { method: "PATCH", body: JSON.stringify({ title }) }),
  deleteConversation: (id: string) => request<void>(`/chat/conversations/${id}`, { method: "DELETE" }),
  ask: (payload: { question: string; conversation_id?: string; document_ids: string[] }) =>
    request<{ conversation_id: string; message_id: string; answer: string; sources: Source[]; confidence_score?: number | null }>("/chat/ask", { method: "POST", body: JSON.stringify(payload) }),
  async streamAsk(
    payload: { question: string; conversation_id?: string; document_ids: string[] },
    onToken: (token: string) => void,
    signal?: AbortSignal,
  ) {
    const token = localStorage.getItem("documind_token");
    const response = await fetch(`${API_URL}/chat/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify(payload),
      signal,
    });
    if (!response.ok || !response.body) {
      const error = await response.json().catch(() => ({ detail: "Streaming request failed" }));
      throw new ApiError(response.status, errorMessage(error.detail));
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalPayload: { conversation_id: string; message_id: string; answer: string; sources: Source[]; confidence_score?: number | null } | null = null;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";
      for (const event of events) {
        const eventName = event.match(/^event: (.+)$/m)?.[1];
        const data = event.match(/^data: (.+)$/m)?.[1];
        if (!data) continue;
        const parsed = JSON.parse(data);
        if (eventName === "token") onToken(parsed.token);
        if (eventName === "done") finalPayload = parsed;
      }
    }
    if (!finalPayload) throw new ApiError(500, "No final chat payload received");
    return finalPayload;
  },
  feedback: (payload: { message_id: string; helpful: boolean; comment?: string }) =>
    request("/feedback", { method: "POST", body: JSON.stringify(payload) }),
};
