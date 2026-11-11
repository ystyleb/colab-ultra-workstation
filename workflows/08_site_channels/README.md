# 08 · 三个工具站的 YouTube 频道（Songifted / PawMotif / TryOnSwap）

> 定位（2026-11-10 定）：**一站一个独立频道，以给网站引流为主**。和 MakeItRap（先做内容 IP，网站顺带）的做法相反：每条视频本身就是产品演示，观众看完的下一步是去网站试。
> 视频来源（2026-11-10 定）：**上 Colab 做 AI 动态视频**，主要用 H3 FL2VA 首尾帧，沿用 07 号流水线的出片方式。

| 站点 | 卖什么 | 频道名 / Handle / 频道 ID | 方案 |
|---|---|---|---|
| songifted.com | 写进对方名字的定制礼物歌，$49 起，首次可免费试听 45 秒 | **Songifted** · `@songifted` · `UCzeTUCqNXgBSFFpE_iOsZjQ` | [`songifted/频道方案.md`](songifted/频道方案.md) |
| pawmotif.com | 用宠物照片画肖像，6 种画风，$29 | **PawMotif** · `@pawmotif` · `UC8M9W5_TlNenrilxQBTkBJw` | [`pawmotif/频道方案.md`](pawmotif/频道方案.md) |
| tryonswap.com | AI 虚拟试衣（衣服穿到模特身上），按张计费 | **TryOnSwap** · `@tryonswap` · `UCxXCgsXBIbSJ3_naKqeQNvw` | [`tryonswap/频道方案.md`](tryonswap/频道方案.md) |

三个频道都在 2026-11-10 建好，都是挂在 `winsonaibuilder@gmail.com` 下的品牌账号。头像、横幅、简介、2 个 UTM 链接、8 个关键词都已发布，并从公开页核验过（TryOnSwap 的关键词在 Studio 里已保存，公开页同步比较慢）。还没有上传视频；所在国家/地区、联系邮箱、视频水印都没设置。

## 频道素材

```bash
python3 workflows/08_site_channels/make_channel_assets.py            # 三个站全部生成
python3 workflows/08_site_channels/make_channel_assets.py --site pawmotif
```

- 输出 `out/<site>/avatar_800.png`、`banner_2560x1440.png`、`_banner_check.png`（青框 = 电脑端可见区，品红框 = 所有设备都能看到的安全区，只用来目检）。
- 配色、字体、图片都取自线上站点（2026-11-10 读的各站 CSS）。字体首次运行时下载到 `fonts/`，站点图片下载到 `.cache/`，这两个目录和 `out/` 都不进 git。
- 网站换了视觉，就改脚本顶部的色值和图片路径，再重跑。

## 三个频道共用的规则

1. **AI 标注**：画面里有逼真的人物或动物，上传时都要勾选 Altered or synthetic content = **Yes**；「不是为儿童制作」；「无付费推广」（自家产品不算付费推广）。
2. **不夸大产品能力**：PawMotif 和 TryOnSwap 卖的都是**静态图**。视频里的动态是我们在 Colab 上另外做的，所以每条视频都要写明哪部分是网站产出（比如 `Portrait: PawMotif · Motion: AI video`），不能让观众以为网站能直接出视频。
3. **人物和宠物素材的来源**：只用 AI 生成的人物、宠物，或者有书面授权的用户投稿。不用网上随手找的真人或别人家宠物的照片。
4. **UTM 统一格式**：`utm_source=youtube&utm_medium={channel|video|shorts|comment}&utm_campaign=<视频 slug>`，在各站 GA4 里按来源 = youtube 看效果。
5. **引流位置**：简介第一行、置顶评论、频道 About 里的链接。Shorts 里不能放可点击的外链，所以「相关视频」挂到对应的长视频上。片尾画面在加入 YPP 之前不能链到外部网站。
6. **身份**：三个频道都建成品牌账号，挂在 `winsonaibuilder@gmail.com` 下，和 MakeItRap、Motion & Mood 同一个 Google 账号。浏览器里登录了多个 Google 账号，进 Studio 前先看清当前身份（坑见 memory `makeitrap-youtube-channel`）。

## 共用的 Colab 出片方式

