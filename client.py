import os
import time

import boto3

from config.config import config
from config.logger import logger


class MinioFileWatcher:
    def __init__(
            self, endpoint_url, access_key, secret_key, bucket_name, local_download_path
    ):
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.local_download_path = local_download_path
        self.s3_client = self._create_s3_client()

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

        with open(local_path, "wb") as f:
            self.s3_client.download_fileobj(self.bucket_name, object_name, f)

        # self.s3_client.download_file(self.bucket_name, object_name, local_path)
        logger.info(f"文件 {object_name} 已下载到 {local_path}")
        return local_path

    def _delete_file(self, object_name):
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
        logger.info(f"文件 {object_name} 已从 MinIO 删除")

    def watch_and_download(self, interval=5):
        """
        定时检查存储桶中的新文件，并下载到本地。
        :param interval: 检查间隔时间（秒）
        """
        last_checked = None
        index = 1
        while True:
            try:
                response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
                if "Contents" in response:
                    for obj in response["Contents"]:
                        object_name = obj["Key"]
                        last_modified = obj["LastModified"]

                        # 如果是新文件或上次检查后有更新
                        if last_checked is None or last_modified > last_checked:
                            logger.info(f"检测到新文件 {index} : {object_name}")
                            local_path = self._download_file(object_name)
                            self._delete_file(object_name)
                            last_checked = last_modified
                            index += 1

            except Exception as e:
                logger.error(f"监控存储桶时出错: {e}")

            time.sleep(interval)


# 示例调用
if __name__ == "__main__":
    endpoint_url = config["minio"]["endpoint_url"]
    access_key = config["minio"]["access_key"]
    secret_key = config["minio"]["secret_key"]
    bucket_name = config["minio"]["bucket_name"]
    local_download_path = r"E:\dataset\top1000"  # 本地下载路径

    watcher = MinioFileWatcher(
        endpoint_url, access_key, secret_key, bucket_name, local_download_path
    )
    watcher.watch_and_download(interval=0)  # 每 10 秒检查一次
