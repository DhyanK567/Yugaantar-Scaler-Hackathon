import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GuptKavach | Healthcare Privacy Firewall Console",
  description: "Enterprise Control Centre for Collaborative Healthcare Privacy Intelligence",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#070D18] text-slate-100 antialiased selection:bg-cyan-500/30 selection:text-cyan-200">
        {children}
      </body>
    </html>
  );
}
