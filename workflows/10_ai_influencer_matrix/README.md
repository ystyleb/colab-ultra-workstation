# 🎭 工作流 10：AI 虚拟人矩阵 × 零月租数字产品变现 SOP（`10_ai_influencer_matrix`）

本工作流是 **Mark Tilbury「7 天 AI 虚拟网红变现实验」** 的实战升级版与本仓库零月租工业化落地管线，覆盖 **Wealth（Vivian · 谈钱、花钱与边界）/ Relationships（June · 关系里的小动作）/ 休息与分寸（Henry Wen · 茶铺与庄子）** 三个赛道，并修补了原实验中的三大漏损。

> **2026-11-17 起为 V3.1 阵型**：人设、台词规则、产品和盲听记录以 `PERSONA_BIBLE_V3.md` 为准（决策过程见 `PERSONA_STRATEGY_BRIEF.md`）。旧 V2 阵型（Elias / Sienna）的配置、关键帧规范和脚本备份在 `work/archive/`。下面的三大漏损和管线说明仍然适用，产品形态已按 V3.1 调整（Wen 的产品不设打卡）。


1. **全账号 Day-1 预埋变现基建**：三个账号发第 1 条视频前均备齐 **免费诱饵 PDF + \$14–\$15 付费手册 + \$9 结账加购项**（杜绝类似 Grandma Vivian 单条破 25 万播放却无货可卖的遗憾）。
2. **双级漏斗替代纯 Bio 跳转**：脚本结尾统一引导评论关键词（`RULES` / `NOTICE` / `TEA`）触发 **ManyChat 自动私信发免费 PDF → 追销付费手册**，同时拉高算法评论权重与私信点击率。
3. **100% 复用仓库零月租工具链**：用 **Codex 0-CCU 关键帧锁脸** + **Colab L4 英文音色种子/对白 (`1.71 CCU/h`)** + **Colab G4 `MiniMax-H3 Ref2VA` (`10.05 CCU/h`)** + **本地 0-CCU PIL 自动字幕与 1080×1920 超分**，替代原视频中 \$99/月的第三方订阅工具。

---

## 📂 目录结构

```text
10_ai_influencer_matrix/
├── README.md                          # 本操作总览
├── PERSONA_BIBLE_V3.md                # V3.1 人设档案：风控线、写作约束、产品、盲听记录（写脚本前的唯一依据）
├── PERSONA_STRATEGY_BRIEF.md          # 选人设的决策过程
├── script_check.py                    # 0-CCU 脚本检查（字数 / 预告收尾 / 风控词 / 横幅字符）+ 生成盲听卷
├── FUNNEL_AND_STORE_COPY.md           # IG/YT/TikTok/Gumroad/ManyChat 一键复制上线手册与 14 天排期
├── influencer_config.json             # 三大人设、声线 F0 区间、双场景、H3 参数与双阶产品配置
├── scripts_30_manifest.json           # 30 条英文口播脚本（V01-V10, J01-J10, W01-W10）
├── keyframes.json                     # 7 张 9:16 锁脸锚点规范（Vivian jet 仅作身份基准 + 三人各两场景）
├── gen_keyframes.py                   # 0-CCU Codex 关键帧生成器 + 3×2 质检总览拼图
├── build_digital_products.py          # 0-CCU 渲染 6 本 A4 PDF（共用样式 + Headless Chrome 渲染与页数校验）
├── products_v3.py                     # V3.1 六本产品的内容（Vivian / June / Wen 各一本免费 + 一本付费）
├── make_store_and_profile_assets.py   # 0-CCU 生成 800×800 头像与 1280×720 Gumroad 封面
├── cloud_influencer_tts.py            # 云端 L4 独立双引擎英文 TTS 生成器（含 F0 Pitch Guard 与 17k+5 帧对齐）
├── run_influencer_tts_remote.py       # 本地遥控器：L4 TTS（支持 --dry-run / --pull-only / 计费包裹）
├── cloud_influencer_h3.py             # 云端 G4 MiniMax-H3 Ref2VA 9:16 批量口播生成器（铁律 F）
├── run_influencer_video_remote.py     # 本地遥控器：G4 H3 批量出片（支持 --dry-run / --pull-only / 计费包裹）
├── subtitle_and_finalize.py           # 本地 0-CCU 1080×1920 超分 + 声学包络动态短语字幕 + Hook 贴片（含 --self-test）
├── sample_inputs/                     # 768×1344 人物参考图（入库；elias/sienna 为旧阵型遗留）
├── products/                          # V3.1 可打印 A4 PDF（免费 4–5 页 / 付费 11 页；V2 旧版在 work/archive/products_v2/）
├── work/                              # 原始生图、HTML 源码、L4 WAV 缓存（gitignored）
├── out/                               # 头像、店铺封面与总览看板（gitignored）
└── outputs/                           # 云端原始成片与终版 1080×1920 成品（gitignored）
```

