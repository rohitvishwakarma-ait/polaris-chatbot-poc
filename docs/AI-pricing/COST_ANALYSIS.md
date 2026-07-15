# Polaris ChatBot — AI Model Cost Analysis

## Token Usage (from token_counter.py)

| Metric | Per Query | Per 100 Queries |
|--------|-----------|-----------------|
| Input tokens | ~2,496 | 249,600 |
| Output tokens | ~350 | 35,000 |
| Total tokens | ~2,846 | 284,600 |

**Exchange rate:** 1 USD = ₹96.36 INR

---

## Cloudflare Workers AI (Current Setup)

| Model | Input $/MTok | Output $/MTok | Cost (100q) USD | INR |
|-------|-------------|--------------|-----------------|-----|
| **@cf/meta/llama-3.3-70b-instruct-fp8-fast (YOUR MODEL)** | $0.293 | $2.253 | $0.152 | **₹14.6** |
| @cf/meta/llama-3.1-8b-instruct-fp8-fast | $0.045 | $0.384 | $0.025 | ₹2.4 |
| @cf/meta/llama-3.2-3b-instruct | $0.051 | $0.335 | $0.024 | ₹2.4 |
| @cf/meta/llama-3.2-1b-instruct | $0.027 | $0.201 | $0.014 | ₹1.3 |
| @cf/qwen/qwen3-30b-a3b-fp8 | $0.051 | $0.335 | $0.024 | ₹2.4 |
| @cf/google/gemma-4-26b-a4b-it | $0.100 | $0.300 | $0.035 | ₹3.4 |
| @cf/meta/llama-4-scout-17b-16e-instruct | $0.270 | $0.850 | $0.097 | ₹9.4 |
| @cf/mistralai/mistral-small-3.1-24b-instruct | $0.351 | $0.555 | $0.107 | ₹10.3 |
| @cf/nvidia/nemotron-3-120b-a12b | $0.500 | $1.500 | $0.177 | ₹17.1 |
| @cf/moonshotai/kimi-k2.5 | $0.600 | $3.000 | $0.255 | ₹24.5 |
| @cf/deepseek-ai/deepseek-r1-distill-qwen-32b | $0.497 | $4.881 | $0.295 | ₹28.4 |
| @cf/moonshotai/kimi-k2.6 | $0.950 | $4.000 | $0.377 | ₹36.3 |

**Free tier:** 10,000 Neurons/day. Your model uses ~138 neurons/query = **~72 queries/day free**.

**With Caching (kimi models only):**

| Model | Cached Input $/MTok | Cost with 90% cache (100q) | INR |
|-------|--------------------|-----------------------------|-----|
| @cf/moonshotai/kimi-k2.5 | $0.100 | $0.130 | ₹12.5 |
| @cf/moonshotai/kimi-k2.6 | $0.160 | $0.178 | ₹17.2 |

---

## Claude (Anthropic)

### Standard Pricing

| Model | Input $/MTok | Output $/MTok | Cost (100q) USD | INR |
|-------|-------------|--------------|-----------------|-----|
| Claude Haiku 4.5 | $1.00 | $5.00 | $0.42 | ₹41 |
| Claude Sonnet 5 (intro till Aug 31, 2026) | $2.00 | $10.00 | $0.85 | ₹82 |
| Claude Sonnet 5 (after Sep 1, 2026) | $3.00 | $15.00 | $1.27 | ₹123 |
| Claude Sonnet 4.6 | $3.00 | $15.00 | $1.27 | ₹123 |
| Claude Sonnet 4.5 | $3.00 | $15.00 | $1.27 | ₹123 |
| Claude Opus 4.8 | $5.00 | $25.00 | $2.12 | ₹204 |
| Claude Opus 4.5 | $5.00 | $25.00 | $2.12 | ₹204 |
| Claude Fable 5 | $10.00 | $50.00 | $4.24 | ₹409 |

### With 5-minute Caching (90% of input tokens cached)

| Model | 5m Cache Write $/MTok | Cache Hit $/MTok | Cost (100q) USD | INR |
|-------|---------------------|-----------------|-----------------|-----|
| Claude Haiku 4.5 | $1.25 | $0.10 | $0.23 | ₹22 |
| Claude Sonnet 5 (intro) | $2.50 | $0.20 | $0.46 | ₹44 |
| Claude Sonnet 5 (after Sep) | $3.75 | $0.30 | $0.68 | ₹66 |
| Claude Opus 4.8 | $6.25 | $0.50 | $1.15 | ₹111 |

