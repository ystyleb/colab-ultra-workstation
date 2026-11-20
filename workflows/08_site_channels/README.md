# 08 · 三个工具站的 YouTube 频道（Songifted / PawMotif / TryOnSwap）

> 定位（2026-11-10 定）：**一站一个独立频道，以给网站引流为主**。和 MakeItRap（先做内容 IP，网站顺带）的做法相反：每条视频本身就是产品演示，观众看完的下一步是去网站试。
> 视频来源（2026-11-10 定）：**上 Colab 做 AI 动态视频**，主要用 H3 FL2VA 首尾帧，沿用 07 号流水线的出片方式。

| 站点 | 卖什么 | 频道名 / Handle / 频道 ID | 方案 |
|---|---|---|---|
| songifted.com | 写进对方名字的定制礼物歌，$49 起，首次可免费试听 45 秒 | **Songifted** · `@songifted` · `UCzeTUCqNXgBSFFpE_iOsZjQ` | `site-social-ops/brands/songifted/频道方案-youtube.md` |
| pawmotif.com | 用宠物照片画肖像，6 种画风，$29 | **PawMotif** · `@pawmotif` · `UC8M9W5_TlNenrilxQBTkBJw` | `site-social-ops/brands/pawmotif/频道方案-youtube.md` |
| tryonswap.com | AI 虚拟试衣（衣服穿到模特身上），按张计费 | **TryOnSwap** · `@tryonswap` · `UCxXCgsXBIbSJ3_naKqeQNvw` | `site-social-ops/brands/tryonswap/频道方案-youtube.md` |

三个频道都在 2026-11-10 建好，都是挂在 `winsonaibuilder@gmail.com` 下的品牌账号。头像、横幅、简介、2 个 UTM 链接、8 个关键词都已发布，并从公开页核验过（TryOnSwap 的关键词在 Studio 里已保存，公开页同步比较慢）。还没有上传视频；所在国家/地区、联系邮箱、视频水印都没设置。

## 发布与运营已迁到 site-social-ops（2026-11-12）

本目录只管**制作**：频道美术、H3 样片、引流版 Shorts 合成。**发布、跨平台分发（YouTube / Pinterest / Instagram / Facebook）、社区运营、产品体验问题记录**都在 `/Volumes/WorkData/Workspace/projects/site-social-ops`：

- 频道方案、产品体验问题、YouTube Studio 上传流程：`brands/<site>/`、`docs/platforms/youtube.md`
- 交接方式：本目录合成母版（`out/promo/<site>/*.mp4`），在 site-social-ops 的 `releases/<id>/release.json` 里写 `source.master` 指向它，再用 `python3 -m ops import` 拷过去

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
- [x] 2026-11-11 PawMotif 用站长测试号完整走了一遍产品流程，问题记录在 `site-social-ops/brands/pawmotif/产品体验问题.md`
- [x] 2026-11-11 上线：Songifted `W4t3RBjlIA0`、TryOnSwap `cGNfbJA6eFo`（公开，oEmbed 200 核验）
- [x] 2026-11-11 杜宾水彩画像 H3 Living Portrait 1 条（G4 12 分 11 秒，余额实际减少 1.67 CCU），已剪进 PawMotif 引流版（17.2 秒），上线 `eQuDr1kLsHc`（公开，oEmbed 200）
- [x] 2026-11-12 第二批引流 Shorts 各 1 条（全部站上真实产出，0 CCU），公开上线并用 oEmbed 核验：
  - PawMotif `l5EfuX47GDM`「One Pet, 6 Styles」：测试号用杜宾全身照生成全部 6 种画风（`promo_short.py pawmotif-styles`）
  - Songifted `0S8IrjXonjs`「Happy Birthday Mom」：站上 /birthday-song-for-mom 的现成示例歌 + /create 真实手机截图（`songifted-mom`）
  - TryOnSwap `ZDOXYAwCRT4`「One sweater, six photoshoots」：站长账号 6 个 Scene 预设各 1 张 2K 9:16，扣 60 credits（`tryonswap-campaign`）
  - 三个站的产品问题分别记在 `site-social-ops/brands/<site>/产品体验问题.md`
