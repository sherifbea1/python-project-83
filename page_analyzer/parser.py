import requests
from bs4 import BeautifulSoup


def parse_page(html_text: str) -> dict:
    soup = BeautifulSoup(html_text, "html.parser")
    title_tag = soup.find("title")
    h1_tag = soup.find("h1")
    desc_tag = soup.find(
        "meta", attrs={"name": "description"}
    )
    title = title_tag.text.strip() if title_tag else None
    h1 = h1_tag.text.strip() if h1_tag else None
    description = (
        desc_tag.get("content").strip()
        if desc_tag and desc_tag.get("content")
        else None
    )
    return {"title": title, "h1": h1, "description": description}


def check_page(url: str):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        parsed = parse_page(response.text)
        return {
            "status_code": response.status_code,
            "title": parsed["title"],
            "h1": parsed["h1"],
            "description": parsed["description"],
        }
    except requests.RequestException:
        return None