def safe_next(url: str | None, default: str = "/passages") -> str:
    if url and url.startswith("/") and not url.startswith("//"):
        return url
    return default
