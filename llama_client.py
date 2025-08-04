import os
from dotenv import load_dotenv
from llama_api_client import LlamaAPIClient
# from llama_api_client.types import UserMessageParam

load_dotenv()

client = LlamaAPIClient(
    api_key=os.environ.get("LLAMA_API_KEY")
)

def query_llama(term):
    try:
        # Step 1: Get detailed meaning
        detailed_response = client.chat.completions.create(
            model="Llama-4-Maverick-17B-128E-Instruct-FP8",
            messages=[
                {"role": "user", "content": f"What does the slang term '{term}' mean?"}
            ],
        )
        full_meaning = detailed_response.completion_message.content.text.strip()

        # Step 2: Use summarize_definition for summary
        short_summary = summarize_definition(term, full_meaning)

        return f"{full_meaning}\n\n✏️ Simple Summary: {short_summary}"

    except Exception as e:
        print("LLAMA API Error:", e)
        return None

def summarize_definition(term, definition, summary=None):
    """
    Returns a summary for the slang term.
    If `summary` is provided (e.g., from a dataset), returns it.
    Otherwise, queries the LLM for a summary.
    """
    if summary:
        return summary
    try:
        response = client.chat.completions.create(
            model="Llama-4-Maverick-17B-128E-Instruct-FP8",
            messages=[
                {
                    "role": "user",
                    "content": f"Summarize the slang term '{term}', which means: '{definition}', in one short sentence using simple English."
                }
            ],
        )
        return response.completion_message.content.text.strip()
    except Exception as e:
        print("LLAMA Summary Error:", e)
        return "Summary not available."