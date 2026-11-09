# Workflow 05：历史人物说唱对决（Ancient / Historical Rap Battle）— 项目进度、操作指南与问题复盘

> **最新进展（2026-11-09）**：完整版样片 `episodes/edison-vs-tesla-full/`（两回合、1 分 36 秒）改用 H3 锁音直出口型、统一背景参考图、真实运镜和后期现场运镜层，不再使用下文的 Wav2Lip 局部驱动方案。**做一集照着 [SOP_每集制作流程.md](SOP_每集制作流程.md) 走**（选题 → 歌曲 → 分镜 → 出片 → Shorts → 封面 → 上传）；原因、坑和未解决问题见 [经验沉淀_完整版样片.md](经验沉淀_完整版样片.md)；下文是第一版（30 秒）的记录。

> **当前剧集**：`edison-vs-tesla`（爱迪生 vs 特斯拉 · 30 秒英文 Freestyle Rap Battle）  
> **剧集目录**：`workflows/05_ancient_rap_battle/episodes/edison-vs-tesla/`  
> **硬件架构**：云端 Colab Pro+ G4（NVIDIA RTX PRO 6000 Blackwell 96GB，用于 H3 视频生成，用完即焚 `0.00 CCU/h`）+ 本地 Mac（Apple M6 MPS，用于音频处理、口型对齐、字幕包装与成片合成，`0 CCU`）

---

## 一、当前项目进度（Project Progress）

### 1.1 整体里程碑状态

| 阶段 | 任务模块 | 状态 | 产出概要 |
| :---: | :--- | :---: | :--- |
| **Step 1** | 题材选定与分镜/台词剧本设计 | ✅ 已完成 | 选定「爱迪生 vs 特斯拉（直流电 vs 交流电）」，全英文 30 秒 8 句对决（Edison 4 句 + Tesla 4 句），配置于 `episode.json` |
| **Step 2** | Kie.ai Suno V5 音乐生成与词级时间戳提取 | ✅ 已完成 | 生成双版本音乐（`suno_v1.mp3`、`suno_v2.mp3`），提取词级时间戳 `kie_suno.json` 并裁剪为 30.76 秒高潮段 |
| **Step 3** | 人声伴奏分离与双男声（Edison / Tesla）音色区分 | ✅ 已完成 | 通过 Kie.ai Vocal Separation 分离干声/伴奏，并为 Edison（浑厚男中音 `-2.2` 半音）与 Tesla（锐利男高音 `+1.8` 半音）合成独立音色干声与总混音 `music_final.wav` |
| **Step 4** | 角色/场景视觉设定图与封面制作 | ✅ 已完成 | 完成 Edison、Tesla 全身设定图、面部特写、半身裁切图（`a_bust.png` / `b_bust.png`）、1890s 工业发电厂舞台、观众、DJ 台及横/竖版封面 |
| **Step 5** | 分镜脚本（12 镜头）与 EDL 时间线生成 | ✅ 已完成 | 生成 `work/clips.json`（8 个说唱镜头 `A01–A04`、`B01–B04` + 4 个过场/反应镜头 `OPEN`、`DJ`、`B_REACT`、`END`）、`work/edl.json` 及 `分镜表.md` |
| **Step 6** | Colab G4 MiniMax-H3 12 镜头 768p 视频生成 | ✅ 已完成 | 在 Colab G4（96GB VRAM）使用 `MiniMaxH3ReferenceToVideo` 生成全部 12 个 `1344x768 @ 24fps`（124 帧，`5.167s`）分镜视频，并备份原始分镜至 `clips/raw_h3/`；云端实例已释放（`0.00 CCU/h`） |
| **Step 7** | 本地 Apple M6 音画时间轴对齐与 768p 口型驱动 | ✅ 已完成 | 搭建 `/tmp/lipsync_venv` 本地环境，完成单词边界强锚定时间轴映射 + F1/F2 元音共振峰（`300–2400 Hz`）音节开合提取 + 768p 微分同胚下唇驱动与闭唇仿射融合 |
| **Step 8** | 成片剪辑、电影级调色、花字字幕与横/竖屏封装 | ✅ 已完成 | 修复 `assemble.py` 与 `package.py` 中间文件断层问题，输出最新 16:9 横屏成片 `Edison_vs_Tesla_成片.mp4` 与手机预览版 `Edison_vs_Tesla_竖屏.mp4` |

