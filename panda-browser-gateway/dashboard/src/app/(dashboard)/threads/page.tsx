"use client"

import { useEffect, useState } from "react"
import { gatewayApi, ThreadEntry, formatTs } from "@/lib/gateway-api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { MessageSquare, RefreshCw, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function ThreadsPage() {
  const [threads, setThreads] = useState<ThreadEntry[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = async (quiet = false) => {
    if (!quiet) setLoading(true)
    else setRefreshing(true)
    try {
      const data = await gatewayApi.threads()
      if (data.error) setError(data.error)
      else setError(null)
      setThreads(data.threads ?? [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Cannot reach API on :8000")
      setThreads([])
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(() => load(true), 15000)
    return () => clearInterval(id)
  }, [])

  return (
    <>
      <div className="px-4 lg:px-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Threads</h1>
          <p className="text-muted-foreground text-sm mt-1">Conversation history — auto-refresh every 15s</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => load(true)} disabled={refreshing}>
          <RefreshCw className={`size-3.5 mr-1.5 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="px-4 lg:px-6">
          <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <AlertCircle className="size-4 shrink-0" />
            {error}
          </div>
        </div>
      )}

      <div className="px-4 lg:px-6">
        {loading ? (
          <div className="text-muted-foreground text-sm py-8 text-center">Loading threads…</div>
        ) : threads.length === 0 ? (
          <Card>
            <CardContent className="py-12 flex flex-col items-center gap-3 text-muted-foreground">
              <MessageSquare className="size-10 opacity-30" />
              <p className="text-sm">No threads yet — send a message via the gateway to start a conversation.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-3">
            {threads.map((t, i) => (
              <Card key={t.id ?? i} className="hover:bg-muted/30 transition-colors">
                <CardHeader className="pb-2 pt-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <MessageSquare className="size-4 shrink-0 text-primary" />
                      <CardTitle className="text-sm font-medium truncate">
                        {t.title ?? t.id ?? `Thread ${i + 1}`}
                      </CardTitle>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {t.message_count != null && (
                        <Badge variant="secondary" className="text-xs">
                          {t.message_count} msgs
                        </Badge>
                      )}
                      {t.created_at != null && (
                        <span className="text-xs text-muted-foreground">
                          {formatTs(t.created_at)}
                        </span>
                      )}
                    </div>
                  </div>
                </CardHeader>
                {t.id && (
                  <CardContent className="pt-0 pb-3">
                    <code className="text-xs text-muted-foreground font-mono">{t.id}</code>
                  </CardContent>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
