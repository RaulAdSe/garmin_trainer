import type { Metadata, Viewport } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "Reactive Training",
  description: "AI-powered training analysis and coaching",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#0d9488",
};

// Root layout - serves as the base for all pages
// The actual <html> and <body> tags are rendered in [locale]/layout.tsx
// to properly set the lang attribute based on the current locale.
// This layout just passes children through.
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
