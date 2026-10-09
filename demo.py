#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""青禾报销助手_ybw · demo 一键演示。

流程：生成示例数电发票 -> 提取 -> 归档查重 -> 合规校验 -> 生成报销单(HTML)+查重台账(CSV)。
纯标准库，无需安装任何第三方包；直接 `python demo.py` 即可运行。
"""
import os
import sys
import json
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from src.extract import extract_from_file, InvoiceRecord
from src.archive import archive_invoices, write_ledger_csv
from src.compliance import load_policy, check_all
from src.packet import generate_packet
from src.cn_amount import num_to_cn_capital

INBOX = os.path.join(ROOT, "data", "inbox")
ARCHIVE = os.path.join(ROOT, "data", "archive")
OUTPUT = os.path.join(ROOT, "data", "output")
POLICY = os.path.join(ROOT, "config", "policy.json")


# ---------- 1. 生成示例数电发票（demo 自带样例，真实使用时替换为你的发票）----------
SAMPLES = [
    dict(no="24417000000123456789", date="2026-09-10", seller="老街红烧饭店", category="餐饮",
         total=320.00, tax=9.06, rate="3%", buyer="青禾科技有限公司"),
    dict(no="24417000000123456790", date="2026-09-12", seller="滴滴出行科技有限公司", category="交通",
         total=158.00, tax=4.48, rate="3%", buyer="青禾科技有限公司"),
    dict(no="24417000000123456791", date="2026-09-15", seller="云顶大酒楼", category="餐饮",
         total=880.00, tax=24.95, rate="3%", buyer="青禾科技有限公司"),
    # 第 4 张与第 1 张发票号相同 -> 用于演示查重
    dict(no="24417000000123456789", date="2026-09-10", seller="老街红烧饭店", category="餐饮",
         total=320.00, tax=9.06, rate="3%", buyer="青禾科技有限公司"),
]


def gen_sample_xml(spec, path):
    amount = round(spec["total"] - spec["tax"], 2)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice>
  <InvoiceNo>{spec['no']}</InvoiceNo>
  <InvoiceDate>{spec['date']}</InvoiceDate>
  <BuyerName>{spec['buyer']}</BuyerName>
  <SellerName>{spec['seller']}</SellerName>
  <TaxRate>{spec['rate']}</TaxRate>
  <Amount>{amount:.2f}</Amount>
  <Tax>{spec['tax']:.2f}</Tax>
  <TotalAmount>{spec['total']:.2f}</TotalAmount>
  <CNTotalAmount>{num_to_cn_capital(spec['total'])}</CNTotalAmount>
</Invoice>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)


def auto_classify(rec):
    """业务事实初步归类（最终由业务事实核对人确认）。"""
    s = (rec.seller_name or "") + (rec.notes and " ".join(rec.notes) or "")
    if any(k in s for k in ("餐厅", "酒楼", "饭店", "餐饮", "食")):
        return "餐饮"
    if any(k in s for k in ("滴滴", "出行", "出租", "高铁", "航空", "地铁", "交通")):
        return "交通"
    if any(k in s for k in ("酒店", "宾馆", "住宿", "民宿")):
        return "住宿"
    return "办公"


def main():
    os.makedirs(INBOX, exist_ok=True)
    os.makedirs(ARCHIVE, exist_ok=True)
    os.makedirs(OUTPUT, exist_ok=True)

    # 生成示例发票（仅当 inbox 为空时）
    existing = [f for f in os.listdir(INBOX) if f.lower().endswith(".xml")]
    if not existing:
        for i, spec in enumerate(SAMPLES, 1):
            gen_sample_xml(spec, os.path.join(INBOX, f"sample_{i}.xml"))
        print(f"[demo] 已生成 {len(SAMPLES)} 张示例数电发票到 data/inbox/")
    else:
        print(f"[demo] 检测到 data/inbox/ 已有 {len(existing)} 张发票，跳过生成")

    # 2. 提取
    records = []
    for fn in sorted(os.listdir(INBOX)):
        if not fn.lower().endswith((".xml", ".pdf")):
            continue
        path = os.path.join(INBOX, fn)
        rec = extract_from_file(path)
        rec.source_path = path
        rec.category = auto_classify(rec)
        records.append(rec)
    print(f"[demo] 已提取 {len(records)} 张发票")

    # 3. 归档 + 查重台账
    archived, ledger = archive_invoices(records, ARCHIVE)
    ledger_path = os.path.join(OUTPUT, "发票查重台账.csv")
    write_ledger_csv(ledger, ledger_path)
    print(f"[demo] 台账已写出：{ledger_path}")

    # 4. 合规校验
    policy = load_policy(POLICY)
    report = check_all(records, policy)

    # 5. 生成报销单
    meta = dict(
        org=policy.get("org_name", "青禾科技有限公司"),
        applicant="张三",
        department="研发部",
        period="2026-09",
        purpose="9 月差旅及业务招待费",
        created=datetime.now().strftime("%Y-%m-%d"),
    )
    packet_path = os.path.join(OUTPUT, "报销单.html")
    generate_packet(meta, records, report, packet_path)
    print(f"[demo] 报销单已生成：{packet_path}")

    # 控制台汇总
    total = sum(r.total_amount for r in records)
    dups = [r["发票号"] for r in ledger if r["是否重复"] == "是"]
    warns = sum(len(c["issues"]) for c in report)
    print("\n========== 青禾报销助手_ybw · 运行结果 ==========")
    print(f"  报销人：{meta['applicant']}（{meta['department']}）  所属期：{meta['period']}")
    print(f"  票据数：{len(records)} 张   合计：¥{total:.2f}（{num_to_cn_capital(total)}）")
    print(f"  重复发票号：{', '.join(dups) if dups else '无'}")
    print(f"  合规风险项：{warns} 项")
    for c in report:
        flag = "⚠" if c["issues"] else "✅"
        print(f"    {flag} {c['category']:>4} {c['invoice_no']} ¥{c['total']:.2f}")
    print("================================================")
    print("  下一步：用浏览器打开 data/output/报销单.html 打印/另存 PDF；")
    print("         用 Excel 打开 data/output/发票查重台账.csv 留存备查。")


if __name__ == "__main__":
    main()
