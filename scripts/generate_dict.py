#!/usr/bin/env python3
"""
采集沪深 A 股、台湾、美股股票名称，生成 RIME 格式词库
输出文件：dict/stock.dict.yaml

数据来源说明（均选用对境外 IP 友好的接口）：
  - 沪深 A 股：新浪财经 stock_info_a_code_name
  - 台湾股票：新浪财经 stock_tw_spot_em
  - 美股：新浪财经 get_us_stock_name
"""

import os
import time
import datetime
import akshare as ak
from pypinyin import lazy_pinyin, Style

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "dict", "stock.dict.yaml")

HEADER_TEMPLATE = """\
# Rime dictionary
# encoding: utf-8
#
# 股票名称词库（沪深A股 + 台湾 + 美股）
# 数据来源：新浪财经 / akshare
# 更新时间：{date}
# 股票数量：{count}
#
# 使用方法：在 rime-ice 的 cn_dicts/ 目录下放置此文件
# 并在 rime_ice.dict.yaml 的 import_tables 中添加：
#   - cn_dicts/stock
#
---
name: stock
version: "{date}"
sort: by_weight
...

"""


def get_pinyin(name: str) -> str:
    """将名称转换为拼音，以空格分隔"""
    return " ".join(lazy_pinyin(name, style=Style.NORMAL))


def filter_names(raw: list[str]) -> list[str]:
    """过滤无效条目：过短、纯数字、空白"""
    result = []
    for name in sorted(set(raw)):
        name = str(name).strip()
        if len(name) < 2:
            continue
        if name.isdigit():
            continue
        result.append(name)
    return result


def fetch_cn_stocks() -> list[str]:
    """沪深 A 股：新浪财经接口，返回全部 A 股代码和名称"""
    print("正在获取沪深 A 股（新浪财经）...")
    try:
        df = ak.stock_info_a_code_name()
        col = "name" if "name" in df.columns else df.columns[1]
        names = df[col].dropna().tolist()
        print(f"  沪深 A 股：{len(names)} 条")
        return names
    except Exception as e:
        print(f"  [警告] 沪深 A 股获取失败：{e}")
        return []


def fetch_tw_stocks() -> list[str]:
    """台湾股票：新浪财经台股实时行情接口"""
    print("正在获取台湾股票（新浪财经）...")
    try:
        df = ak.stock_tw_spot_em()
        col = "名称" if "名称" in df.columns else df.columns[1]
        names = df[col].dropna().tolist()
        print(f"  台湾股票：{len(names)} 条")
        return names
    except Exception as e:
        print(f"  [警告] 台湾股票获取失败：{e}")
        return []


def fetch_us_stocks() -> list[str]:
    """美股：新浪财经接口，返回全部美股代码和名称"""
    print("正在获取美股（新浪财经）...")
    try:
        df = ak.get_us_stock_name()
        # 列名可能是 'name' 或中文
        if "name" in df.columns:
            col = "name"
        elif "名称" in df.columns:
            col = "名称"
        else:
            col = df.columns[1]
        names = df[col].dropna().tolist()
        # 过滤纯英文（只保留含中文字符的名称，减少词库噪音）
        cn_names = [n for n in names if any('\u4e00' <= c <= '\u9fff' for c in str(n))]
        print(f"  美股总计：{len(names)} 条，其中含中文名称：{len(cn_names)} 条")
        return cn_names
    except Exception as e:
        print(f"  [警告] 美股获取失败：{e}")
        return []


def generate_dict(names: list[str]) -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    today = datetime.date.today().isoformat()
    lines = []

    for name in names:
        pinyin = get_pinyin(name)
        lines.append(f"{name}\t{pinyin}\t1")

    content = HEADER_TEMPLATE.format(date=today, count=len(lines))
    content += "\n".join(lines) + "\n"

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n词库已写入：{OUTPUT_PATH}（共 {len(lines)} 条）")


if __name__ == "__main__":
    all_names: list[str] = []

    all_names.extend(fetch_cn_stocks())
    all_names.extend(fetch_tw_stocks())
    all_names.extend(fetch_us_stocks())

    filtered = filter_names(all_names)
    print(f"\n全部去重过滤后共 {len(filtered)} 条")

    generate_dict(filtered)