### Batch API (50% off)

| Model | Batch Input $/MTok | Batch Output $/MTok | Cost (100q) USD | INR |
|-------|-------------------|--------------------|-----------------|----|
| Claude Haiku 4.5 | $0.50 | $2.50 | $0.21 | ₹20 |
| Claude Sonnet 5 (intro) | $1.00 | $5.00 | $0.42 | ₹41 |
| Claude Opus 4.8 | $2.50 | $12.50 | $1.06 | ₹102 |

---

## Gemini (Google)

### Standard Pricing

| Model | Input $/MTok | Output $/MTok | Cost (100q) USD | INR |
|-------|-------------|--------------|-----------------|-----|
| Gemini 2.5 Flash-Lite | $0.10 | $0.40 | $0.039 | ₹3.7 |
| Gemini 3.1 Flash-Lite | $0.25 | $1.50 | $0.115 | ₹11.1 |
| Gemini 2.5 Flash | $0.30 | $2.50 | $0.162 | ₹15.7 |
| Gemini 3 Flash Preview | $0.50 | $3.00 | $0.230 | ₹22 |
| Gemini 2.5 Pro (≤200k) | $1.25 | $10.00 | $0.662 | ₹64 |
| Gemini 3.5 Flash | $1.50 | $9.00 | $0.689 | ₹66 |
| Gemini 3.1 Pro Preview (≤200k) | $2.00 | $12.00 | $0.919 | ₹89 |

### With Context Caching (90% cached at cache hit rate)

| Model | Cache Hit $/MTok | Cost with caching (100q) | INR |
|-------|-----------------|--------------------------|-----|
| Gemini 2.5 Flash-Lite | $0.01 | $0.019 | ₹1.8 |
| Gemini 2.5 Flash | $0.03 | $0.102 | ₹9.8 |
| Gemini 2.5 Pro | $0.125 | $0.410 | ₹39 |
| Gemini 3.5 Flash | $0.15 | $0.380 | ₹37 |

### Batch API (50% off)

| Model | Batch Input $/MTok | Batch Output $/MTok | Cost (100q) USD | INR |
|-------|-------------------|--------------------|-----------------|----|
| Gemini 2.5 Flash-Lite | $0.05 | $0.20 | $0.019 | ₹1.9 |
| Gemini 2.5 Flash | $0.15 | $1.25 | $0.081 | ₹7.8 |
| Gemini 2.5 Pro | $0.625 | $5.00 | $0.331 | ₹32 |

---

## OpenAI

### Standard Pricing

| Model | Input $/MTok | Output $/MTok | Cost (100q) USD | INR |
|-------|-------------|--------------|-----------------|-----|
| GPT-5-nano | $0.05 | $0.40 | $0.027 | ₹2.6 |
| GPT-4.1-nano | $0.10 | $0.40 | $0.039 | ₹3.7 |
| GPT-4o-mini | $0.15 | $0.60 | $0.058 | ₹5.6 |
| GPT-5.4-nano | $0.20 | $1.25 | $0.094 | ₹9 |
| GPT-5-mini | $0.25 | $2.00 | $0.132 | ₹12.8 |
| GPT-4.1-mini | $0.40 | $1.60 | $0.156 | ₹15 |
| GPT-5.6-luna | $1.00 | $6.00 | $0.460 | ₹44 |
| GPT-5.4-mini | $0.75 | $4.50 | $0.344 | ₹33 |
| o4-mini | $1.10 | $4.40 | $0.428 | ₹41 |
| GPT-5 | $1.25 | $10.00 | $0.662 | ₹64 |
| GPT-5.2 | $1.75 | $14.00 | $0.927 | ₹89 |
| GPT-4.1 | $2.00 | $8.00 | $0.779 | ₹75 |
| o3 | $2.00 | $8.00 | $0.779 | ₹75 |
| GPT-4o | $2.50 | $10.00 | $0.974 | ₹94 |
| GPT-5.4 | $2.50 | $15.00 | $1.149 | ₹111 |
| GPT-5.6-terra | $2.50 | $15.00 | $1.149 | ₹111 |
| GPT-5.6-sol | $5.00 | $30.00 | $2.298 | ₹221 |
| o3-pro | $20.00 | $80.00 | $7.791 | ₹751 |

