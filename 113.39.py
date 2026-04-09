import pandas as pd
from serpapi import GoogleSearch
import time
import re
import os
from datetime import datetime

# ================= 配置区 =================
SERPAPI_KEY = "5f9a191f10d54745f3c40ddaadaf93dd9e585a216e65005d35cf10c13fc4a46d"
INPUT_PATH = r"E:\Pycharm Project\pa\热销产品.xlsx"

# 根据日期生成文件名
current_date = datetime.now().strftime("%Y%m%d")
OUTPUT_PATH = rf"E:\Pycharm Project\pa\爬取结果_{current_date}.xlsx"

PLATFORMS = [
    "Amazon", "TikTok", "AliExpress", "Shopee", "eBay",
    "Shein", "Mercado Libre", "Walmart", "Temu",
    "Ozon", "Wish", "Coupang", "Joom", "Noon", "Jumia"
]
# ==========================================

def clean_platform_name(source_text):
    if not source_text:
        return "Other"
    for p in PLATFORMS:
        if p.lower() in source_text.lower():
            return p
    return source_text

def get_market_data(brand, sku):
    query = f"{brand} {sku}"
    print(f"正在检索: {query}...", end="", flush=True)

    results = []
    try:
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": SERPAPI_KEY,
            "gl": "us",
            "hl": "en"
        }
        search = GoogleSearch(params)
        data = search.get_dict()
        shopping_results = data.get("shopping_results", [])

        for item in shopping_results:
            source_raw = item.get("source", "")
            platform = clean_platform_name(source_raw)

            if platform in PLATFORMS:
                # 核心修复逻辑：多路径获取链接
                final_link = item.get("link")
                if not final_link:
                    final_link = item.get("product_link")

                # 处理 Google 广告跳转链接
                if final_link and "google.com/url" in final_link:
                    match = re.search(r"url=(http[^&]+)", final_link)
                    if match:
                        from urllib.parse import unquote
                        final_link = unquote(match.group(1))

                results.append({
                    "平台来源": platform,
                    "全网价格": item.get("extracted_price"),
                    "价格单位": item.get("currency", "$"),
                    "商品链接": final_link if final_link else "提取失败",
                    "商品标题": item.get("title", "无标题").strip()
                })

        print(f" 找到 {len(results)} 条记录")
    except Exception as e:
        print(f" 错误: {e}")

    return results

def main():
    if not os.path.exists(INPUT_PATH):
        print(f"找不到输入文件: {INPUT_PATH}")
        return

    print("开始执行脚本...")
    df = pd.read_excel(INPUT_PATH)
    final_data = []

    for index, row in df.iterrows():
        brand = str(row.get('核心品牌词', '')).strip()
        sku = str(row.get('SKU', '')).strip()
        my_price = row.get('MAY', 0)

        if not brand or not sku:
            continue

        market_items = get_market_data(brand, sku)

        if not market_items:
            entry = row.to_dict()
            entry.update({"平台来源": "无匹配", "商品链接": "无结果", "比我便宜": "-"})
            final_data.append(entry)
        else:
            for item in market_items:
                entry = row.to_dict()
                entry.update(item)

                # 价格对比
                try:
                    ext_p = float(item["全网价格"]) if item["全网价格"] else 0
                    if ext_p > 0 and my_price > 0:
                        entry["比我便宜"] = "是" if ext_p < my_price else "否"
                    else:
                        entry["比我便宜"] = "-"
                except:
                    entry["比我便宜"] = "-"

                final_data.append(entry)

        time.sleep(0.5)

    if final_data:
        output_df = pd.DataFrame(final_data)
        cols_order = [
            '国家', 'ASIN', 'SKU', '核心品牌词', 'MAY',
            '平台来源', '全网价格', '价格单位', '商品标题', '商品链接', '比我便宜'
        ]
        existing_cols = [c for c in cols_order if c in output_df.columns]
        output_df = output_df[existing_cols]
        output_df.to_excel(OUTPUT_PATH, index=False)
        print(f"\n执行完成！结果保存在: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()