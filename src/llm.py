import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

def _real_call(prompt: str) -> list[dict]:
    """Call Claude API. Requires ANTHROPIC_API_KEY in env or .env."""
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []

def _mock_call(prompt: str) -> list[dict]:
    """Mock LLM that returns example inferred relationships."""
    return [
        {
            "source": "src/main",
            "target": "src/utils",
            "relation": "semantically_similar_to",
            "confidence": 0.8,
            "evidence": "Both handle configuration loading."
        },
        {
            "source": "DataProcessor.process",
            "target": "DataLoader.load_data",
            "relation": "depends_on",
            "confidence": 0.9,
            "evidence": "processing step follows data loading."
        }
    ]

def extract_semantic_relationships(file_contents: dict[str, str]) -> list[dict]:
    """Return a list of inferred edges given a dictionary of filename->content."""
    summaries = []
    for fname, content in file_contents.items():
        summaries.append(f"FILE: {fname}\n```\n{content[:2000]}\n```")
    prompt = (
        "You are a codebase analysis assistant. Given the following files and their contents, "
        "return a JSON array of semantic relationships you can infer between different parts of the code. "
        "Each relationship object must have: source (string), target (string), relation (string), confidence (float 0-1), evidence (string). "
        "Only output the JSON array, nothing else.\n\n" +
        "\n\n".join(summaries)
    )

    if os.getenv("ANTHROPIC_API_KEY") and os.getenv("ANTHROPIC_API_KEY") != "your-key-here":
        try:
            return _real_call(prompt)
        except Exception as e:
            print(f"Claude call failed, falling back to mock: {e}")
            return _mock_call(prompt)
    else:
        print("No valid ANTHROPIC_API_KEY found, using mock relationships.")
        return _mock_call(prompt)
