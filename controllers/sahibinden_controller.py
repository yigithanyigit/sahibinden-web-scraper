from .base_controller import BaseScrapeController
from scraper import SahibindenScraper
from dataclasses import asdict
from typing import Tuple, Any

class SahibindenScrapeController(BaseScrapeController):
    def initialize_scraper(self, **kwargs):
        self.scraper = SahibindenScraper(
            max_pages=kwargs.get('max_pages', 1),
            delay=kwargs.get('delay', 1.5),
            headless=kwargs.get('headless', False)
        )

    def scrape_page(self, url: str):
        return self.scraper.scrape_listing_page(url)

    def scrape_detail(self, url: str) -> Tuple[Any, Any]:
        return self.scraper.scrape_detail_page(url)

    def get_next_page(self, url: str) -> str:
        return self.scraper.next_page(url)

    def create_listing_data(self, listing, details) -> dict:
        property_details, contact_info = details
        return {
            "data_source": "Sahibinden",
            "listing": asdict(listing),
            "property_details": asdict(property_details),
            "contact_info": asdict(contact_info)
        }