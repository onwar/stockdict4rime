#!/usr/bin/env python3
"""
采集沪深 A 股、台湾、美股股票名称，生成 RIME 格式词库
输出文件：dict/stock.dict.yaml
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
# 数据来源：东方财富 / akshare
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
    """沪深 A 股：使用东方财富接口，对境外网络友好"""
    print("正在获取沪深 A 股（东方财富）...")
    try:
        df = ak.stock_zh_a_spot_em()
        col = "名称" if "名称" in df.columns else df.columns[1]
        names = df[col].dropna().tolist()
        print(f"  沪深 A 股：{len(names)} 条")
        return names
    except Exception as e:
        print(f"  [警告] 沪深 A 股获取失败：{e}")
        return []


def fetch_tw_stocks() -> list[str]:
    """台湾股票：上市 + 上柜"""
    print("正在获取台湾股票...")
    names = []
    try:
        df_list = ak.stock_info_tw_code()
        col = "公司简称" if "公司简称" in df_list.columns else df_list.columns[1]
        n = df_list[col].dropna().tolist()
        names.extend(n)
        print(f"  台湾上市：{len(n)} 条")
    except Exception as e:
        print(f"  [警告] 台湾上市获取失败：{e}")

    time.sleep(1)

    try:
        df_otc = ak.stock_info_tw_code(indicator="上柜")
        col = "公司简称" if "公司简称" in df_otc.columns else df_otc.columns[1]
        n = df_otc[col].dropna().tolist()
        names.extend(n)
        print(f"  台湾上柜：{len(n)} 条")
    except Exception as e:
        print(f"  [警告] 台湾上柜获取失败：{e}")

    return names


def fetch_us_stocks() -> list[str]:
    """美股：通过东方财富接口获取"""
    print("正在获取美股...")
    try:
        df = ak.stock_us_spot_em()
        col = "名称" if "名称" in df.columns else df.columns[1]
        names = df[col].dropna().tolist()
        print(f"  美股：{len(names)} 条")
        return names
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
