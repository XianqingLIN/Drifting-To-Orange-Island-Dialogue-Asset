import os
import json
import requests

APP_ID     = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
APP_TOKEN  = os.getenv("FEISHU_APP_TOKEN")
TABLE_ID   = os.getenv("FEISHU_TABLE_ID")

# 1. 换 token
token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
token_res = requests.post(token_url, json={"app_id": APP_ID, "app_secret": APP_SECRET})

print("status:", token_res.status_code)
print("APP_ID:", repr(APP_ID))
print("APP_SECRET:", repr(APP_SECRET))
print("body:", token_res.text) 

token = token_res.json()["tenant_access_token"]

# 2. 拉表格数据
records_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
headers = {"Authorization": f"Bearer {token}"}
records = requests.get(records_url, headers=headers).json()

# 3. 保存 JSON
with open("feishu_data.json", "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print("✅ Feishu data saved to feishu_data.json")