### 1.2 当前 8 个说唱分镜口型对齐指标（`work/lipcheck_report.json`）

| 分镜 ID | 角色 / 景别 | 台词内容 | 有效张嘴区间 `raw_active_span (s)` | 时间映射节点 `knots_s (s)` | 元音开合相关度 `VowelCorr@0ms` | 全频段 `RMSCorr@0ms` | 嘴部开合范围 `[min..max]` |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **A01** | Edison 单人特写 (M2) | *Over a thousand patents stamped under my name* | `(0.42, 2.42)` | `(0.44, 1.64, 2.35)` | **`+0.877`** | `+0.121` | `[0.000 .. 0.158]` |
| **A02** | Edison 双人中景 (M5) | *I lit up New York City while you chased a phantom flame* | `(0.00, 2.50)` | `(0.07, 1.30, 2.50)` | **`+0.938`** | `+0.280` | `[0.001 .. 0.145]` |
| **A03** | Edison 单人中近景 (M3) | *You wired up the future? Boy, you couldn't pay the rent* | `(0.12, 2.50)` | `(0.12, 1.21, 2.43)` | **`+0.986`** | `+0.223` | `[0.002 .. 0.162]` |
| **A04** | Edison 双人仰拍 (M7) | *Feeding pigeons in a hotel without a single cent* | `(0.08, 2.75)` | `(0.08, 1.64, 2.63)` | **`+0.891`** | `+0.386` | `[0.001 .. 0.174]` |
| **B01** | Tesla 单人中近景 (M3) | *Twenty-two men built the bulb before you made the steal* | `(0.21, 2.71)` | `(0.13, 1.26, 2.59)` | **`+0.504`** | `+0.385` | `[0.008 .. 0.101]` |
| **B02** | Tesla 单人特写 (M2) | *You promised fifty thousand bucks then broke the whole deal* | `(0.00, 2.83)` | `(0.00, 1.47, 2.76)` | `+0.127` | `+0.185` | `[0.008 .. 0.079]` |
| **B03** | Tesla 双人近景 (M6) | *Your weak direct current left the city in the dark* | `(0.00, 2.29)` | `(0.12, 0.95, 2.35)` | `+0.188` | `+0.336` | `[0.001 .. 0.111]` |
| **B04** | Tesla 双人仰拍 (M7) | *Now the future drives my name on every high-voltage spark* | `(0.00, 2.83)` | `(0.04, 1.20, 2.71)` | **`+0.915`** | `+0.637` | `[0.002 .. 0.167]` |

> **当前状态说明**：
> - `A01`、`A02`、`A03`、`A04`、`B01`、`B04` 的元音开合相关度均达到 `+0.50 ~ +0.98`，且最佳延迟为 `0 ms`。
> - `B02` 与 `B03` 中由于特斯拉留有浓密黑色八字胡且麦克风紧贴下唇下方，为防止八字胡重影和麦克风边缘形变，脚本限制了单调回退帧数（`prev_idx - 2`）与下唇位移幅度，因此嘴部开合幅度较保守（`mo_max` 约 `0.08~0.11`）。

---

## 二、具体怎么操作（Step-by-Step Operating Guide）

所有命令均在仓库根目录 `/Volumes/WorkData/Workspace/projects/colab-ultra-workstation` 下执行。

### 2.1 日常最高频操作：本地一键重跑口型对齐 + 合成包装（`0 CCU`，耗时约 45 秒）

如果你修改了口型对齐参数、字幕样式或时间轴，**无需启动云端 GPU**，直接在本地运行以下三条命令即可更新全部成片：

