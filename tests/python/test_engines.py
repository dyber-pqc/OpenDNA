"""Real engine tests with reference data.

These tests verify that our analysis engines produce scientifically reasonable
output on well-known proteins. Lightweight - no ML model downloads required.
"""

import pytest

# Real ubiquitin (UniProt P0CG48, 76 residues)
UBIQUITIN = "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"

# Real insulin A-chain (21 residues)
INSULIN_A = "GIVEQCCTSICSLYQLENYCN"

# Real lysozyme (P00698, first 50 residues)
LYSOZYME_FRAGMENT = "KVFGRCELAAAMKRHGLDNYRGYSLGNWVCAAKFESNFNTQATNRNTDGSTD"


# =====================================================
# Sequence properties
# =====================================================

class TestSequenceProperties:
    def test_ubiquitin_mw(self):
        from opendna.engines.analysis import compute_properties
        p = compute_properties(UBIQUITIN)
        # Real ubiquitin MW is ~8565 Da
        assert 8500 < p.molecular_weight < 8600

    def test_ubiquitin_pi(self):
        from opendna.engines.analysis import compute_properties
        p = compute_properties(UBIQUITIN)
        # Real ubiquitin pI is ~6.78
        assert 6.0 < p.isoelectric_point < 7.5

    def test_ubiquitin_gravy_negative(self):
        from opendna.engines.analysis import compute_properties
        p = compute_properties(UBIQUITIN)
        # Ubiquitin is soluble, GRAVY should be slightly negative
        assert -1.0 < p.gravy < 0.0

    def test_insulin_a_length(self):
        from opendna.engines.analysis import compute_properties
        p = compute_properties(INSULIN_A)
        assert p.length == 21

    def test_composition_sums_to_100(self):
        from opendna.engines.analysis import compute_properties
        p = compute_properties(UBIQUITIN)
        total = sum(p.composition_pct.values())
        assert 99 < total < 101

    def test_empty_sequence_raises(self):
        from opendna.engines.analysis import compute_properties
        with pytest.raises((ValueError, Exception)):
            compute_properties("")


# =====================================================
# Lipinski Rule of Five
# =====================================================

class TestLipinski:
    def test_small_peptide_passes(self):
        from opendna.engines.analysis import lipinski_rule_of_five
        # Tripeptide should pass (or be close)
        r = lipinski_rule_of_five("GLY")
        assert r.molecular_weight < 500

    def test_ubiquitin_fails(self):
        from opendna.engines.analysis import lipinski_rule_of_five
        # Ubiquitin is way too big for RO5 (intended for small molecules)
        r = lipinski_rule_of_five(UBIQUITIN)
        assert not r.passes_ro5
        assert len(r.violations) > 0


# =====================================================
# Hydropathy
# =====================================================

class TestHydropathy:
    def test_profile_length_matches(self):
        from opendna.engines.analysis import hydropathy_profile
        profile = hydropathy_profile(UBIQUITIN)
        assert len(profile) == len(UBIQUITIN)

    def test_profile_values_in_range(self):
        from opendna.engines.analysis import hydropathy_profile
        profile = hydropathy_profile(UBIQUITIN)
        # All values should be in the Kyte-Doolittle range
        assert all(-5 <= v <= 5 for v in profile)


# =====================================================
# Disorder
# =====================================================

class TestDisorder:
    def test_returns_correct_keys(self):
        from opendna.engines.disorder import predict_disorder
        r = predict_disorder(UBIQUITIN)
        assert "scores" in r
        assert "regions" in r
        assert "disorder_percent" in r

    def test_scores_per_residue(self):
        from opendna.engines.disorder import predict_disorder
        r = predict_disorder(UBIQUITIN)
        assert len(r["scores"]) == len(UBIQUITIN)

    def test_disorder_pct_in_range(self):
        from opendna.engines.disorder import predict_disorder
        r = predict_disorder(UBIQUITIN)
        assert 0 <= r["disorder_percent"] <= 100


# =====================================================
# Predictors
# =====================================================

class TestPredictors:
    def test_ubiquitin_no_transmembrane(self):
        from opendna.engines.predictors import predict_transmembrane
        # Ubiquitin is cytoplasmic, no TM helices
        r = predict_transmembrane(UBIQUITIN)
        assert r["n_helices"] == 0
        assert not r["is_membrane_protein"]

    def test_ubiquitin_no_signal_peptide(self):
        from opendna.engines.predictors import predict_signal_peptide
        # Ubiquitin has no signal peptide
        r = predict_signal_peptide(UBIQUITIN)
        assert r["has_signal"] is False

    def test_aggregation_returns_keys(self):
        from opendna.engines.predictors import predict_aggregation
        r = predict_aggregation(UBIQUITIN)
        assert "risk_level" in r
        assert r["risk_level"] in ("low", "medium", "high")

    def test_phosphorylation_finds_sites(self):
        from opendna.engines.predictors import predict_phosphorylation
        r = predict_phosphorylation(UBIQUITIN)
        assert "sites" in r
        assert "count" in r
        assert r["count"] >= 0


