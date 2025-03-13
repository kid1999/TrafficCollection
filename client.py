import os
import threading
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from config.config import config
from config.logger import logger


class MinioFileWatcher:
    def __init__(self, endpoint_url, access_key, secret_key, bucket_name, local_download_path, max_workers=4, batch_size=10):
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.local_download_path = local_download_path
        self.s3_client = self._create_s3_client()
        self.lock = threading.Lock()
        self.max_workers = max_workers
        self.batch_size = batch_size

    def _create_s3_client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="us-east-1",
        )

    def _download_file(self, object_name):
        local_path = os.path.join(self.local_download_path, object_name)
        try:
            with open(local_path, "wb") as f:
                self.s3_client.download_fileobj(self.bucket_name, object_name, f)
            logger.info(f"文件 {object_name} 已下载到 {local_path}")
            return local_path
        except (BotoCoreError, ClientError) as e:
            logger.warning(f"下载文件 {object_name} 失败: {e}")
        return None

    def _delete_file(self, object_name):
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
            logger.info(f"文件 {object_name} 已从 MinIO 删除")
        except (BotoCoreError, ClientError) as e:
            logger.warning(f"删除文件 {object_name} 失败: {e}")

    def _process_file(self, object_name):
        local_path = self._download_file(object_name)
        if local_path:
            self._delete_file(object_name)

    def watch_and_download(self):
        """
        监听 MinIO 存储桶，批量下载文件并删除。
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while True:
                try:
                    response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
                    if "Contents" in response:
                        object_list = [obj["Key"] for obj in response["Contents"]]
                        for i in range(0, len(object_list), self.batch_size):
                            batch = object_list[i:i + self.batch_size]
                            tasks = [executor.submit(self._process_file, obj) for obj in batch]
                            for task in tasks:
                                task.result()  # 确保任务执行完毕
                except (BotoCoreError, ClientError) as e:
                    logger.error(f"监控存储桶时出错: {e}")


# 示例调用
if __name__ == "__main__":
    endpoint_url = config["minio"]["endpoint_url"]
    access_key = config["minio"]["access_key"]
    secret_key = config["minio"]["secret_key"]
    bucket_name = config["minio"]["bucket_name"]
    local_download_path = r"D:\code\Traffic\TrafficCollection"  # 本地下载路径

    watcher = MinioFileWatcher(endpoint_url, access_key, secret_key, bucket_name, local_download_path, max_workers=4, batch_size=10)
    watcher.watch_and_download()
