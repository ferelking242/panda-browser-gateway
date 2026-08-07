/**
 * Custom Next.js server — proxies /vnc/* (HTTP + WebSocket) to noVNC on :6080.
 * This lets the noVNC iframe live inside the dashboard without exposing port 6080.
 */

const { createServer } = require('http')
const { parse }        = require('url')           // Next.js handle() requires url.parse objects
const fs               = require('fs')
const path             = require('path')
const next             = require('next')
const httpProxy        = require('http-proxy')

const dev    = process.env.NODE_ENV !== 'production'
const port   = parseInt(process.env.PORT || '5000', 10)
const API_HTTP = 'http://127.0.0.1:8000'
const VNC_HTTP = 'http://localhost:6080'
const VNC_WS   = 'ws://localhost:6080'

function loadApiToken() {
  if (process.env.API_TOKEN !== undefined) return process.env.API_TOKEN

  try {
    const envPath = path.resolve(__dirname, '..', '.env')
    const envFile = fs.readFileSync(envPath, 'utf8')
    const line = envFile.match(/^\s*API_TOKEN\s*=\s*(.*?)\s*$/m)
    return line ? line[1].replace(/^(['"])(.*)\1$/, '$2') : ''
  } catch {
    return ''
  }
}

const API_TOKEN = loadApiToken()

function forwardVncPath(requestUrl, websocket = false) {
  const withoutPrefix = (requestUrl || '/').replace(/^\/vnc(?=\/|$)/, '') || '/'

  // noVNC serves its UI over HTTP, but websockify expects the WebSocket
  // handshake on /websockify. Keep /vnc as the public prefix so the
  // dashboard and native VNC clients can use the same origin.
  if (websocket && (withoutPrefix === '/' || withoutPrefix === '')) {
    return '/websockify'
  }

  return withoutPrefix
}

function isApiPath(pathname) {
  return (
    pathname === '/status' ||
    pathname === '/threads' ||
    pathname === '/chat' ||
    pathname === '/healthz' ||
    pathname.startsWith('/api/') ||
    pathname.startsWith('/v1/')
  )
}

const app    = next({ dev, hostname: '0.0.0.0', port })
const handle = app.getRequestHandler()

const proxy  = httpProxy.createProxyServer({ changeOrigin: true })

proxy.on('error', (err, _req, res) => {
  const msg = `[vnc-proxy] ${err.message}`
  console.error(msg)
  if (res && typeof res.writeHead === 'function' && !res.headersSent) {
    res.writeHead(502).end(msg)
  }
})

app.prepare().then(() => {
  const server = createServer((req, res) => {
    // url.parse is intentional here — Next.js handle() requires its output shape.
    const parsedUrl = parse(req.url || '/', true)
    const { pathname = '/' } = parsedUrl

    if (pathname === '/vnc' || pathname.startsWith('/vnc/')) {
      req.url = forwardVncPath(req.url)
      proxy.web(req, res, { target: VNC_HTTP })
    } else if (isApiPath(pathname)) {
      if (API_TOKEN) {
        req.headers.authorization = `Bearer ${API_TOKEN}`
      }
      proxy.web(req, res, { target: API_HTTP })
    } else {
      handle(req, res, parsedUrl)
    }
  })

  // WebSocket upgrades — required for noVNC's VNC-over-WebSocket
  server.on('upgrade', (req, socket, head) => {
    if (req.url && (req.url === '/vnc' || req.url.startsWith('/vnc/'))) {
      req.url = forwardVncPath(req.url, true)
      proxy.ws(req, socket, head, { target: VNC_WS })
    }
  })

  server.listen(port, '0.0.0.0', () => {
    console.log(`\n> Panda Dashboard  : http://localhost:${port}`)
    console.log(`> VNC proxy        : /vnc/* → ${VNC_HTTP}\n`)
  })
})
