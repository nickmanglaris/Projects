import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { SWRProvider } from "@/components/SWRProvider";

export const metadata: Metadata = {
  title: "Sports Card Dashboard",
  description: "Business dashboard for sports card investing",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full flex bg-gray-50 text-gray-900 antialiased font-sans">
        <SWRProvider>
          <Sidebar />
          <main className="flex-1 overflow-auto">{children}</main>
        </SWRProvider>
      </body>
    </html>
  );
}
