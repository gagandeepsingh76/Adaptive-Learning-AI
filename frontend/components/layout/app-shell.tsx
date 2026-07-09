"use client";

import {
  Home,
  Map,
  MessageSquare,
  Moon,
  PanelsTopLeft,
  Settings,
  Sparkles,
  Sun,
  Target,
  TrendingUp
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  ensureLearnerId,
  getThemePreference,
  setThemePreference,
  type ThemePreference
} from "@/lib/storage";
import { cn } from "@/lib/utils";

const navigation = [
  { href: "/", label: "Home", icon: Home },
  { href: "/roadmap", label: "Roadmap", icon: Map },
  { href: "/project", label: "Project", icon: Target },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/progress", label: "Progress", icon: TrendingUp },
  { href: "/settings", label: "Settings", icon: Settings }
];

const themeEventName = "adaptive-learning-theme";

function applyTheme(theme: ThemePreference) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [theme, setTheme] = React.useState<ThemePreference>("light");

  React.useEffect(() => {
    ensureLearnerId();
    const stored = getThemePreference();
    const preferred =
      stored ??
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    setTheme(preferred);
    applyTheme(preferred);
    function handleThemeEvent(event: Event) {
      const nextTheme = (event as CustomEvent<ThemePreference>).detail;
      if (nextTheme === "dark" || nextTheme === "light") {
        setTheme(nextTheme);
        applyTheme(nextTheme);
      }
    }
    window.addEventListener(themeEventName, handleThemeEvent);
    return () => window.removeEventListener(themeEventName, handleThemeEvent);
  }, []);

  function toggleTheme() {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    setThemePreference(nextTheme);
    applyTheme(nextTheme);
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-background focus:px-4 focus:py-2 focus:text-sm focus:shadow-soft"
      >
        Skip to main content
      </a>
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
        <div className="container flex min-h-16 items-center justify-between gap-4">
          <Link href="/" className="flex min-w-0 items-center gap-3 font-semibold">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="h-5 w-5" aria-hidden="true" />
            </span>
            <span className="truncate">Adaptive Learning AI</span>
          </Link>
          <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary navigation">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Button
                  key={item.href}
                  asChild
                  variant={isActive ? "secondary" : "ghost"}
                  size="sm"
                >
                  <Link href={item.href} aria-current={isActive ? "page" : undefined}>
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {item.label}
                  </Link>
                </Button>
              );
            })}
          </nav>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
            >
              {theme === "dark" ? (
                <Sun className="h-4 w-4" aria-hidden="true" />
              ) : (
                <Moon className="h-4 w-4" aria-hidden="true" />
              )}
            </Button>
          </div>
        </div>
        <nav
          className="container flex gap-1 overflow-x-auto pb-3 lg:hidden"
          aria-label="Mobile navigation"
        >
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex min-w-20 flex-col items-center gap-1 rounded-md px-3 py-2 text-xs text-muted-foreground",
                  isActive && "bg-secondary text-secondary-foreground"
                )}
                aria-current={isActive ? "page" : undefined}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>
      <main id="main-content" className="container py-8 md:py-10">
        {children}
      </main>
      <footer className="border-t">
        <div className="container flex flex-col gap-3 py-6 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between">
          <span>Adaptive roadmap, project, RAG chat, and progress tracking in one workflow.</span>
          <span className="flex items-center gap-2">
            <PanelsTopLeft className="h-4 w-4" aria-hidden="true" />
            Production-ready Next.js and FastAPI
          </span>
        </div>
      </footer>
    </div>
  );
}
