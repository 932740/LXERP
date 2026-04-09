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
    # 读取 config.json
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 启动调试模式的 Edge
    cmd = f'"{config["edge_path"]}" --remote-debugging-port=9222 --user-data-dir="{config["user_data_path"]}"'
    subprocess.Popen(cmd, shell=True)
    time.sleep(3)  # 等待浏览器启动

    # 设置调试地址，连接浏览器
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Edge(options=options)

    # 如果页面没有加载，跳转到目标页面
    if "lingxing.com" not in driver.current_url:
        driver.get(config["target_url"])

    return driver


def auto_login(driver):
    # 读取 credentials.yaml
    with open('credentials.yaml', 'r', encoding='utf-8') as f:
        creds = yaml.safe_load(f)['lingxing']

    try:
        # 设置 WebDriverWait，等待页面加载
        wait = WebDriverWait(driver, 10)

        # 检查是否在登录页面
        username_fields = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, "//input[contains(@placeholder, '账号') or @type='text']")))

        # 确保输入框可交互
        if username_fields and username_fields[0].is_displayed() and username_fields[0].is_enabled():
            print("检测到登录页面，开始填写账号和密码...")

            # 清空并填写账号和密码
            username_fields[0].clear()
            username_fields[0].send_keys(creds['user'])

            password_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))

            # 确保密码框可交互
            if password_field.is_displayed() and password_field.is_enabled():
                password_field.clear()
                password_field.send_keys(creds['pass'])

                # 查找并点击登录按钮
                login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'lingxing')]")))
                login_btn.click()

                print("登录按钮已点击，请检查是否有验证码需要手动处理。")
            else:
                print("密码输入框不可用或被遮挡。")
        else:
            print("当前已登录，跳过登录流程。")

    except Exception as e:
        print(f"登录过程出错：{e}")

