import type { CitationResponse, ProjectResponse, RoadmapResponse } from "@/types/api";

export const storageKeys = {
  backendUrl: "adaptive-learning.backendUrl",
  chatMessages: "adaptive-learning.chatMessages",
  conversationId: "adaptive-learning.conversationId",
  latestRoadmap: "adaptive-learning.latestRoadmap",
  latestProject: "adaptive-learning.latestProject",
  learnerId: "adaptive-learning.learnerId",
  theme: "adaptive-learning.theme"
} as const;

export type ThemePreference = "light" | "dark";

export interface StoredChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: CitationResponse[];
  followUpQuestions?: string[];
  status: "sent" | "loading" | "error";
}

function readJson<T>(key: string): T | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(key);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as T;
  } catch {
    window.localStorage.removeItem(key);
    return null;
  }
}

function writeJson<T>(key: string, value: T): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(key, JSON.stringify(value));
}

export function getStoredRoadmap(): RoadmapResponse | null {
  return readJson<RoadmapResponse>(storageKeys.latestRoadmap);
}

export function storeRoadmap(roadmap: RoadmapResponse): void {
  writeJson(storageKeys.latestRoadmap, roadmap);
}

export function getStoredProject(): ProjectResponse | null {
  return readJson<ProjectResponse>(storageKeys.latestProject);
}

export function storeProject(project: ProjectResponse): void {
  writeJson(storageKeys.latestProject, project);
}

export function getStoredChatMessages(): StoredChatMessage[] {
  return readJson<StoredChatMessage[]>(storageKeys.chatMessages) ?? [];
}

export function storeChatMessages(messages: StoredChatMessage[]): void {
  writeJson(storageKeys.chatMessages, messages);
}

export function getStoredConversationId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(storageKeys.conversationId);
}

export function setStoredConversationId(conversationId: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(storageKeys.conversationId, conversationId);
}

export function getLearnerId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(storageKeys.learnerId);
}

export function setLearnerId(learnerId: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(storageKeys.learnerId, learnerId);
}

export function ensureLearnerId(): string {
  const current = getLearnerId();
  if (current) {
    return current;
  }
  const next =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  setLearnerId(next);
  return next;
}

export function getBackendUrl(defaultUrl: string): string {
  if (typeof window === "undefined") {
    return defaultUrl;
  }
  return window.localStorage.getItem(storageKeys.backendUrl) || defaultUrl;
}

export function setBackendUrl(url: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(storageKeys.backendUrl, url.replace(/\/+$/, ""));
}

export function getThemePreference(): ThemePreference | null {
  if (typeof window === "undefined") {
    return null;
  }
  const value = window.localStorage.getItem(storageKeys.theme);
  return value === "dark" || value === "light" ? value : null;
}

export function setThemePreference(theme: ThemePreference): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(storageKeys.theme, theme);
}
