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
    except psutil.NoSuchProcess:
        pass


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
        self.bucket = config["minio"]["bucket_name"]  # 存储桶名称
        self.tshark_process = None
        self.pcap_data = io.BytesIO()
        self.capture_thread = None
        self.stop_event = threading.Event()  # 线程终止标志

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
                data = self.tshark_process.stdout.read(4096)  # 分块读取
                if not data:
                    break
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
                self.interface,  # 指定接口
                "-w",
                "-",  # 输出到标准输出
                "-a",
                "duration:30",
            ]

            # 启动 tshark 进程
            self.tshark_process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # 启动独立线程读取 stdout
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
        if self.tshark_process:
            logger.info("停止 tshark 捕获")
            self.stop_event.set()  # 终止读取线程

            # 关闭 stdout/stderr，防止阻塞
            self.tshark_process.stdout.close()
            self.tshark_process.stderr.close()

            # 确保杀掉所有相关进程
            kill_process_and_children(self.tshark_process.pid)
            self.tshark_process.wait()

            try:
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
                self.pcap_data.seek(0)
                self.pcap_data.truncate()
                self.tshark_process = None
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