---

## 🛠️ Phase 1：本地 0-CCU 备料与自检命令

```bash
# 0. 改脚本后先跑检查（不通过 exit 1）
python3 workflows/10_ai_influencer_matrix/script_check.py

# 1. 生成锁脸关键帧（首次调用 codex 需放行网络）
python3 workflows/10_ai_influencer_matrix/gen_keyframes.py --skip-existing -j 3

# 2. 渲染 V3.1 免费/付费 PDF 数字产品
python3 workflows/10_ai_influencer_matrix/build_digital_products.py

# 3. 生成头像、Gumroad 封面与可视化总览看板
python3 workflows/10_ai_influencer_matrix/make_store_and_profile_assets.py

# 4. 0-CCU 预演云端 L4 TTS 与 G4 视频管线 + 本地字幕合成自测
python3 workflows/10_ai_influencer_matrix/run_influencer_tts_remote.py --dry-run
python3 workflows/10_ai_influencer_matrix/run_influencer_video_remote.py --dry-run
python3 workflows/10_ai_influencer_matrix/subtitle_and_finalize.py --self-test
```

---

## 🚀 Phase 2：云端 GPU 批量生产命令（⚠️ 消耗 CCU，开跑前先确认）

建议先跑 **3 条试水首映包（`V01,J01,W01`，三人设各 1 条）**，验证口型、声线与完播表现后再全量开跑 30 条：

### A. 3 条试水首映包（预计总计 ~2.7 CCU）
```bash
# 1) Colab L4 合成 V01,J01,W01 英文配音（约 4.4 分钟 ≈ 0.13 CCU）
python3 workflows/10_ai_influencer_matrix/run_influencer_tts_remote.py --ids V01,J01,W01 --mode qwen

# 2) Colab G4 批量生成 3 条 9:16 Ref2VA 口播（约 15.3 分钟 ≈ 2.56 CCU）
python3 workflows/10_ai_influencer_matrix/run_influencer_video_remote.py --ids V01,J01,W01

# 3) 本地 0-CCU 超分至 1080×1920 + 烧录 Hook 与动态字幕
python3 workflows/10_ai_influencer_matrix/subtitle_and_finalize.py --ids V01,J01,W01
```

### B. 30 条全量矩阵包（预计总计 ~19.1 CCU）
```bash
# 1) Colab L4 一次开机合成全部 30 条英文配音（约 8.2 分钟 ≈ 0.23 CCU）
python3 workflows/10_ai_influencer_matrix/run_influencer_tts_remote.py --mode qwen

# 2) Colab G4 一次热机连出 30 条 9:16 口播（约 112.5 分钟 ≈ 18.84 CCU）
python3 workflows/10_ai_influencer_matrix/run_influencer_video_remote.py

# 3) 本地 0-CCU 一键批量出终版成品
python3 workflows/10_ai_influencer_matrix/subtitle_and_finalize.py
```
