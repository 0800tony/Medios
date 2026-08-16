"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import ProjectFlow from "@/components/ProjectFlow";
import { Dossier, Project, StrategyDecision, request, requestBlob, saveBlob } from "@/lib/api";

const order = ["resumen_ejecutivo", "pedido_original", "interpretacion_del_pedido", "fuentes_y_calidad", "que_sabemos", "que_creemos", "que_no_sabemos", "diagnostico_del_problema", "objetivos_diferenciados", "comportamiento_a_cambiar", "categoria_y_competencia", "antecedentes_oliva", "audiencias", "barreras", "tension_humana", "insight", "oportunidad_estrategica", "rol_de_marca", "promesa", "razones_para_creer", "tono", "canales_y_contextos", "ruta_1", "ruta_2", "ruta_3", "ruta_4", "ruta_5", "ruta_6", "ruta_7", "comparacion_de_rutas", "riesgos", "indicadores", "preguntas_indispensables", "preguntas_importantes", "preguntas_deseables", "proxima_decision"];
const criticalFields: Record<string, string> = {
  "Arquitectura y relación entre las marcas": "brand_architecture",
  "Valor percibido y aceptación del precio": "price_value_evidence",
  "Capacidad productiva y de distribución": "capacity_distribution_evidence",
  "Priorización de audiencias": "audience_priority_evidence",
  "Prueba competitiva y de producto": "competitive_product_evidence",
  "Motivación y comportamiento real de las personas": "consumer_behavior_evidence",
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
    return <article className="critical-gap" key={`${gap.vacio}-${index}`}><h3>{gap.vacio}</h3><p><strong>Estado:</strong> {gap.estado || "Aproximación pendiente"}</p>{gap.respuesta_cargada && <p><strong>Respuesta actual:</strong> {gap.respuesta_cargada}</p>}<p><strong>Por qué importa:</strong> {gap.por_que_importa}</p><p><strong>Cómo aproximarlo ahora:</strong> {gap.aproximacion_suficiente || gap.evidencia_necesaria}</p>{gap.evidencia_ideal && <p><strong>Validación ideal, si es viable:</strong> {gap.evidencia_ideal}</p>}{field && <Link className="btn ghost" href={`/projects/${projectId}/brief#${field}`}>Cargar o mejorar esta aproximación →</Link>}</article>;
  })}</div>;
}

function CriticalGapActions({ value, projectId }: { value: unknown; projectId: string }) {
  if (!Array.isArray(value) || value.length === 0) return null;
  return <section className="card resolve-gaps"><p className="eyebrow">Siguiente paso</p><h2>Construí una base suficiente para avanzar</h2><p className="muted">La validación formal es ideal, no un requisito. Podés combinar observación local con estudios y publicaciones de terceros; cada botón abre el campo para registrar esa aproximación.</p><div className="inline-actions"><Link className="btn ghost" href={`/projects/${projectId}#research`}>Buscar información de terceros →</Link></div><div className="resolve-gap-actions">{value.map((item, index) => {
    const gap = item as Record<string, string>;
    const field = criticalFields[gap.vacio];
    return field ? <Link className="btn lime" key={`${gap.vacio}-${index}`} href={`/projects/${projectId}/brief#${field}`}>{index + 1}. Responder: {gap.vacio} →</Link> : null;
  })}</div></section>;
}

function StrategicRecommendation({ value }: { value: unknown }) {
  if (!value || typeof value !== "object") return null;
  const decision = value as Record<string, string>;
  if (!decision.recomendacion_estrategica) return null;
  return <section className="card strategic-recommendation"><p className="eyebrow">Recomendación de OLIVA Strategy</p><h2>{decision.recomendacion_estrategica}</h2><p>{decision.por_que_ahora}</p><dl className="structured"><div><dt>Primer movimiento</dt><dd><p>{decision.primer_movimiento}</p></dd></div><div><dt>No hacer todavía</dt><dd><p>{decision.no_hacer_aun}</p></dd></div></dl><p className="muted smallprint">Recomendación de trabajo basada en la evidencia disponible y aproximaciones explícitas. Se revisa con el aprendizaje del lanzamiento.</p></section>;
}

