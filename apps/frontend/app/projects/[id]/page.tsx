"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { EvidenceItem, Project, request } from "@/lib/api";

type EvidenceMode = "file" | "reference" | "client_note";

export default function ProjectPage({ params }: { params: { id: string } }) {
  const [project, setProject] = useState<Project | null>(null);
  const [mode, setMode] = useState<EvidenceMode>("file");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => request<Project>(`/api/projects/${params.id}`).then(setProject);
  useEffect(() => { load(); }, []);

  async function upload(file: File) {
    setBusy(true); setError("");
    const form = new FormData(); form.append("file", file);
    try { setProject(await request<Project>(`/api/projects/${params.id}/documents`, { method: "POST", body: form })); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function addEvidence(event: FormEvent<HTMLFormElement>, kind: "reference" | "client_note") {
    event.preventDefault(); setBusy(true); setError("");
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    try {
      setProject(await request<Project>(`/api/projects/${params.id}/evidence`, {
        method: "POST", body: JSON.stringify({ ...values, kind })
      }));
      form.reset();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function removeEvidence(item: EvidenceItem) {
    if (!confirm(`¿Quitar “${item.title}” de la evidencia?`)) return;
    setBusy(true); setError("");
    try {
      await request(`/api/projects/${params.id}/evidence/${item.id}`, { method: "DELETE" });
      await load();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function analyze() {
    setBusy(true); setError("");
    try {
      const output = await request<Project>(`/api/projects/${params.id}/analyze`, { method: "POST" });
      setProject(output); location.href = `/projects/${params.id}/result`;
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  if (!project) return <main className="shell"><Nav/><p>Cargando…</p></main>;
  const evidenceCount = project.documents.length + project.evidence_items.length;

  return <main className="shell">
    <Nav/>
    <div className="pagehead">
      <div><p className="eyebrow">Proyecto · {evidenceCount} evidencias</p><h1>{project.name}</h1><span className={`status ${project.status}`}>{project.status}</span></div>
      {project.result && <Link className="btn" href={`/projects/${project.id}/result`}>Ver resultado</Link>}
    </div>

    <section className="project-layout">
      <div>
        <div className="card">
          <p className="eyebrow">Biblioteca de evidencia</p>
          <h2>¿Qué querés incorporar?</h2>
          <div className="tabs">
            <button className={mode === "file" ? "active" : ""} onClick={() => setMode("file")}>Archivo</button>
            <button className={mode === "reference" ? "active" : ""} onClick={() => setMode("reference")}>Enlace</button>
            <button className={mode === "client_note" ? "active" : ""} onClick={() => setMode("client_note")}>Nota del cliente</button>
          </div>

          {mode === "file" && <div>
            <p className="muted">PDF, Word, texto o Markdown · hasta 15 MB</p>
            <label className="drop" style={{display:"block",cursor:"pointer"}}>
              <input type="file" hidden accept=".pdf,.docx,.txt,.md" onChange={e => e.target.files?.[0] && upload(e.target.files[0])}/>
              <strong>{busy ? "Procesando…" : "Elegir documento"}</strong><br/>
              <small>Extraemos el texto y lo incorporamos al análisis.</small>
            </label>
          </div>}

          {mode === "reference" && <form onSubmit={e => addEvidence(e, "reference")}>
            <div className="field"><label>Título del artículo o referencia</label><input name="title" required placeholder="Ej. Por qué cae la confianza en las marcas"/></div>
            <div className="field"><label>Enlace</label><input name="url" type="url" required placeholder="https://…"/></div>
            <div className="field"><label>Fuente o publicación</label><input name="source" placeholder="Ej. El País, estudio de mercado…"/></div>
            <div className="field"><label>Extracto o relevancia estratégica</label><textarea name="content" placeholder="¿Qué dato, argumento o perspectiva aporta esta referencia?"/></div>
            <button className="btn lime" disabled={busy}>Agregar referencia</button>
          </form>}

          {mode === "client_note" && <form onSubmit={e => addEvidence(e, "client_note")}>
            <div className="field"><label>Título de la conversación</label><input name="title" required placeholder="Ej. Entrevista inicial con Gerencia"/></div>
            <div className="field"><label>Quién aportó la información</label><input name="source" placeholder="Nombre, cargo o área"/></div>
            <div className="field"><label>Información obtenida</label><textarea name="content" required placeholder="Hechos, opiniones, preocupaciones, frases textuales, datos pendientes y contradicciones observadas…"/></div>
            <button className="btn lime" disabled={busy}>Guardar nota</button>
          </form>}
        </div>

        <div className="evidence-list">
          {project.documents.map(document => <article className="evidence-row" key={document.id}>
            <span className="evidence-icon">PDF</span><div><strong>{document.filename}</strong><p>{Math.ceil(document.size / 1024)} KB · texto extraído</p></div>
          </article>)}
          {project.evidence_items.map(item => <article className="evidence-row" key={item.id}>
            <span className="evidence-icon">{item.kind === "reference" ? "URL" : "NOTA"}</span>
            <div><strong>{item.title}</strong><p>{item.source || (item.kind === "reference" ? "Referencia externa" : "Fuente no indicada")}</p>{item.url && <a href={item.url} target="_blank" rel="noreferrer">Abrir enlace ↗</a>}</div>
            <button className="remove" onClick={() => removeEvidence(item)} aria-label="Quitar evidencia">×</button>
          </article>)}
          {evidenceCount === 0 && <div className="empty small"><p>Todavía no hay evidencia incorporada.</p></div>}
        </div>
      </div>

      <aside className="card project-brief">
        <p className="eyebrow">Punto de partida</p><h3>Objetivo declarado</h3><p>{project.objective || "Sin definir"}</p>
        <h3>Brief</h3><p className="muted">{project.brief || "Sin contexto adicional"}</p>
        <hr/><p className="muted"><strong>OLIVA Strategy</strong> tratará los archivos, enlaces y notas como fuentes diferenciadas. Una opinión del cliente no se convertirá automáticamente en un hecho.</p>
      </aside>
    </section>

    {error && <p className="error">{error}</p>}
    <div className="analyze-bar"><div><strong>{evidenceCount} fuentes disponibles</strong><p className="muted">Podés volver a analizar cuando agregues nueva evidencia.</p></div><button className="btn lime" disabled={busy} onClick={analyze}>{busy ? "Analizando…" : "Analizar con OLIVA Strategy →"}</button></div>
  </main>;
}
