import re
import time

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
    urls = extract_urls(data.iloc[0]['GitHub URLs'])
    organization = data.iloc[0]['Organization']
    return urls, organization



if __name__ == '__main__':

    urls, organization = read_urls('./config/organizations_github_urls_.csv')

    # print(urls)
    main(urls, organization)






