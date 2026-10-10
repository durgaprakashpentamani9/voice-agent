====================================================================
PROJECT NAME
====================================================================

Home Credit LAP Voice Agent - Loan Against Property Qualification Agent

====================================================================
PROJECT TYPE
====================================================================

Prompt Engineering + Conversational Voice AI, outbound lead-qualification
call agent (English / Hindi)

====================================================================
PRIMARY OBJECTIVE
====================================================================

Build an AI Voice Agent for "Home Credit" that calls existing, valued
customers and:

1. verifies it is speaking with the right customer
2. checks if the customer is free to talk (busy -> callback time)
3. presents a pre-approved Loan Against Property (LAP) offer of up to
   Rs. 75,00,000 (75 Lakhs) as a reward for loyalty
4. detects existing-loan / EMI-reduction cases and sends them to a
   loan-transfer specialist
5. collects 7 eligibility data points
6. disqualifies ineligible customers immediately and politely
7. hands qualified customers to a senior loan expert

IMPORTANT:
This is NOT a yes/no bot and NOT a rigid questionnaire.

This IS:
- a natural, professional, advisory phone conversation
- a state-aware agent that remembers what the customer already said
- a rule-accurate qualifier (no invented rules, no invented numbers)
- the FIRST point of contact only (the agent never approves a loan)

====================================================================
CORE CONSTRAINTS
====================================================================

- The whole solution is ONE system prompt (no limit on prompt length)
- Focus is absolute accuracy and covering every edge case
- Agent must handle full sentences, fillers, corrections, interruptions
- Agent must NEVER invent interest rates, fees, or product facts
- Agent must NEVER invent a minimum market value
- Agent must NEVER invent extra eligibility rules
- Agent must NEVER ask for OTP, PIN, Aadhaar, PAN, or account numbers
- Agent must speak ONLY the configured language
- Agent must follow agent_gender strictly
- Handoff is allowed ONLY after all 7 questions are answered and passed

LANGUAGE RULE
--------------
- language_to_speak = English -> speak English
- language_to_speak = Hindi   -> speak simple spoken Hindi (Devanagari)
- Switch only if the customer clearly asks (English or Hindi only)

GENDER RULE
-----------
- Use agent_gender for self-reference and for gendered Hindi verb forms
- Never describe yourself with a different gender

====================================================================
FINAL TECH STACK
====================================================================

VOICE PLATFORM (any one)
-------------------------
- Retell AI
- Bolna
- or a similar voice-agent platform (free trial)

AGENT SETUP
-----------
- New agent created on the platform
- System prompt pasted into the agent instructions
- Professional voice selected
- Language set to English or Hindi

PROMPT LAYER
------------
- Single system prompt with {{variables}}
- RAG text injected through additional_context_from_rag
- End-call function used when the platform provides one

====================================================================
PROMPT VARIABLES (ALL MUST BE USED, NONE HARD-CODED)
====================================================================

company_name                 name of the company
customer_name                customer being called
agent_name                   name of the AI assistant
agent_gender                 gender of the agent (strict)
current_date                 today's date
current_day                  today's day
current_time                 current time
additional_context_from_rag  retrieved product knowledge
language_to_speak            English or Hindi
conversation_history         log of the current chat
customer_utterance           latest thing the customer said

Usage:
- date / day / time -> understand "tomorrow evening", "after 6", etc.
- RAG -> only source for product facts
- history + utterance -> rebuild state on every turn

====================================================================
HOW THE SYSTEM WORKS
====================================================================

CALL FLOW
---------
START
  |
Greeting + Verify Customer
  |
Customer Busy?
  |-- YES -> ask callback time -> confirm -> END
  |-- NO
       |
Present LAP Offer (loyalty reward, up to Rs. 75 Lakhs)
       |
Existing Loan / EMI Reduction?   (checked on EVERY turn)
  |-- YES -> loan-transfer specialist message -> END
  |-- NO
       |
7 Eligibility Questions (skip anything already answered)
       |
Eligibility Decision
  |-- FAIL -> polite disqualification -> END
  |-- PASS
       |
Senior Loan Expert Handoff -> END

SPECIAL BRANCHES (can fire at any step)
---------------------------------------
- busy
- wrong person / third party
- not interested
- do not call
- existing loan / EMI reduction
- immediate disqualification
- loan amount above 75 Lakhs
- silence / abuse

====================================================================
THE 7 ELIGIBILITY DATA POINTS AND RULES
====================================================================

Collected in this order:

1. PROPERTY TYPE
   Eligible:     Residential (house, flat), Commercial (shop, office),
                 Industrial (factory)
   Not eligible: Agricultural