### With Caching (90% of input cached)

| Model | Cached Input $/MTok | Cost with caching (100q) | INR |
|-------|--------------------|--------------------------|----|
| GPT-5-nano | $0.005 | $0.016 | ₹1.6 |
| GPT-4.1-nano | $0.025 | $0.022 | ₹2.1 |
| GPT-4o-mini | $0.075 | $0.042 | ₹4.0 |
| GPT-5-mini | $0.025 | $0.076 | ₹7.3 |
| GPT-4.1-mini | $0.10 | $0.090 | ₹8.7 |
| GPT-4.1 | $0.50 | $0.442 | ₹43 |
| GPT-4o | $1.25 | $0.694 | ₹67 |

### Batch API (50% off)

| Model | Batch Input $/MTok | Batch Output $/MTok | Cost (100q) USD | INR |
|-------|-------------------|--------------------|-----------------|----|
| GPT-5-nano | $0.025 | $0.20 | $0.013 | ₹1.3 |
| GPT-4.1-nano | $0.05 | $0.20 | $0.019 | ₹1.9 |
| GPT-4o-mini | $0.075 | $0.30 | $0.029 | ₹2.8 |
| GPT-4.1 | $1.00 | $4.00 | $0.389 | ₹37 |

---

## Final Ranking — All Providers (100 Queries)

### Standard Pricing (no caching, no batch)

| Rank | Provider | Model | USD | INR |
|------|----------|-------|-----|-----|
| 1 | Cloudflare | llama-3.2-1b-instruct | $0.014 | ₹1.3 |
| 2 | Cloudflare | llama-3.2-3b / qwen3-30b | $0.024 | ₹2.4 |
| 3 | Cloudflare | llama-3.1-8b-fp8-fast | $0.025 | ₹2.4 |
| 4 | OpenAI | GPT-5-nano | $0.027 | ₹2.6 |
| 5 | Cloudflare | gemma-4-26b-a4b-it | $0.035 | ₹3.4 |
| 6 | Gemini | 2.5 Flash-Lite | $0.039 | ₹3.7 |
| 7 | OpenAI | GPT-4.1-nano | $0.039 | ₹3.7 |
| 8 | OpenAI | GPT-4o-mini | $0.058 | ₹5.6 |
| 9 | OpenAI | GPT-5.4-nano | $0.094 | ₹9 |
| 10 | Cloudflare | llama-4-scout-17b | $0.097 | ₹9.4 |
| 11 | Cloudflare | mistral-small-3.1-24b | $0.107 | ₹10.3 |
| 12 | Gemini | 3.1 Flash-Lite | $0.115 | ₹11.1 |
| 13 | OpenAI | GPT-5-mini | $0.132 | ₹12.8 |
| 14 | **Cloudflare** | **llama-3.3-70b (YOUR MODEL)** | **$0.152** | **₹14.6** |
| 15 | OpenAI | GPT-4.1-mini | $0.156 | ₹15 |
| 16 | Gemini | 2.5 Flash | $0.162 | ₹15.7 |
| 17 | Cloudflare | nemotron-3-120b | $0.177 | ₹17.1 |
| 18 | Gemini | 3 Flash Preview | $0.230 | ₹22 |
| 19 | Cloudflare | kimi-k2.5 | $0.255 | ₹24.5 |
| 20 | Cloudflare | deepseek-r1-qwen-32b | $0.295 | ₹28.4 |
| 21 | OpenAI | GPT-5.4-mini | $0.344 | ₹33 |
| 22 | Cloudflare | kimi-k2.6 | $0.377 | ₹36.3 |
| 23 | Claude | Haiku 4.5 | $0.424 | ₹41 |
| 24 | OpenAI | o4-mini | $0.428 | ₹41 |
| 25 | OpenAI | GPT-5.6-luna | $0.460 | ₹44 |
| 26 | Gemini | 2.5 Pro | $0.662 | ₹64 |
| 27 | OpenAI | GPT-5 | $0.662 | ₹64 |
| 28 | Gemini | 3.5 Flash | $0.689 | ₹66 |
| 29 | OpenAI | GPT-4.1 / o3 | $0.779 | ₹75 |
| 30 | Claude | Sonnet 5 (intro) | $0.849 | ₹82 |
| 31 | Gemini | 3.1 Pro Preview | $0.919 | ₹89 |
| 32 | OpenAI | GPT-4o | $0.974 | ₹94 |
| 33 | OpenAI | GPT-5.4 / GPT-5.6-terra | $1.149 | ₹111 |
| 34 | Claude | Sonnet 5 (after Sep) / Sonnet 4.6 | $1.274 | ₹123 |
| 35 | Claude | Opus 4.8 | $2.122 | ₹204 |
| 36 | OpenAI | GPT-5.6-sol | $2.298 | ₹221 |
| 37 | Claude | Fable 5 | $4.244 | ₹409 |
| 38 | OpenAI | o3-pro | $7.791 | ₹751 |

