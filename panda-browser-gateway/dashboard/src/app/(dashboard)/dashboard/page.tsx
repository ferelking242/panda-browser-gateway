"use client"

import { useEffect, useState } from "react"
import { gatewayApi, GatewayStatus, GatewayConfig, formatMs, formatUptime } from "@/lib/gateway-api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Wifi, WifiOff, Bot, Code2, Database, Server, Zap,
  RefreshCw, Trash2, Activity, Layers, ChevronRight
} from "lucide-react"

const ALL_PROVIDERS = [
  { id: "chatgpt", label: "ChatGPT", color: "bg-green-500", models: ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"] },
  { id: "claude", label: "Claude", color: "bg-orange-500", models: ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"] },
  { id: "gemini", label: "Gemini", color: "bg-blue-500", models: ["gemini-2.0-flash", "gemini-1.5-pro"] },
  { id: "deepseek", label: "DeepSeek", color: "bg-cyan-500", models: ["deepseek-r1", "deepseek-v3"] },
  { id: "grok", label: "Grok", color: "bg-slate-400", models: ["grok-3", "grok-3-mini", "grok-2"] },
  { id: "mistral", label: "Mistral", color: "bg-purple-500", models: ["mistral-large", "mistral-small", "codestral"] },
  { id: "qwen", label: "Qwen", color: "bg-rose-500", models: ["qwen-max", "qwen-plus", "qwq-32b"] },
  { id: "kimi", label: "Kimi", color: "bg-sky-500", models: ["kimi-k2", "moonshot-v1-32k", "moonshot-v1-128k"] },
]

interface PoolStatus {
  pool_size: number
  available: number
  provider: string
  default_model: string
  slots: Array<{ index: number; healthy: boolean }>
}

interface CacheStats {
  enabled: boolean
  ttl_seconds: number
  entries_total: number
  entries_valid: number
  hits: number
  misses: number
  hit_rate_pct: number
}

export default function DashboardPage() {
  const [status, setStatus] = useState<GatewayStatus | null>(null)
  const [config, setConfig] = useState<GatewayConfig | null>(null)
  const [poolStatus, setPoolStatus] = useState<PoolStatus | null>(null)
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null)
  const [stats, setStats] = useState<{ uptime_seconds: number; total_requests: number; successful_requests: number; avg_response_time_ms: number } | null>(null)
  const [offline, setOffline] = useState(false)
  const [clearingMemory, setClearingMemory] = useState(false)
  const [clearingCache, setClearingCache] = useState(false)

  const load = async () => {
    try {
      const [st, cfg, gStats] = await Promise.all([
        gatewayApi.status(),
        gatewayApi.config(),
        gatewayApi.stats(),
      ])
      setStatus(st)
      setConfig(cfg)
      setStats(gStats)
      setOffline(false)

      // Load pool and cache stats (best-effort — may not be available if gateway is down)
      const [poolRes, cacheRes] = await Promise.allSettled([
        fetch("/v1/pool/status", { cache: "no-store" }).then(r => r.json()),
        fetch("/v1/cache/stats", { cache: "no-store" }).then(r => r.json()),
      ])
      if (poolRes.status === "fulfilled") setPoolStatus(poolRes.value)
      if (cacheRes.status === "fulfilled") setCacheStats(cacheRes.value)
    } catch {
      setOffline(true)
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [])

  const handleClearMemory = async () => {
    setClearingMemory(true)
    try {
      await fetch("/v1/memory/clear", { method: "POST", cache: "no-store" })
    } finally {
      setClearingMemory(false)
    }
  }

  const handleClearCache = async () => {
    setClearingCache(true)
    try {
      await fetch("/v1/cache/clear", { method: "POST", cache: "no-store" })
      await load()
    } finally {
      setClearingCache(false)
    }
  }

  const activeProvider = config?.provider || "chatgpt"
  const providerInfo = ALL_PROVIDERS.find(p => p.id === activeProvider) || ALL_PROVIDERS[0]

  return (
    <>
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="px-4 lg:px-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xl">🐼</span>
              <h1 className="text-2xl font-bold tracking-tight">Panda Gateway</h1>
            </div>
            <p className="text-muted-foreground text-sm mt-1">OpenAI-compatible browser gateway · 8 providers</p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {!offline && status && (
              <Badge
                variant={status.logged_in ? "default" : "secondary"}
                className="flex items-center gap-1.5 px-3 py-1"
              >
                {status.logged_in
                  ? <><Wifi className="size-3" /> Browser active</>
                  : <><WifiOff className="size-3" /> Needs login</>}
              </Badge>
            )}
            {offline && (
              <Badge variant="destructive" className="flex items-center gap-1.5 px-3 py-1">
                <WifiOff className="size-3" /> API offline · start on :8000
              </Badge>
            )}
            <Button variant="ghost" size="sm" onClick={load} className="gap-1.5">
              <RefreshCw className="size-3" /> Refresh
            </Button>
          </div>
        </div>
      </div>

      <div className="px-4 lg:px-6 space-y-6">

        {/* ── KPI cards ──────────────────────────────────────── */}
        <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1.5">
                <Activity className="size-3" /> Uptime
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <div className="text-2xl font-bold">
                {stats ? formatUptime(stats.uptime_seconds) : "—"}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1.5">
                <Zap className="size-3" /> Requests
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <div className="text-2xl font-bold">
                {stats ? stats.total_requests.toLocaleString() : "—"}
              </div>
              {stats && stats.total_requests > 0 && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  {Math.round((stats.successful_requests / stats.total_requests) * 100)}% success
                </p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1.5">
                <Bot className="size-3" /> Avg Latency
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <div className="text-2xl font-bold">
                {stats ? formatMs(stats.avg_response_time_ms) : "—"}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">per request</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1.5">
                <Layers className="size-3" /> Pool
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <div className="text-2xl font-bold">
                {poolStatus ? `${poolStatus.available}/${poolStatus.pool_size}` : "—"}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">browsers free</p>
            </CardContent>
          </Card>
        </div>

        {/* ── Middle row ─────────────────────────────────────── */}
        <div className="grid gap-4 md:grid-cols-3">

          {/* Gateway status */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Server className="size-4 text-primary" /> Gateway
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5 text-sm">
              {offline ? (
                <p className="text-muted-foreground">Cannot reach API server.</p>
              ) : config ? (
                <>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Provider</span>
                    <span className="font-medium flex items-center gap-1.5">
                      <span className={`inline-block size-2 rounded-full ${providerInfo.color}`} />
                      {providerInfo.label}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Model</span>
                    <span className="font-mono text-xs">{poolStatus?.default_model || "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Pool size</span>
                    <span className="font-medium">{poolStatus?.pool_size ?? 1}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Browser</span>
                    <span className={`font-medium ${status?.logged_in ? "text-green-500" : "text-yellow-500"}`}>
                      {status?.logged_in ? "Logged in" : "Needs login"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Thread</span>
                    <span className="font-mono text-xs truncate max-w-[130px]">
                      {status?.current_thread || "none"}
                    </span>
                  </div>
                </>
              ) : (
                <p className="text-muted-foreground text-sm">Loading…</p>
              )}
              <div className="pt-1">
                <Button
                  size="sm" variant="outline" className="w-full gap-1.5 text-xs"
                  onClick={handleClearMemory} disabled={clearingMemory || offline}
                >
                  <Trash2 className="size-3" />
                  {clearingMemory ? "Clearing…" : "Clear Memory"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Cache */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Database className="size-4 text-primary" /> Cache
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5 text-sm">
              {cacheStats ? (
                <>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status</span>
                    <Badge variant={cacheStats.enabled ? "default" : "secondary"} className="text-xs">
                      {cacheStats.enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </div>
                  {cacheStats.enabled && (
                    <>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">TTL</span>
                        <span className="font-medium">{cacheStats.ttl_seconds}s</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Entries</span>
                        <span className="font-medium">{cacheStats.entries_valid} / {cacheStats.entries_total}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Hit rate</span>
                        <span className="font-medium text-green-500">{cacheStats.hit_rate_pct}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Hits / Misses</span>
                        <span className="font-medium">{cacheStats.hits} / {cacheStats.misses}</span>
                      </div>
                    </>
                  )}
                  {!cacheStats.enabled && (
                    <p className="text-xs text-muted-foreground">Set <code className="text-xs bg-muted px-1 rounded">CACHE_TTL=300</code> to enable.</p>
                  )}
                </>
              ) : (
                <p className="text-muted-foreground text-sm">Loading…</p>
              )}
              {cacheStats?.enabled && (
                <div className="pt-1">
                  <Button
                    size="sm" variant="outline" className="w-full gap-1.5 text-xs"
                    onClick={handleClearCache} disabled={clearingCache || offline}
                  >
                    <Trash2 className="size-3" />
                    {clearingCache ? "Clearing…" : "Clear Cache"}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick start */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Code2 className="size-4 text-primary" /> Quick Start
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-xs bg-muted rounded-md p-3 overflow-x-auto text-muted-foreground leading-relaxed">
{`from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="none"
)

resp = client.chat.completions.create(
    model="${providerInfo.models[0]}",
    messages=[{"role":"user",
               "content":"Hello!"}]
)
print(resp.choices[0].message.content)`}
              </pre>
            </CardContent>
          </Card>
        </div>

        {/* ── Provider grid ───────────────────────────────────── */}
        <div>
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3 flex items-center gap-2">
            <Bot className="size-4" /> Supported Providers
          </h2>
          <div className="grid gap-3 grid-cols-2 md:grid-cols-4">
            {ALL_PROVIDERS.map(p => {
              const isActive = p.id === activeProvider
              return (
                <Card key={p.id} className={`relative transition-all ${isActive ? "ring-2 ring-primary" : "opacity-80 hover:opacity-100"}`}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className={`size-2.5 rounded-full ${p.color}`} />
                        <span className="font-semibold text-sm">{p.label}</span>
                      </div>
                      {isActive && (
                        <Badge className="text-[10px] px-1.5 py-0">Active</Badge>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {p.models.slice(0, 2).map(m => (
                        <span key={m} className="text-[10px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded-sm font-mono truncate max-w-full">
                          {m}
                        </span>
                      ))}
                      {p.models.length > 2 && (
                        <span className="text-[10px] text-muted-foreground">+{p.models.length - 2} more</span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>

        {/* ── Pool slots ──────────────────────────────────────── */}
        {poolStatus && poolStatus.pool_size > 1 && (
          <div>
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3 flex items-center gap-2">
              <Layers className="size-4" /> Browser Pool
            </h2>
            <div className="flex gap-2 flex-wrap">
              {poolStatus.slots.map(slot => (
                <div
                  key={slot.index}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-md border text-sm font-medium ${
                    slot.healthy ? "border-green-500/30 bg-green-500/5 text-green-600 dark:text-green-400" : "border-red-500/30 bg-red-500/5 text-red-600 dark:text-red-400"
                  }`}
                >
                  <span className={`size-2 rounded-full ${slot.healthy ? "bg-green-500" : "bg-red-500"}`} />
                  Browser {slot.index}
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </>
  )
}
