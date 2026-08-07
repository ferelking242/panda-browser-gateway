"use client"

import { useEffect, useState } from "react"
import { gatewayApi, GatewayConfig, patchConfig } from "@/lib/gateway-api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Settings, Save, Bot, Timer, Brain, Activity, Lock, RefreshCw, Eye, EyeOff, Copy, Check } from "lucide-react"
import { toast } from "sonner"

function Row({
  label,
  description,
  children,
}: {
  label: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="min-w-0">
        <Label className="text-sm">{label}</Label>
        {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  )
}

export default function ConfigPage() {
  const [config, setConfig] = useState<GatewayConfig | null>(null)
  const [apiToken, setApiToken] = useState("")
  const [generatedToken, setGeneratedToken] = useState("")
  const [showToken, setShowToken] = useState(false)
  const [copiedToken, setCopiedToken] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    gatewayApi
      .config()
      .then(setConfig)
      .catch(() => toast.error("Cannot reach API server on :8000"))
  }, [])

  const set = (patch: Partial<GatewayConfig>) =>
    setConfig((c) => (c ? { ...c, ...patch } : c))

  const generateToken = async () => {
    setGenerating(true)
    try {
      const res = await gatewayApi.generateToken()
      if (res.ok) {
        setGeneratedToken(res.token)
        setApiToken(res.token)
        setShowToken(true)
        setConfig(c => c ? { ...c, api_token_set: true } : c)
        toast.success("Token généré et activé")
      }
    } catch {
      toast.error("Erreur génération token")
    } finally { setGenerating(false) }
  }

  const copyToken = async () => {
    const t = generatedToken || apiToken
    if (!t) return
    await navigator.clipboard.writeText(t)
    setCopiedToken(true)
    setTimeout(() => setCopiedToken(false), 2000)
  }

  const save = async () => {
    if (!config) return
    setSaving(true)
    try {
      const payload: Partial<GatewayConfig & { api_token?: string }> = { ...config }
      if (apiToken.trim()) payload.api_token = apiToken.trim()
      const updated = await patchConfig(payload)
      setConfig(updated)
      setApiToken("")
      toast.success("Configuration saved")
    } catch {
      toast.error("Failed to save config")
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <div className="px-4 lg:px-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Configuration</h1>
            <p className="text-muted-foreground text-sm mt-1">
              Runtime settings · changes apply immediately without restart
            </p>
          </div>
          <Button onClick={save} disabled={saving || !config} size="sm">
            <Save className="size-3.5 mr-1.5" />
            {saving ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>

      {!config ? (
        <div className="px-4 lg:px-6 text-muted-foreground text-sm">Loading…</div>
      ) : (
        <div className="px-4 lg:px-6 space-y-4">

          {/* Provider */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Bot className="size-4 text-primary" /> Provider
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <Row label="AI Provider" description="Which browser-based AI to use as backend">
                <Select
                  value={config.provider}
                  onValueChange={(v) => set({ provider: v })}
                >
                  <SelectTrigger className="w-36">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="chatgpt">
                      <span className="flex items-center gap-2">ChatGPT</span>
                    </SelectItem>
                    <SelectItem value="claude">
                      <span className="flex items-center gap-2">Claude</span>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </Row>

              <Row label="Headless Browser" description="Run without a visible window (login won't work)">
                <Switch
                  checked={config.headless}
                  onCheckedChange={(v) => set({ headless: v })}
                />
              </Row>

              <Row label="Slow Motion" description="Delay between browser actions in ms (25 = realistic)">
                <Input
                  type="number"
                  className="w-24 text-right"
                  value={config.slow_mo}
                  onChange={(e) => set({ slow_mo: parseInt(e.target.value) || 0 })}
                  min={0}
                  max={2000}
                />
              </Row>
            </CardContent>
          </Card>

          {/* Rate & Timeouts */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Timer className="size-4 text-primary" /> Rate & Timeouts
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <Row label="Rate Limit" description="Minimum seconds between requests">
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    className="w-20 text-right"
                    value={config.rate_limit_seconds}
                    onChange={(e) => set({ rate_limit_seconds: parseInt(e.target.value) || 0 })}
                    min={0}
                  />
                  <span className="text-xs text-muted-foreground">s</span>
                </div>
              </Row>

              <Row label="Response Timeout" description="Max wait for a complete AI response">
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    className="w-24 text-right"
                    value={config.response_timeout_ms}
                    onChange={(e) => set({ response_timeout_ms: parseInt(e.target.value) || 0 })}
                    min={1000}
                    step={1000}
                  />
                  <span className="text-xs text-muted-foreground">ms</span>
                </div>
              </Row>

              <Row label="Selector Timeout" description="Max wait for a page element to appear">
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    className="w-24 text-right"
                    value={config.selector_timeout_ms}
                    onChange={(e) => set({ selector_timeout_ms: parseInt(e.target.value) || 0 })}
                    min={1000}
                    step={1000}
                  />
                  <span className="text-xs text-muted-foreground">ms</span>
                </div>
              </Row>

              <Row label="Poll Interval" description="How often to check if the AI has finished responding">
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    className="w-24 text-right"
                    value={config.poll_interval_ms}
                    onChange={(e) => set({ poll_interval_ms: parseInt(e.target.value) || 0 })}
                    min={50}
                    step={50}
                  />
                  <span className="text-xs text-muted-foreground">ms</span>
                </div>
              </Row>
            </CardContent>
          </Card>

          {/* Human Simulation */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Brain className="size-4 text-primary" /> Human Simulation
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <Row label="Typing Speed" description="Random delay between keystrokes (min → max ms)">
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    className="w-20 text-right"
                    value={config.typing_speed_min}
                    onChange={(e) => set({ typing_speed_min: parseInt(e.target.value) || 0 })}
                    min={0}
                  />
                  <span className="text-xs text-muted-foreground">→</span>
                  <Input
                    type="number"
                    className="w-20 text-right"
                    value={config.typing_speed_max}
                    onChange={(e) => set({ typing_speed_max: parseInt(e.target.value) || 0 })}
                    min={0}
                  />
                  <span className="text-xs text-muted-foreground">ms</span>
                </div>
              </Row>

              <Row label="Thinking Pause" description="Random pause before sending (min → max ms)">
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    className="w-20 text-right"
                    value={config.thinking_pause_min}
                    onChange={(e) => set({ thinking_pause_min: parseInt(e.target.value) || 0 })}
                    min={0}
                  />
                  <span className="text-xs text-muted-foreground">→</span>
                  <Input
                    type="number"
                    className="w-20 text-right"
                    value={config.thinking_pause_max}
                    onChange={(e) => set({ thinking_pause_max: parseInt(e.target.value) || 0 })}
                    min={0}
                  />
                  <span className="text-xs text-muted-foreground">ms</span>
                </div>
              </Row>
            </CardContent>
          </Card>

          {/* Logging */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Activity className="size-4 text-primary" /> Logging
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <Row label="Log Level" description="Minimum severity to write to log files">
                <Select
                  value={config.log_level}
                  onValueChange={(v) => set({ log_level: v })}
                >
                  <SelectTrigger className="w-36">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DEBUG">DEBUG</SelectItem>
                    <SelectItem value="INFO">INFO</SelectItem>
                    <SelectItem value="WARNING">WARNING</SelectItem>
                    <SelectItem value="ERROR">ERROR</SelectItem>
                  </SelectContent>
                </Select>
              </Row>

              <Row label="Verbose Console" description="Print INFO+ logs to stdout">
                <Switch
                  checked={config.verbose}
                  onCheckedChange={(v) => set({ verbose: v })}
                />
              </Row>
            </CardContent>
          </Card>

          {/* API Auth */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Lock className="size-4 text-primary" /> API Authentication
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <Row
                label="Clé API (Bearer Token)"
                description="Protège l'API avec un token. Vide = pas d'auth."
              >
                <div className="flex flex-col gap-2 items-end">
                  <div className="flex items-center gap-2">
                    {config.api_token_set && (
                      <Badge variant="outline" className="text-xs text-green-500 border-green-500/30">token actif</Badge>
                    )}
                    <div className="relative">
                      <Input
                        type={showToken ? "text" : "password"}
                        className="w-48 pr-8 font-mono text-xs"
                        placeholder={config.api_token_set ? "••••••••" : "Nouveau token…"}
                        value={apiToken}
                        onChange={(e) => { setApiToken(e.target.value); setGeneratedToken("") }}
                        autoComplete="new-password"
                      />
                      <button
                        type="button"
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        onClick={() => setShowToken(v => !v)}
                      >
                        {showToken ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                      </button>
                    </div>
                    <Button variant="outline" size="icon" className="size-9 shrink-0" onClick={copyToken} title="Copier le token" disabled={!apiToken && !generatedToken}>
                      {copiedToken ? <Check className="size-4 text-green-500" /> : <Copy className="size-4" />}
                    </Button>
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="gap-2 w-full"
                    onClick={generateToken}
                    disabled={generating}
                  >
                    <RefreshCw className={`size-3.5 ${generating ? "animate-spin" : ""}`} />
                    {generating ? "Génération…" : "Générer une nouvelle clé API"}
                  </Button>
                  {generatedToken && (
                    <div className="w-full rounded border border-green-500/30 bg-green-500/5 px-3 py-2 text-xs font-mono text-green-400 break-all">
                      {generatedToken}
                    </div>
                  )}
                </div>
              </Row>

              <Row label="API Host" description="Address the gateway binds to">
                <Input
                  className="w-36 font-mono text-sm"
                  value={config.api_host}
                  readOnly
                  disabled
                />
              </Row>

              <Row label="API Port" description="Port the gateway listens on">
                <Input
                  className="w-24 font-mono text-sm text-right"
                  value={config.api_port}
                  readOnly
                  disabled
                />
              </Row>
            </CardContent>
          </Card>

        </div>
      )}
    </>
  )
}
