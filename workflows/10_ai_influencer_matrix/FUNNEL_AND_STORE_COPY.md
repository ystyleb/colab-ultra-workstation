# 矩阵漏斗、Gumroad 店铺与 ManyChat 自动私信配置手册（V3.1 · Vivian / June / Wen）

> **核心原则**：三个账号必须在**发布第 1 条短视频前**完成「免费诱饵 + 付费主品 + ManyChat 关键词私信 + 危机固定回复」上线，不先赛马后建店。
> **人设与写作约束**以 `PERSONA_BIBLE_V3.md` 为准；V2（Elias / Sienna / 旧 Vivian）版本见 `work/archive/FUNNEL_AND_STORE_COPY_v2_elias_sienna_vivian.md`。
> **所有店铺文案只描述「产品里有什么」，不承诺效果，不写读者反馈**（风控线第 3 条）。

---

## 一、 账号设置（IG Reels / TikTok / YT Shorts）

| 账号 | 定位 | Handle（⚠️ 均为占位，尚未注册） | AI 透明化 | 主页 Bio（直接复制） |
| :--- | :--- | :--- | :--- | :--- |
| **Vivian Sterling** | Money, Spending & Boundaries | `@vivian.oldmoney` | IG 勾选 `AI info`；TikTok 打开 AI-generated 标签；YT 勾选 `Altered or synthetic content = Yes`；每条 caption 末尾写 `AI-generated character` | `78yo AI grandmother 💐 Money, manners & saying no`<br>`Gentle with people, sharp with the rules`<br>`Comment RULES or tap below for the Free Approval Tax Audit 👇` |
| **June Whitaker** | Relationships & Small Gestures | `@june.noticing` | 同上 | `61yo AI wedding photographer 📷 Small moments, honest notes`<br>`Watch what happens when no one's posing`<br>`Comment NOTICE or tap below for the Free 3-Day Notice Journal 👇` |
| **Henry Wen** | Rest & Measure for Busy Lives | `@wen.teashop` | 同上 | `71yo AI tea shop owner 🍵 Zhuangzi & doing a little less`<br>`Rest and measure for busy lives · not therapy`<br>`Comment TEA or tap below for The Tea Drawer 👇` |

**跨平台分发**：`subtitle_and_finalize.py` 输出的 `1080×1920` MP4 无平台水印，同一母版分发到：
- **Instagram Reels（主成交）**：ManyChat 评论关键词私信 + Bio 里的 Gumroad 链接。
- **TikTok**：置顶评论写关键词，引导到 Bio 链接。
- **YouTube Shorts**：用 `scripts_30_manifest.json` 的 `yt_shorts_title`，置顶评论放 Gumroad 免费品链接。

---

## 二、 Gumroad / Lemon Squeezy 上架清单（6 个 PDF）

> PDF 在 `products/`（`python3 build_digital_products.py` 生成），封面在 `out/<persona>/gumroad_*_cover_1280x720.png`（`python3 make_store_and_profile_assets.py` 生成）。
> **定价只写真实售价**：`influencer_config.json` 里的 `anchor_price_usd` 是从未实际售出过的价格，**不要在店铺页写「原价 \$24，现价 \$15」**，否则属于虚构原价（FTC 16 CFR 233）。确实以原价卖过一段时间之后，才可以展示折扣。

### 1. Vivian Sterling

**免费诱饵** · `products/vivian_free_approval_tax_audit.pdf` · `$0+` · 按钮 `Get the Free Approval Tax Audit`
```text
The Approval Tax Audit — 72 Hours of Noticing What You Spend to Be Seen

A free 4-page printable from Vivian. Not a budget. One question about each purchase: who was it for?
• Collect: a one-page sheet for your recent purchases
• Sort: the five approval taxes, from the Keeping-Up Tax to the Proof Tax
• Decide: keep it, trim it, or say one sentence out loud (sentences included)

Vivian Sterling is an AI-generated character with a fictional background. General education about spending habits, not financial advice.
```

