# Cover letter draft for PeerJ Computer Science (author to review, sign and paste)

Dear Editors,

Please consider the enclosed Research Article, "Post-Training k-Quantization and Agentic
Tool-Calling Accuracy on Five Qwen3 and Llama Models", for PeerJ Computer Science.

What it measures. Post-training quantization is how language models reach laptops, and tool
calling is what agents on laptops do; the accuracy cost of quantization has been measured on
prose, knowledge and reasoning benchmarks and not on the function call an agent emits. The paper
builds a controlled five-rung llama.cpp k-quant ladder from one FP16 source for Qwen3-1.7B, and
three-rung ladders for four further models in two families, and scores every rung on the Berkeley
Function Calling Leaderboard by deterministic AST matching and on GSM8K with the same weight files.
Every number is recomputed from the raw run files by a script in the public repository.

Points the editor should know.

1. Template. The manuscript is built with a plain LaTeX article class that follows the PeerJ
   author instructions (US Letter, 12 pt, 2.5 cm margins, line numbers, Author Cover Page first,
   structured abstract under 500 words, declarations). The official Overleaf template requires a
   PeerJ login; I will move the accepted version onto it at production.
2. Hypotheses. Five hypotheses with thresholds were written in a dated file on the first day of
   the study. The file's first commit postdates the first ladder, so the paper does not call the
   study pre-registered; Section 3.1 gives the commit record, and Table 1 lists every departure
   from the file's design.
3. Prior versions and concurrent submission. An earlier version was submitted to arXiv on
   24 September 2026 and was not accepted for announcement; no preprint is public. A TMLR-format
   draft exists in the repository history and has not been submitted to TMLR or anywhere else.
   The manuscript is not under consideration elsewhere.
4. Identity. I am an independent researcher. The corresponding email is my IIT Roorkee alumni
   address, which I keep as my research identity; my ORCID record (0009-0006-3613-538X) and the
   repository (github.com/akshayaggarwal99) carry the same identity under the surname spelling
   Aggarwal, which is the same person. I am employed full time at Amazon; the work is unaffiliated
   with my employer, which is stated in the Competing Interests section.
5. Data. Code, raw result and score files, generations, server logs, the hypothesis file and the
   dated lab notebook are public at the release tag v1.3-peerj named in the Data Availability
   statement; a DOI-bearing Zenodo archive of that tag will be deposited on acceptance.
6. Generative AI. A large language model coding assistant was used for scripts, drafting and
   citation checks, as declared in the manuscript; I reviewed and am responsible for all content.

Suggested reviewers: researchers who work on LLM quantization evaluation (for example the authors
of the llama.cpp GGUF evaluation on Llama-3.1-8B-Instruct, arXiv 2601.14277) and on function-calling
benchmarks (the BFCL team at UC Berkeley). No opposed reviewers.

Thank you for your consideration.

Akshay Kumar
Independent Researcher, [city, country]
akumar8@mt.iitr.ac.in, ORCID 0009-0006-3613-538X
