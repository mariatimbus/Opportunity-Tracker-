"""A9 deterministic eligibility engine."""

from opportunity_api.eligibility import evaluate
from opportunity_api.eligibility.engine import combine
from opportunity_api.schemas.eligibility import (
    EligibilityResult,
    EligibilityStatus,
    OpportunityInput,
    RuleResult,
    StudentInput,
)

BACHELOR = StudentInput(
    degree_level="bachelor", study_year=2, graduation_year=2029, location="Bucharest, Romania"
)
FULL_OPP = OpportunityInput(
    degree_level="both",
    study_year=[1, 2, 3],
    location="Berlin, Germany",
)


def test_bachelor_with_bachelor_is_eligible():
    result = evaluate(
        StudentInput(degree_level="bachelor"),
        OpportunityInput(degree_level="bachelor"),
        rules=_degree_only(),
    )
    assert result.status == EligibilityStatus.eligible
    assert result.reasons[0].rule == "degree_level"
    assert "Bachelor" in result.reasons[0].reason


def test_bachelor_with_both_is_eligible():
    result = evaluate(
        StudentInput(degree_level="bachelor"),
        OpportunityInput(degree_level="both"),
        rules=_degree_only(),
    )
    assert result.status == EligibilityStatus.eligible


def test_bachelor_with_master_is_not_eligible():
    result = evaluate(
        StudentInput(degree_level="bachelor"),
        OpportunityInput(degree_level="master"),
        rules=_degree_only(),
    )
    assert result.status == EligibilityStatus.not_eligible


def test_master_with_bachelor_is_not_eligible():
    result = evaluate(
        StudentInput(degree_level="master"),
        OpportunityInput(degree_level="bachelor"),
        rules=_degree_only(),
    )
    assert result.status == EligibilityStatus.not_eligible


def test_null_degree_level_is_unknown():
    result = evaluate(
        StudentInput(degree_level="bachelor"),
        OpportunityInput(degree_level=None),
        rules=_degree_only(),
    )
    assert result.status == EligibilityStatus.unknown
    assert "does not specify" in result.reasons[0].reason


def test_null_student_degree_is_unknown():
    result = evaluate(
        StudentInput(degree_level=None),
        OpportunityInput(degree_level="bachelor"),
        rules=_degree_only(),
    )
    assert result.status == EligibilityStatus.unknown


def test_year_in_range_is_eligible():
    result = evaluate(
        StudentInput(study_year=2),
        OpportunityInput(study_year=[1, 2, 3]),
        rules=_year_only(),
    )
    assert result.status == EligibilityStatus.eligible


def test_year_out_of_range_is_not_eligible():
    result = evaluate(
        StudentInput(study_year=4),
        OpportunityInput(study_year=[1, 2, 3]),
        rules=_year_only(),
    )
    assert result.status == EligibilityStatus.not_eligible


def test_null_study_year_is_unknown():
    result = evaluate(
        StudentInput(study_year=2),
        OpportunityInput(study_year=None),
        rules=_year_only(),
    )
    assert result.status == EligibilityStatus.unknown


def test_one_hard_failure_overrides_other_passes():
    result = evaluate(
        StudentInput(degree_level="bachelor", study_year=2),
        OpportunityInput(degree_level="master", study_year=[1, 2, 3]),
    )
    assert result.status == EligibilityStatus.not_eligible
    statuses = {reason.rule: reason.status for reason in result.reasons}
    assert statuses["degree_level"] == EligibilityStatus.not_eligible
    assert statuses["study_year"] == EligibilityStatus.eligible


def test_all_known_rules_pass_is_eligible():
    result = evaluate(
        StudentInput(degree_level="bachelor", study_year=2, location="Berlin, Germany"),
        OpportunityInput(degree_level="both", study_year=[1, 2, 3], location="Berlin, Germany"),
    )
    # graduation rule is unknown in v1 (no structured source) → not all pass
    assert result.status == EligibilityStatus.possibly_eligible


