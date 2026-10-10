"""Deterministic policy coverage for all 24 scenarios in test_scenarios.md."""

from dataclasses import dataclass
from decimal import Decimal
import re
import unittest
from pathlib import Path

from lap_agent.qualification import QualificationState, TurnSignals, evaluate_turn


ROOT = Path(__file__).resolve().parents[1]


def passing(**changes):
    facts = {
        "customer_verified": True,
        "property_type": "residential",
        "ownership_status": "sole",
        "documents_available": True,
        "loan_amount_rupees": Decimal("5000000"),
        "occupation": "salaried",
        "income_mode": "bank",
        "market_value": Decimal("10000000"),
        "tenure_years": Decimal("10"),
    }
    facts.update(changes)
    return facts


@dataclass(frozen=True)
class TurnCase:
    facts: dict
    expected_action: str
    expected_field: str | None = None
    signals: TurnSignals = TurnSignals()


@dataclass(frozen=True)
class Scenario:
    number: int
    name: str
    turns: tuple[TurnCase, ...]
    initial_state: QualificationState | None = None


SCENARIOS = [
    Scenario(1, "Perfect eligible customer", (TurnCase(passing(), "handoff_to_senior_expert_and_end"),)),
    Scenario(2, "Agricultural property", (TurnCase(passing(property_type="agricultural"), "disqualify_and_end"),)),
    Scenario(3, "Cash-only income", (TurnCase(passing(income_mode="cash"), "disqualify_and_end"),)),
    Scenario(4, "No original documents", (TurnCase(passing(documents_available=False), "disqualify_and_end"),)),
    Scenario(5, "Tenure 2 years", (TurnCase(passing(tenure_years=Decimal("2")), "disqualify_and_end"),)),
    Scenario(6, "Tenure 20 years", (TurnCase(passing(tenure_years=Decimal("20")), "disqualify_and_end"),)),
    Scenario(7, "Loan 90 Lakhs, accepts 75", (
        TurnCase(passing(loan_amount_rupees=Decimal("9000000")), "explain_limit_and_ask_to_proceed"),
        TurnCase({"loan_amount_75_lakh_decision": "yes"}, "handoff_to_senior_expert_and_end"),
    )),
    Scenario(8, "Loan 90 Lakhs, refuses 75", (
        TurnCase(passing(loan_amount_rupees=Decimal("9000000")), "explain_limit_and_ask_to_proceed"),
        TurnCase({"loan_amount_75_lakh_decision": "no"}, "end_amount_declined"),
    )),
    Scenario(9, "Joint ownership", (TurnCase(passing(ownership_status="joint"), "handoff_to_senior_expert_and_end"),)),
    Scenario(10, "Existing loan plus disqualifying answer", (
        TurnCase(passing(property_type="agricultural", existing_loan_same_property=True), "transfer_specialist_and_end"),
    )),
    Scenario(11, "Wants to reduce EMI", (
        TurnCase(passing(emi_reduction_request=True), "transfer_specialist_and_end"),
    )),
    Scenario(12, "Busy customer", (
        TurnCase({"callback_time": "tomorrow after four"}, "confirm_callback_and_end",
                 signals=TurnSignals(busy=True, callback_time_clear=True)),
    )),
    Scenario(13, "Out-of-order answers", (
        TurnCase({"customer_verified": True, "property_type": "residential", "ownership_status": "joint",
                  "market_value": Decimal("12000000")}, "ask_next_missing_question", "documents_available"),
        TurnCase({"documents_available": True}, "ask_next_missing_question", "loan_amount_rupees"),
    )),
    Scenario(14, "Many answers and mixed income", (
        TurnCase({"customer_verified": True, "property_type": "commercial", "ownership_status": "sole",
                  "documents_available": True, "loan_amount_rupees": Decimal("4000000"),
                  "occupation": "self_employed", "income_mode": "mixed", "market_value": Decimal("8000000"),
                  "tenure_years": Decimal("8")}, "ask_mixed_income_bank_clarification", "mixed_income_bank_received"),
    )),
    Scenario(15, "Correction from 10 to 12 years", (
        TurnCase({"tenure_years": Decimal("12")}, "handoff_to_senior_expert_and_end"),
    ), initial_state=QualificationState(customer_verified=True, property_type="residential", ownership_status="sole",
        documents_available=True, loan_amount_rupees=Decimal("5000000"), occupation="salaried", income_mode="bank",
        market_value=Decimal("10000000"), tenure_years=Decimal("10"))),
    Scenario(16, "Contradiction ending in agricultural", (
        TurnCase(passing(property_type="agricultural"), "disqualify_and_end"),
    )),
    Scenario(17, "Interest-rate diversion", (
        TurnCase({}, "ask_next_missing_question", "loan_amount_rupees"),
    ), initial_state=QualificationState(customer_verified=True, property_type="residential", ownership_status="sole",
        documents_available=True)),
    Scenario(18, "Interruption mid-question", (
        TurnCase({}, "ask_next_missing_question", "property_type"),
    ), initial_state=QualificationState(customer_verified=True)),
    Scenario(19, "Plot and unclear documents", (
        TurnCase({"customer_verified": True, "property_type": "plot_or_land_unresolved"},
                 "ask_next_missing_question", "property_type"),
    )),
    Scenario(20, "Skipped question after diversion", (
        TurnCase({"customer_verified": True, "property_type": "residential", "ownership_status": "joint"},
                 "ask_next_missing_question", "documents_available"),
        TurnCase({"documents_available": True}, "ask_next_missing_question", "loan_amount_rupees"),
    )),
    Scenario(21, "Not interested", (
        TurnCase({}, "thank_and_end", signals=TurnSignals(not_interested=True)),
    )),
    Scenario(22, "Wrong person answers", (
        TurnCase({}, "ask_for_customer_or_callback", signals=TurnSignals(wrong_person=True)),
    )),
    Scenario(23, "Full Hindi call", (
        TurnCase({}, "ask_next_missing_question", "property_type"),
    ), initial_state=QualificationState(customer_verified=True)),
    Scenario(24, "Pushback after rejection", (
        TurnCase({"property_type": "agricultural"}, "disqualify_and_end"),
    ), initial_state=QualificationState(customer_verified=True, property_type="agricultural", disqualified=True)),
]


