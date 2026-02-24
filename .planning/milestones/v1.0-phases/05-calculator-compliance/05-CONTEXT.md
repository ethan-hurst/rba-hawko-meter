# Phase 5: Calculator & Compliance - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Mortgage impact calculator with scenario slider, plus full compliance audit ensuring all content meets ASIC RG 244 requirements. Covers calculator UI, repayment math, localStorage persistence, disclaimer text, and neutral language enforcement. Does NOT add new data sources or visualization types.

</domain>

<decisions>
## Implementation Decisions

### Calculator Inputs
- **5 fields:** Loan amount, remaining term, current rate, repayment type (P&I vs IO), repayment frequency (monthly/fortnightly/weekly)
- **Pre-filled with Australian averages** — ~$600k loan, 25yr term, current RBA rate. User adjusts as needed
- Stored in localStorage (no login required)

### Scenario Slider
- **Range:** 0% to 10% — covers full historical range including extreme scenarios
- **Steps:** 0.25% increments (matches RBA's typical move size)
- **Visual feedback:** Both live repayment update AND comparison table
  - Monthly repayment changes in real-time as user slides
  - Comparison shows: current vs scenario monthly difference, annual difference, total interest difference

### Disclaimer Language
- **Plain English** — "This tool shows data, not advice. Talk to a financial adviser before making decisions."
- **Footer only** — standard footer disclaimer visible on every page
- No expandable legal text — keep it simple and readable

### Compliance Guardrails
- **Educational framing** for the calculator: "See how rate changes affect a typical mortgage" — not "your" mortgage
- Neutral language enforcement approach: Claude's discretion on whether to use a formal word list or principle-based approach
- Key principle: present data neutrally, never imply action

### Claude's Discretion
- Exact neutral language enforcement approach (word list vs principle-based)
- Calculator layout and input styling
- Repayment calculation edge cases
- Additional disclaimer placement near calculator if needed for ASIC compliance beyond footer

</decisions>

<specifics>
## Specific Ideas

- Educational framing is critical — "See how rate changes affect a typical mortgage" not "your mortgage"
- Plain English disclaimer, not legal jargon — aligns with "Data, not opinion" ethos
- 0.25% slider steps match RBA's actual move increments — intuitive for users
- Comparison table alongside live update gives users both immediate feedback and detailed analysis

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-calculator-compliance*
*Context gathered: 2026-02-04*
