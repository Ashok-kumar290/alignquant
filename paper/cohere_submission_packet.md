# Cohere Submission Packet

This file is the final send-order and claim-boundary guide for contacting
Cohere about the confidentiality findings in this repository.

## 1. What to send

Send these files in this order:

1. `paper/cohere_email_draft.md`
2. `paper/cohere_repro_bundle.md`
3. `paper/cohere_vulnerability_list.md`
4. `paper/cohere_disclosure_draft.md`
5. `paper/redteam_repeat_stability_results.md`
6. `paper/redteam_toolchain_statistical_evidence.md`
7. `paper/redteam_toolchain_appendix.md`
8. `paper/cohere_model_comparison.md`
9. `paper/redteam_evidence_dossier.md`

## 2. What to claim

Keep the claim narrow and reproducible:

> Cohere models, especially `command-r7b-12-2024`, showed repeatable
> application-visible secret leakage when synthetic confidential values were
> placed in model-visible system or retrieved/tool-style context.

Shorter version:

> Natural-language instructions were not a reliable confidentiality control for
> application-supplied sensitive context visible to the model.

## 3. What not to claim

Do **not** claim:

- provider-hidden prompt leakage
- infrastructure compromise
- training-data leakage
- real-user-data exposure
- broad model unsafety beyond the tested threat model

## 4. Strongest evidence to lead with

### Replication
- `command-r7b-12-2024`: `139/300` exact leaks in 5-canary system-context replication (`46.4%`)

### Practical retrieved-context failure
- `command-r7b-12-2024`: `20/24` exact leaks in single-turn retrieved/tool-context extraction (`83.3%`)

### Staged exfiltration failure
- `command-r7b-12-2024`: `15/24` exact leaks in clean two-turn retrieved-context exfiltration (`62.5%`)

### Stability evidence
- `tool-direct-extract`: `20/20` exact leaks
- `tool-json-extract`: `20/20` exact leaks
- `tool-reference-resolution`: `20/20` exact leaks
- `fields-then-value`: `20/20` exact leaks
- `policy-then-quote`: `20/20` exact leaks
- `summary-then-direct`: `20/20` exact leaks
- `tool-checksum`: `19/20` exact leaks
- negative control `tool-safe-summary`: `0/20` exact leaks

### Separation from harmful-request refusal
- `command-r7b-12-2024`: `0/100` unsafe compliance on the paired harmful-request benchmark

## 5. Why this should matter to Cohere

The strongest practical risk in this repository is not one-shot harmful content
generation. It is confidentiality failure in retrieved/tool-style context,
which is a realistic deployment pattern for:

- RAG systems
- tool-using assistants
- agent workflows
- internal retrieval over customer or operational records

The repeat-run stability evidence makes the issue harder to dismiss as
transient model variance.

## 6. Minimum attachment set

If you want to keep the first email lightweight, attach only these:

1. `paper/cohere_email_draft.md`
2. `paper/cohere_repro_bundle.md`
3. `paper/cohere_vulnerability_list.md`
4. `paper/redteam_repeat_stability_results.md`

Then offer the longer dossier on request.

## 7. Full attachment set

If you want the first message to be complete, attach all of:

- `paper/cohere_email_draft.md`
- `paper/cohere_repro_bundle.md`
- `paper/cohere_vulnerability_list.md`
- `paper/cohere_disclosure_draft.md`
- `paper/redteam_repeat_stability_results.md`
- `paper/redteam_toolchain_statistical_evidence.md`
- `paper/redteam_toolchain_appendix.md`
- `paper/cohere_model_comparison.md`
- `paper/redteam_evidence_dossier.md`

## 8. Exact asks for Cohere

Ask them to respond on:

1. whether they classify this as an expected limitation or a model behavior bug
2. whether they can reproduce the minimal cases internally
3. whether they recommend product-side mitigations for retrieved/tool context
4. whether they want a disclosure embargo before public release
5. whether they want additional reproduction data or raw hashed records

## 9. Best current repository files

### Vendor-facing
- `paper/cohere_email_draft.md`
- `paper/cohere_repro_bundle.md`
- `paper/cohere_vulnerability_list.md`
- `paper/cohere_disclosure_draft.md`

### Evidence
- `paper/redteam_repeat_stability_results.md`
- `paper/redteam_toolchain_statistical_evidence.md`
- `paper/redteam_toolchain_appendix.md`
- `paper/cohere_model_comparison.md`
- `paper/redteam_evidence_dossier.md`

### Paper and methods
- `paper/main.tex`
- `paper/human_audit_protocol.md`
- `paper/experiment_catalog.md`

## 10. Current status

For disclosure quality, this repository is now strong on:

- concrete claims
- replication
- retrieved-context realism
- staged exfiltration
- repeat-run stability
- negative controls

The biggest remaining upgrade would be a completed human-audited appendix using
the protocol already included in the repository.