class TwentyFourScenarioTests(unittest.TestCase):
    def test_all_scenario_rows_have_policy_expectations(self):
        doc = (ROOT / "test_scenarios.md").read_text(encoding="utf-8")
        markdown_numbers = [int(number) for number in re.findall(r"(?m)^\|\s*(\d+)\s*\|", doc)]
        self.assertEqual(markdown_numbers, list(range(1, 25)))
        self.assertEqual([scenario.number for scenario in SCENARIOS], list(range(1, 25)))

    def test_policy_action_for_each_of_24_scenarios(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario.number, name=scenario.name):
                state = scenario.initial_state
                for turn in scenario.turns:
                    result = evaluate_turn(state, turn.facts, turn.signals)
                    self.assertEqual(result.action, turn.expected_action)
                    if turn.expected_field is not None:
                        self.assertEqual(result.next_field, turn.expected_field)
                    state = result.state

    def test_prompt_contains_bilingual_and_handoff_contract(self):
        prompt = (ROOT / "system_prompt.md").read_text(encoding="utf-8")
        for token in ("{{company_name}}", "{{customer_name}}", "{{agent_name}}", "{{agent_gender}}",
                      "{{current_date}}", "{{current_day}}", "{{current_time}}",
                      "{{additional_context_from_rag}}", "{{language_to_speak}}",
                      "{{conversation_history}}", "{{customer_utterance}}"):
            self.assertIn(token, prompt)
        self.assertIn("simple Hindi in Devanagari", prompt)
        self.assertIn("Do not hand off until every one of the seven items is complete and passed", prompt)
        self.assertIn("transfer takes priority", prompt)


if __name__ == "__main__":
    unittest.main()
