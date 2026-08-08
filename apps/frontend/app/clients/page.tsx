"use client";
import { FormEvent, useEffect, useState } from "react";
import Nav from "@/components/Nav";
import { Client, request } from "@/lib/api";

export default function ClientsPage(){
  const [clients,setClients]=useState<Client[]>([]),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  const load=()=>request<Client[]>("/api/clients").then(setClients);
  useEffect(()=>{load()},[]);
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError("");const form=event.currentTarget;try{await request("/api/clients",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(form)))});form.reset();await load()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
  return <main className="shell"><Nav/><div className="pagehead"><div><p className="eyebrow">Sprint 2 · Clientes</p><h1>Clientes</h1></div></div><section className="client-layout"><form className="card" onSubmit={submit}><h2>Nuevo cliente</h2><div className="field"><label>Nombre</label><input name="name" required/></div><div className="field"><label>Industria</label><input name="industry" placeholder="Ej. Alimentos, retail…"/></div><div className="field"><label>Contexto</label><textarea name="description" placeholder="Qué hace la organización, situación y datos relevantes…"/></div>{error&&<p className="error">{error}</p>}<button className="btn lime" disabled={busy}>{busy?"Guardando…":"Crear cliente"}</button></form><div><p className="eyebrow">Directorio</p><div className="client-grid">{clients.map(client=><article className="card" key={client.id}><h3>{client.name}</h3><p className="tags">{client.industry||"Industria sin definir"}</p><p className="muted">{client.description||"Sin contexto adicional."}</p></article>)}</div>{clients.length===0&&<div className="empty small">Todavía no hay clientes.</div>}</div></section></main>
}
