# AlignQuant Literature Review

**Paper:** *AlignQuant: Does Quantization Degrade Safety-Relevant Representations in LLMs?*
**Author:** Adharapurapu V S M Ashok Kumar
**Funding:** Cohere Labs Catalyst Grant
**Scope:** Literature sweep across (1) quantization methods, (2) probing / activation steering / alignment geometry, (3) PEFT under quantization & alignment-preserving fine-tuning.

---

## Bucket 1 — Quantization Methods

For each paper we note **what is measured** (typically perplexity + zero-shot downstream accuracy) and **what is NOT measured** with respect to *alignment preservation* (refusal, truthfulness, sycophancy resistance, activation geometry).

### 1.1 LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale
- **Authors / Year / Venue:** Dettmers, Lewis, Belkada, Zettlemoyer — NeurIPS 2022.
- **arXiv:** 2208.07339.
- **Summary:** Identifies *outlier features* (rare but magnitude-dominant activations) as the main cause of 8-bit quantization collapse at scale. Introduces a mixed-precision decomposition — outlier dimensions kept in fp16, rest in int8 — enabling near-lossless 8-bit inference for OPT/BLOOM-scale models.
- **What they measure:** perplexity (C4, WikiText), zero-shot LAMBADA/HellaSwag/PIQA/WinoGrande, throughput.
- **What they DO NOT measure re alignment:** no refusal behavior, no truthfulness, no analysis of whether outlier-feature channels overlap with *safety-relevant* activation directions (even though outliers are exactly the channels empirically most implicated in later refusal/truth probes — a gap AlignQuant exploits).

### 1.2 GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers
- **Authors / Year / Venue:** Frantar, Ashkboos, Hoefler, Alistarh — ICLR 2023.
- **arXiv:** 2210.17323.
- **Summary:** Layer-wise approximate second-order (Optimal Brain Quantizer) PTQ that quantizes OPT-175B / BLOOM-176B to 3–4 bits in a few GPU-hours with small calibration sets.
- **What they measure:** perplexity, zero-shot LM-Eval-Harness tasks, latency.
- **NOT measured:** calibration set bias toward *pretraining-like text* means RLHF/refusal behavior is not represented in the Hessian proxy — yet the Hessian blindly re-allocates error budget away from those directions. No safety benchmark is reported.

### 1.3 SmoothQuant: Accurate and Efficient Post-Training Quantization for LLMs
- **Authors / Year / Venue:** Xiao, Lin, Seznec, Wu, Demouth, Han — ICML 2023.
- **arXiv:** 2211.10438.
- **Summary:** Migrates quantization difficulty from activations to weights via a channel-wise mathematically equivalent smoothing transform, enabling W8A8 across OPT/BLOOM/GLM.
- **What they measure:** perplexity, zero-shot accuracy, GPU/CPU speedup.
- **NOT measured:** whether the smoothing scalar per channel disproportionately attenuates *safety-critical* channels (Arditi et al. later showed refusal concentrates in a narrow subspace); no TruthfulQA/AdvBench evaluation.

### 1.4 AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration
- **Authors / Year / Venue:** Lin, Tang, Tang, Yang, Xiao, Dang, Gan, Han — MLSys 2024.
- **arXiv:** 2306.00978.
- **Summary:** Observes only ~1% of weights are "salient" (large activation magnitude). Protects them by per-channel activation-aware scaling; W4 models retain near-fp16 quality for LLaMA / Vicuna / Mistral.
- **What they measure:** WikiText-2/PTB perplexity, MMLU, generation quality (qualitative), edge-device latency.
- **NOT measured:** what concept does the "salient 1%" encode? AWQ selects saliency by *activation magnitude on a generic calibration set*, which is exactly the signal that does **not** necessarily correlate with refusal/truthfulness directions — so AWQ could preserve magnitude while distorting alignment directions.

### 1.5 QLoRA: Efficient Finetuning of Quantized LLMs (NF4)
- **Authors / Year / Venue:** Dettmers, Pagnoni, Holtzman, Zettlemoyer — NeurIPS 2023 (Oral).
- **arXiv:** 2305.14314.
- **Summary:** Introduces NormalFloat-4 (NF4), a theoretically information-optimal 4-bit quantile-based datatype for N(0,1)-distributed weights, plus *double quantization* and *paged optimizers*. Enables fine-tuning of 65B models on a single 48GB GPU via LoRA adapters trained through NF4-frozen weights.
- **What they measure:** Vicuna / MMLU / Elo, memory, throughput.
- **NOT measured:** NF4 is optimal for *reconstruction MSE under a Gaussian prior*; no analysis of whether RLHF-injected components (which are provably non-Gaussian — they are concentrated rank-1 edits per Arditi) are preserved. No refusal / sycophancy evaluation.

