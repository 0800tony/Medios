"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { AgentRun, BrandAsset, CampaignPlanItem, CreativeConcept, CreativeNote, CreativeProductionPlan, CreativeReview, CreativeTerritory, CreativeVisual, Dossier, ProductionPackage, Project, StrategyDecision, request, requestBlob } from "@/lib/api";

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
function agentItems(plan: Record<string, unknown> | null): CampaignPlanItem[] {
  return Array.isArray(plan?.mesa_de_agentes) ? plan!.mesa_de_agentes as CampaignPlanItem[] : [];
}
function visualDrafts(plan: Record<string, unknown> | null): CampaignPlanItem[] {
  return Array.isArray(plan?.bocetos_visuales) ? plan!.bocetos_visuales as CampaignPlanItem[] : [];
}

export default function Creative({ params }: { params: { id: string } }) {
  const [project, setProject] = useState<Project | null>(null);
  const [strategy, setStrategy] = useState<Dossier | null>(null);
  const [decision, setDecision] = useState<StrategyDecision | null>(null);
  const [concepts, setConcepts] = useState<CreativeConcept[]>([]);
  const [plans, setPlans] = useState<CreativeProductionPlan[]>([]);
  const [brandAssets, setBrandAssets] = useState<BrandAsset[]>([]);
  const [visuals, setVisuals] = useState<CreativeVisual[]>([]);
  const [visualUrls, setVisualUrls] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState<CreativeNote[]>([]);
  const [tableRuns, setTableRuns] = useState<AgentRun[]>([]);
  const [productionPackage, setProductionPackage] = useState<ProductionPackage | null>(null);
  const [planBoard, setPlanBoard] = useState<Record<string, unknown> | null>(null);
  const [reviews, setReviews] = useState<CreativeReview[]>([]);
  const [board, setBoard] = useState<Record<string, unknown> | null>(null);
  const [territoryId, setTerritoryId] = useState("");
  const [instruction, setInstruction] = useState("");
  const [newPiece, setNewPiece] = useState("");
  const [newPieceFormat, setNewPieceFormat] = useState("Pieza a definir");
  const [visualFocus, setVisualFocus] = useState("");
  const [visualStyle, setVisualStyle] = useState("Editorial OLIVA: papel cálido, verde profundo, lima y dirección de arte contemporánea.");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    const [projectData, conceptData, reviewData, planData] = await Promise.all([
      request<Project>(`/api/projects/${params.id}`), request<CreativeConcept[]>(`/api/projects/${params.id}/creative-concepts`), request<CreativeReview[]>(`/api/projects/${params.id}/creative`), request<CreativeProductionPlan[]>(`/api/projects/${params.id}/creative-plans`),
    ]);
    const [assets, visualData, noteData, tableData] = await Promise.all([request<BrandAsset[]>(`/api/clients/${projectData.client_id}/brand-assets`), request<CreativeVisual[]>(`/api/projects/${params.id}/creative-visuals`), request<CreativeNote[]>(`/api/projects/${params.id}/creative-notes`), request<AgentRun[]>(`/api/projects/${params.id}/creative-table`)]);
    setProject(projectData); setConcepts(conceptData); setReviews(reviewData); setPlans(planData); setBrandAssets(assets); setVisuals(visualData); setNotes(noteData); setTableRuns(tableData);
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
  useEffect(() => {
    let active = true; const urls: string[] = [];
    Promise.all(visuals.filter(item => item.status === "generated").map(async item => [item.id, URL.createObjectURL(await requestBlob(`/api/projects/${params.id}/creative-visuals/${item.id}/media`))] as const)).then(items => { if (active) { const next = Object.fromEntries(items); Object.values(next).forEach(url => urls.push(url)); setVisualUrls(next); } });
    return () => { active = false; urls.forEach(url => URL.revokeObjectURL(url)); };
  }, [visuals, params.id]);

  const ready = strategy?.approval_status === "approved" && !!decision;
  const selectedConcept = concepts.find(concept => concept.status === "selected");
  const selectedPlan = selectedConcept ? plans.find(plan => plan.concept_id === selectedConcept.id) : undefined;
  const creativeCriteria = (planBoard?.criterio_creativo || {}) as Record<string, unknown>;
  const current = territories(board).find(item => item.id === territoryId) || territories(board)[0];
  const latestTable = tableRuns[0]?.output || {};
  const tableInterventions = Array.isArray(latestTable.intervenciones) ? latestTable.intervenciones as Record<string, string>[] : [];
  const tableClosing = (latestTable.cierre || {}) as Record<string, string>;

  async function generate() {
    setBusy(true); setError(""); setSaved("");
    try { const concept = await request<CreativeConcept>(`/api/projects/${params.id}/creative-concepts/generate`, { method: "POST", body: JSON.stringify({ instruction }) }); setConcepts(current => [concept, ...current]); setSaved("OLIVA Creative Director propuso tres plataformas editables. Elegí una, corregila si hace falta y confirmala."); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  async function uploadBrand(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!project) return; const form = event.currentTarget; setBusy(true); setError(""); setSaved("");
    try { const asset = await request<BrandAsset>(`/api/clients/${project.client_id}/brand-assets`, { method: "POST", body: new FormData(form) }); setBrandAssets(current => [asset, ...current]); form.reset(); setSaved("Logo y paleta guardados en la identidad del cliente. OLIVA los tendrá disponibles para los próximos bocetos."); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  async function generateVisual(title = "Boceto OLIVA de campaña", focus = visualFocus) {
    if (!selectedPlan) return; setBusy(true); setError(""); setSaved("");
    try { const draft = await request<CreativeVisual>(`/api/projects/${params.id}/creative-plans/${selectedPlan.id}/visuals/generate`, { method: "POST", body: JSON.stringify({ title, focus: focus || "Desarrollar la pieza madre y sus aplicaciones de campaña con la identidad disponible.", visual_style: visualStyle }) }); setVisuals(current => [draft, ...current]); setVisualFocus(""); setSaved("Boceto generado desde la campaña y guardado en el expediente creativo."); }
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
      const targetStatus = status === "draft" && concepts[0].status === "selected" ? "selected" : status;
      const updated = await request<CreativeConcept>(`/api/projects/${params.id}/creative-concepts/${concepts[0].id}`, { method: "PATCH", body: JSON.stringify({ content, status: targetStatus }) });
      setConcepts(current => [updated, ...current.filter(item => item.id !== updated.id)]); setSaved(targetStatus === "selected" ? "Cambios guardados. La estrategia y el plan vigente se mantienen; no se recalcularon." : "Cambios creativos guardados. Podés seguir editando o elegir esta plataforma."); await load();
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
  function addCreativePiece() {
    if (!planBoard || !newPiece.trim()) return;
    const next = copy(planBoard); const item = { id: `idea_${Date.now()}`, pieza: "Idea del equipo", medio: newPieceFormat || "Pieza a definir", duracion_formato: newPieceFormat || "Pieza a definir", objetivo: "Definir el comportamiento que esta idea debe provocar.", propuesta: newPiece.trim(), guion: "Idea en desarrollo: transformá esta observación en una escena, un giro, un cierre y una acción concreta.", produccion: "Definir formato, activos de marca y requisitos antes de producir.", control: "¿Esta idea mantiene la plataforma aprobada y aporta algo que el guion inicial no cubría?" };
    next.propuestas_de_produccion = [...productionItems(next), item]; setPlanBoard(next); setNewPiece(""); setSaved("Idea agregada al tablero. Guardá los ajustes cuando quieras incorporarla al plan.");
  }
  function removeCreativePiece(id: string) {
    if (!planBoard) return;
    const next = copy(planBoard); next.propuestas_de_produccion = productionItems(next).filter(item => item.id !== id); setPlanBoard(next); setSaved("Pieza retirada del borrador. Guardá los ajustes para confirmar el cambio.");
  }
  async function savePlan(status: "draft" | "approved") {
    if (!planBoard || !selectedPlan) return;
    setBusy(true); setError(""); setSaved("");
    try {
      const targetStatus = status === "draft" && selectedPlan.status === "approved" ? "approved" : status;
      const updated = await request<CreativeProductionPlan>(`/api/projects/${params.id}/creative-plans/${selectedPlan.id}`, { method: "PATCH", body: JSON.stringify({ content: planBoard, status: targetStatus }) });
      setPlans(current => [updated, ...current.filter(item => item.id !== updated.id)]); setSaved(targetStatus === "approved" ? (selectedPlan.status === "approved" ? "Cambios guardados. La estrategia y los guiones no se recalcularon." : "Plan aprobado: OLIVA preparó las propuestas de ejecución para pasar a producción.") : "Plan de campaña guardado. Podés corregir piezas, soportes y cobertura antes de aprobarlo."); await load();
    } catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; setBusy(true); setError("");
    try { await request(`/api/projects/${params.id}/creative`, { method: "POST", body: new FormData(form) }); form.reset(); setSaved("Material cargado y revisado contra la plataforma creativa elegida."); await load(); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  async function addNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; setBusy(true); setError("");
    try { const note = await request<CreativeNote>(`/api/projects/${params.id}/creative-notes`, { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))) }); setNotes(current => [note, ...current]); form.reset(); setSaved("Aporte guardado en la mesa. No recalculó la estrategia ni los guiones."); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  async function updateNote(note: CreativeNote, status: "applied" | "discarded") {
    setBusy(true); try { const updated = await request<CreativeNote>(`/api/projects/${params.id}/creative-notes/${note.id}`, { method: "PATCH", body: JSON.stringify({ status }) }); setNotes(current => current.map(item => item.id === updated.id ? updated : item)); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  async function runTable(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; setBusy(true); setError("");
    try { const run = await request<AgentRun>(`/api/projects/${params.id}/creative-table`, { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))) }); setTableRuns(current => [run, ...current]); form.reset(); setSaved("La Mesa OLIVA dejó sus objeciones y aportes. La decisión queda en manos del equipo."); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  async function loadProductionPackage() {
    if (!selectedPlan) return; setBusy(true); setError("");
    try { setProductionPackage(await request<ProductionPackage>(`/api/projects/${params.id}/creative-plans/${selectedPlan.id}/production-package`)); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  async function saveOutcome(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; setBusy(true); setError("");
    try { const values = Object.fromEntries(new FormData(form)); await request("/api/learning", { method: "POST", body: JSON.stringify({ ...values, project_id: params.id, client_id: project?.client_id, source_type: "resultado_de_campana", confidence: "por_validar", tags: "resultado, creatividad" }) }); form.reset(); setSaved("Resultado registrado. Pasará por Aprobaciones antes de alimentar el aprendizaje reutilizable de OLIVA."); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }

  if (!project) return <main className="shell"><Nav/><p>{error || "Cargando…"}</p></main>;
  return <main className="shell"><Nav/>
    <div className="pagehead"><div><p className="eyebrow">Dirección creativa</p><h1>{project.name}</h1></div><div className="page-actions"><Link className="btn ghost" href={`/projects/${project.id}/result`}>← Estrategia</Link><Link className="btn ghost" href={`/projects/${project.id}`}>Proyecto</Link></div></div>
    {!ready && <div className="brief-alert"><strong>Primero confirmá la estrategia y la ruta de trabajo</strong><p>El agente creativo sólo propone campañas cuando tiene una decisión estratégica concreta a la que responder.</p></div>}
    {decision && <section className="brief-alert"><strong>Base aprobada · {decision.route_key.replace("_", " ")}</strong><p>{decision.rationale}</p><small>Plan: {decision.launch_plan}</small></section>}
    <section className="card creative-director-intro"><div><p className="eyebrow">OLIVA Creative Director</p><h2>De estrategia a plataformas de campaña</h2><p className="muted">Propone tres caminos distintos, controla estrategia, marca y propiedad, y te deja editar la plataforma elegida antes de producir materiales.</p></div><div className="field"><label>Foco adicional para el agente (opcional)</label><textarea value={instruction} onChange={event => setInstruction(event.target.value)} placeholder="Ej. Priorizar punto de venta, radio regional, lanzamiento de bajo presupuesto…"/><button type="button" className="btn lime" disabled={!ready || busy} onClick={generate}>{busy ? "Proponiendo campañas…" : "Proponer 3 campañas →"}</button></div></section>
    <section className="card brand-kit"><div><p className="eyebrow">Identidad de marca</p><h2>Logo y paleta para los borradores</h2><p className="muted">Subí el logo real una vez. Queda guardado para este cliente y se incorpora como referencia en los próximos bocetos y controles de marca.</p>{brandAssets.length ? <div className="brand-asset-list">{brandAssets.map(asset => <span key={asset.id}><strong>{asset.label}</strong> · {asset.filename}{asset.palette ? ` · ${asset.palette}` : ""}</span>)}</div> : <p className="muted">Aún no hay un logo cargado.</p>}</div><form onSubmit={uploadBrand}><div className="field"><label>Logo (PNG, JPG o WEBP)</label><input required name="file" type="file" accept="image/png,image/jpeg,image/webp"/></div><div className="field"><label>Paleta institucional (opcional)</label><input name="palette" placeholder="#153F35, #D9FF43, #F4F1E9"/></div><button className="btn ghost" disabled={busy}>{busy ? "Guardando…" : "Guardar identidad"}</button></form></section>
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
    {selectedPlan?.status === "approved" && planBoard && productionItems(planBoard).length > 0 ? <section className="card production-desk"><div className="campaign-plan-head"><div><p className="eyebrow">Dirección creativa y producción</p><h2>La idea primero. Los guiones, después.</h2><p className="muted">Cada pieza parte de una tensión, un giro y una frase rectora. Abrí sólo el guion que querés trabajar.</p></div><span className="status">listo para producir</span></div>
      <div className="production-proposal"><strong>{String((planBoard.propuesta_de_campana as Record<string, unknown>)?.nombre || "Campaña en desarrollo")}</strong><p>{String((planBoard.propuesta_de_campana as Record<string, unknown>)?.promesa_de_trabajo || "Definí la propuesta de campaña.")}</p><small>{String((planBoard.propuesta_de_campana as Record<string, unknown>)?.tono_y_sistema || "")}</small></div>
      <details className="creative-criteria"><summary>Criterio creativo aplicado por OLIVA</summary><p>{String(creativeCriteria.aclaracion || "La idea se evalúa por estrategia, marca, propiedad y capacidad de vivir en distintos medios.")}</p>{Array.isArray(creativeCriteria.principios) && <ul>{(creativeCriteria.principios as string[]).map(item => <li key={item}>{item}</li>)}</ul>}<p className="creative-references">{String(creativeCriteria.referencias || "")}</p></details>
      <nav className="creative-stage-nav" aria-label="Navegación de producción"><a href="#guiones">Guiones</a><a href="#mesa">Mesa OLIVA</a><a href="#bocetos">Estudio visual</a><a href="#produccion">Producción</a><a href="#materiales">Materiales</a></nav>
      <div className="team-idea-form"><div><strong>Sumá una idea o una pieza nueva</strong><p>Es un borrador del equipo: no recalcula la estrategia ni reemplaza los guiones existentes.</p></div><div className="field"><label>Formato</label><input value={newPieceFormat} onChange={event => setNewPieceFormat(event.target.value)} placeholder="Ej. activación, gráfica, radio, acción digital"/></div><div className="field"><label>Idea</label><textarea value={newPiece} onChange={event => setNewPiece(event.target.value)} placeholder="Escribí una observación, escena, titular, acción o pieza que quieras explorar…"/></div><button type="button" className="btn ghost" onClick={addCreativePiece} disabled={!newPiece.trim()}>Agregar al tablero</button></div>
      <div id="guiones" className="production-list">{productionItems(planBoard).map(item => <article className="production-item" key={item.id}><div className="production-item-head"><div><span className="status">{item.duracion_formato || item.medio || "formato"}</span><h3>{item.pieza || "Pieza de campaña"}</h3></div><p>{item.propuesta || "Definí la propuesta de ejecución."}</p></div><details><summary>Ver y editar guion de trabajo</summary><div className="production-item-editor"><div className="field two"><div><label>Pieza</label><input value={item.pieza || ""} onChange={event => updateProductionItem(item.id, "pieza", event.target.value)}/></div><div><label>Medio / formato</label><input value={item.duracion_formato || item.medio || ""} onChange={event => updateProductionItem(item.id, "duracion_formato", event.target.value)}/></div></div><div className="field"><label>Objetivo</label><textarea value={item.objetivo || ""} onChange={event => updateProductionItem(item.id, "objetivo", event.target.value)}/></div><div className="field"><label>Propuesta de ejecución</label><textarea value={item.propuesta || ""} onChange={event => updateProductionItem(item.id, "propuesta", event.target.value)}/></div><div className="field"><label>Guion técnico sugerido</label><textarea className="script-area" value={item.guion || ""} onChange={event => updateProductionItem(item.id, "guion", event.target.value)}/></div><div className="field"><label>Requisitos de producción</label><textarea value={item.produccion || ""} onChange={event => updateProductionItem(item.id, "produccion", event.target.value)}/></div><small><strong>Control final:</strong> {item.control}</small><button type="button" className="text-action danger-link" onClick={() => removeCreativePiece(item.id)}>Quitar esta pieza</button></div></details></article>)}</div>
      <div id="mesa" className="agent-board creative-table"><div><p className="eyebrow">Mesa Creativa Real</p><h3>Una conversación de trabajo, no una caja negra</h3><p className="muted">Sumá ideas, objeciones o referencias. Podés pedir una ronda a Estrategia, Dirección Creativa, Dirección de Arte y Producción; sus aportes no modifican por sí solos lo aprobado.</p></div><form className="table-question" onSubmit={runTable}><div className="field"><label>Pregunta para la mesa</label><textarea name="question" required placeholder="Ej. ¿Cómo convertimos esta idea en una activación que la gente quiera contar?"/></div><button className="btn lime" disabled={busy}>{busy ? "Conversando…" : "Convocar mesa →"}</button></form>{tableInterventions.length > 0 && <div className="table-interventions">{tableInterventions.map(item => <article key={item.rol}><span>{item.rol}</span><h4>{item.acuerdo}</h4><p><strong>Objeción:</strong> {item.objecion}</p><p><strong>Aporte:</strong> {item.aporte_concreto}</p><small>{item.prueba_de_propiedad}</small></article>)}</div>}{Object.keys(tableClosing).length > 0 && <div className="table-closing"><strong>Decisión de la mesa</strong>{Object.entries(tableClosing).map(([key, value]) => <p key={key}><b>{key.replace("_", " ")}:</b> {value}</p>)}</div>}<div className="agent-grid">{agentItems(planBoard).map(item => <article key={item.agente}><span>{item.rol}</span><strong>{item.agente}</strong><p>{item.aporte}</p><small>{item.control}</small></article>)}</div><form className="team-idea-form compact" onSubmit={addNote}><div><strong>Creatividad colaborativa</strong><p>Registrá una idea, devolución, decisión o referencia del equipo.</p></div><div className="field"><label>Tipo</label><select name="kind"><option value="idea">Idea</option><option value="feedback">Devolución</option><option value="decision">Decisión</option><option value="reference">Referencia</option></select></div><div className="field"><label>Aporte</label><textarea required name="content" placeholder="Escena, titular, referencia, ajuste o decisión…"/></div><input type="hidden" name="author" value="Equipo OLIVA"/><button className="btn ghost" disabled={busy}>Guardar aporte</button></form>{notes.length > 0 && <div className="creative-notes">{notes.slice(0, 8).map(note => <article key={note.id}><span className="status">{note.kind} · {note.status}</span><p>{note.content}</p>{note.status === "open" && <div className="row-actions"><button disabled={busy} onClick={() => updateNote(note, "applied")}>Incorporar</button><button className="danger-link" disabled={busy} onClick={() => updateNote(note, "discarded")}>Descartar</button></div>}</article>)}</div>}</div>
      <div id="bocetos" className="visual-board"><div className="visual-head"><div><p className="eyebrow">Estudio Creativo Visual</p><h3>Generar una imagen real desde una decisión concreta</h3><p className="muted">El estudio usa la plataforma aprobada, el foco de la pieza, la identidad cargada y una dirección de arte editable. Si la cuenta no tiene acceso a imágenes, OLIVA lo informa: nunca muestra una plantilla como si fuera resultado.</p></div></div><div className="visual-request"><div className="field"><label>Qué querés visualizar</label><input value={visualFocus} onChange={event => setVisualFocus(event.target.value)} placeholder="Ej. pieza madre en un kiosco, activación de recreo, cartel de ruta…"/></div><div className="field"><label>Dirección de arte</label><input value={visualStyle} onChange={event => setVisualStyle(event.target.value)} placeholder="Luz, encuadre, materialidad, tono y composición"/></div><button className="btn lime" disabled={busy} onClick={() => generateVisual()}>{busy ? "Generando…" : "Generar imagen de boceto →"}</button>{error && <p className="error visual-error" role="alert">{error}</p>}</div><div className="visual-grid">{visuals.map(item => <article key={item.id} className="visual-draft">{visualUrls[item.id] ? <img src={visualUrls[item.id]} alt={`Boceto generado: ${item.title}`} /> : <div className="visual-prompt"><span>{item.status}</span><strong>{item.title}</strong></div>}<div><span className="status">imagen generada por OLIVA</span><h4>{item.title}</h4><details><summary>Ver dirección usada</summary><p>{item.prompt}</p></details></div></article>)}{visualDrafts(planBoard).map(item => <article key={item.id} className="visual-draft"><div className="visual-prompt"><span>Dirección pendiente</span><strong>{item.pieza}</strong></div><div><span className="status">{item.estado}</span><h4>{item.titulo}</h4><p>{item.direccion}</p><button type="button" className="text-action" disabled={busy} onClick={() => generateVisual(String(item.titulo || "Boceto de campaña"), String(item.prompt_de_produccion || item.direccion || ""))}>Generar esta imagen →</button></div></article>)}</div></div>
      {Array.isArray(planBoard.faltantes_de_produccion) && <div className="production-missing"><strong>Antes de producir, confirmar</strong><ul>{(planBoard.faltantes_de_produccion as string[]).map(item => <li key={item}>{item}</li>)}</ul></div>}<div id="produccion" className="production-package"><div><p className="eyebrow">Producción Profesional</p><h3>Paquete de entrega para el equipo</h3><p className="muted">Convierte el plan aprobado en una lista de piezas, guiones, activos, confirmaciones y próximos responsables. No bloquea las ediciones del equipo.</p></div><button className="btn ghost" disabled={busy} onClick={loadProductionPackage}>Preparar paquete →</button>{productionPackage && <div className="package-grid"><article><strong>Campaña</strong><p>{productionPackage.campaign}</p><small>{productionPackage.strategy}</small></article><article><strong>Activos disponibles</strong><ul>{productionPackage.assets.map(item => <li key={item}>{item}</li>)}</ul></article><article><strong>Confirmaciones</strong><ul>{productionPackage.confirmations.map(item => <li key={item}>{item}</li>)}</ul></article><article><strong>Entrega</strong><ul>{productionPackage.handoff.map(item => <li key={item}>{item}</li>)}</ul></article></div>}<form className="outcome-form" onSubmit={saveOutcome}><div><strong>Aprendizaje de resultados</strong><p>Al cerrar una prueba o campaña, registrá qué pasó, qué evidencia lo respalda y cuál es su límite. No se convierte en regla automática.</p></div><div className="field"><label>Resultado o aprendizaje</label><input required name="title" placeholder="Ej. La exhibición resolvió la elección en kioscos"/></div><div className="field"><label>Qué ocurrió y con qué evidencia</label><textarea required name="content" placeholder="Indicá período, plaza, indicador, resultado observado y límites de la lectura."/></div><button className="btn ghost" disabled={busy}>Enviar a validación</button></form></div><div className="creative-actions campaign-actions"><button className="btn lime" disabled={busy} onClick={() => savePlan("approved")}>Guardar ajustes de producción</button></div>
    </section> : selectedPlan?.status === "approved" ? <div className="brief-alert"><strong>Preparando guiones de producción…</strong><p>Recargá esta pantalla si no aparecen en unos segundos.</p></div> : null}
    <section id="materiales" className="creative-layout creative-materials"><form className="card" onSubmit={submit}><p className="eyebrow">Materiales</p><h2>Subir una pieza para revisión</h2><p className="muted">{selectedConcept ? "La revisión se hará contra la plataforma elegida, la ruta aprobada y los controles de marca y propiedad." : "Primero elegí y guardá una plataforma creativa. Así ninguna pieza se evalúa contra un diagnóstico genérico."}</p><div className="field"><label>Nombre</label><input name="name" required/></div><div className="field"><label>Medio o formato</label><input name="medium" placeholder="Radio 30s, historia vertical, cartel, gráfica…"/></div><div className="field"><label>Fundamento creativo</label><textarea name="rationale" placeholder="Explicá cómo la pieza desarrolla la plataforma elegida y qué comportamiento busca provocar."/></div><div className="field"><label>Archivo</label><input name="file" type="file" required accept="image/*,.pdf,.txt,.md"/></div><button className="btn lime" disabled={!selectedConcept || busy}>{busy ? "Evaluando…" : "Cargar y revisar material"}</button></form>
      <div>{reviews.length === 0 ? <div className="empty"><h3>No hay materiales revisados</h3><p className="muted">Después de elegir una plataforma, subí bocetos, guiones o piezas para recibir una devolución publicitaria concreta.</p></div> : <div className="library-list">{reviews.map(review => <article className="card" key={review.id}><div className="review-head"><div><span className="status">{review.verdict.replace("_", " ")}</span><h2>{review.name}</h2></div><small>{review.medium || review.filename}</small></div><p className="creative-evaluation">{review.evaluation}</p><div className="score-grid">{Object.entries(review.scores).map(([key, score]) => <div className="score" key={key}><span>{labels[key] || key}</span><strong>{score}/5</strong><i><b style={{ width: `${score * 20}%` }}/></i></div>)}</div></article>)}</div>}</div>
    </section>
  </main>;
}
