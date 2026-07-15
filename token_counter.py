# token_counter.py — Run this to measure actual token usage for your queries

import os
import sys

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['GLASSBOT_SKIP_CONFIG'] = '1'

import tiktoken
from chatbot.prompts import SYSTEM_PROMPT, render_metadata
from chatbot.metadata_service import _FALLBACK_TABLES

enc = tiktoken.encoding_for_model("gpt-4o")  # cl100k_base works for most models

def count_tokens(text: str) -> int:
    return len(enc.encode(text))

# ----- Measure fixed costs -----
system_prompt_tokens = count_tokens(SYSTEM_PROMPT)
metadata_context_tokens = count_tokens(render_metadata(_FALLBACK_TABLES))

print("=" * 60)
print("TOKEN USAGE ANALYSIS — GlassBot")
print("=" * 60)
print()
print("FIXED COSTS (same for every query):")
print(f"  System prompt:      {system_prompt_tokens:,} tokens")
print(f"  Metadata context:   {metadata_context_tokens:,} tokens")
print(f"  Fixed total:        {system_prompt_tokens + metadata_context_tokens:,} tokens")
print()

# ----- Sample questions to measure variable costs -----
sample_questions = [
    "Show me all delivered orders",
    "Give me completed production orders",
    "What is the average temperature for machine M01?",
    "Show me production targets where actual qty is less than planned",
    "Show all customer orders along with their corresponding production orders",
    "Which machines are currently running?",
    "How many orders does each customer have?",
    "Show me defects by machine for last week",
    "What is today's production target?",
    "Give me dashboard summary",
]

print(f"VARIABLE COSTS (sample of {len(sample_questions)} questions):")
print()

total_input = 0
total_output_estimate = 0

for i, q in enumerate(sample_questions, 1):
    q_tokens = count_tokens(q)
    # Input = system_prompt + metadata + question + overhead
    input_tokens = system_prompt_tokens + metadata_context_tokens + q_tokens + 20  # 20 for message framing
    output_estimate = 80  # avg SQL output is ~80 tokens

    # Call 2: ResponseFormatter
    summary_input = 150 + 200  # summary prompt + sample results
    summary_output = 100

    total_per_query = input_tokens + output_estimate + summary_input + summary_output
    total_input += input_tokens + summary_input
    total_output_estimate += output_estimate + summary_output

    print(f"  Q{i:2d}: \"{q[:50]}{'...' if len(q) > 50 else ''}\"")
    print(f"       Question tokens: {q_tokens} | Total per query: ~{total_per_query:,}")

print()
print("-" * 60)

avg_per_query = (total_input + total_output_estimate) // len(sample_questions)
print(f"AVERAGE per query:    ~{avg_per_query:,} tokens")
print()
print("PROJECTIONS:")
print(f"  10 queries:         ~{avg_per_query * 10:,} tokens")
print(f"  50 queries:         ~{avg_per_query * 50:,} tokens")
print(f"  100 queries:        ~{avg_per_query * 100:,} tokens")
print(f"  500 queries:        ~{avg_per_query * 500:,} tokens")
print(f"  1000 queries:       ~{avg_per_query * 1000:,} tokens")
print()
print("NOTE: These estimates assume no conversation history.")
print("      Multi-turn adds ~200-800 tokens per prior turn.")