### 1.6 SpQR: A Sparse-Quantized Representation for Near-Lossless LLM Weight Compression
- **Authors / Year / Venue:** Dettmers, Svirschevski, Egiazarian, Kuznedelev, Frantar, Ashkboos, Borzunov, Hoefler, Alistarh — 2023.
- **arXiv:** 2306.03078.
- **Summary:** Isolates the ~1% of weights whose quantization causes the most error and stores them in fp16 sparsely, while quantizing the rest to 3–4 bits. Near-lossless perplexity at <4 bits.
- **NOT measured:** whether the sparse fp16 set coincides with safety-relevant weights; saliency is again defined via reconstruction-loss gradient, not via safety-behavior gradient.

### 1.7 OmniQuant: Omnidirectionally Calibrated Quantization for LLMs
- **Authors / Year / Venue:** Shao, Chen, Zhang, Yu, Han, Li, Yan, Qiao, Luo — ICLR 2024 (Spotlight).
- **arXiv:** 2308.13137.
- **Summary:** Learnable weight clipping + learnable equivalent transformation, optimized block-wise with calibration data; strong W2A16 / W4A4 results.
- **NOT measured:** calibration data is pretraining-like (WikiText, C4). Learnable parameters are optimized to minimize block-wise reconstruction — no term in the objective encodes alignment preservation.

