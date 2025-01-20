from abc import ABC, abstractmethod
import logging
import time
from state_manager import StateManager

class BaseScrapeController(ABC):
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)
        self.scraper = None
        self.paused = False
        self.should_stop = False
        
    @abstractmethod
    def initialize_scraper(self, **kwargs):
        """Initialize the specific scraper with arguments"""
        pass

    @abstractmethod
    def scrape_page(self, url: str):
        """Scrape a single page and return listings"""
        pass

    @abstractmethod
    def scrape_detail(self, url: str):
        """Scrape details of a single listing"""
        pass

    @abstractmethod
    def get_next_page(self, url: str) -> str:
        """Get next page URL or empty string if no more pages"""
        pass

    @abstractmethod
    def create_listing_data(self, listing, details) -> dict:
        """Create standardized listing data dictionary"""
        pass

    @abstractmethod
    def on_listing_processed(self, listing_data: dict):
        """Handle processed listing data"""
        pass

    @abstractmethod
    def on_error(self, error: Exception):
        """Handle errors during scraping"""
        pass

    @abstractmethod
    def on_progress(self, message: str):
        """Handle progress updates"""
        pass

    @abstractmethod
    def on_completed(self):
        """Handle completion of scraping"""
        pass

    def start_scraping(self, url: str, scraper_args: dict):
        """Main scraping logic"""
        try:
            self.initialize_scraper(**scraper_args)
            current_page, last_id, processed_urls = self.state_manager.get_resume_info()
            
            while url and current_page <= scraper_args['max_pages'] and not self.should_stop:
                # Handle pause
                while self.paused and not self.should_stop:
                    time.sleep(0.1)
                
                if self.should_stop:
                    self.on_progress("Scraping stopped")
                    return

                self.on_progress(f"Starting to scrape page {current_page}")
                
                try:
                    listings = self.scrape_page(url)
                    
                    if last_id:
                        listings = [l for l in listings if l.listing_id > last_id]
                        last_id = None
                    
                    for listing in listings:
                        # Check stop/pause for each listing
                        while self.paused and not self.should_stop:
                            time.sleep(0.1)
                            
                        if self.should_stop:
                            self.on_progress("Scraping stopped")
                            return

                        if listing.detail_url in processed_urls:
                            self.on_progress(f"Skipping already processed: {listing.listing_id}")
                            continue

                        try:
                            details = self.scrape_detail(listing.detail_url)
                            listing_data = self.create_listing_data(listing, details)
                            
                            self.state_manager.update_progress(
                                listing.listing_id, 
                                listing.detail_url
                            )
                            self.on_listing_processed(listing_data)
                            
                        except Exception as e:
                            self.on_error(e)
                            continue
                            
                    current_page += 1
                    self.state_manager.update_page(current_page)
                    url = self.get_next_page(url)
                    
                except Exception as e:
                    self.on_error(e)
                    break

            self.state_manager.mark_completed()
            self.on_completed()
            
        except Exception as e:
            self.on_error(e)
        finally:
            self.state_manager.save_state()

    def pause(self):
        """Pause scraping"""
        self.paused = True

    def resume(self):
        """Resume scraping"""
        self.paused = False

    def stop(self):
        """Stop scraping"""
        self.should_stop = True

    def exit(self):
        """Exit scraper"""
        self.stop()
        self.on_completed()
