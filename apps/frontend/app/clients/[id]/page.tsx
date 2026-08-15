"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { Client, ClientMemory, Project, request } from "@/lib/api";

const fields = [
  ["history", "Historia y relación"], ["products", "Productos y servicios"], ["audiences", "Públicos y ocasiones"], ["competitors", "Competencia y sustitutos"], ["positioning", "Posicionamiento"], ["tone", "Tono y vocabulario"], ["visual_codes", "Códigos visuales y sonoros"], ["restrictions", "Restricciones y obligatorios"], ["approved_patterns", "Aprendizajes aprobados"], ["rejected_patterns", "Enfoques a evitar"], ["commercial_context", "Contexto comercial"], ["territories", "Territorios"], ["notes", "Notas estratégicas"],
];

export default function ClientProfile({ params }: { params: { id: string } }) {
  const [client, setClient] = useState<Client | null>(null); const [memory, setMemory] = useState<ClientMemory | null>(null); const [projects, setProjects] = useState<Project[]>([]); const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [saved, setSaved] = useState(false);
  const load = async () => { const [clientData, memoryData, projectsData] = await Promise.all([request<Client[]>("/api/clients").then(items => items.find(item => item.id === params.id) || null), request<ClientMemory>(`/api/clients/${params.id}/memory`), request<Project[]>("/api/projects")]); setClient(clientData); setMemory(memoryData); setProjects(projectsData.filter(project => project.client_id === params.id)); };
  useEffect(() => { load().catch(error => setError(error.message)); }, [params.id]);
  async function save(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setBusy(true); setError(""); setSaved(false); try { const data = Object.fromEntries(new FormData(event.currentTarget)); setMemory(await request<ClientMemory>(`/api/clients/${params.id}/memory`, { method: "PUT", body: JSON.stringify({ data }) })); setSaved(true); } catch (error) { setError((error as Error).message); } finally { setBusy(false); } }
  if (!client || !memory) return <main className="shell"><Nav/><p>{error || "Cargando cliente…"}</p></main>;
  return <main className="shell"><Nav/><div className="pagehead"><div><p className="eyebrow">Memoria de cliente · versión {memory.version}</p><h1>{client.name}</h1><p className="muted">{client.industry || "Industria sin definir"}</p></div><div className="page-actions"><Link className="btn ghost" href="/clients">← Clientes</Link><Link className="btn lime" href="/projects/new">Nuevo proyecto</Link></div></div>
    <section className="client-memory-layout"><form className="card memory-form" onSubmit={save}><p className="eyebrow">Memoria estratégica</p><h2>Lo que OLIVA debe recordar</h2><p className="muted">Esta memoria se reutiliza como contexto, nunca como evidencia nueva. Actualizala cuando exista una decisión, aprendizaje o material confirmado.</p>{fields.map(([key, label]) => <div className="field" key={key}><label>{label}</label><textarea name={key} defaultValue={memory.data[key] || ""}/></div>)}<button className="btn lime" disabled={busy}>{busy ? "Guardando…" : "Guardar memoria"}</button>{saved && <p className="success">Memoria actualizada y versionada.</p>}{error && <p className="error">{error}</p>}</form>
      <aside><div className="card"><p className="eyebrow">Expediente vivo</p><h2>{projects.length} proyectos</h2>{projects.length === 0 ? <p className="muted">Todavía no hay proyectos asociados.</p> : <div className="library-list">{projects.map(project => <Link className="card nested-card" href={`/projects/${project.id}`} key={project.id}><span className="status">{project.workflow_stage.replaceAll("_", " ")}</span><h3>{project.name}</h3><p className="muted">{project.objective || "Sin objetivo declarado"}</p></Link>)}</div>}</div></aside>
    </section>
  </main>;
}
