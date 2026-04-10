"""
eyes.py — Screen capture and vision analysis module

Captures the screen using mss (lightweight, fast) and sends it to a
vision-capable AI model for analysis.

Requires: pip install mss
"""

import base64
import os
import sys
from datetime import datetime

import config

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
VISION_PATH  = os.path.join(BASE_DIR, "last_vision.png")


def capture_screen() -> str:
    """
    Capture the primary monitor using mss and save to disk.
    Returns the image as a base64-encoded string.
    """
    try:
        from mss import mss
    except ImportError:
        print("❌ [Vision] mss not installed. Run: pip install mss")
        return ""

    try:
        with mss() as sct:
            sct.shot(mon=1, output=VISION_PATH)

        with open(VISION_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"❌ [Vision] Screen capture failed: {e}", file=sys.stderr)
        return ""


async def analisar_tela_groq(question: str) -> str:
    """
    Capture the screen and ask a vision AI model to describe it.
    Compatible with Groq (llama-vision), OpenRouter and OpenAI.
    """
    img_b64 = capture_screen()
    if not img_b64:
        return "Screen capture unavailable."

    system_prompt = (
        "You are the vision module of an AI assistant system. "
        "Your only function is to describe what is on the user's screen "
        "directly, objectively and in detail. "
        "Do NOT add greetings, do NOT try to converse, do NOT use formatting tags. "
        "Just return the description."
    )

    now         = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_prompt = f"Instruction: {question} (Timestamp: {now})"

    try:
        client = None
        model  = ""
        # ── MODEL ROUTING ─────────────────────────────────────────────────
        if config.CURRENT_MODE == "groq" and config.client_groq:
            client = config.client_groq
            model  = config.config_data.get("modelo_visao",     "meta-llama/llama-4-scout-17b-16e-instruct")
        elif config.CURRENT_MODE == "openrouter" and config.client_openrouter:
            client = config.client_openrouter
            model  = config.config_data.get("modelo_visao",     "google/gemini-2.0-flash-001")
        elif config.client_openai:
            client = config.client_openai
            model  = config.config_data.get("modelo_visao",     "gpt-4o-mini")

        if not client:
            raise RuntimeError(
                "No AI client initialized (Groq / OpenRouter / OpenAI). "
                "Add your API keys in the dashboard."
            )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": [
                    {"type": "text",      "text": user_prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{img_b64}"
                    }}
                ]}
            ]
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"❌ [Vision] Analysis failed: {e}", file=sys.stderr)
        return f"Vision error: {e}"
