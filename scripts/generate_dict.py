#!/usr/bin/env python3
"""
采集沪深北 A 股、港股、台湾股票名称，生成 RIME 格式词库
输出文件：dict/stock.dict.yaml

数据来源：
  - 沪深北 A 股：akshare stock_info_a_code_name（新浪，含沪深京三所）
                 备用：stock_zh_a_spot（新浪实时行情）
  - 港股：      akshare stock_hk_spot（新浪港股实时行情）
                 备用：stock_hk_spot_em（东方财富港股实时行情）
  - 台湾股票：  台湾证交所（TWSE）+ 柜买中心（TPEx）官方 JSON API
"""

import os
import time
import datetime
import requests
import akshare as ak
import opencc
from pypinyin import lazy_pinyin, Style

# 繁体 → 简体转换器
CC = opencc.OpenCC("t2s")

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "dict", "stock.dict.yaml")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

HEADER_TEMPLATE = """\
# Rime dictionary
# encoding: utf-8
#
# 股票名称词库（沪深北A股 + 港股 + 台湾上市/上柜）
# 数据来源：新浪财经 / 东方财富 / 台湾证交所 / 柜买中心
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


def to_simplified(names: list[str]) -> list[str]:
    """繁体中文转简体"""
    return [CC.convert(n) for n in names]


def fetch_cn_stocks() -> list[str]:
    """沪深北 A 股：新浪财经接口，含沪深京三所"""
    print("正在获取沪深北 A 股...")

    # 主接口：轻量代码名称表
    try:
        df = ak.stock_info_a_code_name()
        col = "name" if "name" in df.columns else df.columns[1]
        names = df[col].dropna().tolist()
        if len(names) > 100:
            print(f"  [主接口] 沪深北 A 股：{len(names)} 条")
            return names
        print(f"  [主接口] 数据过少（{len(names)}条），尝试备用...")
    except Exception as e:
        print(f"  [主接口] 失败：{e}，尝试备用...")

    time.sleep(2)

    # 备用接口：新浪实时行情
    try:
        df = ak.stock_zh_a_spot()
        col = "名称" if "名称" in df.columns else df.columns[1]
        names = df[col].dropna().tolist()
        print(f"  [备用接口] 沪深北 A 股：{len(names)} 条")
        return names
    except Exception as e:
        print(f"  [备用接口] 失败：{e}")
        return []


def fetch_hk_stocks() -> list[str]:
    """
    港股：从港交所官方「可进行卖空的指定证券名单」CSV 获取股份简称
    URL 格式：https://www.hkex.com.hk/-/media/HKEX-Market/Services/Trading/
              Securities/Securities-Lists/Designated-Securities-Eligible-for-
              Short-Selling/ds_list{YYYYMMDD}_c.csv
    该文件每个交易日更新，回溯最近 10 个自然日找到最新文件
    """
    print("正在获取港股（港交所官方名单）...")
    base_url = (
        "https://www.hkex.com.hk/-/media/HKEX-Market/Services/Trading/"
        "Securities/Securities-Lists/Designated-Securities-Eligible-for-"
        "Short-Selling/ds_list{date}_c.csv"
    )

    today = datetime.date.today()
    for delta in range(10):
        date = today - datetime.timedelta(days=delta)
        url = base_url.format(date=date.strftime("%Y%m%d"))
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                continue
            # 解码：港交所 CSV 使用 UTF-8 with BOM
            text = resp.content.decode("utf-8-sig")
            lines = text.splitlines()
            names = []
            for line in lines:
                parts = line.split(",")
                # 格式：数目,股份代号,股份简称,交易货币,种类,...
                if len(parts) >= 3:
                    name = parts[2].strip().strip('"')
                    # 跳过表头和非中文行
                    if name and any('\u4e00' <= c <= '\u9fff' for c in name):
                        names.append(name)
            if len(names) > 100:
                names = to_simplified(names)
                print(f"  港股（{date}）：{len(names)} 条")
                return names
        except Exception as e:
            print(f"  [跳过] {date}：{e}")
            continue

    print("  [警告] 港股所有日期均获取失败")
    return []


def fetch_twse_listed() -> list[str]:
    """台湾证交所上市股票（TWSE 官方 API）"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        names = [item.get("Name", "").strip() for item in data if item.get("Name")]
        names = [n for n in names if any('\u4e00' <= c <= '\u9fff' for c in n)]
        names = to_simplified(names)
        print(f"  台湾证交所上市：{len(names)} 条")
        return names
    except Exception as e:
        print(f"  [警告] 台湾证交所上市获取失败：{e}")

    # 备用：证交所公司基本资料 API
    try:
        url2 = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
        resp = requests.get(url2, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        names = [item.get("公司简称", item.get("公司名称", "")).strip() for item in data]
        names = [n for n in names if n and any('\u4e00' <= c <= '\u9fff' for c in n)]
        names = to_simplified(names)
        print(f"  台湾证交所上市（备用）：{len(names)} 条")
        return names
    except Exception as e:
        print(f"  [警告] 台湾证交所备用接口失败：{e}")
        return []


def fetch_tpex_otc() -> list[str]:
    """台湾柜买中心上柜股票（TPEx 官方 API）"""
    url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        names = [item.get("CompanyName", "").strip() for item in data if item.get("CompanyName")]
        names = [n for n in names if any('\u4e00' <= c <= '\u9fff' for c in n)]
        names = to_simplified(names)
        print(f"  台湾柜买中心上柜：{len(names)} 条")
        return names
    except Exception as e:
        print(f"  [警告] 台湾柜买中心获取失败：{e}")
        return []


def fetch_tw_stocks() -> list[str]:
    """台湾股票：上市 + 上柜"""
    print("正在获取台湾股票...")
    names = []
    names.extend(fetch_twse_listed())
    time.sleep(1)
    names.extend(fetch_tpex_otc())
    return names


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
    all_names.extend(fetch_hk_stocks())
    all_names.extend(fetch_tw_stocks())

    filtered = filter_names(all_names)
    print(f"\n全部去重过滤后共 {len(filtered)} 条")

    if len(filtered) == 0:
        print("错误：所有接口均未返回数据，请检查网络或接口状态")
        raise SystemExit(1)

    generate_dict(filtered)

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "dict", "stock.dict.yaml")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

