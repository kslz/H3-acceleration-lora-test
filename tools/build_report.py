"""Build GitHub Markdown and Chinese CSV from the checked-in workbook snapshot.

Run with Python 3.10+: python tools/build_report.py
No third-party packages or access to the original workspace are required.
"""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import csv
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DOCS = ROOT / "docs"
IDS = ["U0", "P2", "P3", "T4_4", "T8_4", "T8_8", "B50"]
FINE_KEYS = ["overall", "blur", "noise", "artifact", "temporal", "color"]
FINE_LABELS = ["综合评分", "模糊评分", "噪点评分", "伪影评分", "时序一致性", "色彩评分"]
DOVER_LABELS = ["技术分", "美学分", "综合分"]
LABELS = {
    "A3": "Pika · 6步一采", "U0": "仅放大解码 · 0步", "P2": "Pika · 2步二采",
    "P3": "Pika · 3步二采", "T4_4": "Turbo4 v1.0 · 4步二采",
    "T8_4": "Turbo8 v1.1 · 4步二采", "T8_8": "Turbo8 v1.1 · 8步二采",
    "B50": "无加速 LoRA · 50步独立一采",
}


def fmt(value, places=2):
    if not isinstance(value, (int, float)):
        return str(value)
    return str(Decimal(str(value)).quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP))


