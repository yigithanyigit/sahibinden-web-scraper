import time
from DrissionPage import ChromiumPage
from DrissionPage.common import wait_until
from CloudflareBypasser import CloudflareBypasser
import logging

class SahibindenMessager:
    def __init__(self, message, delay=1.5):
        self.page = ChromiumPage()
        self.message = message
        self.delay = delay
        self.cf_bypasser = CloudflareBypasser(self.page)
        self.logger = logging.getLogger(__name__)

    def _is_message_page(self):
        print(self.page.url, '/yeni' in self.page.url)
        return "/yeni" in self.page.url

    def _is_detail_page(self):
        return "/detay" in self.page.url

    @staticmethod
    def state_guard(expected_states):
        """
        Guards against unexpected state changes
        expected_states: List of state check functions
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                self = args[0]  # Get instance reference from first argument
                current_url = self.page.url
                result = func(*args, **kwargs)
                for state_check in expected_states:
                    if state_check(self):  # Pass self to state check
                        return result
                self.logger.info(f"Unexpected state. Current URL: {self.page.url}")
                self.cf_bypasser.bypass()
                time.sleep(self.delay)
                self.logger.info("Waiting user to proceed, Please type 'y' to continue")
                print(self.args, self.kwargs)
                if input() == 'y':
                    self._get_page(current_url) #FIXME?
                    return func(*args, **kwargs)
                return result
            return wrapper
        return decorator
    
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
            self.logger.info("Waiting user to proceed, Please type 'y' to continue")
            if input() == 'y':
                self._get_page(url)

    def _find_message_box(self):
        message_box_div = self.page.ele("tag:div@@class=msg-form")
        message_box = message_box_div.ele("tag:textarea@@id:messageContent")
        return message_box # ChromiumElement
    
    def _find_send_button(self):
        send_button = self.page.ele("tag:button@@class=btn btn-form")
        return send_button # ChromiumElement

    def _find_detail_message_button(self):
        detail_message_button_div = self.page.ele("tag:div@@class=user-info-send-message")
        detail_message_button = detail_message_button_div.ele("tag:a")
        return detail_message_button # ChromiumElement
    

    @state_guard([_is_message_page, _is_detail_page])
    def _click(self, button):
        button.click()
        time.sleep(self.delay)
        while self.page.states.ready_state != "complete":
            time.sleep(1)
        
    def send_message(self, url: str):
        try:
            self._get_page(url)
            detail_message_button = self._find_detail_message_button()
            #detail_message_button = detail_message_button.attr("href")
            #self._get_page(detail_message_button)
            self._click(detail_message_button)
            messageBox = self._find_message_box()
            self._click(messageBox)
            self.page.actions.type(self.message)
            send_button = self._find_send_button()
            self._click(send_button)
        except Exception as e:
            self.logger.error(f"Error sending message: {e}", exc_info=True)

