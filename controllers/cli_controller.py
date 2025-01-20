from .sahibinden_controller import SahibindenScrapeController
from state_manager import StateManager
from config import PATHS
import json
import os

class CLIScrapeController(SahibindenScrapeController):
    def __init__(self, state_manager: StateManager):
        super().__init__(state_manager)
        self.continuous_file = PATHS['CONTINUOUS_DATA']

    def on_listing_processed(self, listing_data: dict):
        self._save_continuous_json(listing_data)
        self.logger.info(f"Processed listing: {listing_data['listing']['listing_id']}")

    def on_error(self, error: Exception):
        self.logger.error(f"Error during scraping: {error}")

    def on_progress(self, message: str):
        self.logger.info(message)
        super().on_progress(message)

    def on_completed(self):
        self.logger.info("Scraping completed successfully")
        super().on_completed()

    def _save_continuous_json(self, listing_data: dict):
        mode = 'a' if os.path.exists(self.continuous_file) else 'w'
        try:
            with open(self.continuous_file, mode, encoding='utf-8') as f:
                if mode == 'w':
                    f.write('[\n')
                else:
                    f.seek(0, 2)
                    f.seek(f.tell() - 2, 0)
                    f.write(',\n')
                
                json.dump(listing_data, f, ensure_ascii=False, indent=2)
                f.write('\n]')
        except Exception as e:
            self.logger.error(f"Error saving continuous data: {e}")
