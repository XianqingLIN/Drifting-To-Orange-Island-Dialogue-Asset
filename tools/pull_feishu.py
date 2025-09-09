"""
 —  拉取飞书多维表格 → 逐表生成 *.bytes
"""
import os
import json
import requests
import tempfile
import flatbuffers
from export_dialog import convert_table_to_bytes   # ← 把转换逻辑拆出去
import hashlib 

APP_ID     = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
APP_TOKEN  = os.getenv("FEISHU_APP_TOKEN")
BASE_DIR   = "feishu_tables"

def table_hash(records):
    """对 records 按固定顺序算哈希"""
    # 只取会变动的字段，排除 id/revision
    core = [
        {k: v for k, v in r["fields"].items() if k not in {"id", "revision"}}
        for r in sorted(records, key=lambda x: x["id"])
    ]
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
 
# ------------------------------------------------------------------
# 1. 拿 token
token = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}
).json()["tenant_access_token"]
headers = {"Authorization": f"Bearer {token}"}

# ------------------------------------------------------------------
# 2. 枚举所有表
tables = requests.get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables",
    headers=headers
).json()["data"]["items"]

os.makedirs(BASE_DIR, exist_ok=True)

# ------------------------------------------------------------------
# 3. 逐表处理
for tbl in tables:
    table_id   = tbl["table_id"]
    table_name = tbl["name"]
    prefix     = table_name.split("_", 1)[0] if "_" in table_name else "uncategorized"
    out_dir    = os.path.join(BASE_DIR, prefix)
    os.makedirs(out_dir, exist_ok=True)

    # 拉全量记录
    records = requests.get(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records",
        headers=headers,
        params={"page_size": 500}
    ).json()["data"]["items"]

    # 计算哈希
    new_hash = table_hash(records)
    hash_path = os.path.join(out_dir, f".{table_name}.hash")
    old_hash  = open(hash_path).read().strip() if os.path.exists(hash_path) else ""

    if new_hash == old_hash:
        print(f"⏭  {table_name} 无变更")
        continue

    # 有变更
    bytes_path = os.path.join(out_dir, f"{table_name}.bytes")
    convert_table_to_bytes(records, bytes_path)
    with open(hash_path, "w") as f:
        f.write(new_hash)
    print(f"✅ {bytes_path} 已更新")