- **FL2VA 首尾帧**（07 号 `run_runway.py` + `FL2VA_15S_SINGLE_SHOT_SOP.md`）：首帧放「之前」，尾帧放「之后」，15 秒一镜到底。宠物照片 → 画作、穿搭 A → 穿搭 B，都用这个结构。
- **成本口径**沿用 07 号 `run_batch_pipeline.py`：单条 15 秒约占 G4 **10.2 分钟（约 1.7 CCU）**，每次开机冷启动 3.5 分钟（约 0.6 CCU）。**一次开机连出 N 条**，不要一条开一次机。8 秒版本成本减半。
- 竖版原生渲染 768×1344，本地超分到 1080×1920，不从横版裁切（05 号踩过的坑）。
- 首帧、尾帧、提示词、配乐全部在本地准备好再开 GPU（防烧钱硬规则第 6 条）。

## 状态

- [x] 2026-11-10 方案 + 频道素材（头像、横幅）
- [x] 2026-11-10 建频道 + 上传头像和横幅 + 填写简介、链接、关键词（ego-browser）
- [x] 2026-11-11 PawMotif 样片 2 条（Living Portrait · 柯基植物系列，首尾帧都是网站首页现成成品），实耗约 2.4 CCU（G4 14 分 23 秒）
- [x] 2026-11-11 Songifted 2 条（生日反应 + 网站示例歌）+ TryOnSwap 2 条（转身换装），一次开机，G4 22 分 14 秒，按时长折算 3.72 CCU（余额实际减少 3.03）。TryOnSwap 吊带裙那条作废（见下）
- [x] 2026-11-11 三个站的引流版 Shorts 各 1 条（`promo_short.py`，本地合成 0 CCU），见下文「引流版 Shorts」
- [x] 2026-11-11 PawMotif 用站长测试号完整走了一遍产品流程，问题记录在 `pawmotif/产品体验问题.md`
- [x] 2026-11-11 上线：Songifted `W4t3RBjlIA0`、TryOnSwap `cGNfbJA6eFo`（公开，oEmbed 200 核验）
- [x] 2026-11-11 杜宾水彩画像 H3 Living Portrait 1 条（G4 12 分 11 秒，余额实际减少 1.67 CCU），已剪进 PawMotif 引流版（17.2 秒），上线 `eQuDr1kLsHc`（公开，oEmbed 200）
- [ ] 三个站的页脚加上 YouTube 链接（在各站自己的仓库里改，不在本仓库）

## 样片出片（`render_samples.py` + `finish_sample.py`）

```bash
python3 workflows/08_site_channels/render_samples.py --jobs workflows/08_site_channels/samples/pawmotif/jobs.json --dry-run   # 0 CCU 预演
python3 workflows/08_site_channels/render_samples.py --jobs workflows/08_site_channels/samples/pawmotif/jobs.json             # 开 G4（先问）
python3 workflows/08_site_channels/finish_sample.py -i <raw.mp4> -o <final.mp4> --start 5 --end 186 --credit "Portrait: PawMotif · Motion: AI video"
```

