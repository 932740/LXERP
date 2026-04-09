import pandas as pd
from serpapi import GoogleSearch
import time
import re

# ================= 配置区 =================
# 请在此处填写你的真实 SerpApi Key
SERPAPI_KEY = ""  

# 输入输出路径配置（已替换为占位路径）
INPUT_PATH = r"C:\path\to\your\input_file.xlsx"
OUTPUT_PATH = r"C:\path\to\your\output_result.xlsx"

# 默认搜索国家
COUNTRY_CODE = "us"
# ==========================================

def get_platform_data(row):
    """
    抓取全网信息，确保提取数值价格、货币符号和商品链接
    """
    brand = str(row.get('核心品牌词', '')).strip()
    sku = str(row.get('SKU', '')).strip()
    asin = str(row.get('ASIN', '')).strip()

    # 构造精准搜索词逻辑
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
            print(f"⚠️  警告: [{search_query}] 未返回任何结果")

        for item in shopping_results:
            title = item.get("title", "").lower()

            # 基础过滤：保留与核心业务相关的关键词
            valid_keywords = ['heater', 'induction', 'bolt', 'tool', 'magnetic', 'smoke', 'fog', 'machine']
            if any(k in title for k in valid_keywords):

                # 1. 价格处理
                raw_price = item.get("price", "")
                ext_price = item.get("extracted_price")
                currency_unit = re.sub(r'[0-9., ]', '', raw_price) if raw_price else "$"

                # 2. 链接处理
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
    print("🚀 启动任务：正在检索全网价格并比对...")
    try:
        # 读取原始数据
        df = pd.read_excel(INPUT_PATH)
    except Exception as e:
        print(f"❌ 读取 Excel 失败: {e}")
        return

    # 移除不需要的列（如果有）
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

                # 计算“比我便宜”逻辑
                p = offer.get("全网价格")
                if p and my_price:
                    new_row["比我便宜"] = "是" if p < my_price else "否"
                else:
                    new_row["比我便宜"] = "-"

                final_data.append(new_row)

        # 保护 API 额度，设定延迟
        time.sleep(0.5)

    if final_data:
        output_df = pd.DataFrame(final_data)
        
        # 按照需求对齐最终列顺序
        cols_order = [
            'ASIN', 'MAY', '平台来源', '全网价格', '价格单位', '比我便宜',
            '商品链接', '商品标题', '国家', 'SKU', '核心品牌词'
        ]

        # 最终检查列是否存在并排序
        final_cols = [c for c in cols_order if c in output_df.columns]
        output_df = output_df[final_cols]

        # 导出文件
        output_df.to_excel(OUTPUT_PATH, index=False)
        print(f"👉 任务完成。\n👉 结果文件保存在: {OUTPUT_PATH}")
    else:
        print("未产生任何有效数据。")


if __name__ == "__main__":
    main()
