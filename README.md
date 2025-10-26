# Auction Property Condition Scoreboard

**A system for turning unstructured property inspection text into a structured, at-a-glance condition summary—helping auction bidders spot red flags fast, with human review where it matters.**

---

## Overview

The **Auction Property Condition Scoreboard** ingests text-heavy inspection reports from real estate auction providers and transforms them into a structured “scoreboard” summarizing property condition. It uses a hybrid of **NLP, rule-based logic**, and **human-in-the-loop** review to ensure high accuracy and auditability.

![Auction Property Condition Scoreboard](https://raw.githubusercontent.com/JaydenAi7/Auction-Property-Condition-Scoreboard/main/Figure_1.png)

---

## Inputs

- **BPO Notes (General Condition):** Free-text narrative from inspectors.
- **Subcategory Notes (Detailed):** Area-specific comments (e.g., kitchen, roof, utilities).
- **Optional Metadata:** Inspection date, photo counts, inspector/source ID.
- **URL for your API**

---

## Methodology

1. **Parse & Normalize**  
   Clean text, detect structure, and normalize synonyms across domains.

2. **Evidence Extraction**  
   Detect condition signals (e.g., “mold,” “renovated,” “leak”) with spans and rationales.

3. **Label Assignment**  
   Each subcategory and BPO narrative is labeled:
   - `Positive` – improvements or good condition
   - `Negative` – defects, damage, repairs needed
   - `No Info` – no meaningful signal
   - `Mixed` – conflicting evidence

4. **Conflict Detection**  
   Compare BPO and subcategories; flag discrepancies (e.g., BPO says “good” but roof is poor).

5. **Scoring & Aggregation**  
   Combine subcategory and BPO labels using a weighted rubric to assign an **Overall Condition Rating**.

---

## Scoring Rubric

- **Subcategory Scores:**
  - `Positive` = +1  
  - `Negative` = -1  
  - `Mixed` / `No Info` = 0  
  - Weighted by materiality (e.g., roof > interior cosmetics)

- **BPO Multiplier:**  
  BPO is treated as a weighted prior (e.g., 1.5× a subcategory), but never overrides strong contradictory evidence without flag.

- **Overall Rating Bands:**
  - `Strong Positive`: ≥ +2 and no critical negatives
  - `Cautious Positive`: +1 to +2, minor negatives
  - `Mixed/Uncertain`: −1 to +1 or multiple No-Info
  - `Negative`: ≤ −2 or any critical issue (e.g., structural, roof, severe mold, inoperable utilities)

Each score includes:
- **Rationales:** Evidence quotes or bullets per label
- **Confidence:** Based on evidence strength, recency, and agreement

---

## UI: Condition Scoreboard

- **Top Row:** Overall Rating, Confidence, and Flag badge (if any)
- **Grid View:** Subcategory chips (green/yellow/red/gray) with hover-over evidence
- **BPO Card:** BPO label + evidence snippet
- **Reviewer Tools:** Mark as reviewed, override with reason, tune weights

---

## Automation & Guardrails

- Fully automated by default, with manual override tools
- Flags discrepancies and weak evidence for human review
- Analyst decisions are logged for audit and continuous learning

---

## Success Criteria

- **50%+ faster** per-property review  
- **≥90% precision** on identifying material negatives  
- **≥95% recall** on flaggable conflicts  
- **≥80% analyst satisfaction** with explanations & controls  


