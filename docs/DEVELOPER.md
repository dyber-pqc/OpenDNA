# OpenDNA Developer Guide

For people who want to contribute code, fix bugs, add features, or extend OpenDNA.

## Getting Set Up for Development

### Clone and install

```bash
git clone https://github.com/dyber-pqc/OpenDNA.git
cd OpenDNA
pip install -e ".[dev]"
cd ui && npm install && cd ..
```

### Run with auto-reload

For backend dev (Python auto-reloads on changes):
```bash
uvicorn opendna.api.server:app --reload --port 8765
```

For UI dev (Vite hot-reloads on save):
```bash
cd ui && npm run dev
```

### Run tests

```bash
# Python tests
python -m pytest tests/python/ -v

# Rust tests
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 cargo test

# UI type check
cd ui && npx tsc --noEmit

# UI build
cd ui && npm run build
```

---

## Code Style

### Python
- Use **ruff** for linting and formatting
- Type hints everywhere
- Docstrings for all public APIs
- Prefer dataclasses over plain dicts for data
- Imports: stdlib, then third-party, then local

```bash
ruff check .
ruff format .
```

### TypeScript
- Use TypeScript strict mode
- Prefer functional components with hooks
- Use the API client (`api/client.ts`) for all HTTP calls
- Use the toast hook for user-facing messages

### Rust
- Standard `rustfmt` (run `cargo fmt`)
- `cargo clippy` clean
- Use Result types for fallible functions

### CSS
- Use CSS variables from `App.css` for theming
- Component-scoped CSS files (e.g. `Sidebar.css` for `Sidebar.tsx`)
- Avoid inline styles except for dynamic values

---

## Adding a New Engine

Let's say you want to add a "ConservationAnalyzer" engine that scores sequence conservation.

### Step 1: Write the engine

`python/opendna/engines/conservation.py`:
```python
"""Conservation analysis using ESM perplexity."""

from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ConservationResult:
    scores: list[float]
    most_conserved: list[int]
    least_conserved: list[int]


def analyze_conservation(sequence: str) -> ConservationResult:
    """Compute per-residue conservation scores."""
    # ... your implementation ...
    return ConservationResult(
        scores=[0.5] * len(sequence),
        most_conserved=[],
        least_conserved=[],
    )
```

### Step 2: Add an API endpoint

In `python/opendna/api/server.py`:

```python
class ConservationRequest(BaseModel):
    sequence: str


@app.post("/v1/conservation")
async def conservation(request: ConservationRequest):
    from opendna.engines.conservation import analyze_conservation
    result = analyze_conservation(request.sequence)
    return _to_dict(result)
```

### Step 3: Add the API client method

In `ui/src/api/client.ts`:

```typescript
export interface ConservationResult {
  scores: number[];
  most_conserved: number[];
  least_conserved: number[];
}

export const conservation = (sequence: string) =>
  post<ConservationResult>("/v1/conservation", { sequence });
```

### Step 4: Wire into the UI

Add to the analysis panel, sidebar button, or command palette.

### Step 5: Add tests

`tests/python/test_conservation.py`:
```python
from opendna.engines.conservation import analyze_conservation

def test_conservation_basic():
    result = analyze_conservation("MKTVRQERLK")
    assert len(result.scores) == 10
    assert all(0 <= s <= 1 for s in result.scores)
```

### Step 6: Document it

- Add to `docs/API_REFERENCE.md`
- Add to `docs/SCIENCE.md` if it has scientific basis
- Add to `docs/COOKBOOK.md` with a recipe
- Update `docs/USER_GUIDE.md` if user-facing

---

## Adding a New UI Component

### Step 1: Create the component

`ui/src/components/MyComponent/MyComponent.tsx`:
```tsx
import "./MyComponent.css";

interface MyComponentProps {
  data: string;
  onAction: () => void;
}

export default function MyComponent({ data, onAction }: MyComponentProps) {
  return (
    <div className="my-component">
      <h3>{data}</h3>
      <button onClick={onAction}>Click me</button>
    </div>
  );
}
```

### Step 2: Style it

`ui/src/components/MyComponent/MyComponent.css`:
```css
.my-component {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  padding: 16px;
}
```

Use CSS variables from `App.css` for theming consistency.

### Step 3: Use it

In `App.tsx` or another component:
```tsx
import MyComponent from "./components/MyComponent/MyComponent";

// ...

<MyComponent data={someData} onAction={() => console.log("clicked")} />
```

---

## Adding a Keyboard Shortcut

In `App.tsx`, the `useKeyboard` hook accepts a map of shortcuts:

```tsx
useKeyboard({
  "cmd+k": () => setPaletteOpen(true),
  "cmd+shift+s": () => handleSaveProject(),
  "g": () => doSomething(),
});
```

Format: `"[cmd+][shift+]key"` where:
- `cmd` = Ctrl on Windows/Linux, Cmd on Mac
- `key` is lowercase (e.g. `"f"`, `"escape"`, `"arrowdown"`)

