// Typed API client for Panda Gateway backend

export interface GatewayStats {
  uptime_seconds: number;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  avg_response_time_ms: number;
  success_rate: number;
}

export interface RequestEntry {
  timestamp: number;
  endpoint: string;
  status: string;
  response_time_ms: number;
  model: string;
  error: string;
}

export interface GatewayConfig {
  // Provider
  provider: string;
  headless: boolean;
  slow_mo: number;
  // Timeouts
  rate_limit_seconds: number;
  response_timeout_ms: number;
  selector_timeout_ms: number;
  poll_interval_ms: number;
  // Human simulation
  typing_speed_min: number;
  typing_speed_max: number;
  thinking_pause_min: number;
  thinking_pause_max: number;
  // Logging
  log_level: string;
  verbose: boolean;
  // API
  api_host: string;
  api_port: number;
  api_token_set: boolean;
}

export interface GatewayStatus {
  status: string;
  logged_in: boolean;
  current_thread: string;
}

export interface LogEntry {
  line: string;
  level: string;
  timestamp: string;
  logger: string;
  message: string;
  file: string;
}

export interface ImageEntry {
  filename: string;
  size_bytes: number;
  created_at: number;
  url: string;
}

export interface ThreadEntry {
  id: string;
  title?: string;
  created_at?: number;
  message_count?: number;
  [key: string]: unknown;
}

export interface GatewayModel {
  id: string;
  object?: string;
  created?: number;
  owned_by?: string;
}

export interface ChatCompletionResponse {
  id: string;
  model: string;
  choices: Array<{
    message: {
      role: string;
      content?: string | null;
    };
  }>;
}

// ── Fetch helpers ─────────────────────────────────────────────────

async function safeJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  try { return JSON.parse(text) as T; }
  catch { throw new Error(`Non-JSON response (${res.status}): ${text.slice(0, 120)}`); }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return safeJson<T>(res);
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return safeJson<T>(res);
}

export async function patchConfig(body: Partial<GatewayConfig & { api_token?: string }>): Promise<GatewayConfig> {
  const res = await fetch("/api/dashboard/config", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const gatewayApi = {
  models: () => get<{ data: GatewayModel[] }>("/v1/models"),
  chat: (body: {
    model: string;
    messages: Array<{ role: "system" | "user" | "assistant"; content: string }>;
    temperature?: number;
    stream?: boolean;
  }) => post<ChatCompletionResponse>("/v1/chat/completions", body),
  stats: () => get<GatewayStats>("/api/dashboard/stats"),
  requests: () => get<RequestEntry[]>("/api/dashboard/requests"),
  config: () => get<GatewayConfig>("/api/dashboard/config"),
  status: () => get<GatewayStatus>("/status"),
  logs: (lines = 200, level = "all") =>
    get<{ entries: LogEntry[]; error?: string }>(`/api/dashboard/logs?lines=${lines}&level=${level}`),
  images: () => get<{ images: ImageEntry[]; error?: string }>("/api/dashboard/images"),
  threads: () => get<{ threads: ThreadEntry[]; error?: string }>("/api/dashboard/threads"),
  resetSession: () => post<{ ok: boolean; message?: string; error?: string }>("/api/dashboard/settings/reset-session"),
  exportCookies: () => get<{ ok: boolean; cookies: object[]; count: number }>("/api/dashboard/cookies"),
  importCookies: (cookies: object[]) => post<{ ok: boolean; imported: number; logged_in: boolean; message: string; error?: string }>("/api/dashboard/cookies", { cookies }),
  generateToken: () => post<{ ok: boolean; token: string }>("/api/dashboard/token/generate"),
  patchConfig,
};

// ── Formatters ────────────────────────────────────────────────────

export function formatUptime(s: number): string {
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
}

export function formatMs(ms: number): string {
  if (ms >= 60000) return `${(ms / 60000).toFixed(1)}m`;
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.round(ms)}ms`;
}

export function formatTs(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString();
}

export function formatBytes(bytes: number): string {
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}
