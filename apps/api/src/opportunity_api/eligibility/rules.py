"""Individual eligibility rules (A9).

Each rule inspects one structured requirement and returns a ``RuleResult``
with a human-readable reason. The contract for every rule:

- decide only from structured data — never parse free text into requirements;
- a requirement the source did not state stays ``unknown``;
- a clear mismatch is ``not_eligible``; a clear match is ``eligible``;
- ambiguous free text is ``unknown``, never ``not_eligible``.
"""

from opportunity_api.schemas.eligibility import (
    EligibilityStatus,
    OpportunityInput,
    RuleResult,
    StudentInput,
)


def check_degree_level(
    student: StudentInput, opportunity: OpportunityInput
) -> RuleResult:
    required = opportunity.degree_level
    actual = student.degree_level
    if required is None:
        return RuleResult(
            rule="degree_level",
            status=EligibilityStatus.unknown,
            reason="Opportunity does not specify a degree level",
        )
    if actual is None:
        return RuleResult(
            rule="degree_level",
            status=EligibilityStatus.unknown,
            reason="Student has not declared a degree level",
        )
    if required.value == "both" or required.value == actual.value:
        return RuleResult(
            rule="degree_level",
            status=EligibilityStatus.eligible,
            reason=f"{actual.value.capitalize()} students are accepted",
        )
    return RuleResult(
        rule="degree_level",
        status=EligibilityStatus.not_eligible,
        reason=f"Opportunity requires {required.value} students; student is {actual.value}",
    )


def check_study_year(
    student: StudentInput, opportunity: OpportunityInput
) -> RuleResult:
    accepted = opportunity.study_year
    actual = student.study_year
    if accepted is None:
        return RuleResult(
            rule="study_year",
            status=EligibilityStatus.unknown,
            reason="Opportunity does not specify accepted study years",
        )
    if actual is None:
        return RuleResult(
            rule="study_year",
            status=EligibilityStatus.unknown,
            reason="Student study year is not known",
        )
    if actual in accepted:
        return RuleResult(
            rule="study_year",
            status=EligibilityStatus.eligible,
            reason=f"Year {actual} is accepted",
        )
    years = ", ".join(str(year) for year in sorted(accepted))
    return RuleResult(
        rule="study_year",
        status=EligibilityStatus.not_eligible,
        reason=f"Opportunity accepts years {years}; student is in year {actual}",
    )


def check_graduation_year(
    student: StudentInput, opportunity: OpportunityInput
) -> RuleResult:
    """Structured graduation constraints only; never inferred from description."""
    required = opportunity.graduation_years
    actual = student.graduation_year
    if required is None:
        return RuleResult(
            rule="graduation_year",
            status=EligibilityStatus.unknown,
            reason="No structured graduation restriction available",
        )
    if actual is None:
        return RuleResult(
            rule="graduation_year",
            status=EligibilityStatus.unknown,
            reason="Student graduation year is not known",
        )
    if actual in required:
        return RuleResult(
            rule="graduation_year",
            status=EligibilityStatus.eligible,
            reason=f"Graduation year {actual} is accepted",
        )
    years = ", ".join(str(year) for year in sorted(required))
    return RuleResult(
        rule="graduation_year",
        status=EligibilityStatus.not_eligible,
        reason=f"Opportunity requires graduation in {years}; student graduates {actual}",
    )


def check_location(
    student: StudentInput, opportunity: OpportunityInput
) -> RuleResult:
    """Deterministic, conservative: free text can establish a match or
    remote-friendly status, but never a hard rejection."""
    location = opportunity.location
    if location is None:
        return RuleResult(
            rule="location",
            status=EligibilityStatus.unknown,
            reason="Opportunity does not specify a location",
        )
    lowered = location.lower()
    if "remote" in lowered:
        return RuleResult(
            rule="location",
            status=EligibilityStatus.eligible,
            reason="Remote opportunity; no location barrier",
        )
    student_location = (student.location or "").strip().lower()
    if student_location and student_location in lowered:
        return RuleResult(
            rule="location",
            status=EligibilityStatus.eligible,
            reason="Opportunity location matches the student's location",
        )
    if not student_location:
        return RuleResult(
            rule="location",
            status=EligibilityStatus.unknown,
            reason="Student location is not known; cannot compare",
        )
    return RuleResult(
        rule="location",
        status=EligibilityStatus.unknown,
        reason="No clear location restriction can be derived from free text",
    )
