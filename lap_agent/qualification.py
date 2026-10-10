"""Deterministic mirror of the LAP eligibility and branch rules.

The Retell voice agent follows system_prompt.md. This module provides a
testable representation of the same rule table; it does not attempt to
interpret raw speech or replace the prompt's conversational reasoning.
Amounts are rupees and should be supplied only after they have been clearly
understood from the customer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


LOAN_LIMIT_RUPEES = Decimal("7500000")
MIN_TENURE_YEARS = Decimal("3")
MAX_TENURE_YEARS = Decimal("15")


@dataclass
class QualificationState:
    customer_verified: bool | None = None
    property_type: str | None = None
    ownership_status: str | None = None
    documents_available: bool | None = None
    loan_amount_rupees: Decimal | None = None
    loan_amount_over_limit: bool = False
    loan_amount_75_lakh_decision: str | None = None
    occupation: str | None = None
    income_mode: str | None = None
    mixed_income_bank_received: bool | None = None
    mixed_income_clarification_asked: bool = False
    market_value: str | Decimal | None = None
    market_value_asked: bool = False
    tenure_years: Decimal | None = None
    existing_loan_or_emi_request: bool = False
    disqualified: bool = False
    callback_time: str | None = None
    callback_clarification_asked: bool = False
    abuse_responses: int = 0
    clarification_pending: str | None = None


@dataclass(frozen=True)
class TurnSignals:
    busy: bool = False
    wrong_person: bool = False
    wrong_number: bool = False
    not_interested: bool = False
    do_not_call: bool = False
    silence: bool = False
    abuse: bool = False
    transfer_trigger: bool = False
    callback_time_clear: bool = False


@dataclass(frozen=True)
class Decision:
    action: str
    next_field: str | None = None
    reason: str | None = None
    state: QualificationState = field(default_factory=QualificationState)


_STATE_FACT_FIELDS = {
    "customer_verified",
    "property_type",
    "ownership_status",
    "documents_available",
    "loan_amount_rupees",
    "loan_amount_75_lakh_decision",
    "occupation",
    "income_mode",
    "mixed_income_bank_received",
    "market_value",
    "tenure_years",
    "existing_loan_or_emi_request",
    "callback_time",
}


def decimal_value(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def months_to_years(months: Any) -> Decimal | None:
    value = decimal_value(months)
    return value / Decimal("12") if value is not None else None


def _apply_clear_facts(state: QualificationState, facts: Mapping[str, Any]) -> None:
    """Apply only normalized, clear facts; later clear facts overwrite older ones."""
    for key in _STATE_FACT_FIELDS:
        if key in facts and facts[key] is not None:
            setattr(state, key, facts[key])

    if facts.get("tenure_months") is not None and facts.get("tenure_years") is None:
        converted = months_to_years(facts["tenure_months"])
        if converted is not None:
            state.tenure_years = converted

    if facts.get("market_value_unknown") is True:
        state.market_value = "unsure"

    if facts.get("mixed_income_bank_received") is not None:
        answer = facts["mixed_income_bank_received"]
        state.mixed_income_bank_received = bool(answer)
        state.mixed_income_clarification_asked = True
        state.income_mode = "bank" if answer else "cash"

    if state.loan_amount_75_lakh_decision in {"yes", "no"}:
        state.loan_amount_over_limit = True


def _transfer_applies(state: QualificationState, signals: TurnSignals, facts: Mapping[str, Any]) -> bool:
    return bool(
        state.existing_loan_or_emi_request
        or signals.transfer_trigger
        or facts.get("existing_loan_same_property") is True
        or facts.get("emi_reduction_request") is True
        or facts.get("balance_transfer_request") is True
        or facts.get("originals_held_by_bank_for_existing_loan") is True
    )


def _failure(state: QualificationState) -> str | None:
    if state.property_type == "agricultural":
        return "agricultural_property"
    if state.documents_available is False:
        return "original_documents_unavailable"
    if state.income_mode == "cash":
        return "cash_income"
    if state.occupation == "none":
        return "no_job_or_business"
    if state.tenure_years is not None and not (MIN_TENURE_YEARS <= state.tenure_years <= MAX_TENURE_YEARS):
        return "tenure_outside_allowed_range"
    return None


def _next_missing(state: QualificationState) -> str | None:
    if state.property_type is None or state.property_type == "plot_or_land_unresolved":
        return "property_type"
    if state.ownership_status is None:
        return "ownership_status"
    if state.documents_available is None:
        return "documents_available"
    if state.loan_amount_rupees is None:
        return "loan_amount_rupees"
    if state.loan_amount_75_lakh_decision == "pending":
        return "loan_amount_75_lakh_decision"
    if state.occupation is None:
        return "occupation"
    if state.income_mode is None:
        return "income_mode"
    if state.income_mode == "mixed" and state.mixed_income_bank_received is None:
        return "mixed_income_bank_received" if not state.mixed_income_clarification_asked else "mixed_income_unresolved"
    if state.market_value is None:
        return "market_value"
    if state.tenure_years is None:
        return "tenure_years"
    return None


def _eligible_complete(state: QualificationState) -> bool:
    return (
        state.customer_verified is True
        and state.property_type in {"residential", "commercial", "industrial", "residential_cum_commercial"}
        and state.ownership_status in {"sole", "joint"}
        and state.documents_available is True
        and state.loan_amount_rupees is not None
        and state.loan_amount_rupees <= LOAN_LIMIT_RUPEES
        and state.loan_amount_75_lakh_decision != "pending"
        and state.occupation in {"salaried", "self_employed"}
        and state.income_mode == "bank"
        and (state.mixed_income_bank_received is not False or state.mixed_income_clarification_asked is False)
        and state.market_value is not None
        and state.tenure_years is not None
        and MIN_TENURE_YEARS <= state.tenure_years <= MAX_TENURE_YEARS
        and not state.existing_loan_or_emi_request
        and not state.disqualified
    )


def evaluate_turn(
    prior: QualificationState | None = None,
    facts: Mapping[str, Any] | None = None,
    signals: TurnSignals | None = None,
) -> Decision:
    """Update state from a turn and return the deterministic next action.

    Callers must pass normalized facts, not untrusted model guesses. Special
    branches are evaluated before eligibility. Transfer is evaluated before
    failure so a simultaneous transfer/failure resolves to transfer.
    """
    state = QualificationState(**vars(prior)) if prior else QualificationState()
    facts = facts or {}
    signals = signals or TurnSignals()
    _apply_clear_facts(state, facts)

    if state.market_value_asked and state.market_value is None:
        state.market_value = "unsure"

    # Check transfer on every turn, including turns that take another branch.
    transfer = _transfer_applies(state, signals, facts)

    if signals.do_not_call:
        return Decision("end_do_not_call", reason="do_not_call", state=state)
    if signals.wrong_number:
        return Decision("end_wrong_number", reason="wrong_number", state=state)
    if signals.wrong_person:
        return Decision("ask_for_customer_or_callback", reason="wrong_person", state=state)
    if signals.busy:
        if state.callback_time and signals.callback_time_clear:
            return Decision("confirm_callback_and_end", reason="busy_callback", state=state)
        if not state.callback_clarification_asked:
            state.callback_clarification_asked = True
            return Decision("ask_callback_time", reason="busy", state=state)
        return Decision("end_callback_unconfirmed", reason="vague_callback", state=state)
    if signals.not_interested:
        return Decision("thank_and_end", reason="not_interested", state=state)
    if signals.silence:
        return Decision("check_audio_and_end_politely", reason="silence", state=state)
    if signals.abuse:
        if state.abuse_responses == 0:
            state.abuse_responses = 1
            return Decision("calm_response", reason="first_abusive_turn", state=state)
        return Decision("end_politely", reason="continued_abuse", state=state)

    if transfer:
        state.existing_loan_or_emi_request = True
        return Decision("transfer_specialist_and_end", reason="existing_loan_or_emi", state=state)

    if state.customer_verified is not True:
        return Decision("verify_customer", next_field="customer_verified", state=state)

    failure = _failure(state)
    if failure:
        state.disqualified = True
        return Decision("disqualify_and_end", reason=failure, state=state)

    decision = state.loan_amount_75_lakh_decision
    if decision == "no":
        return Decision("end_amount_declined", reason="declined_75_lakh", state=state)
    if state.loan_amount_rupees is not None and state.loan_amount_rupees > LOAN_LIMIT_RUPEES:
        state.loan_amount_over_limit = True
        if decision != "yes":
            state.loan_amount_75_lakh_decision = "pending"
            return Decision("explain_limit_and_ask_to_proceed", next_field="loan_amount_75_lakh_decision", state=state)
        state.loan_amount_rupees = LOAN_LIMIT_RUPEES
    elif decision == "yes":
        state.loan_amount_rupees = LOAN_LIMIT_RUPEES

    missing = _next_missing(state)
    if missing == "mixed_income_bank_received":
        state.mixed_income_clarification_asked = True
        return Decision("ask_mixed_income_bank_clarification", next_field=missing, state=state)
    if missing == "mixed_income_unresolved":
        return Decision("clarification_unresolved", next_field=missing, state=state)
    if missing == "market_value":
        state.market_value_asked = True
    if missing:
        return Decision("ask_next_missing_question", next_field=missing, state=state)

    if _eligible_complete(state):
        return Decision("handoff_to_senior_expert_and_end", reason="all_seven_passed", state=state)
    return Decision("clarification_unresolved", reason="state_not_complete_or_passing", state=state)
