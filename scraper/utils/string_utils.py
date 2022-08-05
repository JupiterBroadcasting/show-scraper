def capitalize_text(text: str) -> str:
    """Capitalize all the words in a string"""

    return " ".join([word.capitalize() for word in text.split(" ")])
