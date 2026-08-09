"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { Dossier, Project, request, requestBlob, saveBlob } from "@/lib/api";

const order = ["resumen_ejecutivo", "pedido_original", "interpretacion_del_pedido", "fuentes_y_calidad", "que_sabemos", "que_creemos", "que_no_sabemos", "diagnostico_del_problema", "objetivos_diferenciados", "comportamiento_a_cambiar", "categoria_y_competencia", "antecedentes_oliva", "audiencias", "barreras", "tension_humana", "insight", "oportunidad_estrategica", "rol_de_marca", "promesa", "razones_para_creer", "tono", "canales_y_contextos", "ruta_1", "ruta_2", "ruta_3", "comparacion_de_rutas", "riesgos", "indicadores", "preguntas_indispensables", "preguntas_importantes", "preguntas_deseables", "proxima_decision"];
const criticalFields: Record<string, string> = {
  "Arquitectura y relación entre las marcas": "brand_architecture",
  "Valor percibido y aceptación del precio": "price_value_evidence",
  "Capacidad productiva y de distribución": "capacity_distribution_evidence",
  "Priorización de audiencias": "audience_priority_evidence",
  "Prueba competitiva y de producto": "competitive_product_evidence",
  "Motivación y comportamiento real de las personas": "motivations",
};

function Content({ value }: { value: unknown }) {
  if (Array.isArray(value)) return <ul className="structured">{value.map((item, index) => <li key={index}><Content value={item}/></li>)}</ul>;
  if (value && typeof value === "object") return <dl className="structured">{Object.entries(value as Record<string, unknown>).map(([key, item]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd><Content value={item}/></dd></div>)}</dl>;
  return <p>{String(value ?? "")}</p>;
}

function CriticalGaps({ value, projectId }: { value: unknown; projectId: string }) {
  if (!Array.isArray(value) || value.length === 0) return <p>No quedan vacíos críticos registrados en esta versión.</p>;
  return <div className="critical-gaps">{value.map((item, index) => {
    const gap = item as Record<string, string>;
    const field = criticalFields[gap.vacio];
    return <article className="critical-gap" key={`${gap.vacio}-${index}`}><h3>{gap.vacio}</h3><p><strong>Por qué importa:</strong> {gap.por_que_importa}</p><p><strong>Pregunta a responder:</strong> {gap.pregunta}</p><p><strong>Qué cargar:</strong> {gap.evidencia_necesaria}</p>{field && <Link className="btn ghost" href={`/projects/${projectId}/brief#${field}`}>Responder este vacío en el brief →</Link>}</article>;
  })}</div>;
}

export default function ResultPage({ params }: { params: { id: string } }) {
  const [project, setProject] = useState<Project | null>(null);
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [missingStrategy, setMissingStrategy] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setError(""); setMissingStrategy(false);
    const projectData = await request<Project>(`/api/projects/${params.id}`);
    setProject(projectData);
    try { setDossier(await request<Dossier>(`/api/projects/${params.id}/strategy`)); }
    catch (error) { setMissingStrategy(true); setError((error as Error).message); }
  }
  useEffect(() => { load().catch(error => setError(error.message)); }, [params.id]);

  async function generate() { setBusy(true); setError(""); try { await request(`/api/projects/${params.id}/analyze`, { method: "POST" }); await load(); } catch (error) { setError((error as Error).message); } finally { setBusy(false); } }
  async function approve(status: string) { setBusy(true); try { setDossier(await request<Dossier>(`/api/projects/${params.id}/strategy/approval`, { method: "PATCH", body: JSON.stringify({ status, notes: "" }) })); } catch (error) { setError((error as Error).message); } finally { setBusy(false); } }
  async function download() { setBusy(true); try { saveBlob(await requestBlob(`/api/projects/${params.id}/report`), `estrategia-${project?.name || "oliva"}.md`); } catch (error) { setError((error as Error).message); } finally { setBusy(false); } }

  if (!project) return <main className="shell"><Nav/><p>{error || "Cargando proyecto…"}</p></main>;
  if (!dossier && missingStrategy) return <main className="shell"><Nav/><div className="empty"><p className="eyebrow">OLIVA Strategy</p><h2>El brief está guardado, pero todavía no se generó el contrabrief.</h2><p className="muted">Generarlo ahora analizará el brief, los documentos, las evidencias y las señales del Radar aprobadas.</p>{error && <p className="error">{error}</p>}<div className="inline-actions" style={{ justifyContent: "center" }}><button className="btn lime" disabled={busy} onClick={generate}>{busy ? "Generando estrategia…" : "Generar estrategia ahora →"}</button><Link className="btn ghost" href={`/projects/${params.id}/brief`}>Revisar brief</Link></div></div></main>;
  if (!dossier) return <main className="shell"><Nav/><p>Cargando estrategia…</p></main>;

  return <main className="shell result-page"><Nav/>
    <div className="pagehead"><div><p className="eyebrow">Contrabrief · Versión {dossier.version}</p><h1>{project.name}</h1><div className="strategy-status"><span className="status">{dossier.approval_status.replace("_", " ")}</span><small>{dossier.model_used}</small></div></div><div className="page-actions"><button className="btn lime" onClick={download}>Descargar</button><Link className="btn ghost" href={`/projects/${project.id}/brief`}>Editar brief</Link><Link className="btn ghost" href={`/projects/${project.id}`}>← Evidencia</Link></div></div>
    <section className="approval-bar"><div><strong>Aprobación humana</strong><p>Podés aprobar esta versión de trabajo y avanzar. Los vacíos críticos quedan visibles como riesgos a validar, no como un bloqueo.</p></div><div className="inline-actions"><button className="btn lime" disabled={busy} onClick={() => approve("approved")}>Aprobar versión de trabajo</button><button className="btn ghost" disabled={busy} onClick={() => approve("changes")}>Pedir cambios</button>{dossier.approval_status === "approved" && <Link className="btn" href={`/projects/${project.id}/creative`}>Revisar propuestas →</Link>}</div></section>
    {error && <p className="error">{error}</p>}<section className="dossier">{order.map((key, index) => <article className={`card dossier-section ${["resumen_ejecutivo", "que_no_sabemos", "diagnostico_del_problema", "insight", "oportunidad_estrategica", "comparacion_de_rutas", "proxima_decision"].includes(key) ? "featured" : ""}`} key={key}><p className="section-number">{String(index + 1).padStart(2, "0")}</p><h2>{key === "que_no_sabemos" ? "Vacíos críticos: qué falta y cómo resolverlo" : key.replaceAll("_", " ")}</h2>{key === "que_no_sabemos" ? <CriticalGaps value={dossier.sections[key]} projectId={project.id}/> : <Content value={dossier.sections[key]}/>}</article>)}</section>
  </main>;
}
