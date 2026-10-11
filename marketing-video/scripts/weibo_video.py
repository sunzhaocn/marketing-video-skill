#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博视频直链提取 / 下载工具  (weibo_video.py)

支持输入:
  https://video.weibo.com/show?fid=1034:5352515886317584
  https://weibo.com/tv/show/1034:5352515886317584
  https://h5.video.weibo.com/show/1034:5352515886317584
  https://m.weibo.cn/detail/5352515961095905   (普通微博正文里的视频)
  1034:5352515886317584                       (裸 fid)

原理:
  1. passport.weibo.com/visitor/genvisitor + /visitor/visitor?a=incarnate
     拿到访客 cookie(SUB/SUBP), 免登录过 Sina Visitor System。
  2. POST weibo.com/tv/api/component?page=/tv/show/<fid>
     body: data={"Component_Play_Playinfo":{"oid":"<fid>"}}
     返回 data.Component_Play_Playinfo.urls -> {"高清 720P": "//f.video.weibocdn.com/....mp4?...", ...}

注意: 直链带 Expires/ssig 签名, 有时效(约几小时), 过期重新跑一次即可。

用法:
  python weibo_video.py "<视频链接>"                 # 只打印直链
  python weibo_video.py "<视频链接>" -q 720          # 指定清晰度
  python weibo_video.py "<视频链接>" -d ./download   # 下载(带断点续传)
  python weibo_video.py "<视频链接>" -j info.json    # 额外导出完整元数据
