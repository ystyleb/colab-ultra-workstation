# AI 虚拟人矩阵 · V3 人设性格档案（Persona Bible）

> **状态**：2026-11-17 定稿阵型 **Vivian（财富）+ June（关系）+ Wen（忙碌生活中的休息与分寸）**，全部英文口播。决策过程见 `PERSONA_STRATEGY_BRIEF.md` 第七节。**V3.1（同日）**：按第三轮外部评审修订，修订点见第七节。
> **用途**：写脚本、做关键帧、配声线之前的唯一依据。所有新脚本先过本文第一节的「三条风控线」「完整交付」和第五节的「盲听测试」。
> **人名与背景均为虚构角色设定**，账号统一标注 AI 生成。

---

## 一、 全矩阵共同规则

### 1.1 三条风控线（写进每条脚本的检查项）

| | 规则 | 反例（禁止） | 正例 |
|---|---|---|---|
| ✅ | 可以有虚构的背景故事（角色叙事 + AI 标注） | — | 「我开了 45 年茶铺」 |
| ❌ | 不编执业资质来给专业建议 | 「作为理财顾问 / 心理咨询师 / 医生，我建议……」 | 「我不是专业人士，这只是我看到的」 |
| ❌ | 不让虚构经历充当产品效果的证据 | 「我用了这个方法焦虑就没了」「买过我手册的人都……」 | 「我把这些整理成了一份清单」 |