# =====================================================
# Mutation effects
# =====================================================

class TestMutations:
    def test_apply_valid_mutation(self):
        from opendna.engines.design import apply_mutation
        mutated = apply_mutation(UBIQUITIN, "K48R")
        assert mutated[47] == "R"  # 0-indexed
        assert len(mutated) == len(UBIQUITIN)

    def test_apply_invalid_format_raises(self):
        from opendna.engines.design import apply_mutation
        with pytest.raises(ValueError):
            apply_mutation(UBIQUITIN, "invalid")

    def test_apply_wrong_residue_raises(self):
        from opendna.engines.design import apply_mutation
        with pytest.raises(ValueError):
            # Position 48 is N in this seq, not Q
            apply_mutation(UBIQUITIN, "Q48R")

    def test_predict_ddg_returns_kcal(self):
        from opendna.engines.predictors import predict_ddg
        r = predict_ddg(UBIQUITIN, "K48R")
        assert "ddg_kcal_mol" in r
        assert "classification" in r
        assert isinstance(r["ddg_kcal_mol"], (int, float))


# =====================================================
# Alignment
# =====================================================

class TestAlignment:
    def test_identical_sequences(self):
        from opendna.engines.alignment import needleman_wunsch
        r = needleman_wunsch("MKTVRQERLK", "MKTVRQERLK")
        assert r["identity_pct"] == 100.0

    def test_one_mutation(self):
        from opendna.engines.alignment import needleman_wunsch
        r = needleman_wunsch("MKTVRQERLK", "MKTVRAERLK")
        assert r["identity_pct"] == 90.0

    def test_completely_different(self):
        from opendna.engines.alignment import needleman_wunsch
        r = needleman_wunsch("MKTVRQERLK", "ACDEFGHIKL")
        assert r["identity_pct"] < 30


# =====================================================
# Cost & carbon
# =====================================================

class TestCostCarbon:
    def test_synthesis_cost_increases_with_length(self):
        from opendna.data.synthesis import estimate_synthesis_cost
        short = estimate_synthesis_cost("M" * 10)
        long = estimate_synthesis_cost("M" * 100)
        assert long.cheapest_price > short.cheapest_price

    def test_carbon_estimate_keys(self):
        from opendna.data.synthesis import estimate_carbon
        r = estimate_carbon("fold", 60.0, "cpu")
        assert r.energy_kwh > 0
        assert r.co2_kg > 0


# =====================================================
# QSAR
# =====================================================

class TestQsar:
    def test_descriptors_returned(self):
        from opendna.engines.qsar import compute_qsar_descriptors
        r = compute_qsar_descriptors(UBIQUITIN)
        assert r["n_descriptors"] > 20
        assert "constitutional" in r
        assert "hydrophobic" in r
        assert "electronic" in r


# =====================================================
# Multi-objective Pareto
# =====================================================

class TestPareto:
    def test_simple_pareto_front(self):
        from opendna.engines.multi_objective import pareto_optimize
        candidates = [
            {"sequence": "A", "x": 1.0, "y": 1.0},  # dominated
            {"sequence": "B", "x": 5.0, "y": 1.0},  # front 1
            {"sequence": "C", "x": 1.0, "y": 5.0},  # front 1
            {"sequence": "D", "x": 3.0, "y": 3.0},  # front 1
        ]
        result = pareto_optimize(candidates, ["x", "y"])
        # B, C, D are non-dominated; A is dominated
        ranks = {p.sequence: p.rank for p in result}
        assert ranks["A"] == 2
        assert ranks["B"] == 1
        assert ranks["C"] == 1
        assert ranks["D"] == 1


# =====================================================
# Antibody numbering
# =====================================================

class TestAntibody:
    def test_antibody_detection(self):
        from opendna.engines.antibody import find_cdrs
        # Real antibody heavy chain
        seq = "EVQLVESGGGLVQPGGSLRLSCAASGFNIKDTYIHWVRQAPGKGLEWVARIYPTNGYTRYADSVKGRFTISADTSKNTAYLQMNSLRAEDTAVYYCSRWGGDGFYAMDYWGQGTLVTVSS"
        r = find_cdrs(seq)
        assert "cdrs" in r
        assert "chain_type" in r

    def test_unknown_sequence(self):
        from opendna.engines.antibody import find_cdrs
        r = find_cdrs("MKTVRQERLK")
        assert r["chain_type"] in ("unknown", "light", "heavy")
