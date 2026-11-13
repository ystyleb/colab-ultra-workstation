# 05 号 · 历史说唱对决：每集制作 SOP（从选题到上线）

> 依据第 1 集 `episodes/edison-vs-tesla-full/`（2026-11-08 ~ 11-09）的完整制作过程整理。
> 节奏：**每周 2 集长视频 + 每集 3 条竖版 Shorts**，频道 YouTube **@makeitrap**（英文）。
> 各环节「为什么这样做」和踩坑细节见 [经验沉淀_完整版样片.md](经验沉淀_完整版样片.md)，频道运营与文案模板见 [channel/频道方案.md](channel/频道方案.md)。
> **2026-11-10 起有第二种拍法**（手持麦 + 真实运镜 + 一条口型镜头跨多句 + 句中切反应），第 4～7 节的分镜和出片方式不同，见 [经验沉淀_运镜拍法.md](经验沉淀_运镜拍法.md) 第 4、8 节，模板是 `episodes/edison-vs-tesla-remake/build_storyboard.py`。
> **2026-11-11 起升级为 Realism V3 电影级实拍标准管线（不加 2.7K 超分，单集仍保持 ~12–16 CCU）**：参考图执行 `python3 scripts/film_optics.py episodes/<ep>` 预置 3200K 暖血色肌肤 + `r=16` 沸腾人群剪影与烛台光学散景；云端开启 `--steps 12 --runner-args "--fit --lock-strength 1.0 --mic handheld --realism-v2"`（调用 `Singularity v1.3` 去油光底模，**默认不加 `--tessera-2k`**，省去 2.7K 约 5 倍额外算力开销）；本地使用 `assemble.py --film` + `package.py --film --1080p` 单通直出 Kodak Vision3 500T + Pro-Mist 1/8 + `c0s=3` 细银盐颗粒 1080p 成片。根因诊断、三轮盲测参数边界与复用模板见 [经验沉淀_电影实拍质感升级.md](经验沉淀_电影实拍质感升级.md)。
> **2026-11-12 ~ 11-13 升级音乐制作（Beat Switch + 咆哮原声）与无麦电影 MV / V2 Shorts 管线（第 5～7 集）**：
> - **音频 V2**：歌词初稿调 Kie Suno `ai-music-api/generate-lyrics`（`0.40` 额度）提取地道俚语、缩写打点（`F.I.B.`）与内生曲风碰撞词条；支持**单曲多幕剧烈 Beat Switch**（如 90s G-Funk ⇄ 失真 808 Trap Metal）；Colab L4（实耗仅 **`0.11–0.55 CCU`**）单次跑完主备双槽 `RVC v2`（含狂暴嗓 `protect=0.44` 防电音档 `rvc_grit`）+ `Seed-VC` 并本地毫秒对齐。详见 [经验沉淀_音乐制作与游戏原声还原.md](经验沉淀_音乐制作与游戏原声还原.md)。
> - **无麦纯电影实景模式 & 多 G4 并行**：支持 `"mic_en": "none"` 解放双手表演 + 三场景叙事切换，且 `run_rap_battle_remote.py` 支持文件锁并发开 3 台 G4 将全集渲染墙钟时间压缩至 ~30 分钟（包体积瘦身至 ~43 MB）。
> - **Battle Shorts V2（`0 CCU` 双雄对轰高转化模板）**：以 `episodes/michael-vs-trevor/build_shorts_v2.py` 为标准，直接复用正片电影镜头零算力合成 `1080×1920` 竖版（`0.0s` 上下分屏双雄对峙 + 多机位反应切镜 + `words_edit.json` 逐词弹跳大字幕 + 结尾前 `3.0s` 左下角金色箭头指引导流条 + 唱完 `+0.14s` 零静音无缝循环）；网站引流独立栏目方案见 [channel/MakeYourOwnShorts_网站引流计划.md](channel/MakeYourOwnShorts_网站引流计划.md)。

---

## 0. 总览

