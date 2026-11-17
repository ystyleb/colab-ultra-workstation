#!/usr/bin/env python3
"""V3.1 产品内容（Vivian / June / Wen），由 build_digital_products.py 调用渲染成 PDF。

写作约束来自 PERSONA_BIBLE_V3.md：
- 三条风控线：不编执业资质；不让虚构经历充当产品效果证据（不写「读者反馈」「保证见效」）。
- Vivian：只讲消费取舍、谈钱话术、人情边界，不涉及投资增值。
- June：四步框架（记录 → 找反复 → 准备一次谈话 → 两周后回看），A 约会中 / B 已有伴侣两个分支；不替读者宣判关系。
- Wen：不设天数、不设连续打卡，按困境查；原文须准确并注明篇章；不是心理治疗，附 988。
"""

from __future__ import annotations

from build_digital_products import esc, make_footer, make_header, wrap_doc

# ---------------------------------------------------------------------------
# 排版小工具
# ---------------------------------------------------------------------------


def page(tag: str, n: int, total: int, title: str, body: str, brand: str, note: str) -> str:
    return f'<div class="page">{make_header(tag, n, total)}<h2>{title}</h2>{body}{make_footer(brand, note)}</div>'


def cover(kicker: str, title: str, sub: str, box_title: str, box_body: str, lower: str, brand: str, meta_right: str) -> str:
    return (
        f'<div class="page cover-page"><div><span class="kicker">{kicker}</span>'
        f'<h1 class="cover-title">{title}</h1><p class="cover-sub">{sub}</p>'
        f'<div class="cover-box"><h3>{box_title}</h3>{box_body}</div></div>'
        f'<div>{lower}<div class="cover-meta"><span>{esc(brand)}</span><span>{meta_right}</span></div></div></div>'
    )


def cards(items: list[tuple[str, str]]) -> str:
    return "\n".join(f'<div class="card"><h3>{t}</h3>{b}</div>' for t, b in items)


def callout(label: str, text: str) -> str:
    return f'<div class="callout"><strong>{label}</strong> {text}</div>'


def lines(n: int) -> str:
    return '<div class="write-line"></div>' * n


