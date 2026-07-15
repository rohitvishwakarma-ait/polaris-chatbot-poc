---
title: "Pricing"
source: "https://developers.cloudflare.com/workers-ai/platform/pricing/#llm-model-pricing"
author:
published: 2026-07-09
created: 2026-07-15
description: "Workers AI pricing is based on Neurons, with a free daily allocation and per-model rates."
tags:
  - "clippings"
---
Workers AI is included in both the [Free and Paid Workers plans](https://developers.cloudflare.com/workers/platform/pricing/) and is priced at **$0.011 per 1,000 Neurons**.

Our free allocation allows anyone to use a total of **10,000 Neurons per day at no charge**. To use more than 10,000 Neurons per day, you need to sign up for the [Workers Paid plan](https://developers.cloudflare.com/workers/platform/pricing/#workers). On Workers Paid, you will be charged at $0.011 / 1,000 Neurons for any usage above the free allocation of 10,000 Neurons per day.

You can monitor your Neuron usage in the [Cloudflare Workers AI dashboard ↗](https://dash.cloudflare.com/?to=/:account/ai/workers-ai).

All limits reset daily at 00:00 UTC. If you exceed any one of the above limits, further operations will fail with an error.

|  | Free   allocation | Pricing |
| --- | --- | --- |
| Workers Free | 10,000 Neurons per day | N/A - Upgrade to Workers Paid |
| Workers Paid | 10,000 Neurons per day | $0.011 / 1,000 Neurons |

## What are Neurons?

Neurons are our way of measuring AI outputs across different models, representing the GPU compute needed to perform your request. Our serverless model allows you to pay only for what you use without having to worry about renting, managing, or scaling GPUs.

## LLM model pricing

| Model | Price in Tokens | Price in Neurons |
| --- | --- | --- |
| @cf/meta/llama-3.2-1b-instruct | $0.027 per M input tokens   $0.201 per M output tokens | 2457 neurons per M input tokens   18252 neurons per M output tokens |
| @cf/meta/llama-3.2-3b-instruct | $0.051 per M input tokens   $0.335 per M output tokens | 4625 neurons per M input tokens   30475 neurons per M output tokens |
| @cf/meta/llama-3.1-8b-instruct-fp8-fast | $0.045 per M input tokens   $0.384 per M output tokens | 4119 neurons per M input tokens   34868 neurons per M output tokens |
| @cf/meta/llama-3.2-11b-vision-instruct | $0.049 per M input tokens   $0.676 per M output tokens | 4410 neurons per M input tokens   61493 neurons per M output tokens |
| @cf/meta/llama-3.1-70b-instruct-fp8-fast | $0.293 per M input tokens   $2.253 per M output tokens | 26668 neurons per M input tokens   204805 neurons per M output tokens |
| @cf/meta/llama-3.3-70b-instruct-fp8-fast | $0.293 per M input tokens   $2.253 per M output tokens | 26668 neurons per M input tokens   204805 neurons per M output tokens |
| @cf/deepseek-ai/deepseek-r1-distill-qwen-32b | $0.497 per M input tokens   $4.881 per M output tokens | 45170 neurons per M input tokens   443756 neurons per M output tokens |
| @cf/mistral/mistral-7b-instruct-v0.1 | $0.110 per M input tokens   $0.190 per M output tokens | 10000 neurons per M input tokens   17300 neurons per M output tokens |
| @cf/mistralai/mistral-small-3.1-24b-instruct | $0.351 per M input tokens   $0.555 per M output tokens | 31876 neurons per M input tokens   50488 neurons per M output tokens |
| @cf/meta/llama-3.1-8b-instruct | $0.282 per M input tokens   $0.827 per M output tokens | 25608 neurons per M input tokens   75147 neurons per M output tokens |
| @cf/meta/llama-3.1-8b-instruct-fp8 | $0.152 per M input tokens   $0.287 per M output tokens | 13778 neurons per M input tokens   26128 neurons per M output tokens |
| @cf/meta/llama-3.1-8b-instruct-awq | $0.123 per M input tokens   $0.266 per M output tokens | 11161 neurons per M input tokens   24215 neurons per M output tokens |
| @cf/meta/llama-3-8b-instruct | $0.282 per M input tokens   $0.827 per M output tokens | 25608 neurons per M input tokens   75147 neurons per M output tokens |
| @cf/meta/llama-3-8b-instruct-awq | $0.123 per M input tokens   $0.266 per M output tokens | 11161 neurons per M input tokens   24215 neurons per M output tokens |
| @cf/meta/llama-2-7b-chat-fp16 | $0.556 per M input tokens   $6.667 per M output tokens | 50505 neurons per M input tokens   606061 neurons per M output tokens |
| @cf/meta/llama-guard-3-8b | $0.484 per M input tokens   $0.030 per M output tokens | 44003 neurons per M input tokens   2730 neurons per M output tokens |
| @cf/meta/llama-4-scout-17b-16e-instruct | $0.270 per M input tokens   $0.850 per M output tokens | 24545 neurons per M input tokens   77273 neurons per M output tokens |
| @cf/google/gemma-3-12b-it | $0.345 per M input tokens   $0.556 per M output tokens | 31371 neurons per M input tokens   50560 neurons per M output tokens |
| @cf/qwen/qwq-32b | $0.660 per M input tokens   $1.000 per M output tokens | 60000 neurons per M input tokens   90909 neurons per M output tokens |
| @cf/qwen/qwen2.5-coder-32b-instruct | $0.660 per M input tokens   $1.000 per M output tokens | 60000 neurons per M input tokens   90909 neurons per M output tokens |
| @cf/qwen/qwen3-30b-a3b-fp8 | $0.051 per M input tokens   $0.335 per M output tokens | 4625 neurons per M input tokens   30475 neurons per M output tokens |
| @cf/openai/gpt-oss-120b | $0.350 per M input tokens   $0.750 per M output tokens | 31818 neurons per M input tokens   68182 neurons per M output tokens |
| @cf/openai/gpt-oss-20b | $0.200 per M input tokens   $0.300 per M output tokens | 18182 neurons per M input tokens   27273 neurons per M output tokens |
| @cf/aisingapore/gemma-sea-lion-v4-27b-it | $0.351 per M input tokens   $0.555 per M output tokens | 31876 neurons per M input tokens   50488 neurons per M output tokens |
| @cf/ibm-granite/granite-4.0-h-micro | $0.017 per M input tokens   $0.112 per M output tokens | 1542 neurons per M input tokens   10158 neurons per M output tokens |
| @cf/zai-org/glm-4.7-flash | $0.060 per M input tokens   $0.400 per M output tokens | 5500 neurons per M input tokens   36400 neurons per M output tokens |
| @cf/zai-org/glm-5.2 | $1.400 per M input tokens   $0.260 per M cached input tokens   $4.400 per M output tokens | 127273 neurons per M input tokens   23636 neurons per M cached input tokens   400000 neurons per M output tokens |
| @cf/nvidia/nemotron-3-120b-a12b | $0.500 per M input tokens   $1.500 per M output tokens | 45455 neurons per M input tokens   136364 neurons per M output tokens |
| @cf/moonshotai/kimi-k2.5 | $0.600 per M input tokens   $0.100 per M cached input tokens   $3.000 per M output tokens | 54545 neurons per M input tokens   9091 neurons per M cached input tokens   272727 neurons per M output tokens |
| @cf/moonshotai/kimi-k2.6 | $0.950 per M input tokens   $0.160 per M cached input tokens   $4.000 per M output tokens | 86364 neurons per M input tokens   14545 neurons per M cached input tokens   363636 neurons per M output tokens |
| @cf/moonshotai/kimi-k2.7-code | $0.950 per M input tokens   $0.190 per M cached input tokens   $4.000 per M output tokens | 86364 neurons per M input tokens   17273 neurons per M cached input tokens   363636 neurons per M output tokens |
| @cf/google/gemma-4-26b-a4b-it | $0.100 per M input tokens   $0.300 per M output tokens | 9091 neurons per M input tokens   27273 neurons per M output tokens |