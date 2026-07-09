import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { ToastProvider } from "@/components/shared/toast-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Adaptive Learning AI",
  description:
    "A production-ready AI learning platform for roadmap generation, project recommendations, RAG chat, and progress tracking."
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning data-scroll-behavior="smooth">
      <body>
        <ToastProvider>
          <AppShell>{children}</AppShell>
        </ToastProvider>
      </body>
    </html>
  );
}
