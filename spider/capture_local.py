import os
import queue
import threading
import datetime
import subprocess
import socket
import psutil

from config.config import config
from config.logger import logger
from spider.spider import SequentialSpider


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


class TrafficCapture:
    def __init__(self):
        """流量捕获器"""
        self.interface = config["spider"]["interface"]  # 从配置读取网卡
        self.output_dir = config["spider"]["output_dir"]  # 从配置读取存储路径
        os.makedirs(self.output_dir, exist_ok=True)

        # 队列存储流量数据，异步写入
        self.data_queue = queue.Queue(maxsize=100)

        self.tshark_process = None
        self.capture_thread = None
        self.write_thread = None
        self.stop_event = threading.Event()

        self.output_file = None

    def _generate_filename(self, organization, index):
        """生成基于时间戳的唯一文件名"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        return os.path.join(self.output_dir, f"{index}_{organization}_{timestamp}.pcap")

    def _capture_output(self):
        """将 tshark 输出数据写入队列"""
        try:
            while not self.stop_event.is_set():
                data = self.tshark_process.stdout.read(4096)  # 分块读取
                if not data:
                    break
                self.data_queue.put(data)
        except Exception as e:
            logger.error(f"读取 tshark 输出失败: {e}")

    def _write_to_file(self):
        """将数据队列写入本地文件"""
        logger.info("启动本地文件写入线程")
        with open(self.output_file, "wb") as f:
            while not self.stop_event.is_set() or not self.data_queue.empty():
                try:
                    data = self.data_queue.get(timeout=1)
                    f.write(data)
                except queue.Empty:
                    continue
            logger.info(f"数据写入完成: {self.output_file}")

    def start_capture(self, organization, index, duration=30):
        """启动流量捕获"""
        logger.info(f"开始流量捕获: {organization} - {index}")

        # 生成输出文件路径
        self.output_file = self._generate_filename(organization, index)

        # tshark命令
        command = [
            "tshark",
            "-i",
            self.interface,  # 从配置读取网卡
            "-w",
            "-",  # 输出到标准输出流
            "-a",
            f"duration:{duration}",  # 捕获时长
        ]

        try:
            self.tshark_process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # 启动读取线程
            self.capture_thread = threading.Thread(
                target=self._capture_output, daemon=True
            )
            self.capture_thread.start()

            # 启动写入线程
            self.write_thread = threading.Thread(
                target=self._write_to_file, daemon=True
            )
            self.write_thread.start()

            logger.info("流量捕获线程已启动")
            return True

        except Exception as e:
            logger.error(f"启动流量捕获失败: {e}")
            return False

    def stop_capture(self):
        """停止流量捕获"""
        logger.info("停止流量捕获")

        # 停止事件
        self.stop_event.set()

        # 杀掉 tshark 及其子进程
        if self.tshark_process:
            kill_process_and_children(self.tshark_process.pid)
            self.tshark_process.wait()

        # 等待线程结束
        self.capture_thread.join()
        self.write_thread.join()

        logger.info(f"流量捕获完成，数据保存至: {self.output_file}")
        return self.output_file


def _get_target_ip(url):
    """解析 URL 获取目标 IP 地址"""
    try:
        hostname = url.split("://")[-1].split("/")[0]
        return socket.gethostbyname(hostname)
    except Exception as e:
        logger.error(f"解析 URL {url} 失败: {e}")
        return None


def run_task(urls, organization, index, duration=30):
    """爬虫 + 流量监听任务"""
    if not urls:
        logger.error("没有提供 URL")
        return False

    # 初始化流量捕获
    capture = TrafficCapture()

    # 解析第一个 URL 获取目标 IP
    target_ip = _get_target_ip(urls[0])
    if not target_ip:
        logger.error("无法解析目标 IP")
        return False

    logger.info(f"解析目标 IP 成功: {target_ip}")

    # 启动流量监听
    if not capture.start_capture(organization, index, duration):
        logger.error("启动流量捕获失败")
        return False

    # 启动爬虫任务
    try:
        logger.info(f"开始爬取 URLs: {urls}")
        spider = SequentialSpider(urls)
        spider.scrape()
        logger.info("爬虫任务完成")
    except Exception as e:
        logger.error(f"爬虫出错: {e}")
    finally:
        pcap_file = capture.stop_capture()

    logger.info(f"流量保存至: {pcap_file}")
    return True


def main(urls, organization, index, duration=30):
    """统一入口"""
    logger.info(f"开始任务 {index}_{organization}，URL 数量: {len(urls)}")

    success = run_task(urls, organization, index, duration)

    if success:
        logger.info(f"任务 {index}_{organization} 成功")
    else:
        logger.error(f"任务 {index}_{organization} 失败")

    logger.info(f"任务 {index}_{organization} 结束")
