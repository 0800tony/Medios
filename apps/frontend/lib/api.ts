const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Client = { id: string; name: string; industry: string; description: string };
export type User = { id: string; name: string; email: string };
export type Result = { diagnosis: string; evidence: string; hypotheses: string; contradictions: string; strategic_question: string; confidence: string; model_used: string };
export type EvidenceItem = { id: string; kind: "reference" | "client_note"; title: string; url: string; source: string; content: string; created_at: string };
export type KnowledgeItem = { id: string; kind: "article" | "video" | "photo"; title: string; url: string; source: string; notes: string; tags: string; content_type: string; size: number; ai_summary: string; ai_observations: string; index_status: string; created_at: string };
export type RadarSuggestion = { item: KnowledgeItem; status: "suggested" | "approved" | "dismissed"; score: number; reason: string };
export type DocumentItem = { id:string; filename:string; content_type:string; size:number; category:"document"|"audio"|"email"; processed:boolean; text_excerpt:string; created_at:string };
export type Project = { id: string; name: string; brief: string; objective: string; status: string; workflow_stage:string; group_company:string; participants:string; territory:string; deadline:string; budget:string; confidentiality:string; client_id: string; created_at: string; updated_at: string; documents: DocumentItem[]; evidence_items: EvidenceItem[]; result: Result | null };
export type Brief={data:Record<string,string>;completeness:number;missing_required:string[]};
export type Dossier={id:string;version:number;sections:Record<string,unknown>;approval_status:"draft"|"approved"|"changes"|"rejected"|"pending_information";approval_notes:string;model_used:string;created_at:string};
export type StrategyDecision={id:string;project_id:string;dossier_id:string;route_key:"ruta_1"|"ruta_2"|"ruta_3";rationale:string;launch_plan:string;created_at:string;updated_at:string};
export type LibraryItem={id:string;kind:string;title:string;url:string;source:string;description:string;tags:string;year:string;festival:string;award:string;results:string;client_id:string|null;content_type:string;size:number;ai_analysis:string;created_at:string};
export type CreativeReview={id:string;project_id:string;name:string;medium:string;rationale:string;filename:string;content_type:string;size:number;verdict:string;scores:Record<string,number>;evaluation:string;model_used:string;created_at:string};
export type CreativeTerritory={id:string;nombre:string;tension:string;idea_central:string;rol_de_marca:string;tipo_de_campana:string;estilo:string;tono:string;medios:string[];propiedad:string;riesgos_y_cliches:string;control:string};
export type CreativeConcept={id:string;project_id:string;dossier_id:string;decision_id:string;title:string;content:Record<string,unknown>;status:"draft"|"selected"|"rejected";model_used:string;created_at:string;updated_at:string};
export type CampaignPlanItem={id:string;[key:string]:string};
export type CreativeProductionPlan={id:string;project_id:string;concept_id:string;content:Record<string,unknown>;status:"draft"|"approved";model_used:string;created_at:string;updated_at:string};
export type BrandAsset={id:string;client_id:string;label:string;filename:string;content_type:string;size:number;palette:string;created_at:string};
export type CreativeVisual={id:string;project_id:string;plan_id:string;title:string;prompt:string;status:string;model_used:string;created_at:string};
export type ClientMemory={id:string;client_id:string;data:Record<string,string>;version:number;updated_at:string};
export type LearningRecord={id:string;project_id:string|null;client_id:string|null;title:string;content:string;source_type:string;tags:string;confidence:string;status:string;evidence:string[];created_at:string;updated_at:string};
export type ApprovalTask={id:string;project_id:string|null;kind:string;entity_id:string;title:string;summary:string;status:string;notes:string;created_at:string;resolved_at:string|null};
export type AgentDefinition={key:string;name:string;stage:string;description:string};
export type AgentRun={id:string;project_id:string;agent_key:string;instruction:string;output:Record<string,unknown>;status:string;model_used:string;created_at:string};
export type Foundation={references:{author:string;work:string;lens:string}[];creative_lenses:{group:string;names:string;lens:string}[];festivals:{id:string;name:string;url:string;focus:string}[];principle:string};
export type ResearchSource={id:string;name:string;url:string;domain:string;country:string;topic:string;description:string;priority:number;active:boolean;is_foundational:boolean;created_at:string};
export type CreativeNote={id:string;project_id:string;concept_id:string|null;kind:"idea"|"feedback"|"decision"|"reference";author:string;content:string;status:"open"|"applied"|"discarded";created_at:string;updated_at:string};
export type ProductionPackage={campaign:string;status:string;strategy:string;deliverables:{pieza:string;formato:string;objetivo:string;guion:string;produccion:string}[];assets:string[];confirmations:string[];handoff:string[]};
export type ProjectTask={id:string;project_id:string;title:string;description:string;assignee:string;stage:string;status:"pending"|"in_progress"|"blocked"|"done";priority:"alta"|"media"|"baja";due_date:string;created_at:string;updated_at:string};
export type CreativeAnnotation={id:string;creative_submission_id:string;project_id:string;author:string;comment:string;x:number;y:number;status:"open"|"resolved"|"dismissed";created_at:string;updated_at:string};
export type Measurement={id:string;project_id:string;metric:string;value:string;baseline:string;target:string;period:string;source:string;notes:string;created_at:string};
export type MarketWatch={id:string;client_id:string|null;name:string;query:string;kind:"competitor"|"category"|"source_monitor";active:boolean;last_summary:string;last_sources:{title:string;url:string}[];last_checked_at:string|null;created_at:string};
export type Governance={models:Record<string,string>;audit:{agentes_ejecutados:number;bocetos_generados:number;aprendizajes_aprobados:number};controls:string[];api_configured:boolean};

export function token() { return typeof window === "undefined" ? "" : localStorage.getItem("oliva_token") || ""; }
export function logout() { localStorage.removeItem("oliva_token"); localStorage.removeItem("oliva_user"); window.location.href = "/login"; }

function readableError(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(entry => {
    const issue = entry as Record<string, unknown>;
    const location = Array.isArray(issue.loc) && issue.loc.length ? String(issue.loc[issue.loc.length - 1]) : "dato";
    return `${location}: ${String(issue.msg || "Valor inválido")}`;
  }).join(" · ");
  return "Ocurrió un error. Revisá los datos e intentá nuevamente.";
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string,string> || {}) };
  if (!(init.body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (token()) headers.Authorization = `Bearer ${token()}`;
  const response = await fetch(`${API}${path}`, { ...init, headers });
  if (response.status === 401 && typeof window !== "undefined") logout();
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(readableError(data.detail)); }
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
