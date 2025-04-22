import datetime
import io
import socket
import subprocess
import threading

import boto3
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
        parent.wait(timeout=2)  # 等待父进程结束
    except psutil.NoSuchProcess:
        pass
    except psutil.TimeoutExpired:
        parent.kill()  # 如果超时未结束，强制杀掉


class TrafficCapture:
    def __init__(self, interface="WLAN"):
        self.interface = config["spider"]["interface"]
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=config["minio"]["endpoint_url"],  # MinIO 地址
            aws_access_key_id=config["minio"]["access_key"],  # MinIO 访问密钥
            aws_secret_access_key=config["minio"]["secret_key"],  # MinIO 密钥
            region_name="us-east-1",
            verify=False,
        )
        self.bucket = config["minio"]["bucket_name"]
        self.tshark_process = None
        self.pcap_data = io.BytesIO()
        self.capture_thread = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()  # 添加线程锁保护共享资源

    def _get_target_ip(self, url):
        """解析 URL 获取目标 IP 地址"""
        try:
            hostname = url.split("://")[-1].split("/")[0]
            return socket.gethostbyname(hostname)
        except Exception as e:
            logger.error(f"解析 URL {url} 失败: {e}")
            return None

    def _capture_output(self):
        """持续读取 tshark 输出到 pcap_data"""
        try:
            while not self.stop_event.is_set():
                data = self.tshark_process.stdout.read(4096)
                if not data:
                    break
                with self.lock:  # 使用锁保护 pcap_data 的写入
                    self.pcap_data.write(data)
            # 捕获结束后，确保读取所有剩余数据
            while True:
                data = self.tshark_process.stdout.read(4096)
                if not data:
                    break
                with self.lock:
                    self.pcap_data.write(data)
        except Exception as e:
            logger.error(f"读取 tshark 输出失败: {e}")

    def start_capture(self, target_ip):
        """使用 tshark 启动流量捕获"""
        if not target_ip:
            logger.error("无目标 IP，无法启动捕获")
            return False

        try:
            logger.info(f"开始捕获流量，目标 IP: {target_ip}")
            command = [
                "tshark",
                "-i",
                self.interface,
                "-w",
                "-",  # 输出到标准输出
                "-F",
                "pcap",  # 明确指定 PCAP 格式
            ]

            self.tshark_process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0  # 无缓冲
            )

            self.stop_event.clear()  # 重置停止事件
            self.capture_thread = threading.Thread(
                target=self._capture_output, daemon=True
            )
            self.capture_thread.start()

            logger.info("tshark 捕获进程已启动")
            return True
        except Exception as e:
            logger.error(f"启动 tshark 捕获失败: {e}")
            return False

    def stop_capture_and_upload(self, output_name):
        """停止捕获并上传数据"""
        if not self.tshark_process:
            logger.warning("未启动 tshark 进程，无需停止")
            return False

        logger.info("准备停止 tshark 捕获")
        self.stop_event.set()  # 设置停止标志

        # 等待捕获线程完成，确保所有数据被读取
        if self.capture_thread:
            self.capture_thread.join(timeout=5)
            if self.capture_thread.is_alive():
                logger.warning("捕获线程未及时结束")

        # 优雅地终止 tshark 进程
        try:
            self.tshark_process.terminate()  # 尝试正常终止
            self.tshark_process.wait(timeout=3)  # 等待进程结束
        except subprocess.TimeoutExpired:
            logger.warning("tshark 未正常终止，强制杀掉")
            kill_process_and_children(self.tshark_process.pid)
        finally:
            # 确保关闭管道
            self.tshark_process.stdout.close()
            self.tshark_process.stderr.close()
            self.tshark_process = None

        # 上传捕获的数据
        try:
            with self.lock:  # 确保线程安全地读取 pcap_data
                pcap_content = self.pcap_data.getvalue()
                if not pcap_content:
                    logger.warning("捕获数据为空")
                    return False

                logger.info(f"开始上传 {output_name} 到 MinIO")
                self.s3_client.put_object(
                    Body=self.pcap_data.getvalue(), Bucket=self.bucket, Key=output_name
                )
                logger.info(f"上传 {output_name} 到 MinIO 成功")
                return True
        except Exception as e:
            logger.error(f"上传失败: {e}")
            return False
        finally:
            with self.lock:
                self.pcap_data.seek(0)
                self.pcap_data.truncate()
            self.capture_thread = None


def run_task(urls, organization, index):
    """执行爬取任务并捕获流量"""
    if not urls:
        logger.error("没有提供 URL")
        return False

    capture = TrafficCapture()
    target_ip = capture._get_target_ip(urls[0])
    if not target_ip:
        logger.error("无法解析目标 IP")
        return False

    output_name = f"{index}_{organization}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pcap"

    if not capture.start_capture(target_ip):
        logger.error("启动流量捕获失败")
        return False

    try:
        logger.info(f"开始爬取 URLs: {urls}")
        spider = SequentialSpider(urls)
        spider.scrape()
        logger.info("爬虫任务完成")
    except Exception as e:
        logger.error(f"爬虫出错: {e}")
    finally:
        capture.stop_capture_and_upload(output_name)

    return True


def main(urls, organization, index):
    """任务入口"""
    logger.info(f"开始任务 {index}_{organization}, URL 数量: {len(urls)}")
    success = run_task(urls, organization, index)
    if success:
        logger.info(f"任务 {index}_{organization} 成功")
    else:
        logger.error(f"任务 {index}_{organization} 失败")
    logger.info(f"任务 {index}_{organization} 结束")
