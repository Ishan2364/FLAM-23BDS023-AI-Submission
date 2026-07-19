# Part C — Decision Memo: Casual Tone in 6 Indic Languages

**Recommendation: (b) a small (≤1B) inference-time rewriter model**, trained via LoRA on synthetic formal→casual pairs, sitting after the main model.

**Why not the alternatives:** (a) SFT on the main model risks unverifiable regressions in 4 of 6 languages our reviewer can't check, and is riskier to roll back mid-flight. (c) Prompt-only is the safest fallback but likely too weak to fix a "textbook-formal" style problem reliably across 6 typologically different languages — kept as the fallback, not the primary bet.

## Assumptions

- Synthetic (formal, casual) pairs can be generated using the production model itself, few-shot prompted, run locally — no external API budget needed.
- Style transfer (not knowledge injection) needs modest data: ~3,000 pairs/language is enough to steer a ≤1B rewriter via LoRA.
- The Hindi/Kannada reviewer's judgments are a reasonable proxy signal for whether the *approach* works at all, even though they can't directly verify Bengali/Tamil/Telugu/Marathi output.
- A ≤1B rewriter adds acceptable latency as a second small forward pass (no external call, all on the same GPU/serving path).

## Back-of-envelope arithmetic

- **Data volume:** 6 languages × 3,000 pairs = 18,000 synthetic pairs. Generation at ~1.5s/pair on the A100 ≈ 7.5 GPU-hours.
- **Training cost:** LoRA fine-tune of a ≤1B model on 18k examples, 3 epochs ≈ 9 GPU-hours per run. Two weeks of A100 time ≈ 330+ GPU-hours available — generation + training + 2-3 iteration rounds costs well under 50 GPU-hours, leaving comfortable margin for hyperparameter passes.
- **Reviewer throughput:** 10h/week × 2 weeks (before the 3rd week's launch review) = 20 hours, at ~120 short judgments/hour ≈ 2,400 reviewable examples — enough to fully evaluate held-out Hindi/Kannada sets (~500-1000 examples each) with room to re-review after a training iteration.
- **Unverified languages (tam/tel/ben/mar):** no native review capacity this cycle — quality there rests on the generation pipeline being consistent across languages, checked only by automated proxies (self-consistency scoring), not human judgment.

## Success metric (numeric threshold)

On a held-out set of ≥200 examples per language, **Hindi and Kannada: ≥75% rated "casual and natural" by the native reviewer, and ≥90% rated "meaning preserved"** (no correctness regressions). For the other 4 languages, track an automated casualness/self-consistency proxy score, reported as unverified pending future native review.

## Kill criterion

**By end of week 2:** if Hindi/Kannada casualness rating is below 60%, OR meaning-preservation drops below 85%, abandon the rewriter and ship prompt-engineering-only (option c) for the week-3 launch review. Also an immediate kill regardless of casualness gains: if the reviewer flags hallucination/factual drift in >5% of rewritten Hindi/Kannada outputs.

## Day-1 experiment

Generate a small batch (~50 pairs/language) of formal→casual examples using the production model itself, and get the Hindi/Kannada subset spot-checked by the reviewer that same day — before spending any GPU time on training. If the base model can't produce convincing casual Hindi/Kannada examples at the generation stage, the whole synthetic-data approach is falsified cheaply, before committing the 2-week GPU budget to it.
