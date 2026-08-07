# Panda Browser Gateway — Roadmap

> Dernier état: August 2026  
> Langage: Python (bottleneck = browser, pas Python — on garde Python)  
> Stratégie: push GitHub après chaque feature terminée

---

## État actuel

| Composant | Status |
|---|---|
| ChatGPT browser client | ✅ Fonctionnel |
| Claude browser client | ✅ Fonctionnel |
| OpenAI-compatible API (`/v1/chat/completions`) | ✅ Fonctionnel |
| Tool calling (prompt engineering) | ✅ Fonctionnel |
| Upload fichiers/images | ✅ Fonctionnel |
| Next.js dashboard | ✅ Fonctionnel |
| VNC (accès visuel au browser) | ✅ Fonctionnel |
| Android WebView bridge | ✅ Fonctionnel |
| Multi-session (pool) | ✅ BrowserPool — N browsers en parallèle |
| Vrais noms de modèles (gpt-4o, etc.) | ✅ Catalog complet par provider |
| Sélection du modèle dans l'UI provider | ✅ select_model() sur ChatGPT + Claude |
| Streaming réseau (< 1s first token) | ❌ Polling DOM |
| Gemini AI Studio | ✅ Client + détecteur + sélecteurs |
| DeepSeek | ✅ Client + détecteur + sélecteurs |
| Grok / Mistral / Qwen / Kimi | ✅ Client + détecteur + sélecteurs |
| Pipeline multimodal (audio/image/vidéo/PDF) | ✅ Audio (Whisper) + PDF (pypdf) |
| Memory wipe | ✅ `POST /v1/memory/clear` |
| Cache réponses | ✅ TTL cache `GET /v1/cache/stats` `POST /v1/cache/clear` |
| Fallback chain entre providers | ✅ `PROVIDER_CHAIN=chatgpt,claude,gemini` |
| Streaming SSE (`stream=true`) | ✅ Word-chunk SSE, OpenAI-compatible |
| UI redesign (Panda UI) | ✅ 8 providers, pool widget, cache stats |

---

## 🔴 Sprint 1 — Fondations critiques

### [DONE ✅ → EN COURS] 1.1 Structure repo propre
- Tout à la racine (plus de sous-dossier `panda-browser-gateway/`)
- `.gitignore` propre
- ROADMAP.md présent et à jour

### 1.2 Vrais noms de modèles + sélection dans l'UI
**Problème**: `catgpt-browser` et `claude-browser` ne correspondent à aucun modèle réel. Les clients qui appellent l'API doivent deviner.

**Solution**:
- `GET /v1/models` retourne les vrais modèles disponibles : `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-o1`, `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`, `claude-3-opus-20240229`, etc.
- Quand le client demande un modèle spécifique → le gateway **clique sur le sélecteur de modèle** dans l'UI ChatGPT/Claude avant d'envoyer
- `Config.MODEL` = modèle actif, changeable via header `X-Model` ou champ `model` de la requête
- Les anciens IDs (`catgpt-browser`, `claude-browser`) restent comme alias vers le modèle par défaut

**Fichiers**:
- `src/config.py` → ajouter `MODEL`, `CHATGPT_DEFAULT_MODEL`, `CLAUDE_DEFAULT_MODEL`
- `src/chatgpt/models.py` → liste des modèles disponibles + logique de sélection UI
- `src/chatgpt/client.py` → `select_model(model_id)` clique le bon modèle
- `src/claude/client.py` → idem
- `src/api/openai_routes.py` → `/v1/models` liste les vrais modèles, parse `model` dans la requête

### 1.3 Multi-session — Pool de navigateurs
**Problème**: 1 seul navigateur = 1 requête à la fois. 8-15s par requête = blocage total.

**Solution**: Pool de N navigateurs Chromium (configurable, défaut = 3). Chaque requête prend un browser libre, exécute, le remet dans le pool.

```
[Request 1] → Browser A (libre)  → réponse en 10s
[Request 2] → Browser B (libre)  → réponse en 10s (en parallèle !)
[Request 3] → Browser C (libre)  → réponse en 10s (en parallèle !)
[Request 4] → attend qu'un browser se libère
```

**Architecture**:
- `src/browser/pool.py` → `BrowserPool` avec asyncio.Queue de `(BrowserManager, client)` paires
- `src/api/openai_routes.py` → remplace `_lock` par `pool.acquire()` / `pool.release()`
- `Config.POOL_SIZE` = nombre de browsers (défaut 3, configurable via `POOL_SIZE` env)
- Chaque browser a son propre `browser_data/` (suffixé `_0`, `_1`, `_2`)
- Health check : si un browser crash, il est remplacé automatiquement

**Fichiers**:
- `src/browser/pool.py` (nouveau)
- `src/api/server.py` → init pool au démarrage
- `src/api/openai_routes.py` → utilise pool
- `src/config.py` → `POOL_SIZE`

---

## 🟠 Sprint 2 — Vitesse + Nouveaux providers

### 2.1 Interception réseau (streaming natif)
**Problème**: Le gateway attend que le DOM soit stable (copy-button appear). First-token = 8-15s.

