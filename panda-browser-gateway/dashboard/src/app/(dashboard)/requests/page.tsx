"use client"

import { useEffect, useState } from "react"
import { gatewayApi, RequestEntry, formatTs, formatMs } from "@/lib/gateway-api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Activity, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export default function RequestsPage() {
  const [rows, setRows] = useState<RequestEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = async () => {
    try {
      const data = await gatewayApi.requests()
      setRows(data)
      setError(false)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 3000)
    return () => clearInterval(id)
  }, [])

  return (
    <>
      <div className="px-4 lg:px-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Requests</h1>
            <p className="text-muted-foreground text-sm mt-1">Last 100 requests · auto-refresh every 3s</p>
          </div>
          <Button variant="outline" size="sm" onClick={load}>
            <RefreshCw className="size-3.5 mr-1.5" />
            Refresh
          </Button>
        </div>
      </div>

      <div className="px-4 lg:px-6">
        {error && (
          <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 text-destructive px-4 py-3 text-sm">
            Cannot reach the API server.
          </div>
        )}

        <Card>
          <CardHeader className="py-4">
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className="size-4 text-primary" />
              Request Log
              <Badge variant="secondary" className="ml-auto">{rows.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center py-16 text-muted-foreground text-sm gap-2">
                <RefreshCw className="size-4 animate-spin" /> Loading…
              </div>
            ) : rows.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-2">
                <Activity className="size-8 opacity-30" />
                <p className="text-sm">No requests yet — send one to the API</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Time</TableHead>
                      <TableHead>Endpoint</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Model</TableHead>
                      <TableHead>Error</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((r, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                          {formatTs(r.timestamp)}
                        </TableCell>
                        <TableCell className="font-mono text-xs">{r.endpoint}</TableCell>
                        <TableCell>
                          <Badge variant={r.status === "ok" ? "default" : "destructive"} className="text-xs">
                            {r.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs">{formatMs(r.response_time_ms)}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{r.model || "—"}</TableCell>
                        <TableCell className="text-xs text-destructive truncate max-w-[180px]">
                          {r.error || "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  )
}
