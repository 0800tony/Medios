"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { CampaignPlanItem, CreativeConcept, CreativeProductionPlan, CreativeReview, CreativeTerritory, Dossier, Project, StrategyDecision, request } from "@/lib/api";

const labels: Record<string, string> = { estrategia: "Estrategia", verdad_humana: "Verdad humana", rol_de_marca: "Rol de marca", apropiabilidad: "Propiedad", originalidad: "Originalidad", claridad: "Claridad", fertilidad: "Fertilidad", coherencia: "Coherencia", adecuacion_al_medio: "Adecuación al medio", viabilidad: "Viabilidad" };
const copy = <T,>(value: T): T => JSON.parse(JSON.stringify(value));

function territories(board: Record<string, unknown> | null): CreativeTerritory[] {
  return Array.isArray(board?.territorios) ? board!.territorios as CreativeTerritory[] : [];
}
function planItems(plan: Record<string, unknown> | null, key: "piezas_creativas" | "soportes_de_medios"): CampaignPlanItem[] {
  return Array.isArray(plan?.[key]) ? plan![key] as CampaignPlanItem[] : [];
}
function productionItems(plan: Record<string, unknown> | null): CampaignPlanItem[] {
  return Array.isArray(plan?.propuestas_de_produccion) ? plan!.propuestas_de_produccion as CampaignPlanItem[] : [];
}