HEADER_TEMPLATE = """\
# Rime dictionary
# encoding: utf-8
#
# 股票名称词库（沪深北A股 + 台湾上市/上柜）
# 数据来源：新浪财经 / 台湾证交所 / 柜买中心
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
    """沪深北 A 股：新浪财经接口，含沪深京三所"""
    print("正在获取沪深北 A 股...")

    # 主接口：轻量代码名称表
    try:
        df = ak.stock_info_a_code_name()
        col = "name" if "name" in df.columns else df.columns[1]
        names = df[col].dropna().tolist()
        if len(names) > 100:
            print(f"  [主接口] 沪深北 A 股：{len(names)} 条")
            return names
        print(f"  [主接口] 数据过少（{len(names)}条），尝试备用...")
    except Exception as e:
        print(f"  [主接口] 失败：{e}，尝试备用...")

    time.sleep(2)

    # 备用接口：新浪实时行情
    try:
        df = ak.stock_zh_a_spot()
        col = "名称" if "名称" in df.columns else df.columns[1]
        names = df[col].dropna().tolist()
        print(f"  [备用接口] 沪深北 A 股：{len(names)} 条")
        return names
    except Exception as e:
        print(f"  [备用接口] 失败：{e}")
        return []


def to_simplified(names: list[str]) -> list[str]:
    """繁体中文转简体"""
    return [CC.convert(n) for n in names]


def fetch_twse_listed() -> list[str]:
    """台湾证交所上市股票（TWSE 官方 API）"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        names = [item.get("Name", "").strip() for item in data if item.get("Name")]
        names = [n for n in names if any('\u4e00' <= c <= '\u9fff' for c in n)]
        names = to_simplified(names)
        print(f"  台湾证交所上市：{len(names)} 条")
        return names
    except Exception as e:
        print(f"  [警告] 台湾证交所上市获取失败：{e}")

    # 备用：证交所公司基本资料 API
    try:
        url2 = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
        resp = requests.get(url2, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        names = [item.get("公司简称", item.get("公司名称", "")).strip() for item in data]
        names = [n for n in names if n and any('\u4e00' <= c <= '\u9fff' for c in n)]
        names = to_simplified(names)
        print(f"  台湾证交所上市（备用）：{len(names)} 条")
        return names
    except Exception as e:
        print(f"  [警告] 台湾证交所备用接口失败：{e}")
        return []


def fetch_tpex_otc() -> list[str]:
    """台湾柜买中心上柜股票（TPEx 官方 API）"""
    url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        names = [item.get("CompanyName", "").strip() for item in data if item.get("CompanyName")]
        names = [n for n in names if any('\u4e00' <= c <= '\u9fff' for c in n)]
        names = to_simplified(names)
        print(f"  台湾柜买中心上柜：{len(names)} 条")
        return names
    except Exception as e:
        print(f"  [警告] 台湾柜买中心获取失败：{e}")
        return []


def fetch_tw_stocks() -> list[str]:
    """台湾股票：上市 + 上柜"""
    print("正在获取台湾股票...")
    names = []
    names.extend(fetch_twse_listed())
    time.sleep(1)
    names.extend(fetch_tpex_otc())
    return names


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
