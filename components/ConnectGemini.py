# components/ConnectGemini.py
from dotenv import load_dotenv
import os

from google import genai
from google.genai import types

load_dotenv()

_client = None

def _get_client():
    global _client
    if _client is None:
        # GEMINI_API_KEY or GOOGLE_API_KEY のどちらでもOKにしておく
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            _client = genai.Client(api_key=api_key)
        else:
            # 環境によっては env を自動参照できるため一応残す
            _client = genai.Client()
    return _client


def requestGemini(systemContent: str, userContent: str, model: str = None, temperature: float = 0.0) -> str:
    """
    systemContent: システム指示（Geminiでは system_instruction に入れる）
    userContent  : ユーザー入力
    """
    client = _get_client()

    # モデルは env で上書き可（例: GEMINI_MODEL=gemini-3-flash-preview）
    model = model or os.getenv("GEMINI_MODEL") or "gemini-3-flash-preview"

    resp = client.models.generate_content(
        model=model,
        contents=userContent,
        config=types.GenerateContentConfig(
            system_instruction=systemContent,
            temperature=temperature,
        ),
    )
    return resp.text or ""