export default function Creative({ params }: { params: { id: string } }) {
  const [project, setProject] = useState<Project | null>(null);
  const [strategy, setStrategy] = useState<Dossier | null>(null);
  const [decision, setDecision] = useState<StrategyDecision | null>(null);
  const [concepts, setConcepts] = useState<CreativeConcept[]>([]);
  const [plans, setPlans] = useState<CreativeProductionPlan[]>([]);
  const [planBoard, setPlanBoard] = useState<Record<string, unknown> | null>(null);
  const [reviews, setReviews] = useState<CreativeReview[]>([]);
  const [board, setBoard] = useState<Record<string, unknown> | null>(null);
  const [territoryId, setTerritoryId] = useState("");
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    const [projectData, conceptData, reviewData, planData] = await Promise.all([
      request<Project>(`/api/projects/${params.id}`), request<CreativeConcept[]>(`/api/projects/${params.id}/creative-concepts`), request<CreativeReview[]>(`/api/projects/${params.id}/creative`), request<CreativeProductionPlan[]>(`/api/projects/${params.id}/creative-plans`),
    ]);
    setProject(projectData); setConcepts(conceptData); setReviews(reviewData); setPlans(planData);
    request<Dossier>(`/api/projects/${params.id}/strategy`).then(setStrategy).catch(() => setStrategy(null));
    request<StrategyDecision>(`/api/projects/${params.id}/strategy/decision`).then(setDecision).catch(() => setDecision(null));
  };
  useEffect(() => { load().catch(error => setError(error.message)); }, [params.id]);
  useEffect(() => {
    const latest = concepts[0];
    if (!latest) { setBoard(null); setTerritoryId(""); return; }
    const next = copy(latest.content); const first = territories(next)[0];
    setBoard(next); setTerritoryId(String(next.selected_territory_id || first?.id || ""));
  }, [concepts]);
  useEffect(() => {
    const selected = concepts.find(concept => concept.status === "selected");
    const next = selected ? plans.find(plan => plan.concept_id === selected.id) : undefined;
    setPlanBoard(next ? copy(next.content) : null);
  }, [concepts, plans]);

  const ready = strategy?.approval_status === "approved" && !!decision;
  const selectedConcept = concepts.find(concept => concept.status === "selected");
  const selectedPlan = selectedConcept ? plans.find(plan => plan.concept_id === selectedConcept.id) : undefined;
  const current = territories(board).find(item => item.id === territoryId) || territories(board)[0];

  async function generate() {
    setBusy(true); setError(""); setSaved("");
    try { const concept = await request<CreativeConcept>(`/api/projects/${params.id}/creative-concepts/generate`, { method: "POST", body: JSON.stringify({ instruction }) }); setConcepts(current => [concept, ...current]); setSaved("OLIVA Creative Director propuso tres plataformas editables. Elegí una, corregila si hace falta y confirmala."); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  function updateTerritory(field: keyof CreativeTerritory, value: string) {
    if (!board || !current) return;
    const next = copy(board); next.territorios = territories(next).map(item => item.id === current.id ? { ...item, [field]: field === "medios" ? value.split(",").map(item => item.trim()).filter(Boolean) : value } : item); setBoard(next);
  }
  async function saveBoard(status: "draft" | "selected") {
    if (!board || !concepts[0]) return;
    setBusy(true); setError(""); setSaved("");
    try {
      const content = { ...board, selected_territory_id: territoryId };
      const updated = await request<CreativeConcept>(`/api/projects/${params.id}/creative-concepts/${concepts[0].id}`, { method: "PATCH", body: JSON.stringify({ content, status }) });
      setConcepts(current => [updated, ...current.filter(item => item.id !== updated.id)]); setSaved(status === "selected" ? "Plataforma elegida y guardada. Ya podés cargar materiales para revisión." : "Cambios creativos guardados. Podés seguir editando o elegir esta plataforma."); await load();
    } catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  function updatePlanItem(group: "piezas_creativas" | "soportes_de_medios", id: string, field: string, value: string) {
    if (!planBoard) return;
    const next = copy(planBoard); next[group] = planItems(next, group).map(item => item.id === id ? { ...item, [field]: value } : item); setPlanBoard(next);
  }
  function updateProductionItem(id: string, field: string, value: string) {
    if (!planBoard) return;
    const next = copy(planBoard); next.propuestas_de_produccion = productionItems(next).map(item => item.id === id ? { ...item, [field]: value } : item); setPlanBoard(next);
  }
  async function savePlan(status: "draft" | "approved") {
    if (!planBoard || !selectedPlan) return;
    setBusy(true); setError(""); setSaved("");
    try {
      const updated = await request<CreativeProductionPlan>(`/api/projects/${params.id}/creative-plans/${selectedPlan.id}`, { method: "PATCH", body: JSON.stringify({ content: planBoard, status }) });
      setPlans(current => [updated, ...current.filter(item => item.id !== updated.id)]); setSaved(status === "approved" ? "Plan aprobado: OLIVA ya preparó propuestas de ejecución y guiones editables para pasar a producción." : "Plan de campaña guardado. Podés corregir piezas, soportes y cobertura antes de aprobarlo."); await load();
    } catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try { await request(`/api/projects/${params.id}/creative`, { method: "POST", body: new FormData(event.currentTarget) }); event.currentTarget.reset(); setSaved("Material cargado y revisado contra la plataforma creativa elegida."); await load(); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }

  if (!project) return <main className="shell"><Nav/><p>{error || "Cargando…"}</p></main>;
  return <main className="shell"><Nav/>
    <div className="pagehead"><div><p className="eyebrow">Dirección creativa</p><h1>{project.name}</h1></div><div className="page-actions"><Link className="btn ghost" href={`/projects/${project.id}/result`}>← Estrategia</Link><Link className="btn ghost" href={`/projects/${project.id}`}>Proyecto</Link></div></div>
    {!ready && <div className="brief-alert"><strong>Primero confirmá la estrategia y la ruta de trabajo</strong><p>El agente creativo sólo propone campañas cuando tiene una decisión estratégica concreta a la que responder.</p></div>}
    {decision && <section className="brief-alert"><strong>Base aprobada · {decision.route_key.replace("_", " ")}</strong><p>{decision.rationale}</p><small>Plan: {decision.launch_plan}</small></section>}
    <section className="card creative-director-intro"><div><p className="eyebrow">OLIVA Creative Director</p><h2>De estrategia a plataformas de campaña</h2><p className="muted">Propone tres caminos distintos, controla estrategia, marca y propiedad, y te deja editar la plataforma elegida antes de producir materiales.</p></div><div className="field"><label>Foco adicional para el agente (opcional)</label><textarea value={instruction} onChange={event => setInstruction(event.target.value)} placeholder="Ej. Priorizar punto de venta, radio regional, lanzamiento de bajo presupuesto…"/><button type="button" className="btn lime" disabled={!ready || busy} onClick={generate}>{busy ? "Proponiendo campañas…" : "Proponer 3 campañas →"}</button></div></section>
    {saved && <p className="success creative-success" role="status">{saved}</p>}{error && <p className="error">{error}</p>}
    {board && current ? <section className="creative-workbench"><aside className="card creative-territories"><p className="eyebrow">Plataformas</p><h2>Elegí un camino</h2>{territories(board).map(item => <button type="button" className={`territory-choice ${item.id === territoryId ? "selected" : ""}`} key={item.id} onClick={() => setTerritoryId(item.id)}><strong>{item.nombre}</strong><span>{item.tipo_de_campana}</span></button>)}<div className="creative-actions"><button className="btn ghost" disabled={busy} onClick={() => saveBoard("draft")}>Guardar correcciones</button><button className="btn lime" disabled={busy} onClick={() => saveBoard("selected")}>Elegir esta plataforma →</button></div></aside>
      <div className="card creative-editor"><p className="eyebrow">Plataforma editable</p><div className="field"><label>Nombre de campaña</label><input value={current.nombre} onChange={event => updateTerritory("nombre", event.target.value)}/></div><div className="field"><label>Tensión u observación</label><textarea value={current.tension} onChange={event => updateTerritory("tension", event.target.value)}/></div><div className="field"><label>Idea central</label><textarea value={current.idea_central} onChange={event => updateTerritory("idea_central", event.target.value)}/></div><div className="field two"><div><label>Tipo de campaña</label><input value={current.tipo_de_campana} onChange={event => updateTerritory("tipo_de_campana", event.target.value)}/></div><div><label>Tono</label><input value={current.tono} onChange={event => updateTerritory("tono", event.target.value)}/></div></div><div className="field"><label>Estilo / dirección de arte</label><textarea value={current.estilo} onChange={event => updateTerritory("estilo", event.target.value)}/></div><div className="field"><label>Medios (separados por coma)</label><input value={(current.medios || []).join(", ")} onChange={event => updateTerritory("medios", event.target.value)}/></div><div className="creative-controls"><div><strong>Rol de marca</strong><p>{current.rol_de_marca}</p></div><div><strong>Prueba de propiedad</strong><p>{current.propiedad}</p></div><div><strong>Riesgos a evitar</strong><p>{current.riesgos_y_cliches}</p></div><div><strong>Control del director</strong><p>{current.control}</p></div></div></div>
    </section> : <div className="empty"><h3>Todavía no hay plataformas creativas</h3><p className="muted">El agente propone las campañas después de que la estrategia esté confirmada.</p></div>}
    {selectedConcept && planBoard ? <section className="card campaign-planner"><div className="campaign-plan-head"><div><p className="eyebrow">Plan de campaña y medios</p><h2>De la plataforma a los materiales y soportes</h2><p className="muted">Esta propuesta usa el territorio definido en el brief. Editá cada elemento antes de aprobar el plan y pasar a producción.</p></div><span className="status">{selectedPlan?.status === "approved" ? "plan aprobado" : "plan editable"}</span></div>
      <div className="media-assumption"><strong>Zona: {String((planBoard.base_aprobada as Record<string, unknown>)?.territorio || project.territory || "por definir")}</strong><p>{String((planBoard.criterio_de_medios as Record<string, unknown>)?.lectura_local || "Definí el territorio y los soportes prioritarios.")}</p><small>{String((planBoard.criterio_de_medios as Record<string, unknown>)?.estado || "Propuesta a validar con fuentes de medios.")}</small></div>
      <div className="campaign-plan-grid"><div><h3>Materiales creativos sugeridos</h3>{planItems(planBoard, "piezas_creativas").map(item => <article className="plan-item" key={item.id}><div className="field"><label>Material</label><input value={item.nombre || ""} onChange={event => updatePlanItem("piezas_creativas", item.id, "nombre", event.target.value)}/></div><div className="field two"><div><label>Formato</label><input value={item.formato || ""} onChange={event => updatePlanItem("piezas_creativas", item.id, "formato", event.target.value)}/></div><div><label>Prioridad</label><input value={item.prioridad || ""} onChange={event => updatePlanItem("piezas_creativas", item.id, "prioridad", event.target.value)}/></div></div><div className="field"><label>Función dentro de la campaña</label><textarea value={item.funcion || ""} onChange={event => updatePlanItem("piezas_creativas", item.id, "funcion", event.target.value)}/></div><small>{item.momento}</small></article>)}</div>
        <div><h3>Soportes y rol de medios</h3>{planItems(planBoard, "soportes_de_medios").map(item => <article className="plan-item" key={item.id}><div className="field"><label>Soporte</label><input value={item.soporte || ""} onChange={event => updatePlanItem("soportes_de_medios", item.id, "soporte", event.target.value)}/></div><div className="field"><label>Rol específico</label><textarea value={item.rol || ""} onChange={event => updatePlanItem("soportes_de_medios", item.id, "rol", event.target.value)}/></div><div className="field two"><div><label>Cobertura</label><input value={item.cobertura || ""} onChange={event => updatePlanItem("soportes_de_medios", item.id, "cobertura", event.target.value)}/></div><div><label>Indicador</label><input value={item.indicador || ""} onChange={event => updatePlanItem("soportes_de_medios", item.id, "indicador", event.target.value)}/></div></div></article>)}</div></div>
      <div className="campaign-phases"><h3>Fases de trabajo</h3>{Array.isArray(planBoard.fases) && (planBoard.fases as Record<string, string>[]).map(phase => <div key={phase.fase}><strong>{phase.fase}</strong><p>{phase.objetivo}</p><small>{phase.acciones}</small></div>)}</div><div className="creative-actions campaign-actions"><button className="btn ghost" disabled={busy} onClick={() => savePlan("draft")}>Guardar correcciones</button><button className="btn lime" disabled={busy} onClick={() => savePlan("approved")}>{selectedPlan?.status === "approved" ? "Confirmar plan de producción →" : "Aprobar plan y generar guiones →"}</button></div>
    </section> : selectedConcept ? <div className="brief-alert"><strong>Preparando el plan de campaña…</strong><p>Recargá esta pantalla si no aparece en unos segundos.</p></div> : null}
    {selectedPlan?.status === "approved" && planBoard && productionItems(planBoard).length > 0 ? <section className="card production-desk"><div className="campaign-plan-head"><div><p className="eyebrow">Mesa de producción</p><h2>Propuestas de campaña y guiones de trabajo</h2><p className="muted">Parten de la plataforma y el plan aprobados. Son editables: corregí antes de encargar o producir materiales.</p></div><span className="status">listo para producir</span></div>
      <div className="production-proposal"><strong>{String((planBoard.propuesta_de_campana as Record<string, unknown>)?.nombre || "Campaña en desarrollo")}</strong><p>{String((planBoard.propuesta_de_campana as Record<string, unknown>)?.promesa_de_trabajo || "Definí la propuesta de campaña.")}</p><small>{String((planBoard.propuesta_de_campana as Record<string, unknown>)?.tono_y_sistema || "")}</small></div>
      <div className="production-list">{productionItems(planBoard).map(item => <article className="production-item" key={item.id}><div className="field two"><div><label>Pieza</label><input value={item.pieza || ""} onChange={event => updateProductionItem(item.id, "pieza", event.target.value)}/></div><div><label>Medio / formato</label><input value={item.duracion_formato || item.medio || ""} onChange={event => updateProductionItem(item.id, "duracion_formato", event.target.value)}/></div></div><div className="field"><label>Propuesta de ejecución</label><textarea value={item.propuesta || ""} onChange={event => updateProductionItem(item.id, "propuesta", event.target.value)}/></div><div className="field"><label>Guion sugerido</label><textarea className="script-area" value={item.guion || ""} onChange={event => updateProductionItem(item.id, "guion", event.target.value)}/></div><div className="field"><label>Requisitos de producción</label><textarea value={item.produccion || ""} onChange={event => updateProductionItem(item.id, "produccion", event.target.value)}/></div><small><strong>Control final:</strong> {item.control}</small></article>)}</div>
      {Array.isArray(planBoard.faltantes_de_produccion) && <div className="production-missing"><strong>Antes de producir, confirmar</strong><ul>{(planBoard.faltantes_de_produccion as string[]).map(item => <li key={item}>{item}</li>)}</ul></div>}<div className="creative-actions campaign-actions"><button className="btn lime" disabled={busy} onClick={() => savePlan("approved")}>Guardar ajustes de producción</button></div>
    </section> : selectedPlan?.status === "approved" ? <div className="brief-alert"><strong>Preparando guiones de producción…</strong><p>Recargá esta pantalla si no aparecen en unos segundos.</p></div> : null}
    <section className="creative-layout creative-materials"><form className="card" onSubmit={submit}><p className="eyebrow">Materiales</p><h2>Subir una pieza para revisión</h2><p className="muted">{selectedConcept ? "La revisión se hará contra la plataforma elegida, la ruta aprobada y los controles de marca y propiedad." : "Primero elegí y guardá una plataforma creativa. Así ninguna pieza se evalúa contra un diagnóstico genérico."}</p><div className="field"><label>Nombre</label><input name="name" required/></div><div className="field"><label>Medio o formato</label><input name="medium" placeholder="Radio 30s, historia vertical, cartel, gráfica…"/></div><div className="field"><label>Fundamento creativo</label><textarea name="rationale" placeholder="Explicá cómo la pieza desarrolla la plataforma elegida y qué comportamiento busca provocar."/></div><div className="field"><label>Archivo</label><input name="file" type="file" required accept="image/*,.pdf,.txt,.md"/></div><button className="btn lime" disabled={!selectedConcept || busy}>{busy ? "Evaluando…" : "Cargar y revisar material"}</button></form>
      <div>{reviews.length === 0 ? <div className="empty"><h3>No hay materiales revisados</h3><p className="muted">Después de elegir una plataforma, subí bocetos, guiones o piezas para recibir una devolución publicitaria concreta.</p></div> : <div className="library-list">{reviews.map(review => <article className="card" key={review.id}><div className="review-head"><div><span className="status">{review.verdict.replace("_", " ")}</span><h2>{review.name}</h2></div><small>{review.medium || review.filename}</small></div><p className="creative-evaluation">{review.evaluation}</p><div className="score-grid">{Object.entries(review.scores).map(([key, score]) => <div className="score" key={key}><span>{labels[key] || key}</span><strong>{score}/5</strong><i><b style={{ width: `${score * 20}%` }}/></i></div>)}</div></article>)}</div>}</div>
    </section>
  </main>;
}