```bash
# 1. 基于 clips/raw_h3/ 原始备份，重新执行音节时间轴对齐与 768p 口型驱动，输出至 clips/A01_t1.mp4 .. B04_t1.mp4
MPLCONFIGDIR=/tmp/mpl_cache /tmp/lipsync_venv/bin/python \
  workflows/05_ancient_rap_battle/scripts/align_and_lipsync.py \
  workflows/05_ancient_rap_battle/episodes/edison-vs-tesla

# 2. 按 work/edl.json 拼接全部 12 个分镜，同时写入 preview/草稿.mp4 与 preview/成片_拼接.mp4
python3 workflows/05_ancient_rap_battle/scripts/assemble.py \
  workflows/05_ancient_rap_battle/episodes/edison-vs-tesla

# 3. 叠加调色、双语花字字幕、人物铭牌、片头片尾与欢呼环境音，生成最终横屏与手机预览版成片
python3 workflows/05_ancient_rap_battle/scripts/package.py \
  workflows/05_ancient_rap_battle/episodes/edison-vs-tesla --phone && \
cp workflows/05_ancient_rap_battle/episodes/edison-vs-tesla/final/Edison_vs_Tesla_成片_手机预览.mp4 \
   workflows/05_ancient_rap_battle/episodes/edison-vs-tesla/final/Edison_vs_Tesla_竖屏.mp4
```

---

### 2.2 从零制作一集新说唱对决的完整全流程 SOP（Step 1 ~ Step 9）

#### Step 1：配置剧集 `episode.json` 与生成歌词提示词
1. 在 `workflows/05_ancient_rap_battle/episodes/<剧集名>/episode.json` 中定义双方角色（`a`、`b`）、造型描述（`look`）、标志性道具（`prop` / `prop_desc`）、舞台环境（`venue_en`）、8 句歌词（`lyrics.a` 4 句 + `lyrics.b` 4 句）、每句历史典故注释（`notes`）及镜头动作（`actions`）。
2. 生成歌词与 Suno 指南文档：
   ```bash
   python3 workflows/05_ancient_rap_battle/scripts/analyze_song.py \
     workflows/05_ancient_rap_battle/episodes/edison-vs-tesla --guide
   ```

#### Step 2：调用 Kie.ai Suno V5 生成说唱歌曲、分离干声并制作双人不同音色
使用 `kie_suno.py` 自动完成 Suno V5 歌曲生成、获取词级时间戳（`get-timestamped-lyrics`）、人声/伴奏分离（`separate-vocals`）、30 秒高潮段裁剪，以及 A/B 角色差异化音色处理（Edison 降调浑厚男中音 / Tesla 升调锐利男高音）：
```bash
# 若已有 kie_suno.json 缓存，仅重新按照最新音色参数合成双人声音与 lines.json / grid.json：
python3 workflows/05_ancient_rap_battle/scripts/kie_suno.py \
  workflows/05_ancient_rap_battle/episodes/edison-vs-tesla --reprocess-only
```
- **核心产物**：`song.mp3`、`音乐_最终.wav`、`字幕.srt`、`work/music_final.wav`、`work/voc_a.wav`、`work/voc_b.wav`、`work/lines.json`、`work/grid.json`。

#### Step 3：准备角色与场景视觉参考图（`refs/`）及封面（`cover/`）
在 `episodes/<剧集名>/refs/` 放置以下 8 张参考图：
- `a_sheet.png`、`b_sheet.png`（角色三视图设定图）
- `a_face.png`、`b_face.png`（角色面部表情特写）
- `venue.png`（舞台全景）、`crowd.png`（观众群像）、`dj.png`（DJ 台）、`hecklers.png`（欢呼观众）
- 生成横竖版封面：
  ```bash
  python3 workflows/05_ancient_rap_battle/scripts/cover.py \
    workflows/05_ancient_rap_battle/episodes/edison-vs-tesla
  ```

#### Step 4：生成分镜表、半身参考图与剪辑时间线（`make_clips.py`）
```bash
python3 workflows/05_ancient_rap_battle/scripts/make_clips.py \
  workflows/05_ancient_rap_battle/episodes/edison-vs-tesla
```
- 自动从 `a_sheet.png` / `b_sheet.png` 裁切半身特写 `work/a_bust.png` 与 `work/b_bust.png`（防止全身参考图导致 H3 拍出远景小人）。
- 输出 `work/clips.json`、`work/edl.json` 与中文可读版 `分镜表.md`。