- [x] 2026-11-13 第三批：三个站各 1 条 H3 引流 Shorts（一次开机 6 条每站挑 1 条，G4 33 分钟，实耗 5.03 CCU），同日公开上线并用 oEmbed 核验：PawMotif `dk-3tSHBxxw`、TryOnSwap `RyqvI_cORPQ`、Songifted `NIp1Ct3OeXs`：
  - PawMotif「照片 → 画像」（`pawmotif-photo2art`）：首帧杜宾头部原照（按画像里的五官位置对齐裁剪），尾帧是测试号用**同一张照片**在 `/portraits/golden` 新生成的 Botanical（job `8ec5dc7c`）。H3 放完后交叉淡化到站上真实下载的画像，观众最后看到的是产品真实输出
  - TryOnSwap 转身换装 v2（`tryonswap-knit`）：model-a → 第二批 Studio 毛衣图。T1 作废（提示词禁了近景，仍硬切到脸部和臀部特写）；T2 在背身转侧面的那一帧瞬间换装，全程不切镜
  - Songifted 反应片（`songifted-wife`）：站首页 `/videos/reaction-quiet.jpg` 竖裁 + `/demos/for-wife.mp3`（虚构的 Nora），副歌「Nora」在成片 4.56 s，③ 段 4.58 s 开始
- [x] 2026-11-15 第四批：用户要求「跳出四段式，用小故事」。三条多镜头故事片做到母版 + 发布包（`site-social-ops/releases/2026-11-15_*`，YouTube 已于当天公开上线：PawMotif `QiMxArC_kyE`、TryOnSwap `MGFoyYX02Ss`、Songifted `rf6Rh9x9qL8`，oEmbed 200；Pinterest/IG/FB 仍为 draft）。Codex 关键帧 0 CCU，H3 一次开机 28 条（每镜 2 seed）挑 14 条，G4 101 分钟，实耗 16.62 CCU；Kie Suno 纯音乐 2 次共 24 积分：
  - PawMotif《Into the Frame》（`story_short.py pawmotif-intoframe`，23.6 s）：杜宾盯着墙上自己的画像 → 一跃钻进画框溶成水彩 → 画里的它转头冲你笑 → 空客厅推镜，画里的狗看向镜头。画框里贴的是测试号用全身照真实生成的 Watercolor（红项圈和真狗一致）
  - TryOnSwap《The Photoshoot That Never Happened》（`tryonswap-photoshoot`，25.1 s）：深夜卖家看到 $2,400 拍摄报价（本地画的示意报价单，标 Example quote）→ 揉掉 → 手机拍平铺图 → 第二批 6 个 Scene 真实上身图弹出 → 街拍 → 举杯。鼓点（Suno 源 19.0 s）卡在揉纸那一刻
  - Songifted《It Was Not Nothing》（`songifted-danny`，28.6 s）：用户指定「女生给男生送歌」，用 `/demos/for-husband.mp3`（虚构 Danny）。镜头切点卡歌词换句：打字 → 「Danny, don't make a joke yet」→ 雪夜铲雪闪回 → 递钥匙 → 他流泪 →（接尾声）「Go on, make the joke now」拥抱。歌里两句之间 1.4 s 停顿用拥抱镜头的 H3 笑声补上
- [x] 2026-11-16 第五批（节日季小故事）。用户看片后要求去掉画面里的 AI 胶囊，当天 YouTube 公开上线（oEmbed 200 核验）：PawMotif `fBPSLU5ZHg8`、TryOnSwap `-SnKUYoPxWQ`、Songifted `vebsJuhKz58`；发布包 `site-social-ops/releases/2026-11-16_*`，Pinterest/IG/FB 仍为 draft。站上真实产出：PawMotif 测试号用 AI 金毛照生成 Old World 油画（job `1867f515`）；TryOnSwap 站长账号用 AI 圣诞毛衣平铺图生成 3 张上身图（Custom 雪夜街景、Custom 圣诞客厅、Street style，扣 30 credits）。H3 一次开机 26 条挑 13 条，G4 94 分 47 秒，本会话按时长折算 15.88 CCU（同时段 09 号另开实例出片，账户余额共减少 31.03）；Kie 纯音乐 2 次共 24 积分：
  - PawMotif《Under the Tree》（`story_short.py pawmotif-tree`，23.8 s）：圣诞早晨她递给他扁礼盒 → 拆开是他家金毛的油画 → 金毛跑来趴在画前摆出同样姿势 → 晚上画挂到壁炉上，画里的狗转头冲你笑
  - TryOnSwap《Model Cancelled》（`tryonswap-cancelled`，23.3 s）：黑五上新前一晚模特发消息取消 → 手机拍平铺图 → 3 张上身图卡在配乐 drop（10.0 s）弹出 → 零点上线、订单通知（示意）
  - Songifted《Porch Light》（`songifted-porch`，37.0 s）：用 `/demos/for-dad.mp3`（虚构的 Daniel），镜头切点卡在逐词时间戳上：门廊灯 → 门口拥抱 → 故事卡 →「Happy birthday, Dad!」捂嘴笑出眼泪 → 全家举咖啡杯
  - 关键帧 `gen_keyframes.py` 只排两轮依赖：`edit_of` 套 `edit_of`（pt_d → pt_c → pt_a）的帧要第二次单独 `--only` 补跑
  - 贴画改用 `paste_into_canvas`（floodfill 求画布，前景遮挡物如狗头自动保留）；PIL `thresh` 是三通道差之和，阴影画布约 105、金毛毛色约 175、金框约 285，取 120
