const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Client = { id: string; name: string; industry: string; description: string };
export type Result = { diagnosis: string; evidence: string; hypotheses: string; contradictions: string; strategic_question: string; confidence: string; model_used: string };
export type Project = { id: string; name: string; brief: string; objective: string; status: string; client_id: string; created_at: string; documents: {id:string; filename:string; size:number}[]; result: Result | null };

export function token() { return typeof window === "undefined" ? "" : localStorage.getItem("oliva_token") || ""; }
export function logout() { localStorage.removeItem("oliva_token"); localStorage.removeItem("oliva_user"); window.location.href = "/login"; }

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string,string> || {}) };
  if (!(init.body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (token()) headers.Authorization = `Bearer ${token()}`;
  const response = await fetch(`${API}${path}`, { ...init, headers });
  if (response.status === 401 && typeof window !== "undefined") logout();
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.detail || "Ocurrió un error"); }
  return response.json();
}