#### Step 5：在 Colab G4 上批量生成 12 个 H3 视频分镜（`run_rap_battle_remote.py`）
通过本地编排器连接 Colab G4（96GB Blackwell GPU），在云端启动 ComfyUI `MiniMaxH3ReferenceToVideo` 8 步极速工作流，生成 `1344x768 @ 24fps`、124 帧（严格遵循 `17k+5` Group-Phase Ladder 规则）的分镜视频：
```bash
# 生成全部 12 个分镜（或通过 --ids A01 A02 指定重绘单个分镜）
python3 workflows/05_ancient_rap_battle/run_rap_battle_remote.py \
  --episode workflows/05_ancient_rap_battle/episodes/edison-vs-tesla \
  --steps 8
```
> ⚠️ **算力保护铁律**：云端渲染拉取回本地 `clips/` 后，必须立即把原始未修改分镜备份到 `clips/raw_h3/`，并执行 `colab_Burst_Workspace.py --action teardown` 释放 G4 实例，确保 `0.00 CCU/h`。

#### Step 6：本地 Apple M6 口型对齐与验证（`align_and_lipsync.py` & `lipcheck.py`）
```bash
# 运行完整时间轴扭曲 + 768p 下唇驱动 + 闭唇融合 + 自动检测
MPLCONFIGDIR=/tmp/mpl_cache /tmp/lipsync_venv/bin/python \
  workflows/05_ancient_rap_battle/scripts/align_and_lipsync.py \
  workflows/05_ancient_rap_battle/episodes/edison-vs-tesla

# 单独运行原版 lipcheck.py 查看各分镜嘴部开合与音频相关性
/tmp/lipsync_venv/bin/python workflows/05_ancient_rap_battle/scripts/lipcheck.py \
  workflows/05_ancient_rap_battle/episodes/edison-vs-tesla
```

#### Step 7：成片拼接与字幕包装（`assemble.py` & `package.py`）
```bash
python3 workflows/05_ancient_rap_battle/scripts/assemble.py \
  workflows/05_ancient_rap_battle/episodes/edison-vs-tesla && \
python3 workflows/05_ancient_rap_battle/scripts/package.py \
  workflows/05_ancient_rap_battle/episodes/edison-vs-tesla --phone && \
cp workflows/05_ancient_rap_battle/episodes/edison-vs-tesla/final/Edison_vs_Tesla_成片_手机预览.mp4 \
   workflows/05_ancient_rap_battle/episodes/edison-vs-tesla/final/Edison_vs_Tesla_竖屏.mp4
```

---

## 三、已经制作的东西（Inventory of Produced Assets & Code）

### 3.1 最终成片与预览视频（`episodes/edison-vs-tesla/final/` & `preview/`）

| 文件路径 | 分辨率 / 帧率 / 时长 | 说明 |
| :--- | :---: | :--- |
| `final/Edison_vs_Tesla_成片.mp4` | `1344x768` · `24fps` · `30.76s` (79.3 MB) | **16:9 正式横屏成片**：含 Grade B 胶片调色、金色书法歌词字幕（尾词红刷放大）、底部白字历史考据注释、角色登场铭牌、片头/片尾大字标题、水印及立体声双男声混音 |
| `final/Edison_vs_Tesla_竖屏.mp4` | `1280x732` · `30fps` · `30.77s` (8.15 MB) | **手机端轻量预览版**（与 `final/Edison_vs_Tesla_成片_手机预览.mp4` 相同，`< 10 MB` 便于移动端秒开预览） |
| `final/Edison_vs_Tesla_分镜预演版.mp4` | `1344x768` · `24fps` · `30.75s` (73.1 MB) | **前期动态分镜预演版（Animatic）**：调用云端 GPU 前用于确认节奏、字幕与音乐卡点的静态图推拉预演视频 |
| `preview/成片_拼接.mp4` | `1344x768` · `24fps` · `30.76s` | 12 个分镜按 `work/edl.json` 拼接后的无字幕净版源片（供 `package.py` 读取） |
| `preview/草稿.mp4` | `1344x768` · `24fps` · `30.76s` | `assemble.py` 输出的无字幕拼接草稿（现已与 `成片_拼接.mp4` 自动保持同步） |

