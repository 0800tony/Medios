"use client";
import { FormEvent, useEffect, useState } from "react";
import Nav from "@/components/Nav";
import { request, User } from "@/lib/api";

export default function AccountPage(){
  const [user,setUser]=useState<User|null>(null),[error,setError]=useState(""),[saved,setSaved]=useState(false),[busy,setBusy]=useState(false);
  useEffect(()=>{request<User>("/api/auth/me").then(setUser)},[]);
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError("");setSaved(false);const data=Object.fromEntries(new FormData(event.currentTarget));try{const updated=await request<User>("/api/auth/me",{method:"PATCH",body:JSON.stringify(data)});setUser(updated);localStorage.setItem("oliva_user",JSON.stringify(updated));setSaved(true);(event.currentTarget.elements.namedItem("current_password") as HTMLInputElement).value="";(event.currentTarget.elements.namedItem("new_password") as HTMLInputElement).value=""}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
  if(!user)return <main className="shell"><Nav/><p>Cargando…</p></main>;
  return <main className="shell"><Nav/><div className="pagehead"><div><p className="eyebrow">Sprint 2 · Usuario</p><h1>Mi cuenta</h1></div></div><form className="card form" onSubmit={submit}><div className="field"><label>Nombre</label><input name="name" defaultValue={user.name} required/></div><div className="field"><label>Email</label><input value={user.email} disabled/></div><hr/><h3>Cambiar contraseña</h3><p className="muted">Dejá estos campos vacíos si no querés cambiarla.</p><div className="field"><label>Contraseña actual</label><input name="current_password" type="password"/></div><div className="field"><label>Nueva contraseña</label><input name="new_password" type="password" minLength={8}/></div>{error&&<p className="error">{error}</p>}{saved&&<p className="success">Perfil actualizado.</p>}<button className="btn lime" disabled={busy}>{busy?"Guardando…":"Guardar cambios"}</button></form></main>
}