def table(headers: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{h}</th>" for h in headers)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>"


def blank_rows(cols: int, n: int, height: int = 22) -> list[list[str]]:
    first = f'<div style="height:{height}px;"></div>'
    return [[first] + [""] * (cols - 1) for _ in range(n)]


def cta(title: str, body: str) -> str:
    return f'<div class="cta-box"><h3>{title}</h3><p style="margin-bottom:0;">{body}</p></div>'


# ---------------------------------------------------------------------------
# Vivian Sterling
# ---------------------------------------------------------------------------

VIVIAN_CSS = {
    "bg_tint": "#FAF8F4",
    "accent": "#132924",
    "accent_soft": "#E9EFEA",
    "ink": "#1C1F1E",
    "muted": "#5A605E",
    "border": "#D5CFC0",
    "gold": "#B08D57",
}
VIVIAN_DISCLAIMER = (
    "Vivian Sterling is an AI-generated character. Her background is fictional. This guide is general education "
    "about spending habits and money conversations. It is not financial, investment, tax or legal advice."
)


def build_vivian_free() -> tuple[str, str]:
    brand = "Vivian Sterling (@vivian.oldmoney) · AI-generated character"
    total = 4
    p1 = cover(
        "FREE · 72-HOUR AUDIT",
        "The Approval Tax Audit",
        "72 Hours of Noticing What You Spend to Be Seen",
        "Darling, this is not a budget.",
        "<p>I'm not going to tell you to stop buying coffee. I'm going to ask one question about each purchase: "
        "<em>who was it for?</em> Some money buys you something. Some money buys you a look. The second kind is "
        "what I call the approval tax. You decide which taxes you're happy to keep paying.</p>",
        cards([
            ("Your 72 hours",
             "<p><strong>Hour 0–24 · Collect:</strong> write down your recent purchases. No judging yet.</p>"
             "<p><strong>Hour 24–48 · Sort:</strong> mark the ones you'd still buy if nobody ever saw.</p>"
             "<p><strong>Hour 48–72 · Decide:</strong> keep, trim, or say one sentence out loud.</p>"),
        ]),
        brand,
        "4-page printable",
    )
    p2 = page(
        "HOUR 0–24 · COLLECT", 2, total, "Write It Down Before You Judge It",
        "<p>Open your card and bank apps. List your last 12 purchases that weren't rent, bills or groceries. "
        "Then answer the only question that matters here.</p>"
        + table(["Date", "What", "$", "Would I buy it if nobody ever saw?"],
                [r[:3] + ["&#9744; Yes &nbsp; &#9744; No &nbsp; &#9744; Not sure"] for r in blank_rows(4, 12)])
        + callout("Vivian's note:", "\"Not sure\" is an honest answer. Leave it. We'll come back to it."),
        brand, "Collect",
    )
    p3 = page(
        "HOUR 24–48 · SORT", 3, total, "The Five Approval Taxes",
        "<p>Look at every \"No\" and \"Not sure\" from page 2. Which of these does it belong to?</p>"
        + table(
            ["Tax", "What it looks like", "Count", "$ total"],
            [
                ["<strong>The Keeping-Up Tax</strong>", "An upgrade you bought mostly because the people around you have it.", "", ""],
                ["<strong>The Doing-Fine Tax</strong>", "Picking up the check, the round, the nicer option, so nobody wonders.", "", ""],
                ["<strong>The Group Tax</strong>", "Even splits, group gifts and trips you wouldn't have chosen alone.", "", ""],
                ["<strong>The Can't-Say-No Tax</strong>", "Upsells, add-ons and favors you paid for because declining felt awkward.", "", ""],
                ["<strong>The Proof Tax</strong>", "Something bought to prove a point to one particular person.", "", ""],
            ],
        )
        + callout(
            "What is not a tax:",
            "flowers for your own kitchen, a good coat you'll wear for twenty years, dinner with someone you love. "
            "If you'd buy it with nobody watching, it isn't a tax, darling. It's your life. Enjoy it.",
        ),
        brand, "Sort",
    )
    p4 = page(
        "HOUR 48–72 · DECIDE", 4, total, "Keep It, Trim It, or Say It",
        "<p>Pick your biggest tax from page 3. You have three honest options. All three are allowed.</p>"
        + cards([
            ("1. Keep it, on purpose", "<p>If it's worth it to you, keep paying it. The difference is that now you chose it.</p>"),
            ("2. Trim it", "<p>Keep the habit, shrink the size: one round instead of two, the trip without the extra night.</p>"),
            ("3. Say one sentence",
             "<p><em>\"I'll cover mine, plus tip.\"</em><br/><em>\"I can't do the trip, but I'd love to take you to dinner when you're back.\"</em><br/>"
             "<em>\"I'm keeping this year simple. Can I bring something homemade?\"</em></p>"),
        ])
        + cta("The Quiet Money Rules · $15",
              "The full guide: 10 spending rules, scripts for raises, loans and splitting the bill, and worksheets for the "
              "conversations people put off. Tap the link in my bio.")
        + f'<p style="font-size:8.5pt;color:var(--muted);margin-top:10px;">{VIVIAN_DISCLAIMER}</p>',
        brand, "Decide",
    )
    return "vivian_free_approval_tax_audit.pdf", wrap_doc("The Approval Tax Audit", VIVIAN_CSS, [p1, p2, p3, p4], brand)


def build_vivian_paid() -> tuple[str, str]:
    brand = "Vivian Sterling (@vivian.oldmoney) · The Quiet Money Rules"
    total = 11
    p1 = cover(
        "THE COMPLETE GUIDE",
        "The Quiet Money Rules",
        "Spending Choices, Money Talk &amp; Boundaries",
        "Rules, darling. Not a diet.",
        "<p>This isn't a 30-day challenge and there's nothing to keep up with. Read the part you need, when you need it. "
        "It's about three things: how you choose what to spend on, how you talk about money out loud, and where you draw "
        "the line with the people you love.</p>",
        '<div class="grid-2">'
        '<div class="card"><strong>Part I</strong><br/>Spending Choices (pp. 2–4)</div>'
        '<div class="card"><strong>Part II</strong><br/>Money Talk at Work (pp. 5–6)</div>'
        '<div class="card"><strong>Part III</strong><br/>Friends, Family &amp; Lending (pp. 7–8)</div>'
        '<div class="card"><strong>Part IV</strong><br/>Partners &amp; Your Money Hour (pp. 9–11)</div>'
        "</div>",
        brand,
        "11-page printable guide",
    )
    p2 = page(
        "PART I · SPENDING CHOICES", 2, total, "Rules 1–5: Spend Loudly on Few Things",
        cards([
            ("Rule 1 · The nobody-saw test", "<p>Before you buy, ask: would I still want this if no one ever knew I had it? Yes means enjoy it. No means look again.</p>"),
            ("Rule 2 · Price it in hours", "<p>Divide the price by what you take home per hour. A $300 jacket at $25 an hour is twelve hours of your week. Sometimes that's worth it. Know before you pay.</p>"),
            ("Rule 3 · Name your flowers", "<p>Pick two or three things you genuinely love spending on. Spend on them without guilt. Mine is flowers. Spend quietly on almost everything else.</p>"),
            ("Rule 4 · A waiting list, not a willpower contest", "<p>Choose your own number. Anything above it goes on a list for 48 hours first. What you still want on day three, buy calmly.</p>"),
            ("Rule 5 · Know your hard-month number", "<p>Add up what you must pay in a bad month: rent, bills, food, minimums. Calm money starts with knowing that one number.</p>"),
        ]),
        brand, "Rules 1–5",
    )
    p3 = page(
        "PART I · SPENDING CHOICES", 3, total, "Rules 6–10: Protect the Pleasure",
        cards([
            ("Rule 6 · Remove one tap", "<p>Saved cards make buying effortless. Remove them from the shops you visit when you're tired or bored.</p>"),
            ("Rule 7 · Cancel what you'd never sign up for today", "<p>Read your last statement. Any subscription you wouldn't start today, end today.</p>"),
            ("Rule 8 · Buy once, buy well, when it matters to you", "<p>Shoes you'll walk in for twenty years are worth more than five pairs that look right for one season. This is a choice, not a rule for everyone.</p>"),
            ("Rule 9 · Don't upgrade on someone else's schedule", "<p>A new model came out. A friend renovated. Neither is a reason. Your reason is the only reason.</p>"),
            ("Rule 10 · Leave room for joy", "<p>A plan with no room for pleasure breaks by Friday. Write a small, lovely line into your month and keep it.</p>"),
        ]),
        brand, "Rules 6–10",
    )
    p4 = page(
        "PART I · WORKSHEET", 4, total, "My Flowers, My Taxes, My List",
        "<h3>My two or three flowers (spend on these without guilt)</h3>" + lines(3)
        + "<h3>My hard-month number</h3>"
        + table(["Rent / housing", "Bills", "Food", "Minimum payments", "Total"], blank_rows(5, 1, 28))
        + "<h3>My 48-hour waiting list</h3>"
        + table(["Date", "Item", "$", "Hours of work", "Day 3: still want it?"],
                [r[:4] + ["&#9744; Buy &nbsp; &#9744; Skip"] for r in blank_rows(5, 7)]),
        brand, "Worksheet",
    )
    p5 = page(
        "PART II · MONEY TALK AT WORK", 5, total, "Asking to Be Paid for What You Do",
        "<p>Most people don't lose money at work by being refused. They lose it by never asking. Prepare on paper first.</p>"
        "<h3>Before the conversation</h3>"
        + table(["What I've delivered in the last 6 months", "Proof (numbers, emails, results)"], blank_rows(2, 3, 26))
        + "<p><strong>The going rate:</strong> check two or three salary surveys or job postings for your role and city. Write the range: $________ to $________</p>"
        + cards([
            ("Opening line", "<p><em>\"I'd like to talk about my compensation. Over the last six months I've taken on ___ and delivered ___. "
             "For this role, the range I'm seeing is ___. I'd like to discuss moving to ___.\"</em></p>"),
            ("If they say \"not right now\"", "<p><em>\"I understand. What would need to be true for this to happen, and can we put a date on revisiting it?\"</em> Then write the date down and send a short email confirming it.</p>"),
        ]),
        brand, "Raises",
    )
    p6 = page(
        "PART II · MONEY TALK AT WORK", 6, total, "When They Call It an Opportunity",
        table(
            ["Situation", "What to say", "What to avoid"],
            [
                ["More work, same pay", "<em>\"Happy to talk about it. What will this be worth at review time?\"</em>", "Saying yes before you know what it's worth."],
                ["A new job offer", "<em>\"Thank you, I'm excited. Is there flexibility on the base?\"</em>", "Accepting on the spot to seem grateful."],
                ["Being asked to cover for someone, again", "<em>\"I can do this once. After that, let's find a plan that doesn't land on me each time.\"</em>", "Quietly absorbing it for months."],
                ["Unpaid \"quick favor\" from a client", "<em>\"Happy to help. That's outside our scope, so here's what it would cost.\"</em>", "Apologizing for having a price."],
                ["Review keeps getting moved", "<em>\"Can we set the date now and put it in writing?\"</em>", "Waiting to be remembered."],
            ],
        )
        + callout("Vivian's note:", "Silence is an answer too, darling. If you ask clearly and nothing comes back, write that down. It's information for your next decision, and the decision is yours."),
        brand, "Work scripts",
    )
    p7 = page(
        "PART III · FRIENDS &amp; FAMILY", 7, total, "Bills, Trips, Weddings &amp; Gifts",
        table(
            ["Situation", "One kind sentence"],
            [
                ["Splitting a bill evenly when you ordered less", "<em>\"I'll cover mine, plus tip.\"</em> Then pay for your soup and keep the friend."],
                ["A trip you can't afford", "<em>\"I can't do the whole trip. Could I join for one night, or host you when you're back?\"</em>"],
                ["A $3,000 destination wedding", "<em>\"I love you and I can't make the trip. I'd like to celebrate you properly at home.\"</em> Send a real gift and a handwritten note."],
                ["Group gift that's more than you'd spend", "<em>\"I'll give separately this time.\"</em>"],
                ["Holiday gift spiral", "<em>\"Can we do one name each this year?\"</em> Someone was hoping you'd say it."],
            ],
        )
        + callout("Remember:", "these sentences decline a cost, not a person. You can say no to the price and yes to the friendship in the same breath."),
        brand, "Friends & family",
    )
    p8 = page(
        "PART III · LENDING", 8, total, "Before You Lend, Ask One Question",
        "<p><strong>If this money never comes back, can I still enjoy dinner with this person?</strong></p>"
        + cards([
            ("If yes: lend, and write it down", "<p>Amount, date, and when you'd both like it settled. Writing it down isn't distrust. It saves both of you from remembering it differently.</p>"),
            ("If not: a smaller gift may be kinder", "<p><em>\"I can't lend that much, but I'd like to give you $___. No need to pay it back.\"</em></p>"),
            ("If neither feels right: decline warmly", "<p><em>\"I care about you, and I don't lend money to people I love. Can I help in another way?\"</em></p>"),
        ])
        + table(["Who", "Amount", "Date", "Agreed timing", "Status"], blank_rows(5, 4))
        + callout("Your call:", "there's no correct answer here, only the one you can live with."),
        brand, "Lending",
    )
    p9 = page(
        "PART IV · PARTNERS", 9, total, "The Monthly Money Date",
        "<p>Thirty minutes, once a month, somewhere pleasant. Not a trial. A conversation between two people on the same side.</p>"
        + table(
            ["Minutes", "Topic", "One question to ask"],
            [
                ["0–5", "Something good", "What did we spend on this month that we're glad about?"],
                ["5–15", "The numbers", "Where did the month go? Any surprises?"],
                ["15–25", "One decision", "What's one thing we'd like to change, or keep?"],
                ["25–30", "Something to look forward to", "What's one small, lovely thing we're planning?"],
            ],
        )
        + "<h3>Yours, mine, ours</h3><p>Some couples pool everything, some keep it separate, most do something in between. "
          "None is more grown-up than the others. What matters is that you both chose it out loud.</p>"
        + lines(3),
        brand, "Money date",
    )
    p10 = page(
        "PART IV · YOUR MONEY HOUR", 10, total, "One Hour a Month, With Something Nice",
        "<p>Pour something you like, put on good music, and spend one unhurried hour with your accounts. Use this sheet each month.</p>"
        + table(["Month", "Flowers (spent happily)", "Taxes I noticed", "One sentence I said", "One thing I'll change"], blank_rows(5, 12, 20)),
        brand, "Money hour",
    )
    p11 = page(
        "CLOSING", 11, total, "Gentle With People, Sharp With the Rules",
        "<p>You don't need to become someone who never spends. You need to know who you're spending for. Keep the flowers. "
        "Question the taxes. Say the awkward sentence sooner than feels comfortable.</p>"
        + cards([
            ("The three questions to keep", "<p>1. Would I buy it if nobody saw?<br/>2. What will this be worth at review time?<br/>3. If it never comes back, can I still enjoy dinner with them?</p>"),
        ])
        + "<h3>Notes</h3>" + lines(6)
        + f'<div class="callout" style="margin-top:8px;"><strong>Disclaimer:</strong> {VIVIAN_DISCLAIMER}</div>',
        brand, "Closing",
    )
    return "vivian_paid_quiet_money_rules.pdf", wrap_doc(
        "The Quiet Money Rules", VIVIAN_CSS, [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11], brand
    )


# ---------------------------------------------------------------------------
# June Whitaker
# ---------------------------------------------------------------------------

JUNE_CSS = {
    "bg_tint": "#FBF7F2",
    "accent": "#6B4A32",
    "accent_soft": "#F1E6DA",
    "ink": "#2A2420",
    "muted": "#6E645C",
    "border": "#DCCFC2",
    "gold": "#B98B5E",
}
JUNE_SAFETY = (
    "If you notice fear, control, threats or harm, this isn't a small moment and this journal isn't the right tool. "
    "In the US you can reach the National Domestic Violence Hotline at 1-800-799-7233, text START to 88788, or visit "
    "thehotline.org. In a crisis, call or text 988. Outside the US, contact your local emergency number."
)
JUNE_DISCLAIMER = (
    "June Whitaker is an AI-generated character. Her background is fictional. This journal is for personal reflection, "
    "not counseling or therapy, and it can't tell you what a relationship means. Only the people in it can."
)


def build_june_free() -> tuple[str, str]:
    brand = "June Whitaker (@june.noticing) · AI-generated character"
    total = 4
    p1 = cover(
        "FREE · 3-DAY JOURNAL",
        "The 3-Day Notice Journal",
        "Three Small Moments Worth Writing Down",
        "Watch what happens when no one's posing.",
        "<p>For three days, watch for one small moment a day: in a date, a marriage, a friendship, a family dinner. "
        "Write down what happened, not what you think it means. One moment is just one frame. Meaning comes from the "
        "whole contact sheet.</p>",
        cards([
            ("The three moments",
             "<p><strong>Day 1 · The hand-back:</strong> after someone is interrupted, does anyone give the conversation back?</p>"
             "<p><strong>Day 2 · When the plan goes wrong:</strong> late, rained out, booked wrong. How do people treat each other?</p>"
             "<p><strong>Day 3 · The swap:</strong> who notices the cold plate, the empty glass, the tired face?</p>"),
        ]),
        brand,
        "4-page printable",
    )

    def day_block(day: str, title: str, watch: str) -> str:
        return (
            f'<div class="card"><h3>{day} · {title}</h3><p>{watch}</p>'
            "<p><strong>What happened (just the facts):</strong></p>" + lines(3)
            + "<p><strong>How it felt to me:</strong></p>" + lines(2)
            + "<p><strong>And me? Did I do this for someone today?</strong></p>" + lines(1) + "</div>"
        )

    p2 = page(
        "DAYS 1–2", 2, total, "Watch the Small Things",
        day_block("Day 1", "The hand-back", "At dinner, in a meeting, on a call: someone gets cut off mid-sentence. Watch the people around them. Does anyone hand the conversation back?")
        + day_block("Day 2", "When the plan goes wrong", "Something small goes sideways. Watch the first ten seconds. Blame, a joke, a hand on the shoulder, silence?"),
        brand, "Days 1–2",
    )
    p3 = page(
        "DAY 3 &amp; READING YOUR NOTES", 3, total, "One Frame Is Not the Whole Story",
        day_block("Day 3", "The swap", "The quiet things: someone swaps plates because yours went cold, refills a glass, notices you're tired before you say so.")
        + callout("Reading your notes:", "one moment is a moment. Don't draw a conclusion from it, good or bad. If the same thing shows up again and again "
                  "across different days and situations, that's a pattern, and a pattern is worth a conversation."),
        brand, "Day 3",
    )
    p4 = page(
        "WHAT NEXT", 4, total, "From Noticing to Saying Something",
        "<p>Noticing is the first step. The harder part is knowing whether something keeps happening and how to bring it up kindly. "
        "That's what the full journal is for.</p>"
        + cta("The Contact Sheet · $14",
              "Two weeks of notes, a simple way to spot what repeats, a page to prepare one honest conversation, and a check-in two weeks later. "
              "Separate chapters for dating and for long-term partners. Tap the link in my bio.")
        + f'<div class="callout" style="margin-top:12px;"><strong>Please read:</strong> {JUNE_SAFETY}</div>'
        + f'<p style="font-size:8.5pt;color:var(--muted);">{JUNE_DISCLAIMER}</p>',
        brand, "What next",
    )
    return "june_free_3day_notice_journal.pdf", wrap_doc("The 3-Day Notice Journal", JUNE_CSS, [p1, p2, p3, p4], brand)


def build_june_paid() -> tuple[str, str]:
    brand = "June Whitaker (@june.noticing) · The Contact Sheet"
    total = 11
    p1 = cover(
        "DATING &amp; PARTNERED EDITIONS",
        "The Contact Sheet",
        "From Noticing to One Honest Conversation",
        "A contact sheet shows every frame, not just the best one.",
        "<p>Photographers print a whole roll on one page so they can see what really happened, not the one flattering shot. "
        "This journal does the same for the small moments between you and someone else. It won't tell you what your "
        "relationship means. It helps you see clearly enough to talk about it.</p>",
        table(
            ["Step", "What you do", "Pages"],
            [
                ["1 · Record", "Two weeks of small moments, facts first", "2–3"],
                ["2 · Find what repeats", "Separate single frames from patterns", "4"],
                ["3 · Prepare one conversation", "Plan what to say, and how", "5"],
                ["A · Dating", "Early relationships, under about six months", "6–7"],
                ["B · Partnered", "Long-term relationships", "8–9"],
                ["4 · Two weeks later", "Look back at what changed", "10"],
            ],
        ),
        brand,
        "11-page printable",
    )
    p2 = page(
        "STEP 1 · RECORD", 2, total, "Two Weeks of Frames",
        "<p>One line per moment. Facts first, feelings second. Write the good moments too. A contact sheet that only records "
        "problems isn't honest either.</p>"
        + table(["Date", "What happened", "How it felt", "Seen this before?"],
                [r[:3] + ["&#9744; First time &#9744; Again"] for r in blank_rows(4, 14, 20)]),
        brand, "Record",
    )
    p3 = page(
        "STEP 1 · WHAT TO WATCH", 3, total, "Eight Moments Worth Noticing",
        table(
            ["Moment", "What to watch, without judging"],
            [
                ["The hand-back", "When one of you is interrupted, does the other bring the conversation back?"],
                ["When plans go wrong", "Late, cancelled, lost. The first ten seconds of how you treat each other."],
                ["The swap", "Small unasked kindnesses: the cold plate, the coat, the charger."],
                ["The repair", "After a sharp word, does anyone come back to it? How, and how soon?"],
                ["Whose calendar wins", "When plans collide, whose plans usually move?"],
                ["Phones at the table", "Who looks up when the other starts talking?"],
                ["Good news", "When one of you shares good news, how does the other respond?"],
                ["Other people", "How each of you talks to waiters, family and friends when the other is watching."],
            ],
        )
        + callout("June's note:", "I watched couples for thirty-four years and I still can't tell you what a single moment means. Neither can you, from one. Keep writing."),
        brand, "What to watch",
    )
    p4 = page(
        "STEP 2 · FIND WHAT REPEATS", 4, total, "Single Frames and Patterns",
        "<p>At the end of two weeks, go back through page 2 with two colored pens: one for moments that made you feel closer, one for moments that didn't.</p>"
        + table(["Moment that keeps showing up", "How many times", "In how many different situations", "Closer or further?"], blank_rows(4, 6, 24))
        + cards([
            ("A useful rule of thumb", "<p>Once is a frame. Several times across different days and situations is worth talking about. "
             "This isn't a verdict on the person. It's a reason to start a conversation.</p>"),
            ("Pick one", "<p>Choose one pattern to bring up, not five. The one that matters most to you, or the easiest one to start with.</p>"),
        ]),
        brand, "Patterns",
    )
    p5 = page(
        "STEP 3 · PREPARE ONE CONVERSATION", 5, total, "What You Saw, How It Landed, What You'd Like",
        "<p>Write it out first. Saying it will still feel awkward, and that's fine.</p>"
        + cards([
            ("1. What I noticed (facts, no labels)", lines(2)),
            ("2. How it landed for me", lines(2)),
            ("3. What I'd like instead", lines(2)),
            ("4. A question for them", "<p><em>\"How does it look from your side?\"</em></p>" + lines(1)),
        ])
        + callout("Timing:", "not in the middle of the moment, not by text late at night, not when either of you is starving or rushing out the door."),
        brand, "Prepare",
    )
    p6 = page(
        "BRANCH A · DATING", 6, total, "When It's Still Early",
        "<p>In the first months you're learning how someone behaves when the effort of first impressions wears off. It's fair to "
        "notice things early. It's also fair to give people room to be imperfect.</p>"
        + table(
            ["What you might notice", "A fair question to ask yourself"],
            [
                ["Plans are often made last minute, or by you", "Have I said what I'd like, or am I hoping they'll guess?"],
                ["They rarely ask about your day", "Have I seen them curious about me in other ways?"],
                ["Warmth comes mostly late at night", "Does it show up in daytime plans too?"],
                ["They hand the conversation back", "That's a good frame. Write it down too."],
            ],
        )
        + "<h3>My notes for this relationship</h3>" + lines(4),
        brand, "Dating (1/2)",
    )
    p7 = page(
        "BRANCH A · DATING", 7, total, "Openers for Early Conversations",
        cards([
            ("About plans", "<p><em>\"I like spending time with you. I'd love it if we planned a bit further ahead sometimes. How do you usually like to make plans?\"</em></p>"),
            ("About attention", "<p><em>\"I noticed I do most of the asking. I'd like to hear more from you, too.\"</em></p>"),
            ("About pace", "<p><em>\"I'm enjoying this. Where are you at with it?\"</em></p>"),
        ])
        + callout("If the answer is defensive:", "notice it, and notice what happens next time. One defensive answer is a frame. How you want to move forward, "
                  "and how fast, is your decision.")
        + "<h3>What I said, and what happened</h3>" + lines(4),
        brand, "Dating (2/2)",
    )
    p8 = page(
        "BRANCH B · PARTNERED", 8, total, "When You've Been Together a While",
        "<p>In long relationships, small moments harden into routines. Most of them are kind. Some quietly put the weight on one person.</p>"
        + table(
            ["What you might notice", "A fair question to ask yourself"],
            [
                ["One of you remembers every appointment and birthday", "Have we ever talked about who carries what?"],
                ["After an argument, nobody comes back to it", "Do we have a way to repair, or do we just wait it out?"],
                ["Plans usually bend around one person's schedule", "Is that still working for both of us?"],
                ["Good news gets a distracted \"nice\"", "Have I told them how much a real reaction would mean?"],
            ],
        )
        + "<h3>My notes for this relationship</h3>" + lines(4),
        brand, "Partnered (1/2)",
    )
    p9 = page(
        "BRANCH B · PARTNERED", 9, total, "A Twenty-Minute Check-In",
        table(
            ["Minutes", "What to do"],
            [
                ["0–5", "Each say one thing the other did recently that you appreciated. Be specific."],
                ["5–12", "One person shares one pattern from Step 2, using the four lines from page 5. The other only listens and asks questions."],
                ["12–17", "Switch, if the other person has something too."],
                ["17–20", "Agree on one small thing to try for two weeks. Write it below."],
            ],
        )
        + cards([("Opening line", "<p><em>\"Can we take twenty minutes this weekend? Nothing's wrong. I've noticed something I'd like us to talk about.\"</em></p>")])
        + "<h3>What we agreed to try</h3>" + lines(3),
        brand, "Partnered (2/2)",
    )
    p10 = page(
        "STEP 4 · TWO WEEKS LATER", 10, total, "Look at the New Frames",
        "<p>Go back to page 2 and record two more weeks. Then answer honestly.</p>"
        + table(["Question", "My answer"], [
            ["What changed?", '<div style="height:34px;"></div>'],
            ["What didn't change?", '<div style="height:34px;"></div>'],
            ["What did I do differently?", '<div style="height:34px;"></div>'],
            ["What do I want to do next?", '<div style="height:34px;"></div>'],
        ])
        + callout("June's note:", "some things change after one conversation. Some take many. Some don't change at all. What you do with what you see is yours to decide."),
        brand, "Look back",
    )
    p11 = page(
        "WHEN IT ISN'T A SMALL MOMENT", 11, total, "Some Things Need More Than a Journal",
        f"<p>{JUNE_SAFETY}</p>"
        "<p>If you'd like help thinking through a relationship, a licensed counselor or therapist can offer what a journal can't.</p>"
        + "<h3>Frames I want to remember</h3>" + lines(7)
        + f'<div class="callout" style="margin-top:8px;"><strong>About this journal:</strong> {JUNE_DISCLAIMER}</div>',
        brand, "Safety & notes",
    )
    return "june_paid_contact_sheet.pdf", wrap_doc(
        "The Contact Sheet", JUNE_CSS, [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11], brand
    )


# ---------------------------------------------------------------------------
# Henry Wen
# ---------------------------------------------------------------------------

WEN_CSS = {
    "bg_tint": "#F6F5EE",
    "accent": "#2F4A3A",
    "accent_soft": "#E6EDE4",
    "ink": "#1F2420",
    "muted": "#5E655F",
    "border": "#D3D6C8",
    "gold": "#A9824A",
}
WEN_CARE = (
    "This is not therapy and it can't treat anxiety, depression or burnout. If you're struggling, please talk to someone you "
    "trust or a doctor. In the US, call or text 988 any time. Outside the US, contact your local emergency number."
)
WEN_DISCLAIMER = (
    "Henry Wen is an AI-generated character. His background is fictional. The stories are retold in plain English from "
    "the Zhuangzi and the Tao Te Ching; the source chapter is noted beside each one."
)


def pause_card(n: int, when: str, pause: str, source: str = "") -> str:
    src = f'<p style="color:var(--muted);font-size:8.6pt;margin-bottom:0;">{source}</p>' if source else ""
    return (
        f'<div class="card" style="margin-bottom:8px;"><h3 style="font-size:10.5pt;">{n:02d} · {when}</h3>'
        f"<p style=\"margin-bottom:4px;\">{pause}</p>{src}</div>"
    )


WEN_PAUSES = [
    ("Before you answer the email that made your jaw tight", "Hold a warm cup for three breaths. Then decide: tonight, or tomorrow morning?"),
    ("Before you open your inbox", "Write the one thing that matters today on a scrap of paper. Then open it."),
    ("Before a meeting", "Find the farthest thing you can see from a window. Look at it for thirty seconds."),
    ("When someone asks, \"Can you take this on?\"", "Say, \"Let me see what I'd set down first.\" Find the gap before you say yes.", "Cook Ding · 庖丁解牛 · Zhuangzi, ch. 3 养生主"),
    ("Lunch at your desk", "Eat the first five bites with no screen in front of you."),
    ("Around two in the afternoon", "Close something for twenty minutes: a tab, a door, a laptop lid. I close my whole shop."),
    ("When you're performing busy", "Put your heels down. Cut one exclamation mark from the next message you send.", "企者不立 · Tao Te Ching, ch. 24"),
    ("When everything feels urgent", "List what's in the cup. Pour one thing out into next week.", "持而盈之，不如其已 · Tao Te Ching, ch. 9"),
    ("When you want to fix yourself", "Write down one thing about yourself you'll leave unfixed today.", "Hundun · 浑沌 · Zhuangzi, ch. 7 应帝王"),
    ("When the same news sounds worse at night", "Write it down. Read it again in the morning. Same acorns, different order.", "朝三暮四 · Zhuangzi, ch. 2 齐物论"),
    ("When you can't decide", "Pour a cup of tea. Decide before it cools. Agonizing is the option that costs you both."),
    ("Before you lend or give", "Ask which reluctance you can live with. Pour only what you can let go of."),
    ("On the way home", "Pick a street corner. When you pass it, say \"tomorrow\" to the last work thought."),
    ("At dinner", "Put your phone in a drawer for the length of one meal."),
    ("Sunday evening", "Write Monday's first task on paper and close the notebook. Monday can arrive without you."),
    ("At three in the morning", "Write the thought, write \"noted\" under it, turn the page. Don't solve anything in the dark."),
    ("When you're loving someone your way", "Ask them once how they'd like it.", "The seabird · 鲁侯养鸟 · Zhuangzi, ch. 18 至乐"),
    ("In a heated thread", "Wait one full breath before you reply. Then wait one more.", "The wooden rooster · 呆若木鸡 · Zhuangzi, ch. 19 达生"),
    ("When nothing feels like enough", "Name one thing today that already is.", "知足不辱 · Tao Te Ching, ch. 44"),
    ("In a disagreement", "Find one place you can give way without losing what matters.", "上善若水 · Tao Te Ching, ch. 8"),
]


def build_wen_free() -> tuple[str, str]:
    brand = "Henry Wen (@wen.teashop) · AI-generated character"
    total = 5
    p1 = cover(
        "FREE · 20 PAUSE CARDS",
        "The Tea Drawer",
        "20 Pause Cards, Picked by Situation · No Streaks",
        "Keep them in a drawer, my friend. Not on a schedule.",
        "<p>In my shop there's a drawer of loose tea. Nobody drinks it in order. You open it when you need it. These cards work "
        "the same way. Find the situation you're in, take one small pause, and close the drawer. Skip any card. Repeat any card. "
        "There are no days to complete and nothing to keep up.</p>",
        table(
            ["If you're…", "Cards"],
            [
                ["At work, before something", "01 – 04"],
                ["In the middle of the day", "05 – 08"],
                ["Being hard on yourself", "09 – 12"],
                ["Heading home, or at home", "13 – 16"],
                ["With other people", "17 – 20"],
            ],
        ),
        brand,
        "5-page printable · cut along the cards",
    )
    card_html = [pause_card(i + 1, *c) for i, c in enumerate(WEN_PAUSES)]
    p2 = page("CARDS 01–07", 2, total, "At Work and Midday", '<div class="grid-2">' + "".join(card_html[0:7]) + "</div>", brand, "Cards 01–07")
    p3 = page("CARDS 08–14", 3, total, "When It's Too Much", '<div class="grid-2">' + "".join(card_html[7:14]) + "</div>", brand, "Cards 08–14")
    p4 = page("CARDS 15–20", 4, total, "Evenings and Other People", '<div class="grid-2">' + "".join(card_html[14:20]) + "</div>", brand, "Cards 15–20")
    p5 = page(
        "WHEN YOU WANT MORE", 5, total, "Same Trouble, Next Time",
        "<p>The cards are for the moment. When the same trouble keeps coming back, the boss who adds work, the Sunday dread, the friend "
        "who wants to borrow, it helps to have somewhere to look it up.</p>"
        + cta("Doing Less, Case by Case · $14",
              "Sixteen everyday troubles. For each one: a story from Zhuangzi or Lao Tzu, one small thing to do today, and one thing you're "
              "allowed to skip today. No schedule, no tracking. Tap the link in my bio.")
        + f'<div class="callout" style="margin-top:12px;"><strong>Please read:</strong> {WEN_CARE}</div>'
        + f'<p style="font-size:8.5pt;color:var(--muted);">{WEN_DISCLAIMER}</p>',
        brand, "More",
    )
    return "wen_free_tea_drawer.pdf", wrap_doc("The Tea Drawer", WEN_CSS, [p1, p2, p3, p4, p5], brand)


# (title, source label, story, one small step, one thing to skip, a line to keep)
WEN_CASES = [
    # Work
    ("The boss adds a project", "Cook Ding · 庖丁解牛 · Zhuangzi, ch. 3 养生主",
     "Cook Ding carved oxen for Lord Wenhui. A good cook changes his knife once a year because he cuts; an ordinary cook changes it every month because he hacks. "
     "Ding's knife had lasted nineteen years and still looked fresh from the whetstone. He never forced it through bone. He followed the spaces between the joints.",
     "Before you say yes, write down which existing task gets set down, slowed or handed over. Bring that list to the conversation.",
     "Skip answering on the spot. \"Let me look at what I'd set down\" is a complete sentence.",
     "Find the space between the joints."),
    ("The inbox at midnight", "The shrine oak · 栎社树 · Zhuangzi, ch. 4 人间世",
     "A master carpenter passed a giant oak by a village shrine and didn't look twice: its wood was useless, boats would sink and coffins would rot. "
     "That night the oak appeared in his dream. Useful trees, it said, get their branches broken and their fruit stripped. "
     "Being of no use to the carpenter is how it grew so old.",
     "Tonight, let one email wait until morning. Pick the one that would be fine either way.",
     "Skip being instantly useful to everyone after dark.",
     "Not everything needs your best wood tonight."),
    ("Everything feels urgent", "持而盈之，不如其已 · Tao Te Ching, ch. 9",
     "Lao Tzu says: fill a cup to the brim and it's better to have stopped in time. A blade honed too sharp won't keep its edge. "
     "A hall full of gold and jade can't be guarded. When the work is done, step back.",
     "List everything you're holding this week. Move one item to next week, and tell whoever needs to know.",
     "Skip the item that's urgent only because someone said it loudly.",
     "Stop before the cup spills."),
    ("Performing busy", "企者不立 · Tao Te Ching, ch. 24",
     "Lao Tzu says: whoever stands on tiptoe doesn't stand firm, and whoever takes huge strides doesn't walk far. Whoever shows off isn't seen clearly.",
     "In your next message, remove one exclamation mark and one apology.",
     "Skip the late-night \"just checking in\" message you're sending so people know you're working.",
     "Heels down."),
    # Rest
    ("You can't stop working", "知足不辱，知止不殆 · Tao Te Ching, ch. 44",
     "Lao Tzu asks: your name or your life, which is dearer? Your life or your goods, which is worth more? Know what is enough and you won't be disgraced. "
     "Know when to stop and you won't be in danger. In my forties I opened a second shop and didn't take a day off for two years. "
     "I fell asleep behind the counter in the middle of the afternoon. I closed the second shop that spring.",
     "Decide today what \"done for the day\" means, and write it on paper before lunch.",
     "Skip the one extra task after you've reached it.",
     "Know when to stop."),
    ("Sunday dread", "A story from the shop",
     "Every Sunday evening someone sits at my counter carrying all of Monday already. They hold the cup and don't drink it. "
     "I tell them Monday doesn't need their help to arrive. It has managed every week so far.",
     "Write Monday's first task on paper. Just the first one. Close the notebook.",
     "Skip checking your work inbox after dinner on Sunday.",
     "Monday can arrive without you."),
    ("Thoughts at three in the morning", "朝三暮四 · Zhuangzi, ch. 2 齐物论",
     "A monkey keeper told his monkeys they'd get three acorns in the morning and four in the evening. They were furious. "
     "So he offered four in the morning and three in the evening, and they were delighted. Nothing about the acorns had changed.",
     "Write the worry down, write \"noted\" underneath, and read it again after breakfast. Same acorns, different order.",
     "Skip solving anything important in the dark.",
     "Same acorns."),
    ("Time off you can't enjoy", "The joy of fish · 濠梁之辩 · Zhuangzi, ch. 17 秋水",
     "Zhuangzi and his friend Huizi stood on a bridge over the Hao river. \"See how the minnows swim, free and easy. That's the joy of fish.\" "
     "Huizi said, \"You're not a fish. How do you know what fish enjoy?\" Zhuangzi said, \"You're not me. How do you know I don't know?\" "
     "In the end, he said, he knew it standing right there above the river.",
     "Spend ten minutes of your time off doing something without photographing it, rating it or planning the next thing.",
     "Skip the question \"am I relaxing properly?\"",
     "Know it from the bridge."),
    # People
    ("Loving someone your way", "The seabird · 鲁侯养鸟 · Zhuangzi, ch. 18 至乐",
     "A seabird landed outside the capital of Lu. The Marquis welcomed it into the ancestral temple, poured it wine, had the finest court music played, "
     "and laid out a grand feast. The bird was dazed and frightened. It wouldn't eat a bite or drink a cup, and in three days it died. "
     "He had cared for it the way he would care for himself, not the way a bird needs to be cared for.",
     "Ask someone you love, once: \"When you're having a hard week, what actually helps?\" Then listen.",
     "Skip the grand gesture this week if it's really for you.",
     "Feed the bird like a bird."),
    ("A friend asks to borrow money", "A story from my family",
     "In 1981 my father lent half his savings to a cousin. He never asked for it back, and he never quite forgave him either. "
     "There are two kinds of reluctance: lending when you don't want to, and pretending afterward that you don't mind. The second one lasts longer.",
     "Before you answer, decide which reluctance you can live with. Then pour only what you can let go of.",
     "Skip deciding in the same conversation. \"Let me think tonight\" is allowed.",
     "Pour only what you can let go of."),
    ("An invitation you can't afford", "A story from the shop",
     "Every week someone sits at my counter, stuck between two choices, letting their tea go cold. Go or don't go. Both can be right. "
     "Agonizing is the only option that costs you both the money and the peace.",
     "Pour a cup. Decide before it cools. Then send your answer while you still mean it.",
     "Skip rehearsing the reply for three more days.",
     "Decide before it cools."),
    ("An argument you want to win", "上善若水 · Tao Te Ching, ch. 8",
     "Lao Tzu says the highest good is like water. Water benefits all things and doesn't compete. It settles in the low places people avoid, "
     "and that is why it comes close to the Way.",
     "Find one point you can give way on without losing what matters to you. Give it out loud.",
     "Skip the last word.",
     "Water doesn't compete."),
    # Mind
    ("Trying to fix yourself", "Hundun · 浑沌 · Zhuangzi, ch. 7 应帝王",
     "Hundun, emperor of the center, had no openings in his face: no eyes, no ears, no mouth. His two friends, the emperors of the north and south seas, "
     "wanted to repay his kindness. \"Everyone has seven openings to see, hear, eat and breathe,\" they said. \"Let's give him some.\" "
     "They bored one hole a day. On the seventh day, Hundun died.",
     "Write down one thing about yourself you'll leave unfixed today.",
     "Skip the new self-improvement plan this week.",
     "Leave one thing unfixed."),
    ("When your job is your whole name", "The butterfly dream · 庄周梦蝶 · Zhuangzi, ch. 2 齐物论",
     "Zhuangzi dreamed he was a butterfly, fluttering happily about, with no idea he was Zhuangzi. Suddenly he woke up, and there he was, Zhuangzi. "
     "He didn't know whether he'd been Zhuangzi dreaming of a butterfly, or was now a butterfly dreaming of being Zhuangzi.",
     "Write three things you are that have nothing to do with your job title.",
     "Skip introducing yourself with your job the next time you meet someone.",
     "You are more than one dream."),
    ("Waiting for a reply", "The wooden rooster · 呆若木鸡 · Zhuangzi, ch. 19 达生",
     "Ji Xingzi trained a fighting rooster for the king. After ten days: not ready, still proud and full of itself. Ten more: still jumps at every sound and shadow. "
     "Ten more: still glares and puffs up. After forty days: other roosters crow and it doesn't stir. It looks like a rooster carved from wood. "
     "The others take one look and walk away.",
     "Put the phone face down for one hour. Do one ordinary thing with your hands.",
     "Skip refreshing to see if they've read it.",
     "Be the wooden rooster."),
    ("Feeling useless", "无用之用 · Zhuangzi, ch. 4 人间世",
     "At the end of the same chapter as the shrine oak, Zhuangzi writes: everyone knows the use of being useful, but no one knows the use of being useless.",
     "Do one thing today purely because you like it, with no result to show for it.",
     "Skip justifying your rest to anyone, including yourself.",
     "The use of the useless."),
]


def case_block(n: int, case: tuple[str, str, str, str, str, str]) -> str:
    title, source, story, step, skip, keep = case
    return (
        f'<div class="card"><h3>{n:02d} · {esc(title)}</h3>'
        f'<p style="color:var(--muted);font-size:8.8pt;margin-bottom:4px;">{esc(source)}</p>'
        f"<p>{esc(story)}</p>"
        f"<p><strong>One small step today:</strong> {esc(step)}</p>"
        f"<p><strong>One thing you can skip today:</strong> {esc(skip)}</p>"
        f'<p style="margin-bottom:0;"><strong>A line to keep:</strong> <em>{esc(keep)}</em></p></div>'
    )


def build_wen_paid() -> tuple[str, str]:
    brand = "Henry Wen (@wen.teashop) · Doing Less, Case by Case"
    groups = [("WORK", 0), ("WORK", 2), ("REST", 4), ("REST", 6), ("PEOPLE", 8), ("PEOPLE", 10), ("MIND", 12), ("MIND", 14)]
    total = 2 + len(groups) + 1
    p1 = cover(
        "LOOK IT UP WHEN YOU NEED IT",
        "Doing Less, Case by Case",
        "One Story, One Small Step, One Thing to Skip",
        "This is not a program, my friend.",
        "<p>There's no day one, no streak and no progress bar. Open it when a particular trouble shows up, find that page, and read one story. "
        "Each page gives you one small thing to do today and one thing you're allowed to skip today. Then close the book and go back to your life.</p>",
        callout("Why stories?", "I'm not a teacher, a monk or a doctor. I've run a tea shop for forty-five years and read the same two old books over and over. "
                "Their stories have outlasted every productivity method I've seen. I retell them here in plain English, with the chapter noted so you can read the original."),
        brand,
        f"{total}-page printable",
    )
    contents_rows = []
    for i, c in enumerate(WEN_CASES):
        area = ["Work", "Rest", "People", "Mind"][i // 4]
        contents_rows.append([f"{i + 1:02d}", area, esc(c[0]), str(3 + i // 2)])
    p2 = page(
        "CONTENTS", 2, total, "Find Your Trouble",
        table(["#", "Area", "When…", "Page"], contents_rows)
        + callout("How to use:", "read only the page you need. If none fits, read the one that makes you smile. Skip the rest without guilt."),
        brand, "Contents",
    )
    pages = [p1, p2]
    for gi, (area, start) in enumerate(groups):
        pages.append(page(
            f"{area} · CASES {start + 1:02d}–{start + 2:02d}", 3 + gi, total, f"{esc(WEN_CASES[start][0])} · {esc(WEN_CASES[start + 1][0])}",
            case_block(start + 1, WEN_CASES[start]) + case_block(start + 2, WEN_CASES[start + 1]),
            brand, f"{area.title()}",
        ))
    pages.append(page(
        "CLOSING", total, total, "Drink It Before It Cools",
        "<p>You don't have to do all of this. You don't have to do any of it every day. If one story helped once, that's enough for a book.</p>"
        + "<h3>The troubles that keep coming back for me</h3>" + lines(4)
        + "<h3>The lines I want to keep</h3>" + lines(4)
        + f'<div class="callout" style="margin-top:8px;"><strong>Please read:</strong> {WEN_CARE}</div>'
        + f'<p style="font-size:8.5pt;color:var(--muted);">{WEN_DISCLAIMER}</p>',
        brand, "Closing",
    ))
    return "wen_paid_doing_less_case_by_case.pdf", wrap_doc("Doing Less, Case by Case", WEN_CSS, pages, brand)


BUILDERS = [
    ("free", build_vivian_free),
    ("paid", build_vivian_paid),
    ("free", build_june_free),
    ("paid", build_june_paid),
    ("free", build_wen_free),
    ("paid", build_wen_paid),
]
