#!/usr/bin/env python3
"""
采集沪深 A 股股票名称，生成 RIME 格式词库 dict/a_stock.dict.yaml
"""

import os
import datetime
import akshare as ak
from pypinyin import lazy_pinyin, Style

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "dict", "a_stock.dict.yaml")

HEADER_TEMPLATE = """\
# Rime dictionary
# encoding: utf-8
#
# A 股股票名称词库
# 数据来源：东方财富（通过 akshare）
# 更新时间：{date}
# 股票数量：{count}
#
# 使用方法：在 rime-ice 的 cn_dicts/ 目录下放置此文件
# 并在 rime_ice.dict.yaml 的 import_tables 中添加：
#   - cn_dicts/a_stock
#
---
name: a_stock
version: "{date}"
sort: by_weight
...

"""

def get_pinyin(name: str) -> str:
    """将股票名称转换为拼音，以空格分隔每个字的拼音"""
    return " ".join(lazy_pinyin(name, style=Style.NORMAL))

def fetch_stocks() -> list[tuple[str, str]]:
    """获取沪深 A 股全部股票名称，返回 (名称, 拼音) 列表"""
    print("正在获取沪市 A 股...")
    sh = ak.stock_info_sh_name_code(symbol="主板A股")
    print(f"  沪市主板：{len(sh)} 条")

    sh_star = ak.stock_info_sh_name_code(symbol="科创板")
    print(f"  科创板：{len(sh_star)} 条")

    print("正在获取深市 A 股...")
    sz = ak.stock_info_sz_name_code(indicator="A股列表")
    print(f"  深市 A 股：{len(sz)} 条")

    # 统一取股票名称列
    names = set()

    for df in [sh, sh_star]:
        col = "证券简称" if "证券简称" in df.columns else df.columns[1]
        names.update(df[col].dropna().tolist())

    col_sz = "证券简称" if "证券简称" in sz.columns else sz.columns[1]
    names.update(sz[col_sz].dropna().tolist())

    # 过滤掉明显无效的条目（含字母、纯数字、过短）
    filtered = []
    for name in sorted(names):
        name = str(name).strip()
        if len(name) < 2:
            continue
        if name.isdigit():
            continue
        filtered.append(name)

    print(f"去重过滤后共 {len(filtered)} 条股票名称")
    return filtered

def generate_dict(names: list[str]) -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    today = datetime.date.today().isoformat()
    lines = []

    for name in names:
        pinyin = get_pinyin(name)
        # 格式：词条\t拼音（以空格分隔）\t权重
        lines.append(f"{name}\t{pinyin}\t1")

    content = HEADER_TEMPLATE.format(date=today, count=len(lines))
    content += "\n".join(lines) + "\n"

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"词库已写入：{OUTPUT_PATH}（共 {len(lines)} 条）")

if __name__ == "__main__":
    names = fetch_stocks()
    generate_dict(names)