| # | 环节 | 产出 | 花费 | 用时 | 谁做 |
|---|---|---|---|---|---|
| 1 | 选题 + 歌词 | `episode.json`、`歌词_完整版.md`、`line_actions.json` | 0（润色 0.4 Kie） | 1 小时 | Claude 写 + Suno 润色，**用户确认** |
| 2 | 生成歌曲 + 原声还原 | `work/kie_suno.json`、`lines.json`、`音乐_最终.wav`、`vocals_final.wav` | Kie 约 13 额度（+ L4 约 `0.11–0.55 CCU`） | 12～20 分钟 | Claude（**用户听歌确认**） |
| 3 | 参考图 | `refs/*.png`、`work/*_face_clean.png`、`work/stage_a/b.png` | 0（复用）或生图 | 30 分钟 | Claude |
| 4 | 分镜 | `work/clips.json`、`edl.json`、`fx.json`、`live.json` | 0 | 30 分钟 | Claude |
| 5 | 小样 | 2～3 个镜头的对比片 | 约 1.5 CCU | 15 分钟 | Claude，**用户看片** |
| 6 | 批量出片 | 32 个口型镜头 + 非口型镜头（支持 3 台 G4 锁并发） | 约 12～14 CCU | ~30 分钟 | Claude |
| 7 | 质检 + 重抽 | 拼帧图、音轨相关度 | 每轮约 1～2 CCU | 按需 | Claude，**用户看片** |
| 8 | 合成 + 打包 | `final/*_1080p_胶片版.mp4`、手机预览版 | 0 | 5 分钟 | Claude |
| 9 | Shorts V2 × 3 | 3 条 `1080×1920` 双雄对轰胶片版 + 6 帧质检图 | **0 CCU** | 2 分钟 | Claude |
| 10 | 封面 | 横版缩略图 + 3 张 Shorts 封面 | 0（Codex 用 ChatGPT 账号） | 30 分钟 | Claude |
| 11 | 上传发布 | 1 个长视频 + 3 条 Shorts，置顶评论 | 0 | 30 分钟 | Claude 浏览器操作，**用户批准发布** |
| 12 | 提交 + 记录 | git commit、经验更新 | 0 | 10 分钟 | Claude，**用户说「提交」** |

**单集预算**：G4 约 10～15 CCU（首集踩坑用了约 27 CCU），Kie 约 13 额度。每周 2 集约 25～30 CCU。

**必须停下来问用户的节点**：歌词定稿、小样效果、成片验收、公开发布、git 提交、网站部署。

---

## 1. 选题 + 歌词

1. 从 `channel/频道方案.md` 第 5 节选题表里挑一组**已故**历史人物（不做在世的人）。
2. 新建剧集目录 `episodes/<a>-vs-<b>/`，复制上一集的 `episode.json` 改写：
   - `a` / `b`：`name_cn`（显示名，英文频道用英文大写）、`name_en`、`look`、`prop`（**每人一个标志性道具**）、`voice`
   - `venue_en`：场景描述，左右两侧分别放两人的视觉元素
   - `lyrics` + `notes`：两回合，每人每回合 8 句，每句一小节；每句配史实注释，传说和单方说法要标明
   - `structure`：intro → A1-8 → crowd → B1-8 → crowd → A9-16 → crowd → B9-16 → outro
   - 英文频道固定：`"show_notes": false`、`"disclaimer": "AI-GENERATED · FOR ENTERTAINMENT"`、`"end_question": "NEXT BATTLE|WHO DO YOU WANT TO SEE?"`、`"name_card_lines": 1`
   - 每集的场景风格（第 2 集起）：`suno_style`（曲风/配器）、`light_en`（光线）、`arena_sound_en`、`crowd_motion_en`（台下观众怎么跟着音乐动）。**第 4 集起固定开启电影实拍质感**：设 `"film_look": true`、`"mic_en": "vintage chrome handheld microphone with a round mesh head"`，`light_en` 用「`3200K` 暖钨丝伦勃朗侧主光 + `5600K` 冷银顶逆发丝轮廓光 + `2700K` 暖烛台背景散景」双色温模板（直接从 [经验沉淀_电影实拍质感升级.md](经验沉淀_电影实拍质感升级.md) 第 3.3 节复制；避免单色冷光导致脸部青灰，或平光导致塑料感）
   - **两人固定站位**：A 永远在左、B 永远在右，`venue_en` 里左边只放 A 的元素、右边只放 B 的元素
   - **道具名就是提示词**：避开会把模型带偏的词（「laurel-leaf crown」被画成镶宝石王冠，改成「laurel wreath」才对）
