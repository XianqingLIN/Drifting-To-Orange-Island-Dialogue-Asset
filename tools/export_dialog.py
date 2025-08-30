#!/usr/bin/env python3
"""
把飞书单行记录变成 DialogueFlowchart.bytes
"""
import os
import re
import flatbuffers
from DialoguePy import *

# ---------------- DSL 解析 ----------------
DSL_REGEX = {
    "Say":   re.compile(r'^Say\s+"(.*?)"(?:\s*\[角色:(.*?)\])?$'),
    "If":    re.compile(r'^If\s+(.+?)$'),
    "EndIf": re.compile(r'^EndIf$'),
}

def parse_dsl(content: str):
    """把多行 DSL 转成 [{'type':'Say','params':[...]}, ...]"""
    cmds = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue
        for cmd_type, pat in DSL_REGEX.items():
            m = pat.match(line)
            if m:
                params = [p or "" for p in m.groups()]
                cmds.append({"type": cmd_type, "params": params})
                break
    return cmds

# ---------------- FlatBuffers 构建 ----------------
def convert_table_to_bytes(records: list, out_path: str):
    """
    records: 飞书返回的 items
    out_path: 输出的 *.bytes
    """
    # 1. 飞书 → {BlockName: [Command, ...]}
    blocks_data = {}
    for rec in records:
        fields = rec.get("fields", {})
        block_name = fields.get("BlockName", "Unnamed")
        content = fields.get("Content", "")
        blocks_data[block_name] = parse_dsl(content)

    # 2. 收集所有字符串并一次性创建 offset
    str_pool = set()
    str_pool.add("RuntimeChart")
    for block_name, cmds in blocks_data.items():
        str_pool.add(block_name)
        for cmd in cmds:
            str_pool.add(cmd["type"])
            str_pool.update(cmd["params"])
    builder = flatbuffers.Builder(1024)
    str_offsets = {s: builder.CreateString(s) for s in str_pool}

    # 3. Command 对象
    cmd_offsets = []
    for cmds in blocks_data.values():
        for cmd in cmds:
            params = cmd["params"]
            CommandStartParametersVector(builder, len(params))
            for p in reversed(params):
                builder.PrependUOffsetTRelative(str_offsets[p])
            params_vec = builder.EndVector()

            CommandStart(builder)
            CommandAddCommandType(builder, str_offsets[cmd["type"]])
            CommandAddParameters(builder, params_vec)
            cmd_offsets.append(CommandEnd(builder))

    # 4. DialogueBlock 对象
    block_offsets = []
    cmd_idx = 0
    for block_name, cmds in blocks_data.items():
        n_cmds = len(cmds)
        DialogueBlockStartCommandsVector(builder, n_cmds)
        for i in range(n_cmds):
            builder.PrependUOffsetTRelative(cmd_offsets[cmd_idx + n_cmds - 1 - i])
        cmds_vec = builder.EndVector()
        cmd_idx += n_cmds

        DialogueBlockStart(builder)
        DialogueBlockAddBlockName(builder, str_offsets[block_name])
        DialogueBlockAddCommands(builder, cmds_vec)
        block_offsets.append(DialogueBlockEnd(builder))

    # 5. DialogueFlowchart 对象
    DialogueFlowchartStartBlocksVector(builder, len(block_offsets))
    for bo in reversed(block_offsets):
        builder.PrependUOffsetTRelative(bo)
    blocks_vec = builder.EndVector()

    DialogueFlowchartStart(builder)
    DialogueFlowchartAddChartName(builder, str_offsets["RuntimeChart"])
    DialogueFlowchartAddBlocks(builder, blocks_vec)
    root = DialogueFlowchartEnd(builder)
    builder.Finish(root)

    # 6. 写文件
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(builder.Output())
# 允许独立运行测试
if __name__ == "__main__":
    test = [{"fields":{"BlockName":"test_block","Content":'Say "你好" [角色:Player]\nIf HasItem(5)\nSay "有钥匙" [角色:NPC]\nEndIf'}}]
    convert_table_to_bytes(test, "test.bytes")
