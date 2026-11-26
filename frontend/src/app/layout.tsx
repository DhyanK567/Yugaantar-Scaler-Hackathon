import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MediLocker — Secure. Private. Clinically Usable.",
  description: "Healthcare Data Privacy & Secure Research Collaboration Infrastructure. Multilingual patient identity protection with clinical data preservation.",
  icons: {
    icon: "/medilocker-logo.jpg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
