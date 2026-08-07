"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import {
  Activity,
  ArrowUpRight,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Database,
  Layers,
  MessageCircle,
  MonitorPlay,
  RefreshCw,
  Server,
  Trash2,
  Wifi,
  WifiOff,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  gatewayApi,
  GatewayConfig,
  GatewayStatus,
  RequestEntry,
  formatMs,
  formatTs,
  formatUptime,
} from "@/lib/gateway-api"

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

interface GatewayStats {
  uptime_seconds: number
  total_requests: number
  successful_requests: number
  failed_requests: number
  avg_response_time_ms: number
}

function RuntimeRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex min-w-0 items-center justify-between gap-3 border-b py-2.5 last:border-0">
      <span className="shrink-0 text-xs text-muted-foreground sm:text-sm">{label}</span>
      <span className={`min-w-0 truncate text-right text-xs sm:text-sm ${mono ? "font-mono" : "font-medium"}`}>
        {value}
      </span>
    </div>
  )
}

export default function DashboardPage() {
  const [status, setStatus] = useState<GatewayStatus | null>(null)
  const [config, setConfig] = useState<GatewayConfig | null>(null)
  const [poolStatus, setPoolStatus] = useState<PoolStatus | null>(null)
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null)
  const [stats, setStats] = useState<GatewayStats | null>(null)
  const [requests, setRequests] = useState<RequestEntry[]>([])
  const [offline, setOffline] = useState(false)
  const [loading, setLoading] = useState(true)
  const [clearingMemory, setClearingMemory] = useState(false)
  const [clearingCache, setClearingCache] = useState(false)

  const load = async () => {
    try {
      const [st, cfg, gStats, recent] = await Promise.all([
        gatewayApi.status(),
        gatewayApi.config(),
        gatewayApi.stats(),
        gatewayApi.requests(),
      ])
      setStatus(st)
      setConfig(cfg)
      setStats(gStats)
      setRequests(recent.slice(0, 6))
      setOffline(false)

      const [poolRes, cacheRes] = await Promise.allSettled([
        fetch("/v1/pool/status", { cache: "no-store" }).then((response) => response.json()),
        fetch("/v1/cache/stats", { cache: "no-store" }).then((response) => response.json()),
      ])
      if (poolRes.status === "fulfilled") setPoolStatus(poolRes.value)
      if (cacheRes.status === "fulfilled") setCacheStats(cacheRes.value)
    } catch {
      setOffline(true)
    } finally {
      setLoading(false)
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

  const successRate = stats && stats.total_requests > 0
    ? Math.round((stats.successful_requests / stats.total_requests) * 100)
    : 0
  const sessionReady = !offline && Boolean(status?.logged_in)
  const provider = config?.provider ? config.provider.charAt(0).toUpperCase() + config.provider.slice(1) : "—"

  return (
    <>
      <div className="px-3 sm:px-4 lg:px-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Server className="size-4" />
              </div>
              <h1 className="truncate text-xl font-bold tracking-tight sm:text-2xl">Control room</h1>
            </div>
            <p className="mt-1 max-w-2xl text-xs text-muted-foreground sm:text-sm">
              Live operational view of the gateway, browser session and traffic.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant={offline ? "destructive" : sessionReady ? "default" : "secondary"}
              className="gap-1.5 px-2.5 py-1 text-[11px] sm:text-xs"
            >
              {offline ? <WifiOff className="size-3" /> : <Wifi className="size-3" />}
              {offline ? "API offline" : sessionReady ? "Session ready" : "Login required"}
            </Badge>
            <Button variant="ghost" size="sm" onClick={load} className="gap-1.5 text-xs sm:text-sm">
              <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
            </Button>
          </div>
        </div>
      </div>

      <div className="min-w-0 space-y-4 px-3 sm:space-y-5 sm:px-4 lg:space-y-6 lg:px-6">
        <div className="grid grid-cols-2 gap-2 sm:gap-4 xl:grid-cols-4">
          <Card>
            <CardHeader className="px-3 pb-1 pt-3 sm:px-4 sm:pt-4">
              <CardTitle className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground sm:text-xs">
                <Clock3 className="size-3" /> Uptime
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 pb-3 sm:px-4 sm:pb-4">
              <div className="text-lg font-bold sm:text-2xl">{stats ? formatUptime(stats.uptime_seconds) : "—"}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="px-3 pb-1 pt-3 sm:px-4 sm:pt-4">
              <CardTitle className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground sm:text-xs">
                <Activity className="size-3" /> Requests
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 pb-3 sm:px-4 sm:pb-4">
              <div className="text-lg font-bold sm:text-2xl">{stats ? stats.total_requests.toLocaleString() : "—"}</div>
              <p className="mt-0.5 text-[10px] text-muted-foreground sm:text-xs">{stats ? `${successRate}% success` : "Waiting for data"}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="px-3 pb-1 pt-3 sm:px-4 sm:pt-4">
              <CardTitle className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground sm:text-xs">
                <Activity className="size-3" /> Avg latency
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 pb-3 sm:px-4 sm:pb-4">
              <div className="text-lg font-bold sm:text-2xl">{stats ? formatMs(stats.avg_response_time_ms) : "—"}</div>
              <p className="mt-0.5 text-[10px] text-muted-foreground sm:text-xs">per request</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="px-3 pb-1 pt-3 sm:px-4 sm:pt-4">
              <CardTitle className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground sm:text-xs">
                <Layers className="size-3" /> Browser pool
              </CardTitle>
            </CardHeader>
            <CardContent className="px-3 pb-3 sm:px-4 sm:pb-4">
              <div className="text-lg font-bold sm:text-2xl">{poolStatus ? `${poolStatus.available}/${poolStatus.pool_size}` : "—"}</div>
              <p className="mt-0.5 text-[10px] text-muted-foreground sm:text-xs">slots available</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(17rem,0.65fr)]">
          <Card className="min-w-0">
            <CardHeader className="flex flex-row items-center justify-between gap-3 pb-3">
              <CardTitle className="flex items-center gap-2 text-sm sm:text-base">
                <Server className="size-4 text-primary" /> Gateway runtime
              </CardTitle>
              <Badge variant={offline ? "destructive" : "outline"} className="text-[10px] sm:text-xs">
                {offline ? "Unavailable" : "Connected"}
              </Badge>
            </CardHeader>
            <CardContent className="min-w-0">
              {offline ? (
                <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-muted-foreground sm:text-sm">
                  <CircleAlert className="mt-0.5 size-4 shrink-0 text-destructive" />
                  <span>The API server cannot be reached. Check the workflow before sending traffic.</span>
                </div>
              ) : (
                <div className="grid gap-x-8 sm:grid-cols-2">
                  <RuntimeRow label="Provider" value={provider} />
                  <RuntimeRow label="Model" value={poolStatus?.default_model || "—"} mono />
                  <RuntimeRow label="Browser session" value={status?.logged_in ? "Authenticated" : "Login required"} />
                  <RuntimeRow label="API endpoint" value={`:${config?.api_port ?? 8000}`} mono />
                  <RuntimeRow label="Current thread" value={status?.current_thread || "None"} mono />
                  <RuntimeRow label="Cache" value={cacheStats?.enabled ? "Enabled" : "Disabled"} />
                </div>
              )}
              <div className="mt-4 flex flex-wrap gap-2 border-t pt-4">
                <Button asChild size="sm" className="gap-1.5 text-xs sm:text-sm">
                  <Link href="/client"><MessageCircle className="size-3.5" /> Open client</Link>
                </Button>
                <Button asChild size="sm" variant="outline" className="gap-1.5 text-xs sm:text-sm">
                  <Link href="/browser"><MonitorPlay className="size-3.5" /> Manage browser</Link>
                </Button>
                <Button size="sm" variant="ghost" className="gap-1.5 text-xs sm:text-sm" onClick={handleClearMemory} disabled={clearingMemory || offline}>
                  <Trash2 className="size-3.5" /> {clearingMemory ? "Clearing…" : "Clear memory"}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="min-w-0">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm sm:text-base">
                <CheckCircle2 className="size-4 text-primary" /> Session readiness
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                ["Gateway API", !offline],
                ["Browser process", !offline && Boolean(status)],
                ["Provider session", sessionReady],
              ].map(([label, ready]) => (
                <div key={String(label)} className="flex items-center gap-2 text-xs sm:text-sm">
                  {ready ? <CheckCircle2 className="size-4 text-emerald-500" /> : <CircleAlert className="size-4 text-amber-500" />}
                  <span className={ready ? "" : "text-muted-foreground"}>{label}</span>
                  <span className="ml-auto text-[10px] uppercase tracking-wide text-muted-foreground">{ready ? "Ready" : "Action needed"}</span>
                </div>
              ))}
              <div className="mt-2 rounded-lg bg-muted/50 p-3 text-xs leading-relaxed text-muted-foreground">
                {sessionReady
                  ? "The gateway can receive requests from the client."
                  : "Open Browser to authenticate the provider session before sending a request."}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(17rem,0.65fr)]">
          <Card className="min-w-0">
            <CardHeader className="flex flex-row items-center justify-between gap-3 pb-3">
              <CardTitle className="flex items-center gap-2 text-sm sm:text-base">
                <Activity className="size-4 text-primary" /> Recent activity
              </CardTitle>
              <Button asChild variant="ghost" size="sm" className="h-7 gap-1 text-xs">
                <Link href="/requests">View all <ArrowUpRight className="size-3" /></Link>
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              {requests.length === 0 ? (
                <div className="px-4 pb-5 pt-2 text-xs text-muted-foreground sm:text-sm">No requests recorded yet.</div>
              ) : (
                <div className="divide-y">
                  {requests.map((request, index) => (
                    <div key={`${request.timestamp}-${index}`} className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 px-4 py-3 text-xs sm:grid-cols-[7rem_minmax(0,1fr)_auto_auto] sm:text-sm">
                      <span className="font-mono text-muted-foreground">{formatTs(request.timestamp)}</span>
                      <span className="truncate font-mono">{request.endpoint}</span>
                      <Badge variant={request.status === "ok" ? "default" : "destructive"} className="h-5 text-[10px]">{request.status}</Badge>
                      <span className="hidden font-mono text-muted-foreground sm:block">{formatMs(request.response_time_ms)}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="min-w-0">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm sm:text-base">
                <Database className="size-4 text-primary" /> Cache & capacity
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5">
              <RuntimeRow label="Cache status" value={cacheStats?.enabled ? "Enabled" : "Disabled"} />
              <RuntimeRow label="Cache entries" value={cacheStats ? `${cacheStats.entries_valid}/${cacheStats.entries_total}` : "—"} mono />
              <RuntimeRow label="Hit rate" value={cacheStats ? `${cacheStats.hit_rate_pct}%` : "—"} />
              <RuntimeRow label="Healthy browsers" value={poolStatus ? `${poolStatus.available}/${poolStatus.pool_size}` : "—"} mono />
              {cacheStats?.enabled && (
                <Button size="sm" variant="outline" className="mt-2 w-full gap-1.5 text-xs" onClick={handleClearCache} disabled={clearingCache || offline}>
                  <Trash2 className="size-3.5" /> {clearingCache ? "Clearing…" : "Clear cache"}
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  )
}