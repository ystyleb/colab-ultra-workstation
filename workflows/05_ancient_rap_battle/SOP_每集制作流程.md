# 05 号 · 历史说唱对决：每集制作 SOP（从选题到上线）

> 依据第 1 集 `episodes/edison-vs-tesla-full/`（2026-11-08 ~ 11-09）的完整制作过程整理。
> 节奏：**每周 2 集长视频 + 每集 3 条竖版 Shorts**，频道 YouTube **@makeitrap**（英文）。
> 各环节「为什么这样做」和踩坑细节见 [经验沉淀_完整版样片.md](经验沉淀_完整版样片.md)，频道运营与文案模板见 [channel/频道方案.md](channel/频道方案.md)。
> **2026-11-10 起有第二种拍法**（手持麦 + 真实运镜 + 一条口型镜头跨多句 + 句中切反应），第 4～7 节的分镜和出片方式不同，见 [经验沉淀_运镜拍法.md](经验沉淀_运镜拍法.md) 第 4、8 节，模板是 `episodes/edison-vs-tesla-remake/build_storyboard.py`。

---

## 0. 总览

| # | 环节 | 产出 | 花费 | 用时 | 谁做 |
|---|---|---|---|---|---|
| 1 | 选题 + 歌词 | `episode.json`、`歌词_完整版.md`、`line_actions.json` | 0 | 1 小时 | Claude 写，**用户确认** |
| 2 | 生成歌曲 | `work/kie_suno.json`、`lines.json`、`words_edit.json`、`grid.json` | Kie 约 13 额度 | 10 分钟 | Claude |
| 3 | 参考图 | `refs/*.png`、`work/*_face_clean.png`、`work/stage_a/b.png` | 0（复用）或生图 | 30 分钟 | Claude |
| 4 | 分镜 | `work/clips.json`、`edl.json`、`fx.json`、`live.json` | 0 | 30 分钟 | Claude |
| 5 | 小样 | 2～3 个镜头的对比片 | 约 1 CCU | 15 分钟 | Claude，**用户看片** |
| 6 | 批量出片 | 32 个口型镜头 + 非口型镜头 | 约 5～7 CCU | 30～40 分钟 | Claude |
| 7 | 质检 + 重抽 | 拼帧图、音轨相关度 | 每轮约 1～2 CCU | 按需 | Claude，**用户看片** |
| 8 | 合成 + 打包 | `final/*_成片.mp4`、1080p 上传版 | 0 | 5 分钟 | Claude |
| 9 | Shorts × 3 | 3 条 9:16 成片 + 1080×1920 上传版 | 约 4 CCU | 40 分钟 | Claude |
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
   - 每集的场景风格（第 2 集起）：`suno_style`（曲风/配器）、`light_en`（光线）、`arena_sound_en`、`crowd_motion_en`（台下观众怎么跟着音乐动）。不写就用第 1 集的默认值
   - **两人固定站位**：A 永远在左、B 永远在右，`venue_en` 里左边只放 A 的元素、右边只放 B 的元素
   - **道具名就是提示词**：避开会把模型带偏的词（「laurel-leaf crown」被画成镶宝石王冠，改成「laurel wreath」才对）
3. `line_actions.json`：32 句每句一个手势/动作（英文短语）。
4. 写 `歌词_完整版.md` 给用户确认。**歌词里避开像制作人署名的词**（如 "fifty grand"），Suno 会拒收。

## 2. 生成歌曲

```bash
python3 scripts/kie_suno.py episodes/<ep>          # 生成 2 版，自动挑词级对齐最好的一版
python3 scripts/kie_suno.py episodes/<ep> --reuse  # 只重算双声线 / lines.json，不重新花钱
```

检查：
- `work/lines.json` 有 32 句，每句的 `start/end` 合理（一小节约 2.5 秒）
- `work/words_edit.json`（词级时间轴）由脚本自动写出，分镜断言和甩镜避让都靠它
- Suno 可能跳过写好的观众段，导致上一个词被拉长（第 1 集 A16 的 "for?" 拉到 2.9 秒，第 2 集 A16 的 "blood" 拉到 3.3 秒，都是第四段前那个 OOOH）。这种情况镜头保持在歌手身上，不要切走