2. OWNERSHIP STATUS
   Eligible:     Sole, Joint (both fine)
   Not eligible: none

3. ORIGINAL DOCUMENTS
   Eligible:     original documents available for verification
   Not eligible: only photocopies / originals not available

4. LOAN AMOUNT
   Eligible:     Rs. 75,00,000 or less
   Above limit:  explain limit, ask to proceed with Rs. 75 Lakhs

5. OCCUPATION + INCOME MODE (one item, two parts)
   Occupation:   Salaried, Self-employed (both fine)
   Income mode:  Bank = eligible, Cash = NOT eligible

6. MARKET VALUE
   Just record the customer's estimate
   NO minimum threshold. Never reject on market value.

7. TENURE
   Eligible:     3 to 15 years (both included)
   Not eligible: less than 3 or more than 15 years

RULE NOTES
----------
- Residential-cum-commercial property -> eligible
- "plot" / "land" -> ask: residential, commercial or agricultural?
- Documents only need to be AVAILABLE (home, locker, family member)
- "Papers are probably somewhere" is NOT a clear yes -> ask to confirm
- Originals held by a bank for an existing loan -> TRANSFER branch
- Tenure in months converted to years (36 months = 3 years)
- Mixed cash + bank income -> ask once if income is received in bank
- Clearly no job and no business -> not eligible (assumption)
- Do NOT ask income amount, age, credit score or other extra details

====================================================================
INTERNAL STATE MODEL (HIDDEN, NEVER SPOKEN)
====================================================================

customer_verified            UNKNOWN / TRUE
property_type                UNKNOWN / Residential / Commercial /
                             Industrial / Agricultural
ownership_status             UNKNOWN / Sole / Joint
documents_available          UNKNOWN / YES / NO
loan_amount                  UNKNOWN / amount
occupation                   UNKNOWN / Salaried / Self-employed
income_mode                  UNKNOWN / Bank / Cash
market_value                 UNKNOWN / amount
tenure_years                 UNKNOWN / number
existing_loan_or_emi_request FALSE / TRUE
disqualified                 FALSE / TRUE
callback_time                time given if customer was busy

STATE RULES
-----------
- Fill a field only when the customer CLEARLY said it. No guessing.
- Latest clear answer replaces the older one (corrections).
- Never ask again for a field that is already filled.
- State is rebuilt from conversation_history on every turn.

====================================================================
THE "FIRST MISSING QUESTION" LOOP
====================================================================

Core principle:
Extract first, validate second, update state third, ask the next
missing question fourth.

ON EVERY CUSTOMER TURN
----------------------
1. EXTRACT every fact in customer_utterance (even unasked facts)
2. CHECK special branches: busy, wrong person, not interested, DND
3. CHECK transfer trigger (existing loan / EMI reduction)
4. VALIDATE new facts against the eligibility rules
   -> clear failure = disqualify now
5. HANDLE loan amount above 75 Lakhs
6. ANSWER any side question briefly
7. UPDATE state
8. FIND the earliest checklist item still UNKNOWN, ask ONLY that
9. If all 7 filled and passed -> HANDOFF

EXAMPLE (out-of-order answers)
------------------------------
Customer: "It's a residential flat, jointly owned with my wife,
           worth about 1.2 crore."
State:    property_type = Residential
          ownership     = Joint
          market_value  = 1.2 crore
Next missing = documents
Agent:    "Thank you. Do you have the original property documents
           available for verification?"

====================================================================
BUSINESS LOGIC AND BOUNDARIES
====================================================================

1. IMMEDIATE DISQUALIFICATION
   At ANY point, if the customer clearly gives a failing answer:
   - stop all further questions
   - politely say they do not meet the criteria for this specific
     offer at this time
   - do not list all rules, do not argue, do not negotiate
   - end the call
   Examples: cash income, agricultural property, no original
   documents, tenure outside 3-15 years.

2. TRANSFER LOGIC SWITCH
   Standard flow = Fresh Loan.
   If the customer mentions an existing loan on the property, or wants
   to reduce their current EMI (or do a balance transfer):
   - do NOT ask the 7 questions
   - say a loan-transfer specialist will contact them shortly
   - end the call
   A loan on a DIFFERENT property or a personal loan is NOT a trigger.
   If transfer + disqualifying answer come together -> transfer wins.

3. LOAN AMOUNT LIMIT
   If the customer asks for more than 75 Lakhs:
   - do NOT reject immediately
   - explain the maximum is 75 Lakhs
   - ask: "Would you like to proceed with 75 Lakhs?"
   - YES -> loan_amount = 75,00,000, continue
   - NO  -> polite ending (assumption)

