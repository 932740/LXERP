import asyncio
import httpx
import json
import time
import hashlib
import base64
import os
import glob
import pandas as pd
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from send2trash import send2trash  # 导入回收站模块

# 注意：需确保本地存在 get_token 模块或将其逻辑整合至此
# from get_token import get_appid, get_appsecret, get_access_token

# ================= 1. 签名算法 =================
def get_lx_sign(all_params, app_id):
    """通用签名逻辑"""
    sorted_keys = sorted(all_params.keys())
    kv_pairs = []
    for k in sorted_keys:
        v = all_params[k]
        if v == "" or v is None:
            if v is None: kv_pairs.append(f"{k}=null")
            continue
        if isinstance(v, (list, dict)):
            v = json.dumps(v, separators=(',', ':'), ensure_ascii=False)
        kv_pairs.append(f"{k}={v}")
    sign_str = "&".join(kv_pairs)
    md5_val = hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()
    
    # AES 加密逻辑（保持算法结构，用于后续填入 app_id）
    key_bytes = app_id.encode('utf-8').ljust(16, b'\0')[:16]
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    padded_data = pad(md5_val.encode('utf-8'), AES.block_size, style='pkcs7')
    aes_bytes = cipher.encrypt(padded_data)
    return base64.b64encode(aes_bytes).decode('utf-8')


# ================= 2. 获取店铺 ID =================
async def get_target_shop_sid(target_name="Your-Shop-Name"):
    """
    根据店铺名称获取对应的 SID
    需预先配置 get_appid, get_appsecret 等函数获取权限
    """
    # 假设这些函数从环境变量或配置文件中读取
    # app_id = get_appid()
    # app_secret = get_appsecret()
    # access_token = get_access_token(app_id, app_secret)
    
    app_id = "YOUR_APP_ID"
    access_token = "YOUR_ACCESS_TOKEN"

    url = "https://openapi.example.com/api/v1/get_shops" # 已替换为占位地址
    params = {
        "access_token": access_token, 
        "app_key": app_id, 
        "timestamp": str(int(time.time()))
    }
    params["sign"] = get_lx_sign(params, app_id)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=15)
            res_data = response.json()
            if res_data.get('code') == 0:
                for s in res_data.get('data', []):
                    if s['name'] == target_name: return s['sid']
        except Exception as e:
            print(f"获取店铺信息异常: {e}")
    return None


# ================= 3. 滚动去重查询逻辑 =================
async def get_rolling_unique_asins(sid, days_count=10):
    """根据 SID 滚动查询过去 X 天内的去重 ASIN"""
    # app_id = get_appid()
    # access_token = get_access_token(app_id, get_appsecret())
    app_id = "YOUR_APP_ID"
    access_token = "YOUR_ACCESS_TOKEN"

    end_dt = datetime.now()
    date_list = [(end_dt - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days_count)]

    url = "https://openapi.example.com/api/v1/data_query" # 已替换为占位地址
    seen_asins = set()
    export_data = []

    async with httpx.AsyncClient() as client:
        for target_date in date_list:
            offset = 0
            length = 500
            while True:
                biz_params = {
                    "sid": sid,
                    "event_date": target_date,
                    "asin_type": 1,
                    "type": 2,
                    "offset": offset,
                    "length": length
                }
                query_params = {
                    "access_token": access_token,
                    "app_key": app_id,
                    "timestamp": str(int(time.time()))
                }
                sign_params = {**biz_params, **query_params}
                query_params["sign"] = get_lx_sign(sign_params, app_id)

                try:
                    response = await client.post(url, params=query_params, json=biz_params, timeout=20)
                    result = response.json()
                    if result.get('code') == 0:
                        data_node = result.get('data', [])
                        page_items = data_node if isinstance(data_node, list) else data_node.get('list', [])
                        if not page_items: break
                        
                        for item in page_items:
                            asin = item.get('asin')
                            if asin and asin not in seen_asins:
                                seen_asins.add(asin)
                                export_data.append({"首次出现日期": target_date, "ASIN": asin})
                        
                        if len(page_items) < length: break
                        offset += length
                        await asyncio.sleep(0.1)
                    else:
                        break
                except Exception:
                    break
            print(f"日期 {target_date} 处理完成，累计去重 ASIN: {len(seen_asins)}")
    return export_data


# ================= 4. 清理旧文件模块 (放入回收站) =================
def clean_old_reports_to_trash(prefix="Shop_ASIN_Stats_"):
    """在生成新文件前，将匹配前缀的旧统计 Excel 移至回收站"""
    old_files = glob.glob(f"{prefix}*.xlsx")
    for f in old_files:
        try:
            send2trash(f)
            print(f"[回收站] 已移至回收站: {f}")
        except Exception as e:
            print(f"[错误] 无法处理文件 {f}: {e}")


# ================= 5. 主执行逻辑 =================
async def main():
    # 替换为你需要查询的店铺标识名
    shop_name = "US" 
    sid = await get_target_shop_sid(shop_name)

    if sid:
        print(f"--- 正在查询【{shop_name}】最新滚动数据 ---")
        final_list = await get_rolling_unique_asins(sid, days_count=10)

        if final_list:
            df = pd.DataFrame(final_list)
            now_str = datetime.now().strftime('%Y%m%d_%H%M')
            file_prefix = f"{shop_name}_ASIN统计_"
            file_name = f"{file_prefix}{now_str}.xlsx"

            # 保存新文件前清理带有相同前缀的旧文件
            clean_old_reports_to_trash(prefix=file_prefix)

            try:
                df.to_excel(file_name, index=False)
                print("\n" + "=" * 50)
                print(f"导出成功！旧统计文件已清理至回收站。")
                print(f"当前文件: {file_name}")
                print(f"ASIN 总数: {len(df)}")
                print("=" * 50)
            except Exception as e:
                print(f"Excel 保存失败: {e}")
        else:
            print("未获取到数据。")
    else:
        print("未找到对应店铺，请检查店铺名称配置。")


if __name__ == "__main__":
    asyncio.run(main())
