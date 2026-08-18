"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { ApprovalTask, request } from "@/lib/api";

export default function ApprovalsPage() {
  const [tasks, setTasks] = useState<ApprovalTask[]>([]); const [busy, setBusy] = useState(""); const [error, setError] = useState("");
  const load = () => request<ApprovalTask[]>("/api/approvals").then(setTasks);
  useEffect(() => { load().catch(error => setError(error.message)); }, []);
  async function resolve(task: ApprovalTask, status: "approved" | "changes" | "rejected") { setBusy(task.id); setError(""); try { await request(`/api/approvals/${task.id}`, { method: "PATCH", body: JSON.stringify({ status, notes: "" }) }); await load(); } catch (error) { setError((error as Error).message); } finally { setBusy(""); } }
  return <main className="shell"><Nav/><section className="radar-hero"><div><p className="eyebrow">Gobierno del proceso</p><h1>Aprobaciones</h1></div><p>La IA propone; el equipo decide. Este tablero conserva la trazabilidad de estrategias, piezas, aprendizajes y salidas de agentes.</p></section>{error && <p className="error">{error}</p>}
    {tasks.length === 0 ? <div className="empty"><h2>No hay pendientes</h2><p className="muted">Las salidas que requieran criterio humano aparecerán acá.</p></div> : <div className="approval-list">{tasks.map(task => <article className="card" key={task.id}><div className="review-head"><div><span className="status">{task.kind.replaceAll("_", " ")}</span><h2>{task.title}</h2></div>{task.project_id && <Link className="btn ghost" href={`/projects/${task.project_id}/result`}>Ver proyecto</Link>}</div><p>{task.summary}</p><div className="inline-actions"><button className="btn lime" disabled={busy === task.id} onClick={() => resolve(task, "approved")}>Aprobar</button><button className="btn ghost" disabled={busy === task.id} onClick={() => resolve(task, "changes")}>Pedir cambios</button><button className="danger-link" disabled={busy === task.id} onClick={() => resolve(task, "rejected")}>Rechazar</button></div></article>)}</div>}
  </main>;
}
