from .sahibinden_controller import SahibindenScrapeController
from PyQt5.QtCore import QObject, QThread, pyqtSignal

# First create a signal emitter class
class UISignals(QObject):
    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    listing_processed = pyqtSignal(dict)
    completed = pyqtSignal()
    page_started = pyqtSignal(int)  # Add signal for page progress

class UIScrapeController(SahibindenScrapeController):
    def __init__(self, state_manager):
        super().__init__(state_manager)
        # Create signals object
        self.signals = UISignals()
        self.paused = False
        self.should_stop = False

    def initialize_scraper(self, **kwargs):
        """Initialize with error handling"""
        try:
            super().initialize_scraper(**kwargs)
            # Test connection
            if not self.scraper or not hasattr(self.scraper, 'page'):
                raise Exception("Failed to initialize browser")
        except Exception as e:
            self.on_error(e)
            self.stop()
            return False
        return True

    def on_listing_processed(self, listing_data: dict):
        self.signals.listing_processed.emit(listing_data)

    def on_error(self, error: Exception):
        self.signals.error.emit(str(error))
        self.logger.error(f"Error during scraping: {error}")

    def on_progress(self, message: str):
        """Handle progress updates without recursive calls"""
        # Don't call stop() from here anymore
        self.signals.progress.emit(message)
        if "Scraping page:" in message:
            try:
                page = int(message.split("page:")[1].strip())
                self.signals.page_started.emit(page)
            except:
                pass
        self.logger.info(message)

    def on_completed(self):
        self.signals.completed.emit()
        self.logger.info("Scraping completed successfully")

    def pause(self):
        self.paused = True
        self.on_progress("Scraping paused")

    def resume(self):
        self.paused = False
        self.on_progress("Scraping resumed")

    def stop(self):
        """Stop scraping and cleanup without recursive calls"""
        self.should_stop = True
        if hasattr(self, 'scraper') and self.scraper:
            try:
                self.scraper.close()
            except:
                pass
            finally:
                self.scraper = None
        # Instead of calling on_progress, emit signal directly
        self.signals.progress.emit("Scraping stopped")
        self.logger.info("Scraping stopped")

    def start_scraping(self, url: str, scraper_args: dict):
        self.should_stop = False  # Reset stop flag
        self.paused = False  # Reset pause flag
        if not self.initialize_scraper(**scraper_args):
            return
        super().start_scraping(url, scraper_args)
