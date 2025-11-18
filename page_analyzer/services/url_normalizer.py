from urllib.parse import urlparse


def normalize_url(input_url: str) -> str:
    parsed = urlparse(input_url)
    if not parsed.scheme:
        parsed = urlparse(f"http://{input_url}")
    return f"{parsed.scheme}://{parsed.netloc}"