- [x] 2026-11-17/18 第六批（三条多镜头故事片），母版已经用户审定，`ops import` 和 `ops validate` 都通过（发布包 `site-social-ops/releases/2026-11-17_*`），**还没有发布**。H3 首批 30 条，G4 113 分 55 秒，按时长算 19.08 CCU；《Mia》返工又开了 3 次机，补渲 12 条，按时长共约 9.3 CCU：
  - PawMotif《Back in His Spot》（`story_short.py pawmotif-biscuit`，24.8 s）：第一人称怀念老牧羊犬，站上真实生成的 Watercolor（job `943726cc`）
  - TryOnSwap《One Dress, Every Party》（`tryonswap-party`，20.2 s）：一条祖母绿丝绒裙，3 张上身图（办公室、跨年夜、家宴）在配乐 drop 7.20 s 弹出；封面取 13.6 s 跨年夜举杯
  - Songifted《Mia》（`songifted-mia`，38.1 s）：`/demos/for-daughter.mp3`，感恩节当天过 23 岁生日。用户审片后返工 3 镜：过马路（Cross T3）、宿舍（方案一 S1_T2：侧面道别 → 转身走开 → 回头挥手）、吹蜡烛（Pie T3：蜡烛不再复燃，吹灭时间对准「Mia」）。经验见上文「有走位、有转身的镜头怎么做」
- [ ] 三个站的页脚加上 YouTube 链接（在各站自己的仓库里改，不在本仓库）
- [x] 2026-11-19 第六批三条已按时公开（oEmbed 200 核验）；site-social-ops 里的 release.json 还是 `scheduled`，要改成 `published`
- [x] 2026-11-19 Songifted 横屏长视频「How it works」母版（`songifted_longform.py`，87.8 s，1920x1080，**0 CCU**），**等用户审片**，还没做发布包、没上传。素材全部来自网站本身：/create 桌面版逐状态截图（`capture_songifted_create.mjs`）、首页 4 条 AI 反应视频 `/videos/reaction-*.mp4`、场合配图、`/demos/*.mp3`。用户定的：只用现成示例歌（不真实提交，不占用免费试听资格），不要旁白
- [x] 2026-11-20 Songifted 横屏故事片《Nora》成片（`nora_film.py`，196 s，1920x1080，整首 `/demos/for-wife.mp3`，产品只出现在片尾卡），**等用户在审核页审片**，还没做发布包、没上传。关键帧经过两轮页面评审（第二轮重做公寓环境图：床的长宽画反了）。H3 27 个镜头三次开机共渲 63 条，56.5 CCU（开机前估 26～28，第一轮约一半不能用）。经验见下文「横屏故事片《Nora》」和 H3 SOP 铁律 I
- [ ] 长视频上线后（简介里放可点的 UTM 链接）：每条 Songifted Shorts 的「相关视频」都挂到它上面，走 Shorts → 长视频 → 网站。原因：Shorts 简介和评论里的网址不能点（2023-08 起）。效果好再推广到 PawMotif / TryOnSwap

## 小故事 Shorts（`story_short.py` + `gen_keyframes.py` + `kie_bgm.py`，第四批起）

```bash
python3 workflows/08_site_channels/gen_keyframes.py samples/<dir> -j 4          # Codex 生关键帧，0 CCU；有 edit_of 的帧以基础帧为参考只改动作
python3 workflows/08_site_channels/story_short.py prep-pawmotif                  # 把站上真实画像贴进关键帧的画框
python3 workflows/08_site_channels/kie_bgm.py --title ... --style ... --out out/bgm/<site>   # Suno 纯音乐，一次 2 条，约 12 积分
python3 workflows/08_site_channels/story_short.py <pawmotif-intoframe|tryonswap-photoshoot|songifted-danny> [--preview]
```

