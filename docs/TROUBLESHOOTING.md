# OpenDNA Troubleshooting

When things break, look here first.

## API Server Won't Start

### "ERROR: bind on address ('0.0.0.0', 8000): permission denied"

**Cause:** Port 8000 is reserved or in use on your system (common on Windows).

**Fix:** Use a different port:
```bash
python -c "from opendna.api.server import start_server; start_server(port=8765)"
```

You'll need to also update the UI to point to that port. Check `ui/src/api/client.ts` line 3:
```typescript
const API_BASE = "http://localhost:8765";
```

### "ModuleNotFoundError: No module named 'opendna'"

**Cause:** You haven't installed the Python package.

**Fix:**
```bash
cd /path/to/opendna
pip install -e ".[dev]"
```

### "ModuleNotFoundError: No module named 'fastapi'"

**Cause:** Missing dependencies.

**Fix:**
```bash
pip install -e ".[dev]"
```

If that fails, try:
```bash
pip install fastapi uvicorn[standard] sqlalchemy typer rich pydantic httpx pyyaml sse-starlette psutil torch transformers fair-esm biopython biotite torch-geometric
```

---

## Folding Issues

### "Torch not compiled with CUDA enabled"

**Cause:** You have an NVIDIA GPU but installed CPU-only PyTorch. The hardware detector says "use CUDA" but PyTorch can't.

**Fix option 1 - Install CUDA torch:**
```bash
pip uninstall torch -y
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

**Fix option 2 - Force CPU mode in your fold call:**
The latest version of `hardware/detect.py` already verifies torch supports the backend before recommending it. If you still hit this, restart the API server.

### Folding hangs at "Loading weights"

**Cause:** Model is downloading from HuggingFace Hub. ESMFold is ~8 GB.

**Fix:** Wait. Watch the API terminal for download progress. If it stays at 0% for >5 minutes, check your internet connection.

### Folding completes but viewer shows empty

**Cause:** UI didn't receive the result, or PDB couldn't be parsed.

**Fix:**
1. Open browser DevTools (F12) → Console tab
2. Look for errors during the fold completion
3. Check API terminal for any errors
4. Try a shorter sequence to test

### "RuntimeError: CUDA out of memory"

**Cause:** Your GPU doesn't have enough VRAM for this protein.

**Fix:**
- Try a shorter sequence
- Close other GPU-using applications
- Switch to CPU mode (slower but works)

### Folding takes forever on CPU

That's expected. ESMFold on CPU is slow:
- 30 residues: ~1 minute
- 100 residues: ~5-10 minutes
- 200 residues: ~30 minutes
- 500+ residues: not recommended

**Speedup options:**
- Get an NVIDIA GPU
- Get a Mac with Apple Silicon (MPS support)
- Use a cloud GPU (Lambda Labs, RunPod, etc.) — manual setup for now

---

## UI Issues

### Blank white screen

**Cause:** UI dev server isn't running, or there's a build error.

**Fix:**
1. Make sure `npm run dev` is running in `ui/`
2. Check the Vite terminal for errors
3. Open browser DevTools (F12) → Console for runtime errors
4. Try `npm install` in `ui/` to reinstall dependencies

### "Failed to fetch" errors

**Cause:** API server isn't running, or wrong port.

**Fix:**
1. Make sure the API server is running on port 8765
2. Check the URL in `ui/src/api/client.ts`
3. Try `curl http://localhost:8765/health` to verify the API works

### 3D viewer is blank/black

**Cause:** Molstar failed to load, or no PDB data.

**Fix:**
1. Open DevTools console for Molstar errors
2. Make sure you've actually folded a protein (check the Structures tab)
3. Try refreshing the page

### Buttons don't do anything

**Cause:** Click handlers aren't firing, or the action depends on missing state.

**Fix:**
1. Check DevTools console for JavaScript errors
2. Make sure you have a sequence loaded (some buttons require one)
3. Make sure you have a folded structure (some buttons require it)

### Imported sequence doesn't show in textarea

**Fixed in v0.2.1.** Update to the latest version. Old behavior: import would set state but the sidebar textarea had its own local state. New behavior: textarea is bound to the shared `currentSequence` state.

### Academy match game doesn't accept correct matches

**Fixed in v0.2.1.** The shuffled list was being re-randomized on every render, causing the visible buttons to change between clicks. Now memoized once.

---

## Installation Issues

### `pip install` fails on Python 3.14

**Cause:** Some packages don't yet have wheels for Python 3.14 (it's very new).