**Solution**: Intercepter les requêtes réseau Playwright (`page.route()` + `page.on("response")`). ChatGPT et Claude font du streaming SSE vers leurs APIs. On lit les chunks directement.

```
ChatGPT → https://chatgpt.com/backend-api/conversation (SSE stream)
Claude  → https://claude.ai/api/append_message (SSE stream)
```

**Architecture**:
- `src/browser/network_interceptor.py` → intercepte les réponses SSE, bufferise les tokens
- `ChatGPTClient.send_message()` → déclenche l'interception avant envoi, yield tokens
- `openai_routes.py` → streaming SSE vers le client API (`stream=true`)
- Fallback : si l'interception échoue (URL changée), retour au mode DOM polling

**Fichiers**:
- `src/browser/network_interceptor.py` (nouveau)
- `src/chatgpt/client.py` → intégrer intercepteur
- `src/claude/client.py` → idem
- `src/api/openai_routes.py` → activer streaming SSE quand `stream=true`

### 2.2 Gemini AI Studio (provider)
**Pourquoi en premier**: Gratuit, 1M tokens contexte, multimodal natif, aucun login complexe.

**URL**: `https://aistudio.google.com/app/prompts/new_chat`

**Architecture** (même pattern que ChatGPT/Claude):
- `src/gemini/` → `client.py`, `detector.py`, `selectors.py`
- `Config.PROVIDER = "gemini"` 
- Support modèles: `gemini-2.0-flash`, `gemini-1.5-pro`, `gemini-2.0-flash-thinking`
- Multimodal natif → pas besoin du pipeline de conversion

**Fichiers**:
- `src/gemini/` (nouveau dossier)
- `src/config.py` → ajouter `GEMINI_URL`
- `src/api/server.py` → gérer `PROVIDER=gemini`

### 2.3 DeepSeek R1 (provider)
**URL**: `https://chat.deepseek.com`

**Architecture** (même pattern):
- `src/deepseek/` → `client.py`, `detector.py`, `selectors.py`
- Support modèles: `deepseek-r1`, `deepseek-v3`
- Pas de support image natif → utilise le pipeline multimodal (Sprint 3)

### 2.4 Autres providers
Ordre d'implémentation: **Mistral** → **Grok** → **Qwen** → **Kimi**

Chacun suit le même pattern `src/{provider}/client.py + detector.py + selectors.py`.

---

## 🟡 Sprint 3 — Pipeline multimodal + Features avancées

### 3.1 Pipeline multimodal (audio/image/vidéo/PDF → texte enrichi)
**Concept**: Convertir tous les médias en texte propre AVANT d'envoyer au browser provider. Ça marche même avec DeepSeek/Qwen qui ne supportent pas les uploads.

```
Requête avec média
    │
    ▼
src/media/processor.py  (détecte le type, route)
    ├── Audio (.mp3/.wav/.ogg) → faster-whisper → transcription texte
    ├── Image (.jpg/.png/.webp) → modèle vision → description/OCR
    ├── OCR (.jpg) → PaddleOCR → texte brut
    ├── Vidéo (.mp4) → extraction frames → vision → résumé
    └── PDF (.pdf) → PyMuPDF → texte structuré
    │
    ▼
Prompt enrichi: "[TRANSCRIPT: ...]\n[IMAGE: ...]\n[PDF CONTENT: ...]\n\nQuestion: ..."
    │
    ▼
ChatGPT / Claude / Gemini (via browser)
```

**Modèles — 2 options**:

Option A — Local (CPU):
| Tâche | Modèle | RAM |
|---|---|---|
| Audio → texte | faster-whisper tiny/base | ~500MB |
| Image → description | moondream2 | ~2GB |
| OCR | PaddleOCR | ~300MB |
| PDF | PyMuPDF | négligeable |
| Vidéo | frames → moondream2 | ~2GB |

Option B — Hébergé (VPS/API):
| Tâche | Service | Config |
|---|---|---|
| Audio | Groq Whisper API | `WHISPER_API_KEY` |
| Vision | OpenAI Vision API | `VISION_API_KEY` |
| Gemma 4 tout-en-un | VPS perso | `MEDIA_MODEL_URL`, `MEDIA_MODEL_KEY` |

Config: `MEDIA_BACKEND=local|hosted` — les deux coexistent, `hosted` prioritaire si configuré.

**Fichiers**:
- `src/media/processor.py` (nouveau)
- `src/media/audio.py` (nouveau)
- `src/media/vision.py` (nouveau)
- `src/media/ocr.py` (nouveau)
- `src/media/pdf.py` (nouveau)
- `src/api/openai_routes.py` → passer par `processor.py` avant envoi au client

### 3.2 Memory Wipe
**Feature**: endpoint `POST /v1/memory/clear` + bouton dashboard.

Efface:
- Thread courant (démarre un nouveau chat)
- Compteur de messages (`_thread_message_count = 0`)
- Cache réponses (si activé)
- Optionnel: `browser_data/` complet (déconnexion)

**Fichiers**:
- `src/api/routes.py` → endpoint `/v1/memory/clear`
- dashboard → bouton "Clear Memory"

