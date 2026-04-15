from typing import Dict, List
import requests
from bs4 import BeautifulSoup

TNAU_FEED_URL = "http://www.agritech.tnau.ac.in/expert_system/cattlebuffalo/Feeding%20management.html"


def fetch_tnau_feed_ingredients() -> List[str]:
    """Scrape publicly available TNAU feed ingredient names for local catalog seeding."""
    try:
        response = requests.get(TNAU_FEED_URL, timeout=12)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        anchor_texts = set()

        for link in soup.find_all("a"):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            if href.startswith("#") and text:
                anchor_texts.add(text)

        if anchor_texts:
            return sorted(anchor_texts)
    except requests.RequestException:
        pass

    return [
        "Maize",
        "Soybean Meal",
        "Wheat Bran",
        "Groundnut Oil Cake",
        "Rice Bran",
        "Napier Grass",
        "Bajra",
        "Sorghum",
        "Sunflower Oil Cake",
        "Broken Rice",
        "Cotton Seed Meal",
        "Molasses",
    ]


def fetch_sample_market_prices() -> Dict[str, float]:
    """Return sample market prices for common feed ingredients."""
    return {
        "Maize Grain": 18.5,
        "Soybean Meal": 36.0,
        "Wheat Bran": 12.0,
        "Groundnut Oil Cake": 30.0,
        "Rice Bran": 14.0,
        "Sunflower Oil Cake": 28.0,
    }
