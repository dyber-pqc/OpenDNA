"""End-to-end smoke tests for v0.5.0 phases.

These tests exercise the Python-side modules created in phases 2-16.
They deliberately avoid heavy ML imports so they run in seconds on CI.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def test_components_registry():
    from opendna.components import list_components, get_component
    cs = list_components()
    assert len(cs) >= 10
    esm = get_component("esmfold")
    assert esm is not None and esm.category == "folding"


def test_pqc_identity_token_roundtrip():
    from opendna.auth import (
        generate_identity, issue_token, validate_token,
        get_user_store,
    )
    store = get_user_store()
    ident = store.create_user("test_phase4", "pw1", ["user", "admin"])
    token = issue_token(ident, scopes=["user", "admin"])
    ctx = validate_token(token, lambda u: store.get_identity(u))
    assert ctx is not None
    assert ctx.user_id == "test_phase4"
    assert "admin" in ctx.scopes


def test_workspaces_encryption(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENDNA_WORKSPACES_DIR", str(tmp_path / "ws"))
    from opendna.workspaces import get_workspace
    ws = get_workspace("alice", password="p@ss", name="default")
    ws.save_project("p1", {"k": "v"})
    assert ws.load_project("p1") == {"k": "v"}


def test_priority_queue_runs_job():
    import asyncio
    from opendna.runtime import get_queue

    async def _run():
        q = get_queue()
        await q.start()

        def work(on_progress, x):
            on_progress("go", 0.5, "half")
            return {"out": x + 1}

        jid = await q.submit(work, priority=0, kwargs={"x": 10})
        for _ in range(40):
            j = q.get(jid)
            if j and j["status"] == "completed":
                return j
            await asyncio.sleep(0.05)
        return None

    j = asyncio.run(_run())
    assert j is not None and j["status"] == "completed"
    assert j["result"]["out"] == 11


def test_reliability_retry_and_crash():
    from opendna.reliability import retry, RetryPolicy, get_crash_reporter
    attempts = {"n": 0}

    @retry(policy=RetryPolicy(max_attempts=3, initial_delay=0.001, jitter=0))
    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise RuntimeError("try again")
        return "ok"

    assert flaky() == "ok"
    try:
        raise ValueError("boom secret=xyz")
    except Exception as e:
        cid = get_crash_reporter().report(e)
    assert cid


def test_provenance_diff_blame_bisect():
    from opendna.provenance import record_step, diff_steps, blame_residue, bisect_regression
    import secrets
    pid = "t_" + secrets.token_hex(3)
    n1 = record_step(pid, "fold", {}, {"sequence": "MKTV", "pdb": "x"}, score=0.7)
    n2 = record_step(pid, "design", {}, {"sequence": "MKAV", "pdb": "x"}, score=0.8, parent_ids=[n1.id])
    n3 = record_step(pid, "design", {}, {"sequence": "MEAV", "pdb": "x"}, score=0.4, parent_ids=[n2.id])
    d = diff_steps(n1.id, n2.id)
    assert any(m["pos"] == 3 and m["to"] == "A" for m in d["mutations"])
    b = bisect_regression(pid)
    assert b and b["regression_node"] == n3.id
    assert len(blame_residue(pid, 3)) >= 2


def test_workflow_graph_runner():
    from opendna.workflows.graph_runner import run_workflow, list_node_types
    assert len(list_node_types()) >= 8
    wf = {
        "nodes": [
            {"id": "c", "kind": "constant", "params": {"value": "MKTV"}},
            {"id": "e", "kind": "evaluate", "params": {}},
        ],
        "edges": [{"source": "c", "target": "e", "out_key": "value", "in_key": "sequence"}],
    }
    res = run_workflow(wf)
    assert res["order"] == ["c", "e"]
    assert "error" not in res["outputs"]["e"]


def test_external_vendors_and_webhooks():
    from opendna.external import list_vendors, quote_synthesis, register_webhook, list_webhooks, delete_webhook
    assert any(v["id"] == "twist" for v in list_vendors())
    q = quote_synthesis("ATG" * 30, kind="dna_gene")
    assert q["quotes"] and q["quotes"][0]["available"]
    wid = register_webhook("https://example.invalid/wh", event="vendor.order")
    assert any(w["id"] == wid for w in list_webhooks())
    assert delete_webhook(wid)


def test_notebook_and_exports():
    from opendna.notebook import get_notebook, export_figure_svg, pdb_to_obj, pdb_to_gltf
    nb = get_notebook("tproj")
    e = nb.add_entry("t", "# hi", tags=["x"])
    assert any(en.get("id") == e.id for en in nb.list_entries())
    svg = export_figure_svg({"x": [1, 2, 3], "y": [4, 5, 6]}, title="t")
    assert svg.startswith("<svg")
    pdb = ("ATOM      1  CA  MET A   1      11.104  13.207  10.000\n"
           "ATOM      2  CA  ALA A   2      14.500  13.500  12.000\n")
    obj = pdb_to_obj(pdb)
    assert obj.count("v ") == 12
    gltf = pdb_to_gltf(pdb)
    assert gltf["accessors"][0]["count"] == 2


def test_alphafold_db_import():
    from opendna.external import fetch_alphafold, fetch_alphafold_meta
    assert callable(fetch_alphafold)
    assert callable(fetch_alphafold_meta)


def test_trajectory_to_gif(tmp_path):
    from opendna.notebook import trajectory_to_gif
    pdb = ("ATOM      1  CA  MET A   1      11.104  13.207  10.000\n"
           "ATOM      2  CA  ALA A   2      14.500  13.500  12.000\n")
    pdb2 = ("ATOM      1  CA  MET A   1      11.500  13.700  10.500\n"
            "ATOM      2  CA  ALA A   2      14.900  13.900  12.500\n")
    out = tmp_path / "traj.gif"
    path = trajectory_to_gif([pdb, pdb2], str(out), fps=5)
    assert path == str(out)
    assert Path(path).exists() and Path(path).stat().st_size > 0


def test_academy_levels_and_badges():
    from opendna.academy import list_levels, get_level, BADGES, GLOSSARY, daily_challenge
    assert [l["id"] for l in list_levels()] == [4, 5, 6, 7]
    assert get_level(6) is not None
    assert len(BADGES) >= 10
    assert len(GLOSSARY) >= 15
    assert daily_challenge()["kind"]


def test_compliance_sbom_and_privacy():
    from opendna.compliance import generate_sbom, privacy_report, hipaa_checklist, gdpr_checklist
    sbom = generate_sbom()
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    rep = privacy_report()
    assert "auth_db" in rep["areas"]
    assert len(hipaa_checklist()) >= 5
    assert len(gdpr_checklist()) >= 5
