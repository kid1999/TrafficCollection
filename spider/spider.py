from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from config.config import config
from config.logger import logger


class SequentialSpider:
    def __init__(self, urls, timeout=int(config['spider']['page_timeout'])):
        self.urls = urls
        self.timeout = timeout

    def scrape(self):
        """
        Perform sequential scraping of the given URLs.
        """
        with sync_playwright() as p:
            with p.chromium.launch(headless=True) as browser:  # 确保浏览器正确关闭
                with browser.new_context(ignore_https_errors=True) as context:  # 确保上下文正确关闭
                    context.set_default_navigation_timeout(self.timeout)
                    for i, url in enumerate(self.urls):
                        page = None  # 初始化 page 为 None
                        try:
                            logger.info(f"{i} - Scraping {url}...")
                            page = context.new_page()  # 创建新页面
                            page.set_extra_http_headers(
                                {
                                    "Cache-Control": "no-cache, no-store, must-revalidate",
                                    "Pragma": "no-cache",
                                    "Expires": "0",
                                }
                            )
                            # page.goto(url, timeout=self.timeout, wait_until=config['spider']['wait_until'])
                            page.goto(url, timeout=self.timeout)
                            page.wait_for_load_state(state=config['spider']['wait_until'], timeout=self.timeout)
                            content = page.content()
                            page.close()
                            logger.info(f"Success accessing: {url}")
                        except PlaywrightTimeoutError:
                            logger.warning(f"Timeout while loading {url}. Skipping...")
                        except Exception as e:
                            logger.error(f"Error scraping {url}: {e}", exc_info=True)  # 记录完整的异常信息
                        finally:
                            context.close()
                            browser.close()
                            logger.debug(f"Finished processing {url}")
