"use client";

import { FormEvent, useEffect, useState } from "react";
import { ProjectTask, request } from "@/lib/api";

const stages = ["estrategia", "creatividad", "producción", "medios", "resultados"];
const labels: Record<string, string> = { pending: "Pendiente", in_progress: "En curso", blocked: "Bloqueada", done: "Hecha" };

export default function WorkflowBoard({ projectId }: { projectId: string }) {
  const [tasks, setTasks] = useState<ProjectTask[]>([]); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const load = () => request<ProjectTask[]>(`/api/projects/${projectId}/tasks`).then(setTasks);
  useEffect(() => { load().catch(error => setError(error.message)); }, [projectId]);
  async function add(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = event.currentTarget; setBusy(true); try { await request(`/api/projects/${projectId}/tasks`, { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))) }); form.reset(); await load(); } catch (error) { setError((error as Error).message); } finally { setBusy(false); } }
  async function status(task: ProjectTask, next: ProjectTask["status"]) { setBusy(true); try { await request(`/api/projects/${projectId}/tasks/${task.id}`, { method: "PATCH", body: JSON.stringify({ status: next }) }); await load(); } catch (error) { setError((error as Error).message); } finally { setBusy(false); } }
  return <section className="workflow card"><div><p className="eyebrow">Flujo de trabajo</p><h2>Responsables y próximos pasos</h2><p className="muted">Las tareas coordinan el trabajo del equipo; no cambian la estrategia ni reescriben la creatividad.</p></div><form className="task-form" onSubmit={add}><input required name="title" placeholder="Nueva tarea"/><input name="assignee" placeholder="Responsable"/><select name="stage">{stages.map(stage => <option key={stage}>{stage}</option>)}</select><select name="priority"><option value="alta">Alta</option><option value="media">Media</option><option value="baja">Baja</option></select><input name="due_date" placeholder="Fecha / hito"/><button className="btn lime" disabled={busy}>Agregar</button></form>{error && <p className="error">{error}</p>}<div className="workflow-grid">{stages.map(stage => <article key={stage}><h3>{stage}</h3>{tasks.filter(task => task.stage === stage).map(task => <div className={`task ${task.status}`} key={task.id}><span>{task.priority}</span><strong>{task.title}</strong><small>{task.assignee || "Sin responsable"}{task.due_date ? ` · ${task.due_date}` : ""}</small><select value={task.status} disabled={busy} onChange={event => status(task, event.target.value as ProjectTask["status"])}>{Object.entries(labels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></div>)}{tasks.filter(task => task.stage === stage).length === 0 && <small className="muted">Sin tareas.</small>}</article>)}</div></section>;
}
