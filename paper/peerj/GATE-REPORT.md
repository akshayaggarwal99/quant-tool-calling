# Pre-submission gate, PeerJ Computer Science version, 29 Sep 2026 (revision after review)

Checked against the gate in the research-paper skill. PDF: paper/peerj/main.pdf, 24 pages,
sha256 64d9909933083639c5994e91647dd8858fe5a5a6ab34e4ec4c9aebc4c6923538.

## Substance
- PASS  Two model families (Qwen3, Llama 3.x), two datasets (BFCL simple_python and multi_turn_base, GSM8K), one hardware target, one toolchain; Table 5 and Table 4.
- PASS  Contributions list: 8 items, each with a number and a table or figure pointer (Introduction, items 1 to 8).
- PASS  Formal problem statement: Section 3.2 defines ladder, item set, verdict, strict and coerced verdicts, McNemar families, Holm, cliff rung, floor, tolerance tau, minimum detectable difference.
- PASS  Every headline number carries n, the seed policy (no sampling seed; GSM8K drawn at seed 42) and a test or interval; raw result, score, generation and server logs are in runs/ in the repository.
- PASS  Gap statement names Kurt (2026), Lotfi et al. (2026), Jin et al. (2024), Li et al. (2024) and says what each does not do (Related work, "The gap").
- PASS  Three PeerJ Computer Science citations: Dincer and Kilimci 2026 (e3769), Turkmen 2026 (e4000), Hebenstreit et al. 2024 (e1999); each checked against the paper on 30 Sep per the notebook.

## Prose
- PASS  Humanizer and human-writing passes run on every rewritten section; pdftotext shows 0 em dashes and 0 en dashes outside bibliography page ranges; grep for significance words returns nothing.
- PASS  Title states variable (post-training k-quantization), context (five Qwen3 and Llama models), outcome (agentic tool-calling accuracy); 12 words; no slogan.
- PASS  Introduction opens on a concrete scenario (item simple_python_21 at Q3_K_M answering in prose with the wrong GCD).
- PASS  No sentence promises significance; "significant" does not appear.
- AUTHOR One human reader outside the drafting sessions has not yet read the full PDF.

## Author and account
- AUTHOR Name, email (akumar8@mt.iitr.ac.in) and ORCID are identical on the cover page and in the cover-letter draft; the venue form and the ORCID record are the author's to align. The repository handle spells the surname Aggarwal; the cover letter explains it.
- AUTHOR Affiliation "Independent Researcher" is used on the cover page, the cover letter and the README; city and country still have to be added (PeerJ asks for a location).
- AUTHOR PeerJ account age and ORCID linkage cannot be checked from here.

## Format
- AUTHOR Format followed from the author-instructions reading of 29 Sep recorded in the main.tex header (US Letter, 12 pt, line numbers, cover page, structured abstract of 486 words, declarations); the plain article class is stated in the cover letter. Re-verify the live page two days before submission.
- PASS  PDF compiles with tectonic, 0 undefined references, 0 "??", 0 BLOCKED, 0 overfull boxes, no blank page (24 pages, references end on page 24).
- AUTHOR Artifact: repository is public and MIT-licensed; tags prereg-v1, v1.2-peerj and v1.3-peerj exist locally only and must be pushed; the Zenodo DOI in Data Availability is the placeholder 10.5281/zenodo.XXXXXXX until reserved.

## arXiv
- PASS  No arXiv upload is planned before acceptance.
- PASS  Primary category is not at issue (no upload).
- FAIL  This manuscript's earlier version was rejected by arXiv (submit/8125878, 25 Sep 2026). Consequence: no resubmission; appeal only with the PeerJ DOI. Declared in the manuscript's Preprint statement and the cover letter.
- PASS  A public DOI before acceptance is not needed by the venue; Zenodo will carry the archive DOI.

## Reviewer items not closed in this pass (see not_fixed in the run record)
- Llama-3.1-8B second-path cross-check (chat completions with --jinja and tools): needs about an hour of the author's GPU; a decision line is in AUTHOR-CHECKLIST.md.
- Multi-turn re-run with a per-trajectory context: needs GPU time; the arm is reported as confounded until then.
- Zenodo DOI, OSF deposit, tag push, city and country: author account actions.
