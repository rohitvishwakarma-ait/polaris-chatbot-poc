# token_counter.py — Run this to measure actual token usage for your queries

import os
import sys

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['POLARIS_SKIP_CONFIG'] = '1'

import tiktoken
from chatbot.prompts import build_system_prompt, render_metadata
from chatbot.models import TableMetadata, ColumnInfo

enc = tiktoken.encoding_for_model("gpt-4o")  # cl100k_base works for most models

# Example tables to demonstrate token counting (replace with your actual metadata)
_EXAMPLE_TABLES = [
    TableMetadata(
        fqn="my_postgres.public.orders",
        name="orders",
        description="Customer orders table",
        columns=[
            ColumnInfo("id", "integer", "Primary key"),
            ColumnInfo("customer_name", "varchar", "Customer name"),
            ColumnInfo("total", "decimal", "Order total"),
            ColumnInfo("status", "varchar", "Order status"),
            ColumnInfo("created_at", "timestamp", "Creation timestamp"),
        ],
        tags=["Sales"],
    ),
    TableMetadata(
        fqn="my_postgres.public.products",
        name="products",
        description="Product catalog",
        columns=[
            ColumnInfo("id", "integer", "Primary key"),
            ColumnInfo("name", "varchar", "Product name"),
            ColumnInfo("price", "decimal", "Unit price"),
            ColumnInfo("category", "varchar", "Category"),
        ],
        tags=["Catalog"],
    ),
]


def count_tokens(text: str) -> int:
    return len(enc.encode(text))


# ----- Measure costs with example tables -----
system_prompt = build_system_prompt(_EXAMPLE_TABLES)
system_prompt_tokens = count_tokens(system_prompt)
metadata_context_tokens = count_tokens(render_metadata(_EXAMPLE_TABLES))

print("=" * 60)
print("TOKEN USAGE ANALYSIS — Polaris")
print("=" * 60)
print()
print(f"Using {len(_EXAMPLE_TABLES)} example table(s) for estimation.")
print()
print("FIXED COSTS (same for every query):")
print(f"  System prompt:      {system_prompt_tokens:,} tokens")
print(f"  (Metadata embedded in prompt, no separate context needed)")
print(f"  Fixed total:        {system_prompt_tokens:,} tokens")
print()

# ----- Sample questions to measure variable costs -----
sample_questions = [
    "Show me all orders",
    "What products are in the catalog?",
    "How many orders per customer?",
    "Show me orders with total above 100",
    "List products by category",
]

print(f"VARIABLE COSTS (sample of {len(sample_questions)} questions):")
print()

total_input = 0
total_output_estimate = 0

for i, q in enumerate(sample_questions, 1):
    q_tokens = count_tokens(q)
    input_tokens = system_prompt_tokens + q_tokens + 20
    output_estimate = 80

    summary_input = 150 + 200
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
print("NOTE: Token usage scales with the number of tables/columns configured.")
print("      More data sources = larger system prompt = higher cost per query.")
print("      Multi-turn adds ~200-800 tokens per prior turn.")
