import type { Metadata } from "next";
import { Providers } from "./providers";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "Reactive Training",
  description: "AI-powered training analysis and coaching",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        <Providers>
          <div className="flex min-h-screen">
            {/* Sidebar */}
            <aside className="w-64 bg-gray-900 border-r border-gray-800 p-4 hidden md:block">
              <div className="mb-8">
                <h1 className="text-xl font-bold text-teal-400">
                  Reactive Training
                </h1>
                <p className="text-sm text-gray-500">AI-Powered Coach</p>
              </div>
              <nav className="space-y-2">
                <NavLink href="/">Dashboard</NavLink>
                <NavLink href="/workouts">Workouts</NavLink>
                <NavLink href="/plans">Training Plans</NavLink>
                <NavLink href="/goals">Goals</NavLink>
                <NavLink href="/design">Workout Designer</NavLink>
              </nav>
            </aside>

            {/* Main content */}
            <main className="flex-1 p-6">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}

function NavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      className="block px-4 py-2 rounded-lg text-gray-300 hover:bg-gray-800 hover:text-teal-400 transition-colors"
    >
      {children}
    </a>
  );
}