function RouteDecision({ dossier, decision, busy, savedMessage, onSave }: { dossier: Dossier; decision: StrategyDecision | null; busy: boolean; savedMessage: string; onSave: (routeKey: string, rationale: string, launchPlan: string) => Promise<void> }) {
  const [routeKey, setRouteKey] = useState(decision?.route_key || "ruta_1");
  const [rationale, setRationale] = useState(decision?.rationale || "");
  const [launchPlan, setLaunchPlan] = useState(decision?.launch_plan || "");
  useEffect(() => { setRouteKey(decision?.route_key || "ruta_1"); setRationale(decision?.rationale || ""); setLaunchPlan(decision?.launch_plan || ""); }, [decision]);
  const routeKeys = Object.keys(dossier.sections).filter(key => /^ruta_[1-7]$/.test(key)).sort((a, b) => Number(a.slice(5)) - Number(b.slice(5)));
  const route = dossier.sections[routeKey] as Record<string, unknown> | undefined;
  return <section className="card route-decision"><p className="eyebrow">Decisión de trabajo</p><h2>Elegí la ruta que va a guiar el desarrollo creativo</h2><p className="muted">OLIVA propone rutas; la elección queda explícita para que cada pieza se evalúe contra una decisión real, no contra un diagnóstico genérico.</p>
    <form onSubmit={async event => { event.preventDefault(); await onSave(routeKey, rationale, launchPlan); }}>
      <div className="field"><label>Ruta estratégica</label><select value={routeKey} onChange={event => setRouteKey(event.target.value)}>{routeKeys.map(key => { const candidate = dossier.sections[key] as Record<string, unknown> | undefined; return <option value={key} key={key}>{String(candidate?.nombre || key.replace("_", " "))}</option>; })}</select></div>
      {route && <div className="route-preview"><strong>{String(route.nombre || routeKey)}</strong><p>{String(route.problema_que_resuelve || route.hipotesis || route.condicion_para_elegirla || "")}</p><p className="muted">{String(route.condicion_para_elegirla || "")}</p></div>}
      <div className="field"><label>Por qué elegimos esta ruta</label><textarea value={rationale} onChange={event => setRationale(event.target.value)} required minLength={12} placeholder="Qué problema resuelve primero y por qué es la prioridad."/></div>
      <div className="field"><label>Primer plan de activación</label><textarea value={launchPlan} onChange={event => setLaunchPlan(event.target.value)} required minLength={12} placeholder="Qué haremos, dónde, con quién y qué vamos a aprender."/></div>
      <div className="route-save-row"><button className="btn lime" disabled={busy}>{busy ? "Guardando y confirmando…" : decision ? "Actualizar ruta y continuar →" : "Guardar ruta y continuar →"}</button>{savedMessage && <p className="success" role="status">{savedMessage}</p>}</div>
    </form>
  </section>;
}

