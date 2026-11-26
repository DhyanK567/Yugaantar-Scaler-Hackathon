import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MediLocker — Healthcare Data Privacy Infrastructure",
  description:
    "What happens in the ward, stays in the ward. MediLocker protects patient identities while keeping every clinically valuable value intact.",
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
      <body className="min-h-screen bg-[#F4F4F2] text-[#090909] antialiased">
        {children}
      </body>
    </html>
  );
}
