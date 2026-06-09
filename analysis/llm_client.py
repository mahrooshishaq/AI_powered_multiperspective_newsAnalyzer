import os
from utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_MESSAGE = (
    "You are an expert media analyst who identifies bias, framing, and perspective differences "
    "in news coverage. Always respond in valid JSON format only. Do not add any explanation outside the JSON."
)


class LLMUnavailableError(Exception):
    pass


def call_llm(prompt: str, system_message: str = None) -> str:
    if system_message is None:
        system_message = SYSTEM_MESSAGE

    groq_key = os.getenv("GROQ_API_KEY", "")
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
            logger.warning(f"Groq API failed: {e}. Falling back to Gemini.")

    gemini_key = os.getenv("GEMINI_API_KEY", "")
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
            logger.warning(f"Gemini API failed: {e}")

    raise LLMUnavailableError(
        "Both Groq and Gemini APIs are unavailable. "
        "Check your API keys and network connection."
    )
