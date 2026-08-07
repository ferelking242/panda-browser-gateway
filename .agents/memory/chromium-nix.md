---
name: Chromium on Nix
description: Runtime dependency requirement for Patchright bundled Chromium in this Replit Nix environment.
---

Patchright's bundled Chromium does not reliably start from the bare Python environment on Nix; the required shared libraries must be provided through the environment's system dependency setup.

**Why:** The gateway API initializes its browser during FastAPI startup, so a missing browser library makes the API exit even though the dashboard itself can still render.

**How to apply:** When starting a browser-backed Python service, verify its health endpoint after startup and install the missing Chromium runtime libraries before diagnosing application code.