import "./globals.css";

export const metadata = { title: "OLIVA Intelligence", description: "Inteligencia estratégica para mejores decisiones" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="es"><body>{children}</body></html>;
}
