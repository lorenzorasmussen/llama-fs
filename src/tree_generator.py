import json

from groq import Groq

from src.config import GROQ_API_KEY, LLM_MODEL
from src.prompts import FILE_PROMPT


def create_file_tree(summaries: list, session):
    client = Groq(api_key=GROQ_API_KEY)
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": FILE_PROMPT},
            {"role": "user", "content": json.dumps(summaries)},
        ],
        model=LLM_MODEL,
        response_format={"type": "json_object"},  # Uncomment if needed
        temperature=0,
    )

    file_tree = json.loads(chat_completion.choices[0].message.content)["files"]
    return file_tree
