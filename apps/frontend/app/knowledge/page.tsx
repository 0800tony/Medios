"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Nav from "@/components/Nav";
import { KnowledgeItem, request, requestBlob } from "@/lib/api";

type RadarMode = "article" | "video" | "photo";

function Photo({ item }: { item: KnowledgeItem }) {
  const [src, setSrc] = useState("");
  useEffect(() => {
    let objectUrl = "";
    requestBlob(`/api/knowledge/${item.id}/media`).then(blob => { objectUrl = URL.createObjectURL(blob); setSrc(objectUrl); });
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [item.id]);
  return src ? <img className="radar-photo" src={src} alt={item.title}/> : <div className="radar-photo placeholder">Cargando foto…</div>;
}

export default function KnowledgePage() {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [mode, setMode] = useState<RadarMode>("article");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = () => request<KnowledgeItem[]>("/api/knowledge").then(setItems);
  useEffect(() => { load(); }, []);

  const visible = useMemo(() => {
    const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
    return items.filter(item => terms.every(term => `${item.title} ${item.source} ${item.notes} ${item.tags} ${item.ai_summary} ${item.ai_observations}`.toLowerCase().includes(term)));
  }, [items, query]);

  async function addLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const form = event.currentTarget;
    try {
      await request("/api/knowledge/links", { method: "POST", body: JSON.stringify({ ...Object.fromEntries(new FormData(form)), kind: mode }) });
      form.reset(); await load();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function addPhoto(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const form = event.currentTarget; const data = new FormData(form);
    try { await request("/api/knowledge/photos", { method: "POST", body: data }); form.reset(); await load(); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function remove(item: KnowledgeItem) {
    if (!confirm(`¿Eliminar “${item.title}” del Radar OLIVA?`)) return;
    setBusy(true);
    try { await request(`/api/knowledge/${item.id}`, { method: "DELETE" }); await load(); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function reindex(item: KnowledgeItem) {
    setBusy(true); setError("");
    try { await request(`/api/knowledge/${item.id}/reindex`, { method: "POST" }); await load(); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return <main className="shell">
    <Nav/>
    <section className="radar-hero"><div><p className="eyebrow">Memoria transversal</p><h1>Radar OLIVA</h1></div><p>Guardá señales, referencias y observaciones del mundo real. La IA las indexa y recupera cuando encuentra relación con un proyecto.</p></section>

    <section className="radar-layout">
      <div className="card radar-form">
        <p className="eyebrow">Nueva señal</p><h2>Agregar al Radar</h2>
        <div className="tabs"><button className={mode === "article" ? "active" : ""} onClick={() => setMode("article")}>Artículo</button><button className={mode === "video" ? "active" : ""} onClick={() => setMode("video")}>Video</button><button className={mode === "photo" ? "active" : ""} onClick={() => setMode("photo")}>Foto</button></div>
        {mode !== "photo" ? <form onSubmit={addLink}>
          <div className="field"><label>Enlace</label><input name="url" type="url" required placeholder="https://…"/></div>
          <p className="muted smallprint">El título, el medio y la ubicación se completan automáticamente al leer el enlace.</p><details className="radar-details"><summary>Corregir datos manualmente (opcional)</summary><div className="field"><label>Título</label><input name="title"/></div><div className="field"><label>Medio, autor o canal</label><input name="source"/></div></details>
          <div className="field"><label>{mode === "video" ? "Resumen, ideas o transcripción" : "Qué te resultó interesante"}</label><textarea name="notes" placeholder={mode === "video" ? "Pegá una transcripción o anotá las ideas centrales del video…" : "Ideas, citas, patrones o motivos por los que conviene recordarlo…"}/></div>
          <div className="field"><label>Etiquetas</label><input name="tags" placeholder="retail, alimentos, tendencias, experiencia"/></div>
          <button className="btn lime" disabled={busy}>{busy ? "Indexando…" : "Guardar e indexar"}</button>
          <p className="muted smallprint">Intentamos leer automáticamente el título, la descripción y el contenido público del enlace. Tus notas siempre tienen prioridad.</p>
        </form> : <form onSubmit={addPhoto}>
          <div className="field"><label>Título</label><input name="title" required placeholder="Ej. Stand destacado en feria"/></div>
          <div className="field"><label>Foto</label><input name="file" type="file" accept="image/jpeg,image/png,image/webp" required/></div>
          <div className="field"><label>Lugar o fuente</label><input name="source" placeholder="Ej. Expo Retail, Buenos Aires"/></div>
          <div className="field"><label>Qué viste y por qué importa</label><textarea name="notes" placeholder="Contexto de la foto, detalle que llamó la atención y posible aplicación…"/></div>
          <div className="field"><label>Etiquetas</label><input name="tags" placeholder="stand, vidriera, exhibición, diseño"/></div>
          <button className="btn lime" disabled={busy}>{busy ? "Analizando imagen…" : "Subir e indexar foto"}</button>
          <p className="muted smallprint">Con una API key, la IA describe elementos visuales y texto visible. Sin ella, indexa tu título, contexto y etiquetas.</p>
        </form>}
        {error && <p className="error">{error}</p>}
      </div>

      <div>
        <div className="radar-toolbar"><div><p className="eyebrow">Biblioteca</p><h2>{items.length} señales guardadas</h2></div><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Buscar en el Radar…"/></div>
        {visible.length === 0 ? <div className="empty"><h3>{items.length ? "No encontramos coincidencias" : "Todavía no hay señales"}</h3><p className="muted">Los artículos, videos y fotos que cargues aparecerán acá.</p></div> : <div className="radar-grid">
          {visible.map(item => <article className="radar-card" key={item.id}>
            {item.kind === "photo" ? <Photo item={item}/> : <div className={`radar-cover ${item.kind}`}><span>{item.kind === "article" ? "ARTÍCULO" : "VIDEO"}</span></div>}
            <div className="radar-body"><div className="radar-meta"><span>{item.kind}</span><span>{item.index_status === "indexed" ? "Contenido indexado" : item.index_status === "failed" ? "Revisión pendiente" : "Indexación manual"}</span></div><h3>{item.title}</h3><p className="muted">{item.ai_summary || item.notes || item.source}</p>{item.tags && <p className="tags">{item.tags}</p>}<div className="radar-actions">{item.url && <a href={item.url} target="_blank" rel="noreferrer">Abrir ↗</a>}<button onClick={() => reindex(item)} disabled={busy}>Reindexar</button><button onClick={() => remove(item)}>Eliminar</button></div></div>
          </article>)}
        </div>}
      </div>
    </section>
    <div style={{height:70}}/>
  </main>;
}
