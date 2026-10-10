from decimal import Decimal
import unittest

from lap_agent.qualification import (
    LOAN_LIMIT_RUPEES,
    QualificationState,
    TurnSignals,
    evaluate_turn,
    months_to_years,
)


def passing_facts(**changes):
    facts = {
        "customer_verified": True,
        "property_type": "residential",
        "ownership_status": "sole",
        "documents_available": True,
        "loan_amount_rupees": Decimal("5000000"),
        "occupation": "salaried",
        "income_mode": "bank",
        "market_value": Decimal("1"),
        "tenure_years": Decimal("10"),
    }
    facts.update(changes)
    return facts


class EligibilityRuleTests(unittest.TestCase):
    def test_all_seven_complete_pass_and_handoff(self):
        result = evaluate_turn(facts=passing_facts())
        self.assertEqual(result.action, "handoff_to_senior_expert_and_end")

    def test_joint_ownership_is_eligible(self):
        result = evaluate_turn(facts=passing_facts(ownership_status="joint"))
        self.assertEqual(result.action, "handoff_to_senior_expert_and_end")

    def test_residential_commercial_is_eligible(self):
        result = evaluate_turn(facts=passing_facts(property_type="residential_cum_commercial"))
        self.assertEqual(result.action, "handoff_to_senior_expert_and_end")

    def test_agricultural_is_immediate_failure(self):
        result = evaluate_turn(facts=passing_facts(property_type="agricultural"))
        self.assertEqual(result.reason, "agricultural_property")
        self.assertTrue(result.state.disqualified)

    def test_unresolved_plot_is_not_guessed(self):
        result = evaluate_turn(facts={"customer_verified": True, "property_type": "plot_or_land_unresolved"})
        self.assertEqual(result.next_field, "property_type")

    def test_no_original_documents_fails(self):
        result = evaluate_turn(facts=passing_facts(documents_available=False))
        self.assertEqual(result.reason, "original_documents_unavailable")

    def test_cash_income_fails(self):
        result = evaluate_turn(facts=passing_facts(income_mode="cash"))
        self.assertEqual(result.reason, "cash_income")

    def test_mixed_income_asks_once_and_bank_answer_passes(self):
        result = evaluate_turn(facts=passing_facts(income_mode="mixed"))
        self.assertEqual(result.action, "ask_mixed_income_bank_clarification")
        followup = evaluate_turn(result.state, {"mixed_income_bank_received": True})
        self.assertEqual(followup.state.income_mode, "bank")
        self.assertTrue(followup.state.mixed_income_clarification_asked)
        self.assertEqual(followup.action, "handoff_to_senior_expert_and_end")

    def test_mixed_income_not_received_in_bank_fails(self):
        result = evaluate_turn(facts=passing_facts(income_mode="mixed"))
        followup = evaluate_turn(result.state, {"mixed_income_bank_received": False})
        self.assertEqual(followup.action, "disqualify_and_end")

    def test_no_job_and_no_business_assumption_fails(self):
        result = evaluate_turn(facts=passing_facts(occupation="none"))
        self.assertEqual(result.reason, "no_job_or_business")

    def test_exact_limit_passes(self):
        result = evaluate_turn(facts=passing_facts(loan_amount_rupees=LOAN_LIMIT_RUPEES))
        self.assertEqual(result.action, "handoff_to_senior_expert_and_end")

    def test_above_limit_waits_for_yes(self):
        result = evaluate_turn(facts=passing_facts(loan_amount_rupees=Decimal("9000000")))
        self.assertEqual(result.action, "explain_limit_and_ask_to_proceed")
        self.assertEqual(result.state.loan_amount_75_lakh_decision, "pending")
        accepted = evaluate_turn(result.state, {"loan_amount_75_lakh_decision": "yes"})
        self.assertEqual(accepted.state.loan_amount_rupees, LOAN_LIMIT_RUPEES)
        self.assertEqual(accepted.action, "handoff_to_senior_expert_and_end")

    def test_above_limit_no_ends_politely(self):
        result = evaluate_turn(facts=passing_facts(loan_amount_rupees=Decimal("9000000")))
        declined = evaluate_turn(result.state, {"loan_amount_75_lakh_decision": "no"})
        self.assertEqual(declined.action, "end_amount_declined")

    def test_market_value_has_no_minimum_and_unsure_is_complete(self):
        result = evaluate_turn(facts=passing_facts(market_value=Decimal("1")))
        self.assertEqual(result.action, "handoff_to_senior_expert_and_end")
        unsure = evaluate_turn(facts=passing_facts(market_value="unsure"))
        self.assertEqual(unsure.action, "handoff_to_senior_expert_and_end")

    def test_unknown_market_value_after_question_becomes_unsure(self):
        first = evaluate_turn(facts=passing_facts(market_value=None, tenure_years=None))
        self.assertEqual(first.next_field, "market_value")
        second = evaluate_turn(first.state, {"tenure_years": Decimal("10")})
        self.assertEqual(second.state.market_value, "unsure")
        self.assertEqual(second.action, "handoff_to_senior_expert_and_end")

    def test_tenure_boundaries_are_inclusive(self):
        for years in (Decimal("3"), Decimal("15")):
            with self.subTest(years=years):
                self.assertEqual(evaluate_turn(facts=passing_facts(tenure_years=years)).action,
                                 "handoff_to_senior_expert_and_end")

    def test_tenure_outside_bounds_fails(self):
        for years in (Decimal("2"), Decimal("16")):
            with self.subTest(years=years):
                self.assertEqual(evaluate_turn(facts=passing_facts(tenure_years=years)).reason,
                                 "tenure_outside_allowed_range")

    def test_tenure_months_conversion(self):
        self.assertEqual(months_to_years(36), Decimal("3"))
        self.assertEqual(months_to_years(180), Decimal("15"))

    def test_transfer_wins_over_simultaneous_failure(self):
        result = evaluate_turn(
            facts=passing_facts(property_type="agricultural"),
            signals=TurnSignals(transfer_trigger=True),
        )
        self.assertEqual(result.action, "transfer_specialist_and_end")
        self.assertFalse(result.state.disqualified)

    def test_different_property_loan_alone_is_not_transfer(self):
        result = evaluate_turn(facts=passing_facts(), signals=TurnSignals())
        self.assertEqual(result.action, "handoff_to_senior_expert_and_end")

    def test_personal_loan_alone_is_not_transfer(self):
        result = evaluate_turn(facts=passing_facts(personal_loan_only=True))
        self.assertEqual(result.action, "handoff_to_senior_expert_and_end")

    def test_originals_held_by_bank_for_existing_loan_triggers_transfer(self):
        result = evaluate_turn(facts=passing_facts(originals_held_by_bank_for_existing_loan=True))
        self.assertEqual(result.action, "transfer_specialist_and_end")

    def test_latest_clear_fact_replaces_prior_fact(self):
        initial = QualificationState(tenure_years=Decimal("10"), customer_verified=True)
        corrected = evaluate_turn(initial, {"tenure_years": Decimal("12")})
        self.assertEqual(corrected.state.tenure_years, Decimal("12"))

    def test_first_missing_question_skips_filled_fields(self):
        result = evaluate_turn(facts={
            "customer_verified": True,
            "property_type": "residential",
            "ownership_status": "joint",
            "market_value": Decimal("10000000"),
        })
        self.assertEqual(result.next_field, "documents_available")

    def test_do_not_call_ends_immediately(self):
        result = evaluate_turn(facts=passing_facts(property_type="agricultural"),
                               signals=TurnSignals(do_not_call=True))
        self.assertEqual(result.action, "end_do_not_call")

    def test_busy_requests_callback_and_does_not_continue_checklist(self):
        result = evaluate_turn(facts=passing_facts(property_type="agricultural"),
                               signals=TurnSignals(busy=True))
        self.assertEqual(result.action, "ask_callback_time")

    def test_wrong_person_shares_no_eligibility_result(self):
        result = evaluate_turn(facts=passing_facts(property_type="agricultural"),
                               signals=TurnSignals(wrong_person=True))
        self.assertEqual(result.action, "ask_for_customer_or_callback")

    def test_abuse_allows_one_calm_response_then_ends(self):
        first = evaluate_turn(signals=TurnSignals(abuse=True))
        self.assertEqual(first.action, "calm_response")
        second = evaluate_turn(first.state, signals=TurnSignals(abuse=True))
        self.assertEqual(second.action, "end_politely")

    def test_not_interested_ends(self):
        result = evaluate_turn(signals=TurnSignals(not_interested=True))
        self.assertEqual(result.action, "thank_and_end")


if __name__ == "__main__":
    unittest.main()
