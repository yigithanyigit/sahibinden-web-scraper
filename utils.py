def isPageChanged(chromiumPage, url, function):
    import time
    def wrapper(self, *args, **kwargs):
        self.page.get(url)
        self.cf_bypasser.bypass()
        while self.page.url_available is False:
            time.sleep(1)
        time.sleep(self.delay)
        if self.page.url != url:
            self.logger.info(f"Redirected to: {self.page.url}")
            self.cf_bypasser.bypass()
            time.sleep(self.delay)
            
            # Modified to support both CLI and UI
            if hasattr(self, 'ui_mode') and self.ui_mode:
                return False
            else:
                self.logger.info(f"Waiting user to proceed, Please type 'y' to continue")
                inp = input()
                if inp == 'y':
                    return function(self, *args, **kwargs)
        return function(self, *args, **kwargs)
    return wrapper