import re

import pandas as pd

from capture import main


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

    urls, organizations = read_urls('./config/organizations_github_urls_.csv')
    index = 0
    for url_, organization in zip(urls[1:], organizations[1:]):
        for url in url_:
            name = organization + '-' + url.split('/')[-1]
            main([url], name, index)
            # print(name, url)
            index += 1







