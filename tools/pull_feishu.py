import os, json, requests

APP_ID     = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
APP_TOKEN  = os.getenv("FEISHU_APP_TOKEN")
BASE_DIR   = "feishu_tables"

# 1. token
token = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}
).json()["tenant_access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. 所有 table
tables = requests.get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables",
    headers=headers
).json()["data"]["items"]

os.makedirs(BASE_DIR, exist_ok=True)

# 3. 根据前缀拆分目录
for tbl in tables:
    table_id, table_name = tbl["table_id"], tbl["name"]

    if "_" in table_name:
        prefix, name = table_name.split("_", 1)
    else:
        prefix, name = "uncategorized", table_name

    out_dir = os.path.join(BASE_DIR, prefix)
    os.makedirs(out_dir, exist_ok=True)

    # 拉数据
    records = requests.get(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records",
        headers=headers,
        params={"page_size": 500}
    ).json()

    file_path = os.path.join(out_dir, f"{name}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"✅ {file_path}")
