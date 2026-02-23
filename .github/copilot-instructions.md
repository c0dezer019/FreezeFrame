# FreezeFrame – Copilot Instructions

## What This Is

FreezeFrame is a **ComfyUI custom node extension** that adds pausable sampler nodes. It wraps ComfyUI's standard KSampler API, injecting a per-step callback that polls a shared `PAUSE_STATE` dict. A frontend JS extension adds PAUSE/RESUME buttons to each node in the LiteGraph canvas UI.

## Architecture

| File | Role |
|---|---|
| `__init__.py` | Package entry point: registers the aiohttp API route (`POST /comfy/pause_signal`), exports `NODE_CLASS_MAPPINGS`, `NODE_DISPLAY_NAME_MAPPINGS`, `WEB_DIRECTORY` |
| `nodes.py` | Four node classes (`PSampler`, `PSamplerAdvanced`, `PSamplerCustom`, `PSamplerCustomAdvanced`) |
| `shared.py` | Global `PAUSE_STATE` dict + `state_lock` (threading.Lock) shared between the async API handler and the synchronous sampler callback |
| `js/pausing_bridge.js` | ComfyUI frontend extension — injects PAUSE/RESUME widgets into each node via `app.registerExtension` |

**Data flow:** Button click → `api.fetchApi("/comfy/pause_signal")` → aiohttp route in `__init__.py` → writes `PAUSE_STATE["command"]` under `state_lock` → `intercept_callback` in `nodes.py` polls the state every 0.1 s and busy-waits while `"PAUSE"`.

## ComfyUI Node Conventions

Every node class must define:
- `INPUT_TYPES(s)` – classmethod returning a dict with `"required"` (and optionally `"optional"`) keys
- `RETURN_TYPES` – tuple of type strings (e.g. `("LATENT",)`)
- `FUNCTION` – string naming the method ComfyUI will call
- `CATEGORY` – display category in the node menu (all nodes here use `"ComfyPause"`)
- The execution method named by `FUNCTION`

`NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` in `__init__.py` must be kept in sync with any new or renamed node classes. `WEB_DIRECTORY = "./js"` tells ComfyUI to serve files from the `js/` folder.

## Pause Mechanism Pattern

All four nodes use the same `intercept_callback` pattern — wrap the preview callback then poll `PAUSE_STATE`:

```python
def intercept_callback(step, x0, x, total_steps):
    if preview_callback: preview_callback(step, x0, x, total_steps)
    if PAUSE_STATE.get("command") == "PAUSE":
        while PAUSE_STATE.get("command") == "PAUSE":
            time.sleep(0.1)
```

Reading `PAUSE_STATE` without the lock is intentional — CPython's GIL makes dict reads safe; the lock is only needed when writing.

## Frontend (LiteGraph) Conventions

- LiteGraph renders on a `<canvas>` — CSS margins don't apply. Use the **ghost widget** trick to create vertical spacing:
  ```js
  const w = this.addWidget("label", "", "");
  w.computeSize = () => [0, height];
  ```
- Buttons are added via `this.addWidget("button", label, null, callback)`.
- Use `api.fetchApi(path, options)` (from `../../scripts/api.js`) for backend calls, not `fetch`.
- Extend `nodeType.prototype.onNodeCreated` (not override) — always call the original first.

## Linting

```bash
ruff check .        # lint
ruff check . --fix  # auto-fix
```

Ruff is the only configured linter (`.ruff_cache` is present; no `pyproject.toml` ruff config section, so defaults apply).

## Installation / Runtime

This package is not pip-installed. It runs by being placed inside `ComfyUI/custom_nodes/`. There is no standalone test suite — testing requires a running ComfyUI instance.