3. `line_actions.json`：32 句每句一个手势/动作（英文短语）。
4. **固定执行 Suno 歌词审校与润色（`0.40` Kie 额度，`0 CCU`）**：先在本地写好 32 句初稿骨架（`episode.json` 的 `lyrics` 与可选 `lyrics_polish_prompt`），随后运行：
   ```bash
   python3 workflows/05_ancient_rap_battle/scripts/polish_lyrics_suno.py workflows/05_ancient_rap_battle/episodes/<ep>
   ```
   调 Kie `ai-music-api/generate-lyrics` 生成两版润色稿（自动存档于 `work/suno_lyrics_polish.json`），从中提取地道母语狠词、内韵双押、缩写打点（如 `U.N.S.C.`、`F.I.B.`）与 Suno 内生曲风碰撞 `tags` 回填 `episode.json`，再更新 `歌词_完整版.md` 给用户确认。**歌词里避开像制作人署名的词**（如 "fifty grand"），Suno 会拒收。

## 2. 生成歌曲与人物原声还原

```bash
# 1) Suno V6 生成 2 版底曲 + 词级对齐（约 13 Kie 额度，0 CCU）
python3 scripts/kie_suno.py episodes/<ep>
python3 scripts/kie_suno.py episodes/<ep> --reuse   # 微调 suno_track / intro_keep / outro_keep 重算，不重新花钱

# 2) 游戏/影视等具象原声角色：准备 24s 纯净单人干音（work/<role>_ref_clean.wav）与已校验 RVC v2 链接，跑 L4 原声还原（~0.55 CCU）
python3 scripts/run_game_voice_remote.py episodes/<ep>

# 3) 本地 0 CCU 自由混搭 A/B 最优音高档位并写入正式音轨（work/vocals_final.wav、work/music_final.wav、音乐_最终.wav）
python3 scripts/run_game_voice_remote.py episodes/<ep> --remaster-only --pair-a rvc --pair-b rvc_fifth --out-tag rvc_best
```

检查（详见 [经验沉淀_音乐制作与游戏原声还原.md](经验沉淀_音乐制作与游戏原声还原.md)）：
- `work/lines.json` 有 32 句，每句的 `start/end` 合理（90–96 BPM 下一小节约 2.5 秒）；**不能只看总 `match_score`**，若某一版 `B16`/`A16` 被拉长到 10～30 秒则切另一版
- `work/words_edit.json`（词级时间轴）由脚本自动写出，分镜断言和甩镜避让都靠它；**`song.mp3` 必须保留未裁剪原始曲**，原声母带只覆盖 `音乐_最终.wav`、`work/music_final.wav` 与 `work/vocals_final.wav`
- 参考干音必须过 `P15 < -37 dBFS` 无配乐门限与低通稳频单说话人 `F0` 门控，杜绝混入 BGM 或第二说话人
- Suno 可能跳过写好的观众段，导致上一个词被拉长（第 1 集 A16 的 "for?" 拉到 2.9 秒，第 2 集 A16 的 "blood" 拉到 3.3 秒，都是第四段前那个 OOOH）。这种情况镜头保持在歌手身上，不要切走

## 3. 参考图

- 用 Codex 生图（0 CCU，5 张并行约 10 分钟），提示词存在剧集的 `ref_prompts/*.txt`，照第 2 集改：
  `codex exec --skip-git-repo-check -C /tmp/<ep>_refs/<name> -s workspace-write -o last.txt "$(cat ref_prompts/<name>.txt)" < /dev/null`