**付费主品** · `products/vivian_paid_quiet_money_rules.pdf` · **`$15`** · 按钮 `Get The Quiet Money Rules`
```text
The Quiet Money Rules — Spending Choices, Money Talk & Boundaries

An 11-page printable guide. Read the part you need; there is nothing to keep up with.
• Part I: 10 spending rules + a worksheet (your "flowers", your hard-month number, a 48-hour waiting list)
• Part II: what to say when asking for a raise, and when more work arrives with no more pay
• Part III: kind sentences for splitting bills, trips, weddings, gifts, and a page on lending
• Part IV: a monthly money date for couples and a one-hour monthly review sheet

Vivian Sterling is an AI-generated character with a fictional background. General education, not financial, investment, tax or legal advice.
```
**Order Bump `+$9`** · `Money Talk Cards: Raises, Loans & Splitting the Bill`（⚠️ PDF 尚未制作，上线前补齐或先不开加购）

### 2. June Whitaker

**免费诱饵** · `products/june_free_3day_notice_journal.pdf` · `$0+` · 按钮 `Get the Free Notice Journal`
```text
The 3-Day Notice Journal — Three Small Moments Worth Writing Down

A free 4-page printable from June. For three days, watch for one small moment and write down what happened, not what it means.
• Day 1: the hand-back
• Day 2: when the plan goes wrong
• Day 3: the swap
Plus a page on telling a single moment from a pattern.

June Whitaker is an AI-generated character with a fictional background. For personal reflection, not counseling or therapy.
```

**付费主品** · `products/june_paid_contact_sheet.pdf` · **`$14`** · 按钮 `Get The Contact Sheet`
```text
The Contact Sheet — From Noticing to One Honest Conversation

An 11-page printable journal with Dating and Partnered editions in one file.
• Record: two weeks of small moments, facts first
• Find what repeats: separate single frames from patterns
• Prepare one conversation: what you noticed, how it landed, what you'd like, a question for them
• Branch A (dating) and Branch B (long-term partners), each with examples and openers
• Two weeks later: a page to look back at what changed
• Safety page with US hotline resources

June Whitaker is an AI-generated character with a fictional background. Not counseling or therapy; it can't tell you what a relationship means.
```
**Order Bump `+$9`** · `50 Deep Conversation Cards`（⚠️ PDF 尚未制作）

### 3. Henry Wen

**免费诱饵** · `products/wen_free_tea_drawer.pdf` · `$0+` · 按钮 `Get The Tea Drawer`
```text
The Tea Drawer — 20 Pause Cards, Picked by Situation

A free 5-page printable from Henry Wen. Find the situation you're in, take one small pause, close the drawer.
No days to complete, no streaks, skip any card.
• Cards for before an email, before a meeting, the 2 p.m. slump, Sunday evening, 3 a.m. thoughts and more
• Several cards carry a short line from Zhuangzi or the Tao Te Ching, with the chapter noted

Henry Wen is an AI-generated character with a fictional background. Not therapy. If you're struggling, call or text 988 (US).
```

**付费主品** · `products/wen_paid_doing_less_case_by_case.pdf` · **`$14`** · 按钮 `Get Doing Less, Case by Case`
```text
Doing Less, Case by Case — One Story, One Small Step, One Thing to Skip

An 11-page printable you look up when you need it, not a program.
16 everyday troubles across work, rest, people and mind: the boss adds a project, the inbox at midnight,
Sunday dread, a friend asks to borrow money, trying to fix yourself, and more.
For each: a story retold from Zhuangzi or the Tao Te Ching (chapter noted), one small step today, one thing you can skip today.
No schedule, no tracking.

Henry Wen is an AI-generated character with a fictional background. Not therapy. If you're struggling, call or text 988 (US).
```
**Order Bump `+$9`** · `30 Tao Te Ching Cards (Original + English)`（⚠️ PDF 尚未制作；原文须用户逐条核对）

---

## 三、 ManyChat「评论关键词 → 自动私信」配置

### 3.1 通用节点流（Instagram Automation → User comments on your Reel）

1. **触发**：评论包含 `RULES` / `NOTICE` / `TEA`（不区分大小写）。
2. **公开回复评论（3 条轮换）**：
   - `Sent it to your DMs. Check Requests if you don't see it 💌`
   - `Just sent it over. Peek at your message requests 👇`
   - `It's in your DMs now.`
