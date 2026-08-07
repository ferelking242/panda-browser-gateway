#!/usr/bin/env node
/**
 * Panda Browser Gateway — Extension entry point
 *
 * Responsabilités :
 *  1. Démarrer le serveur Python (uvicorn src.api.server:app)
 *  2. Émettre des événements IPC vers panda-ide (stdout JSON lines)
 *  3. Transmettre les logs Python
 *  4. Répondre aux commandes IPC reçues sur stdin
 *
 * Protocole IPC (JSON lines sur stdout) :
 *   {"event":"ready","port":8000}
 *   {"event":"log","level":"info","msg":"..."}
 *   {"event":"error","msg":"..."}
 *   {"event":"stopped","code":0}
 */

'use strict';

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const readline = require('readline');

// ── Config ────────────────────────────────────────────────────────────────────
const PROJECT_ROOT = path.resolve(__dirname, '..');
const ENV_FILE = process.env.GATEWAY_ENV_FILE
  || path.join(PROJECT_ROOT, 'android.env');
const API_PORT = parseInt(process.env.API_PORT || '8000', 10);
const PYTHON_BIN = process.env.PYTHON_BIN || findPython();

// ── Helpers ───────────────────────────────────────────────────────────────────
function ipc(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function log(level, msg) {
  ipc({ event: 'log', level, msg });
}

function findPython() {
  const candidates = [
    '/data/data/com.termux.app/files/usr/bin/python3',
    '/usr/bin/python3',
    '/usr/local/bin/python3',
    'python3',
    'python',
  ];
  for (const p of candidates) {
    try {
      if (!p.startsWith('/')) return p; // relative — trust PATH
      if (fs.existsSync(p)) return p;
    } catch (_) {}
  }
  return 'python3';
}

function loadEnv(filePath) {
  if (!fs.existsSync(filePath)) return {};
  const out = {};
  for (const line of fs.readFileSync(filePath, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq < 0) continue;
    const key = trimmed.slice(0, eq).trim();
    const val = trimmed.slice(eq + 1).trim().replace(/^['"]|['"]$/g, '');
    out[key] = val;
  }
  return out;
}

// ── Main ─────────────────────────────────────────────────────────────────────
let pythonProc = null;

function startPython() {
  const envVars = loadEnv(ENV_FILE);
  const env = { ...process.env, ...envVars };

  log('info', `Starting Python gateway with ${PYTHON_BIN}`);
  log('info', `Working dir: ${PROJECT_ROOT}`);
  log('info', `Env file: ${ENV_FILE}`);

  pythonProc = spawn(
    PYTHON_BIN,
    ['-m', 'uvicorn', 'src.api.server:app',
      '--host', env.API_HOST || '127.0.0.1',
      '--port', env.API_PORT || String(API_PORT),
      '--log-level', (env.LOG_LEVEL || 'info').toLowerCase()],
    {
      cwd: PROJECT_ROOT,
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
    }
  );

  let started = false;

  function checkReady(line) {
    if (!started && (line.includes('Application startup complete') || line.includes('Uvicorn running'))) {
      started = true;
      ipc({ event: 'ready', port: API_PORT });
    }
  }

  pythonProc.stdout.on('data', (data) => {
    for (const line of data.toString().split('\n')) {
      if (line.trim()) {
        log('info', line.trim());
        checkReady(line);
      }
    }
  });

  pythonProc.stderr.on('data', (data) => {
    for (const line of data.toString().split('\n')) {
      if (line.trim()) {
        log('info', line.trim()); // uvicorn writes to stderr normally
        checkReady(line);
      }
    }
  });

  pythonProc.on('exit', (code, signal) => {
    ipc({ event: 'stopped', code: code ?? -1, signal });
  });

  pythonProc.on('error', (err) => {
    ipc({ event: 'error', msg: `Failed to start Python: ${err.message}` });
  });
}

function stopPython() {
  if (pythonProc) {
    pythonProc.kill('SIGTERM');
    pythonProc = null;
  }
}

// ── IPC: read commands from stdin ─────────────────────────────────────────────
if (process.stdin.isTTY === false || process.env.GATEWAY_IPC === '1') {
  const rl = readline.createInterface({ input: process.stdin });
  rl.on('line', (line) => {
    try {
      const cmd = JSON.parse(line.trim());
      if (cmd.command === 'stop') {
        stopPython();
        process.exit(0);
      }
    } catch (_) {}
  });
}

// ── Graceful shutdown ─────────────────────────────────────────────────────────
process.on('SIGTERM', () => { stopPython(); process.exit(0); });
process.on('SIGINT',  () => { stopPython(); process.exit(0); });

// ── Start ─────────────────────────────────────────────────────────────────────
startPython();