- 人像直接生成 1024 见方的**单张无麦无道具**胸像，存成 `work/a_face_clean.png` / `b_face_clean.png`（也复制一份到 `refs/a_face.png`）。第 1 集是 2×2 四宫格裁出 512 小图放大，画质差
- `refs/venue.png`（擂台全景，左边是 A 的元素、右边是 B 的）、`crowd.png`、`dj.png`，都是 1344×768
- 统一背景：从 `venue.png` 左右各裁一块 768×768，作为 `work/stage_a.png` / `stage_b.png`
- **Realism V3 光学预处理（必跑，0 CCU）**：`python3 scripts/film_optics.py episodes/<ep>`（自动备份原图至 `*_raw_orig.png`，将人像规整为 3200K 暖血色电影色域，并将 `stage_a/b.png` 转为 `r=16` T2.2 沸腾观众剪影 + 暖烛台圆盘散景，彻底消除背景 10px 清晰小假人）
- `work/*.png` 被 gitignore，提交时要用 `git add -f`

## 4. 分镜（`episodes/<ep>/build_storyboard*.py`）

第 2 集起以 `napoleon-vs-wellington/build_storyboard.py` 为模板（逐句指定机位，见 `对标分析_曹操VS刘备.md`）：

- **后半句切对手反应（L-cut）**：每回合 2～3 句在指定词处切到对手的反应特写，声音继续；歌手至少留 0.9 秒。反应镜头入点 1.15 秒（H3 开头约 1 秒是摆拍远景）
- **面对面对峙双人（FACE）**：用 `listener_side` 让听的人留在自己固定的那一侧
- **两句一镜的慢推长镜头（LONG）**、**广角推到贴脸（ECU，`lens`）**：节奏长短交替，镜头中位数约 1.8 秒
- **远景不给场景参考图**：只要喂了 `venue.png` / 半边背景图，H3 就把图里的观众照抄成静止画面（观众帧间差 1.36，不给图 5.07）。近景保留半边背景图保证一致
- 非口型镜头全部在脚本里写提示词（`still()`），不依赖旧剧集的 clips.json

以下是第 1 集定下、仍然有效的规则：

- **每句一个口型镜头，唱完才切**：切点取「下一句开口前 0.08 秒」和「本句最后一个词结束后 0.02 秒」中较晚的那个；脚本里有断言兜底
- **机位每回合轮换**：CU、¾ 左、仰拍、越肩双人、CU、¾ 右、仰拍、CU；所有口型镜头带手持环绕（`HAND`）
- **重拳句用真实推近**（`CREEP`，写明起点「starts on a chest-up medium close-up」，不能只写 "push-in"）
- **远景**：每段首句用正面远景，段中再放一个远景。写法用「观众后脑勺占画面下三分之一」，并设 `closeup_lora: 0`；**不要写「从歌手身后反打」**（拍不出来）
- **两人同框必须写清各自拿什么道具**，否则道具会给错人
- 反应镜头只放在 Suno **实际留出的空隙**里；开场、间奏、结尾用大全景
- `work/live.json`：后期现场运镜参数（手持晃动、推拉、甩镜、调色），直接复制上一集
- `fx.json`：重拳词上的数码推近、闪白、震屏、压暗

生成后跑一遍构建脚本，所有断言都要通过。

## 5. 小样（必做）

```bash
python3 run_rap_battle_remote.py episodes/<ep> --ids A01 B03 WIDE_OPEN --steps 12 \
  --runner-args "--fit --lock-strength 1.0 --mic handheld --realism-v2 --tag s1" --no-post
```

- 挑一个口型近景、一个远景、一个大全景；新写法（新机位、新背景）一定先做小样
- 做成对比片（ffmpeg 拼田字格 / 上下对比）给用户看，确认再批量

## 6. 批量出片

