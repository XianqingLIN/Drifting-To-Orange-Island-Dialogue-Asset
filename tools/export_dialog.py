#!/usr/bin/env python3
"""
把飞书单行记录变成 DialogueFlowchart.bytes
"""
import os
import re
import flatbuffers
from DialoguePy import DialogueFlowchart, DialogueBlock, Command

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
    # 1. 收集 Block → Commands
    blocks = {}
    for rec in records:
        fields = rec.get("fields", {})
        block_name = fields.get("BlockName", "Unnamed")
        content    = fields.get("Content", "")
        blocks[block_name] = parse_dsl(content)

    # 2. 字符串池
    str_pool = []
    def push(s):
        if s not in str_pool:
            str_pool.append(s)
        return builder.CreateString(s)

    builder = flatbuffers.Builder(1024)

    # 3. 构建 Command
    cmd_offsets = []
    for block_name, cmds in blocks.items():
        for cmd in cmds:
            type_off = push(cmd["type"])
            param_offs = [push(p) for p in cmd["params"]]

            CommandStartParametersVector(builder, len(param_offs))
            for po in reversed(param_offs):
                builder.PrependUOffsetTRelative(po)
            params_vec = builder.EndVector()

            CommandStart(builder)
            CommandAddCommandType(builder, type_off)
            CommandAddParameters(builder, params_vec)
            cmd_offsets.append(CommandEnd(builder))

    # 4. 构建 DialogueBlock
    block_offsets = []
    for block_name, cmds in blocks.items():
        cmds_in_block = len(cmds)
        DialogueBlockStartCommandsVector(builder, cmds_in_block)
        for co in reversed(cmd_offsets[-cmds_in_block:]):
            builder.PrependUOffsetTRelative(co)
        cmds_vec = builder.EndVector()

        name_off = push(block_name)
        DialogueBlockStart(builder)
        DialogueBlockAddBlockName(builder, name_off)
        DialogueBlockAddCommands(builder, cmds_vec)
        block_offsets.append(DialogueBlockEnd(builder))

    # 5. 构建 DialogueFlowchart
    DialogueFlowchartStartBlocksVector(builder, len(block_offsets))
    for bo in reversed(block_offsets):
        builder.PrependUOffsetTRelative(bo)
    blocks_vec = builder.EndVector()

    DialogueFlowchartStart(builder)
    DialogueFlowchartAddChartName(builder, push("RuntimeChart"))
    DialogueFlowchartAddBlocks(builder, blocks_vec)
    root = DialogueFlowchartEnd(builder)
    builder.Finish(root)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(builder.Output())

# 允许独立运行测试
if __name__ == "__main__":
    test = [{"fields":{"BlockName":"test_block","Content":'Say "你好" [角色:Player]\nIf HasItem(5)\nSay "有钥匙" [角色:NPC]\nEndIf'}}]
    convert_table_to_bytes(test, "test.bytes")
