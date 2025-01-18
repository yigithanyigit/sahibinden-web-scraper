import logging
from scraper import SahibindenScraper
from messager import SahibindenMessager
import json
from dataclasses import asdict
import argparse

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    args = argparse.ArgumentParser()
    args.add_argument("--url", help="URL to scrape")
    args.add_argument("--max_pages", type=int, help="Maximum number of pages to scrape", default=1)
    args.add_argument("--delay", type=int, help="Delay between requests in seconds", default=1.5)
    args = args.parse_args()

    setup_logging()
    logger = logging.getLogger(__name__)
    
    url = args.url
    scraper = SahibindenScraper(args.max_pages, args.delay)
    messager = SahibindenMessager("Merhaba, ilanınız hala satılık mı?")
    
    try:
        """
        listings = scraper.scrape_listing_page(url)
        url = "https://www.sahibinden.com/ilan/emlak-konut-satilik-arslan-dan-gaziemir-irmak-mah-onu-acik-3-plus1-satilik-daire-1221529389/detay"
        messager.send_message(url)
        exit()
        """

        while url != '':
            logger.info(f"Starting to scrape URL: {url}")
            listings = scraper.scrape_listing_page(url)
            
            logger.info(f"Found {len(listings)} listings to process")
            
            # Scrape details for each listing
            full_data = []
            for listing in listings:
                try:
                    property_details, contact_info = scraper.scrape_detail_page(listing.detail_url)
                    full_data.append({
                        "listing": asdict(listing),
                        "property_details": asdict(property_details),
                        "contact_info": asdict(contact_info)
                    })
                except Exception as e:
                    logger.error(f"Error processing detail page {listing.detail_url}: {e}")
                    continue
                    
            url = scraper.next_page(url)

        # Save results
        with open('scraping_results.json', 'w', encoding='utf-8') as f:
            json.dump(full_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Successfully scraped {len(full_data)} listings")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")

if __name__ == "__main__":
    main()
