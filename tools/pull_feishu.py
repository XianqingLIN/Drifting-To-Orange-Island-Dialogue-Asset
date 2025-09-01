"""
 —  拉取飞书多维表格 → 逐表生成 *.bytes
"""
import os
import json
import requests
import tempfile
import flatbuffers
from export_dialog import convert_table_to_bytes   # ← 把转换逻辑拆出去
from DialoguePy import DialogueFlowchart, DialogueBlock, Command

def load_and_parse_bytes(file_path: str):
    """
    加载并解析 .bytes 文件
    """
    # 读取 .bytes 文件
    with open(file_path, "rb") as f:
        bytes_data = f.read()

    # 解析 FlatBuffers 数据
    chart = DialogueFlowchart.GetRootAsDialogueFlowchart(flatbuffers.Builder().CreateBuffer(bytes_data))

    # 打印解析后的数据结构
    print(f"Chart Name: {chart.ChartName()}")
    print(f"Number of Blocks: {chart.BlocksLength()}")

    for i in range(chart.BlocksLength()):
        block = chart.Blocks(i).Value
        print(f"  Block Name: {block.BlockName()}")
        print(f"  Number of Commands: {block.CommandsLength()}")

        for j in range(block.CommandsLength()):
            cmd = block.Commands(j).Value
            print(f"    Command Type: {cmd.CommandType()}")
            print(f"    Number of Parameters: {cmd.ParametersLength()}")

            for k in range(cmd.ParametersLength()):
                param = cmd.Parameters(k)
                print(f"      Parameter {k}: {param}")
             
APP_ID     = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
APP_TOKEN  = os.getenv("FEISHU_APP_TOKEN")
BASE_DIR   = "feishu_tables"

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

    # 前缀 → 目录
    prefix = table_name.split("_", 1)[0] if "_" in table_name else "uncategorized"
    out_dir = os.path.join(BASE_DIR, prefix)
    os.makedirs(out_dir, exist_ok=True)

    # 拉记录
    records = requests.get(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records",
        headers=headers,
        params={"page_size": 500}
    ).json()["data"]["items"]

    # 直接转 bytes 并写入文件
    bytes_path = os.path.join(out_dir, f"{table_name}.bytes")
    convert_table_to_bytes(records, bytes_path)
    load_and_parse_bytes(bytes_path)
    print(f"✅ {bytes_path}")
