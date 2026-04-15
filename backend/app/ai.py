import json
from typing import Optional
import requests
from .config import settings


def _call_openai(prompt: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a livestock nutrition assistant. Keep answers short, practical, and farmer-friendly."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 250,
        "temperature": 0.7,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def _call_ollama(prompt: str) -> str:
    url = f"{settings.ollama_url.rstrip('/')}/v1/completions"
    payload = {
        "model": "llama2",
        "prompt": prompt,
        "max_tokens": 250,
        "temperature": 0.7,
    }
    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()
    data = response.json()
    return data.get("choices", [{}])[0].get("text", "").strip() or data.get("completion", "").strip()


def generate_ai_explanation(
    prompt: str,
) -> str:
    if settings.openai_api_key:
        return _call_openai(prompt)

    if settings.ollama_url:
        return _call_ollama(prompt)

    return "AI support is not configured. Set OPENAI_API_KEY or OLLAMA_URL in the environment."


def build_nutrition_prompt(request_data: dict, target_data: dict, recommendation: dict) -> str:
    return (
        "Review the following livestock ration recommendation and write a farmer-friendly explanation. "
        "Use simple language, mention the species, purpose, key feed ingredients, and why this blend is safer and more cost-efficient.\n\n"
        f"Input: {json.dumps(request_data, indent=2)}\n"
        f"Target: {json.dumps(target_data, indent=2)}\n"
        f"Recommendation: {json.dumps(recommendation, indent=2)}\n"
    )
