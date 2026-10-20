UNTITLED_WORDS = 6


def display_title(title: str | None, text: str) -> str:
    """The title, or the first words of the text when there is none."""
    if title:
        return title
    words = text.split()
    if len(words) <= UNTITLED_WORDS:
        return " ".join(words)
    return " ".join(words[:UNTITLED_WORDS]) + "…"
