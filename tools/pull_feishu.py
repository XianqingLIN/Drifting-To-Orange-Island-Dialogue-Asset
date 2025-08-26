import os, json, requests

# 环境变量
APP_ID     = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
APP_TOKEN  = os.getenv("FEISHU_APP_TOKEN")
OUT_DIR    = "feishu_tables"            # 输出根目录

# 0. 换取 token
token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
token = requests.post(token_url, json={"app_id": APP_ID, "app_secret": APP_SECRET}).json()["tenant_access_token"]

headers = {"Authorization": f"Bearer {token}"}

# 1. 列出所有 table
tables = requests.get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables",
    headers=headers
).json()["data"]["items"]

os.makedirs(OUT_DIR, exist_ok=True)

# 2. 遍历 table → 遍历 view → 拉取并保存
for tbl in tables:
    table_id   = tbl["table_id"]
    table_name = tbl["name"]

    # 2.1 列出该 table 的所有视图
    views = requests.get(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/views",
        headers=headers
    ).json()["data"]["items"]

    # 2.2 遍历视图
    for vw in views:
        view_id   = vw["view_id"]
        view_name = vw["name"]

        # 拉取该视图下的记录
        records = requests.get(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records",
            headers=headers,
            params={"view_id": view_id, "page_size": 500}
        ).json()

        # 保存
        safe_name = f"{table_name}__{view_name}".replace("/", "_")
        file_path = os.path.join(OUT_DIR, f"{safe_name}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        print(f"✅ {file_path} ({len(records['data']['items'])} rows)")
