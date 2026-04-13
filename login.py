# 领星ERP登录操作
import json
import yaml
import subprocess
import time
import os
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def start_and_connect():
    # 1. 读取本地配置文件
    # 建议 config.json 包含 edge_path, user_data_path, target_url
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: 找不到 config.json 文件")
        return None

    # 2. 启动调试模式的 Edge 浏览器
    # 通过 --remote-debugging-port 允许 Selenium 接管现有会话
    cmd = f'"{config["edge_path"]}" --remote-debugging-port=9222 --user-data-dir="{config["user_data_path"]}"'
    subprocess.Popen(cmd, shell=True)
    time.sleep(3)

    # 3. 设置调试地址并连接
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Edge(options=options)
        # 检查当前 URL，若不在目标域名则跳转
        if "example.com" not in driver.current_url:
            driver.get(config["target_url"])
        return driver
    except Exception as e:
        print(f"连接浏览器失败: {e}")
        return None

def auto_login(driver):
    # 1. 读取凭据文件
    # 建议 credentials.yaml 包含相应站点的 user 和 pass
    try:
        with open('credentials.yaml', 'r', encoding='utf-8') as f:
            creds = yaml.safe_load(f)['site_key']
    except Exception as e:
        print(f"读取凭据失败: {e}")
        return

    try:
        # 2. 设置显式等待
        wait = WebDriverWait(driver, 10)

        # 3. 定位账号输入框 (使用通用的模糊匹配)
        username_fields = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, "//input[contains(@placeholder, '账号') or @type='text']")))

        # 4. 执行输入逻辑
        if username_fields and username_fields[0].is_displayed() and username_fields[0].is_enabled():
            print("检测到登录页面，开始填写信息...")

            # 清空并填写账号
            username_fields[0].clear()
            username_fields[0].send_keys(creds['user'])

            # 定位并填写密码框
            password_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))

            if password_field.is_displayed() and password_field.is_enabled():
                password_field.clear()
                password_field.send_keys(creds['pass'])

                # 定位并点击登录按钮 (XPath 已脱敏)
                login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., '登录')]")))
                login_btn.click()

                print("登录动作已触发，请关注可能出现的验证码。")
            else:
                print("密码输入框不可操作。")
        else:
            print("未检测到登录输入框，可能处于已登录状态。")

    except Exception as e:
        print(f"自动化执行过程出错: {e}")

if __name__ == "__main__":
    browser_driver = start_and_connect()
    if browser_driver:
        auto_login(browser_driver)