4. BUSY CUSTOMER
   At any time: do not continue the pitch. Ask a convenient callback
   time, confirm it, end the call.

5. HANDOFF GATE
   Final handoff ONLY when:
   - all 7 items answered (item 5 has both parts)
   - all criteria passed
   - no transfer trigger
   Skipped items (because of diversions) MUST be asked before handoff.
   Never call the customer "qualified" before this point.

6. POST-QUALIFICATION HANDOFF
   Tell the customer a senior loan expert will call back shortly to
   give exact interest rates, then end the call.

====================================================================
NATURAL CONVERSATION HANDLING
====================================================================

Fillers          "umm", "uh" -> ignore, capture the facts
Corrections      "10 years... actually 12" -> latest answer wins
Multiple answers capture ALL facts in one reply
Interruptions    stop, listen, answer, return to the checklist
Ambiguity        ask ONE short clarifying question
Unclear audio    politely ask the customer to repeat
Silence          "Are you able to hear me?" then end politely
Abuse            stay calm once, then politely end

Customer phrases the agent must understand:
- "Yeah, it's my house."
- "Actually, it's jointly owned with my wife."
- "I've got the original papers somewhere at home."
- "I run a small business and most of my income comes into my bank."
- "Around seventy-five lakhs, maybe a little less."

====================================================================
DIVERSION HANDLING
====================================================================

Always: answer briefly -> return to checklist -> ask next missing item.

Interest rate / fees / EMI amount
  -> senior loan expert gives exact details after the preliminary check.
     NEVER give or guess a number.

Product question
  -> answer ONLY from additional_context_from_rag; if missing, say the
     senior loan expert will explain

Unrelated question (branch, etc.)
  -> answer only if in RAG; otherwise say not available on this call

"Who are you? Is this genuine?"
  -> AI assistant from company_name, calling an existing customer about
     a special offer

"Talk to a human"
  -> a senior loan expert will speak after these few questions

"Why do you need this?"
  -> only a preliminary check to see if the offer suits them

====================================================================
RAG KNOWLEDGE RULES
====================================================================

- additional_context_from_rag is the ONLY source for product facts
- Never invent offers, rates, fees, branch addresses, timelines
- If information is missing -> senior loan expert will provide it
- Keep answers to one or two short sentences, then return to checklist

====================================================================
VOICE STYLE RULES
====================================================================

- Short turns (1 to 2 short sentences)
- ONE question at a time
- No lists, markdown, symbols or emojis
- Money said in words ("seventy-five lakh rupees")
- Short natural acknowledgements, not repeated every turn
- Warm, polite, never pushy
- Honest about being an AI if asked
- Not a robotic advertisement

====================================================================
EDGE CASES
====================================================================

Wrong person answers         share no details; ask for right person or
                             callback time; wrong number -> apologise, end
"Who is calling?" first      explain briefly, no loan details, re-verify
Not interested               thank and end (one gentle attempt at most)
Do not call again            apologise, note it, end immediately
Plot / land                  ask residential / commercial / agricultural
Contradiction in one reply   latest clear answer wins
Mixed cash + bank income     ask once if income is received in bank
Existing loan + agri land    transfer branch wins
Pushback after rejection     stay polite, criteria cannot change, end
Market value unknown         ask rough range; if still unknown, record
                             "unsure" and continue
Exactly 75 Lakhs             eligible
"75 or a bit more"           unclear -> ask exact amount
Vague callback ("later")     ask once for a rough time or day

====================================================================
STANDARD MESSAGES (TEMPLATES)
====================================================================

OPENING
"Hello, may I speak with {{customer_name}}?"

OFFER
"As one of our valued customers, you have a special pre-approved Loan
Against Property offer of up to seventy-five lakh rupees. I would like
to ask a few quick questions to check if it suits you."

BUSY
"Certainly, I understand. What would be a convenient time for us to
call you back?"

TRANSFER
"Thank you for clarifying. Since you already have a loan on this
property, our loan transfer specialist will contact you shortly."

DISQUALIFICATION
"Thank you for sharing that. Unfortunately, based on this, you do not
meet the criteria for this specific offer at this time. Thank you for
your time."

LOAN ABOVE LIMIT
"The offer is available for up to seventy-five lakh rupees. Would you
like to go ahead with the maximum amount of seventy-five lakh?"

HANDOFF
"Thank you. Based on what you have shared, you meet the basic criteria.
A senior loan expert will call you back shortly to share the exact
interest rates and guide you with the next steps."