### 3.2 12 个视频分镜资产（`episodes/edison-vs-tesla/clips/`）

- **原始 H3 生成备份（`clips/raw_h3/`）**：
  - `A01_t1.mp4`、`A02_t1.mp4`、`A03_t1.mp4`、`A04_t1.mp4`（Edison 4 个说唱镜头，均为 `1344x768 @ 24fps`，124 帧 `5.167s` 未修改原片）
  - `B01_t1.mp4`、`B02_t1.mp4`、`B03_t1.mp4`、`B04_t1.mp4`（Tesla 4 个说唱镜头，均为 `1344x768 @ 24fps`，124 帧 `5.167s` 未修改原片）
- **口型对齐后的工作分镜（`clips/`）**：
  - `A01_t1.mp4` ～ `B04_t1.mp4`（经 `align_and_lipsync.py` 时间轴扭曲与 768p 嘴部开合驱动后的分镜，时长匹配 `edl.json` 各句时长 `+ 0.25s` 余量）
- **过场与反应分镜（`clips/`）**：
  - `OPEN_t1.mp4`（`0.00–2.45s`：发电厂舞台开场推镜）
  - `DJ_t1.mp4`（`13.46–14.53s`：蒸汽朋克发电机 DJ 搓碟过场）
  - `B_REACT_t1.mp4`（`14.53–15.41s`：Tesla 手持紫色电弧特斯拉线圈冷笑蓄力反应镜头）
  - `END_t1.mp4`（`26.41–30.76s`：Tesla 高举电弧线圈致意、镜头拉升俯瞰全场欢呼结尾）

### 3.3 音频、时间戳与工程配置数据（`episodes/edison-vs-tesla/work/`）

| 文件路径 | 说明 |
| :--- | :--- |
| `work/kie_suno.json` | Kie.ai Suno V5 返回的完整元数据与 `alignedWords` 逐词毫秒级时间戳 |
| `work/suno_v1.mp3` / `work/suno_v2.mp3` | Suno V5 生成的两版原始完整歌曲（当前采用 `suno_v2.mp3`） |
| `work/vocals_cut.wav` / `work/inst_cut.wav` | 裁剪至 30.76 秒的原始人声干声与纯伴奏 |
| `work/voc_a.wav` / `work/voc_b.wav` | 音色分离重塑后的 Edison 专属男中音干声（`-2.2` 半音）与 Tesla 专属男高音干声（`+1.8` 半音） |
| `work/vocals_final.wav` / `work/music_final.wav` | 按 `lines.json` 时间窗口拼接 A/B 双音色干声后的最终人声轨与最终立体声总混音（等于根目录 `音乐_最终.wav`） |
| `work/audio/A01.wav` ～ `B04.wav` | 各分镜对应的独立干声切片（经词边界包络门控去噪，用于 H3 生成与本地口型对齐） |
| `work/lines.json` / `work/edl.json` / `work/clips.json` | 8 句歌词精确起止时间表、12 镜头剪辑决策表（EDL）、12 镜头 H3 结构化提示词配置 |
| `work/lipcheck_report.json` | 8 个说唱分镜的最新口型同步检测报告（含 `vowel_corr_at_0`、`rms_corr_at_0`、`mouth_open_max/min`、`syllable_dyn`） |

### 3.4 视觉设定图与封面资产（`refs/` & `cover/`）
- **角色与场景参考图（`refs/`）**：`a_sheet.png`（Edison 全身设定）、`b_sheet.png`（Tesla 全身设定）、`a_face.png`、`b_face.png`、`a_bust.png`、`b_bust.png`、`venue.png`、`crowd.png`、`dj.png`、`hecklers.png`。
- **封面图（`cover/`）**：`封面_横版.jpg`（16:9）、`封面_竖版.jpg`（9:16）、`封面_底图.png`。

