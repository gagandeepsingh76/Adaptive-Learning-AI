"use client";

import {
  Activity,
  Bot,
  CheckCircle2,
  Database,
  Loader2,
  Moon,
  RotateCcw,
  Save,
  Server,
  Settings,
  Sun
} from "lucide-react";
import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ApiErrorCard } from "@/components/shared/api-error-card";
import { useToast } from "@/components/shared/toast-provider";
import { DEFAULT_API_URL, createApiClient, getApiBaseUrl } from "@/lib/api-client";
import { getApiDiagnostic } from "@/lib/api-diagnostics";
import {
  getThemePreference,
  setBackendUrl,
  setThemePreference,
  type ThemePreference
} from "@/lib/storage";
import { sentenceCase } from "@/lib/utils";
import type { HealthResponse } from "@/types/api";

const APP_VERSION = process.env.NEXT_PUBLIC_APP_VERSION || "0.1.0";
const themeEventName = "adaptive-learning-theme";

function applyTheme(theme: ThemePreference) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export default function SettingsPage() {
  const { notify } = useToast();
  const [theme, setTheme] = React.useState<ThemePreference>("light");
  const [backendUrl, setBackendUrlState] = React.useState(DEFAULT_API_URL);
  const [health, setHealth] = React.useState<HealthResponse | null>(null);
  const [readiness, setReadiness] = React.useState<HealthResponse | null>(null);
  const [isChecking, setIsChecking] = React.useState(false);
  const [urlError, setUrlError] = React.useState("");
  const [healthError, setHealthError] = React.useState<unknown>(null);

  React.useEffect(() => {
    const storedTheme =
      getThemePreference() ??
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    setTheme(storedTheme);
    setBackendUrlState(getApiBaseUrl());
  }, []);

  function saveTheme(nextTheme: ThemePreference) {
    setTheme(nextTheme);
    setThemePreference(nextTheme);
    applyTheme(nextTheme);
    window.dispatchEvent(new CustomEvent<ThemePreference>(themeEventName, { detail: nextTheme }));
    notify({ tone: "success", title: "Theme updated", description: `${sentenceCase(nextTheme)} mode is active.` });
  }

  function saveBackendUrl() {
    try {
      const normalized = new URL(backendUrl).toString().replace(/\/+$/, "");
      setBackendUrl(normalized);
      setBackendUrlState(normalized);
      setUrlError("");
      notify({ tone: "success", title: "Backend URL saved", description: normalized });
    } catch {
      setUrlError("Enter a valid absolute URL, for example https://api.example.com.");
    }
  }

  function resetBackendUrl() {
    setBackendUrl(DEFAULT_API_URL);
    setBackendUrlState(DEFAULT_API_URL);
    setUrlError("");
    notify({ tone: "info", title: "Backend URL reset", description: DEFAULT_API_URL });
  }

  async function checkHealth() {
    setIsChecking(true);
    setHealthError(null);
    try {
      const client = createApiClient({ baseURL: backendUrl });
      const [healthResponse, readinessResponse] = await Promise.all([
        client.health(),
        client.readiness()
      ]);
      setHealth(healthResponse);
      setReadiness(readinessResponse);
      notify({
        tone: readinessResponse.status === "ready" ? "success" : "info",
        title: "Health check complete",
        description: `API is ${healthResponse.status}; readiness is ${readinessResponse.status}.`
      });
    } catch (error) {
      const diagnostic = getApiDiagnostic(
        error,
        "Health check failed",
        "The backend did not respond to the health check."
      );
      setHealth(null);
      setReadiness(null);
      setHealthError(error);
      notify({ tone: "error", title: diagnostic.title, description: diagnostic.explanation });
    } finally {
      setIsChecking(false);
    }
  }

  const provider = readiness?.ai_provider ?? health?.ai_provider;

  return (
    <div className="app-section">
      <div>
        <Badge variant="secondary" className="mb-3">
          <Settings className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
          Settings
        </Badge>
        <h1 className="text-3xl font-semibold md:text-4xl">Application settings</h1>
        <p className="mt-2 max-w-3xl text-muted-foreground">
          Configure the frontend runtime, inspect model metadata, and verify backend health before a
          demo or deployment handoff.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Interface</CardTitle>
            <CardDescription>Theme preferences are stored in the browser.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="theme">Theme</Label>
              <Select
                id="theme"
                value={theme}
                onChange={(event) => saveTheme(event.target.value as ThemePreference)}
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </Select>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Button type="button" variant={theme === "light" ? "default" : "outline"} onClick={() => saveTheme("light")}>
                <Sun className="h-4 w-4" aria-hidden="true" />
                Light
              </Button>
              <Button type="button" variant={theme === "dark" ? "default" : "outline"} onClick={() => saveTheme("dark")}>
                <Moon className="h-4 w-4" aria-hidden="true" />
                Dark
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Backend URL</CardTitle>
            <CardDescription>
              Used by all API calls for roadmap, project, chat, progress, and health.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="backend_url">API base URL</Label>
              <Input
                id="backend_url"
                value={backendUrl}
                onChange={(event) => setBackendUrlState(event.target.value)}
                aria-invalid={Boolean(urlError)}
              />
              {urlError ? <p className="text-sm text-destructive">{urlError}</p> : null}
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button type="button" onClick={saveBackendUrl}>
                <Save className="h-4 w-4" aria-hidden="true" />
                Save URL
              </Button>
              <Button type="button" variant="outline" onClick={resetBackendUrl}>
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Reset local
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl">AI provider setup</CardTitle>
            <CardDescription>
              Required for roadmap generation, project generation, and grounded chat.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <SetupStep
              done={provider?.configured ?? false}
              title="Configure Gemini"
              description="Set ALA_GEMINI_API_KEY in the backend environment."
            />
            <SetupStep
              done={provider?.status === "ready"}
              title="Restart backend"
              description="Restart FastAPI after changing environment variables so AI services are composed."
            />
            <SetupStep
              done={readiness?.status === "ready"}
              title="Verify readiness"
              description="Run the health check and confirm readiness is ready before demo generation."
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Model information</CardTitle>
            <CardDescription>Configured by backend environment variables and health metadata.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            <InfoBlock icon={Bot} label="AI provider" value={provider?.provider ?? "Gemini"} />
            <InfoBlock icon={Bot} label="LLM" value={provider?.llm_model ?? "Not checked"} />
            <InfoBlock icon={Database} label="Embeddings" value={provider?.embedding_model ?? "Not checked"} />
            <InfoBlock
              icon={Database}
              label="Embedding dimensions"
              value={provider?.embedding_dimensions ? `${provider.embedding_dimensions}` : "Not checked"}
            />
            <InfoBlock icon={Database} label="Vector store" value="ChromaDB" />
            <InfoBlock icon={Server} label="API framework" value="FastAPI" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Application version</CardTitle>
            <CardDescription>Frontend release metadata and backend response metadata.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <InfoBlock icon={CheckCircle2} label="Frontend version" value={APP_VERSION} />
            <InfoBlock icon={Server} label="Backend version" value={health?.version ?? "Not checked"} />
            <InfoBlock icon={Activity} label="Environment" value={health?.environment ?? "Not checked"} />
          </CardContent>
        </Card>
      </div>

      {healthError ? (
        <ApiErrorCard
          error={healthError}
          title="Health check failed"
          explanation="The backend did not respond to the health check."
          onRetry={() => void checkHealth()}
        />
      ) : null}

      <Card id="health-status">
        <CardHeader>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle className="text-xl">Health status</CardTitle>
              <CardDescription>
                Calls `/health` and `/health/ready` on the configured backend URL.
              </CardDescription>
            </div>
            <Button type="button" onClick={checkHealth} disabled={isChecking}>
              {isChecking ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Activity className="h-4 w-4" aria-hidden="true" />
              )}
              Check health
            </Button>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <HealthBlock title="Health" response={health} />
          <HealthBlock title="Readiness" response={readiness} />
        </CardContent>
      </Card>

      {provider ? <ProviderBlock response={provider} /> : null}
    </div>
  );
}

