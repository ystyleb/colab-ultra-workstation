#!/usr/bin/env python3
"""审核页本地服务：静态文件 + 评论 API，评论落盘到 samples/<project>/review_comments.json。

python3 workflows/08_site_channels/review_kit/server.py                 # http://127.0.0.1:8765/
python3 workflows/08_site_channels/review_kit/server.py --dump songifted_nora   # 打印评论（Agent 读这个）

只监听 127.0.0.1。页面只做按条增改（POST /api/<p>/comments、PATCH …/comments/<id>、POST …/rounds/close），
不整份覆盖，所以 Agent 在文件里写回复时，开着的页面不会冲掉它。
"""
from __future__ import annotations

import argparse
import json
import re
import secrets
import threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # workflows/08_site_channels
LOCK = threading.Lock()
PROJ_RE = re.compile(r"^[a-z0-9_]+$")
EDITABLE = {"text", "status", "reply", "pin", "box", "t"}
STATUSES = {"open", "done", "wontfix", "question"}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def store(project: str) -> Path:
    if not PROJ_RE.match(project) or not (ROOT / "samples" / project).is_dir():
        raise ValueError(f"unknown project {project!r}")
    return ROOT / "samples" / project / "review_comments.json"


def load(project: str) -> dict:
    p = store(project)
    if p.exists():
        return json.loads(p.read_text())
    return {"project": project, "rounds": [{"n": 1, "opened": now(), "closed": None}], "comments": []}


def save(project: str, doc: dict):
    p = store(project)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    tmp.replace(p)


def norm_coords(v, n: int):
    """pin = [x, y]、box = [x0, y0, x1, y1]，都是 0–1 的相对坐标；不合法就丢掉。"""
    if not isinstance(v, list) or len(v) != n or not all(isinstance(x, (int, float)) and 0 <= x <= 1 for x in v):
        return None
    return [round(float(x), 4) for x in v]


def current_round(doc: dict) -> dict:
    r = doc["rounds"][-1]
    if r["closed"]:                       # 上一轮已结束，新评论自动开新一轮
        r = {"n": r["n"] + 1, "opened": now(), "closed": None}
        doc["rounds"].append(r)
    return r


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def log_message(self, fmt, *args):
        if "/api/" in (self.path or ""):
            super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, code: int, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _range(self) -> bool:
        """视频拖进度条要 206 Range 响应（SimpleHTTPRequestHandler 不支持）。处理了返回 True。"""
        m = re.match(r"bytes=(\d*)-(\d*)$", self.headers["Range"].strip())
        path = Path(self.translate_path(self.path))
        if not m or not path.is_file():
            return False
        size = path.stat().st_size
        a, b = m.groups()
        start, end = (size - int(b), size - 1) if not a else (int(a), min(int(b) if b else size - 1, size - 1))
        if start < 0 or start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return True
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with path.open("rb") as f:
            f.seek(start)
            left = end - start + 1
            try:
                while left > 0:
                    chunk = f.read(min(left, 1 << 20))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass
        return True

    def _route(self):
        m = re.match(r"^/api/([a-z0-9_]+)/(comments|rounds/close)(?:/([A-Za-z0-9_]+))?$", self.path.split("?")[0])
        return m.groups() if m else None

    def do_GET(self):
        r = self._route()
        if not r:
            if self.path in ("/", "/index.html"):
                self.send_response(302)
                self.send_header("Location", "/out/review/songifted_nora/index.html")
                self.end_headers()
                return
            if self.headers.get("Range") and self._range():
                return
            return super().do_GET()
        try:
            self._json(200, load(r[0]))
        except ValueError as e:
            self._json(404, {"error": str(e)})

    def do_POST(self):
        r = self._route()
        if not r:
            return self._json(404, {"error": "not found"})
        project, kind, _ = r
        try:
            body = self._body()
            with LOCK:
                doc = load(project)
                if kind == "comments":
                    text = str(body.get("text", "")).strip()
                    if not text:
                        return self._json(400, {"error": "empty"})
                    c = {"id": "c" + secrets.token_hex(4), "round": current_round(doc)["n"],
                         "target": str(body["target"]), "label": str(body.get("label", "")), "text": text,
                         "pin": norm_coords(body.get("pin"), 2), "box": norm_coords(body.get("box"), 4), "t": body.get("t"), "img_ver": body.get("img_ver"),
                         "created": now(), "status": "open", "reply": ""}
                    doc["comments"].append(c)
                    save(project, doc)
                    return self._json(200, c)
                rnd = current_round(doc)          # rounds/close
                rnd["closed"] = now()
                save(project, doc)
                return self._json(200, rnd)
        except (ValueError, KeyError) as e:
            return self._json(400, {"error": str(e)})

    def do_PATCH(self):
        r = self._route()
        if not r or r[1] != "comments" or not r[2]:
            return self._json(404, {"error": "not found"})
        project, _, cid = r
        try:
            body = self._body()
            with LOCK:
                doc = load(project)
                c = next((c for c in doc["comments"] if c["id"] == cid), None)
                if not c:
                    return self._json(404, {"error": "no such comment"})
                if body.get("delete"):
                    doc["comments"].remove(c)
                else:
                    for k, v in body.items():
                        if k in EDITABLE and (k != "status" or v in STATUSES):
                            c[k] = v
                    c["edited"] = now()
                save(project, doc)
                return self._json(200, c)
        except ValueError as e:
            return self._json(400, {"error": str(e)})