Single-letter shortcuts only fire when the user is **not** focused on an input/textarea (so they don't interfere with typing).

---

## Adding a Command to the Command Palette

In `App.tsx`, the `commands` array defines all palette entries:

```tsx
const commands: Command[] = useMemo(
  () => [
    {
      id: "my-action",
      group: "Action",
      label: "Do my thing",
      shortcut: "G",  // optional display
      action: () => myFunction(),
    },
    // ...
  ],
  [/* dependencies */]
);
```

Then it's automatically searchable via Ctrl+K.

---

## Database Schema (Rust + Python)

OpenDNA uses SQLite via SQLAlchemy on the Python side and rusqlite on the Rust side.

### Tables

```sql
CREATE TABLE proteins (
    id TEXT PRIMARY KEY,           -- Sequence hash (12 chars)
    name TEXT NOT NULL,
    sequence TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',    -- JSON
    created_at TEXT NOT NULL,      -- ISO 8601
    updated_at TEXT NOT NULL
);

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    job_type TEXT NOT NULL,        -- "fold" | "design" | "iterative" | "md" | etc.
    status TEXT NOT NULL DEFAULT 'pending',
    input TEXT NOT NULL,            -- JSON
    output TEXT,                    -- JSON
    progress REAL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
```

Currently most jobs are stored in-memory (lost on server restart). v0.3 will move them to SQLite for persistence.

---

## Project Workspace Format

A project is a JSON file at `~/.opendna/projects/<name>/workspace.json`:

```json
{
  "name": "my_project",
  "version": "0.2.0",
  "saved_at": "2024-01-15T12:34:56.789012+00:00",
  "structures": [
    {
      "id": "s1234",
      "label": "MKTVRQE... (10aa)",
      "sequence": "MKTVRQERLK",
      "pdbData": "ATOM ...",
      "meanConfidence": 0.87
    }
  ],
  "currentSequence": "MKTVRQERLK",
  "xp": 200
}
```

Add new fields freely — the format is forward-compatible.

---

## Testing Strategy

### Unit tests
Test individual functions in isolation. See `tests/python/test_models.py`, `test_scoring.py`, etc.

### Integration tests
Test the API endpoints with FastAPI's TestClient (TODO).

### E2E tests
Test the UI with Playwright (TODO for v0.3).

### Smoke tests
Quick check that imports work and basic functions return:
```bash
python -c "from opendna.api import server; print('OK')"
```

---

## Common Patterns

### Adding a long-running job

1. Add the work function in your engine module
2. Add a `_run_X` background runner in `server.py`
3. Add an endpoint that creates a job and submits to the executor:

```python
@app.post("/v1/my_long_job", response_model=JobResponse)
async def submit_my_job(request: MyRequest):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "running", "progress": 0.0,
        "result": None, "error": None,
        "type": "my_job", "started_at": time.time(),
    }
    asyncio.get_event_loop().run_in_executor(
        executor, _run_my_job, job_id, request.param
    )
    return JobResponse(job_id=job_id, status="running")


def _run_my_job(job_id, param):
    try:
        def on_progress(stage, frac):
            jobs[job_id]["progress"] = frac
        result = my_engine.do_work(param, on_progress=on_progress)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["result"] = _to_dict(result)
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
```

4. UI polls the job status

### Adding a new instant analysis

Just add an endpoint that computes synchronously:

```python
@app.post("/v1/my_instant_thing")
async def my_instant_thing(request: MyRequest):
    from opendna.engines.mything import analyze
    return analyze(request.input)
```

No background job needed for fast operations.

---

## Pull Request Process

1. **Fork** the repo
2. **Create a branch** from `main`: `git checkout -b feat/my-feature`
3. **Make your changes** with commits that explain why
4. **Run tests**: `python -m pytest && cd ui && npm run build`
5. **Push** to your fork
6. **Open a PR** against `dyber-pqc/OpenDNA:main`

### PR checklist
- [ ] Tests pass
- [ ] TypeScript compiles cleanly
- [ ] No new linter warnings
- [ ] Documentation updated for user-facing changes
- [ ] Commit messages are clear
- [ ] No `console.log` debug code left in
- [ ] No commented-out code blocks
- [ ] No hardcoded secrets or API keys
- [ ] No `.claude/` files committed

---

## Release Process

1. Bump version in:
   - `pyproject.toml`
   - `Cargo.toml` (workspace package)
   - `ui/package.json`
   - `python/opendna/__init__.py`
   - `python/opendna/api/server.py` (FastAPI version)
   - UI version badge in `App.tsx`
2. Update `CHANGELOG.md`
3. Run full test suite + build
4. Commit with message `release: v0.x.y`
5. Tag: `git tag -a v0.x.y -m "..."`
6. Push: `git push origin main && git push origin v0.x.y`
7. Create GitHub release with notes

---

## Areas That Need Help

### High priority
- Add real test coverage for engines
- Persistent jobs in SQLite (currently in-memory)
- Real DiffDock integration
- Multimer folding support
- Light theme polish
- Mobile-responsive UI

### Medium priority
- Plugin system for community engines
- Workflow YAML support
- Batch processing UI
- Export to figure-quality images
- BLAST search integration
- Conservation analysis

### Low priority but cool
- VR mode
- Voice input
- Real-time collaboration
- Plugin marketplace
- Mobile companion app
- Cloud GPU burst
- AR visualization

---

## Code of Conduct

Be respectful. Be inclusive. Help newcomers. No politics, no harassment, no proprietary code.

---

## License

By contributing, you agree to license your contributions under the same Apache 2.0 + Commons Clause as the rest of the project.
