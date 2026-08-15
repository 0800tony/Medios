"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { AgentDefinition, AgentRun, Project, request } from "@/lib/api";

function Output({ value }: { value: unknown }) {
  if (Array.isArray(value)) return <ul className="structured">{value.map((item, index) => <li key={index}><Output value={item}/></li>)}</ul>;
  if (value && typeof value === "object") return <dl className="structured">{Object.entries(value as Record<string, unknown>).map(([key, item]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd><Output value={item}/></dd></div>)}</dl>;
  return <p>{String(value || "")}</p>;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [selected, setSelected] = useState("briefing");
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = async () => { const [agentData, projectData] = await Promise.all([request<AgentDefinition[]>("/api/agents"), request<Project[]>("/api/projects")]); setAgents(agentData); setProjects(projectData); if (!projectId && projectData[0]) setProjectId(projectData[0].id); };
  useEffect(() => { load().catch(error => setError(error.message)); }, []);
  useEffect(() => { if (projectId) request<AgentRun[]>(`/api/projects/${projectId}/agents`).then(setRuns).catch(() => setRuns([])); }, [projectId]);
  async function run(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!projectId) return setError("Elegí un proyecto"); setBusy(true); setError(""); try { const data = new FormData(event.currentTarget); await request(`/api/projects/${projectId}/agents/run`, { method: "POST", body: JSON.stringify({ agent_key: selected, instruction: data.get("instruction") }) }); event.currentTarget.reset(); setRuns(await request<AgentRun[]>(`/api/projects/${projectId}/agents`)); } catch (error) { setError((error as Error).message); } finally { setBusy(false); } }
  return <main className="shell"><Nav/>
    <section className="radar-hero"><div><p className="eyebrow">Orquestación de trabajo</p><h1>Agentes OLIVA</h1></div><p>Cada agente deja un resultado versionado y lo envía a revisión humana. No hay decisiones invisibles ni memoria automática sin validar.</p></section>
    <section className="agent-grid">{agents.map(agent => <button className={`card agent-card ${selected === agent.key ? "selected" : ""}`} key={agent.key} onClick={() => setSelected(agent.key)}><span className="status">{agent.stage}</span><h2>{agent.name}</h2><p>{agent.description}</p></button>)}</section>
    <section className="agent-workspace"><form className="card form" onSubmit={run}><p className="eyebrow">Ejecutar agente</p><div className="field"><label>Proyecto</label><select value={projectId} onChange={event => setProjectId(event.target.value)}><option value="">Seleccionar…</option>{projects.map(project => <option key={project.id} value={project.id}>{project.name} · {project.workflow_stage.replaceAll("_", " ")}</option>)}</select></div><div className="field"><label>Instrucción adicional</label><textarea name="instruction" placeholder="Qué querés que priorice en esta ejecución…"/></div><button className="btn lime" disabled={busy || !projectId}>{busy ? "Trabajando…" : `Ejecutar ${agents.find(agent => agent.key === selected)?.name || "agente"}`}</button>{error && <p className="error">{error}</p>}<p className="muted smallprint">La salida se guarda como borrador y aparece en Aprobaciones. La estrategia formal se genera desde el expediente del proyecto.</p></form>
      <div><div className="pagehead small-head"><div><p className="eyebrow">Historial del proyecto</p><h2>Resultados de agentes</h2></div>{projectId && <Link className="btn ghost" href={`/projects/${projectId}`}>Abrir expediente</Link>}</div>{runs.length === 0 ? <div className="empty"><h3>Todavía no hay ejecuciones</h3><p className="muted">Elegí un agente y un proyecto para iniciar una salida trazable.</p></div> : <div className="library-list">{runs.map(run => <article className="card" key={run.id}><div className="review-head"><div><span className="status">{run.status}</span><h3>{agents.find(agent => agent.key === run.agent_key)?.name || run.agent_key}</h3></div><small>{run.model_used}</small></div><Output value={run.output}/></article>)}</div>}</div>
    </section>
  </main>;
}