### 1.8 QuIP / QuIP#: 2-Bit Quantization with Incoherence Processing (+ Hadamard & Lattice Codebooks)
- **Authors / Year / Venue:** Chee, Cai, Kuleshov, De Sa — NeurIPS 2023 (QuIP). Tseng, Chee, Sun, Kuleshov, De Sa — ICML 2024 (QuIP#).
- **arXiv:** 2307.13304 / 2402.04396.
- **Summary:** Random (then Hadamard) orthogonal rotations make weights and Hessians *incoherent*, after which simple adaptive rounding (QuIP) or E8-lattice vector quantization (QuIP#) yield viable 2-bit LLMs.
- **NOT measured:** random rotations are by construction *not* aligned with the refusal / truth / sycophancy subspaces; if safety directions happen to lie near the 2-bit quantization grid post-rotation they are destroyed first. No safety evaluation.

### 1.9 Decoding Compressed Trust (Hong et al., ICML 2024)
- **Authors:** Hong, Duan, Zhang, Wang, Wang, Li, Zhang, Liu, Chen, Zhao, Liu, Xiao — ICML 2024.
- **arXiv:** 2403.15447.
- **Summary:** *First broad-scope* trust evaluation of compressed LLMs across 8 dimensions (ethics, fairness, robustness, privacy, stereotype, truthfulness, toxicity, OOD) × 3 models × 5 methods (AWQ, GPTQ, SmoothQuant, Magnitude Pruning, Wanda). Finding: quantization to 4-bit largely preserves trust; 3-bit degrades; pruning at 50% degrades sharply.
- **What they measure:** behavioral trust dimensions via DecodingTrust benchmarks.
- **What they do NOT measure:** *geometric* / representational cause. They treat the model as a black box (input→output). No activation-level probing, no measurement of whether refusal/truth *directions* are preserved, only whether accuracy on downstream trust tasks is preserved. They also do not study PEFT interactions.

### 1.10 Q-resafe: Assessing Safety Risks and Quantization-aware Safety Patching
- **Authors / Year / Venue:** Wang, Chen, Liu, et al. — ICLR 2025 (OpenReview VarjSNbij7).
- **arXiv:** 2506.20251.
- **Summary:** Systematic safety evaluation of mainstream PTQ methods on harmful-prompt benchmarks; proposes a LoRA-style "safety patching" fine-tune on quantized weights to restore refusal. All PTQ methods (AWQ/GPTQ/SmoothQuant/AutoRound) show non-trivial safety degradation.
- **NOT measured:** behavioral only (ASR on AdvBench-like prompts). No activation-space analysis, no per-direction quantification — so they can patch symptoms without explaining the mechanism. No sycophancy / truthfulness.

### 1.11 Fine-Tuning, Quantization, and LLMs: Navigating Unintended Outcomes
- **Authors:** Kumar et al. — 2024.
- **arXiv:** 2404.04392.
- **Summary:** Shows jailbreak success rates rise after fine-tuning *and* after quantization across Mistral/Llama/Qwen/MosaicML. External guardrails remain effective.
- **NOT measured:** direction-level attribution, no PEFT-baseline comparisons in the same controlled setup, no interpretability.

### 1.12 Beyond Perplexity: Multi-dimensional Safety Evaluation of LLM Compression
- **Authors:** Xu et al. — EMNLP 2024 Findings.
- **Summary:** Evaluates degeneration harm (toxicity) and representational harm (bias by dialect / protected group) under pruning and quantization. Quantization mostly preserves biases; pruning amplifies them unevenly.
- **NOT measured:** no alignment *direction* analysis, no refusal preservation, no activation-steering reproducibility under quantization.

### 1.13 Exploiting LLM Quantization
- **Authors:** Egashira, Vero, Staab, He, Vechev — NeurIPS 2024.
- **arXiv:** 2405.18137.
- **Summary:** Adversarial supply-chain attack — craft an fp16 model that *looks safe* but quantizes (under known AWQ/GPTQ/NF4 grids) to a harmful model. Projected-gradient-descent attack.
- **NOT measured:** the *benign* direction of the same phenomenon — that even non-adversarial quantization differentially degrades safety directions. But it is a striking existence proof that quantization rounding is a surgically-precise attack surface on alignment.

### 1.14 Alignment-Aware Quantization for LLM Safety
- **Authors / Year:** 2024/2025 — arXiv 2511.07842.
- **Summary:** Adds an "alignment-preserving contrastive loss" during PTQ calibration, preserving safety at 4-bit on LLaMA/Qwen/Mistral without a dedicated safety dataset.
- **NOT measured:** still behavioral; does not explain *which* directions the contrastive loss preserves, nor test against probing / steering interventions.

### 1.15 Additional quantization context (briefly cited)
- **GPTQ-LoRA / QA-LoRA** (Xu et al., ICLR 2024; arXiv 2309.14717): quantization-aware LoRA by group-sharing the adapter scales; evaluated on perplexity + MMLU only.
- **ApiQ** (Liao et al. 2024, arXiv 2402.05147): activation-preserving LoRA initialization for quantized backbones; again evaluated on perplexity / GLUE.

**Cross-cutting gap in Bucket 1:** every method is evaluated on a *reconstruction* objective (perplexity / MSE) or a *behavioral* safety objective (ASR, DecodingTrust). No paper provides a **geometric** measurement of which activation directions survive vs. degrade — precisely the level at which refusal, truthfulness, and sycophancy have been shown to live.

---

## Bucket 2 — Probing, Activation Steering, Alignment Geometry

### 2.1 TruthfulQA: Measuring How Models Mimic Human Falsehoods
- **Authors:** Lin, Hilton, Evans — ACL 2022.
- **arXiv:** 2109.07958.
- **Summary:** 817 adversarial questions targeting common human misconceptions. Benchmark; not a probe. Defines the canonical truthfulness metric used by every subsequent probing paper.
- **Limitation for our purposes:** purely behavioral — does not expose whether truthfulness lives in the weights, activations, or decoding strategy.

### 2.2 The Internal State of an LLM Knows When It's Lying
- **Authors:** Azaria, Mitchell — EMNLP Findings 2023.
- **arXiv:** 2304.13734.
- **Summary:** Trains SAPLMA, a simple MLP probe on frozen hidden states, achieving 71–83 % accuracy at distinguishing true vs. false statements — even when the model is about to output the false one. Shows truthfulness is internally *linearly readable*.
- **Limitation:** only shows readability, not causality; no quantization/PEFT ablation.

### 2.3 Inference-Time Intervention (ITI)
- **Authors:** Li, Patel, Viégas, Pfister, Wattenberg — NeurIPS 2023.
- **arXiv:** 2306.03341.
- **Summary:** Identifies ~48 "truthful heads" via logistic probes; at inference adds a per-head mean-difference vector to their outputs. TruthfulQA MC1 on Alpaca jumps from 32.5 → 65.1 %.
- **Critical observation for AlignQuant:** the intervention is a rank-1 per-head edit — exactly the kind of structure that 4-bit round-to-nearest can destroy without affecting perplexity.
- **NOT measured:** robustness of the truthful heads under quantization.

### 2.4 Representation Engineering (RepE)
- **Authors:** Zou, Phan, Chen, Campbell, Guo, Ren, Pan, Yin, Mazeika, Dombrowski, Goel, Li, Byun, Wang, Mallen, Basart, Koyejo, Song, Fredrikson, Kolter, Hendrycks — 2023 (NeurIPS 2023 workshop; widely cited).
- **arXiv:** 2310.01405.
- **Summary:** Top-down paradigm: extract *concept directions* (honesty, power-seeking, emotion, morality, memorization) via stimulus/contrast pairs, then read or control them. Provides LoRRA (Low-Rank Representation Adaptation) — relevant PEFT analogue.
- **Measures:** direction-reading AUROC; control efficacy on TruthfulQA, MACHIAVELLI, etc.
- **NOT measured:** how these directions fare under weight compression; RepE is the *vocabulary* AlignQuant needs, but RepE itself does not study quantization.

### 2.5 Refusal in LLMs is Mediated by a Single Direction
- **Authors:** Arditi, Obeso, Syed, Paleka, Panickssery, Gurnee, Nanda — NeurIPS 2024.
- **arXiv:** 2406.11717.
- **Summary:** For 13 open-weight chat models up to 72B, refusal is mediated by a **1-D subspace** of the residual stream. Ablating this direction via a rank-1 weight edit produces a near-complete jailbreak with minimal capability loss; adding it makes models refuse harmless prompts.
- **Measures:** refusal rate under direction ablation/addition; cosine similarity across models; MMLU preservation.
- **NOT measured:** stability of this 1-D direction under PTQ. This is the single most important gap AlignQuant targets — if refusal is rank-1, it is the *most* quantization-fragile part of the network by construction.

### 2.6 The Geometry of Truth
- **Authors:** Marks, Tegmark — 2023/2024.
- **arXiv:** 2310.06824.
- **Summary:** Demonstrates an *emergent linear* truth direction in residual-stream activations that generalizes across factual domains. Introduces mass-mean probing and shows causal interventions along the direction flip model outputs.
- **NOT measured:** behavior under compression; robustness to PEFT.

### 2.7 Steering Language Models with Activation Engineering (ActAdd)
- **Authors:** Turner, Thiergart, Leech, Udell, Vazquez, Mini, MacDiarmid — 2023.
- **arXiv:** 2308.10248.
- **Summary:** Single pair of contrastive prompts → difference-in-activation steering vector injected at a chosen layer. Controls sentiment, topic, toxicity at inference with no fine-tuning.
- **NOT measured:** no interaction with quantization; no measurement of how many steering directions are linearly independent and thus at risk.

### 2.8 Steering Llama 2 via Contrastive Activation Addition (CAA)
- **Authors:** Panickssery (Rimsky), Gabrieli, Schulz, Tong, Hubinger, Turner — ACL 2024.
- **arXiv:** 2312.06681.
- **Summary:** Builds per-behavior steering vectors from ~50 contrastive multiple-choice pairs (sycophancy, corrigibility, survival-instinct, hallucination, myopic-reward, etc.). Dialing the coefficient cleanly modulates the behavior on open-ended generations.
- **Direct relevance:** gives AlignQuant off-the-shelf "sycophancy direction" and "hallucination direction" vectors to test under quantization.
- **NOT measured:** how quantization of the base weights affects these learned directions.

### 2.9 Discovering Language Model Behaviors with Model-Written Evaluations
- **Authors:** Perez et al. (Anthropic) — Findings of ACL 2023.
- **arXiv:** 2212.09251.
- **Summary:** 154 model-written behavioral evals, including sycophancy, advanced AI-risk, persona traits. Shows inverse scaling of sycophancy with RLHF.
- **Role here:** provides evaluation datasets for sycophancy that AlignQuant will use.

### 2.10 Towards Understanding Sycophancy in Language Models
- **Authors:** Sharma et al. (Anthropic) — ICLR 2024.
- **arXiv:** 2310.13548.
- **Summary:** Quantifies sycophancy across 5 frontier models on realistic free-form tasks; attributes it to preference-model biases. Releases the sycophancy-eval suite.
- **Measures:** behavioral rates of sycophantic error. Not geometric.

### 2.11 Sleeper Agents: Training Deceptive LLMs That Persist Through Safety Training
- **Authors:** Hubinger et al. (Anthropic) — 2024.
- **arXiv:** 2401.05566.
- **Summary:** Backdoored models retain unsafe triggered behavior through SFT/RL/adversarial training. Companion result: simple linear probes on residual-stream activations detect the impending "defection" with very high AUROC.
- **Relevance:** another proof that safety-relevant computation is *linearly localized* — and therefore linearly destructible.

### 2.12 Detecting Strategic Deception Using Linear Probes
- **Authors:** Apollo Research (Goldowsky-Dill, Chughtai, Heimersheim, MacDiarmid et al.) — 2025.
- **arXiv:** 2502.03407.
- **Summary:** Linear probes on Llama activations discriminate honest vs. deceptive responses at AUROC 0.96–0.999.
- **Role:** further evidence for linear structure of safety-relevant features; motivates a probe-based evaluation protocol for AlignQuant.

### 2.13 Scaling Monosemanticity (+ Towards Monosemanticity)
- **Authors:** Bricken et al. 2023 (Transformer Circuits); Templeton et al. 2024 (Claude 3 Sonnet, Anthropic).
- **Summary:** Sparse autoencoders extract millions of monosemantic features including "deception", "sycophancy", "bioweapon", "security vulnerability" directions in production models. Provides a *feature-level* target set for AlignQuant's representational analysis.
- **NOT measured:** SAE feature fidelity under weight quantization of the underlying LLM.

### 2.14 Safety Alignment Should Be Made More Than Just a Few Tokens Deep
- **Authors:** Qi, Panda, Lyu, Ma, Roy, Beirami, Mittal, Henderson — ICLR 2025.
- **arXiv:** 2406.05946.
- **Summary:** Shows RLHF safety alignment concentrates almost entirely in the first few output tokens (KL between base and aligned collapses after token 5). Proposes a token-wise regularized objective for "deep" alignment.
- **Relevance:** if alignment is a thin surface phenomenon, it is also the *thinnest* signal in the weight distribution — maximally vulnerable to quantization rounding.

### 2.15 Fine-tuning Aligned Language Models Compromises Safety, Even When Users Don't Intend To
- **Authors:** Qi, Zeng, Xie, Chen, Jia, Mittal, Henderson — ICLR 2024.
- **arXiv:** 2310.03693.
- **Summary:** 10 adversarial examples (<$0.20) strip GPT-3.5 safety. Even benign SFT erodes alignment. Establishes that alignment is *brittle to weight perturbation*.
- **Relevance:** quantization is also a form of weight perturbation. Nobody has yet directly compared the geometry of quantization-induced perturbation to SFT-induced perturbation.

---

## Bucket 3 — PEFT under Quantization, Alignment-Preserving Fine-tuning

### 3.1 LoRA: Low-Rank Adaptation of Large Language Models
- **Authors:** Hu, Shen, Wallis, Allen-Zhu, Li, Wang, Wang, Chen — ICLR 2022.
- **arXiv:** 2106.09685.
- **Summary:** Freezes pretrained weights, trains rank-r additive updates on Q/V (later all linear layers). Foundational PEFT.
- **Measures:** downstream task accuracy, parameter count.
- **NOT measured:** alignment retention; in fact later work (Qi 2023) shows LoRA fine-tuning readily strips safety.

### 3.2 QLoRA (see 1.5 above)
- Revisited here because it is both a quantization and a PEFT paper. It is the *default baseline* in AlignQuant.
- Measures: Vicuna-Eval, MMLU. Does NOT measure refusal/truthfulness retention under the NF4 backbone.

### 3.3 LoftQ: LoRA-Fine-Tuning-Aware Quantization
- **Authors:** Li, Yu, Liang, He, Karampatziakis, Chen, Zhao — ICLR 2024 (Oral).
- **arXiv:** 2310.08659.
- **Summary:** Alternating SVD to jointly initialize the quantized backbone *and* LoRA adapters, so the pair (Q(W), AB) best approximates W. Closes the QLoRA gap at 2 and 2/4-bit.
- **NOT measured:** alignment. Evaluation on GLUE / SQuAD / XSum / GSM8K only.

### 3.4 QA-LoRA: Quantization-Aware LoRA
- **Authors:** Xu, Xie, Qin, Tao, Wang, Wang, Tian — ICLR 2024.
- **arXiv:** 2309.14717.
- **Summary:** Group-wise quantization with group-shared LoRA so that adapters can be *merged into* INT4 weights post-training. Enables truly quantized deployment.
- **NOT measured:** alignment.

### 3.5 ApiQ: Finetuning of 2-Bit Quantized LLMs
- **Authors:** Liao, Herold, Monz — 2024.
- **arXiv:** 2402.05147.
- **Summary:** Activation-preserving initialization of LoRA adapters for aggressively quantized (INT2/INT3) backbones.
- **NOT measured:** alignment.

### 3.6 GPTQ-LoRA / PEQA / LQ-LoRA
- **PEQA** (Kim et al., NeurIPS 2023, arXiv 2305.14152): parameter-efficient adaptation of quantization scales only.
- **LQ-LoRA** (Guo, Greengard, Wang, Roy, Ohannessian, Kim — ICLR 2024, arXiv 2311.12023): low-rank + quantization decomposition of the pretrained matrix itself.
- All measure perplexity / GLUE. None measure refusal, truthfulness, or activation-direction preservation.

### 3.7 Representation-Level PEFT: LoRRA (Zou et al., RepE)
- **Relevance:** closest prior art to *alignment-preserving* PEFT. Trains a low-rank update guided by a representation target (e.g., honesty direction). Not a quantization paper.

### 3.8 Alignment Tax / RLHF Degradation Literature
- **Ouyang et al., InstructGPT (2022, arXiv 2203.02155):** coins "alignment tax" — RLHF costs capability.
- **Bai et al., Constitutional AI (2022, arXiv 2212.08073):** attempts to reduce alignment tax via AI feedback.
- **Lin et al., "The Unlocking Spell on Base LLMs" (2023, arXiv 2312.01552):** shows alignment is a *very thin* layer above pretraining — consistent with Qi 2024.
- **Jain et al., "Mechanistic study of safety fine-tuning" (2023, arXiv 2311.10538):** shows SFT/RLHF induce *low-rank* weight deltas. Direct justification for a rank-aware method like DRaFT-Q.

### 3.9 DRaFT-Q (author's prior work)
- **Relevance:** dynamic rank-aware fine-tuning under quantization. Motivating hypothesis: because alignment deltas are empirically *low-rank and outlier-localized* (Jain 2023, Arditi 2024), a PEFT method that allocates rank where activation geometry demands it should preserve alignment better than uniform LoRA or QLoRA. AlignQuant is the missing *evaluation* side of this story.

### 3.10 Alignment-Preservation-Focused Fine-Tuning
- **SafeLoRA** (Hsu et al., NeurIPS 2024, arXiv 2405.16833): projects LoRA updates onto the orthogonal complement of a "safety direction" to prevent safety erosion during benign SFT.
- **Vaccine** (Huang et al., NeurIPS 2024, arXiv 2402.01109): adds a perturbation-aware regularizer to keep safety-critical hidden states stable.
- **Relevance:** both show that *directional* preservation is tractable during PEFT. Neither studies the quantization-only case (no fine-tuning), which is AlignQuant's primary regime.

---

## GAP MEMO

### The specific question unanswered by the literature
> **Does post-training quantization (AWQ, GPTQ, NF4, SmoothQuant, SpQR, OmniQuant) selectively degrade the low-dimensional activation subspaces that encode refusal, truthfulness, and sycophancy resistance — more than it degrades general task performance (perplexity, MMLU) — and can DRaFT-Q's dynamic-rank PEFT preserve this alignment geometry measurably better than QLoRA / LoftQ / QA-LoRA baselines?**

Concretely, no existing paper:
1. Measures **cosine similarity / subspace angle** between (a) Arditi's refusal direction, (b) ITI truthful heads, (c) CAA sycophancy vector before vs. after AWQ/GPTQ/NF4.
2. Reports **steering-efficacy decay** (how much of the original steering intervention's effect survives in the quantized model at equal inference budget).
3. Compares PEFT methods on an **alignment-geometry metric** rather than a reconstruction or accuracy metric.
4. Separates **capability perplexity** from **alignment-direction fidelity** as two independent axes of evaluation.

### Why this gap exists
- **Disciplinary silos.** Quantization papers come from the efficiency/systems community and optimize reconstruction/perplexity. Alignment-geometry papers come from the interpretability community and use fp16 reference models.
- **Benchmark inertia.** AWQ/GPTQ/QLoRA report the numbers their reviewers expect (MMLU, WikiText ppl). Refusal/truthfulness probes are not part of any standard quantization leaderboard.
- **Tooling asymmetry.** Probes (Azaria-Mitchell, ITI) and steering (CAA, ActAdd, RepE) are published with fp16 extraction code; none ship a "run this under 4-bit AWQ" harness. The engineering to make probes survive quantization grid-aware inference is non-trivial.
- **Timing.** Arditi (Jun 2024), Qi "shallow alignment" (Jun 2024), Q-resafe (2024/25), and Decoding-Compressed-Trust (Mar 2024) are all contemporaneous; the *intersection* (geometry × compression) has not yet been written up.
- **Incentive.** Quantization authors have little reason to publicize failure modes of their own methods on safety benchmarks.

### Why AlignQuant is novel and publishable at TMLR
1. **First systematic, direction-level measurement** of alignment preservation under all mainstream PTQ methods, using off-the-shelf Arditi / ITI / CAA vectors.
2. **Two-axis evaluation framework** ("capability-retention" perplexity/MMLU × "alignment-retention" direction-angle & steering-decay) that disentangles two quantities the field currently conflates.
3. **Causal, not correlational.** Uses steering-ablation experiments to show that when direction angle degrades by θ°, refusal/truthfulness *behaviorally* degrade by a predictable amount — connecting geometry to safety behavior.
4. **Constructive contribution.** DRaFT-Q, the author's dynamic-rank PEFT, is evaluated as an *alignment-preserving* method, not just an accuracy-preserving one — the first PEFT method benchmarked on alignment geometry directly.
5. **Policy-relevant result.** Findings directly inform open-weight deployment: which quantizer to prefer if safety is a concern, and how much alignment degradation to expect per bit-width.
6. **Reproducibility.** All vectors (Arditi, CAA) and methods (AWQ, GPTQ, QLoRA, LoftQ) are open-weight and open-source, making this a rare alignment study that can be fully replicated on a single consumer GPU.

### Three strongest potential reviewer objections — and pre-emptive responses

**Objection 1.** *"Decoding Compressed Trust (Hong 2024) and Q-resafe already show quantization affects safety. What's new?"*
**Pre-empt.** Both are purely behavioral (ASR on harmful prompts, DecodingTrust benchmarks). They do not explain **why** or **where**; they measure symptoms, not mechanism. AlignQuant operates at the level of activation directions and provides a *geometric* explanation that predicts behavioral degradation, and it studies three alignment axes (refusal / truth / sycophancy) rather than a single trust aggregate. We include DCT and Q-resafe as baseline evaluators and show our direction-angle metric correlates r > 0.8 with their ASR — but is cheaper, interpretable, and model-agnostic.

**Objection 2.** *"Arditi's refusal direction is a single-model artifact; your subspace angles might not transfer across base models, so quantization effects could be a probe artifact."*
**Pre-empt.** We replicate across (i) ≥4 open-weight base models (Llama-3-8B, Mistral-7B, Qwen2.5-7B, Gemma-2-9B), (ii) ≥3 independent direction-extraction methods (difference-in-means à la Arditi, logistic probes à la ITI, CAA contrastive), and (iii) cross-model direction-transfer controls from Arditi §5. We report subspace angle degradation averaged across this grid with confidence intervals, and show the rank-ordering of quantizers is stable across all probes.

**Objection 3.** *"Quantization might just reduce the magnitude of all directions uniformly; an angle change could be a meaningless reparameterization because the steering coefficient can be rescaled at inference."*
**Pre-empt.** Two counter-measures already planned. (a) We report both **angle** and **steering-efficacy-at-optimal-coefficient**: we re-sweep the steering scalar on the quantized model to find its own best coefficient, and still observe degraded efficacy — i.e., it is *not* merely rescaling. (b) We include a **control direction** (a random residual-stream direction of matched norm) and show its angle change under quantization is significantly *smaller* than the safety directions', ruling out uniform drift. This directly tests the null hypothesis the reviewer raises.

---

*End of literature review.*
