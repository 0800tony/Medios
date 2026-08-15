"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { CreativeConcept, CreativeReview, CreativeTerritory, Dossier, Project, StrategyDecision, request } from "@/lib/api";

const labels: Record<string, string> = { estrategia: "Estrategia", verdad_humana: "Verdad humana", rol_de_marca: "Rol de marca", apropiabilidad: "Propiedad", originalidad: "Originalidad", claridad: "Claridad", fertilidad: "Fertilidad", coherencia: "Coherencia", adecuacion_al_medio: "Adecuación al medio", viabilidad: "Viabilidad" };
const copy = <T,>(value: T): T => JSON.parse(JSON.stringify(value));

function territories(board: Record<string, unknown> | null): CreativeTerritory[] {
  return Array.isArray(board?.territorios) ? board!.territorios as CreativeTerritory[] : [];
}

export default function Creative({ params }: { params: { id: string } }) {
  const [project, setProject] = useState<Project | null>(null);
  const [strategy, setStrategy] = useState<Dossier | null>(null);
  const [decision, setDecision] = useState<StrategyDecision | null>(null);
  const [concepts, setConcepts] = useState<CreativeConcept[]>([]);
  const [reviews, setReviews] = useState<CreativeReview[]>([]);
  const [board, setBoard] = useState<Record<string, unknown> | null>(null);
  const [territoryId, setTerritoryId] = useState("");
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    const [projectData, conceptData, reviewData] = await Promise.all([
      request<Project>(`/api/projects/${params.id}`), request<CreativeConcept[]>(`/api/projects/${params.id}/creative-concepts`), request<CreativeReview[]>(`/api/projects/${params.id}/creative`),
    ]);
    setProject(projectData); setConcepts(conceptData); setReviews(reviewData);
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

  const ready = strategy?.approval_status === "approved" && !!decision;
  const selectedConcept = concepts.find(concept => concept.status === "selected");
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
    <section className="creative-layout creative-materials"><form className="card" onSubmit={submit}><p className="eyebrow">Materiales</p><h2>Subir una pieza para revisión</h2><p className="muted">{selectedConcept ? "La revisión se hará contra la plataforma elegida, la ruta aprobada y los controles de marca y propiedad." : "Primero elegí y guardá una plataforma creativa. Así ninguna pieza se evalúa contra un diagnóstico genérico."}</p><div className="field"><label>Nombre</label><input name="name" required/></div><div className="field"><label>Medio o formato</label><input name="medium" placeholder="Radio 30s, historia vertical, cartel, gráfica…"/></div><div className="field"><label>Fundamento creativo</label><textarea name="rationale" placeholder="Explicá cómo la pieza desarrolla la plataforma elegida y qué comportamiento busca provocar."/></div><div className="field"><label>Archivo</label><input name="file" type="file" required accept="image/*,.pdf,.txt,.md"/></div><button className="btn lime" disabled={!selectedConcept || busy}>{busy ? "Evaluando…" : "Cargar y revisar material"}</button></form>
      <div>{reviews.length === 0 ? <div className="empty"><h3>No hay materiales revisados</h3><p className="muted">Después de elegir una plataforma, subí bocetos, guiones o piezas para recibir una devolución publicitaria concreta.</p></div> : <div className="library-list">{reviews.map(review => <article className="card" key={review.id}><div className="review-head"><div><span className="status">{review.verdict.replace("_", " ")}</span><h2>{review.name}</h2></div><small>{review.medium || review.filename}</small></div><p className="creative-evaluation">{review.evaluation}</p><div className="score-grid">{Object.entries(review.scores).map(([key, score]) => <div className="score" key={key}><span>{labels[key] || key}</span><strong>{score}/5</strong><i><b style={{ width: `${score * 20}%` }}/></i></div>)}</div></article>)}</div>}</div>
    </section>
  </main>;
}
