from typing import Dict, List
from DrissionPage import ChromiumPage
from CloudflareBypasser import CloudflareBypasser
from models import ListingData, PropertyDetails, ContactInfo
import logging
import time
import re

class SahibindenScraper:
    def __init__(self, max_pages: int, delay: int):
        self.page = ChromiumPage()
        self.cf_bypasser = CloudflareBypasser(self.page)
        self.logger = logging.getLogger(__name__)
        self.page_idx = 1
        self.max_pages = max_pages
        self.delay = delay


    def _get_page(self, url: str):
        self.page.get(url)
        self.cf_bypasser.bypass()
        while self.page.url_available is False:
            time.sleep(1)
        time.sleep(self.delay)
        if self.page.url != url:
            self.logger.info(f"Redirected to: {self.page.url}")
            self.cf_bypasser.bypass()
            time.sleep(self.delay)
            self.logger.info(f"Waiting user to proceed, Please type 'y' to continue")
            inp = input()
            if inp == 'y':
                self._get_page(url)

    def scrape_listing_page(self, url: str) -> List[ListingData]:
        self._get_page(url)
        listings = []
        
        # First get the table
        table = self.page.ele('@id=searchResultsTable')
        self.logger.debug(f"Found table: {table is not None}")
        
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
                    date=item.ele('@class=searchResultsDateValue true').text.replace('\n', ' ').strip(),
                    location=item.ele('@class=searchResultsLocationValue true ').text.replace('\n', ' ').strip(),
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
        self._get_page(url)
        
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
        store_name = self.page.ele('@class:user-info-store-name')
        
        if store_name:
            # Company listing

            agency_name = store_name.text.strip()
            agent_name_div = self.page.ele('@class:user-info-agent')
            agent_name = self._safe_extract(agent_name_div, 'tag:h3', 'text')
            office_phone = self._get_phone_number('İş')
            mobile_phone = self._get_phone_number('Cep')


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

    def _get_phone_number(self, phone_type: str) -> str:
        """Get phone number by type"""
        try:
            phones = self.page.eles('@class:dl-group')
            for phone in phones:
                if phone_type in phone.parent().text:
                    return phone.text.strip()
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
    