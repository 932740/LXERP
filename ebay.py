import pandas as pd
from serpapi import GoogleSearch
import time
import re

# ================= 配置区 =================
SERPAPI_KEY = "5f9a191f10d54745f3c40ddaadaf93dd9e585a216e65005d35cf10c13fc4a46d"  # 请填入你的真实 Key
INPUT_PATH = r"E:\Pycharm Project\pa\热销产品.xlsx"
OUTPUT_PATH = r"E:\Pycharm Project\pa\全网比价结果.xlsx"

# 默认搜索国家
COUNTRY_CODE = "us"


# ==========================================

def get_platform_data(row):
    """
    抓取全网信息，确保提取数值价格、货币符号和绝对可以访问的商品链接
    """
    brand = str(row.get('核心品牌词', '')).strip()
    sku = str(row.get('SKU', '')).strip()
    asin = str(row.get('ASIN', '')).strip()

    # 构造精准搜索词
    # 策略：如果品牌名包含产品名，直接用品牌名+SKU；否则组合搜索
    if "machine" in brand.lower() or "heater" in brand.lower():
        search_query = f"{brand} {sku}".strip()
    else:
        search_query = f"{brand} {asin}".strip()

    print(f"🔍 正在抓取关键词: [{search_query}]")

    params = {
        "engine": "google_shopping",
        "q": search_query,
        "google_domain": "google.com",
        "gl": COUNTRY_CODE,
        "hl": "en",
        "api_key": SERPAPI_KEY
    }

    results_list = []
    try:
        search = GoogleSearch(params)
        data = search.get_dict()
        shopping_results = data.get("shopping_results", [])

        if not shopping_results:
            print(f"⚠️  警告: [{search_query}] 未返回任何搜索结果")

        for item in shopping_results:
            title = item.get("title", "").lower()

            # 基础过滤：排除完全不相关的干扰项 (如鞋子、箱子)
            # 如果是搜加热器相关的，保留加热器；如果是烟雾机，保留烟雾机
            valid_keywords = ['heater', 'induction', 'bolt', 'tool', 'magnetic', 'smoke', 'fog', 'machine']
            if any(k in title for k in valid_keywords):

                # 1. 价格处理
                raw_price = item.get("price", "")
                ext_price = item.get("extracted_price")
                currency_unit = re.sub(r'[0-9., ]', '', raw_price) if raw_price else "$"

                # 2. 链接处理 (核心修正)
                # SerpApi 的链接可能在 'link' 字段，有时是直接跳转
                product_link = item.get("link")
                if not product_link:
                    product_link = item.get("product_link", "无链接")

                results_list.append({
                    "平台来源": item.get("source"),
                    "全网价格": ext_price,
                    "价格单位": currency_unit,
                    "商品链接": product_link,
                    "商品标题": item.get("title")
                })

    except Exception as e:
        print(f"❌ 搜索出错: {e}")

    return results_list


def main():
    print("🚀 启动任务：正在修正链接提取逻辑并移除图片列...")
    try:
        # 读取原始数据
        df = pd.read_excel(INPUT_PATH)
    except Exception as e:
        print(f"❌ 读取 Excel 失败: {e}")
        return

    # 按照你的图示要求移除不需要的列
    columns_to_drop = ['产品主图', '运费信息']
    df = df.drop(columns=[c for c in columns_to_drop if c in df.columns])

    final_data = []

    for index, row in df.iterrows():
        my_price = row.get('MAY', 0)

        # 爬取该行的多平台数据
        market_data = get_platform_data(row)

        if not market_data:
            # 如果没搜到，保留一行原表信息，提示未匹配
            temp_row = row.to_dict()
            temp_row.update({
                "平台来源": "未匹配到结果",
                "全网价格": None,
                "价格单位": "-",
                "比我便宜": "N/A",
                "商品链接": "无结果",
                "商品标题": "-"
            })
            final_data.append(temp_row)
        else:
            for offer in market_data:
                new_row = row.to_dict()
                new_row.update(offer)

                # 计算“比我便宜”
                p = offer.get("全网价格")
                if p and my_price:
                    new_row["比我便宜"] = "是" if p < my_price else "否"
                else:
                    new_row["比我便宜"] = "-"

                final_data.append(new_row)

        # 保护 API 额度，微调延迟
        time.sleep(0.5)

    # 按照图二格式对齐最终列顺序
    output_df = pd.DataFrame(final_data)
    cols_order = [
        'ASIN', 'MAY', '平台来源', '全网价格', '价格单位', '比我便宜',
        '商品链接', '商品标题', '国家', 'SKU', '核心品牌词'
    ]

    # 最终检查列是否存在并排序
    final_cols = [c for c in cols_order if c in output_df.columns]
    output_df = output_df[final_cols]

    # 导出文件
    output_df.to_excel(OUTPUT_PATH, index=False)
    print(f"👉 商品已成功抓取。\n👉 结果文件: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()