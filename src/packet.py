"""报销单生成模块（demo 版，输出打印即合规的 HTML 报销单包）。

包含：封面汇总单 + 逐票明细页 + 合规分析页。可直接浏览器打印为 PDF。
"""
import os
import html
from datetime import datetime


def _esc(s):
    return html.escape(str(s if s is not None else ""))


def generate_packet(meta, records, compliance_report, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    total = sum(r.total_amount for r in records)
    from .cn_amount import num_to_cn_capital
    total_cn = num_to_cn_capital(total)

    # 明细行
    rows = ""
    for i, r in enumerate(records, 1):
        cr = next((c for c in compliance_report if c["invoice_no"] == r.invoice_no), None)
        issues = cr["issues"] if cr else []
        issue_html = "<br>".join(_esc(x) for x in issues) if issues else "✅ 合规"
        issue_cls = "" if not issues else "warn"
        rows += f"""
        <tr>
          <td>{i}</td>
          <td>{_esc(r.invoice_no)}</td>
          <td>{_esc(r.invoice_date)}</td>
          <td>{_esc(r.seller_name)}</td>
          <td>{_esc(r.category or '其他')}</td>
          <td class="num">{r.total_amount:.2f}</td>
          <td>{_esc(r.total_amount_cn or num_to_cn_capital(r.total_amount))}</td>
          <td class="{issue_cls}">{issue_html}</td>
        </tr>"""

    # 合规汇总
    all_issues = []
    for c in compliance_report:
        for it in c["issues"]:
            all_issues.append(it)
    if all_issues:
        issue_list = "\n".join(f"<li>{_esc(x)}</li>" for x in all_issues)
        issue_section = f'<div class="box warn-box"><h3>⚠ 合规风险提示（共 {len(all_issues)} 项）</h3><ul>{issue_list}</ul></div>'
    else:
        issue_section = '<div class="box ok-box"><h3>✅ 全部票据通过合规校验</h3></div>'

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>青禾报销单 - {_esc(meta.get('applicant',''))}</title>
<style>
  @page {{ size: A4; margin: 16mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: "Microsoft YaHei", "PingFang SC", sans-serif; color:#222; font-size:12px; }}
  h1 {{ text-align:center; font-size:20px; margin:6px 0 2px; }}
  h3 {{ font-size:13px; margin:14px 0 6px; }}
  .sub {{ text-align:center; color:#666; margin-bottom:14px; }}
  table {{ width:100%; border-collapse:collapse; margin:6px 0; }}
  th, td {{ border:1px solid #999; padding:5px 6px; text-align:left; vertical-align:top; }}
  th {{ background:#f2f2f2; }}
  td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
  .cover {{ width:100%; border-collapse:collapse; margin:10px 0; }}
  .cover th {{ width:22%; background:#f2f2f2; }}
  .total {{ font-size:14px; font-weight:bold; }}
  .box {{ border:1px solid #999; padding:8px 10px; margin:8px 0; border-radius:4px; }}
  .ok-box {{ border-color:#2e7d32; background:#f1f8f1; }}
  .warn-box {{ border-color:#c62828; background:#fdf3f3; }}
  .warn {{ color:#c62828; }}
  .sign {{ margin-top:24px; display:flex; justify-content:space-between; }}
  .sign div {{ width:30%; border-top:1px solid #333; padding-top:4px; text-align:center; color:#333; }}
  .foot {{ margin-top:18px; color:#888; font-size:10px; }}
  @media print {{ .noprint {{ display:none; }} }}
</style></head>
<body>
  <h1>费用报销单</h1>
  <div class="sub">{_esc(meta.get('org','青禾科技有限公司'))} · 制单日期 {_esc(meta.get('created', datetime.now().strftime('%Y-%m-%d')))}</div>

  <table class="cover">
    <tr><th>报销人</th><td>{_esc(meta.get('applicant',''))}</td><th>部门</th><td>{_esc(meta.get('department',''))}</td></tr>
    <tr><th>费用所属期</th><td>{_esc(meta.get('period',''))}</td><th>用途</th><td>{_esc(meta.get('purpose',''))}</td></tr>
    <tr><th>合计金额（小写）</th><td class="num">¥ {total:.2f}</td><th>合计金额（大写）</th><td class="total">{_esc(total_cn)}</td></tr>
    <tr><th>附件张数</th><td>{len(records)} 张</td><th>备注</th><td>{_esc(meta.get('remark','自助生成，金额锚定发票原件'))}</td></tr>
  </table>

  <h3>一、票据明细</h3>
  <table>
    <thead><tr><th>序号</th><th>发票号</th><th>开票日期</th><th>销售方</th><th>费用类型</th><th class="num">价税合计</th><th>大写金额</th><th>合规/提示</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <h3>二、合规分析</h3>
  {issue_section}

  <div class="sign">
    <div>报销人签字</div><div>业务事实核对人</div><div>审批人</div>
  </div>
  <div class="foot">本报销单由「青禾报销助手_ybw」demo 自动生成；金额锚定发票原件，制度由专业一人维护，业务事实由另一人核对（职责分离）。</div>
  <div class="noprint" style="margin-top:20px;color:#1565c0;">💡 在浏览器中按 Ctrl/Cmd+P 即可打印或另存为 PDF。</div>
</body></html>"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_path
