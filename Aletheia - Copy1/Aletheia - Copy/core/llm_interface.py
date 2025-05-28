# core/llm_interface.py
import openai
import os
from dotenv import load_dotenv
from typing import List, Optional

load_dotenv() # Load environment variables from .env

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY not found in .env file or environment variables.")
    # Potentially raise an error or handle as needed
else:
    openai.api_key = OPENAI_API_KEY

def get_openai_embedding(text_chunk: str, model: str = "text-embedding-3-small") -> Optional[List[float]]:
    """
    Generates an embedding for a given text chunk using OpenAI's API.
    """
    if not openai.api_key:
        print("OpenAI API key not configured. Cannot generate embedding.")
        return None
    try:
        response = openai.embeddings.create(
            input=[text_chunk], # API expects a list of strings
            model=model
        )
        embedding = response.data[0].embedding
        return embedding
    except Exception as e:
        print(f"Error generating embedding from OpenAI: {e}")
        return None

def get_llm_completion(prompt: str, system_prompt: Optional[str] = None, model: str = "gpt-4o") -> Optional[str]:
    """
    Gets a completion from the specified OpenAI LLM model.
    """
    if not openai.api_key:
        print("OpenAI API key not configured. Cannot get completion.")
        return None

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = openai.chat.completions.create(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error getting completion from OpenAI: {e}")
        return None

# Example usage (optional, for testing this module)
if __name__ == '__main__':
    if OPENAI_API_KEY:
        # Test embedding
        sample_text = "This is a test sentence for Aletheia's memory."
        embedding = get_openai_embedding(sample_text)
        if embedding:
            print(f"Sample embedding (first 5 dimensions): {embedding[:5]}")
            print(f"Embedding dimension: {len(embedding)}")
        else:
            print("Failed to get embedding.")

        # Test completion
        system_p = "You are Aletheia, a helpful AI assistant."
        user_p = "What is the capital of the United Kingdom?"
        completion = get_llm_completion(user_p, system_prompt=system_p)
        if completion:
            print(f"\nLLM Response: {completion}")
        else:
            print("Failed to get completion.")
    else:
        print("Please set your OPENAI_API_KEY in the .env file to run tests.")