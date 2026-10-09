# 青禾报销助手_ybw · demo

> 基于 GitHub 开源项目 [`xntj-ai/baoxiao`](https://github.com/xntj-ai/baoxiao)（中国报销 Skill）的设计思路，
> 改造而成的**轻量 demo 版智能体**：把杂乱的发票整理成「打印即合规」的报销单 + 查重台账。
>
> **纯标准库实现，零第三方依赖**，直接 `python demo.py` 即可一键运行。

## 设计原则（来自你的产品定位）

1. **职责分离（Segregation of Duties）**
   - **制度由专业一人维护**：只改 `config/policy.json`，无需动代码；
   - **业务事实由另一人核对**：发票字段提取与费用归类先由系统初判，最终由「业务事实核对人」确认；
   - **员工自助**：先提供「有效制度」自助查询，后续可扩展到「经授权查询本人单据状态」（见 `phase2` 设想）。
2. **金额锚定发票原件**：所有金额取自发票本身，不靠猜测（恰好是最不能猜的地方）。
3. **隐私优先（纯本地规则）**：不调用任何外部 LLM / OCR 接口；纸质照片在纯本地模式下标记「需人工核对」。

## 目录结构

```
baoxiao/
├── demo.py                # 一键演示入口（生成样例→提取→归档→合规→出单）
├── src/
│   ├── cn_amount.py       # 中文大写金额转换
│   ├── extract.py         # 发票提取（数电发票XML / 电子发票PDF* / 图片标记）
│   ├── archive.py         # 规范命名 + 分月归档 + 查重台账
│   ├── compliance.py      # 合规校验规则引擎
│   └── packet.py          # 报销单 HTML 生成（打印即合规）
├── config/
│   └── policy.json        # 报销制度（由专业一人维护）
└── data/
    ├── inbox/             # 待处理发票（放入你的发票即可）
    ├── archive/           # 按开票月归档
    └── output/            # 报销单.html + 发票查重台账.csv
```
> *PDF 解析依赖可选包 `pymupdf`；demo 默认样例用数电发票 XML，无需任何依赖。

## 运行

```bash
cd baoxiao
python demo.py
```

首次运行会生成 4 张示例数电发票（含 1 张与首张同号的重复发票、1 张超标餐饮发票），
随后自动输出：

- `data/output/报销单.html` —— 在浏览器中 Ctrl/Cmd+P 即可打印或另存 PDF；
- `data/output/发票查重台账.csv` —— 用 Excel 打开留存备查（按发票号标记重复）。

要把 demo 用于真实报销，只需把你的发票（`.xml` 数电票或 `.pdf` 电子发票）放进 `data/inbox/`，
再次运行 `python demo.py` 即可（已存在的样例会被跳过；删掉 inbox 里的 sample_*.xml 后再放真实发票）。

## 你可以怎么改

| 想调整什么 | 改哪里 |
|-----------|--------|
| 费用类型上限 / 超标规则 | `config/policy.json` 的 `categories` |
| 必填字段、公私行程关键词 | `config/policy.json` 的 `required_fields` / `private_transport_keywords` |
| 报销单抬头、报销人信息 | `demo.py` 里的 `meta` 字典 |
| 新增发票格式支持 | `src/extract.py` 增加解析分支 |

## 后续（phase2 设想）

- 员工自助查询「有效制度」界面（只读 `policy.json`）；
- 经授权查询「本人单据状态」（需引入轻量单据状态存储 + 权限校验）；
- 纸质照片 OCR 接入（可改为本地 OCR 引擎如 PaddleOCR，仍保持纯本地）。

---
青禾报销助手_ybw · demo · 纯本地 · 职责分离