- **人物/场景一致性**：先生成 1 张基础帧，其余帧都用 `edit_of` 把它当参考图，提示词只写「改什么」。同一对夫妻跨 8 个镜头（沙发、厨房、雪夜、玄关）脸都对得上；新镜头要在提示词里写清「忽略参考图的场景，只保留人物」
- **产品真实性**：故事画面全是 AI，但画框里的画、商品页里的上身图、歌都必须是站上真实产出。第四批片中常驻 AI 标注胶囊；**第五批起画面里不放**（2026-11-16 用户定），AI 声明靠 YouTube 上传勾 Altered or synthetic content = Yes + 各平台文案里原样写 `disclosure.credit_line`
- **H3 选片规律**（本批 14 镜 × 2 seed）：首帧 = 尾帧的「微动」镜头，H3 很爱自己推成特写再拉回（TryOnSwap 平铺 T2、举杯 T2、打字 T2、街拍 T1 都这样），选镜头稳的那条；动作镜头（揉纸、扑画框、拥抱）两条都能成，挑动作看得清的。跳画框 192 帧最后 38 帧是定格，只用前 6 s
- 原声：大多 -13～-30 LUFS 不等，狗叫可能冲到 -5 dB。故事片以配乐/歌为主，原声按镜头给增益（0～0.6），最后整体 loudnorm 到 -14
- **拉回失败 ≠ 渲染失败**：本地经代理拉 Drive 偶发 `SSL: UNEXPECTED_EOF`，云端片子其实已在 Drive。`pull_from_drive` 已加指数退避重试；漏拉的用 `render_samples.py --jobs ... --only <id> --pull-only` 补拉（0 CCU）
- **冷启动第一条可能超时**：ComfyUI 报就绪后第一次 `/object_info` 可能超时，第一条 job 直接失败，第四、五、六批都遇到过（11-18 宿舍 S1_T1 也是）。2026-11-18 已在 07 号 `run_runway.py` 里改成 timeout=90，并最多重试 4 次（**还没有上云验证**，下次开机时看日志里有没有 `/object_info 第 N 次失败` 并且最后成功了）

### 有走位、有转身的镜头怎么做（2026-11-18，《Mia》宿舍镜头返工 4 轮）

返工经过：母版审片时用户发现过马路那镜「爸爸不动、女儿原地走」，宿舍那镜「走出去又倒着走回来」。之后每一轮都靠用户指出问题：
1. 首尾帧是同一张图，人物没法产生位移。
2. 尾帧里的人只扭头不转身，而且从远离爸爸的那一侧回头，转身角度超过 180°。
3. 首帧和尾帧各自 `edit_of` 生成，两张图里草坪上的路不一样。
4. 人物参考图里带了动作（扭头）。
5. 首帧其实是这场戏的中间状态，缺了侧面相对道别那一拍。

**关键帧设计规则**

| 规则 | 做法 | 反例（本次踩过的） |
|---|---|---|
| 首尾同图只用于原地动作 | 拥抱、吹蜡烛、表情反应可以首尾同图；走路、离开、靠近**必须用不同的尾帧** | 过马路、宿舍用了 `first == last`：H3 只能原地踏步，或者走出去再倒回来（两个 seed 都这样） |
| 不可逆的状态变化也要给不同的尾帧 | 吹灭蜡烛、打碎、倒满、拆开礼物：尾帧要画成变化**之后**的样子，同时写明哪些东西不变（比如「其他蜡烛照样亮着」）。人不走动的镜头直接 `edit_of` 首帧即可 | 吹蜡烛用了 `first == last`：蜡烛吹灭后又自己复燃（用户审片发现） |
| 位移按步速算 | 正常步速约 1.4 m/s。按「片长 × 步速」估算距离，再换算成人物在画面里缩小的比例 | 尾帧把人放到宿舍台阶下，要走 20 多米，H3 只能小跑或者瞬移 |
| 首尾之间只变一件事 | 一段只做一个动作：只走开，或只回头 | 首帧在回头、尾帧也在回头，H3 只能补成「回头 → 甩头转回去 → 走 → 再回头」 |
| 转身要整个人转，从近侧转 | 回头看人时脚、髋、肩、脸一起转，从离对方近的那一侧转（人能转约 135°） | 身体背对、只扭脖子，挥手的手和抱箱子的手挤在同一侧，像猫头鹰 |
| 方向用画面坐标写 | 写 "toward the LOWER-LEFT of the frame, toward the SUV"、"the arm on the LEFT side of the frame"，渲染提示词再写明 "turns to her RIGHT / LEFT" | 只写 "toward her dad"，模型选了画面右侧 |
| 视线单独写 | "looks directly into her eyes, nose pointing at her face; NOT at the camera" | 要求爸爸「和后一帧姿势完全一样」，他就照搬了目送远处的方向，没看女儿 |
| 先想清楚整场戏的拍子 | 先列出这场戏有哪几拍（道别 → 转身走 → 回头挥手），首帧应该是第一拍，不是中间状态 | 首帧选了「已经背对着走」，缺了道别那一拍 |

