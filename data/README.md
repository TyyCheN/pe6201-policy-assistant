# Data: the Haida Co. Employee Handbook

This folder holds the only data the assistant uses: one company employee handbook, translated into
English, split into numbered clauses, and frozen before any evaluation question was written.

## Source

| | |
|---|---|
| Document | Haida Co. Employee Handbook, October 2026 revision |
| Origin | The employee handbook of a real small manufacturing company in Jiangsu, China (my family's business). "Haida Co." is a substitute name. |
| Language | The original is in Chinese. The files here are my English translation. |
| Size | 12 documents, 175 numbered clauses, 9,828 words |
| Personal data | None. The handbook is a policy document and contains no employee records. |
| Not included | The Chinese original. |

## Files

| File | Content | Clauses | Words |
|---|---|---|---|
| `corpus/D00.md` | Preface and General Provisions | 7 | 444 |
| `corpus/D01.md` | Chapter 1 — Onboarding | 15 | 807 |
| `corpus/D02.md` | Chapter 2 — Leaving the Company | 10 | 552 |
| `corpus/D03.md` | Chapter 3 — Employee Discipline (conduct, confidentiality, safety, working hours, overtime, business trips) | 38 | 2,016 |
| `corpus/D04.md` | Chapter 4 — Training | 5 | 250 |
| `corpus/D05.md` | Chapter 5 — Performance Appraisal | 7 | 381 |
| `corpus/D06.md` | Chapter 6 — Pay | 11 | 639 |
| `corpus/D07.md` | Chapter 7 — Leave | 38 | 2,533 |
| `corpus/D08.md` | Chapter 8 — Insurance | 5 | 279 |
| `corpus/D09.md` | Chapter 9 — Rewards and Discipline | 27 | 1,342 |
| `corpus/D10.md` | Chapter 10 — Supplementary Provisions | 7 | 448 |
| `corpus/D11.md` | Acknowledgement of Receipt | 5 | 137 |
| `corpus/MANIFEST.json` | Source name, version, and per-file title, clause count, word count and SHA-256 | | |

## Format

Each file is plain Markdown: `# chapter title`, optional `## section` headings, and one clause per line:

```
[D07-5.1] An employee who registers a marriage according to law is entitled, under Jiangsu rules, to 13 days of marriage leave, ...
```

- **One clause is one retrieval unit**, so every citation points to one specific clause.
- **Clause IDs** follow the handbook's own numbering: `D07-5.1` is document 07, section 5, item 1.
  The preface uses `P` (`D00-P1`), the general provisions `G` (`D00-G2`) and the acknowledgement form `R` (`D11-R1`).
- The source name and the document date are stored once, in `MANIFEST.json`, and shown with every
  answer (`src/policy_assistant/corpus.py` reads them).

## How the data was prepared

1. **Translation.** I translated the handbook clause by clause and kept the original numbering.
   I then checked every clause against the Chinese text: the same clause IDs exist in both, and every
   number in the original (days, amounts, percentages, deadlines) appears in the translation.
2. **Redaction.** The company's registered name is replaced with "Haida Co.". City names and the
   description of the product line are generalised. Three clauses are affected: D00-P1, D00-G2 and D07-4.1.
   No rule, number or deadline was changed.
3. **Freeze.** The corpus was committed on its own, as the first content commit, before the evaluation
   questions (`git log --reverse`). `MANIFEST.json` records a SHA-256 hash of every file.

## Verify it

```bash
python scripts/freeze_manifest.py --check     # prints "corpus unchanged since freeze", or names the changed file
git log --reverse --oneline                  # corpus commit comes before the evaluation-set commit
```

## Known limits of the data

- The handbook is a revision that takes effect only on formal release (clause D10-2). Answers show the
  document date so a reader can tell which version they come from.
- It is a translation. In a dispute the Chinese original prevails.
- Many clauses defer to the law or to the employment contract ("according to law"). The assistant can
  only report what the handbook itself says.
- One company, one handbook. The evaluation says nothing about other companies' documents.