```bash
# Realism V3 标准生产模式（Singularity v1.3 12步，不加 --tessera-2k，高性价比直出）
python3 run_rap_battle_remote.py episodes/<ep> --steps 12 \
  --runner-args "--fit --lock-strength 1.0 --mic handheld --realism-v2" --no-post
```

- 只渲染 `picks.json` 里没有的镜头；重抽某几个镜头：先从 `picks.json` 删掉，旧片段备份到 `clips_vN/`
- 会话名每次自动唯一（`rap-g4-<时间戳>`），结束时自动释放 G4 并输出计费核验报告
- 后台跑 + Monitor 盯日志；**结果以日志里的 `exit=` 为准**，不看外层退出码
- 中途 G4 消失：先看 `~/.config/colab-cli/history/<session>.jsonl`，可能是别的进程停的

## 7. 质检

1. **音轨**：日志里每个镜头的 QA 相关度应在 0.87 以上（0.87～0.92 是音频 VAE 编解码的固有损耗，`ok: False` 可忽略）
2. **画面**：每个片段抽开头、中间、结尾三帧拼图，检查：
   - 麦克风有没有挡嘴
   - 道具在不在对的人手里
   - 景别对不对（远景是否真的远）
   - 有没有漂成别的画面（非口型镜头 1～2 秒后容易漂，只用开头一段）
3. 不合格的镜头单独重抽，换 `--seed`。

## 8. 合成 + 打包

```bash
# Realism V3 电影级单通 1080p 直出（消除多重锐化白边、死黑与彩噪，0 CCU）
python3 scripts/assemble.py episodes/<ep> --film --out preview/草稿_胶片母带.mp4
python3 scripts/package.py episodes/<ep> --src preview/草稿_胶片母带.mp4 --film --1080p --phone
# 输出：final/<title>_1080p_胶片版.mp4（可直接上传 YouTube / B站）
```

每 4 秒抽一帧拼图看全片；打开成片给用户验收。

## 9. Shorts × 3（V2 双雄对轰零算力标准版）

> **2026-11-13 起默认采用 V2 双人对轰模板（`0 CCU`，耗时约 2 分钟）**，替代早期单人站桩 13 秒 + 1.8 秒静音挡脸尾卡的 V1 模板（V1 实测划走率 64.9% 且破坏循环重播）。

1. 复制 `episodes/michael-vs-trevor/build_shorts_v2.py` 到新剧集目录，挑选 **3 组最具冲突感的双人交锋段落**（A 铺垫 2 句 → 鼓点相位对齐 `100ms` 升余弦桥接过门 → B 狂暴反杀 4 句 + 对手破防反应切镜，总长 `16–19s`）。
2. 本地一键渲染 3 条 `1080×1920` 胶片级成片与 6 帧质检拼图（`0 CCU`）：
   ```bash
   python3 episodes/<ep>/build_shorts_v2.py
   ```
3. 逐帧核验 `preview/qa_shorts_v2_s{1,2,3}.jpg`：
   - **`0.0s–1.15s` 上下分屏双雄同框开场**：人物脸部无遮挡、无多余麦克风；
   - **逐词弹跳大字幕**：严格落在安全区 `x ∈ [44, 900], y ∈ [1160, 1390]`，避开右侧点赞栏与底部 UI，无豆腐块缺字；
   - **导流条与无缝循环**：最后 `3.0s` 左下角金底箭头条 `TAP RELATED VIDEO BELOW FOR FULL BATTLE` 位于 `@makeitrap` 上方（`y ∈ [1470, 1555]`）；最后一句实唱词结束后 `+0.14s` 直接收尾循环，**严禁保留静音傻站尾卡**。
4. **Shorts 文案铁律**：YouTube 已禁用 Shorts 简介与评论区超链接点击，因此 Shorts 简介中**不放 `https://` 裸链接**，改为 `MakeItRap.com` 极短品牌词 + 引导点击下方关联视频胶囊及 `@makeitrap` 主页首链；上传后**必须在 Studio 编辑页将「相关视频（Related video）」绑定到本集横版长视频并保存**。

