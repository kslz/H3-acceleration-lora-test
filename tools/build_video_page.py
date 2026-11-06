"""Rebuild the GitHub video gallery from data/media-manifest.json."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
LABELS = {'A3':'Pika · 6步一采','P2':'Pika · 2步二采','P3':'Pika · 3步二采',
          'T4_4':'Turbo4 v1.0 · 4步二采','T8_4':'Turbo8 v1.1 · 4步二采',
          'T8_8':'Turbo8 v1.1 · 8步二采','B50':'无加速 LoRA · 50步独立一采','U0':'仅放大解码 · 0步'}

def main():
    manifest = json.loads((ROOT/'data/media-manifest.json').read_text(encoding='utf-8'))
    media = {(v['seed'],v['id'],v['region']):v for v in manifest['videos']}
    assert len(media)==48
    text = '''# 视频结果汇总

[返回测试结论](../README.md) · [完整得分表](scores.md) · [实验参数与评分方法](parameters.md)

两个种子各8组结果，每组包含完整视频、脸部固定区域、手部固定区域，共48个视频。点击缩略图或其下方的视频链接，打开对应 MP4；GitHub 根据客户端提供文件预览或下载。

- 每个视频124帧、24fps，约5.17秒，保持原播放速度。
- 完整视频直接保留源 MP4；脸部、手部为静音 H.264 观看版，448×448，未做锐化、美化或调色。评分使用原始无损裁切文件。
- A3 是共享一采来源，仅作画面对照；其局部按本轮坐标生成，没有补入本轮评分。
- **种子2 B50 脸部、手部部分帧出框**，不用于完整局部质量排名。

[跳到种子1](#seed1) · [跳到种子2](#seed2)
'''
    for seed in [1,2]:
        text += f'\n<a id="seed{seed}"></a>\n\n## 种子{seed}\n'
        for id_,label in LABELS.items():
            text += f'\n<a id="seed{seed}-{id_.lower()}"></a>\n\n### {id_}：{label}\n\n'
            if seed==2 and id_=='B50':
                text += '**本组局部视频存在出框，固定区域不能完整覆盖脸、手。**\n\n'
            previews=[]
            links=[]
            for region,region_label in [('full','完整视频'),('face','脸部视频'),('hand','手部视频')]:
                v=media[(seed,id_,region)]
                assert (ROOT/v['path']).is_file() and (ROOT/v['poster']).is_file()
                previews.append(f"[![种子{seed} {id_} {region_label}](../{v['poster']})](../{v['path']})")
                links.append(f"[打开{region_label}](../{v['path']})")
            text+='| 完整视频 | 脸部固定区域 | 手部固定区域 |\n| --- | --- | --- |\n'
            text+='| '+' | '.join(previews)+' |\n'
            text+='| '+' | '.join(links)+' |\n'
        text+='\n[返回页首](#视频结果汇总)\n'
    text+='\n视频源文件与观看版的 SHA-256、编码及尺寸记录见 [视频清单](../data/media-manifest.json)。\n'
    (ROOT/'docs/videos.md').write_text(text,encoding='utf-8')
    print('Built docs/videos.md: 16 result groups, 48 videos and thumbnails.')

if __name__=='__main__':
    main()
