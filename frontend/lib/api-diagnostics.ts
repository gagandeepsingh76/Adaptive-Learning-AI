import { ApiClientError } from "@/lib/api-client";

export interface ApiDiagnostic {
  title: string;
  explanation: string;
  reason?: string;
  action?: string;
  setupSteps?: string[];
  code?: string;
  requestId?: string;
  status?: number;
  retryable?: boolean;
  missingEnv?: string;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function readString(record: Record<string, unknown> | null, key: string): string | undefined {
  const value = record?.[key];
  return typeof value === "string" ? value : undefined;
}

function readStringArray(record: Record<string, unknown> | null, key: string): string[] | undefined {
  const value = record?.[key];
  if (!Array.isArray(value)) {
    return undefined;
  }
  const strings = value.filter((item): item is string => typeof item === "string");
  return strings.length ? strings : undefined;
}

export function getApiDiagnostic(
  error: unknown,
  fallbackTitle: string,
  fallbackExplanation: string
): ApiDiagnostic {
  if (!(error instanceof ApiClientError)) {
    return {
      title: fallbackTitle,
      explanation: fallbackExplanation,
      retryable: true
    };
  }

  const details = asRecord(error.details);
  const isProviderIssue =
    error.code === "AI_PROVIDER_UNAVAILABLE" ||
    readString(details, "missing_env") === "ALA_GEMINI_API_KEY";

  if (isProviderIssue) {
    const reason =
      readString(details, "reason") ??
      "The backend is running, but Gemini is not available for AI generation.";
    return {
      title: readString(details, "title") ?? "AI Service Not Configured",
      explanation:
        "The backend responded successfully, but AI-backed routes cannot run until the provider is configured.",
      reason,
      action:
        readString(details, "action") ??
        "Configure ALA_GEMINI_API_KEY in the backend environment, restart the backend, then retry.",
      setupSteps: readStringArray(details, "setup_steps"),
      code: error.code,
      requestId: error.requestId,
      status: error.status,
      retryable: error.retryable,
      missingEnv: readString(details, "missing_env")
    };
  }

  const titleByStatus: Record<number, string> = {
    400: "Request Could Not Be Processed",
    404: "Resource Not Found",
    422: "Check The Form Fields",
    500: "Backend Error",
    503: "Service Temporarily Unavailable"
  };

  return {
    title: error.status
      ? titleByStatus[error.status] ?? fallbackTitle
      : "Backend Unreachable",
    explanation: error.message || fallbackExplanation,
    action:
      error.status === 422
        ? "Review the highlighted fields and submit again."
        : "Retry the request. If it keeps failing, check Settings and backend logs.",
    code: error.code,
    requestId: error.requestId,
    status: error.status,
    retryable: error.retryable ?? true
  };
}
