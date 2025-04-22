import os
import re
import subprocess
import time

import pandas as pd

from spider.capture_local import main


def extract_urls(text):
    """ Extract URLs from a given string. """
    url_pattern = r'https?://[^\s\',\]]+'  # 匹配 http 或 https 开头，直到空白字符、逗号或右方括号为止
    urls = re.findall(url_pattern, text)
    return urls


def read_urls(path):
    """ Read URLs from a CSV file and return a list. """
    data = pd.read_csv(path)
    urls = []
    organizations = []
    for index, row in data.iterrows():
        urls.append(extract_urls(data.iloc[index]['GitHub URLs']))
        organizations.append(data.iloc[index]['Organization'])
    return urls, organizations


# https://github.com/freeCodeCamp/freeCodeCamp
def read_urls_by_cow(path):
    urls = []
    names = []
    with open(path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        urls.append(line.strip())
        names.append(line.split('/')[-2] + '_' + line.split('/')[-1].strip())
    return urls, names


def kill_dumpcap():
    """ 终止 dumpcap 进程 """
    try:
        result = subprocess.run("ps aux | grep dumpcap | grep -v grep | awk '{print $2}'",
                                shell=True, capture_output=True, text=True)
        pids = result.stdout.strip().split("\n")
        for pid in pids:
            if pid:
                os.system(f"kill -9 {pid}")
                print(f"成功终止 dumpcap 进程 PID: {pid}")
    except Exception as e:
        print(f"终止 dumpcap 进程失败: {e}")


def get_raw_urls(path):
    urls = []
    names = []
    with open(path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        urls.append("http://" + line.strip())
        names.append(line.strip())
    return urls, names



if __name__ == '__main__':
    # top 1w github仓库
    urls, names = get_raw_urls('./config/urls.txt')
    index = 0
    end = 1000
    for url, name in zip(urls[index:end], names[index:end]):
        for _ in range(1):
            main([url], name, index)
            time.sleep(3)
        index += 1
        # 额外检查 dumpcap 是否仍在运行
        # kill_dumpcap()
