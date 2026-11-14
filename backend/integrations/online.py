import os
from html.parser import HTMLParser

import httpx
from urllib.parse import urljoin, urlparse


class SearchResultParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.active_result = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get("class", "").split()
        if tag == "a" and "result__a" in classes:
            result_url = urljoin("https://duckduckgo.com", attributes.get("href", ""))
            if urlparse(result_url).scheme in {"http", "https"}:
                self.active_result = {"title": "", "url": result_url}

    def handle_data(self, data):
        if self.active_result is not None:
            self.active_result["title"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.active_result is not None:
            self.active_result["title"] = self.active_result["title"].strip()
            if self.active_result["title"] and self.active_result["url"]:
                self.results.append(self.active_result)
            self.active_result = None


async def search_web(query: str, limit: int = 8):
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        response = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "JARVIS local assistant/1.0"},
        )
        response.raise_for_status()

    parser = SearchResultParser()
    parser.feed(response.text)
    return parser.results[:limit]


async def lookup_weather(location: str):
    async with httpx.AsyncClient(timeout=12.0) as client:
        geocoding = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1, "language": "en", "format": "json"},
        )
        geocoding.raise_for_status()
        candidates = geocoding.json().get("results", [])
        if not candidates:
            raise ValueError("No matching location was found.")
        place = candidates[0]
        forecast = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
        )
        forecast.raise_for_status()
        return {"location": place, "current": forecast.json().get("current", {})}


async def get_public_github_repository(owner: str, repository: str):
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(
            f"https://api.github.com/repos/{owner}/{repository}",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
    return {
        "name": data.get("full_name"),
        "description": data.get("description"),
        "url": data.get("html_url"),
        "language": data.get("language"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "updated_at": data.get("updated_at"),
    }