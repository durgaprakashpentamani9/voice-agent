# Approach

I used `spec.md` as the sole source for the prompt rules and kept the system prompt in the required fourteen-section order. The eligibility table spells out each accepted answer, failure, boundary, and clarification so the agent does not need to guess what “eligible” means. Market value is recorded only; no minimum is applied. The prompt also prohibits collecting sensitive identifiers or asking for extra eligibility details.

The hidden state records customer verification, each of the seven data points, transfer status, disqualification, and callback time. It distinguishes residential-cum-commercial property, unresolved plot or land, mixed cash-and-bank income, the answer to the one-time bank-income clarification, and a pending decision about proceeding at seventy-five lakh. A value remains unknown until clearly stated. Later clear corrections replace earlier answers. Market value recorded as “unsure” completes that item; occupation and income mode must both be known to complete item five.

On every turn, the agent extracts all stated facts, checks special branches, checks for transfer, validates facts, updates the state, answers permitted diversions, and asks only the earliest missing question. It handles out-of-order answers and returns to any item skipped during a diversion. A transfer trigger takes priority over a disqualifying answer in the same turn. Handoff is allowed only when all seven items are complete and passed, with no transfer trigger.

Special handling covers busy callbacks, wrong persons and wrong numbers, not-interested and do-not-call requests, above-limit loan requests, immediate rejection, interruptions, unclear answers, silence, and abuse. Product facts come only from the RAG context. Rates, fees, EMI amounts, and unavailable product information are deferred to a senior loan expert. Short turns, one question at a time, configured language, and strict configured agent gender guide the spoken style.

Testing was prepared as a 24-scenario checklist and reviewed against the matching cases in `spec.md`, including transfer priority, corrections, diversions, and above-limit decisions. These are written test cases only; no voice-platform calls, audio recordings, or transcripts have been created. The test file gives the procedure for recording separate audio and saving a matching transcript for each scenario on the selected platform.

## Assumptions explicitly stated in `spec.md`

- Clearly having no job and no business means the customer is not eligible.
- If the customer asks for more than seventy-five lakh and declines the seventy-five-lakh option, end politely.