**参考图流程**（用户定的做法）
1. **人物三视图**：正面、90° 侧面、背面，中性站姿，双手空着自然下垂，头和身体始终同向。**不带动作，也不拿道具**；箱子、台灯这些道具写在首尾帧的提示词里。带了扭头动作的三视图会被模型当成人物特征，复制到后面的帧里。
2. **空环境图**：没有人，把路线（这次是那条水泥路）定下来，人物站位要留出空间。不要用 `edit_of` 从带人的帧去删人：这样做机位会被推近，路也会被挤到画面边上。应该拿原帧当参考图，把构图逐项写清楚。
3. **首尾帧都用 `edit_of` 环境图生成**，加上三视图作为参考图。两帧共用同一张底，路和草坪就不会变。
4. 不动的人物（爸爸）在每一帧里位置、大小都要一样，可以把另一帧也放进参考图，并写明 "stand in EXACTLY the same spot"。这样画面里只有一个人在动，H3 补得最顺。

**首尾同图的镜头只截前半段**：做个动作再回原位的镜头（转身转回、举杯），前半段是动作，后半段是复原，H3 还常在后半段推近再拉回。TryOnSwap 第六批每段只截 2.5 s，就没有出现复原感（11-18 复查 PawMotif 和 TryOnSwap 两条，均无问题；NYE 一镜自己推到了半身，用户同意保留）。

**动作卡歌词**：先用 whisper 加 `--word-timestamps True` 拿到关键词的时间，比如「Mia」在 54.14 s，换算到素材里的秒数后写进提示词（"about three seconds in, blows the candle out"）。出片后量实际时间，再在 `t0` 的余量里微调。

**选条要多查一项：走位方向**
- 帧差和接触印样查不出「倒着走」：倒着走和正着走在像素上同样平滑。每条按 0%～100% 抽 8 帧，看人物大小和位置是否**单调变化**，只缩小或只放大，不能先缩后放。
- 转身段落要放大裁切看头部：头有没有来回甩，正面和背面有没有闪，有没有凭空冒出配饰（这次有一条凭空出现了眼镜）。

**一场戏多拍：一次生成还是两段接力**（`render_samples.py` 的 job 支持单独设置 `"length"`）
- 方案一：首帧（道别）→ 尾帧（回头挥手），141 帧一次生成。
- 方案二：A 段 首帧 → 中间帧（背对着走），73 帧；B 段 中间帧 → 尾帧，90 帧。两段共用中间帧，拼起来是一个连续长镜头。
- 对比结果（2026-11-18，G4 一次开机 6 条，S1_T1 因冷启动超时没出片）：
  - 方案一 S1_T2：道别、走开、回头三拍都有，方向也对。但回头挤在最后约 0.5 s 里完成，挥手只停留了不到 1 s。H3 会自己分配每一拍的时间，最后一拍往往被压缩。
  - 方案二：A 两条都自然；B_T1 的转身用了约 0.9 s，最从容，B_T2 有一次甩头。A 末帧接 B 首帧，帧差 1.72～2.01（片内正常运动约 1～1.7，不相关镜头约 64），**直接硬接就是无缝的**，两头也没有定格帧。代价是拼起来约 6.8 s，宿舍这一镜要 6.2 s，得从前一镜借 0.6 s；而且只能剪 A 的头和 B 的尾，剪中间就会跳。
  - 成片：`out/promo/songifted/Songifted_Story_Mia_DormS1_1080x1920.mp4` 和 `…_DormS2_…`（`story_short.py songifted-mia-s1|s2`）。用户选择**方案一**（`songifted_mia()` 默认 `dorm="s1"`），认为首尾帧一次生成的效果已经够用

