"use client"

import { useEffect, useState } from "react"
import { TrendingUp, TrendingDown, Clock, Zap, Activity, CheckCircle2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardAction,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { gatewayApi, GatewayStats, formatUptime, formatMs } from "@/lib/gateway-api"

export function SectionCards() {
  const [stats, setStats] = useState<GatewayStats | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const s = await gatewayApi.stats()
        setStats(s)
        setError(false)
      } catch {
        setError(true)
      }
    }
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [])

  const cards = [
    {
      label: "Uptime",
      value: stats ? formatUptime(stats.uptime_seconds) : "—",
      icon: Clock,
      footer: "since last restart",
      trend: null,
    },
    {
      label: "Total Requests",
      value: stats ? stats.total_requests.toLocaleString() : "—",
      icon: Activity,
      footer: error ? "API offline" : "all time",
      trend: null,
    },
    {
      label: "Success Rate",
      value: stats ? `${stats.success_rate}%` : "—",
      icon: CheckCircle2,
      footer: stats ? `${stats.successful_requests} ok · ${stats.failed_requests} err` : "—",
      trend: stats ? (stats.success_rate >= 90 ? "up" : "down") : null,
    },
    {
      label: "Avg Response",
      value: stats ? formatMs(stats.avg_response_time_ms) : "—",
      icon: Zap,
      footer: "per request",
      trend: stats ? (stats.avg_response_time_ms < 10000 ? "up" : "down") : null,
    },
  ]

  return (
    <div className="*:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card dark:*:data-[slot=card]:bg-card *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:shadow-xs grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {cards.map((c) => (
        <Card key={c.label} className="@container/card">
          <CardHeader>
            <CardDescription>{c.label}</CardDescription>
            <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
              {c.value}
            </CardTitle>
            {c.trend && (
              <CardAction>
                <Badge variant="outline">
                  {c.trend === "up" ? <TrendingUp /> : <TrendingDown />}
                  {c.trend === "up" ? "Good" : "Check"}
                </Badge>
              </CardAction>
            )}
          </CardHeader>
          <CardFooter className="flex-col items-start gap-1.5 text-sm">
            <div className="line-clamp-1 flex gap-2 font-medium text-muted-foreground">
              <c.icon className="size-4" />
              {c.footer}
            </div>
          </CardFooter>
        </Card>
      ))}
    </div>
  )
}
