from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from config.logger import logger
from config.config import config


class SequentialSpider:
    def __init__(self, urls, timeout=config['spider']['page_timeout']):
        self.urls = urls
        self.timeout = timeout

    def scrape(self):
        """
        Perform sequential scraping of the given URLs.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Use incognito context to avoid retaining session data or cache
            context = browser.new_context(ignore_https_errors=True)
            context.set_default_navigation_timeout(self.timeout)

            for i, url in enumerate(self.urls):
                try:
                    logger.info(f"{i} - Scraping {url}...")
                    page = context.new_page()
                    # Set headers to disable cache
                    page.set_extra_http_headers(
                        {
                            "Cache-Control": "no-cache, no-store, must-revalidate",
                            "Pragma": "no-cache",
                            "Expires": "0",
                        }
                    )
                    page.goto(url, timeout=self.timeout)
                    content = page.content()
                    page.wait_for_load_state(
                        "networkidle", timeout=self.timeout
                    )  # 等待所有请求完成
                    logger.info(f"success access: {url}")
                except PlaywrightTimeoutError:
                    logger.debug(f"Timeout while loading {url}. Skipping...")
                except Exception as e:
                    logger.debug(f"Error scraping {url}: {e}")
                finally:
                    page.close()

            browser.close()


# Example usage:
# if __name__ == "__main__":
#     urls = [
#         "https://baidu.com",
#         "https://qq.com",  # Deliberate delay
#         "https://sohu.com",  # Non-existent URL
#     ]
#
#     spider = SequentialSpider(urls, timeout=5000)
#     spider.scrape()
