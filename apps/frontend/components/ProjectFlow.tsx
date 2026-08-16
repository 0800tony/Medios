import Link from "next/link";

export default function ProjectFlow({ projectId, current, hasStrategy }: { projectId: string; current: "intake"|"brief"|"strategy"|"creative"; hasStrategy: boolean }) {
  const steps = [["intake", "1", "Pedido y encuadre", `/projects/${projectId}`], ["brief", "2", "Brief", `/projects/${projectId}/brief`], ["evidence", "3", "Evidencia", `/projects/${projectId}#evidence`], ["strategy", "4", "Strategy", `/projects/${projectId}/result`], ["creative", "5", "Creatividad", `/projects/${projectId}/creative`], ["production", "6", "Producción", `/projects/${projectId}/creative#produccion`], ["results", "7", "Resultados", `/projects/${projectId}#results`]] as const;
  return <nav className="project-flow" aria-label="Flujo de proyecto">{steps.map(([id, number, label, href]) => <Link key={id} href={href} className={`${current === id ? "current" : ""} ${(!hasStrategy && ["strategy", "creative", "production"].includes(id)) ? "pending" : ""}`}><b>{number}</b><span>{label}</span></Link>)}</nav>;
}
