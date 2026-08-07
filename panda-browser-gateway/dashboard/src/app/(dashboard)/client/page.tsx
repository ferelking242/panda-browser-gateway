"use client"

import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react"
import { Bot, Copy, Loader2, MessageCircle, RefreshCw, Send, Trash2, UserRound } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { gatewayApi, GatewayModel } from "@/lib/gateway-api"
import { toast } from "sonner"

type ClientMessage = {
  role: "user" | "assistant"
  content: string
  createdAt: number
}

export default function ClientPage() {
  const [models, setModels] = useState<GatewayModel[]>([])
  const [model, setModel] = useState("")
  const [messages, setMessages] = useState<ClientMessage[]>([])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [loadingModels, setLoadingModels] = useState(true)
  const [online, setOnline] = useState(false)
  const [error, setError] = useState("")
  const endRef = useRef<HTMLDivElement>(null)

  const loadModels = async () => {
    setLoadingModels(true)
    try {
      const response = await gatewayApi.models()
      const nextModels = response.data ?? []
      setModels(nextModels)
      setModel((current) => current || nextModels[0]?.id || "")
      setOnline(true)
      setError("")
    } catch {
      setOnline(false)
      setError("The gateway is not ready. Start the browser session before sending a message.")
    } finally {
      setLoadingModels(false)
    }
  }

  useEffect(() => {
    loadModels()
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, sending])

  const canSend = useMemo(() => Boolean(input.trim() && model && !sending), [input, model, sending])

  const sendMessage = async (event?: FormEvent) => {
    event?.preventDefault()
    if (!canSend) return

    const content = input.trim()
    const nextMessages = [...messages, { role: "user" as const, content, createdAt: Date.now() }]
    setMessages(nextMessages)
    setInput("")
    setSending(true)
    setError("")

    try {
      const response = await gatewayApi.chat({
        model,
        messages: nextMessages.map(({ role, content: messageContent }) => ({ role, content: messageContent })),
        stream: false,
      })
      const answer = response.choices?.[0]?.message?.content?.trim() || "The gateway returned an empty response."
      setMessages((current) => [...current, { role: "assistant", content: answer, createdAt: Date.now() }])
    } catch {
      setError("The request failed. Check the browser session and request log.")
      toast.error("Request failed")
    } finally {
      setSending(false)
    }
  }

  const handleInputKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault()
      void sendMessage()
    }
  }

  const copyMessage = async (content: string) => {
    await navigator.clipboard.writeText(content)
    toast.success("Copied")
  }

  return (
    <>
      <div className="px-3 sm:px-4 lg:px-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <MessageCircle className="size-4" />
              </div>
              <h1 className="truncate text-xl font-bold tracking-tight sm:text-2xl">Client</h1>
            </div>
            <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
              Send a real request through the active browser gateway.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={online ? "default" : "secondary"} className="gap-1.5 text-[11px] sm:text-xs">
              <span className={`size-1.5 rounded-full ${online ? "bg-emerald-400" : "bg-muted-foreground"}`} />
              {online ? "Gateway ready" : "Waiting for gateway"}
            </Badge>
            <Button variant="ghost" size="sm" onClick={loadModels} disabled={loadingModels} className="gap-1.5 text-xs sm:text-sm">
              <RefreshCw className={`size-3.5 ${loadingModels ? "animate-spin" : ""}`} /> Refresh
            </Button>
          </div>
        </div>
      </div>

      <div className="grid min-w-0 gap-4 px-3 sm:px-4 lg:grid-cols-[minmax(0,1fr)_17rem] lg:px-6">
        <Card className="flex min-h-[calc(100vh-14rem)] min-w-0 flex-col overflow-hidden">
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 border-b px-3 py-3 sm:px-5">
            <CardTitle className="flex items-center gap-2 text-sm sm:text-base">
              <Bot className="size-4 text-primary" /> Live conversation
            </CardTitle>
            <div className="flex items-center gap-2">
              <select
                aria-label="Model"
                value={model}
                onChange={(event) => setModel(event.target.value)}
                disabled={loadingModels || models.length === 0 || sending}
                className="h-8 max-w-[13rem] rounded-md border bg-background px-2 text-xs outline-none focus:ring-2 focus:ring-ring"
              >
                {models.length === 0 ? <option value="">No models</option> : models.map((item) => <option key={item.id} value={item.id}>{item.id}</option>)}
              </select>
              <Button
                aria-label="Clear conversation"
                title="Clear conversation"
                variant="ghost"
                size="icon"
                className="size-8"
                onClick={() => setMessages([])}
                disabled={messages.length === 0 || sending}
              >
                <Trash2 className="size-3.5" />
              </Button>
            </div>
          </CardHeader>

          <CardContent className="flex min-h-0 flex-1 flex-col p-0">
            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-3 sm:p-5">
              {messages.length === 0 && (
                <div className="flex min-h-[18rem] flex-col items-center justify-center px-4 text-center">
                  <div className="mb-3 flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                    <MessageCircle className="size-6" />
                  </div>
                  <h2 className="text-base font-semibold sm:text-lg">Ready when you are</h2>
                  <p className="mt-1 max-w-sm text-xs leading-relaxed text-muted-foreground sm:text-sm">
                    Your message will travel through the selected browser-backed model and appear in the request log.
                  </p>
                </div>
              )}
              {messages.map((message, index) => (
                <div key={`${message.createdAt}-${index}`} className={`flex gap-2.5 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                  {message.role === "assistant" && (
                    <div className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary"><Bot className="size-3.5" /></div>
                  )}
                  <div className={`group max-w-[88%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed sm:max-w-[75%] ${message.role === "user" ? "rounded-br-md bg-primary text-primary-foreground" : "rounded-bl-md bg-muted"}`}>
                    <div className="whitespace-pre-wrap break-words">{message.content}</div>
                    {message.role === "assistant" && (
                      <button onClick={() => copyMessage(message.content)} className="mt-2 inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground">
                        <Copy className="size-3" /> Copy
                      </button>
                    )}
                  </div>
                  {message.role === "user" && (
                    <div className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-muted"><UserRound className="size-3.5" /></div>
                  )}
                </div>
              ))}
              {sending && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <div className="flex size-7 items-center justify-center rounded-full bg-primary/10 text-primary"><Bot className="size-3.5" /></div>
                  <Loader2 className="size-4 animate-spin" /> Waiting for the browser response…
                </div>
              )}
              <div ref={endRef} />
            </div>

            <form onSubmit={sendMessage} className="border-t bg-muted/20 p-3 sm:p-4">
              {error && <p className="mb-2 text-xs text-destructive">{error}</p>}
              <div className="flex items-end gap-2">
                <Textarea
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={handleInputKeyDown}
                  placeholder="Write a message…"
                  disabled={!online || sending}
                  className="min-h-[4.5rem] resize-none bg-background text-sm"
                />
                <Button type="submit" size="icon" className="size-10 shrink-0" disabled={!canSend || !online} aria-label="Send message">
                  {sending ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                </Button>
              </div>
              <p className="mt-2 text-[10px] text-muted-foreground">Ctrl/⌘ + Enter to send · Model: <span className="font-mono">{model || "—"}</span></p>
            </form>
          </CardContent>
        </Card>

        <Card className="h-fit min-w-0">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm sm:text-base">Run context</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs sm:text-sm">
            <div className="rounded-lg border bg-muted/30 p-3">
              <p className="text-muted-foreground">Transport</p>
              <p className="mt-1 font-medium">OpenAI-compatible API</p>
            </div>
            <div className="rounded-lg border bg-muted/30 p-3">
              <p className="text-muted-foreground">Mode</p>
              <p className="mt-1 font-medium">Browser-backed session</p>
            </div>
            <div className="rounded-lg border bg-muted/30 p-3">
              <p className="text-muted-foreground">Observability</p>
              <p className="mt-1 font-medium">Every request appears in Requests</p>
            </div>
            <Button asChild variant="outline" size="sm" className="w-full gap-1.5 text-xs">
              <a href="/requests"><RefreshCw className="size-3.5" /> Open request log</a>
            </Button>
          </CardContent>
        </Card>
      </div>
    </>
  )
}