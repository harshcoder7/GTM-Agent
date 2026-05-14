import "./globals.css";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "GTM Agent",
  description: "Personalised outreach pipeline — 6 agents, one human gate.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans">
        <div className="flex min-h-screen">
          <aside className="w-56 border-r border-white/10 p-5 sticky top-0 h-screen">
            <div className="flex items-center gap-2 mb-8">
              <div className="w-7 h-7 rounded brand-gradient" />
              <div className="font-semibold tracking-tight">GTM Agent</div>
            </div>
            <nav className="flex flex-col gap-1 text-sm">
              <NavLink href="/">New run</NavLink>
              <NavLink href="/dashboard">Dashboard</NavLink>
              <NavLink href="/brain">Company brain</NavLink>
              <NavLink href="/settings">Settings</NavLink>
            </nav>
            <div className="mt-10 text-[11px] text-white/40 leading-relaxed">
              6 agents · 1 human gate<br/>Gmail draft on approval
            </div>
          </aside>
          <main className="flex-1 p-8 max-w-[1600px]">{children}</main>
        </div>
      </body>
    </html>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} prefetch
      className="px-3 py-2 rounded-md text-white/70 hover:bg-white/5 hover:text-white transition">
      {children}
    </Link>
  );
}
