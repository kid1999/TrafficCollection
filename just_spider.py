from config.logger import logger
from spider.spider import SequentialSpider


def get_raw_urls(path):
    urls = []
    with open(path, 'r') as f:
        lines = f.readlines()
    for line in lines:
        urls.append("http://" + line.strip())
    return urls

if __name__ == "__main__":
    urls = get_raw_urls('./config/urls.txt')
    index = 0
    end = 1000
    for url in urls[index:end]:
        for _ in range(10):
            spider = SequentialSpider([url])
            spider.scrape()
        
        
# 实时监听tcp流量并将其写入X   192.168.31.108
# tshark -i WLAN -f "tcp" -w D:\code\Traffic\datasets\test2.pcap   
# tshark -i WLAN -f "tcp" -b filesize:50000000 -w D:\code\Traffic\datasets\test.pcap  
# 切分pcap
# editcap -s 5000000 input.pcap output_%03d.pcap
