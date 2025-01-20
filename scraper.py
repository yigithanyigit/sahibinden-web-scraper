from typing import Dict, List
from DrissionPage import ChromiumPage, ChromiumOptions
from CloudflareBypasser import CloudflareBypasser
from models import ListingData, PropertyDetails, ContactInfo
from request_manager import RequestProps
import logging
import time
import re
import random
import os
from requests.exceptions import ConnectionError

MAX_RETRIES = 3

class SahibindenScraper:
    def __init__(self, max_pages: int, delay: int, headless: bool = False):
        self.options = ChromiumOptions()
        self.headless = headless
        self.logger = logging.getLogger(__name__)
        self.page_idx = 1
        self.max_pages = max_pages
        self.delay = delay
        self.retry_count = 0
        self.is_stopped = False
        self.temp_profile_dir = None  # Initialize here
        
        # First get Chrome's actual profile path
        temp_browser = ChromiumPage()
        chrome_profile_path = None
        
        try:
            # Get chrome://version data
            temp_browser.get('chrome://version')
            profile_element = temp_browser.ele('#profile_path')
            if profile_element:
                chrome_profile_path = os.path.dirname(profile_element.text.strip())
                self.logger.info(f"Found Chrome profile path: {chrome_profile_path}")
            
            if not chrome_profile_path:
                # Try to get from command line as fallback
                cmd_line = temp_browser.ele('#command_line')
                if cmd_line:
                    cmd_text = cmd_line.text
                    user_data_match = re.search(r'--user-data-dir=(.*?)(?:\s|$)', cmd_text)
                    if user_data_match:
                        chrome_profile_path = user_data_match.group(1)
        except Exception as e:
            self.logger.warning(f"Could not get Chrome profile path: {e}")
        finally:
            temp_browser.quit()

        # Create new profile directory based on original Chrome profile
        import tempfile
        import uuid
        import shutil
        
        profile_name = f"scraper_profile_{uuid.uuid4().hex[:8]}"
        self.temp_profile_dir = os.path.join(tempfile.gettempdir(), profile_name)
        
        # Copy default profile if we found Chrome's profile path
        if chrome_profile_path and os.path.exists(chrome_profile_path):
            try:
                default_profile = os.path.join(chrome_profile_path, 'Default')
                if os.path.exists(default_profile):
                    self.logger.info("Copying default Chrome profile...")
                    shutil.copytree(
                        default_profile,
                        os.path.join(self.temp_profile_dir, 'Default'),
                        ignore=shutil.ignore_patterns(
                            'Cache*', 'Service Worker', '*.log', '*.db',
                            'Network*', 'Media Cache', '*Storage*'
                        )
                    )
            except Exception as e:
                self.logger.warning(f"Failed to copy Chrome profile: {e}")
        
        # Set Chrome options for the temporary profile
        self.options.set_argument(f'--user-data-dir={self.temp_profile_dir}')
        # self.options.set_argument('--profile-directory=Default')
        self.options.set_argument('--no-first-run')
        self.options.set_argument('--no-default-browser-check')
        self.options.set_argument('--disable-features=TranslateUI')
        self.options.set_argument('--disable-features=ChromeWhatsNewUI')
        self.options.set_argument('--password-store=basic')
        self.options.set_argument('--disable-sync')
        self.options.set_argument('--disable-extensions')
        
        if self.headless:
            print("Running in headless mode")
            self.__set_headless(headless)
            
        self.page = ChromiumPage(self.options)
        self.cf_bypasser = CloudflareBypasser(self.page)
        self.logger = logging.getLogger(__name__)
        self.page_idx = 1
        self.max_pages = max_pages
        self.delay = delay
        self.retry_count = 0

        self.is_stopped = False
        # Store temp directory for cleanup

    def __set_headless(self, headless: bool):
        # Basic settings
        # Must set these before setting headless mode
        self.options.set_argument('--blink-settings=imagesEnabled', 'false')
        
        self.options.set_argument('--disable-infobars')
        self.options.set_argument('--disable-extensions')
        self.options.set_argument('--disable-gpu')
        self.options.set_argument('--no-sandbox')
        
        self.options.headless(headless)

    def __page_loader(self, url: str):
        if self.is_stopped:
            return

        if self.headless:
            self.page.set.window.size(800, 600)
            # Use RequestProps for user agent and headers
            self.page.set.user_agent(ua=RequestProps.get_random_user_agent())
            self.page.set.headers(RequestProps.get_random_headers())
            return self._get_page(url)
        else:
            return self._get_page(url)


    def _get_page(self, url: str):
        """Get page with retry logic"""
        if self.is_stopped:
            return False

        for attempt in range(MAX_RETRIES):
            try:
                self.page.get(url)
                retry = 0
                while self.page.url_available is False and retry < 10:
                    time.sleep(1)
                    retry += 1
                
                if not self.page.url_available:
                    raise ConnectionError("Page not available after timeout")

                self.cf_bypasser.bypass()
                
                if self.page.url != url:
                    self.logger.info(f"Redirected to: {self.page.url}")
                    self.cf_bypasser.bypass()
                    time.sleep(self.delay)
                    if not self.headless:  # Only ask for input in non-headless mode
                        self.logger.info("Waiting user to proceed, Please type 'y' to continue")
                        inp = input()
                        if inp == 'y':
                            return self._get_page(url)
                return True

            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1}/{MAX_RETRIES} failed: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(self.delay * 2)  # Increase delay between retries
                    try:
                        # Try to refresh the page connection
                        self.page.refresh()
                    except:
                        pass
                else:
                    self.logger.error("Max retries reached, giving up")
                    return False
        return False

    def scrape_listing_page(self, url: str) -> List[ListingData]:
        if self.is_stopped:
            return []
            
        if not self.__page_loader(url):
            self.logger.error("Failed to load page")
            return []
            
        listings = []
        
        # First get the table
        table = self.page.ele('@id=searchResultsTable')
        if not table:
            self.logger.error("Table not found")
            return listings
            
        # Get tbody then rows using correct DrissionPage syntax
        tbody = table.ele('@tag()=tbody')
        if not tbody:
            self.logger.error("tbody not found")
            return listings
        
        self.logger.debug(tbody)

        # Get all tr elements with data-id attribute
        all_items = tbody.eles('@tag()=tr')
        self.logger.debug(f"Found {len(all_items)} total items")
        
        for item in all_items:
            try:
                self.logger.debug(f"Processing item: {item}")

                # Skip ads and promos
                class_attr = item.attr('class')
                if 'nativeAd' in class_attr or 'searchResultsPromoToplist' in class_attr:
                    continue
                
                # Find elements using proper DrissionPage syntax
                title_element = item.ele('@@tag()=a@@class= classifiedTitle')
                self.logger.debug(f"Found title element: {title_element}")
                if not title_element:
                    continue

                listing = ListingData(
                    listing_id=item.attr('data-id'),
                    title=title_element.text.strip(),
                    size_m2=float(item.eles('@class=searchResultsAttributeValue')[0].text.replace('m²', '').strip()),
                    room_count=item.eles('@class=searchResultsAttributeValue')[1].text.strip(),
                    price=item.ele('@class=searchResultsPriceValue').text.strip(),
                    date=item.ele('@class:searchResultsDateValue').text.replace('\n', ' ').strip(),
                    location=item.ele('@class:searchResultsLocationValue').text.replace('\n', ' ').strip(),
                    image_url=item.ele('@tag()=img').attr('src'),
                    #detail_url='https://www.sahibinden.com' + title_element.attr('href')
                    detail_url=title_element.attr('href')
                )
                listings.append(listing)
                self.logger.debug(f"Successfully scraped listing: {listing.listing_id}")
            except Exception as e:
                self.logger.error(f"Error scraping listing: {e}", exc_info=True)
                continue
        
        return listings

    def _safe_extract(self, item, selector, extract_type, index=None, attr_name=None):
        """Safely extract data from elements"""
        try:
            if index is not None:
                element = item.ele(selector, index=index, raise_err=False)
            else:
                element = item.ele(selector, raise_err=False)
                
            if element:
                if extract_type == 'text':
                    return element.text.strip()
                elif extract_type == 'attr':
                    return element.attr(attr_name, '')
            return ''
        except Exception as e:
            self.logger.error(f"Error extracting {selector}: {e}")
            return ''

    def scrape_detail_page(self, url: str) -> tuple[PropertyDetails, ContactInfo]:
        if self.is_stopped:
            return None, None
            
        if not self.__page_loader(url):
            self.logger.error("Failed to load detail page")
            return None, None
            
        # Extract property details
        details = {}
        detail_ul = self.page.ele('@class:classifiedInfoList')
        detail_items = detail_ul.eles('@tag()=li')  # Get all li elements
        self.logger.debug(f"Found {len(detail_items)} detail items")
        for item in detail_items:
            strong = item.ele('@tag()=strong')
            span = item.ele('@tag()=span')
            if strong and span:
                label = strong.text.strip(':')
                value = span.text
                details[label] = value

        property_details = PropertyDetails(
            gross_area=float(details.get('m² (Brüt)', '0').replace('m²', '').strip()),
            net_area=float(details.get('m² (Net)', '0').replace('m²', '').strip()),
            room_count=details.get('Oda Sayısı', '').strip(),
            building_age=details.get('Bina Yaşı', '').strip(),
            floor=details.get('Bulunduğu Kat', '').strip(),
            total_floors=int(details.get('Kat Sayısı', '0').strip()),
            heating=details.get('Isıtma', '').strip(),
            bathroom_count=int(details.get('Banyo Sayısı', '0').strip()),
            balcony='Var' in details.get('Balkon', '').strip(),
            elevator='Var' in details.get('Asansör', '').strip(),
            parking=details.get('Otopark', '').strip(),
            furnished='Var' in details.get('Eşyalı', '').strip(),
            usage_status=details.get('Kullanım Durumu', '').strip(),
            in_complex='Var' in details.get('Site İçerisinde', '').strip(),
            maintenance_fee=details.get('Aidat', '').strip(),
            credit_eligible='Var' in details.get('Krediye Uygun', '').strip(),
            deed_status=details.get('Tapu Durumu', '').strip(),
            listed_by=details.get('Kimden', '').strip(),
            exchangeable='Var' in details.get('Takas', '').strip(),
            description=self._safe_extract(self.page, '@id:classifiedDescription', 'inner_html').strip()
        )

        self.logger.debug(f"Extracted property details: {property_details}")

        # Extract contact info with new logic for both company and individual sellers
        contact_info = self._extract_contact_info()

        self.logger.debug(f"Extracted contact info: {contact_info}")

        return property_details, contact_info

    def _extract_contact_info(self) -> ContactInfo:
        """Extract contact info handling both company and individual sellers"""
        
        # Check if it's a company listing (has store info)

        store_info = self.page.ele('@class=classifiedOtherBoxes ').ele('@class=user-info-module')
        
        if store_info:
            # Company listing

            store_name = self.page.ele('@class=user-info-store-name')
            print(store_name)
            agency_name = store_name.text.strip()
            print(agency_name)
            agent_name_div = self.page.ele('@class=user-info-agent')
            print(agent_name_div)
            agent_name = self._safe_extract(agent_name_div, 'tag:h3', 'text')
            print(agent_name)
            office_phone = self._get_phone_number("İş", store_info)
            print(office_phone)
            mobile_phone = self._get_phone_number("Cep", store_info)
            print(mobile_phone)


            return ContactInfo(
                agency_name=agency_name,
                agent_name=agent_name,
                office_phone=office_phone,
                mobile_phone=mobile_phone
            )
        else:
            # Individual listing

            agent_name_inner_html = self.page.ele("@class:sticky-header-store-information-text")
            agent_name = agent_name_inner_html.inner_html if agent_name_inner_html else ''
            
            # Updated regex pattern
            css_class = re.search(r'<span class="(css[a-f0-9\-]+)"', agent_name)
            if css_class:
                class_name = css_class.group(1)
                content_regex = f'<style>\.{class_name}:before {{content: \'([^\']+)\';}}</style>'
                match = re.search(content_regex, agent_name)
                agent_name = match.group(1) if match else ''
            else:
                agent_name = ''
            
            self.logger.debug(f"Extracted agent name: {agent_name}")

            return ContactInfo(
                agency_name='',
                agent_name=agent_name,  # Use extracted name
                office_phone='',
                mobile_phone=self._get_individual_phone()
            )

    def _get_phone_number(self, phone_type: str, parent=None) -> str:
        """Get phone number by type"""
        try:
            phones = parent.eles('@class:dl-group') if parent else self.page.eles('@class:dl-group')
            for phone_field in phones:
                phone_name = phone_field.ele(f'tag:dt@@text()={phone_type}')
                if phone_name:
                    return phone_field.ele(f'tag:dd').text.strip()
            return ''
        except Exception as e:
            self.logger.error(f"Error getting {phone_type} phone: {e}")
            return ''

    def _get_individual_phone(self) -> str:
        """Get phone number for individual sellers"""
        try:
            phone_header_span = self.page.ele('tag:span@@class=pretty-phone-part show-part')
            self.logger.debug(f"Found phone header span: {phone_header_span}")
            if phone_header_span:
                phone_span = phone_header_span.ele('tag:span')
                self.logger.debug(f"Found phone span: {phone_span}")
                if phone_span:
                    # Get the data-content attribute which contains the full phone number
                    return phone_span.attr('data-content')
            return ''
        except Exception as e:
            self.logger.error(f"Error getting individual phone: {e}")
            return ''
        
    def _safe_extract(self, item, selector, extract_type, attr_name=None):
        """Safely extract data from elements"""
        try:
            element = item.ele(selector)
                
            if element:
                if extract_type == 'text':
                    return element.text.strip()
                elif extract_type == 'attr':
                    return element.attr(attr_name)
                elif extract_type == 'inner_html':
                    return element.inner_html
                elif extract_type == 'outer_html':
                    return element.outer_html
            return ''
        except Exception as e:
            self.logger.error(f"Error extracting {selector}: {e}")
            return ''

    def next_page(self, url=None) -> str:

        if self.page_idx >= self.max_pages:
            return ''

        if url:
            self._get_page(url)

        page_nav = self.page.ele('tag:ul@@class:pageNaviButtons')
        if not page_nav:
            self.logger.info("No page nav found")
            return ''

        self.logger.debug(f"Found page nav: {page_nav}")

        next_button = page_nav.ele("tag:a@@class=prevNextBut")
        if next_button:
            link = next_button.attr('href')
            self.page_idx += 1
            return link
        return ''
    

    def close(self):
        """Safely close browser and cleanup temp profile"""
        self.is_stopped = True
        try:
            if hasattr(self, 'page') and self.page:
                try:
                    self.page.refresh()
                except:
                    pass
                time.sleep(1)
                self.page.quit()
                
            # Cleanup temporary profile directory
            if hasattr(self, 'temp_profile_dir') and os.path.exists(self.temp_profile_dir):
                import shutil
                try:
                    shutil.rmtree(self.temp_profile_dir)
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup temp profile: {e}")
        except:
            pass
        finally:
            self.page = None
        self.logger.info("Browser closed and profile cleaned up")