## 横屏长视频（`songifted_longform.py` + `capture_songifted_create.mjs`，2026-11-19 起）

```bash
ego-browser nodejs < workflows/08_site_channels/capture_songifted_create.mjs   # 采集 /create 每一步的状态截图（约 100 张 2560x1440）+ manifest.json
python3 workflows/08_site_channels/songifted_longform.py --still 14 41          # 导出单帧看版式
python3 workflows/08_site_channels/songifted_longform.py --preview              # 960x540 预览（约 50 s）
python3 workflows/08_site_channels/songifted_longform.py                        # 成片 out/promo/songifted/Songifted_HowItWorks_1920x1080.mp4
```

- 结构跟着首页「How it works」三步走：派对钩子 → 标题 → ① 录屏 → ② 歌词 → ③ 反应镜头 → 场合串烧 → 片尾。配乐只用 Sarah 示例歌，基本按原顺序播放：从标题那一刻起从 0 秒开始放，第一段副歌（歌内 24.72 s）落在 ② 开头。录屏段的节奏由 `shot_duration()` 决定，最后会整体缩放，保证总长等于 `T_STEP2 - T_WALK`。
- **录屏不用 screencast**：CDP screencast 每帧都要 ack，而且只在画面变化时出帧，帧率不稳。改成每做一步操作截一张 2x 视口图，同时记下元素坐标，合成时用指数平滑做镜头跟随，再叠光标和点击涟漪。
- **视口覆盖要在 goto/reload 之后设**（`Emulation.setDeviceMetricsOverride`），在那之前设会被重置。
- **账号邮箱打码**：第 5 步页面上有登录邮箱（在 `<strong>` 里）。采集时每一帧都按 "@" 查邮箱坐标；合成脚本从 `s4_next` 起，任何一帧缺邮箱坐标都直接报错，不出片。第一版选错了元素（副标题 "We'll email you…"），邮箱明文漏进了预览，这道闸就是为此加的。
- 清空站点存储会重新弹出隐私同意弹窗：采集脚本会点 Reject all。Turnstile 在自动化浏览器里一直停在 Verifying，镜头不对准它，也不点它。

## 样片出片（`render_samples.py` + `finish_sample.py`）

```bash
python3 workflows/08_site_channels/render_samples.py --jobs workflows/08_site_channels/samples/pawmotif/jobs.json --dry-run   # 0 CCU 预演
python3 workflows/08_site_channels/render_samples.py --jobs workflows/08_site_channels/samples/pawmotif/jobs.json             # 开 G4（先问）
python3 workflows/08_site_channels/finish_sample.py -i <raw.mp4> -o <final.mp4> --start 5 --end 186 --credit "Portrait: PawMotif · Motion: AI video"
```

