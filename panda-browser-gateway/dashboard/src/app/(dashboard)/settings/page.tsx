"use client"

import { useState } from "react"
import { gatewayApi } from "@/lib/gateway-api"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { AlertCircle, Trash2, PawPrint, Info } from "lucide-react"
import { toast } from "sonner"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"

export default function SettingsPage() {
  const [resetting, setResetting] = useState(false)

  const handleResetSession = async () => {
    setResetting(true)
    try {
      const result = await gatewayApi.resetSession()
      if (result.ok) {
        toast.success("Session cleared — restart the gateway to re-login")
      } else {
        toast.error(result.error ?? "Failed to reset session")
      }
    } catch {
      toast.error("Cannot reach API on :8000")
    } finally {
      setResetting(false)
    }
  }

  return (
    <>
      <div className="px-4 lg:px-6">
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">Gateway administration & session management</p>
      </div>

      <div className="px-4 lg:px-6 space-y-4">

        {/* About */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <PawPrint className="size-4 text-primary" /> About Panda Gateway
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              {[
                { label: "Project",      value: "Panda Gateway" },
                { label: "Type",         value: "Browser-based OpenAI proxy" },
                { label: "Providers",    value: "ChatGPT · Claude" },
                { label: "API Port",     value: ":8000" },
                { label: "Dashboard",    value: ":5000" },
                { label: "Protocol",     value: "OpenAI-compatible (/v1/...)" },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between rounded-md bg-muted/40 px-3 py-2">
                  <span className="text-muted-foreground">{label}</span>
                  <Badge variant="secondary" className="font-mono text-xs">{value}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Session */}
        <Card className="border-destructive/30">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2 text-destructive">
              <Trash2 className="size-4" /> Reset Browser Session
            </CardTitle>
            <CardDescription>
              Deletes all saved browser cookies and login state from <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">browser_data/</code>.
              The next gateway start will require you to log in again.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-start gap-3 rounded-md border border-yellow-500/30 bg-yellow-500/5 px-4 py-3 text-sm text-yellow-400 mb-4">
              <AlertCircle className="size-4 shrink-0 mt-0.5" />
              <span>This will log you out of ChatGPT / Claude in the gateway browser. The API Gateway workflow must be restarted after this action.</span>
            </div>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" size="sm" disabled={resetting}>
                  <Trash2 className="size-3.5 mr-1.5" />
                  {resetting ? "Clearing…" : "Clear browser session"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Clear browser session?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This deletes all login cookies from <code className="font-mono text-xs">browser_data/</code>.
                    You will need to manually log in on the next gateway start.
                    This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    onClick={handleResetSession}
                  >
                    Yes, clear session
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </CardContent>
        </Card>

        {/* Instructions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Info className="size-4 text-primary" /> How to restart the gateway
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-3">
              The gateway runs as a workflow. To restart it (e.g. after changing provider or resetting session):
            </p>
            <ol className="text-sm space-y-2 text-muted-foreground list-decimal list-inside">
              <li>Open the <strong className="text-foreground">Workflows</strong> panel in Replit (left sidebar)</li>
              <li>Find <strong className="text-foreground">API Gateway</strong> and click <strong className="text-foreground">Restart</strong></li>
              <li>A browser window will open — log in to ChatGPT or Claude</li>
              <li>Once logged in, the API becomes available on <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">:8000</code></li>
            </ol>
          </CardContent>
        </Card>

      </div>
    </>
  )
}
