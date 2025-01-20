import json
import pickle
import os
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime

@dataclass
class ScraperState:
    url: str
    current_page: int
    last_processed_id: Optional[str]
    processed_urls: List[str]
    total_processed: int
    start_time: datetime
    last_update: datetime
    is_completed: bool
    # Add scraper arguments
    max_pages: int = 1
    delay: float = 1.5
    headless: bool = False

class StateManager:
    def __init__(self, state_file="scraper_state.json"):
        self.state_file = state_file
        self.state = None
        self.load_state()

    def initialize_state(self, url: str, **kwargs):
        """Initialize state with optional scraper arguments"""
        self.state = ScraperState(
            url=url,
            current_page=1,
            last_processed_id=None,
            processed_urls=[],
            total_processed=0,
            start_time=datetime.now(),
            last_update=datetime.now(),
            is_completed=False,
            # Add scraper arguments with defaults
            max_pages=kwargs.get('max_pages', 1),
            delay=kwargs.get('delay', 1.5),
            headless=kwargs.get('headless', False)
        )
        self.save_state()

    def load_state(self) -> Optional[ScraperState]:
        """Load state from file if exists"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data['start_time'] = datetime.fromisoformat(data['start_time'])
                    data['last_update'] = datetime.fromisoformat(data['last_update'])
                    self.state = ScraperState(**data)
                    return self.state
        except Exception as e:
            print(f"Error loading state: {e}")
        return None

    def save_state(self):
        """Save current state to file"""
        if self.state:
            self.state.last_update = datetime.now()
            try:
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    state_dict = asdict(self.state)
                    state_dict['start_time'] = state_dict['start_time'].isoformat()
                    state_dict['last_update'] = state_dict['last_update'].isoformat()
                    json.dump(state_dict, f, indent=2)
            except Exception as e:
                print(f"Error saving state: {e}")

    def update_progress(self, listing_id: str, listing_url: str):
        """Update state with processed listing"""
        if self.state:
            self.state.last_processed_id = listing_id
            self.state.processed_urls.append(listing_url)
            self.state.total_processed += 1
            self.save_state()

    def update_page(self, page_number: int):
        """Update current page number"""
        if self.state:
            self.state.current_page = page_number
            self.save_state()

    def mark_completed(self):
        """Mark scraping as completed"""
        if self.state:
            self.state.is_completed = True
            self.save_state()

    def should_process_url(self, url: str) -> bool:
        """Check if URL should be processed or was already done"""
        return self.state and url not in self.state.processed_urls

    def get_resume_info(self) -> tuple[int, str, List[str]]:
        """Get info needed to resume scraping"""
        if self.state:
            return (
                self.state.current_page,
                self.state.last_processed_id,
                self.state.processed_urls
            )
        return 1, None, []

    def get_scraper_args(self) -> dict:
        """Get scraper arguments from state"""
        if not self.state:
            return {}
        return {
            'max_pages': self.state.max_pages,
            'delay': self.state.delay,
            'headless': self.state.headless
        }