def table(headers, rows, numeric=()):
    def esc(v):
        return str(v).replace("|", "\\|").replace("\n", "<br>")
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---:" if i in numeric else "---" for i in range(len(headers))) + " |"]
    lines += ["| " + " | ".join(esc(v) for v in row) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def main():
    snapshot = json.loads((DATA / "workbook-snapshot.json").read_text(encoding="utf-8"))
    rows = snapshot["rows"]
    assert len(rows) == 14
    by_key = {(r["id"], r["seed"]): r for r in rows}
    assert len(by_key) == 14
    ordered = [by_key[(id_, seed)] for id_ in IDS for seed in [1, 2]]
    mean = lambda id_, region, k: sum(by_key[(id_, s)][region][k] for s in [1, 2]) / 2
    elapsed = lambda id_: sum(by_key[(id_, s)]["elapsed_s"] for s in [1, 2]) / 2

    readme = """# H3 加速 LoRA：双种子二采对照测试

## 测试结论

**本轮建议先试 Pika 2～3步二采；关注脸、手细节时，再试 Turbo4 4步。** 以下结论来自同一参考图、同一提示词下的两组随机种子，测试日期为2026年11月6日。

### 1. 仅放大与加速二采存在评分差异

本轮 P2、P3、T4_4、T8_4、T8_8 的整片、脸部、手部 FineVQ 综合均值均高于只放大解码的 U0；整片 DOVER 综合均值也高于 U0。两步二采已经带来评分改善，实际观感可结合视频判断。

### 2. B50 是参考基准

本轮五个加速二采候选的整片综合评分均值高于无加速 LoRA 的50步独立一采 B50，输出尺寸也更大。B50 为768×1344，二采组为1088×1920；它们的流程与分辨率不同，这里不据此换算端到端加速倍率。

### 3. 二采步数不是越多越划算

P2 / P3 的二采耗时较短，T4_4 的脸、手 FineVQ 综合均值略领先。T8_8 耗时更多，整片 FineVQ 综合均值与 T4_4 持平，所列整片 DOVER 及脸、手综合均值未进一步领先。

| 使用取向 | 优先尝试 | 本阶段平均耗时 |
| --- | --- | ---: |
| 效率优先 | P2：Pika 2步 | 183.9秒，约3.1分钟 |
| 均衡取舍 | P3：Pika 3步 | 216.6秒，约3.6分钟 |
| 关注脸、手细节 | T4_4：Turbo4 4步 | 264.3秒，约4.4分钟 |

### 4. 样本与局部评价范围

两次测试只更换随机种子，两个种子的均值属于描述性统计，不是显著性检验。脸部、手部评分来自固定448×448区域，不能代表完整运动过程。种子2 B50 部分帧出框，保留原始分数供查阅，但不用于完整脸、手质量排名。

## 实验数据参考

### 测试方法与数据口径

每个种子先用 Pika Flex LoRA、LCM 6步生成768×1344共享一采 A3；六个分支复用对应种子的同一份 latent，放大后输出1088×1920。另外运行无加速 LoRA、Euler simple 50步的独立一采 B50。每支视频124帧、24fps，约5.17秒。

- **FineVQ**：整片、脸部、手部各六项原始评分，不换算为百分制；模糊评分越高表示越清晰。
- **DOVER**：只评整片；单种子记录已是三次采样均值，下表再取两个种子的算术均值。FineVQ 和 DOVER 不相减，评分变化不解释为人眼画质提升百分比。
- **耗时**：U0 包含 latent 放大、保存和解码；五个二采候选从已放大 latent 开始，包含本次加载、采样和解码，不含共享一采及放大准备。B50 是独立一采完整阶段耗时。生成硬件未在源表中列明，耗时作为本轮记录参考。

### 两个种子的均值

"""
    headers = ["方案", "阶段 / 步数", "耗时（秒）", "整片综合均值<br>FineVQ", "整片综合均值<br>DOVER", "脸部综合均值<br>FineVQ", "手部综合均值<br>FineVQ"]
    summary_rows = []
    for id_ in IDS:
        row = by_key[(id_, 1)]
        roi = ["不参与排名†"] * 2 if id_ == "B50" else [fmt(mean(id_, rg, "overall")) for rg in ["face", "hand"]]
        summary_rows.append([f"**{id_}**", LABELS[id_], fmt(elapsed(id_), 1), fmt(mean(id_, "native", "overall")), fmt(mean(id_, "dover", "overall_mean")), *roi])
    readme += table(headers, summary_rows, range(2, 7))
    readme += """
† B50 局部原始分数在完整得分表中保留，并标注出框情况。U0、二采候选和 B50 的耗时口径见上文。

### 各方案参考

"""
    notes = {
        "U0": "0步，仅放大 latent 后直接 VAE 解码。作为只放大对照与快速预览候选。",
        "P2": "Pika Flex LoRA，LCM 2步二采。可优先尝试的效率方案。",
        "P3": f"Pika Flex LoRA，LCM 3步二采。比 P2 多花约{fmt(elapsed('P3')-elapsed('P2'), 1)}秒，本轮手部综合均值更高，可作为均衡候选。",
        "T4_4": "Turbo 4step v1.0，Euler 4步二采。本轮二采候选中脸、手 FineVQ 综合均值最高，可作为细节候选。",
        "T8_4": "Turbo 8step v1.1，Euler 4步二采。本轮平均耗时较高，两个种子的耗时分别为488.2秒和279.3秒，波动较大。",
        "T8_8": "Turbo 8step v1.1，Euler 8步二采。整片 FineVQ 综合均值与 T4_4 持平，脸、手综合均值未超过 T4_4。",
        "B50": "无加速 LoRA，Euler simple 50步独立一采，768×1344。作为不同流程、不同输出尺寸的参考基准。",
    }
    for id_ in IDS:
        readme += f"- **{id_}**：{notes[id_]}\n"
    readme += """

### A3：共享一采来源

A3 为 Pika 加速 LoRA、LCM 6步一采，768×1344。每个种子的六个分支共享该种子的 A3 latent。

- 种子1一采耗时91.3657秒，原片与旧记录的 SHA-256、latent SHA-256 已在源资料中核实一致。
- 种子2记录从开始至成功为203.1秒，与种子1是不同原片。
- 种子1旧版整片 FineVQ 综合分68.00、DOVER 综合分70.96；旧版局部裁切协议不同，不并入本轮双种子局部均值。
- 本轮双种子评分集合没有 A3 条目，因此不填 A3 双种子评分。视频汇总中提供 A3 的完整、脸部、手部画面，供观察一采来源。

## 完整得分表与视频结果

| 查看内容 | 入口 |
| --- | --- |
| 14条记录的全部评分子项，按整片、脸部、手部分表 | [完整得分表](docs/scores.md) |
| 两个种子的全部结果，每组含完整、脸部、手部三个视频 | [视频结果汇总](docs/videos.md) |
| 模型、采样器、完整 sigma 点列、固定裁切和耗时说明 | [实验参数与评分方法](docs/parameters.md) |
| 便于下载、筛选的中文完整表格 | [完整得分 CSV](data/full-scores.csv) |

评分表和视频按方案编号、种子标签对应。评分原始数值及精度保存在 [数据快照](data/workbook-snapshot.json)；来源文件名、SHA-256 与核对范围见 [数据来源](data/provenance.json)。
"""
    write(ROOT / "README.md", readme)

    score_text = """# 完整得分表

[返回测试结论](../README.md) · [视频结果汇总](videos.md) · [实验参数与评分方法](parameters.md) · [下载中文完整 CSV](../data/full-scores.csv)

本页逐条保留源 Excel 的14条记录。为便于 GitHub 阅读，按评分模型和画面区域分表；CSV 保留全部配置列、评分列及“未评测”标记。A3 未纳入本轮双种子评分，不补造分数。

## 评分列名说明

"""
    score_text += table(["原字段", "中文列名", "含义"], [
        ["overall", "综合评分", "FineVQ 综合评价"], ["blur", "模糊评分", "越高越清晰；不是模糊程度百分比"],
        ["noise", "噪点评分", "FineVQ 噪点维度原始输出"], ["artifact", "伪影评分", "FineVQ 伪影维度原始输出"],
        ["temporal", "时序一致性", "FineVQ 时间维度原始输出"], ["color", "色彩评分", "FineVQ 色彩维度原始输出"],
        ["technical_mean", "技术分", "DOVER 三次采样技术均值"], ["aesthetic_mean", "美学分", "DOVER 三次采样美学均值"],
        ["overall_mean", "综合分", "DOVER 三次采样综合均值"],
    ])
    score_text += "\nFineVQ 原始分数不换算为百分制，也不与 DOVER 相减。下表 FineVQ 保留至三位小数，以保留本轮0.125等细分值；DOVER 保留至四位小数；完整精度见 CSV 和 JSON。\n"
    score_text += "\n## 方案与耗时\n\n二采组输出1088×1920，B50 输出768×1344。二采组共享对应种子的 Pika 6步一采；B50 是无加速 LoRA 的独立一采。\n\n"
    score_text += table(["方案", "种子", "输出分辨率", "本阶段耗时（秒）", "视频结果"],
        [[r["id"], f"种子{r['seed']}", r["resolution"], fmt(r["elapsed_s"], 4), f"[完整 / 脸 / 手](videos.md#seed{r['seed']}-{r['id'].lower()})"] for r in ordered], [3])
    for region, title in [("native", "整片"), ("face", "脸部固定区域"), ("hand", "手部固定区域")]:
        score_text += f"\n## {title} FineVQ\n\n"
        if region != "native":
            score_text += "固定448×448裁切。**种子2 B50 部分帧出框，其分数仅表示固定区域；B50 局部两种子均值也不用于完整脸、手排名。** DOVER 未评测局部，CSV 中保留为“未评测”。\n\n"
        score_text += table(["方案", "种子", *FINE_LABELS],
            [[r["id"] + ("†" if r["id"] == "B50" and r["seed"] == 2 and region != "native" else ""), f"种子{r['seed']}", *[fmt(r[region][k], 3) for k in FINE_KEYS]] for r in ordered], range(2, 8))
    score_text += "\n## 整片 DOVER\n\n每条记录是该种子视频的三次采样均值，并非跨种子平均。\n\n"
    score_text += table(["方案", "种子", *DOVER_LABELS],
        [[r["id"], f"种子{r['seed']}", *[fmt(r["dover"][k], 4) for k in ["technical_mean", "aesthetic_mean", "overall_mean"]]] for r in ordered], [2, 3, 4])
    write(DOCS / "scores.md", score_text)

    headers = ["方案", "文件名", "视频分辨率", "生成种子", "一采加速LoRA", "一采步数", "一采sigma配方", "二采加速LoRA", "二采步数", "二采sigma配方", "本阶段耗时（秒）"]
    for region in ["整片", "脸部", "手部"]:
        headers += [f"{region} FineVQ {v}" for v in FINE_LABELS] + [f"{region} DOVER {v}" for v in DOVER_LABELS]
    with (DATA / "full-scores.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in ordered:
            out = [r["id"], r["filename"], r["resolution"], f"种子{r['seed']}", *r["config_columns"], r["elapsed_s"]]
            for region in ["native", "face", "hand"]:
                out += [r[region][k] for k in FINE_KEYS]
                out += [r["dover"][k] for k in ["technical_mean", "aesthetic_mean", "overall_mean"]] if region == "native" else ["未评测"] * 3
            assert len(out) == len(headers)
            writer.writerow(out)

    params = """# 实验参数与评分方法

[返回测试结论](../README.md) · [完整得分表](scores.md) · [视频结果汇总](videos.md)

## 输入与流程

两组种子使用相同参考图、提示词和匹配配置，仅更换随机种子。本报告沿用源表的“种子1 / 种子2”标签，不列完整种子值。每支视频124帧、24fps，约5.17秒。

每个种子：参考图 → A3（Pika / LCM 6步，768×1344）→ 共享 latent → latent 放大 → U0 / P2 / P3 / T4_4 / T8_4 / T8_8（1088×1920）。B50 由参考图独立生成，不使用 A3 latent。

### 配置

"""
    configs = snapshot["configs"]
    params += table(["方案", "加速 LoRA", "采样器 / 调度器", "步数", "输出尺寸"],
        [[k, v["lora"], v["sampler"] + (f" / {v['scheduler']}" if v.get("scheduler") else ""), v.get("steps", len(v["sigmas"]) - 1), f"{v['width']}×{v['height']}"] for k, v in configs.items()])
    params += "\n底模：`minimax_h3_ref2va_pruned_int8_convrot.safetensors`。U0 仅放大并解码，不加载去噪模型。手动 sigma 方案的调度器在源表中为“未单独指定”，上表仅列采样器，实际使用下列点列。\n\n### 完整 sigma 点列\n\n除 B50 使用 simple 调度外，其余按记录的手动 sigma 点列执行。以下保留记录精度。\n"
    for k, v in configs.items():
        params += f"\n**{k}**\n\n```json\n{json.dumps(v['sigmas'], ensure_ascii=False)}\n```\n"
    params += """
P2 采用共享一采配方的末两步；P3 在两步方案中增加一个中间点。Turbo4 与 Turbo8 使用不同 LoRA 文件，即使都跑4步也不视为同一配置。B50 为 simple 50步，原始 t = 1 − i/50（i = 0…50），视频 shift = 12、音频 shift = 3，共50次 Euler 更新。

## 固定区域裁切

| 项目 | 设置 |
| --- | --- |
| 裁切画布 | 1088×1920 |
| 脸部左上角 | (332, 183) |
| 手部左上角 | (151, 990) |
| 裁切尺寸 | 脸、手均为448×448 |
| 二采结果 | decoded RGB24，直接在对应位置裁切 |
| B50 | 先用 Lanczos 从768×1344缩放至1088×1920，再按相同坐标裁切 |

种子2 B50 的脸、手部分帧超出固定框，固定框分数不代表完整脸部或手部质量。A3 展示局部同样先缩放后按固定框裁切，仅供观看，没有补入本轮评分。

## 耗时口径

- U0：包括 latent 放大、保存和解码，不含复用的一采。
- P2、P3、T4_4、T8_4、T8_8：从已放大 latent 开始，包括本次加载、采样和解码，不含共享一采与 latent 放大准备。
- B50：独立一采完整阶段耗时。
- A3：种子1为91.3657秒，种子2开始至成功为203.1秒；不并入上面的二采阶段时间。

以上阶段范围不同，因此不直接给出同口径的端到端速度倍率。T8_4 两次记录为488.2秒和279.3秒，T8_8 为379.2秒和377.4秒；不能仅用两个种子的平均耗时推断步数与时间的普遍关系。

## 评分与来源

FineVQ 评整片、脸部、手部各六项；DOVER 只评整片，每条记录取三次采样均值。没有运行局部 DOVER，源表对应84个单元格为“未评测”。模型评分不能替代实际视频观感。

所有14条结果及全部294个已评评分值从指定 Excel 提取，并逐项与双种子汇总 JSON 核对。中文 CSV 另外保留84个“未评测”单元格。原始数值保存在 [数据快照](../data/workbook-snapshot.json)，源表及参考文档校验值见 [数据来源](../data/provenance.json)。视频文件和派生预览的身份、编码及 SHA-256 见 [视频清单](../data/media-manifest.json)。
"""
    write(DOCS / "parameters.md", params)
    print("Built README.md, docs/scores.md, docs/parameters.md, data/full-scores.csv")


if __name__ == "__main__":
    main()
