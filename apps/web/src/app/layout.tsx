import type { Metadata } from "next";
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
        <a href="#main-content" className="sr-only rounded-control bg-primary px-4 py-3 text-on-primary focus:not-sr-only focus:fixed focus:top-4 focus:left-4">
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
