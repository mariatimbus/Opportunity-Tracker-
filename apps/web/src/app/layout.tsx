import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Opportunity Tracker",
  description:
    "A space for students to discover opportunities and track their next steps.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a href="#main-content" className="sr-only rounded-control bg-primary px-4 py-3 text-on-primary focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-10">
          Skip to content
        </a>
        <div className="mx-auto flex min-h-svh max-w-6xl flex-col px-6 sm:px-10">
          <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border py-7">
            <Link href="/" className="rounded-control text-lg font-semibold tracking-tight">
              Opportunity Tracker<span className="text-primary">.</span>
            </Link>
            <nav aria-label="Main navigation">
              <Link href="/" className="rounded-control text-sm font-medium text-primary hover:text-primary-hover">
                Home
              </Link>
            </nav>
          </header>
          <main id="main-content" tabIndex={-1} className="flex flex-1 flex-col">
            {children}
          </main>
          <footer className="border-t border-border py-6 text-sm text-muted">Made for students. Built around possibility.</footer>
        </div>
      </body>
    </html>
  );
}
