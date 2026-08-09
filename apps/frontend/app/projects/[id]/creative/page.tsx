"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { CreativeReview, Dossier, Project, StrategyDecision, request } from "@/lib/api";

const labels: Record<string, string> = { estrategia: "Estrategia", verdad_humana: "Verdad humana", rol_de_marca: "Rol de marca", apropiabilidad: "Apropiabilidad", originalidad: "Originalidad", claridad: "Claridad", fertilidad: "Fertilidad", coherencia: "Coherencia", adecuacion_al_medio: "Adecuación al medio", viabilidad: "Viabilidad" };

export default function Creative({ params }: { params: { id: string } }) {
  const [project, setProject] = useState<Project | null>(null);
  const [strategy, setStrategy] = useState<Dossier | null>(null);
  const [decision, setDecision] = useState<StrategyDecision | null>(null);
  const [reviews, setReviews] = useState<CreativeReview[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = async () => {
    setProject(await request<Project>(`/api/projects/${params.id}`));
    request<Dossier>(`/api/projects/${params.id}/strategy`).then(setStrategy).catch(() => setStrategy(null));
    request<StrategyDecision>(`/api/projects/${params.id}/strategy/decision`).then(setDecision).catch(() => setDecision(null));
    setReviews(await request<CreativeReview[]>(`/api/projects/${params.id}/creative`));
  };
  useEffect(() => { load().catch(error => setError(error.message)); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try { await request(`/api/projects/${params.id}/creative`, { method: "POST", body: new FormData(event.currentTarget) }); event.currentTarget.reset(); await load(); }
    catch (error) { setError((error as Error).message); }
    finally { setBusy(false); }
  }
  if (!project) return <main className="shell"><Nav/><p>{error || "Cargando…"}</p></main>;
  const ready = strategy?.approval_status === "approved" && !!decision;
  return <main className="shell"><Nav/>
    <div className="pagehead"><div><p className="eyebrow">Revisión creativa</p><h1>{project.name}</h1></div><div className="page-actions"><Link className="btn ghost" href={`/projects/${project.id}/result`}>← Estrategia</Link><Link className="btn ghost" href={`/projects/${project.id}`}>Proyecto</Link></div></div>
    {!ready && <div className="brief-alert"><strong>Primero elegí y aprobá la estrategia vigente</strong><p>Así OLIVA evalúa cada pieza contra una ruta estratégica acordada.</p></div>}
    {decision && <div className="brief-alert"><strong>Marco activo: {decision.route_key.replace("_", " ")}</strong><p>{decision.rationale}</p></div>}
    <section className="creative-layout"><form className="card" onSubmit={submit}><p className="eyebrow">Nueva propuesta</p><h2>Subir una pieza</h2><div className="field"><label>Nombre</label><input name="name" required/></div><div className="field"><label>Medio o formato</label><input name="medium"/></div><div className="field"><label>Fundamento creativo</label><textarea name="rationale" placeholder="Explicá cómo responde a la ruta elegida y qué comportamiento busca provocar."/></div><div className="field"><label>Archivo</label><input name="file" type="file" required accept="image/*,.pdf,.txt,.md"/></div><button className="btn lime" disabled={!ready || busy}>{busy ? "Evaluando…" : "Evaluar propuesta"}</button>{error && <p className="error">{error}</p>}<p className="muted smallprint">Evalúa la propuesta contra la ruta elegida, la verdad humana, la marca, la originalidad, la claridad, el medio y la viabilidad.</p></form>
      <div>{reviews.length === 0 ? <div className="empty"><h3>No hay propuestas revisadas</h3><p className="muted">Cuando la estrategia esté aprobada, subí una pieza y OLIVA devolverá criterios accionables para mejorarla.</p></div> : <div className="library-list">{reviews.map(review => <article className="card" key={review.id}><div className="review-head"><div><span className="status">{review.verdict.replace("_", " ")}</span><h2>{review.name}</h2></div><small>{review.medium || review.filename}</small></div><p className="creative-evaluation">{review.evaluation}</p><div className="score-grid">{Object.entries(review.scores).map(([key, score]) => <div className="score" key={key}><span>{labels[key] || key}</span><strong>{score}/5</strong><i><b style={{ width: `${score * 20}%` }}/></i></div>)}</div></article>)}</div>}</div>
    </section>
  </main>;
}
