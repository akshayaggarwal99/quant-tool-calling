# Author actions before submission (29 Sep 2026 revision)

Items the fixing agent could not do because they need the author's account, machine time or
personal information. Each is one action.

- [ ] Zenodo: log in, create a deposit from the GitHub release tag `v1.3-peerj` (or upload the
      tarball), click "Reserve DOI", and replace `10.5281/zenodo.XXXXXXX` in
      `paper/peerj/main.tex` (Data Availability) with the reserved DOI. Rebuild with
      `cd paper/peerj && tectonic main.tex`. The deposit can stay unpublished until acceptance.
- [ ] GitHub: `git push origin main --tags` so that `prereg-v1`, `v1.2-peerj` and `v1.3-peerj`
      exist on the remote. The paper cites `v1.3-peerj`.
- [ ] Optional but recommended: deposit `paper/preregistration.md` at OSF as a retrospective
      registration of a locally dated document, and add the OSF link to Section 3.1. The paper
      already states that no independent time stamp exists; the deposit does not change that
      statement.
- [ ] Cover page: add city and country after "Independent Researcher" (line 44 of
      `paper/peerj/main.tex`) and in the cover letter signature.
- [ ] Confirm the wording of the "Use of generative AI" declaration (names Claude Code, Anthropic;
      scripts, drafting, revision, citation checks). Edit if any part is inaccurate.
- [ ] Confirm the "Preprint" declaration (arXiv submission of 24 Sep 2026 not announced; nothing
      public).
- [ ] Decide on the Llama-3.1-8B second-path cross-check (Section 3.8 says it has not been run):
      Q8_0 and Q3_K_M on the same 200 items through `llama-server /v1/chat/completions` with
      `--jinja` and a `tools` field, or Ollama's tools API. About an hour of GPU. If run, add the
      strict, coerced and quoted-argument rates side by side in Section 3.8.
- [ ] Decide on the multi-turn re-run (Section 4.6 reports the arm as confounded): serve with one
      slot (`-np 1 -c 32768`) or a per-slot cache, re-run `multi_turn_base` on the three rungs,
      regenerate tables. Until then the paper says H5 is not evaluable.
- [ ] Optional: run an FP16 rung of Qwen3-1.7B (the planned reference arm), about 15 minutes.
- [ ] Submission form: upload `paper/figures/fig1-ladder.pdf` as a separate figure file with the
      legend in `paper/peerj/fig1-legend.txt`; paste `COVER-LETTER-DRAFT.md` after review; enter
      the same name, email, affiliation string and ORCID as the cover page.
- [ ] Do not submit `paper/main_tmlr.tex`: it predates this revision, states the multi-turn and
      Llama-3.1-8B results that this revision corrected, and no longer compiles against the
      regenerated tables.
- [ ] One human reader outside the drafting sessions reads the full PDF before submission.
