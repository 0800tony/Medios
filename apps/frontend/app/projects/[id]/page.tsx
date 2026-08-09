"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { DocumentItem, EvidenceItem, Project, RadarSuggestion, request, requestBlob, saveBlob } from "@/lib/api";

type EvidenceMode = "file" | "audio" | "mail" | "reference" | "client_note" | "research";

function AudioPlayer({projectId,item}:{projectId:string;item:DocumentItem}){
  const [src,setSrc]=useState("");
  useEffect(()=>{let objectUrl="";requestBlob(`/api/projects/${projectId}/documents/${item.id}/media`).then(blob=>{objectUrl=URL.createObjectURL(blob);setSrc(objectUrl)});return()=>{if(objectUrl)URL.revokeObjectURL(objectUrl)}},[projectId,item.id]);
  return src?<audio className="audio-player" controls preload="metadata" src={src}/>:<small>Cargando audio…</small>;
}

export default function ProjectPage({ params }: { params: { id: string } }) {
  const [project, setProject] = useState<Project | null>(null);
  const [radar, setRadar] = useState<RadarSuggestion[]>([]);
  const [mode, setMode] = useState<EvidenceMode>("file");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [transcriptFor,setTranscriptFor]=useState("");
  const [manualTranscript,setManualTranscript]=useState("");
  const [editingProject,setEditingProject]=useState(false);
  const [researchSummary,setResearchSummary]=useState("");

  const load = () => request<Project>(`/api/projects/${params.id}`).then(setProject);
  const loadRadar = () => request<RadarSuggestion[]>(`/api/projects/${params.id}/radar`).then(setRadar);
  useEffect(() => { load(); loadRadar(); }, []);

  async function upload(file: File) {
    setBusy(true); setError("");
    const form = new FormData(); form.append("file", file);
    try { setProject(await request<Project>(`/api/projects/${params.id}/documents`, { method: "POST", body: form })); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function uploadAudio(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const form=event.currentTarget; const data=new FormData(form);
    try{setProject(await request<Project>(`/api/projects/${params.id}/audio`,{method:"POST",body:data}));form.reset()}
    catch(e){setError((e as Error).message)}finally{setBusy(false)}
  }

  async function uploadMailFile(file: File) {
    setBusy(true);setError("");const data=new FormData();data.append("file",file);
    try{setProject(await request<Project>(`/api/projects/${params.id}/mail-file`,{method:"POST",body:data}))}
    catch(e){setError((e as Error).message)}finally{setBusy(false)}
  }

  async function addMail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();setBusy(true);setError("");const form=event.currentTarget;
    try{setProject(await request<Project>(`/api/projects/${params.id}/mail`,{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(form)))}));form.reset()}
    catch(e){setError((e as Error).message)}finally{setBusy(false)}
  }

  async function saveTranscript(document:DocumentItem){
    setBusy(true);setError("");try{await request(`/api/projects/${params.id}/documents/${document.id}/text`,{method:"PATCH",body:JSON.stringify({text:manualTranscript})});setTranscriptFor("");setManualTranscript("");await load()}catch(e){setError((e as Error).message)}finally{setBusy(false)}
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

  async function researchWeb(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setResearchSummary("");
    try {
      const result = await request<{summary:string;added_sources:number}>(`/api/projects/${params.id}/research`, { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) });
      setResearchSummary(`${result.summary}\n\nSe incorporaron ${result.added_sources} fuentes para revisar y usar en el próximo análisis.`); await load();
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

  async function removeDocument(document: DocumentItem) {
    if (!confirm(`¿Quitar “${document.filename}” y su contenido del análisis?`)) return;
    setBusy(true); setError("");
    try { await request(`/api/projects/${params.id}/documents/${document.id}`, { method: "DELETE" }); await load(); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function downloadDocument(document: DocumentItem) {
    setError("");
    try { saveBlob(await requestBlob(`/api/projects/${params.id}/documents/${document.id}/media`), document.filename); }
    catch (e) { setError((e as Error).message); }
  }

  async function updateProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      setProject(await request<Project>(`/api/projects/${params.id}`, { method: "PATCH", body: JSON.stringify(Object.fromEntries(new FormData(event.currentTarget))) }));
      setEditingProject(false);
      await loadRadar();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function deleteProject() {
    if (!confirm(`¿Eliminar definitivamente el proyecto “${project?.name}”, sus archivos y el diagnóstico?`)) return;
    setBusy(true); setError("");
    try { await request(`/api/projects/${params.id}`, { method: "DELETE" }); location.href = "/"; }
    catch (e) { setError((e as Error).message); setBusy(false); }
  }

  async function analyze() {
    setBusy(true); setError("");
    try {
      const output = await request<Project>(`/api/projects/${params.id}/analyze`, { method: "POST" });
      setProject(output); location.href = `/projects/${params.id}/result`;
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function decideRadar(suggestion: RadarSuggestion, status: "approved" | "dismissed") {
    setBusy(true); setError("");
    try {
      await request(`/api/projects/${params.id}/radar/${suggestion.item.id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      await loadRadar();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  if (!project) return <main className="shell"><Nav/><p>Cargando…</p></main>;
  const evidenceCount = project.documents.length + project.evidence_items.length;
  const approvedRadarCount = radar.filter(suggestion => suggestion.status === "approved").length;
  const sourceCount = evidenceCount + approvedRadarCount;

  return <main className="shell">
    <Nav/>
    <div className="pagehead">
      <div><p className="eyebrow">Proyecto · {evidenceCount} evidencias</p><h1>{project.name}</h1><span className={`status ${project.status}`}>{project.status}</span></div>
      <div className="page-actions"><Link className="btn lime" href={`/projects/${project.id}/brief`}>Completar brief</Link>{project.result&&<Link className="btn" href={`/projects/${project.id}/result`}>Ver estrategia</Link>}<Link className="btn ghost" href={`/projects/${project.id}/creative`}>Revisar piezas</Link><button className="btn ghost" onClick={()=>setEditingProject(value=>!value)}>{editingProject?"Cancelar edición":"Editar proyecto"}</button></div>
    </div>

    <section className="project-layout">
      <div>
        <div className="card">
          <p className="eyebrow">Biblioteca de evidencia</p>
          <h2>¿Qué querés incorporar?</h2>
          <div className="tabs">
            <button className={mode === "file" ? "active" : ""} onClick={() => setMode("file")}>Archivo</button>
            <button className={mode === "audio" ? "active" : ""} onClick={() => setMode("audio")}>Audio</button>
            <button className={mode === "mail" ? "active" : ""} onClick={() => setMode("mail")}>Correo</button>
            <button className={mode === "reference" ? "active" : ""} onClick={() => setMode("reference")}>Enlace</button>
            <button className={mode === "research" ? "active" : ""} onClick={() => setMode("research")}>Buscar en la web</button>
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

          {mode === "audio" && <form onSubmit={uploadAudio}>
            <p className="muted">MP3, MP4, M4A, WAV o WEBM · hasta 25 MB</p>
            <div className="field"><label>Grabación</label><input name="file" type="file" accept=".mp3,.mp4,.mpeg,.mpga,.m4a,.wav,.webm,audio/*" required/></div>
            <div className="field"><label>Contexto para la transcripción</label><textarea name="context" placeholder="Quiénes hablan, cliente, tema y nombres propios que conviene reconocer…"/></div>
            <div className="field"><label>Transcripción disponible (opcional)</label><textarea name="transcript" placeholder="Si ya tenés una transcripción, pegala acá. Tendrá prioridad sobre la automática."/></div>
            <button className="btn lime" disabled={busy}>{busy?"Procesando audio…":"Subir y transcribir"}</button>
            <p className="muted smallprint">Con una API key se transcribe automáticamente. Sin ella, el audio queda guardado y podés agregar el texto después.</p>
          </form>}

          {mode === "mail" && <div className="mail-ingestion">
            <div><p className="muted">Subí el correo original en formato .eml</p><label className="drop" style={{display:"block",cursor:"pointer"}}><input type="file" hidden accept=".eml,message/rfc822" onChange={e=>e.target.files?.[0]&&uploadMailFile(e.target.files[0])}/><strong>{busy?"Leyendo correo…":"Elegir archivo .eml"}</strong><br/><small>Extraemos remitente, destinatarios, fecha, cuerpo y adjuntos mencionados.</small></label></div>
            <div className="or"><span>o pegar el correo</span></div>
            <form onSubmit={addMail}><div className="field"><label>Asunto</label><input name="subject" required/></div><div className="field two"><div><label>De</label><input name="from_address"/></div><div><label>Para</label><input name="to_address"/></div></div><div className="field"><label>Fecha</label><input name="date" placeholder="Ej. 12 de agosto de 2026"/></div><div className="field"><label>Contenido</label><textarea name="content" required placeholder="Pegá aquí el cuerpo completo del correo…"/></div><button className="btn lime" disabled={busy}>Guardar correo</button></form>
          </div>}

          {mode === "reference" && <form onSubmit={e => addEvidence(e, "reference")}>
            <div className="field"><label>Título del artículo o referencia</label><input name="title" required placeholder="Ej. Por qué cae la confianza en las marcas"/></div>
            <div className="field"><label>Enlace</label><input name="url" type="url" required placeholder="https://…"/></div>
            <div className="field"><label>Fuente o publicación</label><input name="source" placeholder="Ej. El País, estudio de mercado…"/></div>
            <div className="field"><label>Extracto o relevancia estratégica</label><textarea name="content" placeholder="¿Qué dato, argumento o perspectiva aporta esta referencia?"/></div>
            <button className="btn lime" disabled={busy}>Agregar referencia</button>
          </form>}

          {mode === "research" && <form onSubmit={researchWeb}>
            <p className="muted">Busca y cita fuentes públicas. Prioriza Kantar, NielsenIQ, Ipsos, GfK y Euromonitor; prensa empresaria argentina, medios especializados y foros como señales a contrastar.</p>
            <div className="field"><label>¿Qué necesitás investigar?</label><textarea name="query" required minLength={3} placeholder="Ej. Mercado argentino de alfajores: consumo, precio, distribución, competidores y tendencias de compra"/></div>
            <button className="btn lime" disabled={busy}>{busy ? "Investigando…" : "Buscar fuentes relevantes"}</button>
            <p className="muted smallprint">Las fuentes encontradas quedan vinculadas al proyecto con su enlace original. Las notas de foros se identifican como señales, no como hechos.</p>
          </form>}

          {mode === "client_note" && <form onSubmit={e => addEvidence(e, "client_note")}>
            <div className="field"><label>Título de la conversación</label><input name="title" required placeholder="Ej. Entrevista inicial con Gerencia"/></div>
            <div className="field"><label>Quién aportó la información</label><input name="source" placeholder="Nombre, cargo o área"/></div>
            <div className="field"><label>Información obtenida</label><textarea name="content" required placeholder="Hechos, opiniones, preocupaciones, frases textuales, datos pendientes y contradicciones observadas…"/></div>
            <button className="btn lime" disabled={busy}>Guardar nota</button>
          </form>}
        </div>

        {researchSummary && <div className="card research-summary"><p className="eyebrow">Investigación web</p><p>{researchSummary}</p></div>}<div className="evidence-list">
          {project.documents.map(document => <article className={`evidence-row ${document.category}`} key={document.id}>
            <span className="evidence-icon">{document.category === "audio" ? "AUDIO" : document.category === "email" ? "MAIL" : document.filename.toLowerCase().endsWith(".docx") ? "WORD" : "DOC"}</span><div><strong>{document.filename}</strong><p>{Math.ceil(document.size / 1024)} KB · {document.processed ? document.category === "audio" ? "transcripción disponible" : "texto extraído" : "transcripción pendiente"}</p>{document.text_excerpt&&<p className="document-excerpt">{document.text_excerpt}</p>}{document.category === "audio"&&<><AudioPlayer projectId={project.id} item={document}/>{!document.processed&&(transcriptFor===document.id?<div className="transcript-box"><textarea value={manualTranscript} onChange={e=>setManualTranscript(e.target.value)} placeholder="Pegá o escribí la transcripción…"/><button className="btn lime" disabled={busy||manualTranscript.trim().length<2} onClick={()=>saveTranscript(document)}>Guardar transcripción</button></div>:<button className="text-action" onClick={()=>setTranscriptFor(document.id)}>Agregar transcripción</button>)}</>}</div><div className="row-actions"><button onClick={()=>downloadDocument(document)}>Descargar</button><button className="danger-link" onClick={()=>removeDocument(document)}>Quitar</button></div>
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
        {editingProject?<form onSubmit={updateProject}><p className="eyebrow">Editar proyecto</p><div className="field"><label>Nombre</label><input name="name" required defaultValue={project.name}/></div><div className="field"><label>Objetivo declarado</label><input name="objective" defaultValue={project.objective}/></div><div className="field"><label>Brief / contexto</label><textarea name="brief" defaultValue={project.brief}/></div><div className="inline-actions"><button className="btn lime" disabled={busy}>Guardar cambios</button><button type="button" className="btn ghost" onClick={()=>setEditingProject(false)}>Cancelar</button></div></form>:<><p className="eyebrow">Punto de partida</p><h3>Objetivo declarado</h3><p>{project.objective || "Sin definir"}</p><h3>Brief</h3><p className="muted">{project.brief || "Sin contexto adicional"}</p></>}
        <hr/><p className="muted"><strong>OLIVA Strategy</strong> tratará los archivos, enlaces y notas como fuentes diferenciadas. Una opinión del cliente no se convertirá automáticamente en un hecho.</p>
        {radar.length > 0 && <div className="radar-suggestions"><p className="eyebrow">Radar aplicable</p><p className="radar-help">La IA encontró estas conexiones. Aprobá las que deban entrar al próximo análisis.</p>{radar.map(suggestion => <div className={`radar-suggestion ${suggestion.status}`} key={suggestion.item.id}><span className="match-score">{suggestion.score}% afinidad</span><strong>{suggestion.item.title}</strong><small>{suggestion.reason}</small><small>{suggestion.item.kind} · {suggestion.item.source || "Radar OLIVA"}</small><div className="suggestion-actions"><button className={suggestion.status === "approved" ? "selected" : ""} disabled={busy} onClick={() => decideRadar(suggestion, "approved")}>{suggestion.status === "approved" ? "✓ Aplicada" : "Aplicar"}</button><button className={suggestion.status === "dismissed" ? "selected dismiss" : ""} disabled={busy} onClick={() => decideRadar(suggestion, "dismissed")}>{suggestion.status === "dismissed" ? "Descartada" : "Descartar"}</button></div></div>)}</div>}
        <hr/><button className="danger-link project-delete" disabled={busy} onClick={deleteProject}>Eliminar proyecto</button>
      </aside>
    </section>

    {error && <p className="error">{error}</p>}
    <div className="analyze-bar"><div><strong>{sourceCount} {sourceCount === 1 ? "fuente disponible" : "fuentes disponibles"}</strong><p className="muted">Incluye evidencia propia y referencias del Radar que hayas aprobado.</p></div><button className="btn lime" disabled={busy} onClick={analyze}>{busy ? "Analizando…" : "Analizar con OLIVA Strategy →"}</button></div>
  </main>;
}