### With Caching (best case — 90% cache hit)

| Rank | Provider | Model | USD | INR |
|------|----------|-------|-----|-----|
| 1 | OpenAI | GPT-5-nano | $0.016 | ₹1.6 |
| 2 | Gemini | 2.5 Flash-Lite | $0.019 | ₹1.8 |
| 3 | OpenAI | GPT-4.1-nano | $0.022 | ₹2.1 |
| 4 | OpenAI | GPT-4o-mini | $0.042 | ₹4.0 |
| 5 | OpenAI | GPT-5-mini | $0.076 | ₹7.3 |
| 6 | OpenAI | GPT-4.1-mini | $0.090 | ₹8.7 |
| 7 | Gemini | 2.5 Flash | $0.102 | ₹9.8 |
| 8 | Cloudflare | kimi-k2.5 | $0.130 | ₹12.5 |
| 9 | Claude | Haiku 4.5 | $0.230 | ₹22 |
| 10 | Gemini | 2.5 Pro | $0.410 | ₹39 |
| 11 | OpenAI | GPT-4.1 | $0.442 | ₹43 |
| 12 | Claude | Sonnet 5 (intro) | $0.460 | ₹44 |
| 13 | OpenAI | GPT-4o | $0.694 | ₹67 |
| 14 | Claude | Opus 4.8 | $1.150 | ₹111 |

### Batch API (50% off, no caching)

| Rank | Provider | Model | USD | INR |
|------|----------|-------|-----|-----|
| 1 | OpenAI | GPT-5-nano | $0.013 | ₹1.3 |
| 2 | Gemini | 2.5 Flash-Lite | $0.019 | ₹1.9 |
| 3 | OpenAI | GPT-4.1-nano | $0.019 | ₹1.9 |
| 4 | Claude | Haiku 4.5 | $0.212 | ₹20 |
| 5 | OpenAI | GPT-4o-mini | $0.029 | ₹2.8 |
| 6 | Gemini | 2.5 Flash | $0.081 | ₹7.8 |
| 7 | Gemini | 2.5 Pro | $0.331 | ₹32 |
| 8 | OpenAI | GPT-4.1 | $0.389 | ₹37 |
| 9 | Claude | Sonnet 5 (intro) | $0.424 | ₹41 |
| 10 | Claude | Opus 4.8 | $1.061 | ₹102 |

---

## Monthly Cost Projection

| Queries/month | Cloudflare 70B | GPT-5-nano | Gemini Flash-Lite | Claude Haiku 4.5 | GPT-4o |
|---------------|----------------|------------|-------------------|------------------|--------|
| 100 | ₹14.6 (₹0*) | ₹2.6 | ₹3.7 | ₹41 | ₹94 |
| 1,000 | ₹146 (₹106*) | ₹26 | ₹37 | ₹410 | ₹940 |
| 10,000 | ₹1,460 | ₹260 | ₹370 | ₹4,100 | ₹9,400 |
| 100,000 | ₹14,600 | ₹2,600 | ₹3,700 | ₹41,000 | ₹94,000 |

*Cloudflare free tier covers ~72 queries/day (~2,160/month). Costs shown in parentheses are after free tier deduction.

---

## Calculation Formula