### 3.5 核心脚本清单（`workflows/05_ancient_rap_battle/scripts/`）

| 脚本名称 | 功能职责 |
| :--- | :--- |
| `kie_suno.py` | 调用 Kie.ai Suno V5 生成歌曲、获取逐词时间戳、分离人声伴奏、裁剪 30s 片段、合成 Edison/Tesla 双男声音色 |
| `make_clips.py` | 根据 `episode.json` 和 `lines.json` 自动裁切半身图、套用 `M1–M14` 运镜模板生成 `clips.json`、`edl.json` 和 `分镜表.md` |
| `h3_colab_runner.py` | 运行在 Colab G4 上的 ComfyUI `MiniMaxH3ReferenceToVideo` 批量生成脚本（严格遵循 6 段式 `ref-en.txt` 提示词规范与 124 帧 `17k+5` 规则） |
| `run_rap_battle_remote.py` | 本地远程编排器：自动通过 SSH 在 Colab G4 上同步资产、执行 `h3_colab_runner.py` 并将生成的 `.mp4` 拉回本地 |
| `align_and_lipsync.py` | **本地 Apple M6 核心口型对齐流水线**：包含词边界强锚定时间轴扭曲、F1/F2 元音共振峰音节提取、768p 微分同胚下唇驱动、麦克风金属掩码保护与闭唇仿射融合 |
| `wav2lip_arch.py` | PyTorch Wav2Lip 模型定义与梅尔频谱提取模块 |
| `assemble.py` | 按 `edl.json`、`picks.json`、`shifts.json` 将 12 个分镜与 `music_final.wav` 拼接为 `preview/草稿.mp4` 并自动同步至 `preview/成片_拼接.mp4` |
| `package.py` | 为拼接好的视频添加 Grade B 胶片调色、Pillow 金色书法字幕、历史注释、角色铭牌、片头片尾与观众欢呼音效，输出 `final/` 成片 |
| `cover.py` | 合成 16:9 横版与 9:16 竖版对决封面 |
| `lipcheck.py` / `qa.py` | MediaPipe 嘴部开合度与音频包络互相关检测工具 / 画面质量检查工具 |

---

## 四、遇到的问题与解决方案复盘（Problems Encountered & Solutions）

### 问题 1：Suno 生成的对决歌曲中，爱迪生和特斯拉是同一个人的声音
- **现象**：第一版成片中，虽然歌词分了 A（Edison）和 B（Tesla）两段，但 Suno 单曲默认由同一个 AI 男声唱完，听感上不像两个人在 Battle。
- **原因**：Suno 在 30 秒短片段内难以仅靠 `[Edison]` / `[Tesla]` 标签强制切换完全不同的声带模型。
- **解决方案（`scripts/kie_suno.py`）**：
  1. 调用 Kie.ai 的 `separate-vocals` 接口将歌曲拆分为纯人声干声（`vocals_cut.wav`）和纯伴奏（`inst_cut.wav`）。
  2. 使用 `ffmpeg` 的 `asetrate + aresample + atempo` 结合均衡器（EQ），对 Edison 段落（`0 ~ 14.5s`）做 `-2.2` 半音降调 + `160Hz` 低频增厚，塑造成苍老浑厚的工业大亨男中音（`work/voc_a.wav`）；对 Tesla 段落（`14.5s ~ 30.76s`）做 `+1.8` 半音升调 + `2800Hz` 中高频提亮，塑造成锐利高能的青年发明家男高音（`work/voc_b.wav`）。
  3. 在精确保持每一毫秒节奏不变的前提下，将两轨人声与伴奏重新混音为 `work/music_final.wav`。

---

