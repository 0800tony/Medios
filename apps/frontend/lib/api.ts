const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Client = { id: string; name: string; industry: string; description: string };
export type User = { id: string; name: string; email: string };
export type Result = { diagnosis: string; evidence: string; hypotheses: string; contradictions: string; strategic_question: string; confidence: string; model_used: string };
export type EvidenceItem = { id: string; kind: "reference" | "client_note"; title: string; url: string; source: string; content: string; created_at: string };
export type KnowledgeItem = { id: string; kind: "article" | "video" | "photo"; title: string; url: string; source: string; notes: string; tags: string; content_type: string; size: number; ai_summary: string; ai_observations: string; index_status: string; created_at: string };
export type RadarSuggestion = { item: KnowledgeItem; status: "suggested" | "approved" | "dismissed"; score: number; reason: string };
export type DocumentItem = { id:string; filename:string; content_type:string; size:number; category:"document"|"audio"|"email"; processed:boolean; text_excerpt:string; created_at:string };
export type Project = { id: string; name: string; brief: string; objective: string; status: string; client_id: string; created_at: string; updated_at: string; documents: DocumentItem[]; evidence_items: EvidenceItem[]; result: Result | null };

export function token() { return typeof window === "undefined" ? "" : localStorage.getItem("oliva_token") || ""; }
export function logout() { localStorage.removeItem("oliva_token"); localStorage.removeItem("oliva_user"); window.location.href = "/login"; }

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string,string> || {}) };
  if (!(init.body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (token()) headers.Authorization = `Bearer ${token()}`;
  const response = await fetch(`${API}${path}`, { ...init, headers });
  if (response.status === 401 && typeof window !== "undefined") logout();
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.detail || "Ocurrió un error"); }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function requestBlob(path: string): Promise<Blob> {
  const response = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token()}` } });
  if (!response.ok) throw new Error("No se pudo cargar la imagen");
  return response.blob();
}

export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
