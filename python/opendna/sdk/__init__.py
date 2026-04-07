"""OpenDNA Python SDK - lightweight client for the OpenDNA API.

Usage:
    from opendna.sdk import Client

    client = Client("http://localhost:8765")
    result = client.fold("MKTVRQERLKSIVRILER")
    print(result.mean_confidence)

    # Or use the high-level workflow:
    score = client.evaluate("MKTVRQERLK")
    analysis = client.analyze("MKTVRQERLK")
    candidates = client.design(result.pdb_string, num_candidates=10)
"""

from opendna.sdk.client import Client, FoldResult, ScoreResult, DesignResult, AnalysisResult

__all__ = [
    "Client",
    "FoldResult",
    "ScoreResult",
    "DesignResult",
    "AnalysisResult",
]
