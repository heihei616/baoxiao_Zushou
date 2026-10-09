"""合规校验规则引擎（demo 版，纯标准库）。

制度由「专业一人」维护：编辑 config/policy.json 即可调整规则，无需改代码。
本模块对每张发票做：
  - 必填字段校验
  - 按费用类型上限校验（超标标记）
  - 公私行程关键词提示（网约车/交通类）
"""
import json
import os


def load_policy(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_invoice(rec, policy):
    issues = []
    # 必填字段
    for field in policy.get("required_fields", []):
        val = getattr(rec, field, "")
        if not val:
            issues.append(f"缺少必填字段：{field}")
    # 费用类型上限
    cats = policy.get("categories", {})
    cat = rec.category or "其他"
    rule = cats.get(cat)
    if rule and rec.total_amount > rule.get("max_per_invoice", 1e18):
        issues.append(f"【超标】{cat}单张 {rec.total_amount:.2f} 元，超过上限 {rule['max_per_invoice']} 元（{rule.get('note','')}）")
    elif not rule and cat != "其他":
        issues.append(f"【提醒】费用类型「{cat}」未在制度中定义上限，请制度维护人补充")
    # 公私行程提示
    if cat in ("交通", "网约车"):
        text = (rec.seller_name or "") + " " + " ".join(rec.notes)
        hits = [k for k in policy.get("private_transport_keywords", []) if k in text]
        if hits:
            issues.append(f"【公私待核】命中疑似非公务特征：{', '.join(hits)}，请业务事实核对人确认")
    return issues


def check_all(records, policy):
    report = []
    for rec in records:
        report.append({
            "invoice_no": rec.invoice_no,
            "category": rec.category or "其他",
            "total": rec.total_amount,
            "issues": check_invoice(rec, policy),
        })
    return report


if __name__ == "__main__":
    print("compliance module loaded")
