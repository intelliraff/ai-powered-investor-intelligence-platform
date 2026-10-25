from pydantic import BaseModel
from dotenv import load_dotenv
import ollama
import json
import os
import ollama

load_dotenv()


def get_openai_client():
    """
    Create a local Ollama client.

    No API key or Azure account required.
    """

    return ollama.Client(
        host=os.getenv("OLLAMA_HOST", "http://ollama:11434")
    )

def get_structured_completion(
    prompt: str,
    response_model: type[BaseModel],
    model: str | None = None
) -> BaseModel:
    """
    Generate a structured response using a local Ollama model.

    Args:
        prompt: Input prompt.
        response_model: Pydantic response model.
        model: Ollama model name.

    Returns:
        Parsed Pydantic response model.
    """

    # Default local model
    model = model or "llama3.2"

    client = get_openai_client()

    # Tell the model exactly what JSON structure we expect
    schema = response_model.model_json_schema()

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert financial analyst. "
                "Return ONLY valid JSON matching the provided schema. "
                "Do not include markdown, explanations, or extra text."
            )
        },
        {
            "role": "user",
            "content": (
                f"{prompt}\n\n"
                "Return the result according to this JSON schema:\n"
                f"{json.dumps(schema, indent=2)}"
            )
        }
    ]

    print(f"[debug] Using local Ollama model: {model}")

    try:

        response = client.chat(
            model=model,
            messages=messages,
            format=schema
        )

        text = response["message"]["content"]

        print("[debug] Ollama response:")
        print(text)

        # Parse the JSON returned by Ollama
        data = json.loads(text)

        # Convert JSON → Pydantic model
        if hasattr(response_model, "model_validate"):
            return response_model.model_validate(data)

        # Pydantic v1 fallback
        return response_model.parse_obj(data)

    except Exception as exc:

        raise RuntimeError(
            f"Failed to generate structured response "
            f"using Ollama model '{model}': {exc}"
        ) from exc