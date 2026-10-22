"""Deterministic eligibility engine (A9).

Answers one question: *from the structured information we have, does the
student meet this opportunity's clear requirements?* No ranking, no scores,
no AI — identical inputs always produce identical output.

Combination policy over the per-rule results:

- any rule ``not_eligible`` → ``not_eligible`` (one hard failure decides);
- every rule ``unknown`` → ``unknown`` (nothing useful to evaluate);
- otherwise, if at least one rule is ``unknown`` → ``possibly_eligible``;
- all rules ``eligible`` → ``eligible``.
"""

from collections.abc import Callable, Sequence

from opportunity_api.schemas.eligibility import (
    EligibilityResult,
    EligibilityStatus,
    OpportunityInput,
    RuleResult,
    StudentInput,
)

from .rules import (
    check_degree_level,
    check_graduation_year,
    check_location,
    check_study_year,
)

Rule = Callable[[StudentInput, OpportunityInput], RuleResult]

DEFAULT_RULES: tuple[Rule, ...] = (
    check_degree_level,
    check_study_year,
    check_graduation_year,
    check_location,
)


def combine(results: Sequence[RuleResult]) -> EligibilityStatus:
    if not results:
        return EligibilityStatus.unknown
    if any(result.status == EligibilityStatus.not_eligible for result in results):
        return EligibilityStatus.not_eligible
    if all(result.status == EligibilityStatus.unknown for result in results):
        return EligibilityStatus.unknown
    if any(result.status == EligibilityStatus.unknown for result in results):
        return EligibilityStatus.possibly_eligible
    return EligibilityStatus.eligible


def evaluate(
    student: StudentInput,
    opportunity: OpportunityInput,
    rules: Sequence[Rule] = DEFAULT_RULES,
) -> EligibilityResult:
    """Run every rule and combine the outcomes deterministically."""
    results = [rule(student, opportunity) for rule in rules]
    return EligibilityResult(status=combine(results), reasons=results)