**Fix:**
- Use Python 3.11 or 3.12 instead
- Or wait for upstream packages to ship 3.14 wheels
- Or build from source (requires C compiler)

### `npm install` fails with permissions error

**Fix:**
```bash
# Don't use sudo with npm
npm config set prefix ~/.local
export PATH="$HOME/.local/bin:$PATH"
```

### Cargo won't build on Windows

**Cause:** Missing Visual Studio Build Tools.

**Fix:** Install Visual Studio Build Tools with the "Desktop development with C++" workload. Then try `cargo build` again.

### "PYO3_USE_ABI3_FORWARD_COMPATIBILITY" warning

**Cause:** Your Python is newer than PyO3's tested versions.

**Fix:**
```bash
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 cargo build
```

Or set it permanently:
- Linux/Mac: Add to your shell rc file
- Windows: `setx PYO3_USE_ABI3_FORWARD_COMPATIBILITY 1`

---

## Test Issues

### "PermissionError: temp file ... in use" on Windows

**Cause:** SQLAlchemy holds the SQLite file open after tests finish, Windows doesn't release it before the temp dir cleanup.

**Fix:** This is cosmetic, tests still pass. Or use the `ignore_cleanup_errors=True` parameter (already in test_storage.py).

### Tests fail with "no module named opendna_native"

**Cause:** Rust bindings aren't built yet.

**Fix:**
```bash
cargo build  # builds the bindings
# Or use maturin to install them as a Python module
```

The Python tests don't actually need the Rust bindings, only direct imports of Python modules. So you can ignore this if your tests are passing.

---

## Performance Issues

### Everything is slow

**Likely cause:** CPU-only mode with a large protein.

**Fix:**
- Use shorter sequences for testing
- Get a GPU
- Use CUDA torch if you have NVIDIA

### Browser becomes unresponsive

**Cause:** Loading a very complex structure into Molstar, or memory leak.

**Fix:**
- Refresh the page (you'll lose unsaved state)
- Close the structures you don't need
- Use a smaller protein

### API server uses 100% of one CPU core

That's expected during inference. Python's GIL means inference uses one core fully. If you have multiple cores, the rest are still available for other tasks.

### Disk fills up after a few weeks

**Cause:** HuggingFace cache and model cache grow.

**Fix:**
```bash
# Clear HF cache (re-downloads on next use)
rm -rf ~/.cache/huggingface/

# Clear OpenDNA data (loses projects!)
rm -rf ~/.opendna/
```

---

## Network Issues

### UniProt fetch fails

**Cause:** UniProt's API is slow or down.

**Fix:** Try again in a minute. Status: https://www.uniprot.org/

### PDB fetch fails

**Cause:** RCSB PDB server is slow or the ID doesn't exist.

**Fix:** Verify the PDB ID at https://www.rcsb.org/

### HuggingFace download fails

**Cause:** Hub rate limiting or network issue.

**Fix:**
- Try again later
- Set an HF_TOKEN: `export HF_TOKEN=your_token`
- Get a token from https://huggingface.co/settings/tokens

---

## Common Mistakes

### "I changed the code but the API still uses the old behavior"

The API server doesn't auto-reload by default. Restart it after code changes:
```bash
# Ctrl+C the server, then re-run:
python -c "from opendna.api.server import start_server; start_server(port=8765)"
```

For dev with auto-reload:
```bash
uvicorn opendna.api.server:app --reload --port 8765
```

### "My UI changes don't appear"

Vite hot-reloads automatically. If they don't appear:
- Check the Vite terminal for build errors
- Hard refresh the browser (Ctrl+Shift+R)
- Make sure you saved the file

### "I can't find my saved project"

Projects live at `~/.opendna/projects/<name>/workspace.json`. The `~` is your home directory:
- Linux: `/home/yourname/.opendna/`
- Mac: `/Users/yourname/.opendna/`
- Windows: `C:\Users\yourname\.opendna\`

### "I deleted .opendna by mistake"

Sorry, no recovery. Always back up `~/.opendna/projects/` if you care about them.

---

## When All Else Fails

1. **Restart everything** — API server, UI dev server, browser
2. **Update to latest** — `git pull` and `pip install -e ".[dev]"`
3. **Check the issues** — https://github.com/dyber-pqc/OpenDNA/issues
4. **Open a new issue** with:
   - OS, Python version, Node version
   - Steps to reproduce
   - Full error message
   - Output of `python -m pytest tests/python/`
   - Output of `curl http://localhost:8765/health`