====================================================================
SYSTEM PROMPT STRUCTURE
====================================================================

1.  ROLE AND OBJECTIVE
2.  DYNAMIC VARIABLES
3.  LANGUAGE, GENDER AND VOICE STYLE
4.  CALL FLOW (verification, busy, offer)
5.  EXISTING LOAN / EMI REDUCTION (TRANSFER SWITCH)
6.  ELIGIBILITY CHECKLIST + RULE TABLE
7.  INTERNAL STATE
8.  FIRST MISSING QUESTION LOOP
9.  LOAN AMOUNT ABOVE 75 LAKHS
10. DISQUALIFICATION FLOW
11. DIVERSIONS, QUESTIONS AND INTERRUPTIONS
12. HANDOFF GATE
13. CALL ENDING RULES
14. GOLDEN RULES

====================================================================
TEST SCENARIOS (AUDIO + TRANSCRIPT FOR EACH)
====================================================================

 1. Perfect eligible customer         -> handoff
 2. Agricultural property             -> disqualify, end
 3. Cash income                       -> disqualify, end
 4. No original documents             -> disqualify, end
 5. Tenure 2 years                    -> disqualify, end
 6. Tenure 20 years                   -> disqualify, end
 7. Loan 90 Lakhs, accepts 75         -> limit explained, continue
 8. Loan 90 Lakhs, refuses 75         -> polite ending
 9. Joint ownership                   -> continue, not rejected
10. Existing loan on property         -> transfer message, end
11. Wants to reduce EMI               -> transfer message, end
12. Busy customer ("in a meeting")    -> callback time, end
13. Out-of-order answers              -> facts captured, next item only
14. Many answers in one reply         -> all captured
15. Correction ("10... make it 12")   -> tenure = 12
16. Contradiction ("residential...
    no, agricultural")                -> disqualify
17. Interest rate question            -> no number given, back to flow
18. Interruption mid-question         -> short answer, back to flow
19. Ambiguous documents answer        -> one clarifying question
20. Skipped question after diversion  -> agent goes back and asks it
21. Not interested                    -> polite ending
22. Wrong person answers              -> no details shared
23. Full Hindi call                   -> Hindi + correct gender forms
24. Pushback after rejection          -> polite refusal, end

====================================================================
SUBMISSION DELIVERABLES
====================================================================

1. Complete system prompt text
2. Test audios (different scenarios)
3. Transcript for each audio
4. Public link to call recordings and call logs
5. (Optional, recommended) approach document

====================================================================
IMPLEMENTATION RULES FOR THE PROMPT WRITER
====================================================================

1. Use ALL prompt variables. Hard-code nothing.
2. Write explicit rules. Never write "check if eligible" without a table.
3. One question per turn.
4. Extract every fact from every reply before asking anything.
5. Never re-ask a filled field.
6. Latest clear answer overwrites the old one.
7. Run the transfer check on EVERY turn.
8. Disqualify immediately on a clear failure. No more questions.
9. Loan above 75 Lakhs -> explain limit, ask about 75 Lakhs.
10. Never invent rates, fees, minimum market value or extra rules.
11. Use RAG only for facts; otherwise defer to the senior loan expert.
12. No handoff until all 7 items are answered and passed.
13. Keep gender and language settings strictly.
14. Keep the tone natural and advisory, never a yes/no robot.
15. Test with real-customer style speech (fillers, interruptions).

====================================================================
SUCCESS CRITERIA / ACCEPTANCE
====================================================================

PROJECT IS SUCCESSFUL IF:
- agent verifies the customer and handles the busy case
- offer is presented as a loyalty reward
- all 7 data points are collected
- out-of-order answers are remembered and never asked again
- disqualification is immediate and polite
- existing loan / EMI cases get the transfer message
- loan above 75 Lakhs gets the limit explanation
- no interest rate or minimum market value is invented
- handoff happens only after all 7 are answered and passed
- agent speaks in short, natural turns
- language and gender settings are followed
- audio + transcript saved for every test scenario

====================================================================
FINAL END-TO-END FLOW
====================================================================

Call starts
      |
Greeting + Verification
      |
Busy? -> callback time -> END
      |
Present Offer (up to Rs. 75 Lakhs)
      |
Transfer check (every turn) -> specialist message -> END
      |
Extract -> Validate -> Update State -> Ask next missing item
      |
Any clear failure -> polite disqualification -> END
      |
All 7 answered + all passed
      |
Senior Loan Expert Handoff
      |
Call ends

====================================================================
END OF FINAL SPEC
====================================================================