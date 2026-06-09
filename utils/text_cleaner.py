import re
from bs4 import BeautifulSoup


def clean_text(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "lxml")
    text = soup.get_text(separator=" ")
    text = re.sub(r'[^\x20-\x7E\n]', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n+', ' ', text)
    text = text.strip()
    return text


def truncate_to_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])
