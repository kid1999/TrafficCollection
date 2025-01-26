import os
import subprocess
import threading
import time

from config.config import config
from config.logger import logger
from spider.spider import SequentialSpider

stop_event = threading.Event()


class TrafficRecorder:
    def __init__(self, interface='WLAN', output_dir='pcap_files'):
        self.interface = interface
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.process = None

    def _generate_filename(self, organization, index):
        timestamp = time.strftime("%Y%m%d%H%M%S")
        return os.path.join(self.output_dir, f"{index}_{organization}_{timestamp}.pcap")

    def start_listening(self, organization, index):
        stop_event.clear()
        filename = self._generate_filename(organization, index)
        cmd = ['tshark', '-i', self.interface, '-w', filename]
        # cmd = ['tshark', '-i', self.interface, '-w', filename, '-f', 'tcp port 80']

        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 等待 stop_event 被设置，表示需要停止
        stop_event.wait()
        self.stop_listening()

    def stop_listening(self):
        if self.process:
            self.process.terminate()  # 终止 tshark 进程
            self.process.wait()  # 等待进程完全退出


def main(urls, organization, index):
    traffic_recorder = TrafficRecorder(interface=config['spider']['interface'], output_dir=config['spider']['output_dir'])
    capture_thread = threading.Thread(target=traffic_recorder.start_listening, args=(organization,index))
    capture_thread.start()

    # 流量主程序
    spider = SequentialSpider(urls, timeout=int(config['spider']['page_timeout']))
    spider.scrape()

    stop_event.set()  # 设置标志位，通知子线程停止
    capture_thread.join()
    logger.info('Finished {}.'.format(organization))


# if __name__ == "__main__":
#     main("http://baidu.com")
