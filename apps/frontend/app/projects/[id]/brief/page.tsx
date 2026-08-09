"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import Nav from "@/components/Nav";
import { Brief, Project, request } from "@/lib/api";

const groups = [
  { title: "El pedido y el negocio", fields: [["request", "¿Qué está pidiendo el cliente?"], ["business_context", "¿Qué está pasando en el negocio?"], ["product", "Producto, servicio o iniciativa"], ["participants", "¿Quiénes participan y quién decide?"], ["decisions", "Decisiones ya tomadas"]] },
  { title: "Objetivos diferenciados", fields: [["business_goal", "Objetivo de negocio"], ["commercial_goal", "Objetivo comercial"], ["communication_goal", "Objetivo de comunicación"], ["media_goal", "Objetivo de medios"]] },
  { title: "Personas y comportamiento", fields: [["audience", "Personas prioritarias"], ["behavior", "Comportamiento que debe cambiar"], ["barriers", "Barreras y objeciones"], ["motivations", "Motivaciones y tensiones"]] },
  { title: "Marca, mercado y evidencia", fields: [["competitors", "Categoría y competencia"], ["positioning", "Posicionamiento actual y deseado"], ["proof", "Razones para creer"], ["brand_tone", "Tono y criterios de marca"], ["previous_work", "Antecedentes y casos OLIVA"]] },
  { title: "Condiciones", fields: [["territory", "Territorio, Interior y cobertura"], ["distribution", "Distribución y acceso"], ["budget", "Presupuesto"], ["deadline", "Plazos e hitos"], ["restrictions", "Restricciones"], ["measurement", "Cómo mediremos el resultado"]] },
  { title: "Resolver vacíos críticos", fields: [["consumer_behavior_evidence", "Validación de comportamiento", "Entrevistas, observaciones o datos sobre quién compra, quién consume, ocasión, disparador y barreras. Indicá fuente y fecha."], ["brand_architecture", "Arquitectura entre marcas", "Qué representa cada marca, qué comparten y qué nunca debe compartirse. Indicá también quién toma esta decisión."], ["price_value_evidence", "Valor percibido y precio", "Precio, gramaje, márgenes, atributos que lo justifican y cualquier prueba con consumidores o canales."], ["capacity_distribution_evidence", "Capacidad y distribución", "Producción actual/máxima, reposición, puntos de venta, cobertura, inversión y limitaciones logísticas."], ["audience_priority_evidence", "Audiencia prioritaria", "Definí quién compra primero, quién consume, quién prescribe y cuál es la evidencia disponible."], ["competitive_product_evidence", "Prueba competitiva y de producto", "Comparación frente a competidores: producto, sabor, envase, precio, exhibición, rotación o recompra."]] },
];

export default function BriefPage({ params }: { params: { id: string } }) {
  const formRef = useRef<HTMLFormElement>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    Promise.all([request<Project>(`/api/projects/${params.id}`), request<Brief>(`/api/projects/${params.id}/brief`)])
      .then(([projectData, briefData]) => { setProject(projectData); setBrief(briefData); })
      .catch(error => setError(error.message));
  }, [params.id]);

  useEffect(() => {
    if (!brief || typeof window === "undefined") return;
    const field = window.location.hash.slice(1);
    if (field) document.getElementById(`${field}-input`)?.focus();
  }, [brief]);

  async function saveBrief(generateStrategy: boolean) {
    if (!formRef.current) return;
    setBusy(true); setSaved(false); setError("");
    try {
      const updated = await request<Brief>(`/api/projects/${params.id}/brief`, { method: "PUT", body: JSON.stringify({ data: Object.fromEntries(new FormData(formRef.current)) }) });
      setBrief(updated); setSaved(true);
      if (generateStrategy) {
        await request(`/api/projects/${params.id}/analyze`, { method: "POST" });
        window.location.href = `/projects/${params.id}/result`;
      }
    } catch (error) { setError((error as Error).message); }
    finally { setBusy(false); }
  }

  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); saveBrief(false); }
  if (!project || !brief) return <main className="shell"><Nav/><p>{error || "Cargando brief…"}</p></main>;

  return <main className="shell"><Nav/>
    <div className="pagehead"><div><p className="eyebrow">Brief estratégico editable</p><h1>{project.name}</h1></div><div className="page-actions"><Link className="btn ghost" href={`/projects/${project.id}`}>← Proyecto</Link><Link className="btn" href={`/projects/${project.id}/result`}>Ver estrategia existente</Link></div></div>
    <section className="brief-progress"><div><strong>Contexto mínimo: {brief.completeness}%</strong><p>Indica que hay respuestas cargadas; las validaciones estratégicas se muestran aparte.</p></div><div className="progress"><span style={{ width: `${brief.completeness}%` }}/></div></section>
    {brief.missing_required.length > 0 && <div className="brief-alert"><strong>Falta información clave</strong><p>{brief.missing_required.join(" · ")}</p></div>}
    <form ref={formRef} className="brief-form" onSubmit={submit}>
      {groups.map((group, index) => <section className="card brief-group" key={group.title}><p className="section-number">{String(index + 1).padStart(2, "0")}</p><h2>{group.title}</h2>{group.fields.map(([key, label, placeholder]) => <div className="field" id={key} key={key}><label htmlFor={`${key}-input`}>{label}</label><textarea id={`${key}-input`} name={key} defaultValue={brief.data[key] || ""} placeholder={placeholder || "Hechos, percepciones, dudas y fuentes…"}/></div>)}</section>)}
      {error && <p className="error">{error}</p>}{saved && <p className="success">Brief guardado.</p>}
      <div className="brief-save"><button className="btn ghost" type="submit" disabled={busy}>{busy ? "Procesando…" : "Guardar y seguir después"}</button><button className="btn lime" type="button" disabled={busy} onClick={() => saveBrief(true)}>{busy ? "Generando estrategia…" : "Guardar y generar estrategia →"}</button><span>Generar crea una nueva versión del contrabrief.</span></div>
    </form><div style={{ height: 70 }}/>
  </main>;
}
