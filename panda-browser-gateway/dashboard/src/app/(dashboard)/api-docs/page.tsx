"use client"

import { ExternalLink, Terminal } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

const METHOD_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  GET: "secondary",
  POST: "default",
  PATCH: "outline",
}

const endpoints = [
  {
    method: "GET", path: "/healthz", auth: false,
    desc: "Unauthenticated ping for load-balancers / Docker.",
    response: `{ "status": "ok" }`,
  },
  {
    method: "GET", path: "/status", auth: false,
    desc: "Health check — login status and current thread.",
    response: `{ "status": "ok", "logged_in": true, "current_thread": "abc123" }`,
  },
  {
    method: "POST", path: "/chat", auth: true,
    desc: "Send a message in the current conversation.",
    body: `{ "message": "Hello!" }`,
    response: `{ "message": "Hi!", "thread_id": "abc", "response_time_ms": 3200, "images": [] }`,
  },
  {
    method: "POST", path: "/thread/new", auth: true,
    desc: "Start a fresh conversation and send the first message.",
    body: `{ "message": "Start fresh" }`,
    response: `{ "message": "...", "thread_id": "xyz", ... }`,
  },
  {
    method: "POST", path: "/thread/{id}/chat", auth: true,
    desc: "Resume a specific thread by ID.",
    body: `{ "message": "Continue…" }`,
    response: `{ "message": "...", "thread_id": "{id}", ... }`,
  },
  {
    method: "GET", path: "/threads", auth: true,
    desc: "List recent conversation threads.",
    response: `{ "threads": [{ "id": "abc", "title": "My chat", "url": "https://…" }] }`,
  },
  {
    method: "POST", path: "/v1/chat/completions", auth: true,
    desc: "OpenAI-compatible chat completions. Works with any OpenAI SDK.",
    body: `{ "model": "catgpt-browser", "messages": [{ "role": "user", "content": "Hi" }] }`,
    response: `{ "id": "chatcmpl-…", "choices": [{ "message": { "role": "assistant", "content": "…" } }] }`,
  },
  {
    method: "GET", path: "/v1/models", auth: true,
    desc: "List available models.",
    response: `{ "data": [{ "id": "catgpt-browser" }, { "id": "claude-browser" }] }`,
  },
  {
    method: "GET", path: "/api/dashboard/stats", auth: false,
    desc: "Request statistics (uptime, counts, avg latency).",
    response: `{ "uptime_seconds": 3600, "total_requests": 42, "success_rate": 97.6, ... }`,
  },
  {
    method: "GET", path: "/api/dashboard/requests", auth: false,
    desc: "Last 100 request log entries.",
    response: `[{ "timestamp": 1234567890, "endpoint": "/chat", "status": "ok", ... }]`,
  },
  {
    method: "GET", path: "/api/dashboard/config", auth: false,
    desc: "Current runtime configuration.",
    response: `{ "provider": "chatgpt", "headless": false, "rate_limit_seconds": 5, ... }`,
  },
  {
    method: "PATCH", path: "/api/dashboard/config", auth: false,
    desc: "Update runtime config without restarting the gateway.",
    body: `{ "provider": "claude", "headless": true, "rate_limit_seconds": 3 }`,
    response: `{ "provider": "claude", ... }`,
  },
]

export default function ApiDocsPage() {
  return (
    <>
      <div className="px-4 lg:px-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">API Reference</h1>
            <p className="text-muted-foreground text-sm mt-1">All endpoints exposed by CatGPT Gateway</p>
          </div>
          <Button variant="outline" size="sm" asChild>
            <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
              <ExternalLink className="size-3.5 mr-1.5" />
              Swagger UI
            </a>
          </Button>
        </div>
      </div>

      <div className="px-4 lg:px-6 space-y-3">
        <Card className="overflow-hidden">
          <CardHeader className="py-3 bg-muted/40 border-b">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Terminal className="size-4 text-primary" />
              Base URL: <code className="font-mono text-xs bg-muted px-2 py-0.5 rounded">http://localhost:8000</code>
              <span className="text-muted-foreground text-xs ml-2">
                Auth: <code className="font-mono">Authorization: Bearer &lt;API_TOKEN&gt;</code>
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 divide-y">
            {endpoints.map((ep) => (
              <div key={ep.method + ep.path} className="px-5 py-4 hover:bg-muted/30 transition-colors">
                <div className="flex items-start gap-3 flex-wrap mb-2">
                  <Badge variant={METHOD_COLORS[ep.method] ?? "outline"} className="shrink-0 font-mono text-xs mt-0.5">
                    {ep.method}
                  </Badge>
                  <code className="text-sm font-mono font-semibold">{ep.path}</code>
                  {ep.auth && (
                    <Badge variant="outline" className="text-xs text-muted-foreground">🔒 auth</Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground mb-2">{ep.desc}</p>
                {ep.body && (
                  <div className="mb-2">
                    <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Request Body</p>
                    <pre className="text-xs bg-muted rounded p-2.5 overflow-x-auto text-muted-foreground">{ep.body}</pre>
                  </div>
                )}
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Response</p>
                  <pre className="text-xs bg-muted rounded p-2.5 overflow-x-auto text-muted-foreground">{ep.response}</pre>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </>
  )
}
