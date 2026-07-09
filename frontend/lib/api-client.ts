import axios, {
  type AxiosAdapter,
  type AxiosError,
  type AxiosInstance,
  type AxiosResponse,
  type InternalAxiosRequestConfig
} from "axios";
import { getBackendUrl, getLearnerId } from "@/lib/storage";
import type {
  ChatRequest,
  ChatResponse,
  HealthResponse,
  ProgressSummaryResponse,
  ProgressUpdateRequest,
  ProjectCreateRequest,
  ProjectResponse,
  RoadmapCreateRequest,
  RoadmapResponse
} from "@/types/api";

export const DEFAULT_API_URL = "http://localhost:8000";
const MAX_NETWORK_RETRIES = 2;

type RetriableConfig = InternalAxiosRequestConfig & {
  retryCount?: number;
};

type BackendErrorEnvelope = {
  error?: {
    code?: unknown;
    message?: unknown;
    request_id?: unknown;
    retryable?: unknown;
    details?: unknown;
  };
  detail?: unknown;
  message?: unknown;
};

interface ParsedBackendError {
  code?: string;
  message?: string;
  requestId?: string;
  retryable?: boolean;
  details?: unknown;
}

export class ApiClientError extends Error {
  status?: number;
  details?: unknown;
  code?: string;
  requestId?: string;
  retryable?: boolean;

  constructor(
    message: string,
    status?: number,
    details?: unknown,
    code?: string,
    requestId?: string,
    retryable?: boolean
  ) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.details = details;
    this.code = code;
    this.requestId = requestId;
    this.retryable = retryable;
  }
}

export interface ApiClientOptions {
  baseURL?: string;
  adapter?: AxiosAdapter;
  learnerId?: () => string | null;
}

export interface ApiClient {
  createRoadmap(payload: RoadmapCreateRequest): Promise<RoadmapResponse>;
  createProject(payload: ProjectCreateRequest): Promise<ProjectResponse>;
  chat(payload: ChatRequest): Promise<ChatResponse>;
  getProgress(roadmapId: string): Promise<ProgressSummaryResponse>;
  updateProgress(
    roadmapId: string,
    payload: ProgressUpdateRequest
  ): Promise<ProgressSummaryResponse>;
  health(): Promise<HealthResponse>;
  readiness(): Promise<HealthResponse>;
}

export function getApiBaseUrl(): string {
  return getBackendUrl(process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL);
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    globalThis.setTimeout(resolve, ms);
  });
}

function isRetriable(error: AxiosError): boolean {
  const parsed = parseBackendError(error.response?.data);
  if (parsed.retryable === false) {
    return false;
  }
  if (!error.response) {
    return true;
  }
  return error.response.status === 503 || error.response.status >= 500;
}

function parseBackendError(data: unknown): ParsedBackendError {
  if (!data || typeof data !== "object") {
    return {};
  }

  const body = data as BackendErrorEnvelope;
  const error = body.error;
  if (error && typeof error === "object") {
    return {
      code: typeof error.code === "string" ? error.code : undefined,
      message: typeof error.message === "string" ? error.message : undefined,
      requestId: typeof error.request_id === "string" ? error.request_id : undefined,
      retryable: typeof error.retryable === "boolean" ? error.retryable : undefined,
      details: error.details
    };
  }

  const candidate = body.detail ?? body.message;
  return { message: typeof candidate === "string" ? candidate : undefined, details: candidate };
}

function validationMessage(candidate: unknown): string | undefined {
  if (typeof candidate === "string") {
    return candidate;
  }

  if (Array.isArray(candidate)) {
    return candidate
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item && typeof item === "object" && "msg" in item) {
          return String(item.msg);
        }
        return "Validation error";
      })
      .join(" ");
  }

  return undefined;
}

function friendlyMessage(error: AxiosError, parsed: ParsedBackendError): string {
  const status = error.response?.status;
  const details = parsed.details;

  if (parsed.message) {
    return parsed.message;
  }

  const validation = validationMessage(details);
  if (validation) {
    return validation;
  }

  if (!status) {
    return "The backend is not reachable. Check the API URL and try again.";
  }

  if (status === 404) {
    return "That roadmap could not be found.";
  }

  if (status === 422) {
    return "Please review the highlighted fields and try again.";
  }

  if (status === 503) {
    return "The AI provider is unavailable. Open Settings for diagnostics and setup guidance.";
  }

  return "Something went wrong. Please try again.";
}

async function unwrap<T>(request: Promise<AxiosResponse<T>>): Promise<T> {
  try {
    const response = await request;
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const parsed = parseBackendError(error.response?.data);
      throw new ApiClientError(
        friendlyMessage(error, parsed),
        error.response?.status,
        parsed.details ?? error.response?.data,
        parsed.code,
        parsed.requestId,
        parsed.retryable
      );
    }
    throw new ApiClientError("Something went wrong. Please try again.");
  }
}

function buildAxios(options: ApiClientOptions = {}): AxiosInstance {
  const client = axios.create({
    baseURL: options.baseURL ?? getApiBaseUrl(),
    timeout: 90_000,
    adapter: options.adapter,
    headers: {
      "Content-Type": "application/json"
    }
  });

  client.interceptors.request.use((config) => {
    const learnerId = options.learnerId?.() ?? getLearnerId();
    if (learnerId) {
      config.headers.set("X-Learner-ID", learnerId);
    }
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const config = error.config as RetriableConfig | undefined;
      if (!config || !isRetriable(error)) {
        return Promise.reject(error);
      }

      config.retryCount = config.retryCount ?? 0;
      if (config.retryCount >= MAX_NETWORK_RETRIES) {
        return Promise.reject(error);
      }

      config.retryCount += 1;
      await delay(350 * config.retryCount);
      return client(config);
    }
  );

  return client;
}

export function createApiClient(options: ApiClientOptions = {}): ApiClient {
  const client = buildAxios(options);

  return {
    createRoadmap: (payload) => unwrap(client.post<RoadmapResponse>("/roadmap", payload)),
    createProject: (payload) => unwrap(client.post<ProjectResponse>("/project", payload)),
    chat: (payload) => unwrap(client.post<ChatResponse>("/chat", payload)),
    getProgress: (roadmapId) => unwrap(client.get<ProgressSummaryResponse>(`/progress/${roadmapId}`)),
    updateProgress: (roadmapId, payload) =>
      unwrap(client.patch<ProgressSummaryResponse>(`/progress/${roadmapId}`, payload)),
    health: () => unwrap(client.get<HealthResponse>("/health")),
    readiness: () => unwrap(client.get<HealthResponse>("/health/ready"))
  };
}

export const apiClient = createApiClient();
