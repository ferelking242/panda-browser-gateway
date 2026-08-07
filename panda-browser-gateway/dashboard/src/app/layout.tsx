import type { Metadata } from "next";
import "./globals.css";

import { ThemeProvider } from "@/components/theme-provider";
import { SidebarConfigProvider } from "@/contexts/sidebar-context";
import { inter } from "@/lib/fonts";

export const metadata: Metadata = {
  title: "Panda Gateway",
  description: "Browser-based OpenAI-compatible gateway for ChatGPT & Claude",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} antialiased`}>
      <body className={inter.className}>
        <ThemeProvider defaultTheme="dark" storageKey="panda-theme">
          <SidebarConfigProvider>
            {children}
          </SidebarConfigProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
