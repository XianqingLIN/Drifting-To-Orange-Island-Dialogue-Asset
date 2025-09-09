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
REV_DIR    = "feishu_tables/.revision"          # 缓存目录

os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(REV_DIR, exist_ok=True)

def table_hash(records):
    """对 records 按固定顺序算哈希"""
    # 只取会变动的字段，排除 id/revision
    core = [
        {k: v for k, v in r["fields"].items() if k not in {"id", "revision"}}
        for r in sorted(records, key=lambda x: x["id"])
    ]
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
 
# ------------------------------------------------------------------
# 1. 拿 tenant_access_token
token_resp = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}
).json()
if token_resp.get("code") != 0:
    raise RuntimeError(f"get token fail: {token_resp}")
token = token_resp["tenant_access_token"]
headers = {"Authorization": f"Bearer {token}"}

# ------------------------------------------------------------------
# 2. 枚举所有表
tables_resp = requests.get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables",
    headers=headers
).json()
if tables_resp.get("code") != 0:
    raise RuntimeError(f"list tables fail: {tables_resp}")
tables = tables_resp["data"]["items"]

# ------------------------------------------------------------------
# 3. 逐表处理
for tbl in tables:
    table_id   = tbl["table_id"]
    table_name = tbl["name"]

    # 前缀分目录
    prefix  = table_name.split("_", 1)[0] if "_" in table_name else "uncategorized"
    out_dir = os.path.join(BASE_DIR, prefix)
    os.makedirs(out_dir, exist_ok=True)

    # 拉全量记录
    records_resp = requests.get(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records",
        headers=headers,
        params={"page_size": 500}
    ).json()
    if records_resp.get("code") != 0:
        print(f"⚠️  skip {table_name}: {records_resp}")
        continue
    records = records_resp["data"]["items"]
    print(records)
    # 4. 拼表级 revision 指纹 = 所有记录 revision 排序后哈希
    rev_list = sorted(r["revision"] for r in records)
    fingerprint = hashlib.sha256("\n".join(rev_list).encode()).hexdigest()

    # 5. 与本地缓存比对
    rev_file = os.path.join(REV_DIR, f"{table_name}.rev")
    old_fp   = open(rev_file).read().strip() if os.path.exists(rev_file) else ""

    if fingerprint == old_fp:
        print(f"⏭  {table_name} 无变更")
        continue

    # 6. 有变化 → 生成 .bytes + 更新缓存
    bytes_path = os.path.join(out_dir, f"{table_name}.bytes")
    convert_table_to_bytes(records, bytes_path)
    with open(rev_file, "w") as f:
        f.write(fingerprint)
    print(f"✅ {bytes_path} 已更新 / revision={fingerprint[:8]}")

print("全部表处理完成")
