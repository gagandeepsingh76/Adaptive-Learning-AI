"use client";

import { Activity, AlertTriangle, CheckCircle2, RefreshCcw, Settings } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getApiDiagnostic, type ApiDiagnostic } from "@/lib/api-diagnostics";
import { cn } from "@/lib/utils";

interface ApiErrorCardProps {
  error: unknown;
  title: string;
  explanation: string;
  className?: string;
  onRetry?: () => void;
}

export function ApiErrorCard({
  error,
  title,
  explanation,
  className,
  onRetry
}: ApiErrorCardProps) {
  const diagnostic = getApiDiagnostic(error, title, explanation);
  const isProviderSetupIssue = Boolean(diagnostic.missingEnv);
  const actionSteps = getActionSteps(diagnostic);
  const checklistSteps = getChecklistSteps(diagnostic);
  const statusBadges = getStatusBadges(diagnostic);

  return (
    <section
      role="alert"
      className={cn(
        "rounded-lg border p-3 text-sm shadow-sm sm:p-4",
        isProviderSetupIssue
          ? "border-amber-300/90 bg-amber-50/95 text-amber-950 shadow-amber-950/5 dark:border-amber-400/30 dark:bg-amber-950/20 dark:text-amber-50"
          : "border-destructive/25 bg-destructive/5 text-foreground",
        className
      )}
    >
      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-start">
        <div
          className={cn(
            "flex h-9 w-9 shrink-0 items-center justify-center rounded-md border",
            isProviderSetupIssue
              ? "border-amber-200 bg-amber-100 text-amber-700 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-300"
              : "bg-destructive/10 text-destructive"
          )}
        >
          <AlertTriangle className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1 space-y-2.5">
          <div className="space-y-2">
            <div className="space-y-1">
              <h2
                className={cn(
                  "text-base font-semibold leading-6 sm:text-lg",
                  isProviderSetupIssue
                    ? "text-amber-950 dark:text-amber-50"
                    : "text-foreground"
                )}
              >
                {diagnostic.title}
              </h2>
              <p
                className={cn(
                  "max-w-3xl text-sm leading-5 sm:leading-6",
                  isProviderSetupIssue
                    ? "text-amber-900/90 dark:text-amber-100/80"
                    : "text-muted-foreground"
                )}
              >
                {isProviderSetupIssue ? (
                  <>
                    <span className="font-medium">The backend is running successfully.</span>{" "}
                    AI-powered features are currently unavailable because the provider has not
                    been configured.
                  </>
                ) : (
                  diagnostic.explanation
                )}
              </p>
            </div>
            <div className="max-w-full overflow-x-auto pb-0.5">
              <div className="flex w-max flex-nowrap items-center gap-1.5">
                {statusBadges.map((badge) => (
                  <Badge
                    key={badge}
                    variant="outline"
                    className={cn(
                      "whitespace-nowrap px-2 py-0 text-[11px] font-medium leading-5",
                      isProviderSetupIssue
                        ? "border-amber-300/70 bg-white/60 text-amber-900 dark:border-amber-400/25 dark:bg-amber-300/10 dark:text-amber-100"
                        : "bg-background"
                    )}
                  >
                    {badge}
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          {diagnostic.reason ? (
            <DiagnosticSection title="Reason" providerTone={isProviderSetupIssue}>
              <p>{diagnostic.reason}</p>
              {diagnostic.missingEnv ? (
                <p
                  className={cn(
                    "mt-2 w-fit rounded-md border px-2 py-1 font-mono text-[11px] leading-4",
                    isProviderSetupIssue
                      ? "border-amber-300/70 bg-white/55 text-amber-950 dark:border-amber-400/25 dark:bg-amber-300/10 dark:text-amber-100"
                      : "bg-background text-muted-foreground"
                  )}
                >
                  Missing env: {diagnostic.missingEnv}
                </p>
              ) : null}
            </DiagnosticSection>
          ) : null}

          {actionSteps.length ? (
            <DiagnosticSection title="Suggested Action" providerTone={isProviderSetupIssue}>
              <ol className="space-y-1.5">
                {actionSteps.map((step, index) => (
                  <li key={step} className="flex gap-2">
                    <span
                      className={cn(
                        "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
                        isProviderSetupIssue
                          ? "bg-amber-200 text-amber-950 dark:bg-amber-300/15 dark:text-amber-100"
                          : "bg-secondary text-secondary-foreground"
                      )}
                    >
                      {index + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </DiagnosticSection>
          ) : null}

          {checklistSteps.length ? (
            <DiagnosticSection title="Setup Checklist" providerTone={isProviderSetupIssue}>
              <div className="space-y-1.5">
                {checklistSteps.map((step) => (
                  <div key={step} className="flex gap-2">
                    <CheckCircle2
                      className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400"
                      aria-hidden="true"
                    />
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            </DiagnosticSection>
          ) : null}

          {diagnostic.requestId && !isProviderSetupIssue ? (
            <p
              className={cn(
                "break-all text-xs",
                isProviderSetupIssue
                  ? "text-amber-900/75 dark:text-amber-100/60"
                  : "text-muted-foreground"
              )}
            >
              Request ID: {diagnostic.requestId}
            </p>
          ) : null}

          <div className="flex flex-wrap gap-2 pt-1">
            {onRetry ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className={cn(
                  "shrink-0",
                  isProviderSetupIssue &&
                    "border-amber-300 bg-white/70 text-amber-950 hover:bg-amber-100 hover:text-amber-950 dark:border-amber-400/25 dark:bg-white/[0.06] dark:text-amber-50 dark:hover:bg-amber-300/10"
                )}
                onClick={onRetry}
              >
                <RefreshCcw className="h-4 w-4" aria-hidden="true" />
                Retry
              </Button>
            ) : null}
            <Button
              asChild
              variant={isProviderSetupIssue ? "default" : "secondary"}
              size="sm"
              className={cn(
                "shrink-0",
                isProviderSetupIssue &&
                  "bg-amber-950 text-white hover:bg-amber-900 dark:bg-amber-300 dark:text-amber-950 dark:hover:bg-amber-200"
              )}
            >
              <Link href="/settings">
                <Settings className="h-4 w-4" aria-hidden="true" />
                Open Setup Guide
              </Link>
            </Button>
            <Button
              asChild
              variant="outline"
              size="sm"
              className={cn(
                "shrink-0",
                isProviderSetupIssue &&
                  "border-amber-300 bg-white/70 text-amber-950 hover:bg-amber-100 hover:text-amber-950 dark:border-amber-400/25 dark:bg-white/[0.06] dark:text-amber-50 dark:hover:bg-amber-300/10"
              )}
            >
              <Link href="/settings#health-status">
                <Activity className="h-4 w-4" aria-hidden="true" />
                View Backend Health
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}

function getStatusBadges(diagnostic: ApiDiagnostic) {
  const badges: string[] = [];
  if (diagnostic.status) {
    badges.push(`HTTP ${diagnostic.status}`);
  }
  if (diagnostic.code) {
    badges.push(
      diagnostic.code === "AI_PROVIDER_UNAVAILABLE"
        ? "Provider Unavailable"
        : diagnostic.code
    );
  }
  if (diagnostic.missingEnv) {
    badges.push("Environment Missing");
  }
  return badges;
}

function getActionSteps(diagnostic: ApiDiagnostic) {
  if (diagnostic.missingEnv) {
    return [
      `Add ${diagnostic.missingEnv}.`,
      "Restart the backend.",
      "Retry this request."
    ];
  }
  return diagnostic.action ? [diagnostic.action] : [];
}

function getChecklistSteps(diagnostic: ApiDiagnostic) {
  if (diagnostic.missingEnv) {
    return [
      `Add ${diagnostic.missingEnv}`,
      "Restart backend",
      "Run health check"
    ];
  }
  return diagnostic.setupSteps ?? [];
}

function DiagnosticSection({
  title,
  providerTone,
  children
}: {
  title: string;
  providerTone: boolean;
  children: React.ReactNode;
}) {
  return (
    <section
      className={cn(
        "rounded-md border p-2.5",
        providerTone
          ? "border-amber-200/80 bg-white/65 text-amber-900 dark:border-amber-400/15 dark:bg-white/[0.04] dark:text-amber-100/85"
          : "bg-background text-muted-foreground"
      )}
    >
      <h3
        className={cn(
          "mb-1.5 text-[13px] font-semibold leading-5",
          providerTone ? "text-amber-950 dark:text-amber-50" : "text-foreground"
        )}
      >
        {title}
      </h3>
      <div className="text-[13px] leading-5 sm:text-sm sm:leading-6">{children}</div>
    </section>
  );
}