export default function ResultPage({ params }: { params: { id: string } }) {
  const [project, setProject] = useState<Project | null>(null);
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [decision, setDecision] = useState<StrategyDecision | null>(null);
  const [missingStrategy, setMissingStrategy] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [decisionSaved, setDecisionSaved] = useState("");

  async function load() {
    setError(""); setMissingStrategy(false);
    const projectData = await request<Project>(`/api/projects/${params.id}`);
    setProject(projectData);
    try { const strategy = await request<Dossier>(`/api/projects/${params.id}/strategy`); setDossier(strategy); try { setDecision(await request<StrategyDecision>(`/api/projects/${params.id}/strategy/decision`)); } catch { setDecision(null); } }
    catch (error) { setMissingStrategy(true); setError((error as Error).message); }
  }
  useEffect(() => { load().catch(error => setError(error.message)); }, [params.id]);

  async function generate() { setBusy(true); setError(""); try { await request(`/api/projects/${params.id}/analyze`, { method: "POST" }); await load(); } catch (error) { setError((error as Error).message); } finally { setBusy(false); } }
  async function expandRoutes() { setBusy(true); setError(""); setDecisionSaved(""); try { const expanded = await request<Dossier>(`/api/projects/${params.id}/strategy/expand-routes`, { method: "POST" }); setDossier(expanded); try { setDecision(await request<StrategyDecision>(`/api/projects/${params.id}/strategy/decision`)); } catch { setDecision(null); } setDecisionSaved("Se ampliaron las alternativas sin recalcular ni cambiar la ruta que ya habías elegido."); } catch (error) { setError((error as Error).message); } finally { setBusy(false); } }
  async function approve(status: string) { setBusy(true); try { setDossier(await request<Dossier>(`/api/projects/${params.id}/strategy/approval`, { method: "PATCH", body: JSON.stringify({ status, notes: "" }) })); } catch (error) { setError((error as Error).message); } finally { setBusy(false); } }
  async function saveDecision(routeKey: string, rationale: string, launchPlan: string) {
    setBusy(true); setError(""); setDecisionSaved("");
    try {
      const saved = await request<StrategyDecision>(`/api/projects/${params.id}/strategy/decision`, { method: "PUT", body: JSON.stringify({ route_key: routeKey, rationale, launch_plan: launchPlan }) });
      setDecision(saved);
      setDossier(await request<Dossier>(`/api/projects/${params.id}/strategy`));
      setDecisionSaved(`Ruta guardada y estrategia confirmada a las ${new Intl.DateTimeFormat("es-UY", { hour: "2-digit", minute: "2-digit" }).format(new Date())}. Ya podés continuar al desarrollo creativo.`);
    } catch (error) { setError(`No se pudo guardar la ruta: ${(error as Error).message}`); } finally { setBusy(false); }
  }
  async function download() { setBusy(true); try { saveBlob(await requestBlob(`/api/projects/${params.id}/report`), `estrategia-${project?.name || "oliva"}.md`); } catch (error) { setError((error as Error).message); } finally { setBusy(false); } }

  if (!project) return <main className="shell"><Nav/><p>{error || "Cargando proyecto…"}</p></main>;
  if (!dossier && missingStrategy) return <main className="shell"><Nav/><div className="empty"><p className="eyebrow">OLIVA Strategy</p><h2>El brief está guardado, pero todavía no se generó el contrabrief.</h2><p className="muted">Generarlo ahora analizará el brief, los documentos, las evidencias y las señales del Radar aprobadas.</p>{error && <p className="error">{error}</p>}<div className="inline-actions" style={{ justifyContent: "center" }}><button className="btn lime" disabled={busy} onClick={generate}>{busy ? "Generando estrategia…" : "Generar estrategia ahora →"}</button><Link className="btn ghost" href={`/projects/${params.id}/brief`}>Revisar brief</Link></div></div></main>;
  if (!dossier) return <main className="shell"><Nav/><p>Cargando estrategia…</p></main>;

  return <main className="shell result-page"><Nav/>
    <div className="pagehead"><div><p className="eyebrow">Contrabrief · Versión {dossier.version}</p><h1>{project.name}</h1><div className="strategy-status"><span className="status">{dossier.approval_status.replace("_", " ")}</span><small>{dossier.model_used}</small></div></div><div className="page-actions"><button className="btn lime" onClick={download}>Descargar</button><button className="btn ghost" disabled={busy || Object.keys(dossier.sections).filter(key => /^ruta_[1-7]$/.test(key)).length >= 7} onClick={expandRoutes}>Ampliar análisis de rutas</button><Link className="btn ghost" href={`/projects/${project.id}/brief`}>Editar brief</Link><Link className="btn ghost" href={`/projects/${project.id}`}>← Evidencia</Link></div></div><ProjectFlow projectId={project.id} current="strategy" hasStrategy={true}/>
    <section className="approval-bar"><div><strong>{dossier.approval_status === "approved" ? "Estrategia confirmada" : "Confirmación estratégica"}</strong><p>{dossier.approval_status === "approved" ? "La ruta, su fundamento y el primer plan ya están guardados. Podés pasar al desarrollo creativo." : "Guardá la ruta elegida para confirmar esta versión y continuar. Los riesgos quedan visibles, pero no bloquean el avance."}</p></div><div className="inline-actions">{dossier.approval_status === "approved" ? <Link className="btn lime" href={`/projects/${project.id}/creative`}>Continuar a creatividad →</Link> : <button className="btn lime" disabled={busy || !decision} onClick={() => approve("approved")}>{decision ? "Confirmar estrategia y continuar →" : "Elegí una ruta para continuar"}</button>}<button className="btn ghost" disabled={busy} onClick={() => approve("changes")}>Volver a revisión</button></div></section>
    <StrategicRecommendation value={dossier.sections.proxima_decision}/>
    <RouteDecision dossier={dossier} decision={decision} busy={busy} savedMessage={decisionSaved} onSave={saveDecision}/>
    <CriticalGapActions value={dossier.sections.que_no_sabemos} projectId={project.id}/>
    {error && <p className="error">{error}</p>}<section className="dossier">{order.map((key, index) => <article className={`card dossier-section ${["resumen_ejecutivo", "que_no_sabemos", "diagnostico_del_problema", "insight", "oportunidad_estrategica", "comparacion_de_rutas", "proxima_decision"].includes(key) ? "featured" : ""}`} key={key}><p className="section-number">{String(index + 1).padStart(2, "0")}</p><h2>{key === "que_no_sabemos" ? "Vacíos críticos: qué falta y cómo resolverlo" : key.replaceAll("_", " ")}</h2>{key === "que_no_sabemos" ? <CriticalGaps value={dossier.sections[key]} projectId={project.id}/> : <Content value={dossier.sections[key]}/>}</article>)}</section>
  </main>;
}
