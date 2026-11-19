// Songifted /create 桌面版逐状态采集（长视频用）。用法：
//   ego-browser nodejs < workflows/08_site_channels/capture_songifted_create.mjs
// 视口固定 1280×720 @2x，每张就是 2560×1440 的真实屏幕画面（sticky 导航和 Back/Next 栏都在原位）。
// 每次操作截一张，滚动过程按 STEP_PX 分段截；光标目标（视口 CSS 坐标）写进 manifest.json。
// 只走到第 5 步，不点「Start … song」，不碰 Turnstile。第 5 步的邮箱框坐标也记下，合成时打码。
const OUT = "/Volumes/WorkData/Workspace/projects/colab-ultra-workstation/workflows/08_site_channels/samples/songifted_longform/create";
const fs = await import("node:fs/promises");
await fs.rm(OUT, { recursive: true, force: true });
await fs.mkdir(OUT, { recursive: true });

const SPACE_ID = 13;
const entry = (await listTaskSpaces()).find((s) => s.id === SPACE_ID);
const task = entry ? await taskSpace(SPACE_ID) : await taskSpace("songifted longform capture");
const page = (await task.pages())[0] ?? (await task.adopt((await task.tabs())[0].page));

// 和首页那首虚构示例歌「Happy Birthday, Sarah」的 brief 对齐（"thank you for the laughs and late-night calls"）
const NAME = "Sarah";
const MESSAGE = "Thank you for the laughs and the late-night calls. You always pick up, even at 2am.";
const FROM = "The whole gang";
const VW = 1280, VH = 720, STEP_PX = 140;

const viewport = () => page.cdp("Emulation.setDeviceMetricsOverride",
  { width: VW, height: VH, deviceScaleFactor: 2, mobile: false, screenWidth: VW, screenHeight: VH });

await page.goto("https://songifted.com/create", { timeout: 60000 });
await page.waitForSelector('input[name="recipientName"]');
await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
await page.reload({ timeout: 60000 });
await viewport();
await page.waitForSelector('input[name="recipientName"]');
// 清了 localStorage 会重新弹「Your privacy choices」，点 Reject all（不开任何跟踪）关掉
await page.waitForTimeout(1500);
console.log("privacy banner:", await page.evaluate(() => {
  const b = [...document.querySelectorAll("button")].find((b) => b.innerText.trim() === "Reject all");
  if (!b) return "none"; b.click(); return "rejected";
}));
await page.evaluate(() => { document.documentElement.style.scrollBehavior = "auto"; window.scrollTo(0, 0); });
await page.waitForTimeout(1000);

const shots = [];
let n = 0;
const norm = (s) => s.replace(/\s+/g, " ").trim();

// 元素框（视口坐标）。q: "css:<sel>" | "text:<子串>" | 按钮文字（endsWith；以 "=" 开头则全等）
async function boxes(spec) {
  return page.evaluate((spec) => {
    const norm = (s) => s.replace(/\s+/g, " ").trim();
    const out = {};
    for (const [key, q] of Object.entries(spec)) {
      let el = null;
      if (q.startsWith("css:")) el = document.querySelector(q.slice(4));
      else if (q.startsWith("text:")) el = [...document.querySelectorAll("p,span,div,label,strong,b,em,a")]
        .find((e) => e.children.length === 0 && norm(e.textContent).includes(q.slice(5)));
      else if (q.startsWith("=")) el = [...document.querySelectorAll("button")].find((b) => norm(b.innerText) === q.slice(1));
      else el = [...document.querySelectorAll("button")].find((b) => norm(b.innerText).endsWith(q));
      if (!el) { out[key] = null; continue; }
      const r = el.getBoundingClientRect();
      out[key] = [r.x, r.y, r.width, r.height];
    }
    return out;
  }, spec);
}

async function shot(label, spec = {}, wait = 350) {
  await page.waitForTimeout(wait);
  const b = await boxes({ email: "text:@", ...spec });  // 每帧都查账号邮箱，页面上有就记坐标（合成时打码）
  if (!b.email) delete b.email;
  const scrollY = await page.evaluate(() => scrollY);
  const file = `${String(n++).padStart(3, "0")}_${label}.png`;
  const r = await page.cdp("Page.captureScreenshot", { format: "png", fromSurface: true }, { timeout: 30000 });
  await fs.writeFile(`${OUT}/${file}`, Buffer.from(r.data, "base64"));
  shots.push({ file, label, scrollY, targets: b });
  console.log(file, scrollY, JSON.stringify(b));
}

