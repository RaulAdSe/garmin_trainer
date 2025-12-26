import type { Metadata, Viewport } from "next";
import { Providers } from "./providers";
import { Navigation } from "@/components/ui/Navigation";
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

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-gray-950 text-gray-100 min-h-screen antialiased">
        <Providers>
          <div className="flex min-h-screen flex-col md:flex-row">
            <Navigation />
            {/* Main content */}
            <main className="flex-1 p-4 sm:p-6 lg:p-8 pb-20 md:pb-8 overflow-x-hidden">
              <div className="max-w-7xl mx-auto">
                {children}
              </div>
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