## 10. 封面

- **长视频横版缩略图**：改 `channel/make_brand_assets.py` 里的 `thumbnail(...)` 参数（人名、副标题），用剧集的 `cover/frame.png`（`scripts/cover.py --clip <双人同框镜头> --no-mirror` 生成）
- **Shorts 竖版封面**：Codex 生图，方法见 `channel/频道方案.md` 第 9 节：
  ```bash
  codex exec --skip-git-repo-check -C <dir> -s workspace-write -i <参考帧.png> [-i <已有封面当样板>] \
    -o last.txt "$(cat channel/short_cover_prompts/prompt_s1.txt)" < /dev/null
  ```
  三张并排检查拼写、人物、版式一致、无黑边。

## 11. 上传发布（YouTube Studio，浏览器操作）

前提：浏览器当前身份是 **MakeItRap**（右上角头像 → 切换账号）。频道已完成手机号验证。

**长视频**
- 标题、简介（第一行放带 UTM 的网站剧集页链接 `https://makeitrap.com/battles/<slug>?utm_source=youtube&utm_medium=video&utm_campaign=<ep>`；章节时间戳；THE HISTORY BEHIND THE BARS 史实出处；AI 声明）、缩略图
- 不面向儿童、无付费宣传、**AI 内容：是**、标签、语言英语、类别娱乐
- 公开发布 → 发置顶评论（Team A or Team B? + 网站链接）
- **网站同款舞台底图导出（可选，`0 CCU`、<5 秒）**：若本集适合作为 `makeitrap.com` 专属舞台模板，运行 `python3 scripts/export_web_arena_plate.py episodes/<ep> --slug <stage-id>` 自动裁除裸露地板并生成 `768×1344` `r=16` 散景底图到网站 `public/template-assets/<stage-id>-reference.jpg`

**Shorts**（每条）
- 标题带 `#shorts`，简介首行引导看完整版，同样的 AI 声明和链接
- 竖版封面在上传向导「详细信息 → 缩略图 → 上传文件」里直接传
- 发布后到编辑页：「相关视频」设为本集长视频、保存

弹出「我们仍在检查你的内容」时，原创内容点「仍然发布」即可。长视频上传慢（270 MB 约 30 分钟），可以同时在第二个标签页传 Shorts。

**发布后必须核实**：抓公开播放页，`playabilityStatus` 为 `OK`、`isPrivate` 为 `false` 才算公开（`LOGIN_REQUIRED` = 还是私享草稿）。上传向导里给了链接不代表已发布。

文案模板：`channel/频道方案.md` 第 7、8 节。

## 12. 提交 + 记录

- 只提交 05 号相关文件，**不碰其他工作流目录**（别的会话的内容），不用 `git add -A`
- 提交：剧集的 json / 脚本 / 歌词 / song.mp3 / 音乐_最终.wav / 字幕.srt / 封面 jpg；`work/*_face_clean.png`、`stage_*.png` 用 `-f`
- 不提交：clips、final、preview、clips_v*、shorts 的渲染产物、channel/out（都在 .gitignore 里）
- 有新坑：写进 `经验沉淀_完整版样片.md` 和项目 memory

---

## 附：单集检查清单

- [ ] 歌词用户已确认；史实注释标了传说/单方说法
- [ ] lines.json 32 句、对齐合理
- [ ] 分镜断言全部通过（唱完才切、非口型镜头不超长）
- [ ] 小样用户已看
- [ ] 32 个口型镜头音轨相关度 ≥ 0.87；拼帧图无挡嘴、道具正确
- [ ] 成片用户已验收；1080p 上传版
- [ ] 3 条 Shorts：引子、结尾字卡不压歌词；1080×1920 上传版
- [ ] 横版缩略图 + 3 张 Shorts 封面
- [ ] 4 个视频公开（公开页核实）、AI 声明、相关视频、置顶评论
- [ ] G4 全部释放（`colab ls` 无会话，meter Rate 0.00）
- [ ] git 提交、经验更新
