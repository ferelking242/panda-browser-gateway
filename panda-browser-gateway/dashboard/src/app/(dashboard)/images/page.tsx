"use client"

import { useEffect, useState } from "react"
import { gatewayApi, ImageEntry, formatBytes } from "@/lib/gateway-api"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Image as ImageIcon, RefreshCw, AlertCircle, Download } from "lucide-react"

export default function ImagesPage() {
  const [images, setImages] = useState<ImageEntry[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = async (quiet = false) => {
    if (!quiet) setLoading(true)
    else setRefreshing(true)
    try {
      const data = await gatewayApi.images()
      if (data.error) setError(data.error)
      else setError(null)
      setImages(data.images ?? [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Cannot reach API on :8000")
      setImages([])
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <>
      <div className="px-4 lg:px-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Images</h1>
          <p className="text-muted-foreground text-sm mt-1">DALL·E images generated via the gateway</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">{images.length} image{images.length !== 1 ? "s" : ""}</Badge>
          <Button variant="outline" size="sm" onClick={() => load(true)} disabled={refreshing}>
            <RefreshCw className={`size-3.5 mr-1.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
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
          <div className="text-muted-foreground text-sm py-8 text-center">Loading…</div>
        ) : images.length === 0 ? (
          <Card>
            <CardContent className="py-12 flex flex-col items-center gap-3 text-muted-foreground">
              <ImageIcon className="size-10 opacity-30" />
              <p className="text-sm">No images yet — use <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">/v1/images/generations</code> to generate some.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {images.map((img, i) => (
              <Card key={i} className="overflow-hidden group">
                <div className="relative aspect-square bg-muted flex items-center justify-center">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={img.url}
                    alt={img.filename}
                    className="object-cover w-full h-full"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = "none"
                    }}
                  />
                  <a
                    href={img.url}
                    download={img.filename}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-background/80 rounded-md p-1.5"
                    title="Download"
                  >
                    <Download className="size-3.5" />
                  </a>
                </div>
                <CardContent className="py-2.5 px-3">
                  <p className="text-xs font-medium truncate" title={img.filename}>{img.filename}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{formatBytes(img.size_bytes)}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