### 问题 2：初版 H3 视频中麦克风挡嘴、部分镜头景别过远（小人）、且句尾嘴巴还在乱动
- **现象**：
  1. 初版生成中，人物把复古银色麦克风举在正对嘴唇的位置，挡住了大半张嘴；
  2. `B01`、`B04` 出现了全身/远景镜头，人物脸部过小看不清口型；
  3. 每句台词唱完后，人物嘴巴仍然继续张合。
- **原因**：
  1. 提示词未明确限定麦克风高度；
  2. 传入了全身设定图（`a_sheet.png`）给近景镜头；
  3. `cut_audio()` 截取 5.167 秒音频时把下一句开头的歌声也截了进来，导致 H3 在后半段继续张嘴。
- **解决方案（`scripts/make_clips.py` & `scripts/h3_colab_runner.py`）**：
  1. **强制麦克风高度**：在所有说唱提示词中加入硬性约束：`holding the silver corded microphone at upper-chest height a few inches below his chin so his mouth and lips remain 100% uncovered`。
  2. **强制半身参考图与近景景别**：所有说唱镜头（`A01–B04`）统一使用裁切后的半身图 `a_bust.png` / `b_bust.png`，并在提示词首段声明 `FRAMING (most important): this is NOT a wide shot... extreme close-up, close-up, chest-up or waist-up`。
  3. **音频静音填充对齐 124 帧窗口**：修改 `cut_audio()`，仅截取当前句时长 `dur = b - a`，在句尾做 `0.05s` 淡出后使用 `apad=whole_dur=5.167` 填充纯静音至 5.167 秒，使 H3 在后半段（约 `2.5s–5.17s`）自然闭嘴静止。

---

### 问题 3：为什么之前调整口型时「第一个分镜 A01 对得上，后面的 A02–B04 对不上」？
经过逐帧提取 MediaPipe 468 点面部特征与音频包络对比，定位到 **3 个叠加的技术原因**：
1. **原因 A（`A03`、`A04` 后半句闭嘴）—— 原始 H3 视频仅前 `2.3s–2.8s` 有张嘴动作**：
   - 因 `cut_audio()` 在后半段填充了静音，H3 原始视频仅在 `[0.0s .. 2.5s]`（前 64 帧）有张嘴动作，`[2.7s .. 5.17s]`（65~123 帧）完全闭嘴（`raw_mo < 0.005`）。
   - `A01` 的时间映射节点恰好落在 `[0.44s, 2.35s]` 内；而此前无约束搜索将 `A03`（`te=3.74s`）和 `A04`（`te=3.43s`）的后半句拉到了 `2.5s` 之后的闭嘴静止帧，导致后半句有歌声但画面嘴巴紧闭。
   - **修复**：在 `optimize_word_anchored_warp()` 中将每句首尾单词 `[w_start, w_end]` 严格锚定在 H3 活跃张嘴区间 `[raw_t0, raw_t1]` 内。
2. **原因 B（`B03`、`B04` 双人同框跟错人）—— 双人镜头的主唱全部站在画面左侧**：
   - H3 生成的 4 个双人镜头（`A02`、`A04`、`B03`、`B04`）均遵循「主唱在左、旁听者在右」的构图规则（左侧 `x < 0.58 * W` 为持麦说唱主角）。
   - 早期代码按 `who == "b"` 裁剪右半屏检测人脸，导致在 `B03`、`B04` 中追踪并驱动了右侧闭嘴旁听的爱迪生，而左侧真正持麦说唱的特斯拉未被驱动。
   - **修复**：在 `detect_faces_in_frames()` 中对所有 `two_shot=True` 镜头统一裁剪左半屏（`x in [0 .. 0.58*W], y in [0 .. 0.82*H]`），人脸检测命中率提升至 `124/124` 帧且 100% 锁定持麦主唱。
3. **原因 C（`A02`、`B01`–`B03` 音节粘连不合拢）—— 齿音高频导致全频段 RMS 包络不归零**：
   - Suno 干声经过压缩，且英文辅音（`s/t/k` 等 `> 3500 Hz` 齿音）能量高，全频段 RMS 在单词间隙仍维持在 `0.30~0.50`，导致嘴巴持续半张、缺乏一词一开合的节奏感。
   - **修复**：在 `compute_vowel_syllable_envelope()` 中引入 4 阶巴特沃斯带通滤波器，仅提取决定张嘴幅度的 **F1/F2 元音共振峰频段（`300–2400 Hz`）**，并扣除 5 帧滑动极小值（`minimum_filter1d`），使每个元音核心处包络冲上 `1.0`、每个辅音闭合处归零至 `0.0`。

