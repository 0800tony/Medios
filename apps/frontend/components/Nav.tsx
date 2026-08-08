"use client";
import Link from "next/link";
import { logout } from "@/lib/api";
export default function Nav(){return <nav className="nav"><Link className="brand" href="/">OLIVA <span>INTELLIGENCE</span></Link><div className="navlinks"><Link href="/">Proyectos</Link><Link href="/projects/new" className="btn lime">Nuevo proyecto</Link><button className="btn ghost" onClick={logout}>Salir</button></div></nav>}
