import asyncio
import random
import os
import glob
import time
import hmac
import hashlib
import base64
import urllib.parse
import aiohttp
import pandas as pd
from playwright.async_api import async_playwright

# ================= 配置区 =================
DING_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=c80714f7206ed737257a0d0996f554715c8673a4745cb72b08ee47819b95db57"
DING_SECRET = "SEC2a056aaf16c152d2c86e51d86f4bfd90ad6db34111d80b62068fe7e0b354b538"

# 控制台颜色配置
RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

# 全局统计变量
stats = {
    "total": 0,
    "normal": 0,
    "abnormal": 0
}
stats_lock = asyncio.Lock()


# ================= 1. 钉钉发送模块 =================
async def send_dingtalk_msg(content):
    """发送钉钉机器人消息"""
    timestamp = str(round(time.time() * 1000))
    secret_enc = DING_SECRET.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, DING_SECRET)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote(base64.b64encode(hmac_code))

    url = f"{DING_WEBHOOK}&timestamp={timestamp}&sign={sign}"

    data = {
        "msgtype": "text",
        "text": {"content": f"亚马逊巡检预警\n{content}"}
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=data) as resp:
                return await resp.json()
        except Exception:
            return None


# ================= 2. 兼容性 Stealth 加载 =================
async def apply_stealth(page):
    try:
        from playwright_stealth import stealth_async
        await stealth_async(page)
    except ImportError:
        pass


# ================= 3. Worker 逻辑 =================
async def worker(worker_id, browser_context, asins):
    page = await browser_context.new_page()
    await apply_stealth(page)

    for asin in asins:
        error_msg = ""
        try:
            await asyncio.sleep(random.uniform(2, 4))
            url = f"https://www.amazon.com/dp/{asin}"
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # 1. 检查变狗 (404或特定文案)
            title = await page.title()
            if response.status == 404 or "Page Not Found" in title or "Sorry!" in title:
                error_msg = "链接失效 (404)"

            if not error_msg:
                # 2. 检查购物车与卖家
                page_content = await page.content()
                has_cart = await page.locator("#add-to-cart-button").is_visible()
                has_buy_now = await page.locator("#buy-now-button").is_visible()
                is_prime = "Join Prime" in page_content or "Exclusive Prime Price" in page_content
                has_options = await page.locator("#buybox-see-all-buying-choices").is_visible()

                if not (has_cart or has_buy_now or is_prime or has_options):
                    error_msg = "无黄金购物车或不可售"
                else:
                    # 3. 卖家身份校验
                    buybox_area = page.locator("#buybox")
                    buybox_text = await buybox_area.inner_text() if await buybox_area.count() > 0 else ""
                    if "solary" not in buybox_text.lower() and "solary" not in page_content.lower():
                        error_msg = "卖家非 solary (疑似被跟卖)"

        except Exception:
            error_msg = "网络超时或加载失败"

        # 统计并输出结果
        async with stats_lock:
            if error_msg:
                stats["abnormal"] += 1
                alert_text = f"商品 ASIN: {asin}\n状态: {error_msg}\n链接: https://www.amazon.com/dp/{asin}"
                print(f"{RED}[异常提醒] {asin} - {error_msg}{RESET}")
                asyncio.create_task(send_dingtalk_msg(alert_text))
            else:
                stats["normal"] += 1
                print(f"{GREEN}[查询正常] 商品 ASIN: {asin}{RESET}")

    await page.close()


# ================= 4. 主程序 =================
async def main():
    files = glob.glob("松立-US_ASIN统计_*.xlsx")
    if not files:
        files = glob.glob("*.xlsx")
    if not files:
        print("错误: 未找到数据源文件")
        return

    input_file = max(files, key=os.path.getctime)
    df = pd.read_excel(input_file)
    asin_list = df['ASIN'].dropna().unique().tolist()

    stats["total"] = len(asin_list)

    print(f"数据源: {input_file}")
    print(f"模式: 3标签页并行 | 钉钉实时预警 | 总计: {stats['total']} 个商品")
    print("-" * 50)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )

        # 任务分片
        num_workers = 3
        if len(asin_list) > 0:
            chunk_size = (len(asin_list) + num_workers - 1) // num_workers
            asin_chunks = [asin_list[i:i + chunk_size] for i in range(0, len(asin_list), chunk_size)]

            tasks = [worker(i + 1, context, chunk) for i, chunk in enumerate(asin_chunks)]
            await asyncio.gather(*tasks)

        print("-" * 50)
        print("巡检任务结束")
        print(f"总查询商品数: {stats['total']}")
        print(f"状态正常数量: {stats['normal']}")
        print(f"状态异常数量: {stats['abnormal']}")
        print("-" * 50)

        # 结束后发送汇总报告给钉钉
        summary_msg = f"报告汇总\n总巡检数: {stats['total']}\n正常数: {stats['normal']}\n异常数: {stats['abnormal']}"
        await send_dingtalk_msg(summary_msg)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())