---

### 问题 4：局部口型驱动出现「八字胡重影」、「麦克风顶边水平割裂线」与「大幅回退选帧导致头部跳帧」
- **现象**：
  1. 直接使用 Wav2Lip `96x96` 贴片替换 `1344x768` 高清人脸时，嘴部模糊且出现双下巴/双胡子伪影；
  2. 改用 768p 位移场驱动时，若在上下唇分界线 `seam_y` 使用 `1.6px` 阶跃函数或包含下巴区域（`pts[152]`），会在银色麦克风顶部切出一条水平割裂线，并在张嘴时把特斯拉的黑色八字胡向下复制一层；
  3. 若选帧窗口允许大幅向前回退（如 `±11 帧`），人物头部和手部动作会出现肉眼可见的来回抽动（跳帧）。
- **解决方案（`scripts/align_and_lipsync.py`）**：
  1. **严格微分同胚（Diffeomorphic）下唇位移场**：将高斯位移场严格限制在下唇本体（`pts[14]` 与 `pts[17]` 中点），禁止触碰下巴 `pts[152]`，并强制位移导数满足 $|\partial \text{disp}_y / \partial y| \le 0.41 < 1$（即 `|dy_lower_lip| <= 0.68 * sigma_y`），从数学上保证像素映射严格单调、绝不折叠或产生水平折痕。
  2. **HSV 金属麦克风保护掩码（`mic_keep`）**：自动识别下唇下方低饱和度、高明度（`S < 48, V > 105`）的银色金属麦克风像素并将位移权重置零，保证麦克风 100% 稳固不变形。
  3. **鼻底锚定（`pts[61, 291, 2]`）闭唇仿射融合 + 单调选帧约束**：限制局部选帧最多微退 2 帧以保证头部动作平滑，并在辅音闭合帧（`delta_mo < -0.008`）以左右嘴角与鼻底构成的稳固三角形将同镜头原生 768p 闭嘴帧仿射对齐融合至唇部区域。

---

### 问题 5：为什么多次重跑后「成片画面跟之前一模一样，没有任何改善」？
- **现象**：在修复了 `align_and_lipsync.py` 并运行 `assemble.py` + `package.py` 后，打开 `final/Edison_vs_Tesla_成片.mp4` 发现画面与两天前完全一致。
- **根本原因（脚本读写路径断层 Bug）**：
  - `assemble.py` 第 31 行默认输出路径为 `--out preview/草稿.mp4`；
  - 而 `package.py` 第 176 行默认输入源为：
    ```python
    src = a.src or next(p for p in ("preview/成片_拼接.mp4", "preview/最终剪辑.mp4") if os.path.exists(os.path.join(ep, p)))
    ```
  - 因为目录下存在一个生成于 **11 月 5 日 22:56**（第一版单人声音 `suno_v1` 时期）的旧文件 `preview/成片_拼接.mp4`，导致每次运行 `assemble.py` 都只更新了 `preview/草稿.mp4`，而 `package.py` 每次都去读取 11 月 5 日的 `preview/成片_拼接.mp4` 旧视频流并配上新歌音频！
  - 这也彻底解释了为什么之前看 `成片.mp4` 时「只有第一个分镜对得上，后面的全对不上」——因为旧版 `suno_v1` 视频与新版 `suno_v2` 音频只有第一句同在 `2.45s` 入场，后面所有分镜切点完全不同！
- **解决方案（已固化至 `scripts/assemble.py` 第 81–83 行）**：
  - 修改 `assemble.py`，当输出 `preview/草稿.mp4` 时自动调用 `shutil.copy` 同步覆盖 `preview/成片_拼接.mp4`，彻底消除中间文件断层。
