"""Tests for the scoring engine."""

from opendna.engines.scoring import evaluate


def test_evaluate_basic():
    result = evaluate("MKTVRQERLKSIVRILERSKEPVSGAQLAEELS")
    assert 0 <= result.overall <= 1
    assert 0 <= result.confidence <= 1
    assert len(result.summary) > 0
    assert len(result.recommendations) > 0


def test_evaluate_breakdown():
    result = evaluate("MKTVRQERLKSIVRILERSKEPVSGAQLAEELS")
    assert 0 <= result.breakdown.stability <= 1
    assert 0 <= result.breakdown.solubility <= 1
    assert 0 <= result.breakdown.immunogenicity <= 1
    assert 0 <= result.breakdown.developability <= 1


def test_evaluate_short_sequence():
    result = evaluate("MKTV")
    assert 0 <= result.overall <= 1


def test_evaluate_protein_object():
    from opendna.models.protein import Protein
    p = Protein(name="test", sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELS")
    result = evaluate(p)
    assert 0 <= result.overall <= 1
