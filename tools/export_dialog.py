import flatbuffers
from Dialog import DialogBlob, Node, Option

# ------------------------------------------------
def _push_str(builder, str_pool, s: str) -> int:
    if s not in str_pool:
        str_pool.append(s)
    return str_pool.index(s)

def _build_option(builder, str_pool, opt):
    text_id = _push_str(builder, str_pool, opt["textKey"])
    cond_blob = builder.CreateByteVector(opt.get("condition", "").encode("utf-8"))
    evt_blob  = builder.CreateByteVector(opt.get("event", "").encode("utf-8"))
    Option.Start(builder)
    Option.AddTextId(builder, text_id)
    Option.AddTargetIdx(builder, opt.get("target_idx", -1))
    Option.AddCondLen(builder, len(opt.get("condition", "")))
    Option.AddCondBlob(builder, cond_blob)
    Option.AddEvtLen(builder, len(opt.get("event", "")))
    Option.AddEvtBlob(builder, evt_blob)
    return Option.End(builder)

def _build_node(builder, str_pool, node):
    text_id = _push_str(builder, str_pool, node["textKey"])
    opts = [_build_option(builder, str_pool, o) for o in node.get("options", [])]
    Node.StartOptionsVector(builder, len(opts))
    for o in reversed(opts):
        builder.PrependUOffsetTRelative(o)
    opts_vec = builder.EndVector()
    Node.Start(builder)
    Node.AddTextId(builder, text_id)
    Node.AddCharacter(builder, node.get("characterKey", 0))
    Node.AddFlags(builder, node.get("flags", 0))
    Node.AddNextIdx(builder, node.get("next_idx", -1))
    Node.AddOptions(builder, opts_vec)
    return Node.End(builder)

# ------------------------------------------------
def convert_table_to_bytes(records: list, out_path: str):
    """
    records: 飞书接口返回的 items 数组
    out_path: 生成的 .bytes 文件路径
    """
    # 把飞书行数据转成我们需要的 dict 格式（根据你真实字段名调整）
    data = []
    for row in records:
        fields = row.get("fields", {})
        data.append({
            "textKey"     : fields.get("textKey", ""),
            "characterKey": int(fields.get("characterKey", 0)),
            "flags"       : int(fields.get("flags", 0)),
            "next_idx"    : int(fields.get("next_idx", -1)),
            "options"     : fields.get("options", [])
        })

    builder = flatbuffers.Builder(1024)
    str_pool = []
    nodes = [_build_node(builder, str_pool, n) for n in data]
    Node.StartNodesVector(builder, len(nodes))
    for n in reversed(nodes):
        builder.PrependUOffsetTRelative(n)
    nodes_vec = builder.EndVector()

    strings = [builder.CreateString(s) for s in str_pool]
    DialogBlob.StartStringsVector(builder, len(strings))
    for s in reversed(strings):
        builder.PrependUOffsetTRelative(s)
    strings_vec = builder.EndVector()

    DialogBlob.Start(builder)
    DialogBlob.AddNodes(builder, nodes_vec)
    DialogBlob.AddStrings(builder, strings_vec)
    root = DialogBlob.End(builder)
    builder.Finish(root)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(builder.Output())