def test_passes_plus_unknown_rule_is_possibly_eligible():
    result = evaluate(BACHELOR, FULL_OPP)
    statuses = {reason.rule: reason.status for reason in result.reasons}
    assert statuses["degree_level"] == EligibilityStatus.eligible
    assert statuses["study_year"] == EligibilityStatus.eligible
    assert statuses["graduation_year"] == EligibilityStatus.unknown
    assert result.status == EligibilityStatus.possibly_eligible


def test_all_rules_unknown_is_unknown():
    result = evaluate(StudentInput(), OpportunityInput())
    assert result.status == EligibilityStatus.unknown
    assert all(reason.status == EligibilityStatus.unknown for reason in result.reasons)


def test_graduation_rule_never_infers_from_description():
    result = evaluate(BACHELOR, OpportunityInput(degree_level="both", study_year=[2]))
    graduation = next(r for r in result.reasons if r.rule == "graduation_year")
    assert graduation.status == EligibilityStatus.unknown
    assert "structured" in graduation.reason


def test_graduation_with_structured_data():
    result = evaluate(
        StudentInput(graduation_year=2029),
        OpportunityInput(graduation_years=[2028, 2029]),
    )
    graduation = next(r for r in result.reasons if r.rule == "graduation_year")
    assert graduation.status == EligibilityStatus.eligible

    failing = evaluate(
        StudentInput(graduation_year=2030),
        OpportunityInput(graduation_years=[2028, 2029]),
    )
    graduation = next(r for r in failing.reasons if r.rule == "graduation_year")
    assert graduation.status == EligibilityStatus.not_eligible


def test_location_rules_are_conservative():
    def location_status(student: StudentInput, opp: OpportunityInput) -> EligibilityStatus:
        result = evaluate(student, opp)
        return next(r.status for r in result.reasons if r.rule == "location")

    assert (
        location_status(
            StudentInput(location="Bucharest, Romania"), OpportunityInput(location="Remote")
        )
        == EligibilityStatus.eligible
    )
    assert (
        location_status(
            StudentInput(location="Berlin, Germany"), OpportunityInput(location="Berlin, Germany")
        )
        == EligibilityStatus.eligible
    )
    assert (
        location_status(
            StudentInput(location="Bucharest, Romania"),
            OpportunityInput(location="Berlin, Germany"),
        )
        == EligibilityStatus.unknown
    )
    assert location_status(StudentInput(), OpportunityInput(location="Berlin, Germany")) == (
        EligibilityStatus.unknown
    )
    assert location_status(StudentInput(location="Berlin"), OpportunityInput(location=None)) == (
        EligibilityStatus.unknown
    )


def test_determinism_same_inputs_same_output():
    first = evaluate(BACHELOR, FULL_OPP)
    second = evaluate(BACHELOR.model_copy(deep=True), FULL_OPP.model_copy(deep=True))
    assert first == second
    assert isinstance(first, EligibilityResult)


def test_combine_policy():
    eligible = RuleResult(rule="a", status=EligibilityStatus.eligible, reason="ok")
    unknown = RuleResult(rule="b", status=EligibilityStatus.unknown, reason="?")
    failed = RuleResult(rule="c", status=EligibilityStatus.not_eligible, reason="no")

    assert combine([]) == EligibilityStatus.unknown
    assert combine([failed, eligible, unknown]) == EligibilityStatus.not_eligible
    assert combine([unknown, unknown]) == EligibilityStatus.unknown
    assert combine([eligible, unknown]) == EligibilityStatus.possibly_eligible
    assert combine([eligible, eligible]) == EligibilityStatus.eligible


def _degree_only():
    from opportunity_api.eligibility import check_degree_level

    return [check_degree_level]


def _year_only():
    from opportunity_api.eligibility import check_study_year

    return [check_study_year]