### 3.3 Cache réponses
**Feature**: Cache en mémoire (+ optionnel Redis) des réponses. TTL configurable.

- Hash de la requête (messages + model) → clé de cache
- TTL par défaut: 5 minutes
- `Config.CACHE_TTL = 300` (0 = désactivé)

**Fichiers**:
- `src/cache.py` (nouveau)
- `src/api/openai_routes.py` → check cache avant d'envoyer au browser

### 3.4 Fallback chain entre providers
**Feature**: Si le provider principal échoue (rate limit, détection bot, etc.) → essaie le suivant automatiquement.

```
Config: PROVIDER_CHAIN=chatgpt,claude,gemini
```

- Timeout configurable par provider
- Retourne l'erreur seulement si tous les providers de la chain échouent
- Log quel provider a été utilisé (`X-Provider-Used` header)

**Fichiers**:
- `src/api/openai_routes.py` → logique de fallback
- `src/config.py` → `PROVIDER_CHAIN`

### 3.5 Audio prompt (voix → texte)
**Feature**: Endpoint `POST /v1/audio/transcriptions` (OpenAI-compatible).

- Reçoit un fichier audio
- Passe par faster-whisper (ou Groq API)
- Retourne la transcription texte
- Dashboard → bouton micro pour enregistrer

**Fichiers**:
- `src/api/openai_routes.py` → `/v1/audio/transcriptions`
- `src/media/audio.py` (partagé avec Sprint 3.1)

### 3.6 Limites upload fichiers/images
**Feature**: Validation stricte avant envoi.

- Taille max par fichier (défaut: 20MB)
- Types MIME autorisés par provider
- Nombre max d'images par requête (défaut: 5 pour ChatGPT, 1 pour Claude)
- Erreur OpenAI-compatible si dépassé

---

## 🎨 Sprint 4 — UI Redesign (Panda UI)

### 4.1 Refonte complète du dashboard
**Concept**: Dashboard professionnel, dark mode natif, mobile-first.

**Pages**:
- `/` → Chat interface (style ChatGPT, mais multi-provider)
- `/settings` → Config provider, model, API key, pool size
- `/sessions` → Voir les N browsers actifs, leur état, kill/restart
- `/logs` → Logs en temps réel (WebSocket)
- `/browser` → noVNC embed (accès visuel)
- `/docs` → API docs (OpenAPI)

**Features UI**:
- Sélecteur de provider (ChatGPT / Claude / Gemini / DeepSeek / ...)
- Sélecteur de modèle (selon provider actif)
- Indicateur de santé pool (N/N browsers actifs)
- Bouton "Clear Memory"
- Upload drag-and-drop (images, PDF, audio)
- Enregistrement vocal (bouton micro)
- Mode mobile (responsive, PWA-ready)
- Thèmes: dark (défaut) + light

**Tech**: Next.js 14 + Tailwind + shadcn/ui (déjà en place) — refonte des composants

---

## 📊 Métriques cibles

| Métrique | Actuel | Cible Sprint 1 | Cible Sprint 2 |
|---|---|---|---|
| Requêtes simultanées | 1 | 3 | 3+ |
| First-token latency | 8-15s | 8-15s | < 1s |
| Providers supportés | 2 | 2 | 5+ |
| Taille fichier max | non limité | 20MB | 20MB |

---

## 🔧 Notes techniques

- **Python reste le langage** — le bottleneck c'est le browser (8-15s), pas Python
- **Pas Lightpanda** — trop immature pour les SPA React (ChatGPT, Claude)
- **Patchright** reste le moteur (Playwright fork avec anti-détection intégré)
- **Chaque browser du pool a son propre `browser_data/`** pour isoler les sessions
- **Models hébergés sur VPS** : le gateway passe juste `MEDIA_MODEL_URL` + `MEDIA_MODEL_KEY`, aucun modèle ne tourne localement sauf si `MEDIA_BACKEND=local`

---

## Changelog

| Date | Feature | Status |
|---|---|---|
| 2026-08 | Repo structure cleanup | ✅ |
| 2026-08 | ROADMAP.md | ✅ |
| 2026-08 | Vrais noms modèles + sélection UI | ✅ |
| 2026-08 | Multi-session pool (BrowserPool) | ✅ |
| 2026-08 | Gemini AI Studio provider | ✅ |
| 2026-08 | DeepSeek provider | ✅ |
| 2026-08 | Memory wipe `POST /v1/memory/clear` | ✅ |
| 2026-08 | Pool status `GET /v1/pool/status` | ✅ |
| 2026-08 | Pipeline multimodal audio (Whisper) + PDF (pypdf) | ✅ |
| 2026-08 | Cache réponses TTL (`/v1/cache/stats`, `/v1/cache/clear`) | ✅ |
| 2026-08 | Fallback chain entre providers (`PROVIDER_CHAIN`) | ✅ |
| 2026-08 | Grok / Mistral / Qwen / Kimi providers | ✅ |
| 2026-08 | Streaming SSE (stream=true) | ✅ |
| 2026-08 | UI redesign (Panda UI — 8 providers, pool, cache) | ✅ |
