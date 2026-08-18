"use client";
import { FormEvent, useEffect, useState } from "react";
import { Measurement, request } from "@/lib/api";

export default function MeasurementBoard({ projectId }: { projectId: string }) {
  const [items, setItems] = useState<Measurement[]>([]); const [error, setError] = useState("");
  const load = () => request<Measurement[]>(`/api/projects/${projectId}/measurements`).then(setItems);
  useEffect(() => { load().catch(error => setError(error.message)); }, [projectId]);
  async function add(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = event.currentTarget; try { await request(`/api/projects/${projectId}/measurements`, { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))) }); form.reset(); await load(); } catch (error) { setError((error as Error).message); } }
  return <section className="measurement card"><div><p className="eyebrow">Medición de resultados</p><h2>Lo que pasó en realidad</h2><p className="muted">Registrá métricas, fuente y período. OLIVA podrá proponer aprendizaje, pero solo se reutiliza luego de validación humana.</p></div><form onSubmit={add}><input required name="metric" placeholder="Métrica: ventas, rotación, leads…"/><input required name="value" placeholder="Resultado"/><input name="baseline" placeholder="Base"/><input name="target" placeholder="Meta"/><input name="period" placeholder="Período"/><input name="source" placeholder="Fuente"/><button className="btn lime">Registrar</button></form>{error && <p className="error">{error}</p>}<div className="measurement-grid">{items.map(item => <article key={item.id}><strong>{item.metric}</strong><b>{item.value}</b><small>{[item.baseline && `base ${item.baseline}`, item.target && `meta ${item.target}`, item.period, item.source].filter(Boolean).join(" · ")}</small></article>)}</div></section>;
}
