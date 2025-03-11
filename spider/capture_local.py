import os
import subprocess
import threading
from datetime import datetime

import psutil

from config.config import config
from config.logger import logger
from spider.spider import SequentialSpider

stop_event = threading.Event()


def kill_process_and_children(parent_pid):
    """确保杀掉 tshark 及其子进程"""
    try:
        parent = psutil.Process(parent_pid)
        children = parent.children(recursive=True)
        for child in children:
            child.terminate()
        gone, still_alive = psutil.wait_procs(children, timeout=2)
        for child in still_alive:
            child.kill()
        parent.terminate()
    except psutil.NoSuchProcess:
        pass


class TrafficRecorder:
    def __init__(self, interface='WLAN', output_dir='pcap_files'):
        self.interface = interface
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.process = None

    def _generate_filename(self, organization, index):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return os.path.join(self.output_dir, f"{index}_{organization}_{timestamp}.pcap")

    def start_listening(self, organization, index):
        stop_event.clear()
        filename = self._generate_filename(organization, index)
        cmd = ['tshark', '-i', self.interface, '-w', filename]

        self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 等待 stop_event 被设置，表示需要停止
        stop_event.wait()

    def stop_listening(self):
        if self.process:
            stop_event.set()  # 设置标志位，通知子线程停止
            kill_process_and_children(self.process.pid)


def main(urls, organization, index):
    traffic_recorder = TrafficRecorder(interface=config['spider']['interface'],
                                       output_dir=config['spider']['output_dir'])
    capture_thread = threading.Thread(target=traffic_recorder.start_listening, args=(organization, index))
    capture_thread.start()

    # 流量主程序
    spider = SequentialSpider(urls, timeout=int(config['spider']['page_timeout']))
    spider.scrape()

    traffic_recorder.stop_listening()

    capture_thread.join()
    logger.info('Finished {}.'.format(organization))
