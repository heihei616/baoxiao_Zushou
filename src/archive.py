"""归档与查重模块（demo 版，纯标准库）。

- 规范命名：日期_收支_科目_对方_金额CNY_票号尾8位
- 按开票月分文件夹归档
- 生成发票查重台账 CSV（按发票号标记重复）
"""
import os
import csv
import shutil
from datetime import datetime


def _safe(name, limit=20):
    name = (name or "").replace("/", "／").replace("\\", "＿").strip()
    return name[:limit]


def build_filename(rec, category="其他"):
    d = (rec.invoice_date or "").replace("-", "") or "00000000"
    flow = "出"  # 报销为支出
    counterpart = _safe(rec.seller_name or "未知对方")
    amt = f"{rec.total_amount:.2f}CNY" if rec.total_amount else "0.00CNY"
    tail = (rec.invoice_no or "00000000")[-8:]
    return f"{d}_{flow}_{category}_{counterpart}_{amt}_{tail}.pdf"


def archive_invoices(records, archive_root):
    """将记录归档，返回 (归档明细列表, 台账行列表)。"""
    archived = []
    ledger_rows = []
    seen = {}
    for rec in records:
        month = (rec.invoice_date or "")[:7].replace("-", "") or "unknown"
        month_dir = os.path.join(archive_root, month)
        os.makedirs(month_dir, exist_ok=True)
        fname = build_filename(rec, rec.category or "其他")
        dest = os.path.join(month_dir, fname)
        # 不移动原文件，仅复制（demo 留痕）
        src = getattr(rec, "source_path", None)
        if src and os.path.exists(src):
            shutil.copy2(src, dest)
        dup = rec.invoice_no in seen
        if rec.invoice_no:
            seen.setdefault(rec.invoice_no, 0)
            seen[rec.invoice_no] += 1
        archived.append({"dest": dest, "filename": fname})
        ledger_rows.append({
            "发票号": rec.invoice_no,
            "文件名": fname,
            "开票日期": rec.invoice_date,
            "销售方": rec.seller_name,
            "价税合计": f"{rec.total_amount:.2f}",
            "费用类型": rec.category or "其他",
            "是否重复": "是" if (rec.invoice_no and seen[rec.invoice_no] > 1) else "否",
            "置信度": rec.confidence,
        })
    return archived, ledger_rows


def write_ledger_csv(rows, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    return out_path


if __name__ == "__main__":
    print("archive module loaded")
