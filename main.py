import time
from login  import start_and_connect, auto_login
from selenium import webdriver
from login import auto_login
from get_token import get_access_token,get_appid,get_appsecret



def main():
    driver = start_and_connect()
    auto_login(driver)

    # 可以继续添加其他操作，确保登录成功后执行后续步骤
    # Example usage:


if __name__ == "__main__":
    # main()
    token = get_access_token(get_appid(), get_appsecret())
    print(token)