import re


_PATTERNS = (
    ("desktop_action", re.compile(r"\b(open|launch|start|find files|search for files)\b", re.IGNORECASE)),
    ("productivity", re.compile(r"\b(note|task|remind|reminder|todo|to-do)\b", re.IGNORECASE)),
    ("web_search", re.compile(r"\b(search|latest|current|news|weather|today)\b", re.IGNORECASE)),
)


def classify_intent(message: str) -> str:
    for intent, pattern in _PATTERNS:
        if pattern.search(message):
            return intent
    return "general"