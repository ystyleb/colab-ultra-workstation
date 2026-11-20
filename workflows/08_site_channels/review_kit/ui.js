// 审核页评论层（review_kit/server.py 提供 API）。页面约定：
//   <body data-project="songifted_nora">
//   任何可评论的块：data-target="kf:n04_leak_a" data-label="#04 首帧"
//   图片块再加：data-img="原图 URL" data-ver="版本号"（块内第一个 <img> 点开是大图标注）
//   视频块：data-target="video:…" 内含 <video>，评论自动带上当前时间
(() => {
  const P = document.body.dataset.project;
  const API = `/api/${P}`;
  let doc = { rounds: [], comments: [] };
  let online = false;
  const openThreads = new Set();
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const mmss = (t) => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`;
  const STATUS = { open: ["待处理", "st-open"], done: ["已处理", "st-done"], wontfix: ["不改", "st-wont"], question: ["我有疑问", "st-q"] };
  const targets = () => $$("[data-target]");
  const byTarget = (t) => doc.comments.filter((c) => c.target === t);
  const elOf = (t) => targets().find((e) => e.dataset.target === t);

  async function api(method, path, body) {
    const r = await fetch(API + path, { method, headers: { "Content-Type": "application/json" }, body: body && JSON.stringify(body) });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.status);
    return r.json();
  }
  async function refresh() {
    try { doc = await api("GET", "/comments"); online = true; } catch { online = false; }
    renderAll();
  }
  function toast(msg, ms = 2600) {
    const t = $("#rv-toast"); t.textContent = msg; t.classList.add("on");
    clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("on"), ms);
  }

  // ---------- 单条评论 ----------
  function commentHTML(c, i, el) {
    const [stTxt, stCls] = STATUS[c.status] || STATUS.open;
    const stale = el?.dataset.ver && c.img_ver && c.img_ver !== el.dataset.ver;
    const where = (c.pin || c.box ? `<span class="pinno">${i + 1}</span>` : "") +
      (c.t != null ? `<a href="#" class="tlink" data-t="${c.t}">▶ ${mmss(c.t)}</a>` : "");
    return `<div class="cm ${c.status}" data-id="${c.id}">
      <div class="cm-h">${where}<span class="chip ${stCls}">${stTxt}</span>${stale ? '<span class="chip st-new">图已更新</span>' : ""}
        <span class="cm-meta">R${c.round} · ${esc(c.created.slice(5, 16).replace("T", " "))}</span>
        ${c.status === "open" ? '<button class="lnk" data-act="edit">改</button><button class="lnk" data-act="del">删</button>' : ""}
        ${c.status !== "open" ? '<button class="lnk" data-act="reopen">重新打开</button>' : ""}</div>
      <div class="cm-t">${esc(c.text)}</div>
      ${c.reply ? `<div class="cm-r">↳ ${esc(c.reply)}</div>` : ""}</div>`;
  }
  function pinned(t) { return byTarget(t).filter((c) => c.pin || c.box); }
  // 图上的标注：box = 圈（椭圆外接框，0–1 相对坐标），pin = 单点。编号放在圈的左上 45° 处
  const clamp = (v) => Math.min(1, Math.max(0, v));
  function badgeAt(m) {
    if (!m.box) return m.pin;
    const [x0, y0, x1, y1] = m.box, rx = (x1 - x0) / 2, ry = (y1 - y0) / 2;
    return [x0 + rx - rx * 0.707, y0 + ry - ry * 0.707];
  }
  function drawMarks(wrap, list, tmp) {
    $$(".pin, .rv-svg", wrap).forEach((p) => p.remove());
    const ell = (b, cls) => `<ellipse class="${cls}" cx="${(b[0] + b[2]) * 50}" cy="${(b[1] + b[3]) * 50}" rx="${(b[2] - b[0]) * 50}" ry="${(b[3] - b[1]) * 50}"/>`;
    const svg = list.filter((c) => c.box).map((c) => ell(c.box, c.status)).join("") + (tmp?.box ? ell(tmp.box, "tmp") : "");
    wrap.insertAdjacentHTML("beforeend", `<svg class="rv-svg" viewBox="0 0 100 100" preserveAspectRatio="none">${svg}</svg>`);
    list.forEach((c, i) => { const [x, y] = badgeAt(c);
      wrap.insertAdjacentHTML("beforeend", `<span class="pin ${c.status}" title="${esc(c.text)}" style="left:${x * 100}%;top:${y * 100}%">${i + 1}</span>`); });
    if (tmp && !tmp.box) wrap.insertAdjacentHTML("beforeend", `<span class="pin tmp" style="left:${tmp.pin[0] * 100}%;top:${tmp.pin[1] * 100}%">+</span>`);
  }

  // ---------- 评论区（块内展开，或灯箱侧栏）----------
  function threadHTML(el, inBox) {
    const t = el.dataset.target, list = byTarget(t), pins = pinned(t);
    const isImg = !!el.dataset.img, isVid = !!$("video", el);
    return `<div class="th-list">${list.map((c) => commentHTML(c, pins.indexOf(c), el)).join("") || '<div class="dim small">还没有评论</div>'}</div>
      <div class="composer">
        <div class="ctx small dim">${isImg ? (inBox ? "在图上拖动画圈（单击 = 标一个点），再写意见；不标也可以" : '<button class="lnk" data-act="zoom">打开大图画圈标注</button>') : ""}
          ${isVid ? '<span class="vt"></span>' : ""}<span class="pinctx"></span></div>
        <textarea rows="3" placeholder="写下意见… （⌘/Ctrl + Enter 保存）"></textarea>
        <div class="row"><button class="btn" data-act="save">保存评论</button><span class="dim small">${esc(el.dataset.label || t)}</span></div>
      </div>`;
  }
  function bindThread(box, el, getPin) {
    const ta = $("textarea", box);
    const vid = $("video", el);
    const vt = $(".vt", box);
    const getMark = getPin || (() => ({}));
    if (vid && vt) { const upd = () => (vt.textContent = `评论会标在 ${mmss(vid.currentTime)}`); upd(); vid.addEventListener("timeupdate", upd); }
    ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) save(); });
    async function save() {
      const text = ta.value.trim();
      if (!text) return ta.focus();
      if (!online) return toast("没连上本地服务，评论没保存。请用 review_kit/server.py 打开本页");
      const body = { target: el.dataset.target, label: el.dataset.label || "", text, img_ver: el.dataset.ver || null,
                     pin: null, box: null, ...getMark(), t: vid ? +vid.currentTime.toFixed(1) : null };
      try { const c = await api("POST", "/comments", body); doc.comments.push(c); ta.value = ""; toast("已保存"); renderAll(); }
      catch (e) { toast("保存失败：" + e.message); }
    }
    box.addEventListener("click", async (e) => {
      const b = e.target.closest("[data-act],.tlink"); if (!b) return;
      e.preventDefault();
      if (b.classList.contains("tlink")) { if (vid) { vid.currentTime = +b.dataset.t; vid.play(); } return; }
      const act = b.dataset.act, id = b.closest(".cm")?.dataset.id, c = doc.comments.find((x) => x.id === id);
      if (act === "save") return save();
      if (act === "zoom") return openBox(el);
      if (act === "clearmark") { tmpMark = null; return drawBox(); }
      if (act === "del" && confirm("删除这条评论？")) { await api("PATCH", `/comments/${id}`, { delete: true }); doc.comments = doc.comments.filter((x) => x.id !== id); }
      if (act === "edit") { const v = prompt("修改评论", c.text); if (v && v.trim()) Object.assign(c, await api("PATCH", `/comments/${id}`, { text: v.trim() })); }
      if (act === "reopen") Object.assign(c, await api("PATCH", `/comments/${id}`, { status: "open" }));
      renderAll();
    });
  }

  // ---------- 每个块：按钮、缩略图上的标注点、展开的评论区 ----------
  function renderTarget(el) {
    const t = el.dataset.target, list = byTarget(t), nOpen = list.filter((c) => c.status === "open").length;
    let bar = $(":scope > .rv-bar", el);
    if (!bar) {
      bar = document.createElement("div"); bar.className = "rv-bar";
      bar.innerHTML = '<button class="cbtn"></button>';
      $(".cbtn", bar).onclick = () => { openThreads.has(t) ? openThreads.delete(t) : openThreads.add(t); renderTarget(el); };
      el.appendChild(bar);
    }
    $(".cbtn", bar).innerHTML = list.length ? `💬 ${list.length} 条${nOpen ? ` · <b>${nOpen} 待处理</b>` : ""}` : "💬 评论";
    $(".cbtn", bar).classList.toggle("has", nOpen > 0);
    el.classList.toggle("rv-has", nOpen > 0);
    const img = el.dataset.img && $("img", el);
    if (img) {
      let wrap = img.parentElement.classList.contains("rv-pinwrap") ? img.parentElement : null;
      if (!wrap) { wrap = document.createElement("span"); wrap.className = "rv-pinwrap"; img.replaceWith(wrap); wrap.appendChild(img);
        img.style.cursor = "zoom-in"; img.closest("a")?.addEventListener("click", (e) => { e.preventDefault(); openBox(el); }); }
      drawMarks(wrap, pinned(t), null);
    }
    let th = $(":scope > .rv-thread", el);
    if (openThreads.has(t)) {
      const draft = th ? $("textarea", th).value : "";
      if (!th) { th = document.createElement("div"); th.className = "rv-thread"; el.appendChild(th); }
      th.innerHTML = threadHTML(el, false);
      $("textarea", th).value = draft;
      bindThread(th, el, null);
    } else th?.remove();
  }

  // ---------- 灯箱：大图 + 拖动画圈 / 单击标点 ----------
  let boxEl = null, tmpMark = null;
  function openBox(el) {
    boxEl = el; tmpMark = null;
    const lb = $("#rv-lb");
    lb.innerHTML = `<div class="lb-img"><span class="rv-pinwrap big"><img src="${el.dataset.img}" draggable="false"></span></div>
      <div class="lb-side"><div class="lb-h"><b>${esc(el.dataset.label || el.dataset.target)}</b><button class="lnk" data-x>关闭 Esc</button></div><div class="lb-th"></div></div>`;
    lb.classList.add("on");
    $("[data-x]", lb).onclick = closeBox;
    const wrap = $(".rv-pinwrap", lb);
    const norm = (e) => { const r = $("img", wrap).getBoundingClientRect();
      return [clamp((e.clientX - r.left) / r.width), clamp((e.clientY - r.top) / r.height)]; };
    const r4 = (v) => +v.toFixed(4);
    let start = null;
    wrap.addEventListener("pointerdown", (e) => { e.preventDefault(); wrap.setPointerCapture(e.pointerId);
      start = norm(e); tmpMark = { pin: start.map(r4), box: null }; drawMarks(wrap, pinned(boxEl.dataset.target), tmpMark); });
    wrap.addEventListener("pointermove", (e) => {
      if (!start) return;
      const p = norm(e), b = [Math.min(start[0], p[0]), Math.min(start[1], p[1]), Math.max(start[0], p[0]), Math.max(start[1], p[1])];
      tmpMark = (b[2] - b[0] > 0.012 || b[3] - b[1] > 0.012)
        ? { pin: [r4((b[0] + b[2]) / 2), r4((b[1] + b[3]) / 2)], box: b.map(r4) } : { pin: start.map(r4), box: null };
      drawMarks(wrap, pinned(boxEl.dataset.target), tmpMark);
    });
    const end = () => { if (!start) return; start = null; drawBox(); $(".lb-th textarea", lb).focus(); };
    wrap.addEventListener("pointerup", end);
    wrap.addEventListener("pointercancel", end);
    drawBox();
  }
  function drawBox() {
    const lb = $("#rv-lb"), wrap = $(".rv-pinwrap", lb);
    drawMarks(wrap, pinned(boxEl.dataset.target), tmpMark);
    const th = $(".lb-th", lb), draft = $("textarea", th)?.value || "";
    th.innerHTML = threadHTML(boxEl, true);
    $("textarea", th).value = draft;
    $(".pinctx", th).innerHTML = tmpMark ? `${tmpMark.box ? "已圈出一块区域" : "已标一个点"} <button class="lnk" data-act="clearmark">撤销</button>` : "";
    bindThread(th, boxEl, () => { const m = tmpMark || {}; tmpMark = null; return { pin: m.pin || null, box: m.box || null }; });
  }
  function closeBox() { $("#rv-lb").classList.remove("on"); boxEl = null; }
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && boxEl) closeBox(); });

  // ---------- 右侧总览抽屉 ----------
  let filterOpen = true;
  function renderDrawer() {
    const d = $("#rv-drawer"), all = doc.comments, open = all.filter((c) => c.status === "open");
    const rnd = doc.rounds.at(-1);
    $("#rv-fab").innerHTML = `评审 <b>${open.length}</b>${online ? "" : " · 未连接"}`;
    $("#rv-fab").classList.toggle("off", !online);
    const list = (filterOpen ? open : all);
    d.querySelector(".dr-body").innerHTML = (online ? "" : '<div class="warn">没连上本地服务：评论不能保存。请运行 <code>python3 workflows/08_site_channels/review_kit/server.py</code> 后打开 http://127.0.0.1:8765/</div>') +
      `<div class="dr-round small dim">第 ${rnd?.n ?? 1} 轮 · ${rnd?.closed ? "已提交 " + rnd.closed.slice(5, 16).replace("T", " ") + "（再写评论会开始新一轮）" : "进行中"}</div>` +
      (list.map((c) => `<div class="dr-item" data-t="${esc(c.target)}"><div class="small"><span class="chip ${(STATUS[c.status] || STATUS.open)[1]}">${STATUS[c.status]?.[0]}</span> ${esc(c.label || c.target)}${c.t != null ? " @" + mmss(c.t) : ""}</div>
        <div>${esc(c.text)}</div>${c.reply ? `<div class="cm-r">↳ ${esc(c.reply)}</div>` : ""}</div>`).join("") || '<div class="dim small">没有评论</div>');
    $$(".dr-item", d).forEach((it) => it.onclick = () => { const el = elOf(it.dataset.t); if (!el) return;
      openThreads.add(it.dataset.t); renderTarget(el); el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("flash"); setTimeout(() => el.classList.remove("flash"), 1400); });
  }
  function renderAll() { targets().forEach(renderTarget); renderDrawer(); if (boxEl) drawBox(); }

  // ---------- 骨架 ----------
  document.body.insertAdjacentHTML("beforeend", `
    <button id="rv-fab">评审</button>
    <aside id="rv-drawer"><div class="dr-h"><b>评审意见</b>
      <label class="small"><input type="checkbox" id="rv-f" checked> 只看待处理</label><button class="lnk" id="rv-close">收起</button></div>
      <div class="dr-body"></div>
      <div class="dr-f"><textarea id="rv-gen" rows="2" placeholder="总体意见（不针对某张图/某个镜头）"></textarea>
        <button class="btn ghost" id="rv-gen-save">保存总体意见</button>
        <button class="btn" id="rv-submit">完成本轮评审</button>
        <div class="small dim">评论写一条存一条（存在 samples/${P}/review_comments.json）。全部写完后点「完成本轮评审」，再回聊天里告诉我。</div></div></aside>
    <div id="rv-lb"></div><div id="rv-toast"></div>`);
  $("#rv-fab").onclick = () => document.body.classList.toggle("rv-dr-on");
  $("#rv-close").onclick = () => document.body.classList.remove("rv-dr-on");
  $("#rv-f").onchange = (e) => { filterOpen = e.target.checked; renderDrawer(); };
  $("#rv-gen-save").onclick = async () => {
    const ta = $("#rv-gen"), text = ta.value.trim(); if (!text) return;
    try { doc.comments.push(await api("POST", "/comments", { target: "general", label: "总体意见", text })); ta.value = ""; toast("已保存"); renderAll(); }
    catch (e) { toast("保存失败：" + e.message); }
  };
  $("#rv-submit").onclick = async () => {
    const n = doc.comments.filter((c) => c.status === "open").length;
    if (!confirm(`提交第 ${doc.rounds.at(-1)?.n ?? 1} 轮评审（${n} 条待处理）？`)) return;
    try { await api("POST", "/rounds/close"); await refresh(); toast("已提交。回聊天里说一声「评审完了」就行", 5000); }
    catch (e) { toast("提交失败：" + e.message); }
  };
  window.addEventListener("focus", refresh);
  setInterval(() => { if (!document.hidden && !document.activeElement?.matches("textarea")) refresh(); }, 15000);
  refresh();
})();