- `render_samples.py` 复用 07 号的云端执行器和远程函数，**不改 07 号文件**：用自己派生的 config 覆盖 `--config`，把 07 已有的 preset 名 `fl2v_candid_look_camera` 重定义成本批参数；`--style-mode stylized` 把写实人像和特写 LoRA 归零，画作笔触不会变成照片质感。会话名默认 `sitech-g4`。
- 实测（2026-11-11，192 帧 8 秒，10 步）：首条含 ComfyUI 冷启动 7.4 分钟，热机第二条 3.7 分钟。
- **FL2VA 首尾定格跳帧**：生成结果首尾几帧是原图定格，接到生成内容时相邻帧差约 8（正常运动 1.5 左右）。T1 跳在第 4/187 帧，T2 跳在第 180 帧，位置不固定，所以每条都要按帧差选截取范围，再用 `finish_sample.py` 截。
- **循环**：首尾帧用同一张图不保证能循环。T1 截第 5～186 帧后接缝帧差 2.1（低于片中运动峰值 3.5），可无缝循环；T2 首尾姿势差太多（≥7.5），只能做单次播放版。
- **真人类开写实 LoRA**：Songifted/TryOnSwap 用 `style_mode=photorealistic` + `realism_lora_strength=0.7`，提示词以 `r34l1sm` 开头；特写 LoRA 仍是 0。
- **换装会自己推近**：两条 TryOnSwap 都在转身时把镜头推近来掩盖换装，提示词里写了 static full-body 也没压住。大衣那条推到面料特写再拉回全身，作为电商展示反而好用；吊带裙那条在第 73 帧硬切到胸口以上近景，薄缎面透出胸部轮廓，不符合「商品目录、不走性感路线」，作废。下次换装：提示词明确禁近景，或尾帧改成侧身全身图，并优先选不透的面料做样品。
- 动作幅度大的片子（Songifted、换装）帧差中位数在 3～8，不能用固定阈值找跳帧，要看帧差相对中位数的尖峰并抽帧目检。
- Songifted 配乐：`finish_sample.py --audio samples/songifted/songifted_demo_birthday.mp3 --audio-start 24.70`，即首页示例歌唱到「Happy birthday, Sarah, this song belongs to you / Every single line of it is us saying thank you」那段（24.96～32.04 秒，mlx_whisper small 关掉 condition-on-previous-text 后定位；前 30 秒要单独截出来识别，不然会整段幻听成 ooh）。
- 成片在 `out/samples/<site>/`（不进 git）。
- **colab CLI 有新版本时，升级提示会打到 stdout 第一行**（2026-11-11 发布 0.8.0 当天）。`colab dfs token` 的输出因此不是纯 JSON，`render_samples.py` 当时拉回失败，但渲染本身是成功的，片子还在 Drive 上。现在只截取 `{…}` 部分来解析。其他工作流里凡是解析 colab 输出 JSON 的地方，都可能踩到同一个坑。
- 杜宾画像（seed 2026111131）：头部从侧向转到正面再转回，始终保持水彩质感，首尾没有定格跳帧。帧差每隔 4 帧有一个小鼓包，是 H3 潜空间按 4 帧一组压缩造成的，柯基样片也一样，肉眼看是连续动作。

## 引流版 Shorts（`promo_short.py`）

纯结果的样片只能说明「AI 能把图做动」：观众看不出是什么产品、自己能怎么用、去哪用。所以发出去的每条 Shorts 都按四段来剪：

| 段 | 内容 | 素材来源 |
|---|---|---|
| ① 钩子 + 输入 | 一句大标题 + 用户要给的东西（本人照 / 一句话 / 宠物照） | 网站现成的输入示例或真实照片 |
| ② 产品动作 | 还原站上的操作：上传框、风格选择、歌词确认，按钮文案照抄网站 | 网站素材 + 本地画的界面卡片 |
| ③ 结果 | H3 样片（TryOnSwap、Songifted），或原照 → 画像的划屏（PawMotif，0 CCU） | `out/samples/` 或站上真实生成的结果 |
| ④ 落版 | Logo + 网址 + 免费额度原文 +「Link on our channel page」 | 频道素材 |

```bash
python3 workflows/08_site_channels/promo_short.py {tryonswap|songifted|pawmotif}   # 产出 out/promo/<site>/
```

- **Shorts 的简介和评论里的链接点不开**，所以网址从第 ③ 段起常驻在画面顶部居中（右上角会被 Shorts 的搜索按钮挡住）；能点的入口只有频道主页的链接和关联长视频。
- 安全区：关键文字放在 `STEP_Y=1450` 以上；底部约 20% 会被标题、频道名、音乐条盖住。
- 免费额度的说法照搬网站原文，限定条件也照写（Songifted 的「for eligible first-time creators」）。
- Songifted 的歌从示例歌第 `24.96 - 4.6` 秒开始放，这样第 ③ 段一开始正好唱到带名字的那句，歌词字幕里把 Sarah 高亮。
- PawMotif 的原照是站长自家的杜宾（已去掉 EXIF/GPS）。画像用站长测试号在 pawmotif.com 真实生成并下载（无水印 1664×2512）。H3 输入图在顶部补了纸色留白（`pawmotif_doberman_watercolor_768x1344.png`），给网址腾出位置；划屏的终点画面就是 H3 的第一帧，衔接无缝。配乐用 H3 原生的钢琴音轨，相位对齐到画面开始动的那一刻（`PM_MOTION_T`）。`promo_short.py pawmotif-static` 是不用 H3 的 0 CCU 版本。