- `render_samples.py` 复用 07 号的云端执行器和远程函数，**原则上不改 07 号文件**（唯一例外：2026-11-20 给 `run_runway.py` 加了「只锁首帧」开关，`last_frame="__NONE__"` 时走 I2V，不传就和原来一样；注意 07 号整个目录目前不在 git 里）：用自己派生的 config 覆盖 `--config`，把 07 已有的 preset 名 `fl2v_candid_look_camera` 重定义成本批参数；`--style-mode stylized` 把写实人像和特写 LoRA 归零，画作笔触不会变成照片质感。会话名默认 `sitech-g4`。
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
python3 workflows/08_site_channels/promo_short.py {tryonswap|songifted|pawmotif}                        # 第一批
python3 workflows/08_site_channels/promo_short.py {pawmotif-styles|songifted-mom|tryonswap-campaign}   # 第二批，产出 out/promo/<site>/
```

- **合成前先测响度**（`ebur128` + `silencedetect`）：H3 原生音轨不稳定，可能只有底噪（TryOnSwap 换装 T2 只有 -30.7 LUFS），也可能开头有静音。按「H3 出现的时刻」对齐循环相位时，开头的静音会正好落在画面变化的那一刻。这时用 `audio_loop` 借别的样片的音轨，或者先做无缝音床再当 `audio` 用（见 `tryonswap-knit` 的注释）。
- **Shorts 的简介和评论里的链接点不开**，所以网址从第 ③ 段起常驻在画面顶部居中（右上角会被 Shorts 的搜索按钮挡住）；能点的入口只有频道主页的链接和关联长视频。
- 安全区：关键文字放在 `STEP_Y=1450` 以上；底部约 20% 会被标题、频道名、音乐条盖住。
- 免费额度的说法照搬网站原文，限定条件也照写（Songifted 的「for eligible first-time creators」）。
- Songifted 的歌从示例歌第 `24.96 - 4.6` 秒开始放，这样第 ③ 段一开始正好唱到带名字的那句，歌词字幕里把 Sarah 高亮。
- **Songifted 不另外生成歌**：站上每个场合页都有现成示例歌（`/demos/<occasion>.mp3`，11 首英文，已下载到 `samples/songifted/demos/`），直接用。`/create` 最后一步有 Cloudflare 人机验证，自动化不要碰。
- **PawMotif 原照要和画风构图匹配**：头部特写配全身构图的画风（油画趴卧、水粉坐椅、彩铅蜷睡、水彩坐姿）会画成大头小身子。「6 种画风」用全身照（`pawmotif_doberman_fullbody_src.jpg`，车牌已打码、EXIF 已去）。用之前先看头身比。
- **TryOnSwap 场景合集**：Scene try-on 可以连续提交排队，2K 一张约 25 秒，结果原图就是缩略图背后的 `/api/tryon/asset/<id>`。偶发失败（Needs attention）会自动退款，重试一次即可。
- PawMotif 的原照是站长自家的杜宾（已去掉 EXIF/GPS）。画像用站长测试号在 pawmotif.com 真实生成并下载（无水印 1664×2512）。H3 输入图在顶部补了纸色留白（`pawmotif_doberman_watercolor_768x1344.png`），给网址腾出位置；划屏的终点画面就是 H3 的第一帧，衔接无缝。配乐用 H3 原生的钢琴音轨，相位对齐到画面开始动的那一刻（`PM_MOTION_T`）。`promo_short.py pawmotif-static` 是不用 H3 的 0 CCU 版本。



## 横屏故事片《Nora》（`nora_film.py` + `screen_takes.py`，2026-11-20）

```bash
python3 workflows/08_site_channels/gen_keyframes.py samples/songifted_nora -j 4                      # 三视图 → 空环境图 → 首尾帧（0 CCU）
python3 workflows/08_site_channels/nora_film.py --animatic                                         # 全关键帧样片，开机前审节奏
python3 workflows/08_site_channels/render_samples.py --jobs workflows/08_site_channels/samples/songifted_nora/jobs.json --only N01_Counter_T3,... --keep-alive -s sitech-g4   # 开 G4（先问）
python3 workflows/08_site_channels/screen_takes.py out/samples/songifted_nora [N01 N02 ...]       # 硬切/运镜筛片 + 联系表 sheets/<id>.jpg（0 CCU）
python3 workflows/08_site_channels/nora_film.py [--preview] [--take N18_Walk=2]                   # 成片 out/promo/songifted/Songifted_Story_Nora_1920x1080.mp4
```

**流程**：先出人物三视图，再出空环境图（每个新机位各一张，不从广角图上 `edit_of` 改机位），每个首尾帧都 `edit_of` 环境图并带三视图作参考。然后在审核页（见下节）评审两轮，过审后才开机。第二轮用户发现公寓那张床长宽画反了：先出两张候选环境图（`env_apt_cand_a/b`）让用户选 A，再重做依赖它的分镜，旧图备份到 `kf_vN/`，页面上能看「上一版」。

**第一轮 H3 约一半不能用，原因和改法**（通用规则已写进 `references/minimax_h3_zero_waste_sop.md` 铁律 I）：

| 现象 | 镜头 | 改法 |
|---|---|---|
| 首尾同图的近静止全景/中景，H3 推成特写再拉回或硬切回来；换提示词、同 seed 结果几乎一样 | N01 N02 N06 N14 N16 N19 N21 N23 N28 | job 加 `"first_only": true`，只锁首帧（I2V） |
| 提示词写了画外的人，被 H3 编出来 | N10（他的特写冒出陌生女人）、N28（屋外夜景切进屋内） | 只写画面里有的东西 |
| 否定写法反着来 | N17「unable to speak」→ 张嘴说话 | 正向写：「lips pressed tightly together」 |
| 动作控制太细出伪影 | N09 拨头发 → 手里冒棍子；换 seed 冒出镜子 | 删掉动作，只写「watches her sleep and smiles quietly」 |
| 362 帧自己剪成多镜头蒙太奇 | N28 片尾 20 s 空镜 | 渲 192 帧，合成时 `loop=1.0` 交叉溶解循环 |

所有提示词统一成 `r34l1sm, {动作} The camera holds a static shot, keeping the framing of the first frame for the whole clip.`（特写用 static close-up；车内用 hood-mounted camera）。

**选片**：`screen_takes.py` 的判据：逐帧灰度差大于 95 分位 × 4 且大于 12 记为硬切（首尾各 6 帧是定格段跳入跳出，单独标出，不计入）；中位帧差大于 1.8 记为运镜大。阈值用已知好片和坏片对过：N01 的硬切帧差 32.8，中位 4.4，所以不能和中位数比。**脚本报 ✅ 也要看联系表**：N15 雨刮器的周期运动把一次硬切藏住了。选中的 take 写在 `nora_film.py` 的 `TAKES`，审核页每个分镜显示「H3 选用 Tx」和联系表。

**合成器**（`nora_film.py`）：
- `Shot.speed`：硬切离片尾不远的 take（N12 0.94、N15 0.95、N16 0.86、N23 0.96、N25 0.97），用 `setpts` + `framerate` 帧混合放慢，在读到硬切之前就结束。
- `Shot.loop`：短片段掐掉尾部 `LOOP_TRIM=8` 帧，循环时用 1 s 交叉溶解。N28 接缝帧差最大 0.53，片内中位 0.29，看不出接缝。
- 每个镜头读帧要读到它自己的转场尾巴：0.6 s 长溶解的镜头要多读 0.6 s，而不是固定多读 0.25 s，否则溶解段会定格。
- `TAKES` 写 0 表示这个镜头不用 H3，直接用关键帧。
- 之前只渲过关键帧样片，ffmpeg 滤镜里 `crop=…:flags=lanczos` 写错了却一直没暴露（`flags` 是 `scale` 的参数），第一次读 H3 片段时才报错。新合成器至少要用一条真实片段跑通一次。

**`render_samples.py` 新增的防护**：
- `launch_with_retry`：启动指令的回执丢失（"Connection was lost"）时，先查远端：`active_token` 不是本次的、没有任务在跑、ComfyUI 空闲，三条都满足才重发。这次补回 2 条。
- `pull_from_drive(..., since=)`：同名 job 重渲时，只认启动前 60 s 之后修改过的文件。之前 N01 重渲拉回的是旧文件，字节数完全一样。
- 配置文件名带长度和 `_fo`（只锁首帧），同一个 job 换长度或换模式不会互相覆盖。

**耗时**：H3 175 帧每步约 17 s，362 帧约 59 s（一条约 10 分钟）。需要长空镜时，渲短片再循环更省也更稳。

## 审核页（开机前给用户审，可在页面上直接评论）

```bash
python3 workflows/08_site_channels/review_nora.py                  # 生成 out/review/songifted_nora/index.html（数据读 keyframes/jobs/nora_film）
python3 workflows/08_site_channels/review_kit/server.py             # http://127.0.0.1:8765/ （只监听本机）
python3 workflows/08_site_channels/review_kit/server.py --dump songifted_nora [--open-only] [--render]   # Agent 读评论；--render 把圈/点画到原图导出 out/review/<p>/annot/<id>.jpg
```

- 评论写一条存一条，存到 `samples/<project>/review_comments.json`：`target`（`kf:<帧名>` / `shot:NN` / `lyric:NN` / `todo:N` / `video:animatic` / `general`），`box` 是图上画的圈（椭圆外接框 [x0, y0, x1, y1]，0–1 相对坐标），`pin` 是单击标的点 [x, y]（有圈时为圈心），`t` 是样片时间点（秒），`img_ver` 是评论时那张原图的 mtime。
- 用户点「完成本轮评审」后，`rounds[-1].closed` 会写上时间。Agent 处理完一条，就在 JSON 里把它的 `status` 改成 `done`/`wontfix`/`question`，并把说明写进 `reply`，然后重跑 `review_nora.py`。图重做过以后，页面上的旧评论会显示「图已更新」。
- 页面只按条增改评论，不整份覆盖文件，所以 Agent 改 JSON 时页面开着也没关系（页面每 15 秒或窗口重新获得焦点时会刷新）。
- `file://` 直接打开也能看，但评论存不了，页面会给出提示。视频拖进度条需要 206 Range 响应，这个服务已经支持。