def dump(project: str, only_open: bool):
    doc = load(project)
    for rnd in doc["rounds"]:
        print(f"== 第 {rnd['n']} 轮  开始 {rnd['opened']}  结束 {rnd['closed'] or '（进行中）'}")
    for c in doc["comments"]:
        if only_open and c["status"] != "open":
            continue
        extra = ((" 圈[" + ",".join(f"{x:.2f}" for x in c["box"]) + "]") if c.get("box")
                 else f" 点({c['pin'][0]:.2f},{c['pin'][1]:.2f})" if c.get("pin") else "") + (f" @{c['t']:.1f}s" if c.get("t") is not None else "")
        print(f"[{c['id']}] R{c['round']} {c['status']:8} {c['target']}{extra}  {c['label']}\n    {c['text']}" +
              (f"\n    ↳ {c['reply']}" if c.get("reply") else ""))


def render(project: str) -> list[Path]:
    """把图上的圈/点画到原图上，导出 out/review/<project>/annot/<评论id>.jpg（Agent 看图用）。"""
    from PIL import Image, ImageDraw, ImageFont
    doc, out, paths = load(project), ROOT / "out" / "review" / project / "annot", []
    out.mkdir(parents=True, exist_ok=True)
    groups: dict[str, list] = {}
    for c in doc["comments"]:
        if c["target"].startswith("kf:") and (c.get("pin") or c.get("box")):
            groups.setdefault(c["target"], []).append(c)
    try:
        fnt = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 30)
    except OSError:
        fnt = ImageFont.load_default()
    for target, cs in groups.items():
        src = ROOT / "samples" / project / "kf" / f"{target[3:]}_1344x768.png"
        if not src.exists():
            continue
        for i, c in enumerate(cs, 1):
            im = Image.open(src).convert("RGB")
            W, H = im.size
            d = ImageDraw.Draw(im)
            if c.get("box"):
                x0, y0, x1, y1 = c["box"]
                d.ellipse((x0 * W, y0 * H, x1 * W, y1 * H), outline=(255, 111, 94), width=6)
                cx, cy = (x0 + x1) / 2 * W - (x1 - x0) / 2 * W * 0.707, (y0 + y1) / 2 * H - (y1 - y0) / 2 * H * 0.707
            else:
                cx, cy = c["pin"][0] * W, c["pin"][1] * H
            d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=(255, 111, 94), outline="white", width=3)
            d.text((cx, cy), str(i), font=fnt, fill="white", anchor="mm")
            p = out / f"{c['id']}.jpg"
            im.save(p, quality=90)
            paths.append(p)
            print(f"{p}  {target}  {c['text'][:40]}")
    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--dump", metavar="PROJECT")
    ap.add_argument("--open-only", action="store_true")
    ap.add_argument("--render", action="store_true", help="配合 --dump：把圈/点画到原图上导出 jpg")
    a = ap.parse_args()
    if a.dump:
        dump(a.dump, a.open_only)
        if a.render:
            render(a.dump)
        return
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    print(f"审核页: http://127.0.0.1:{a.port}/out/review/songifted_nora/index.html  （Ctrl+C 停止）", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
