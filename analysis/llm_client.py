import os
from utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_MESSAGE = (
    "You are an expert media analyst who identifies bias, framing, and perspective differences "
    "in news coverage. Always respond in valid JSON format only. Do not add any explanation outside the JSON."
)


class LLMUnavailableError(Exception):
    pass


def _get_api_key(name: str) -> str:
    """Read a key from the environment, then from Streamlit Secrets."""
    key = os.getenv(name, "").strip()
    if key:
        return key

    try:
        import streamlit as st

        return str(st.secrets.get(name, "")).strip()
    except (ImportError, KeyError, FileNotFoundError):
        return ""


def call_llm(prompt: str, system_message: str = None) -> str:
    if system_message is None:
        system_message = SYSTEM_MESSAGE

    failures = []
    groq_key = _get_api_key("GROQ_API_KEY")
    if groq_key and groq_key != "your_groq_api_key_here":
        try:
            from langchain_groq import ChatGroq
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = ChatGroq(
                api_key=groq_key,
                model_name="llama-3.3-70b-versatile",
                temperature=0.1,
                max_tokens=2000,
            )
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=prompt),
            ]
            response = llm.invoke(messages)
            logger.info("LLM response received from Groq.")
            return response.content
        except Exception as e:
            failures.append(f"Groq: {e}")
            logger.warning(f"Groq API failed: {e}. Falling back to Gemini.")
    else:
        failures.append("Groq: GROQ_API_KEY is missing or still a placeholder")

    gemini_key = _get_api_key("GEMINI_API_KEY")
    if gemini_key and gemini_key != "your_gemini_api_key_here":
        try:
            import google.generativeai as genai

            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=system_message,
            )
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2000,
                ),
            )
            logger.info("LLM response received from Gemini.")
            return response.text
        except Exception as e:
            failures.append(f"Gemini: {e}")
            logger.warning(f"Gemini API failed: {e}")
    else:
        failures.append("Gemini: GEMINI_API_KEY is missing or still a placeholder")

    raise LLMUnavailableError(
        "No LLM provider succeeded. " + " | ".join(failures)
    )
