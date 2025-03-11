import configparser
import os

current_dir = os.path.dirname(__file__)

# 创建一个配置解析器
config = configparser.ConfigParser()

# 读取配置文件
config_default_path = os.path.join(current_dir, "config.ini")
config.read(config_default_path)

# print(config['spider']['interface'])
