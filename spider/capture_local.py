import datetime
import os
import socket
import subprocess
import threading
import time
import signal
import platform

from config.config import config
from config.logger import logger
from spider.spider import SequentialSpider


class TrafficCapture:
    def __init__(self):
        self.interface = config["spider"]["interface"]
        self.output_dir = config["spider"]["output_dir"]
        os.makedirs(self.output_dir, exist_ok=True)

        self.output_file = None
        self.tshark_process = None
        self.stop_event = threading.Event()
        self.is_windows = platform.system().lower() == "windows"

    def _generate_filename(self, org, index):
        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        return os.path.join(self.output_dir, f"{index}_{org}_{ts}.pcap")

    def start(self, org, index, duration=30):
        self.output_file = self._generate_filename(org, index)
        cmd = ["tshark", "-i", self.interface, "-w", self.output_file, "tcp or udp"]

        try:
            logger.info(f"启动 tshark 采集: {' '.join(cmd)}")

            # 根据操作系统选择不同的启动方式
            if self.is_windows:
                self.tshark_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP  # 在 Windows 上使用新进程组
                )
            else:
                self.tshark_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid  # 在 Unix 上创建一个新的进程组
                )
            return True
        except Exception as e:
            logger.error(f"启动 tshark 失败: {e}")
            return False


    def stop(self):
        if self.tshark_process and self.tshark_process.poll() is None:
            try:
                # 等待爬虫任务结束后发送停止信号
                logger.info("发送 SIGINT 终止 tshark")
                if self.is_windows:
                    self.tshark_process.send_signal(signal.CTRL_BREAK_EVENT)  # Windows 特有的信号
                else:
                    os.killpg(os.getpgid(self.tshark_process.pid), signal.SIGINT)  # 发送 SIGINT 信号

                # 等待 tshark 完成数据写入
                self.tshark_process.wait(timeout=10)
            except Exception as e:
                logger.warning(f"优雅终止失败，尝试强杀: {e}")
                self.tshark_process.kill()  # 强制终止进程

        logger.info(f"流量捕获结束，文件保存至: {self.output_file}")


def resolve_ip(url):
    try:
        return socket.gethostbyname(url.split("://")[-1].split("/")[0])
    except Exception as e:
        logger.error(f"URL 解析失败: {e}")
        return None


def run_task(urls, org, index, duration=30):
    if not urls:
        logger.error("URL 列表为空")
        return False

    ip = resolve_ip(urls[0])
    if not ip:
        return False
    logger.info(f"目标 IP: {ip}")

    capture = TrafficCapture()
    if not capture.start(org, index, duration):
        return False

    try:
        # 启动爬虫任务
        SequentialSpider(urls).scrape()
        logger.info("爬虫任务完成")
    except Exception as e:
        logger.error(f"爬虫异常: {e}")
    finally:
        # 确保捕获进程完全停止
        capture.stop()
        time.sleep(1)  # 额外等待，确保进程完全停止

    return True


def main(urls, org, index, duration=30):
    logger.info(f"任务开始: {index}_{org}，URL 数量: {len(urls)}")
    result = run_task(urls, org, index, duration)
    logger.info(f"任务 {'成功' if result else '失败'}: {index}_{org}")
