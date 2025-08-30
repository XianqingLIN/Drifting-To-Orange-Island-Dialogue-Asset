import os, re, json, flatbuffers
from DialoguePy import DialogueFlowchart, DialogueBlock, Command

# ---------------- 解析 DSL ----------------
DSL_REGEX = {
    "Say":  re.compile(r'^Say\s+"(.*?)"(?:\s*\[角色:(.*?)\])?$'),
    "If":   re.compile(r'^If\s+(.+?)$'),
    "EndIf":re.compile(r'^EndIf$'),
    # 可按需继续扩展 Menu / SetVariable / Call 等
}

def parse_dsl(content: str):
    """
    把多行 DSL 转成 [{'type':'Say','params':[...]}, ...]
    """
    commands = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue
        for cmd_type, pattern in DSL_REGEX.items():
            m = pattern.match(line)
            if m:
                params = list(m.groups())
                commands.append({"type": cmd_type, "params": params})
                break
    return commands

# ---------------- FlatBuffers 构建 ----------------
def _create_str_vector(builder, str_list):
    """一次性把字符串池写进 FlatBuffers"""
    offsets = [builder.CreateString(s) for s in str_list]
    DialogueFlowchart.StartParamsVector(builder, len(offsets))
    for o in reversed(offsets):
        builder.PrependUOffsetTRelative(o)
    return builder.EndVector()

def convert_table_to_bytes(records: list, out_path: str):
    """
    records: 飞书返回的 items
    out_path: 输出的 *.bytes
    """
    # 1. 把飞书记录变成 {BlockName: [Command, ...]}
    blocks_data = {}
    for rec in records:
        fields = rec.get("fields", {})
        block_name = fields.get("BlockName", "Unnamed")
        content    = fields.get("Content", "")
        blocks_data[block_name] = parse_dsl(content)

    # 2. 收集所有字符串做池
    str_pool = []
    def push(s):
        if s not in str_pool:
            str_pool.append(s)
        return str_pool.index(s)

    builder = flatbuffers.Builder(1024)

    # 3. 构建 Command 列表
    cmd_offsets = []
    for params in str_pool:   # 先预创建字符串
        [builder.CreateString(s) for s in str_pool]

    block_offsets = []
    for block_name, cmds in blocks_data.items():
        cmd_objs = []
        for cmd in cmds:
            type_off  = builder.CreateString(cmd["type"])
            param_offs = [builder.CreateString(p or "") for p in cmd["params"]]
            Command.StartParamsVector(builder, len(param_offs))
            for po in reversed(param_offs):
                builder.PrependUOffsetTRelative(po)
            params_vec = builder.EndVector()

            Command.Start(builder)
            Command.AddCommandType(builder, type_off)
            Command.AddParams(builder, params_vec)
            cmd_objs.append(Command.End(builder))

        DialogueBlock.StartCommandsVector(builder, len(cmd_objs))
        for co in reversed(cmd_objs):
            builder.PrependUOffsetTRelative(co)
        cmds_vec = builder.EndVector()

        name_off = builder.CreateString(block_name)
        DialogueBlock.Start(builder)
        DialogueBlock.AddBlockName(builder, name_off)
        DialogueBlock.AddCommands(builder, cmds_vec)
        block_offsets.append(DialogueBlock.End(builder))

    # 4. 构建 Flowchart
    DialogueFlowchart.StartBlocksVector(builder, len(block_offsets))
    for bo in reversed(block_offsets):
        builder.PrependUOffsetTRelative(bo)
    blocks_vec = builder.EndVector()

    DialogueFlowchart.Start(builder)
    DialogueFlowchart.AddChartName(builder, builder.CreateString("RuntimeChart"))
    DialogueFlowchart.AddBlocks(builder, blocks_vec)
    root = DialogueFlowchart.End(builder)
    builder.Finish(root)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(builder.Output())
