import os
import re
import subprocess
import time

import pandas as pd
import psutil

from spider.capture_minio import main


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


def read_urls_by_cow2(path):
    urls = []
    names = []
    with open(path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        url = line.split('\t')[0]
        urls.append('https://' + url.strip())
        names.append(url.strip())
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


def kill_zombie_processes():
    for proc in psutil.process_iter(['pid', 'ppid', 'name', 'status']):
        if proc.info['status'] == psutil.STATUS_ZOMBIE and proc.info['name'] == 'headless_shell':
            try:
                os.waitpid(proc.info['pid'], os.P_NOWAIT)
                print(f"清理僵尸进程：PID {proc.info['pid']}")
            except Exception as e:
                print(f"清理失败：{e}")


if __name__ == '__main__':

    # 按组织采集
    # urls, organizations = read_urls('./config/organizations_github_urls_.csv')
    # index = 0
    # for url, organization in zip(urls, organizations):
    #     if check_disk_space(threshold_gb=10):
    #         break
    #     main(url, organization, index)
    #     index += 1

    # # 按仓库采集
    # urls, organizations = read_urls('./config/organizations_github_urls_.csv')
    # index = 0
    # for url in urls[0]:
    #     organization = organizations[0] + '-' + url.split('/')[-1]
    #     main([url],organization,index)
    #     # print([url], organization)
    #     index += 1

    # top 1w github仓库
    # urls, names = read_urls_by_cow('./config/top_1w_urls.txt')
    # index = 0
    # end = 10000
    # for url, name in zip(urls[index:end], names[index:end]):
    #     for _ in range(10):
    #         main([url], name, index)
    #         kill_zombie_processes()
    #         time.sleep(1.5)
    #     index += 1
    #     # 额外检查 dumpcap 是否仍在运行
    #     kill_dumpcap()
    
    
    # top 1K 热门网站
    urls, names = read_urls_by_cow2('./config/top_1000.txt')
    index = 0
    end = 1000
    for url, name in zip(urls[index:end], names[index:end]):
        for _ in range(10):
            # print(url, name)
            main([url], name, index)
            kill_zombie_processes()
            # time.sleep(1.5)
        index += 1
        # 额外检查 dumpcap 是否仍在运行
        kill_dumpcap()
