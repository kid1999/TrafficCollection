import os
import re
import shutil

import pandas as pd

from capture import main


def extract_urls(text):
    """ Extract URLs from a given string. """
    url_pattern = r'https?://[^\s\',\]]+'  # 匹配 http 或 https 开头，直到空白字符、逗号或右方括号为止
    urls = re.findall(url_pattern, text)
    return urls


def check_disk_space(threshold_gb=10):
    disk_usage = shutil.disk_usage(os.path.dirname(os.path.abspath(__file__)))
    free_gb = disk_usage.free / (1024 ** 3)  # 转换为 GB
    if free_gb < threshold_gb:
        print(f"警告：磁盘空间不足，剩余空间为 {free_gb:.2f} GB，低于阈值 {threshold_gb} GB，即将退出程序。")
        return True
    return False


def read_urls(path):
    """ Read URLs from a CSV file and return a list. """
    data = pd.read_csv(path)
    urls = []
    organizations = []
    for index, row in data.iterrows():
        urls.append(extract_urls(data.iloc[index]['GitHub URLs']))
        organizations.append(data.iloc[index]['Organization'])
    return urls, organizations




if __name__ == '__main__':

    urls, organizations = read_urls('./config/organizations_github_urls_.csv')
    index = 0
    for url, organization in zip(urls, organizations):
        if check_disk_space(threshold_gb=10):
            break
        main(url, organization, index)
        index += 1