function InfoBlock({
  icon: Icon,
  label,
  value
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border bg-background p-4">
      <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
        <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
        {label}
      </div>
      <p className="font-semibold">{value}</p>
    </div>
  );
}

function HealthBlock({
  title,
  response
}: {
  title: string;
  response: HealthResponse | null;
}) {
  const isReady = response?.status === "healthy" || response?.status === "ready";
  return (
    <div className="rounded-lg border bg-background p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-semibold">{title}</h2>
        <Badge variant={response ? (isReady ? "success" : "warning") : "secondary"}>
          {response?.status ?? "Not checked"}
        </Badge>
      </div>
      <div className="space-y-2 text-sm text-muted-foreground">
        <p>Version: {response?.version ?? "Not checked"}</p>
        <p>Environment: {response?.environment ?? "Not checked"}</p>
        <p>AI provider: {response?.ai_provider?.status ?? "Not checked"}</p>
      </div>
    </div>
  );
}

function SetupStep({
  done,
  title,
  description
}: {
  done: boolean;
  title: string;
  description: string;
}) {
  return (
    <div className="flex gap-3 rounded-lg border bg-background p-4">
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-secondary">
        <CheckCircle2
          className={done ? "h-4 w-4 text-primary" : "h-4 w-4 text-muted-foreground"}
          aria-hidden="true"
        />
      </div>
      <div>
        <p className="font-medium">{title}</p>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

function ProviderBlock({ response }: { response: NonNullable<HealthResponse["ai_provider"]> }) {
  const isReady = response.status === "ready";
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <CardTitle className="text-xl">AI provider</CardTitle>
            <CardDescription>
              Gemini configuration and readiness reported by the backend.
            </CardDescription>
          </div>
          <Badge variant={isReady ? "success" : "warning"}>{sentenceCase(response.status)}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          <InfoBlock icon={Bot} label="Provider" value={sentenceCase(response.provider)} />
          <InfoBlock icon={Bot} label="LLM model" value={response.llm_model} />
          <InfoBlock icon={Database} label="Embedding model" value={response.embedding_model} />
        </div>
        {!isReady ? (
          <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            <p className="font-semibold">{response.reason ?? "AI provider is unavailable."}</p>
            <p className="mt-1">{response.action ?? "Check backend environment and restart."}</p>
            {response.missing_env ? (
              <p className="mt-2 font-mono text-xs">Missing: {response.missing_env}</p>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