## 3. 参考图

- 用 Codex 生图（0 CCU，5 张并行约 10 分钟），提示词存在剧集的 `ref_prompts/*.txt`，照第 2 集改：
  `codex exec --skip-git-repo-check -C /tmp/<ep>_refs/<name> -s workspace-write -o last.txt "$(cat ref_prompts/<name>.txt)" < /dev/null`
- 人像直接生成 1024 见方的**单张无麦无道具**胸像，存成 `work/a_face_clean.png` / `b_face_clean.png`（也复制一份到 `refs/a_face.png`）。第 1 集是 2×2 四宫格裁出 512 小图放大，画质差
- `refs/venue.png`（擂台全景，左边是 A 的元素、右边是 B 的）、`crowd.png`、`dj.png`，都是 1344×768
- 统一背景：从 `venue.png` 左右各裁一块 768×768，作为 `work/stage_a.png` / `stage_b.png`
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
python3 run_rap_battle_remote.py episodes/<ep> --ids A01 B03 WIDE_OPEN \
  --runner-args "--fit --lock-strength 1.0 --mic stand --static-cam --tag s1" --no-post
```

- 挑一个口型近景、一个远景、一个大全景；新写法（新机位、新背景）一定先做小样
- 做成对比片（ffmpeg 拼田字格 / 上下对比）给用户看，确认再批量

## 6. 批量出片

```bash
python3 run_rap_battle_remote.py episodes/<ep> \
  --runner-args "--fit --lock-strength 1.0 --mic stand --static-cam" --no-post
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
python3 scripts/assemble.py episodes/<ep>              # → preview/草稿.mp4
python3 scripts/package.py episodes/<ep>               # → final/<title>_成片.mp4（字幕、铭牌、片头片尾）
python3 scripts/package.py episodes/<ep> --phone       # → 手机预览版
# 1080p 上传版（H3 原生 1344×768）
ffmpeg -i final/<title>_成片.mp4 -vf "scale=1920:1097:flags=lanczos,crop=1920:1080:0:8,unsharp=5:5:0.35:5:5:0,setsar=1" \
  -c:v libx264 -preset slow -crf 17 -maxrate 20M -bufsize 40M -pix_fmt yuv420p -movflags +faststart -c:a copy final/<title>_1080p_上传版.mp4
```

每 4 秒抽一帧拼图看全片；打开成片给用户验收。

## 9. Shorts × 3

1. 在 `build_shorts.py` 里定义 3 段（每段一个人连续 4 句，选最狠的），以及每条的引子文案 `HOOK_SUB`
2. 构建迷你剧集：`python3 episodes/<ep>/build_shorts.py`（重跑不会清掉已渲染的 picks）
3. 渲染竖版（每条约 1.3 CCU）：
   ```bash
   python3 run_rap_battle_remote.py episodes/<ep>/shorts/<sid> --runner-args "--fit --lock-strength 1.0 --mic stand --static-cam" --no-post
   ```
4. 合成打包：`assemble.py shorts/<sid> --size 768x1344` → `package.py shorts/<sid>`
5. 1080×1920 上传版：`scale=1098:1920:flags=lanczos,crop=1080:1920,unsharp=...`，码率封顶 16M
6. 检查：开头 2.6 秒有「A VS B」引子；结尾最后一句歌词消失后才出「FULL BATTLE ON THE CHANNEL」

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
- 标题、简介（第一行放带 UTM 的网站链接；章节时间戳；THE HISTORY BEHIND THE BARS 史实出处；AI 声明）、缩略图
- 不面向儿童、无付费宣传、**AI 内容：是**、标签、语言英语、类别娱乐
- 公开发布 → 发置顶评论（Team A or Team B? + 网站链接）

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
