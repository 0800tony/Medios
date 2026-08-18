"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { ApprovalTask, Project, request, token } from "@/lib/api";

const quick = [{ href: "/projects/new", label: "Crear proyecto", text: "Abrir un expediente con cliente, objetivo y responsables." }, { href: "/agents", label: "Analizar un pedido", text: "Normalizar, investigar o desarrollar una salida trazable." }, { href: "/library", label: "Alimentar biblioteca", text: "Incorporar casos, fuentes, referencias y aprendizajes." }, { href: "/approvals", label: "Resolver aprobaciones", text: "Cerrar decisiones para que OLIVA aprenda con criterio humano." }];

export default function Home() {
  const [projects, setProjects] = useState<Project[] | null>(null); const [approvals, setApprovals] = useState<ApprovalTask[]>([]);
  useEffect(() => { if (!token()) { location.href = "/login"; return; } Promise.all([request<Project[]>("/api/projects"), request<ApprovalTask[]>("/api/approvals")]).then(([projectData, approvalData]) => { setProjects(projectData); setApprovals(approvalData); }).catch(() => {}); }, []);
  return <main className="shell"><Nav/><section className="hero"><div><p className="eyebrow">OLIVA Intelligence</p><h1>Entender mejor.<br/>Decidir mejor.</h1></div><p>El sistema operativo de la agencia: evidencia, memoria, criterio estratégico, desarrollo creativo y aprendizaje aprobado en un mismo expediente.</p></section>
    <section className="quick-grid">{quick.map(item => <Link className="card nested-card" href={item.href} key={item.href}><p className="eyebrow">Acción</p><h2>{item.label}</h2><p className="muted">{item.text}</p></Link>)}</section>
    <div className="pagehead"><div><p className="eyebrow">Tu trabajo</p><h1>Proyectos</h1></div><div className="inline-actions">{approvals.length > 0 && <Link className="btn ghost" href="/approvals">{approvals.length} pendiente{approvals.length === 1 ? "" : "s"}</Link>}<Link className="btn lime" href="/projects/new">+ Nuevo proyecto</Link></div></div>
    {projects?.length === 0 ? <div className="empty"><h2>Tu primer diagnóstico empieza acá.</h2><p className="muted">Creá un proyecto, cargá evidencia, completá el brief y activá OLIVA Strategy.</p></div> : <section className="grid">{projects?.map(project => <Link href={`/projects/${project.id}`} className="card" key={project.id}><span className="status">{project.workflow_stage.replaceAll("_", " ")}</span><h2 style={{ marginTop: 22 }}>{project.name}</h2><p className="muted">{project.objective || "Sin objetivo declarado"}</p><small>{project.documents.length + project.evidence_items.length} fuente(s) · {project.group_company}</small></Link>)}</section>}
  </main>;
}
