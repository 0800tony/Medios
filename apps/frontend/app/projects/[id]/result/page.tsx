"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { Project, request, requestBlob, saveBlob } from "@/lib/api";

export default function ResultPage({ params }: { params: { id: string } }) {
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    request<Project>(`/api/projects/${params.id}`).then(setProject).catch(error => setError(error.message));
  }, []);

  async function downloadReport() {
    setBusy(true); setError("");
    try {
      saveBlob(await requestBlob(`/api/projects/${params.id}/report`), `diagnostico-${project?.name || "oliva"}.md`);
    } catch (error) { setError((error as Error).message); }
    finally { setBusy(false); }
  }

  if (!project) return <main className="shell"><Nav/><p>{error || "Cargando…"}</p></main>;
  if (!project.result) return <main className="shell"><Nav/><div className="empty"><h2>Este proyecto todavía no tiene diagnóstico.</h2><Link href={`/projects/${project.id}`} className="btn">Volver al proyecto</Link></div></main>;
  const result = project.result;
  const sources = [
    ...project.documents.map(document => ({ id: document.id, label: document.filename, url: "" })),
    ...project.evidence_items.map(item => ({ id: item.id, label: item.title, url: item.url })),
  ];

  return <main className="shell result-page">
    <Nav/>
    <div className="pagehead">
      <div><p className="eyebrow">Resultado · Confianza {result.confidence}</p><h1>{project.name}</h1><p className="muted">{result.model_used}</p></div>
      <div className="page-actions"><button className="btn lime" disabled={busy} onClick={downloadReport}>{busy ? "Preparando…" : "Descargar informe"}</button><button className="btn ghost" onClick={()=>window.print()}>Imprimir / PDF</button><Link href={`/projects/${project.id}`} className="btn ghost">← Evidencia</Link></div>
    </div>
    {error && <p className="error">{error}</p>}
    <section className="results">
      <article className="card wide"><p className="eyebrow">Diagnóstico</p><p className="quote">{result.diagnosis}</p></article>
      <article className="card"><p className="eyebrow">Evidencia</p><p>{result.evidence}</p></article>
      <article className="card"><p className="eyebrow">Contradicciones</p><p>{result.contradictions}</p></article>
      <article className="card"><p className="eyebrow">Hipótesis a refutar</p><p>{result.hypotheses}</p></article>
      <article className="card" style={{background:"var(--lime)"}}><p className="eyebrow">Pregunta estratégica</p><p className="quote">{result.strategic_question}</p></article>
      <article className="card wide source-manifest"><p className="eyebrow">Fuentes incorporadas directamente</p>{sources.length ? <ul>{sources.map(source => <li key={source.id}>{source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.label} ↗</a> : source.label}</li>)}</ul> : <p className="muted">El análisis se realizó únicamente con el brief y el contexto del cliente.</p>}<p className="muted smallprint">Las señales aprobadas desde Radar OLIVA también quedan enumeradas en el informe descargable.</p></article>
    </section>
    <div style={{height:70}}/>
  </main>;
}
