"""发票提取模块（demo 版，纯标准库，可选 pymupdf 支持 PDF）。

支持：
  - 数电发票 XML：标签直取 + 正则兜底
  - 增值税电子发票 PDF（需 pymupdf）：文本层解析
  - 图片/纸质照片：纯本地 demo 不支持 OCR，标记需人工核对

输出统一 InvoiceRecord。
"""
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict

try:
    import fitz  # pymupdf（可选）
except Exception:
    fitz = None

CN_CAP_RE = re.compile(r"[零壹贰叁肆伍陆柒捌玖拾佰仟万亿圆元角分整]{4,}")
MONEY_RE = re.compile(r"[¥￥]?\s*([\d,]{1,}\,\d{2})")
INVOICE_NO_RE = re.compile(r"发票号码[：: ]*([0-9A-Za-z]{8,30})")
DATE_RE = re.compile(r"开票日期[：: ]*(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})")
NAME_RE = re.compile(r"名称[：: ]*\s*([^\n（(]{2,40}?)\s*(?:$|[（(])")


@dataclass
class InvoiceRecord:
    source_file: str = ""
    invoice_type: str = ""
    invoice_no: str = ""
    invoice_date: str = ""
    buyer_name: str = ""
    seller_name: str = ""
    amount_excl_tax: float = 0.0
    tax: float = 0.0
    total_amount: float = 0.0
    total_amount_cn: str = ""
    tax_rate: str = ""
    category: str = ""           # 业务核对人/系统初步归类
    confidence: str = "low"
    notes: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def _clean_money(s):
    if not s:
        return 0.0
    s = s.replace("¥", "").replace("￥", "").replace(",", "").strip()
    try:
        return round(float(s), 2)
    except ValueError:
        return 0.0


def _parse_date(y, m, d):
    try:
        from datetime import date
        return date(int(y), int(m), int(d)).isoformat()
    except Exception:
        return ""


def _parse_fields(text):
    out = {}
    m = INVOICE_NO_RE.search(text)
    if m:
        out["invoice_no"] = m.group(1).strip()
    m = DATE_RE.search(text)
    if m:
        out["invoice_date"] = _parse_date(m.group(1), m.group(2), m.group(3))
    total_block = re.search(r"价税合计[^\d]{0,40}?([¥￥]?\s*[\d,]+\.\d{2})", text)
    if total_block:
        out["total_amount"] = _clean_money(total_block.group(1))
    cn = CN_CAP_RE.search(text)
    if cn:
        out["total_amount_cn"] = cn.group(0)
    names = [n.strip() for n in NAME_RE.findall(text)]
    if len(names) >= 1:
        out["buyer_name"] = names[0]
    if len(names) >= 2:
        out["seller_name"] = names[1]
    return out


def _extract_xml(path):
    rec = InvoiceRecord(source_file=os.path.basename(path), invoice_type="数电发票XML")
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        raw = ET.tostring(root, encoding="unicode")
    except Exception as e:
        rec.notes.append(f"XML 解析失败：{e}")
        return rec
    text = _xml_to_text(root)
    f = _parse_fields(text)
    tag_map = {
        "invoice_no": ["InvoiceNo", "发票号码", "FPHM"],
        "invoice_date": ["InvoiceDate", "开票日期", "KPRQ"],
        "buyer_name": ["BuyerName", "购买方名称", "GMFMC"],
        "seller_name": ["SellerName", "销售方名称", "XSFMC"],
        "total_amount": ["TotalAmount", "价税合计", "JSHJ"],
        "amount_excl_tax": ["Amount", "不含税金额", "HJJE"],
        "tax": ["Tax", "税额", "SE"],
        "tax_rate": ["TaxRate", "税率", "SL"],
        "total_amount_cn": ["CNTotalAmount", "价税合计大写", "JSHJDX"],
    }
    def _find_local(root, names):
        for el in root.iter():
            if el.tag.split("}")[-1] in names and el.text and el.text.strip():
                return el.text.strip()
        return None

    for field_name, tags in tag_map.items():
        val = _find_local(root, tags)
        if val:
            if field_name in ("total_amount", "amount_excl_tax", "tax"):
                setattr(rec, field_name, _clean_money(val))
            elif field_name == "invoice_date":
                m = re.search(r"(\d{4})[-\/年](\d{1,2})[-\/月](\d{1,2})", val)
                setattr(rec, field_name, _parse_date(*m.groups()) if m else val)
            else:
                setattr(rec, field_name, val)
    for k, v in f.items():
        if not getattr(rec, k):
            setattr(rec, k, v)
    rec.confidence = "high" if (rec.invoice_no and rec.total_amount) else "low"
    if not rec.total_amount_cn and rec.total_amount:
        from .cn_amount import num_to_cn_capital
        rec.total_amount_cn = num_to_cn_capital(rec.total_amount)
    return rec


def _extract_pdf(path):
    rec = InvoiceRecord(source_file=os.path.basename(path), invoice_type="电子发票PDF")
    if fitz is None:
        rec.notes.append("未安装 pymupdf，无法解析 PDF（demo 默认走 XML）")
        return rec
    doc = fitz.open(path)
    text = "\n".join(p.get_text() for p in doc)
    doc.close()
    f = _parse_fields(text)
    for k, v in f.items():
        setattr(rec, k, v)
    rec.confidence = "high" if (rec.invoice_no and rec.total_amount) else "low"
    if not rec.total_amount_cn and rec.total_amount:
        from .cn_amount import num_to_cn_capital
        rec.total_amount_cn = num_to_cn_capital(rec.total_amount)
    return rec


def _xml_to_text(root):
    parts = []
    for el in root.iter():
        if el.text and el.text.strip():
            tag = el.tag.split("}")[-1]
            parts.append(f"{tag}：{el.text.strip()}")
    return "\n".join(parts)


def extract_from_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xml",):
        return _extract_xml(path)
    if ext in (".pdf",):
        return _extract_pdf(path)
    rec = InvoiceRecord(source_file=os.path.basename(path), invoice_type="纸质照片/图片")
    rec.notes.append("纯本地 demo 不支持图片 OCR，请人工核对发票号与金额后补录")
    return rec


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(extract_from_file(sys.argv[1]).to_dict())