"""
import argparse
import http.cookiejar
import json
import os
import random
import re
import shutil
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

TV_API = "https://weibo.com/tv/api/component?page={page}"
STATUS_API = "https://weibo.com/ajax/statuses/show?id={mid}"


class Weibo:
    def __init__(self, timeout=30, verbose=True):
        self.timeout = timeout
        self.verbose = verbose
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj))
        self._visitor_ready = False

    # ---------- low level ----------
    def _log(self, *a):
        if self.verbose:
            print(*a, file=sys.stderr)

    def request(self, url, data=None, headers=None, method=None):
        h = {
            "User-Agent": UA,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        try:
            with self.opener.open(req, timeout=self.timeout) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    # ---------- 1. 访客身份 ----------
    def ensure_visitor(self):
        if self._visitor_ready:
            return
        fp = json.dumps({
            "os": "1",
            "browser": "Chrome124,0,0,0",
            "fonts": "undefined",
            "screenInfo": "1920*1080*24",
            "plugins": "",
        }, separators=(",", ":"))
        _, body = self.request(
            "https://passport.weibo.com/visitor/genvisitor",
            data=urllib.parse.urlencode({"cb": "gen_callback", "fp": fp}).encode(),
            headers={"Referer": "https://passport.weibo.com/visitor/visitor",
                     "Content-Type": "application/x-www-form-urlencoded"})
        m = re.search(r'"tid"\s*:\s*"([^"]+)"', body)
        if not m:
            raise RuntimeError("genvisitor 失败(可能被风控): %s" % body[:200])
        tid = m.group(1)

        q = urllib.parse.urlencode({
            "a": "incarnate", "t": tid, "w": "2", "c": "095", "gc": "",
            "cb": "cross_domain", "from": "weibo",
            "_rand": "%.16f" % random.random()})
        _, body = self.request(
            "https://passport.weibo.com/visitor/visitor?" + q,
            headers={"Referer": "https://passport.weibo.com/visitor/visitor",
                     "Content-Type": "application/x-www-form-urlencoded"})
        sub = re.search(r'"sub"\s*:\s*"([^"]+)"', body)
        subp = re.search(r'"subp"\s*:\s*"([^"]+)"', body)
        if not sub:
            raise RuntimeError("incarnate 失败: %s" % body[:200])
        self._set_cookie("SUB", sub.group(1))
        if subp:
            self._set_cookie("SUBP", subp.group(1))
        self._visitor_ready = True
        self._log("[*] 访客 cookie 已获取 (SUB, %d 字符)" % len(sub.group(1)))

    def _set_cookie(self, name, value):
        for dom in (".weibo.com", ".weibo.cn"):
            self.cj.set_cookie(http.cookiejar.Cookie(
                0, name, value, None, False, dom, False, False, "/", True,
                False, None, False, None, None, {}))

    # ---------- 2. 解析输入 ----------
    @staticmethod
    def parse_fid(text):
        text = text.strip()
        if re.fullmatch(r"\d{4}:\d+", text):
            return text
        m = re.search(r"[?&]fid=(\d{4}:\d+)", text)
        if m:
            return m.group(1)
        m = re.search(r"(?:video\.weibo\.com|h5\.video\.weibo\.com|weibo\.com/tv)/(?:show|show/)(\d{4}:\d+)", text)
        if m:
            return m.group(1)
        m = re.search(r"/(\d{4}:\d+)", text)
        if m:
            return m.group(1)
        raise ValueError("无法从链接中解析 fid: %s" % text)

    @staticmethod
    def parse_mid(text):
        m = re.search(r"weibo\.com/(?:2/)?detail/(\d{6,})", text)
        if m:
            return m.group(1)
        m = re.search(r"m\.weibo\.cn/(?:detail|status|compose)/(\d{6,})", text)
        if m:
            return m.group(1)
        m = re.search(r"weibo\.com/\d+/([A-Za-z0-9]{9,})", text)
        if m:
            return m.group(1)
        m = re.fullmatch(r"\d{15,}", text.strip())
        if m:
            return text.strip()
        return None

    # ---------- 3. 拿播放信息 ----------
    def playinfo(self, fid):
        self.ensure_visitor()
        page = "/tv/show/" + fid
        url = TV_API.format(page=urllib.parse.quote(page, safe=""))
        payload = json.dumps({"Component_Play_Playinfo": {"oid": fid}},
                             separators=(",", ":"))
        _, body = self.request(
            url,
            data=urllib.parse.urlencode({"data": payload}).encode(),
            headers={"Referer": "https://weibo.com" + page,
                     "Content-Type": "application/x-www-form-urlencoded",
                     "X-Requested-With": "XMLHttpRequest"})
        try:
            js = json.loads(body)
        except Exception:
            raise RuntimeError("接口返回非 JSON(风控/需登录): %s" % body[:200])
        info = (js.get("data") or {}).get("Component_Play_Playinfo")
        if not info:
            raise RuntimeError("接口无 Playinfo: %s" % body[:200])
        return js, info

    def playinfo_by_mid(self, mid):
        """普通微博正文链接 -> fid"""
        self.ensure_visitor()
        _, body = self.request(
            STATUS_API.format(mid=mid),
            headers={"Referer": "https://m.weibo.cn/detail/" + mid,
                     "X-Requested-With": "XMLHttpRequest"})
        js = json.loads(body)
        if js.get("error"):
            raise RuntimeError("微博正文接口受限: %s；从已打开的微博页面读取视频链接 fid，再用该链接重试。" % js["error"])
        pi = js.get("page_info") or {}
        obj = (pi.get("media_info") or {}).get("playback_info") or {}
        oid = (pi.get("object_id") or "")
        # object_id 形如 1034:5352515886317584 / 1042015:xxx
        if ":" in str(oid):
            return str(oid)
        for key in ("fid", "media_id", "id"):
            v = pi.get(key) or obj.get(key)
            if v:
                return str(v)
        raise RuntimeError("该微博正文里没找到视频 fid")

    # ---------- 4. 整理输出 ----------
    @staticmethod
    def normalize(u):
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("http://"):
            return "https://" + u[len("http://"):]
        return u

    @staticmethod
    def strip_html(s):
        """微博的 text 字段是 HTML 片段, 去掉标签和实体"""
        s = re.sub(r"<[^>]+>", "", s or "")
        for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                     ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
            s = s.replace(a, b)
        return re.sub(r"\s+", " ", s).strip()

    @classmethod
    def display_name(cls, info):
        """取「真实视频名字」。

        坑: Weibo 的 title 字段绝大多数是通用占位符「<作者>的微博视频」,
        直接拿它当文件名 14 条里 13 条毫无区分度。真实内容名字在:
            1) 少数自定义 title (如 "王仁君裤子太紧没及时回复赵丽颖")
            2) topics[].content  —— 话题, 最干净
            3) text             —— 微博正文, 需要去 HTML
        """
        title = (info.get("title") or "").strip()
        generic = (not title) or title.endswith("的微博视频")
        if not generic:
            return title
        for t in (info.get("topics") or []):
            if isinstance(t, dict):
                c = (t.get("content") or "").strip()
                if c:
                    return c
        text = cls.strip_html(info.get("text"))
        if text:
            # 正文可能是一整段, 取第一个句子做名字更干净
            first = re.split(r"[。！？!?\n]", text)[0].strip()
            return first or text[:40]
        return title or "微博视频"

    @staticmethod
    def quality_key(label):
        m = re.search(r"(\d{3,4})", label or "")
        return int(m.group(1)) if m else 0

    def extract(self, link, want=None):
        mid = None
        try:
            fid = self.parse_fid(link)
        except ValueError:
            mid = self.parse_mid(link)
            if not mid:
                raise
            fid = self.playinfo_by_mid(mid)
            self._log("[*] 由微博正文 %s 解析出 fid=%s" % (mid, fid))
        js, info = self.playinfo(fid)
        urls = info.get("urls") or {}
        items = sorted(
            ({"quality": k, "url": self.normalize(v), "pixels": self.quality_key(k)}
             for k, v in urls.items()),
            key=lambda x: x["pixels"], reverse=True)
        if not items and info.get("stream_url"):
            items = [{"quality": "default",
                      "url": self.normalize(info["stream_url"]), "pixels": 0}]
        if not items:
            raise RuntimeError("未取得任何直链")
        chosen = items[0]
        if want:
            w = str(want)
            for it in items:
                if w in it["quality"] or int(re.search(r"\d+", w).group(0)) == it["pixels"]:
                    chosen = it
                    break
        meta = {
            "fid": fid,
            "mid": info.get("mid"),
            "title": info.get("title"),
            "display_name": self.display_name(info),
            "topics": [t.get("content") for t in (info.get("topics") or [])
                       if isinstance(t, dict) and t.get("content")],
            "text": self.strip_html(info.get("text")),
            "author": info.get("author"),
            "author_id": info.get("author_id"),
            "duration": info.get("duration_time"),
            "cover": self.normalize(info.get("cover_image") or ""),
            "page_url": "https://weibo.com/tv/show/" + fid,
            "stream_url": self.normalize(info.get("stream_url") or ""),
            "qualities": items,
            "chosen": chosen,
        }
        return meta, js

    # ---------- 5. 下载 ----------
    def download(self, url, outdir, filename=None):
        os.makedirs(outdir, exist_ok=True)
        if not filename:
            base = urllib.parse.urlparse(url).path.rsplit("/", 1)[-1] or "video.mp4"
            filename = base
        if not filename.lower().endswith(".mp4"):
            filename += ".mp4"
        path = os.path.join(outdir, filename)
        have = os.path.getsize(path) if os.path.exists(path) else 0
        headers = {"Referer": "https://weibo.com/",
                   "Origin": "https://weibo.com"}
        if have:
            headers["Range"] = "bytes=%d-" % have
        req = urllib.request.Request(url, headers=dict(headers, **{"User-Agent": UA}))
        with self.opener.open(req, timeout=self.timeout) as r:
            total = r.headers.get("Content-Length")
            total = int(total) + have if total else None
            mode = "ab" if (have and r.status == 206) else "wb"
            if mode == "wb":
                have = 0
            self._log("[*] 开始下载 -> %s (已存在 %d 字节)" % (path, have))
            done = have
            t0 = time.time()
            with open(path, mode) as f:
                while True:
                    chunk = r.read(262144)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = done * 100.0 / total
                        speed = (done - have) / max(time.time() - t0, 1e-6) / 1048576
                        sys.stderr.write("\r    %5.1f%%  %.2f MB/s  %.1f/%.1f MB"
                                         % (pct, speed, done / 1048576.0, total / 1048576.0))
                        sys.stderr.flush()
        sys.stderr.write("\n")
        return path


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="微博视频直链提取/下载")
    ap.add_argument("link", help="视频链接或 fid")
    ap.add_argument("-q", "--quality", help="清晰度, 如 720 / 1080 / 480")
    ap.add_argument("-d", "--download", metavar="DIR", help="下载到目录")
    ap.add_argument("-j", "--json", metavar="FILE", help="导出完整接口 JSON")
    ap.add_argument("--all", action="store_true", help="列出所有清晰度直链")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    wb = Weibo(verbose=not args.quiet)
    try:
        meta, raw = wb.extract(args.link, args.quality)
    except Exception as e:
        print("[!] %s" % e, file=sys.stderr)
        return 1

    print("名字 : %s" % meta["display_name"])
    if meta.get("title") and meta["title"] != meta["display_name"]:
        print("标题 : %s  (通用占位, 已用真实名字)" % meta["title"])
    if meta.get("topics"):
        print("话题 : %s" % " / ".join(meta["topics"][:3]))
    print("作者 : %s (uid %s)" % (meta["author"], meta["author_id"]))
    print("时长 : %s" % meta["duration"])
    print("页面 : %s" % meta["page_url"])
    print("-" * 60)
    if args.all:
        for it in meta["qualities"]:
            print("%-12s %s" % (it["quality"], it["url"]))
    else:
        print("直链 : %s" % meta["chosen"]["url"])
        print("清晰度: %s" % meta["chosen"]["quality"])
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=1)
        print("元数据: %s" % os.path.abspath(args.json))
    if args.download:
        p = wb.download(meta["chosen"]["url"], args.download)
        print("已保存: %s" % os.path.abspath(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
