"""OpenDNA SDK client - convenience wrapper around the REST API."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class FoldResult:
    pdb_string: str
    mean_confidence: float
    method: str
    explanation: str

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(self.pdb_string)


@dataclass
class ScoreResult:
    overall: float
    confidence: float
    breakdown: dict
    summary: str
    recommendations: list


@dataclass
class DesignCandidate:
    rank: int
    sequence: str
    score: float
    recovery: float


@dataclass
class DesignResult:
    candidates: list[DesignCandidate]
    method: str

    @property
    def best(self) -> DesignCandidate:
        return self.candidates[0]


@dataclass
class AnalysisResult:
    properties: dict
    lipinski: dict
    hydropathy_profile: list[float]
    disorder: dict
    transmembrane: dict
    signal_peptide: dict
    aggregation: dict
    phosphorylation: dict
    glycosylation: dict
    structure: Optional[dict] = None


class OpenDnaClientError(Exception):
    pass


class Client:
    """Client for the OpenDNA REST API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8765",
        timeout: float = 600.0,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self._client = httpx.Client(timeout=timeout)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._client.close()

    def _post(self, path: str, body: dict) -> dict:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        r = self._client.post(f"{self.base_url}{path}", json=body, headers=headers)
        if r.status_code >= 400:
            try:
                err = r.json()
                raise OpenDnaClientError(err.get("message", r.text))
            except Exception:
                raise OpenDnaClientError(f"{r.status_code}: {r.text[:200]}")
        return r.json()

    def _get(self, path: str) -> dict:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        r = self._client.get(f"{self.base_url}{path}", headers=headers)
        r.raise_for_status()
        return r.json()

    def _wait_for_job(self, job_id: str, poll_interval: float = 1.0, timeout: float = 1800) -> dict:
        start = time.time()
        while time.time() - start < timeout:
            job = self._get(f"/v1/jobs/{job_id}")
            if job["status"] == "completed":
                return job["result"]
            if job["status"] == "failed":
                raise OpenDnaClientError(f"Job {job_id} failed: {job.get('error')}")
            if job["status"] == "cancelled":
                raise OpenDnaClientError(f"Job {job_id} was cancelled")
            time.sleep(poll_interval)
        raise OpenDnaClientError(f"Job {job_id} timed out after {timeout}s")

    # === High-level methods ===

    def health(self) -> dict:
        return self._get("/health")

    def hardware(self) -> dict:
        return self._get("/v1/hardware")

    def fold(self, sequence: str, method: str = "auto") -> FoldResult:
        """Fold a protein sequence (blocking - waits for the job to complete)."""
        job = self._post("/v1/fold", {"sequence": sequence, "method": method})
        result = self._wait_for_job(job["job_id"])
        return FoldResult(
            pdb_string=result["pdb"],
            mean_confidence=result["mean_confidence"],
            method=result["method"],
            explanation=result["explanation"],
        )

    def evaluate(self, sequence: str) -> ScoreResult:
        """Quickly score a protein sequence."""
        r = self._post("/v1/evaluate", {"sequence": sequence})
        return ScoreResult(**r)

    def analyze(self, sequence: str, pdb_string: Optional[str] = None) -> AnalysisResult:
        """Run the comprehensive analysis suite."""
        r = self._post("/v1/analyze", {"sequence": sequence, "pdb_string": pdb_string})
        return AnalysisResult(**r)

    def design(self, pdb_string: str, num_candidates: int = 10, temperature: float = 0.1) -> DesignResult:
        """Generate alternative sequences for a backbone (blocking)."""
        job = self._post("/v1/design", {
            "pdb_string": pdb_string,
            "num_candidates": num_candidates,
            "temperature": temperature,
        })
        result = self._wait_for_job(job["job_id"])
        return DesignResult(
            candidates=[DesignCandidate(**c) for c in result["candidates"]],
            method=result["method"],
        )

    def iterative_design(self, sequence: str, n_rounds: int = 5, candidates_per_round: int = 5) -> dict:
        """Run an iterative optimization loop."""
        job = self._post("/v1/iterative_design", {
            "sequence": sequence,
            "n_rounds": n_rounds,
            "candidates_per_round": candidates_per_round,
        })
        return self._wait_for_job(job["job_id"], timeout=7200)

    def mutate(self, sequence: str, mutation: str) -> str:
        """Apply a point mutation. Returns the mutated sequence."""
        r = self._post("/v1/mutate", {"sequence": sequence, "mutation": mutation})
        return r["mutated"]

    def predict_ddg(self, sequence: str, mutation: str) -> dict:
        """Predict the stability change of a mutation."""
        return self._post("/v1/predict_ddg", {"sequence": sequence, "mutation": mutation})

    def fetch_uniprot(self, accession: str) -> dict:
        """Fetch a protein from UniProt by accession or famous name."""
        return self._post("/v1/fetch_uniprot", {"accession": accession})

    def fetch_pdb(self, pdb_id: str) -> str:
        """Fetch a PDB structure from RCSB."""
        r = self._post("/v1/fetch_pdb", {"pdb_id": pdb_id})
        return r["pdb_string"]

    def explain(self, sequence: str, pdb_string: Optional[str] = None) -> str:
        """Get an AI explanation of a protein."""
        r = self._post("/v1/explain", {"sequence": sequence, "pdb_string": pdb_string})
        return r["explanation"]

    def agent(self, goal: str, max_steps: int = 8) -> dict:
        """Run the LLM agent on a high-level goal."""
        return self._post("/v1/agent", {"goal": goal, "max_steps": max_steps})

    def chat(self, message: str) -> dict:
        """Smart chat with tool calling."""
        return self._post("/v1/smart_chat", {"message": message})

    def list_jobs(self) -> list[dict]:
        return self._get("/v1/jobs")["jobs"]

    def cancel_job(self, job_id: str) -> bool:
        try:
            self._post(f"/v1/jobs/{job_id}/cancel", {})
            return True
        except OpenDnaClientError:
            return False
