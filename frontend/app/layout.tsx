import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { SWRProvider } from "@/components/SWRProvider";

export const metadata: Metadata = {
  title: "Nicks Naks",
  description: "Sports card business dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full flex bg-slate-950 text-slate-100 antialiased font-sans">
        <SWRProvider>
          <Sidebar />
          <main className="flex-1 overflow-auto">{children}</main>
        </SWRProvider>
      </body>
    </html>
  );
}
