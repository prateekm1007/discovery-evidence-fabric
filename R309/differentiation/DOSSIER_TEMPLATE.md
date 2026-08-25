# Differentiation Dossier Template — R309

**Authority:** Article XXXVI §9 (the differentiation dossier is not a patent judgment)
**Commercial interpretation (CEO directive, R275):** We are not a patent office. We build the strongest technical argument, strongest prior-art position in our favor, strongest economic case, and strongest reproducible technology-transfer package. The buyer's counsel handles legal diligence.

---

## What this dossier is

A document that a buyer's counsel can use to begin legal diligence. It surfaces:

1. The closest prior art we found.
2. What that art appears to teach.
3. What our system adds.
4. Why we believe the technical effect is different.
5. The remaining uncertainties.
6. The questions we recommend buyer counsel examine.

That is the full extent of the dossier's job.

---

## What this dossier is NOT

- A patentability opinion. We do not render §102/§103 verdicts.
- An advocacy document. We surface threats, not just favorable art.
- A substitute for buyer counsel. The buyer's counsel decides; we surface.
- A marketing brief. The executive_brief.md (in commercial/) is the marketing document.

---

## Required files

```
differentiation/
  prior_art.md           # C16, C18: closest art + known threats
  technical_delta.md     # C17: what our system adds
  know_how.md            # C19: trade-secret components
  counsel_questions.md   # C20: questions for buyer counsel
```

---

## Template: `prior_art.md`

```markdown
# Prior-Art Landscape — <candidate_id>

## Closest published art

### Reference 1
- **Citation:** <full citation, with DOI/URL>
- **What it teaches:** <one-paragraph summary of the reference's actual content>
- **Why it is close:** <one-paragraph explanation of why this is the closest art>
- **Source provenance:**
  - Search query: <exact query string>
  - Database: <e.g., USPTO, EPO, Google Patents, PubMed, OpenAlex>
  - Result rank: <position in result list>
  - Date of search: <ISO timestamp>

### Reference 2
... (repeat for each close reference; minimum 3, typically 5–10)

## Known third-party claims / patents that could matter (THREATS)

### Threat 1
- **Patent/application number:** <e.g., US12636471B2>
- **What it claims:** <one-paragraph summary>
- **Why it could matter:** <one-paragraph explanation>
- **Our assessment:** <one-paragraph honest assessment — is it a real threat, a watch item, or likely immaterial?>
- **Source provenance:** (same fields as above)

... (repeat for each threat)

## Search saturation evidence

- Total queries executed: <N>
- Databases covered: <list>
- Result saturation: <yes/no — did results plateau after N queries?>
- Negative-search provenance: <per R274 — queries → databases → results → exclusions>

## Honest summary

<2-3 paragraphs. What is the prior-art landscape? How close is the closest art? Are there credible threats?>
```

---

## Template: `technical_delta.md`

```markdown
# Technical Delta — <candidate_id>

## What our system adds

### The mechanism (per mechanism.md)
<one-paragraph restatement of the mechanism, citing technology/mechanism.md>

### The technical effect
<one-paragraph statement of the technical effect our system produces that the closest prior art does not>

### Why we believe the effect is different
<one-paragraph argument. Reference specific elements of the prior art and specific elements of our system.>

## Quantitative comparison

| Metric | Closest prior art | Our system | Delta |
|--------|------------------:|-----------:|------:|
| <metric 1> | <value + citation> | <value + evidence_tier> | <delta> |
| <metric 2> | ... | ... | ... |

## Remaining uncertainties

- <uncertainty 1: what we don't know that could change this delta>
- <uncertainty 2: ...>

## Boundaries of the argument

<one-paragraph. What this argument is NOT claiming. E.g., "We are not claiming the mechanism is novel as a general principle. We are claiming the specific application to <X> produces a technical effect not demonstrated in the prior art.">
```

---

## Template: `know_how.md`

```markdown
# Trade-Secret / Know-How Components — <candidate_id>

## Components NOT in public artifacts

### Know-how 1
- **Description:** <what the know-how is, in general terms — not the secret itself>
- **Why it is necessary:** <one-paragraph explanation of why this know-how is needed to practice the invention>
- **Form of transfer:** <e.g., engineer-to-engineer training, written documentation under NDA, source code escrow>
- **Risk if not transferred:** <what breaks if the buyer doesn't get this know-how>

### Know-how 2
... (repeat)

## Components in public artifacts (NOT trade-secret)

<list of what is in the public TTP and therefore NOT a trade-secret — to prevent the buyer from over-valuing secrets>

## Boundary

<one-paragraph. What is and is not being transferred as trade-secret.>
```

---

## Template: `counsel_questions.md`

```markdown
# Questions for Buyer Counsel — <candidate_id>

## Recommended diligence questions

### Q1. <question>
- **Context:** <one-paragraph context the counsel needs to understand the question>
- **Specific question:** <the question itself>
- **Why we are asking:** <why this is an open question, not advocacy>
- **Possible answers and their implications:** <e.g., "If counsel finds X, the differentiation argument weakens because Y">

### Q2. <question>
... (repeat; minimum 5, typically 8–12)

## Open uncertainties we have NOT resolved

- <uncertainty 1>
- <uncertainty 2>

## What we are NOT asking counsel to do

- We are not asking counsel to render a patentability verdict on our system.
- We are not asking counsel to opine on whether the mechanism is novel as a general principle.
- We are asking counsel to examine the specific questions above, in the context of the buyer's intended use.
```

---

## Anti-patterns (forbidden)

1. **"We believe our system is novel."** Belief is not evidence (Article I). State the technical effect, cite the prior art, and let counsel decide.

2. **Omitting threats.** Article XV (coder must disclose inconvenient results). Threats are mandatory.

3. **Semantic promotion.** Article XXVIII. "Similar to" is not "the same as." If the prior art teaches something similar but not the same, say so explicitly.

4. **Inventing prior art to look thorough.** Cite real references with real provenance. If a search returned nothing, say "no art found in this direction" with the search provenance (R274 negative-search rule).

5. **Advocacy in counsel_questions.md.** The questions are open questions, not arguments. If you find yourself writing "we believe the answer is X," rewrite as "what is the answer to X?"

---

## Provenance requirement

Every reference in `prior_art.md` must have:

- Full citation (DOI, URL, or patent number)
- Exact search query that found it
- Database searched
- Date of search
- Result rank

This is the R274 negative-search provenance rule, extended to all prior-art references.
