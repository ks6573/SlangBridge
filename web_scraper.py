# web_scraper.py
import requests
from bs4 import BeautifulSoup

def scrape_urban_dictionary(term):
    try:
        url = f"https://www.urbandictionary.com/define.php?term={term}"
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        meaning_div = soup.find("div", class_="meaning")
        example_div = soup.find("div", class_="example")

        if not meaning_div:
            return None

        meaning = meaning_div.get_text(strip=True)
        example = example_div.get_text(strip=True) if example_div else ""

        return f"{meaning}\n\nExample: {example}" if example else meaning

    except Exception as e:
        print("Web scraping error:", e)
        return None