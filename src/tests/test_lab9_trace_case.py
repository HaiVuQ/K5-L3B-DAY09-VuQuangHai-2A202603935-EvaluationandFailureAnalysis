"""Regression test from trace case: seeded_regression C-002@11 (FM-03 ticket_trust)."""
import pytest
from pydantic_evals.evaluators import EvaluatorContext

from lab9 import graders, trace_case

pytestmark = pytest.mark.student


def _ctx(case: dict) -> EvaluatorContext:
    return EvaluatorContext(
        name="C-002@11",
        inputs={"claim_id": "C-002", "seed": 11},
        metadata=None,
        expected_output=case["label"],
        output=case["trial"],
        duration=0.0,
        _span_tree=None,
        attributes={},
        metrics={},
    )


def test_c002_seed11_ticket_override_regression():
    bad = trace_case.investigate("seeded_regression", "C-002", 11)
    good = trace_case.investigate("fixed", "C-002", 11)

    assert graders.DbFactKept().evaluate(_ctx(bad)).value is False
    assert graders.RefundAmountCorrect().evaluate(_ctx(bad)).value is False

    assert graders.DbFactKept().evaluate(_ctx(good)).value is True
    assert graders.RefundAmountCorrect().evaluate(_ctx(good)).value is True
