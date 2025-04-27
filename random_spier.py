from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import random
import logging


# 配置日志记录器（你可替换为自己的 logger）
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_raw_urls(path):
    urls = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                urls.append("http://" + line)
    return urls


class SequentialSpider:
    def __init__(self, start_urls, timeout=10000):
        self.start_urls = start_urls
        self.timeout = timeout
        self.visited = set()

    def scrape(self):
        """
        For each starting URL, recursively visit all reachable links without repetition.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            context.set_default_navigation_timeout(self.timeout)

            queue = list(self.start_urls)

            while queue:
                url = queue.pop(0)
                if url in self.visited:
                    continue
                page = None
                try:
                    logger.info(f"[+] 访问: {url}")
                    self.visited.add(url)
                    page = context.new_page()
                    page.set_extra_http_headers({
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0",
                    })
                    page.goto(url, timeout=self.timeout, wait_until='networkidle')
                    time.sleep(random.uniform(1, 2))  # 模拟用户停留

                    # 抓取链接并入队
                    links = page.eval_on_selector_all("a", "elements => elements.map(e => e.href)")
                    for link in links:
                        if link.startswith("http") and link not in self.visited:
                            queue.append(link)

                    logger.info(f"[✓] 成功访问: {url}")
                except PlaywrightTimeoutError:
                    logger.warning(f"[!] 超时跳过: {url}")
                except Exception as e:
                    logger.error(f"[✗] 错误访问 {url}: {e}", exc_info=True)
                finally:
                    if page:
                        page.close()

            context.close()
            browser.close()
            logger.info("🎯 所有链接访问完毕")


if __name__ == "__main__":
    # 配置你的起始 URL 文件路径
    urls = get_raw_urls('./config/urls.txt')  # 一行一个裸域名，如 example.com
    index = 0
    end = 1000

    for url in urls[index:end]:
        logger.info(f"\n🚀 开始爬取起始 URL: {url}")
        spider = SequentialSpider([url])
        spider.scrape()
        logger.info(f"✅ 完成: {url}\n")
