#!/usr/bin/env python3
"""
采集沪深北 A 股、台湾股票名称，生成 RIME 格式词库
输出文件：dict/stock.dict.yaml

数据来源：
  - 沪深北 A 股：stock_info_a_code_name（新浪，含沪深京三所，境外可访问）
                 备用：stock_zh_a_spot（新浪实时行情，含名称列）
  - 台湾股票：  stock_tw_spot_em（东方财富台股行情）
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
# 股票名称词库（沪深北A股 + 台湾）
# 数据来源：新浪财经 / 东方财富 via akshare
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
    """
    沪深北 A 股，优先用 stock_info_a_code_name（轻量，仅返回代码+名称）
    失败则备用 stock_zh_a_spot（新浪实时行情，含名称列）
    """
    print("正在获取沪深北 A 股...")

    # 主接口：轻量代码名称表，含沪深京三所
    try:
        df = ak.stock_info_a_code_name()
        # 列名为 'code' 和 'name'
        col = "name" if "name" in df.columns else df.columns[1]
        names = df[col].dropna().tolist()
        if len(names) > 100:
            print(f"  [主接口] 沪深北 A 股：{len(names)} 条")
            return names
        print(f"  [主接口] 返回数据过少（{len(names)}条），尝试备用接口...")
    except Exception as e:
        print(f"  [主接口] 失败：{e}，尝试备用接口...")

    time.sleep(2)

    # 备用接口：新浪实时行情（含沪深京全部 A 股）
    try:
        df = ak.stock_zh_a_spot()
        col = "名称" if "名称" in df.columns else df.columns[1]
        names = df[col].dropna().tolist()
        print(f"  [备用接口] 沪深北 A 股：{len(names)} 条")
        return names
    except Exception as e:
        print(f"  [备用接口] 失败：{e}")
        return []


def fetch_tw_stocks() -> list[str]:
    """台湾股票：东方财富台股实时行情"""
    print("正在获取台湾股票...")
    try:
        df = ak.stock_tw_spot_em()
        # 列名通常为 '名称' 或第2列
        col = "名称" if "名称" in df.columns else df.columns[1]
        names = df[col].dropna().tolist()
        # 过滤纯英文条目
        names = [n for n in names if any('\u4e00' <= c <= '\u9fff' for c in str(n))]
        print(f"  台湾股票（含中文名）：{len(names)} 条")
        return names
    except Exception as e:
        print(f"  [警告] 台湾股票获取失败：{e}")
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

    filtered = filter_names(all_names)
    print(f"\n全部去重过滤后共 {len(filtered)} 条")

    if len(filtered) == 0:
        print("错误：所有接口均未返回数据，请检查网络或接口状态")
        raise SystemExit(1)

    generate_dict(filtered)