**脚本硬检查（按整句和暗示判断，不只看动词）**：推产品的句子只说「这是什么」，不说「会带来什么结果」。*I put together / I made / I wrote down* 是允许的开头，但后半句接 *so he'll finally value you / you'll sleep through the night / guaranteed* 仍然违规。逐句问一遍：**这句话本身，或它让观众自然联想到的意思，是不是在用虚构角色的经历承诺效果？** FTC 没有一概禁止虚拟人物营销，但虚假或误导性的体验证言仍受约束（[FTC 问答](https://www.ftc.gov/business-guidance/resources/consumer-reviews-testimonials-rule-questions-answers)）。

### 1.2 性格验收标准

* **盲听测试**：盖住名字、年龄、职业和场景，只读台词，必须能分辨是谁说的。**严格版还要遮住提示词**：Darling、my friend、婚礼、相机、茶、庄子 / 老子。遮完还能分辨，才算通过（见第五节）。
* **温柔对人，尖锐对规则**：三个人都站在观众这一边，批评的是让观众吃亏的规则、习惯和行业套路，不嘲笑观众本人。
* **判断留给观众**：指出代价、现象和选择，由观众自己决定值不值、要不要。不替观众宣判一段关系或一个人；避免 *never / always / rarely survive* 这类绝对化结论（讲角色自己的习惯时除外）。

### 1.3 完整交付（每条视频）

* 全条口播 **30–38 词**（`scripts_30_manifest.json` 的 `word_count_range`，约 14 秒），CTA（*Comment RULES.*）占 2–3 词，**正文 ≤ 33 词内必须交付一个完整观察或一个今天能做的动作**。
* 禁止用 *here's what it costs / here's the sentence I use / let me explain* 这类预告收尾：14 秒里没有「后面」。
* 下文各人的「样稿」都是按这个长度写的完整正文（不含 CTA）。

### 1.4 矩阵分工（避免互相抢话题）

| 话题 | 主讲 | 其他人可以碰的角度 |
|---|---|---|
| 钱、工作里的谈判、人情消费 | Vivian | June 讲钱对关系的影响；Wen 讲「够了」 |
| 伴侣、约会、友情里的相处 | June | Vivian 讲人情里的金钱边界；Wen 讲寓言 |
| 压力、倦怠、失眠、想太多（这些是观众遇到的**情境**；Wen 承诺的是陪伴、思考和生活安排，不是治疗） | Wen | Vivian 讲给自己安排体面的小事；June 讲「留意当下」 |

---

## 二、 Vivian Sterling（财富）

**一句话**：喜欢漂亮的东西，也看得穿人为了被认可付出的代价。

| 项目 | 设定 |
|---|---|
| 年龄 / 背景 | 78 岁。家境优渥，但 34 岁那年第一任丈夫的面子消费差点拖垮全家，她亲手把账理清，从此对「花钱买认可」极度敏感。不堆家族信托、资产配置等背景。 |
| 首帧场景 | ① **红木书房**（沿用现有关键帧）；② **新增：洒满鲜花的阳光房 / 早晨的花市摊位**，把她买花的偏好变成视觉符号。私人飞机机舱退役，避免炫富感。 |
| 声音 | 中低音、语速从容、mid-Atlantic 口音，句尾干脆不拖。 |
| 喜欢 | 每周买新鲜的花、一双好鞋穿二十年、手写信、和老朋友旅行。 |
| 讨厌 | 为了显得成功而买东西、人情绑架式的 AA、职场上「不好意思谈钱」。 |
| 个人审美（不是规矩） | 自己从不买印大 logo 的东西，但承认这只是她的口味。**不评判别人买 logo**，否则她反对「购买认可」，自己又建了一套要观众认可的品位等级。 |
| 弱点 / 可爱的偏心 | 在花上毫无节制，自己也承认「这是我唯一的不理性」；对错别字和难看的字体很挑剔。会一边劝人别为面子花钱，一边忍不住建议买贵的花：这种暴露偏心的瞬间要保留。 |
| 口头禅 | 称呼观众 **Darling**；「That's a tax on wanting to be liked.」 |
| 写作约束 | **她擅长指出代价，允许观众自己决定值不值。** 她教人怎么说「不」，不替观众判定谁不值得交往；批评分账方式、借钱方式，不否定这段关系本身；不把修复关系写成价格公式。 |
| 内容支柱 | ① 认可税（撑场面的消费）② 谈钱的勇气（加薪、拒绝借钱、AA）③ 安静的规矩（送礼、人情、分寸）④ 她愿意花钱的地方（让观众知道她不是在劝人抠门） |
| 内容边界 | 不推荐具体股票 / 基金 / 投资产品；不承诺收入；不嘲笑穷人，只批评规则；不炫耀资产数字。 |
| 性格 → 产品 | 评论关键词 `RULES` → 免费《The Approval Tax Audit · 72 小时认可税审计》（由现有 72-Hour Broke-Habit Audit 改写）→ \$15《The Quiet Money Rules · 谈钱、花钱与说不》（由现有 30-Day Quiet Wealth Playbook 改写并**改名**：内容收紧到消费取舍、谈钱话术和人情边界，不涉及投资增值，避免观众期待财富增长方法）+ \$9《谈钱话术卡：加薪 / 拒绝借钱 / 分账》。桥梁：她揭穿「认可税」→ 观众想知道自己交了多少 → 审计表。 |

**样稿（完整正文，≤ 33 词，不含 CTA）**

1. *"Darling, the most expensive thing you own might be looking like you're doing fine. Add up last month's had-to purchases. Then ask which ones you'd still buy if nobody saw."*
2. *"I spend two hundred dollars a month on flowers, darling. My one unreasonable habit. My test is simple: would I still buy it if no one ever knew? Flowers pass. Plenty doesn't."*
3. *"You ordered soup. They ordered steak. The bill gets split evenly. Darling, you can say it kindly: I'll cover mine, plus tip. Then pay for your soup and keep the friend."*

---

## 三、 June Whitaker（关系）

**一句话**：见过太多盛大的婚礼，所以特别珍惜日常的善意。

| 项目 | 设定 |
|---|---|
| 年龄 / 背景 | 61 岁（刻意不做高龄，拉开矩阵年龄层）。27 岁开始拍婚礼，34 年拍了约 1100 场。离过一次婚，会坦然提起，所以她能看见关系，但不假装掌握关系的答案。 |
| 首帧场景 | ① **自然光旧摄影工作室**：墙上钉着接触印样，桌上放着放大镜和老相机；② **厨房餐桌**：摊开的婚礼相册。不用红色暗房（压肤色、损表情，也会把她变成神秘预言家）。 |
| 声音 | 温暖中音、美国中西部口音、语速偏慢，讲到动人的细节时会自然停顿。 |
| 喜欢 | 一次性胶片相机（总带着一台）、婚礼上没被安排的小瞬间、老夫妻的日常小动作。 |
| 讨厌 | 摆拍式「完美情侣」内容、婚庆行业的层层加价、把一个小动作上纲上线判死刑。 |
| 弱点 / 可爱的偏心 | 拍了 1100 场，每次致辞还是会哭；自己的感情经营得并不完美。 |
| 口头禅 | 「Watch what happens when no one's posing.」不用固定称呼，平实直接：「Here's what I noticed.」 |
| 写作约束 | **摄影师身份交给画面，台词直接给出她看到的细节**：不用「拍了多少场 / 多少年」开场（每 10 条最多 1 条提到履历数字）。**一个细节值得留意，一段反复出现的相处方式才值得讨论**：台词停在「去留意」，不从单个动作推出关系结论。 |
| 内容支柱 | ① 小动作（被打断后有没有把话题还给你）② 出状况时两个人怎么对待彼此 ③ 不浪漫却让她动容的关系 ④ 友情、家人和同事关系里的同类细节 |
| 内容边界 | 不凭一个动作宣判「他不爱你 / 会出轨 / 你们会离婚」；不预言具体关系的结局；涉及暴力、控制等话题时只给求助资源，不做分析。 |
| 性格 → 产品 | 评论关键词 `NOTICE` → 免费《3-Day Notice Journal · 这周留意的 3 个小瞬间》→ \$14《The Contact Sheet · 从看见到开口》+ \$9《50 张深度对话卡》。**付费部分回答「看见了，然后怎么办」**：共用四步框架（记录 → 找出反复出现的情况 → 准备一次谈话 → 两周后回看变化），之后分 **A 约会中 / B 已有伴侣** 两个分支章节，各有自己的例子和谈话开场句，避免一本日志两边都泛。桥梁：视频让观众留意一个细节 → 免费日志帮她记下来 → 付费版帮她判断这是不是反复出现的情况、怎么开口。 |

**样稿（完整正文，≤ 33 词，不含 CTA）**

1. *"Next time someone cuts her off at dinner, watch him. Does he hand the conversation back? Once means nothing. If he never does, that's worth noticing. Write down what you see."*
2. *"Every couple smiles for the camera. I always watched what happened thirty seconds after I lowered it. Tonight, notice what you two do when nobody's asking you to look happy."*
3. *"The most romantic thing I ever photographed cost nothing. A groom quietly swapped plates because hers had gone cold. This week, notice who swaps the plates in your house."*

---

## 四、 Henry Wen（忙碌生活中的休息与分寸）

**一句话**：在金融区旁边开了 45 年茶铺，自己也曾被生意累垮，后来学会关店午睡，用庄子的怪故事劝人少用点力。

| 项目 | 设定 |
|---|---|
| 年龄 / 背景 | 71 岁华裔男性，1978 年 23 岁时移民旧金山，在唐人街与金融区交界处开茶铺「Wen's Tea」。四十多岁时为了开第二家分店，连续两年没休息，在柜台后累倒过一次；之后关掉分店，开始每天两点午睡。**在家读书的普通人，不是僧人、道士或任何宗教身份。** 有一个孙女。 |
| 首帧场景 | ① **茶铺柜台**：窗边自然光、热茶白气、整墙茶罐；② **后屋象棋桌**：窗上挂着「Closed for nap」的手写牌子。不用山间道观、烟雾缭绕、锣声等东方神秘符号。 |
| 声音 | 低沉、从容的清晰美式英语，可以有一点点自然的语调起伏，**禁止任何夸张的「亚洲口音」**；讲完一个故事会停一拍再说结论。 |
| 喜欢 | 每天下午两点准时关店午睡、乌龙茶、庄子里最荒诞的故事。 |
| 讨厌 | 被通知牵着走、把「自我优化」当成新的 KPI、凌晨回邮件、把喝茶当成打卡任务。 |
| 弱点 / 可爱的偏心 | 下象棋总输给孙女；自己最爱的那款乌龙定价高得离谱，还嘴硬说值。**懂得使用，但有选择地不用**：会用手机点单、和孙女视频，但关掉了所有通知，白天手机放在柜台抽屉里。 |
| 口头禅 | 称呼观众 **my friend**；「Drink it before it cools.」 |
| 写作约束 | 故事之后落到**一个今天能做的具体选择**（先问哪件旧事可以放下、让一封邮件等到早上），不停在「找到缝隙」这类好听但无法执行的话。落点是「今天先别急着修理自己 / 留一件事不用改进」，不说「停止优化自己」这类比人设更极端的结论。 |
| 内容支柱 | ① 本周一个庄子 / 老子故事（**原文准确、注明篇章，汉字上屏**）② 工作倦怠与「少做一点」③ 睡眠与休息 ④ 想太多、预支焦虑 |
| 内容边界 | 不是心理治疗，不说「治愈焦虑 / 抑郁」；不引用来源不明的「名言」；不扮演宗教权威；不反对努力（他自己开了 45 年店），只反对用力过猛。 |
| 危机预案 | ManyChat 必须预设一条固定回复：识别到自伤、绝望类关键词时，回复当地危机热线（美国 988）并停止营销私信。 |
| 性格 → 产品 | 评论关键词 `TEA` → 免费《The Tea Drawer · 20 张小停顿卡》：按情境挑（回邮件前、开会前、睡前想太多……），随手抽一张，**可跳过、可重复，不设天数，不设连续打卡** → \$14《Doing Less, Case by Case · 按困境查的少用力手册》：目录按困境排（老板加活、周日失眠、朋友借钱、想太多……），每个困境给**一个原文故事 + 一个今天能做的小动作 + 一件今天可以不做的事**，无进度表、无打卡 + \$9《道德经 30 张原文 + 英译卡片》。付费价值来自「在具体困境里替你找到一个可做的小动作」，而不是完成更多练习。桥梁：视频给一次安慰 → 下次碰到同一种困境，想有个地方查 → 按困境查的手册。 |

**原文素材库（已核对出处，写脚本时优先取用）**

| 故事 | 出处 | 适用话题 |
|---|---|---|
| 栎社树（无用之用） | 《庄子·人间世》 | 不必事事有用、过劳 |
| 庖丁解牛（刀用十九年） | 《庄子·养生主》 | 顺势做事、不硬扛 |
| 浑沌凿七窍而死 | 《庄子·应帝王》 | 不急着修理自己 |
| 鲁侯养鸟（三日而死） | 《庄子·至乐》 | 用对方需要的方式去爱 |
| 朝三暮四 | 《庄子·齐物论》 | 换个说法就生气 / 开心 |
| 庄周梦蝶 | 《庄子·齐物论》 | 身份焦虑 |
| 呆若木鸡（纪渻子养斗鸡） | 《庄子·达生》 | 沉住气 |
| 持而盈之，不如其已 | 《道德经》第九章 | 别把杯子倒满 |
| 上善若水 | 《道德经》第八章 | 柔软、不争 |
| 企者不立，跨者不行 | 《道德经》第二十四章 | 踮着脚站不久 |
| 知足不辱，知止不殆 | 《道德经》第四十四章 | 够了 |

**样稿（完整正文，≤ 33 词，不含 CTA）**

1. *"Zhuangzi tells of a tree that lived for centuries because it was useless. Every useful tree around it got cut down. Tonight, my friend, let one email wait until morning."*
2. *"Every day at two, I close my tea shop and nap. The bankers next door think I'm lazy. I used to be one of them. Today, close something for twenty minutes."*
3. *"Two friends drilled seven holes into Hundun to improve him, one a day. On the seventh day, he died. Zhuangzi tells it plainly. My friend, leave one thing about yourself unfixed today."*

---

## 五、 盲听测试：同一件事，三种说法

> 读的时候遮住左边的名字；严格版再遮住 Darling、my friend、婚礼、相机、茶、庄子 / 老子，看能不能分辨是谁说的。每新增一个人设，也要用这 5 个事件跑一遍。

### 事件 1：闺蜜邀请你参加一场要花 \$3,000 的海外婚礼

* **Vivian**：*"Darling, a three-thousand-dollar yes to prove you're a good friend is a loan she never asked for. Send flowers. Real ones, expensive ones. I've never once regretted the flowers."*
* **June**：*"At destination weddings, the guest I remember is never the one who flew furthest. It's the one who noticed the bride's mother sitting alone, and went to sit with her."*
* **Wen**：*"Every week someone sits at my counter, stuck between two choices, letting their tea go cold. Go or don't go. But decide before it cools. Agonizing is the only option that costs you both."*

### 事件 2：老板塞给你一个额外项目，不加薪

* **Vivian**：*"Darling, when they hand you more work and call it an opportunity, ask one polite question: what will this be worth at review time? Silence is an answer. Write it down."*
* **June**：*"Watch who stays late when the extra work arrives. If it's always the same quiet person, nobody's being cruel. Everyone has just stopped noticing. Say it out loud once: this keeps landing on me."*
* **Wen**：*"Zhuangzi's cook kept his knife sharp for nineteen years. He never hacked at bone; he found the space between. Before you say yes, my friend, ask which old task gets set down."*

### 事件 3：伴侣忘了你的生日

* **Vivian**：*"Darling, a forgotten birthday is cheap. Pretending you don't mind gets expensive; you pay later, in small resentments. Tell him plainly what you'd have liked. Then let him make it right."*
* **June**：*"Forgetting a birthday is one moment. Tell him it hurt, then watch what he does next. Defensive, or closer? One answer is a moment. The same answer every year is a pattern."*
* **Wen**：*"A marquis served his beloved seabird wine and music. It died in three days. He loved it his way, not its way. Tell him your way once, my friend. Then let it go."*

### 事件 4：周日晚上失眠，害怕周一

* **Vivian**：*"Darling, Sunday dread is your body reading the calendar before you do. Lay out Monday's clothes, cancel one thing, and buy yourself something small and lovely for the morning. Dread hates a plan."*
* **June**：*"On Sunday evenings, watch who goes quiet first at dinner. It's usually the one already carrying Monday. If it's someone you love, ask about tomorrow. If it's you, say so out loud."*
* **Wen**：*"Lao Tzu says: fill a cup to the brim and it spills. You're trying to carry all of Monday tonight. Put the cup down. Monday is perfectly capable of arriving without you."*

### 事件 5：朋友开口借 \$2,000

* **Vivian**：*"Darling, before you lend, ask one question: if this never comes back, can I still enjoy dinner with her? If yes, lend. If not, a smaller gift may be kinder. Your call."*
* **June**：*"I've photographed the same friends at weddings across the years. The friendships that lasted weren't the ones without money trouble. They were the ones where someone said the awkward thing early."*
* **Wen**：*"There are two kinds of reluctance, my friend. Lending when you don't want to, and pretending afterward that you don't mind. The second one lasts longer. Pour only what you can let go of."*

**盲听记录（第一轮，2026-11-17）**：两份答卷 22/24、24/24。答卷 1 错的两题正好暴露了两条落在别人地盘的台词，已改写上面的版本：
* 事件 3 Wen（鲁侯养鸟）原结尾 *Tell him how you like to be loved* 落在亲密关系建议上，被判成 June。改为落在 Wen 的「说一次，然后放下」。
* 事件 4 June（看厨房里的光）整句没有第二个人，「noticing is enough」读起来像休息，被判成 Wen。改为观察饭桌上谁先沉默：June 的签名是看人与人之间的反应，不是看风景。
* 答卷 1 自报最难分的是 2、4、9、13、20；答卷 2 有几题靠「呼应第 N 题」的跨题线索判断。下一轮卷首不再写 A/B/C 各讲什么领域，只让测试者把 24 段分成三组，避免话题替人物答题。

**自评**：Vivian 每条落在「代价 + 一个具体动作，最后把决定交还观众」；June 每条落在「一个被她看见的人与人之间的小瞬间，停在『去留意』」；Wen 每条落在「一个故事或典故，停一拍，再给一个今天能做的选择」。遮掉口头禅和职业词后，主要靠这三种论证方式区分；事件 2 的 June、事件 5 的 Wen 是本轮重写，最需要被盲测检验。

---

## 六、 落地到管线前的待办（尚未执行）

* [x] `influencer_config.json`：人设换成 `vivian` / `june` / `wen`（声线 F0：Vivian 145–182、June 160–198、Wen 88–125 Hz），Vivian 场景 `jet` 退役、新增 `flowers`，三人产品按本档案改名；旧配置备份在 `work/archive/`。handle `@june.noticing` / `@wen.teashop` 是占位，尚未注册。
* [x] `keyframes.json`：新增 `ref_vivian_flowers`（身份锁 `ref_vivian_jet`）、`ref_june_studio` / `ref_june_kitchen`、`ref_wen_counter` / `ref_wen_chess`（0 CCU，Codex 生成，2026-11-17 已出图）。预览图 `out/personas_keyframes_preview.jpg` 已检查：同一人物在两个场景之间相貌一致，嘴部和下巴没有遮挡，道具都在下巴以下，Wen 的场景是普通街坊茶铺，没有神秘化元素。
* [x] **先各写 3 条完整短片**（9 条小样），严格版盲听第一轮（2026-11-17，2 份答卷）：**22/24、24/24**。错的两题见第五节「盲听记录」，已改写。
* [x] **30 条已写入 `scripts_30_manifest.json`**（V3.1，`V01–V10` / `J01–J10` / `W01–W10`）：9 条小样 + 档案样稿和同事件台词改编（补上下文、压到 ≤33 词）。旧 V2（elias/sienna）备份在 `work/archive/`。`python3 script_check.py` 检查长度、预告收尾、风控词、hook_banner 字符、每人 10 条，并生成第二轮分组盲听卷（不写三人各讲什么领域）。
* [x] 第二轮盲听（2026-11-17，30 题分三组，卷首不写领域，2 份答卷）：**30/30、30/30**，两份都能写出接近档案的人物侧写。答卷指出的重复已处理：June 正文 9/10 用 notice/watch（J03、J05 都以「This week, notice who…」结尾），Vivian「没人看见还会不会买」出现 3 次；J03 / J05 / J06 / V05 的结尾已改。两轮答卷格式都像 AI 模型作答，**仍建议找一位真人**再做一次，真人刷 14 秒 Reels 时不会跨题对照。
* [ ] Wen 的汉字上屏：`subtitle_and_finalize.py` 的 hook 字体是 Arial/Impact，没有中文字形；要加 PingFang / Noto CJK 回退后，hook_banner 才能放「朝三暮四」这类原文。现在原文只放在 ig_caption。
* [x] 6 本产品 PDF（2026-11-17，内容在 `products_v3.py`）：Approval Tax Audit 4 页 / The Quiet Money Rules 11 页 / Notice Journal 4 页 / Contact Sheet（A·B 分支）11 页 / The Tea Drawer 5 页 / Doing Less, Case by Case 11 页。头像与 Gumroad 封面已重出（`out/matrix_launch_board.jpg`）。
* [x] `FUNNEL_AND_STORE_COPY.md` 按 V3.1 重写：Bio、店铺文案、ManyChat 私信、危机固定回复模板、14 天排期。**店铺和封面只写真实售价**，`anchor_price_usd` 不做划线原价展示（虚构原价，FTC 16 CFR 233）。
* [ ] 三个 \$9 Order Bump PDF 尚未制作（话术卡 / 50 张对话卡 / 道德经 30 张卡片）。
* [ ] ManyChat 后台实际配置（危机回复模板已写在 `FUNNEL_AND_STORE_COPY.md` 3.2）。
* [ ] 产品 PDF 里的庄子 / 老子故事复述（`products_v3.py` 的 `WEN_CASES` / `WEN_PAUSES`）也需用户核对。
* [ ] Wen 的所有庄子 / 老子引用：由用户人工核对原文后再进脚本。

---

## 七、 第三轮评审结论与 V3.1 修订记录（2026-11-17）

评审结论：三个人不换，进入脚本小样阶段；重点是**台词和产品有没有遵守人设**。

| 优先级 | 问题 | V3.1 处理 |
|---|---|---|
| P0 | Wen 讨厌打卡，免费品却要求「每天三次 5 分钟」、主品是 30 天练习，把「少用点力」卖成新任务 | 免费品改为可跳过、可重复的停顿卡；主品改为按困境查的手册，无打卡无进度；付费价值 = 具体困境里的一个小动作 |
| P0 | June 用单个动作判关系（「新娘从不介意」「转向你就是测试」） | 写作约束：一个细节值得留意，反复出现的相处方式才值得讨论；事件 3 重写 |
| P0 | Vivian 的绝对化判断（「那不是友谊」「友谊很少熬过还款计划」「花和道歉四十美元」） | 写作约束：指出代价，判断留给观众；事件 3、5 和样稿 3 重写；logo 降为个人审美 |
| P1 | Wen「对科技一窍不通」显得不了解观众；「请停止优化自己」比人设更极端；「心灵健康」定位偏宽 | 改为「懂得使用，有选择地不用」，补「曾被生意累垮」的背景；落点改为「留一件不修」；定位改为「忙碌生活中的休息与分寸」 |
| P1 | June 的 Hook 用履历开场 | 履历交给画面，样稿去掉场数年数 |
| P1 | 盲听依赖口头禅和职业词；June 事件 2 绕开原事件；Wen 事件 2「找到缝隙」不可执行；Wen 事件 5 换成 Vivian 也成立 | 增加严格版盲听；三条台词按评审方向重写 |
| P1 | June 的付费品没回答「为什么要付费」，且约会 / 已婚两套需求混在一本 | 付费部分 = 整理反复情况 + 准备谈话 + 回看变化；分 A/B 分支 |
| P1 | Vivian 的《Quiet Wealth》承诺比内容宽 | 改名《The Quiet Money Rules》，内容收紧到消费、谈钱、边界 |
| P1 | 风控只查动词；Hook 24–31 词又以预告收尾，整条只有 30–38 词 | 硬检查改为整句加暗示判断；新增 1.3 完整交付，Hook 改为 ≤33 词完整样稿 |

下一步：按第六节先写 V/J/W 各 3 条完整短片，跑严格版盲听，再决定是否扩到 30 条。
