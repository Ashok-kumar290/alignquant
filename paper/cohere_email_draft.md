# Mail Draft for Cohere

## Subject

```text
Responsible disclosure: application-visible secret leakage in Cohere models
```

## Body

```text
Hello Cohere Safety Team,

We conducted a controlled red-team evaluation of several Cohere chat models
using synthetic confidential canaries placed in model-visible context. We
observed repeatable application-visible secret leakage, especially when
confidential data appeared in retrieved/tool-style context.

Strongest findings:
- command-r7b-12-2024 leaked an exact synthetic canary in 139/300
  system-context replication probes (46.4%).
- In a clean two-turn retrieved-context exfiltration rerun,
  command-r7b-12-2024 leaked the exact token in 15/24 follow-up cases (62.5%).
- In a single-turn retrieved/tool-context extraction setting, all three tested
  models leaked heavily, including 20/24 exact leaks for command-r7b-12-2024.
- On the paired harmful-request benchmark, command-r7b-12-2024 showed 0/100
  unsafe compliance, which suggests refusal and confidentiality should be
  evaluated separately.

We are not claiming leakage of provider-hidden prompts, infrastructure
compromise, training-data leakage, or real user secrets. Our claim is narrower:
natural-language instructions were not a reliable confidentiality control for
application-supplied sensitive context visible to the model.

Attached are a concise disclosure draft, a vulnerability summary, statistical
evidence, representative redacted cases, a cross-model comparison, and a
consolidated evidence dossier. We would appreciate confirmation of receipt,
your assessment of whether this behavior is considered an expected limitation
or a model behavior bug, and any recommended mitigations for applications
handling confidential context.

Regards,
[Your name]
```

## Attach / Link

- `paper/cohere_disclosure_draft.md`
- `paper/cohere_vulnerability_list.md`
- `paper/redteam_toolchain_statistical_evidence.md`
- `paper/redteam_toolchain_appendix.md`
- `paper/cohere_model_comparison.md`
- `paper/redteam_evidence_dossier.md`

## Ask Cohere For

1. Confirmation of receipt.
2. Their classification of the issue.
3. Whether they can reproduce it internally.
4. Recommended mitigations for applications handling confidential context.
5. Whether they prefer an embargo before public release.