// 把元素滚到视口里（目标中心放在视口 45% 高度处），过程按 STEP_PX 分段截图
async function scrollToShow(q, label) {
  const want = await page.evaluate(({ q, VH }) => {
    const norm = (s) => s.replace(/\s+/g, " ").trim();
    let el = q.startsWith("css:") ? document.querySelector(q.slice(4))
      : q.startsWith("=") ? [...document.querySelectorAll("button")].find((b) => norm(b.innerText) === q.slice(1))
      : [...document.querySelectorAll("button")].find((b) => norm(b.innerText).endsWith(q));
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const max = document.documentElement.scrollHeight - innerHeight;
    // 已经在视口安全区内（顶部导航 70px、底部 sticky 栏 110px 之外）就不滚
    if (r.top > 90 && r.bottom < VH - 120) return scrollY;
    return Math.max(0, Math.min(max, Math.round(scrollY + r.top + r.height / 2 - VH * 0.45)));
  }, { q, VH });
  if (want === null) throw new Error("missing " + q);
  let cur = await page.evaluate(() => scrollY);
  if (Math.abs(want - cur) < 4) return;
  const steps = Math.max(1, Math.ceil(Math.abs(want - cur) / STEP_PX));
  for (let i = 1; i <= steps; i++) {
    const y = Math.round(cur + (want - cur) * i / steps);
    await page.evaluate((y) => window.scrollTo(0, y), y);
    await shot(`${label}_scroll${i}`, {}, 120);
  }
}

const click = (q) => page.evaluate((q) => {
  const norm = (s) => s.replace(/\s+/g, " ").trim();
  const b = q.startsWith("=") ? [...document.querySelectorAll("button")].find((b) => norm(b.innerText) === q.slice(1))
    : [...document.querySelectorAll("button")].find((b) => norm(b.innerText).endsWith(q));
  if (!b) throw new Error("missing button " + q);
  b.click();
}, q);

async function pick(q, label, extra = {}) {
  await scrollToShow(q, label);
  await shot(`${label}_hover`, { target: q, ...extra }, 150);   // 光标移到按钮上、还没点
  await click(q);
  await shot(label, { target: q, ...extra });
}

async function nextStep(label) {
  await shot(`${label}_next_hover`, { target: "=Next" }, 150);
  await click("=Next");
  await page.evaluate(() => window.scrollTo(0, 0));
  await shot(`${label}_next`, {}, 1100);    // 等新一步淡入结束
}

async function typeInto(sel, text, label, every, extra = {}) {
  await scrollToShow("css:" + sel, label);
  await page.focus(sel);
  for (let i = 0; i < text.length; i++) {
    await page.keyboard.insertText(text[i]);
    if ((i + 1) % every === 0 || i === text.length - 1) await shot(`${label}_${i + 1}`, { field: "css:" + sel, ...extra }, 60);
  }
}

// ---- Step 1 Who ----
await shot("s1_empty", { field: 'css:input[name="recipientName"]' }, 2500);  // 等表单淡入、头像加载完
await typeInto('input[name="recipientName"]', NAME, "s1_name", 1);
await pick("Friend", "s1_friend");
await pick("20s–30s", "s1_age");
await nextStep("s1");
// ---- Step 2 Occasion（点 Birthday 会自动跳到第 3 步）----
await pick("Birthday", "s2_birthday");
await shot("s3_enter", {}, 1100);
// ---- Step 3 Sound ----
for (const t of ["English", "Upbeat pop", "Playful", "Female voice", "=⚡ Upbeat"]) {
  await pick(t, `s3_${t.replace(/\W+/g, "_")}`);
}
await nextStep("s3");
// ---- Step 4 Details ----
for (const t of ["=Late-night talks", "=Inside jokes", "=Bad karaoke", "=That laugh"]) {
  await pick(t, `s4_${t.replace(/\W+/g, "_")}`);
}
await typeInto('textarea[name="message"]', MESSAGE, "s4_msg", 4);
await nextStep("s4");
// ---- Step 5 Delivery（只截不提交）----
const s5 = { email: "text:@", offer: "text:Your free 45-second preview", start: `Start ${NAME}'s song` };
await shot("s5_enter", s5);
const nameSel = await page.evaluate(() => {
  const i = [...document.querySelectorAll("input")].find((e) => e.type === "text" && e.name !== "recipientName" && e.offsetParent);
  return i && i.name ? `input[name="${i.name}"]` : null;
});
if (nameSel) await typeInto(nameSel, FROM, "s5_from", 2, s5);
await page.waitForTimeout(5000);   // 等 Turnstile 从 Verifying 变成通过状态（不点它）
await scrollToShow(`Start ${NAME}'s song`, "s5_final");
await shot("s5_final", s5);
await shot("s5_start_hover", { target: `Start ${NAME}'s song`, ...s5 }, 150);

await fs.writeFile(`${OUT}/manifest.json`, JSON.stringify({ name: NAME, message: MESSAGE, from: FROM, viewport: [VW, VH], scale: 2, shots }, null, 1));
console.log({ taskSpaceId: task.spaceId, shots: shots.length });
