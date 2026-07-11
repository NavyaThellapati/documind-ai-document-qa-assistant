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
  created_at: string;
  updated_at: string;
};
export type Source = {
  id?: string | null;
  document_id?: string | null;
  document_name: string;
  page_number?: number | null;
  chunk_number: number;
  excerpt: string;
  relevance_score?: number | null;
};
export type Message = { id: string; question: string; answer: string; sources: Source[]; created_at: string };
export type Conversation = { id: string; title: string; created_at: string; updated_at: string; messages: Message[] };
export type ConversationSummary = Omit<Conversation, "messages"> & { message_count: number };

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("documind_token");
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new ApiError(response.status, payload.detail ?? "Request failed");
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export const api = {
  register: (payload: { email: string; password: string; full_name?: string }) =>
    request<{ access_token: string; user: User }>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: { email: string; password: string }) =>
    request<{ access_token: string; user: User }>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request<User>("/auth/me"),
  documents: (params = "") => request<{ documents: DocumentItem[] }>(`/documents${params}`),
  document: (id: string) => request<DocumentItem>(`/documents/${id}`),
  upload: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<{ document: DocumentItem; duplicate: boolean; message: string }>("/documents/upload", { method: "POST", body });
  },
  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),
  reprocess: (id: string) => request<DocumentItem>(`/documents/${id}/reprocess`, { method: "POST" }),
  conversations: () => request<ConversationSummary[]>("/chat/conversations"),
  conversation: (id: string) => request<Conversation>(`/chat/conversations/${id}`),
  createConversation: (title: string) => request<Conversation>("/chat/conversations", { method: "POST", body: JSON.stringify({ title }) }),
  renameConversation: (id: string, title: string) =>
    request<Conversation>(`/chat/conversations/${id}`, { method: "PATCH", body: JSON.stringify({ title }) }),
  deleteConversation: (id: string) => request<void>(`/chat/conversations/${id}`, { method: "DELETE" }),
  ask: (payload: { question: string; conversation_id?: string; document_ids: string[] }) =>
    request<{ conversation_id: string; message_id: string; answer: string; sources: Source[] }>("/chat/ask", { method: "POST", body: JSON.stringify(payload) }),
  feedback: (payload: { message_id: string; helpful: boolean; comment?: string }) =>
    request("/feedback", { method: "POST", body: JSON.stringify(payload) }),
};