3. **第 1 条私信 + 按钮**：
   - **Vivian (`RULES`)**：*"Here's your Approval Tax Audit, darling 💐 Ten quiet minutes with your statements is all it takes to start. Keep what you love. Question the rest."*
     - 按钮 1：`Get the Free Audit` → Gumroad 免费品
     - 按钮 2：`The Quiet Money Rules ($15)` → Gumroad 付费品
   - **June (`NOTICE`)**：*"Here's your 3-Day Notice Journal 📷 One small moment a day. Write what happened, not what it means."*
     - 按钮 1：`Get the Free Journal` → Gumroad 免费品
     - 按钮 2：`The Contact Sheet ($14)` → Gumroad 付费品
   - **Wen (`TEA`)**：*"Here's The Tea Drawer, my friend 🍵 No order, no streaks. Open it when you need it."*
     - 按钮 1：`Get The Tea Drawer` → Gumroad 免费品
     - 按钮 2：`Doing Less, Case by Case ($14)` → Gumroad 付费品
4. **23 小时后追发一次（Smart Delay 23h，在 IG 24 小时窗口内；只发一次，不连环催）**：
   - **Vivian**：*"Did the audit turn up a tax or two? If you'd like the scripts for the conversations that follow, raises, loans, splitting the bill, they're in The Quiet Money Rules."*
   - **June**：*"Noticed anything yet? If a moment keeps coming back, The Contact Sheet walks you from noticing to one honest conversation."*
   - **Wen**：*"No need to have used any cards yet. If the same trouble keeps showing up, Doing Less, Case by Case lets you look it up when it does."*
   - 每条只配一个按钮，指向付费品。

### 3.2 危机固定回复（三个账号都要配，June 和 Wen 必配，上线前完成）

ManyChat 对**私信内容**设置关键词规则（Default Reply 之前优先匹配），命中后发送固定回复，打上 `crisis` 标签，**把该用户移出所有营销序列**，并开启人工接管（Live Chat）。

- **关键词（模糊匹配，按需增补）**：`suicide`、`kill myself`、`end it all`、`want to die`、`self harm`、`hurt myself`、`no reason to live`；June 另加 `he hits me`、`afraid of him`、`afraid of her`、`abuse`、`controlling`。
- **固定回复（Wen / Vivian）**：
  > *"I'm really glad you wrote. I'm an AI character and can't help with this the way a person can. If you're in the US, please call or text 988 to reach the Suicide & Crisis Lifeline any time. Outside the US, please contact your local emergency number or a crisis line near you. If you're in immediate danger, call 911."*
- **固定回复（June，含亲密关系暴力资源）**：
  > *"I'm really glad you wrote. I'm an AI character and can't help with this the way a person can. In the US, the National Domestic Violence Hotline is 1-800-799-7233, or text START to 88788 (thehotline.org). If you're thinking about hurting yourself, call or text 988. If you're in immediate danger, call 911."*
- **人工兜底**：关键词匹配一定会漏判。上线后**每天至少一次人工翻看私信**，发现漏网的危机消息就手动打标签、发上面的回复。

---

## 四、 14 天冷启动排期与赛马决策

1. **发布节奏（美东 08:30 / 12:30 / 19:30）**：
   - **Day 1–3**：三个号各发 3 条（`V01–V03` / `J01–J03` / `W01–W03`），看哪个人设的开头留存最高。
   - **Day 4–7**：每天各发 1–2 条。哪怕某个号暂时只有几百播放，也不撤主页链接和 ManyChat，因为延迟爆发常出现在第 6–7 天。
   - **Day 8–10**：发完各自 10 条；给领过免费品的邮箱发**一封**付费品介绍邮件（只发一次，只描述内容）。
2. **Day 14 决策门槛**：
   - **暂停线**：单号发满 10 条后，最高单条播放仍 `< 2,000` 且关键词评论 `< 10` 条，暂停该号的 GPU 投入，先复盘脚本和首帧。
   - **放大线**：任意账号单条破 `10,000+` 播放或稳定出单，就按同一人设扩写第 11–30 条，并补齐对应的 Order Bump PDF。
3. **每周人工抽查**：随机读 5 条 caption、5 封自动私信，对照性格档案第一节的三条风控线。
