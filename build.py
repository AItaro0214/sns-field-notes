#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNS FIELD NOTES 静的サイトビルダー

data/observations.json と assets/covers/<date>.jpg（任意）を読み、
docs/ 以下に GitHub Pages 向け静的サイトを生成する。標準ライブラリのみ。
data/marketing.json（マーケティングスペースのスナップショット）があれば、
docs/marketing/index.html も生成する。
data/communities.json（界隈カテゴリの定点観測）があれば、
docs/communities/index.html も生成する。
data/companies.json（企業・業界セクターの定点観測）があれば、
docs/companies/index.html も生成する。

使い方: python3 build.py
"""
import html
import json
import os
import shutil
from collections import Counter
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE, "data", "observations.json")
MARKETING_PATH = os.path.join(BASE, "data", "marketing.json")
COMMUNITIES_PATH = os.path.join(BASE, "data", "communities.json")
COMPANIES_PATH = os.path.join(BASE, "data", "companies.json")
COVERS_DIR = os.path.join(BASE, "assets", "covers")
SITE_DIR = os.path.join(BASE, "docs")

ACCENTS = ["accent-0", "accent-1", "accent-2", "accent-3", "accent-4", "accent-5"]

PILLAR_LABELS = {
    "theory": "最新の理論・手法",
    "stats": "統計・調査で見る社会の傾向",
    "sns": "SNSの流行・ミーム・キーワード",
    "category": "カテゴリ別トレンド",
}
PILLAR_ORDER = ["theory", "stats", "sns", "category"]


def esc(s):
    return html.escape(str(s), quote=True)


def fmt_posts(n):
    """投稿数を表示用に整形する（例: 6500000 -> '6.5M', 57400 -> '57.4K'）。"""
    if n is None:
        return None
    if n >= 1_000_000:
        v = n / 1_000_000
        return (f"{v:.1f}".rstrip("0").rstrip(".")) + "M"
    if n >= 1_000:
        v = n / 1_000
        return (f"{v:.1f}".rstrip("0").rstrip(".")) + "K"
    return f"{n:,}"


def top_trend(day):
    """その日の投稿数最大のトレンド（投稿数が全て不明なら先頭）。"""
    known = [t for t in day["trends"] if t.get("posts")]
    if known:
        return max(known, key=lambda t: t["posts"])
    return day["trends"][0] if day["trends"] else None


def cover_rel(date, from_day_page=False):
    """カバー画像が存在すれば相対パスを、無ければ None を返す。"""
    src = os.path.join(COVERS_DIR, date + ".jpg")
    if not os.path.isfile(src):
        return None
    prefix = "../" if from_day_page else ""
    return f"{prefix}assets/covers/{date}.jpg"


def cover_html(date, from_day_page=False, cls="cover"):
    rel = cover_rel(date, from_day_page)
    if rel:
        return f'<img class="{cls}" src="{esc(rel)}" alt="{esc(date)} の観測カバー画像">'
    return f'<div class="{cls} cover-fallback" role="img" aria-label="{esc(date)} の観測（カバー画像なし）"><span>{esc(date)}</span></div>'


CSS = r"""
:root{
  --bg:#f4f5f7; --surface:#ffffff; --ink:#1c2333; --muted:#5b6478;
  --line:#dde1ea; --accent:#3b5bdb; --accent-soft:#e7ecfd;
  --warn:#b3261e; --warn-soft:#fdecea; --gold:#8a6d00; --gold-soft:#fdf6d8;
  --radius:14px;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family:"Hiragino Kaku Gothic ProN","Hiragino Sans","Noto Sans JP","Yu Gothic UI","Yu Gothic",Meiryo,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  line-height:1.75; font-size:16px;
}
a{color:var(--accent); text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1080px; margin:0 auto; padding:0 16px 64px}
header.site-head{
  background:linear-gradient(135deg,#1c2333,#2c3a5e); color:#fff;
  padding:36px 0 28px; margin-bottom:28px;
}
header.site-head .wrap{padding-bottom:0}
header.site-head h1{margin:0 0 6px; font-size:1.7rem; letter-spacing:.04em}
header.site-head p{margin:0; color:#c6cfe4; font-size:.95rem}
header.site-head a{color:#fff}
.kpis{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:0 0 28px}
.kpi{background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); padding:16px 18px}
.kpi .num{font-size:1.9rem; font-weight:700; line-height:1.2}
.kpi .lbl{color:var(--muted); font-size:.85rem}
section.panel{background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); padding:22px 22px 18px; margin-bottom:24px}
section.panel > h2{margin:0 0 14px; font-size:1.25rem; border-left:5px solid var(--accent); padding-left:10px}
section.panel > h3{margin:20px 0 8px; font-size:1.05rem}
.chart{width:100%; height:auto; display:block}
.chart .bar{fill:var(--accent)}
.chart .bar:hover{fill:#2f4bc0}
.chart text{font-size:12px; fill:var(--ink)}
.chart .muted{fill:var(--muted)}
.theme{border:1px solid var(--line); border-radius:var(--radius); padding:16px 18px; margin-bottom:14px; background:#fbfcfe}
.theme h3{margin:0 0 4px; font-size:1.08rem}
.theme .desc{color:var(--muted); font-size:.92rem; margin:0 0 12px}
.timeline{list-style:none; margin:0; padding:0}
.timeline li{display:flex; gap:12px; padding:8px 0; border-top:1px dashed var(--line)}
.timeline li:first-child{border-top:none}
.timeline .d{flex:0 0 auto; font-weight:700; white-space:nowrap}
.timeline .ph{flex:0 0 auto; background:var(--accent-soft); color:var(--accent); border-radius:999px; padding:0 10px; font-size:.82rem; font-weight:700; height:fit-content; margin-top:3px}
.timeline .nt{color:var(--ink); font-size:.95rem}
.daycards{display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:16px}
.daycard{background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); overflow:hidden; display:flex; flex-direction:column}
.daycard .cover,.daycard .cover-fallback{width:100%; height:170px; object-fit:cover; display:block}
.cover-fallback{background:linear-gradient(135deg,#2c3a5e,#3b5bdb); color:#fff; display:flex; align-items:center; justify-content:center; font-size:1.3rem; font-weight:700; letter-spacing:.06em}
.daycard .body{padding:14px 16px 16px; display:flex; flex-direction:column; gap:6px; flex:1}
.daycard .date{font-weight:700; font-size:1.05rem}
.daycard .top{font-size:.95rem}
.daycard .imp{color:var(--muted); font-size:.9rem; flex:1}
.daycard .more{font-size:.9rem; font-weight:700}
.badge{display:inline-block; border-radius:999px; padding:0 9px; font-size:.78rem; font-weight:700; vertical-align:middle}
.badge-new{background:#e6f4ea; color:#137333}
.badge-cont{background:var(--gold-soft); color:var(--gold)}
/* 日別ページ */
.hero{border-radius:var(--radius); overflow:hidden; margin-bottom:24px; border:1px solid var(--line); background:var(--surface)}
.hero .cover,.hero .cover-fallback{width:100%; height:300px; object-fit:cover; display:block}
.hero .hero-body{padding:20px 22px}
.hero h1{margin:0 0 6px; font-size:1.6rem}
.hero .meta{color:var(--muted); font-size:.92rem}
.hero.accent-0{border-top:8px solid #3b5bdb}.hero.accent-1{border-top:8px solid #0b8043}
.hero.accent-2{border-top:8px solid #b06000}.hero.accent-3{border-top:8px solid #9334a6}
.hero.accent-4{border-top:8px solid #c2185b}.hero.accent-5{border-top:8px solid #00796b}
.trend-row{margin-bottom:14px}
.trend-row .t-head{display:flex; justify-content:space-between; gap:12px; align-items:baseline; flex-wrap:wrap}
.trend-row .t-name{font-weight:700}
.trend-row .t-posts{color:var(--muted); font-size:.88rem; white-space:nowrap}
.trend-row .t-bar{height:10px; background:#edf0f6; border-radius:999px; overflow:hidden; margin:5px 0 6px}
.trend-row .t-bar > div{height:100%; background:var(--accent); border-radius:999px}
.trend-row .t-bar.unknown > div{background:repeating-linear-gradient(45deg,#c9d2e8,#c9d2e8 6px,#e3e8f5 6px,#e3e8f5 12px)}
.trend-row p{margin:0; color:#333c52; font-size:.95rem}
blockquote.post-note{
  margin:0 0 14px; background:#fbfcfe; border:1px solid var(--line);
  border-left:5px solid var(--accent); border-radius:10px; padding:14px 16px;
}
blockquote.post-note h3{margin:0 0 4px; font-size:1rem}
blockquote.post-note .author{color:var(--muted); font-size:.85rem}
blockquote.post-note p{margin:6px 0 0}
blockquote.post-note .feeling{color:#333c52; font-size:.93rem}
blockquote.post-note .feeling::before{content:"推測される気持ち："; font-weight:700; color:var(--muted)}
blockquote.post-note .note-link{margin:8px 0 0}
blockquote.post-note .note-link a{font-weight:700; font-size:.9rem}
.trend-row .t-src{font-size:.8rem; font-weight:700; white-space:nowrap}
.contro{border:1px solid #f0c6c2; background:var(--warn-soft); border-radius:10px; padding:12px 16px; margin-bottom:12px}
.contro h3{margin:0 0 4px; font-size:1rem; color:var(--warn)}
.contro p{margin:0; font-size:.95rem}
.callout{border:1px solid #e8d98a; background:var(--gold-soft); border-radius:10px; padding:14px 18px; margin-bottom:12px}
.callout p{margin:0}
.callout .no{font-weight:700; color:var(--gold)}
.note-box{background:#f0f3fa; border-radius:10px; padding:14px 18px; font-size:.95rem}
.note-box p{margin:0}
.kv{display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px}
.kv .item{background:#fbfcfe; border:1px solid var(--line); border-radius:10px; padding:12px 16px}
.kv .item h3{margin:0 0 4px; font-size:.95rem; color:var(--muted)}
.kv .item p{margin:0; font-size:.95rem}
nav.pager{display:flex; justify-content:space-between; gap:12px; margin-top:8px; flex-wrap:wrap}
nav.pager a{background:var(--surface); border:1px solid var(--line); border-radius:999px; padding:6px 16px; font-size:.92rem}
footer.site-foot{color:var(--muted); font-size:.85rem; text-align:center; padding:24px 16px 40px}
@media (max-width:640px){
  header.site-head h1{font-size:1.35rem}
  .hero .cover,.hero .cover-fallback{height:190px}
  .timeline li{flex-wrap:wrap}
  section.panel{padding:16px}
}
/* 界隈マップ */
.comm-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:16px}
.comm-card{background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); padding:18px 20px; display:flex; flex-direction:column}
.comm-card h3{margin:0; font-size:1.12rem}
.comm-head{display:flex; justify-content:space-between; align-items:flex-start; gap:10px; margin-bottom:4px}
.comm-card .scope{color:var(--muted); font-size:.9rem; margin:0 0 12px}
.phase-badge{flex:0 0 auto; border-radius:999px; padding:1px 11px; font-size:.8rem; font-weight:700; white-space:nowrap; margin-top:3px}
.phase-sprout{background:#e6f4ea; color:#137333}
.phase-growing{background:var(--accent-soft); color:var(--accent)}
.phase-settled{background:var(--gold-soft); color:var(--gold)}
.phase-cooling{background:#e8ecf3; color:#45506a}
.phase-watching{background:#eef0f4; color:var(--muted)}
.comm-card .mech{background:#f0f3fa; border-radius:10px; padding:10px 14px; font-size:.93rem; margin:0 0 12px}
.comm-card .mech .mech-lbl{display:block; font-weight:700; font-size:.8rem; color:var(--muted); margin-bottom:2px}
.comm-card .timeline{margin-top:auto}
.comm-empty{color:var(--muted); font-size:.92rem; margin:auto 0 0}
@media (max-width:640px){
  .comm-grid{grid-template-columns:1fr}
}
/* 企業・業界マップ */
.comp-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:16px}
.comp-card{background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); padding:18px 20px; display:flex; flex-direction:column}
.comp-card h3{margin:0 0 4px; font-size:1.12rem}
.comp-card .scope{color:var(--muted); font-size:.9rem; margin:0 0 12px}
.comp-card .watch{background:#f0f3fa; border-radius:10px; padding:10px 14px; font-size:.93rem; margin:0 0 12px}
.comp-card .watch .watch-lbl{display:block; font-weight:700; font-size:.8rem; color:var(--muted); margin-bottom:2px}
.comp-entries{list-style:none; margin:auto 0 0; padding:0}
.comp-entries li{padding:8px 0; border-top:1px dashed var(--line)}
.comp-entries li:first-child{border-top:none}
.comp-entries .d{font-weight:700; white-space:nowrap; font-size:.92rem}
.comp-entries .ttl{display:block; font-size:.95rem; margin:2px 0}
.comp-entries .src{color:var(--muted); font-size:.83rem}
.comp-empty{color:var(--muted); font-size:.92rem; margin:auto 0 0}
@media (max-width:640px){
  .comp-grid{grid-template-columns:1fr}
}
/* 共通ナビ */
nav.site-nav{background:#141a29; color:#fff}
nav.site-nav .wrap{padding-top:0; padding-bottom:0; display:flex; gap:6px; flex-wrap:wrap}
nav.site-nav a{color:#c6cfe4; padding:10px 14px; font-size:.92rem; font-weight:700; display:inline-block}
nav.site-nav a:hover{text-decoration:none; color:#fff}
nav.site-nav a.active{color:#fff; box-shadow:inset 0 -3px 0 var(--accent); background:rgba(255,255,255,.06)}
/* マーケティング */
.mitate-lead{font-size:1.15rem; font-weight:700; margin:0 0 10px}
.meta-line{color:var(--muted); font-size:.85rem; margin:0 0 12px}
.chips{display:flex; flex-wrap:wrap; gap:6px; margin:8px 0 0}
.chip{display:inline-block; background:#eef1f8; color:#333c52; border-radius:999px; padding:1px 10px; font-size:.8rem}
.chip.media{background:var(--accent-soft); color:var(--accent); font-weight:700}
.chip.cat{background:var(--gold-soft); color:var(--gold); font-weight:700}
.chip .cnt{font-weight:700}
.trend-cards{display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:14px; margin:14px 0 4px}
.trend-card{border:1px solid var(--line); border-radius:var(--radius); padding:16px 18px; background:#fbfcfe}
.trend-card h3{margin:0 0 6px; font-size:1.02rem}
.trend-card p{margin:0; font-size:.93rem; color:#333c52}
.impl{border:1px solid var(--line); border-radius:10px; padding:12px 16px; margin-bottom:12px; background:#fbfcfe}
.impl .cat{font-weight:700; color:var(--accent); font-size:.9rem}
.impl p{margin:4px 0 0; font-size:.95rem}
.impl .imp{background:var(--gold-soft); border-radius:8px; padding:8px 12px}
.feat{border:2px solid var(--accent); border-radius:var(--radius); padding:18px 20px; background:#fbfcfe}
.feat h3{margin:0 0 4px; font-size:1.12rem}
.feat .pub{color:var(--muted); font-size:.9rem; margin:0 0 10px}
.feat ul{margin:8px 0; padding-left:1.3em}
.feat li{font-size:.95rem; margin-bottom:4px}
.feat .survey{font-size:.9rem; color:#333c52; background:#f0f3fa; border-radius:8px; padding:8px 12px}
.feat .srcs{font-size:.92rem; margin:10px 0 0}
.counts{display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:12px}
.counts .item{background:#fbfcfe; border:1px solid var(--line); border-radius:10px; padding:12px 16px}
.counts .item h3{margin:0 0 6px; font-size:.95rem; color:var(--muted)}
.counts table{width:100%; border-collapse:collapse; font-size:.92rem}
.counts td{padding:2px 0}
.counts td.n{text-align:right; font-weight:700; white-space:nowrap}
.artcard{border:1px solid var(--line); border-radius:var(--radius); padding:16px 18px; margin-bottom:12px; background:var(--surface)}
.artcard h3{margin:0 0 6px; font-size:1.02rem; line-height:1.5}
.artcard p{margin:0; font-size:.93rem; color:#333c52}
.artcard .src{color:var(--muted); font-size:.85rem; margin-top:8px}
.chip.pillar{background:#e6f4ea; color:#137333; font-weight:700}
/* フィルターバー（マーケティング） */
.filterbar{position:sticky; top:0; z-index:20; background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); padding:14px 16px; margin-bottom:24px; box-shadow:0 2px 10px rgba(28,35,51,.07)}
.fgroup{display:flex; align-items:flex-start; gap:8px; margin-bottom:8px; flex-wrap:wrap}
.fgroup .flabel{flex:0 0 5em; font-weight:700; font-size:.85rem; color:var(--muted); padding-top:5px}
.fchips{display:flex; flex-wrap:wrap; gap:6px; flex:1; min-width:0}
.fchip{appearance:none; -webkit-appearance:none; border:1px solid var(--line); background:#eef1f8; color:#333c52; border-radius:999px; padding:3px 12px; font-size:.83rem; line-height:1.6; cursor:pointer; font-family:inherit}
.fchip:hover{border-color:var(--accent); color:var(--accent)}
.fchip.active{background:var(--accent); border-color:var(--accent); color:#fff; font-weight:700}
.frow{display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-top:10px}
.fsearch{flex:1; min-width:180px; padding:8px 12px; border:1px solid var(--line); border-radius:8px; font-size:.95rem; font-family:inherit; color:var(--ink)}
.fcount{margin:0; color:var(--muted); font-size:.9rem; white-space:nowrap}
.fcount .n{font-weight:700; color:var(--ink); font-size:1.05rem}
.freset{appearance:none; -webkit-appearance:none; border:1px solid var(--line); background:var(--surface); color:var(--ink); border-radius:8px; padding:7px 14px; font-size:.88rem; cursor:pointer; font-family:inherit}
.freset:hover{border-color:var(--accent); color:var(--accent)}
.fempty{color:var(--muted); text-align:center; padding:28px 0; margin:0}
@media (max-width:640px){
  .filterbar{padding:12px}
  .fgroup .flabel{flex-basis:100%; padding-top:0}
  .fsearch{min-width:140px}
}
"""


def page_shell(title, body, depth=0, section="sns"):
    prefix = "../" * depth
    sns_cls = ' class="active"' if section == "sns" else ""
    mkt_cls = ' class="active"' if section == "marketing" else ""
    comm_cls = ' class="active"' if section == "communities" else ""
    comp_cls = ' class="active"' if section == "companies" else ""
    nav = f"""
<nav class="site-nav"><div class="wrap">
  <a href="{prefix}index.html"{sns_cls}>SNS観測トップ</a>
  <a href="{prefix}marketing/index.html"{mkt_cls}>マーケティング最新情報</a>
  <a href="{prefix}communities/index.html"{comm_cls}>界隈マップ</a>
  <a href="{prefix}companies/index.html"{comp_cls}>企業・業界マップ</a>
</div></nav>"""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
{nav}
{body}
<footer class="site-foot">SNS FIELD NOTES — Instagram / Threads 観測記録（読み取り専用・トレンド起点の観測）</footer>
</body>
</html>
"""


def svg_bar_chart(days):
    """日ごとのトップトレンド投稿数の SVG バーチャート。"""
    tops = []
    for d in days:
        t = top_trend(d)
        tops.append((d, t))
    values = [t["posts"] for _, t in tops if t and t.get("posts")]
    maxv = max(values) if values else 1
    n = len(tops)
    width, height = 1020, 300
    pad_l, pad_b, pad_t = 16, 64, 34
    chart_h = height - pad_b - pad_t
    slot = (width - pad_l * 2) / max(n, 1)
    bar_w = min(96, slot * 0.55)
    parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="日ごとのトップトレンド投稿数グラフ">']
    for i, (d, t) in enumerate(tops):
        x = pad_l + slot * i + (slot - bar_w) / 2
        v = t["posts"] if t and t.get("posts") else 0
        h = (v / maxv) * chart_h if v else 0
        y = pad_t + (chart_h - h)
        label = fmt_posts(v) if v else "—"
        name = t["name"] if t else ""
        parts.append(f'<rect class="bar" x="{x:.0f}" y="{y:.0f}" width="{bar_w:.0f}" height="{h:.0f}" rx="6"><title>{esc(name)}: {esc(label)}</title></rect>')
        parts.append(f'<text x="{x + bar_w / 2:.0f}" y="{y - 8:.0f}" text-anchor="middle" font-weight="700">{esc(label)}</text>')
        parts.append(f'<text x="{x + bar_w / 2:.0f}" y="{height - 40}" text-anchor="middle">{esc(d["date"][5:])}（{esc(d["weekday"])}）</text>')
        short = name if len(name) <= 12 else name[:11] + "…"
        parts.append(f'<text class="muted" x="{x + bar_w / 2:.0f}" y="{height - 20}" text-anchor="middle">{esc(short)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def build_index(data, days):
    total_topics = sum(len(d["trends"]) for d in days)
    total_notes = sum(len(d["postNotes"]) for d in days)
    total_impl = sum(len(d["implications"]) for d in days)
    latest = days[-1]
    lt = top_trend(latest)
    lt_posts = fmt_posts(lt["posts"]) if lt and lt.get("posts") else "—"

    kpis = f"""
<div class="kpis">
  <div class="kpi"><div class="num">{len(days)}</div><div class="lbl">観測日数（日）</div></div>
  <div class="kpi"><div class="num">{total_topics}</div><div class="lbl">累計トレンドトピック数</div></div>
  <div class="kpi"><div class="num">{total_notes}</div><div class="lbl">個別投稿ノート数</div></div>
  <div class="kpi"><div class="num">{total_impl}</div><div class="lbl">累計の示唆</div></div>
  <div class="kpi"><div class="num">{esc(lt_posts)}</div><div class="lbl">最新日（{esc(latest['date'])}）のトップトレンド投稿数：{esc(lt['name'] if lt else '')}</div></div>
</div>"""

    themes_html = []
    for th in data.get("themes", []):
        rows = []
        for ph in th["phases"]:
            rows.append(
                f'<li><span class="d">{esc(ph["date"])}</span>'
                f'<span class="ph">{esc(ph["phase"])}</span>'
                f'<span class="nt">{esc(ph["note"])}</span></li>'
            )
        themes_html.append(
            f'<div class="theme"><h3>{esc(th["name"])}</h3>'
            f'<p class="desc">{esc(th["description"])}</p>'
            f'<ul class="timeline">{"".join(rows)}</ul></div>'
        )

    cards = []
    for d in reversed(days):
        t = top_trend(d)
        imp = d["implications"][0] if d["implications"] else ""
        cards.append(f"""
<article class="daycard">
  {cover_html(d['date'])}
  <div class="body">
    <div class="date">{esc(d['date'])}（{esc(d['weekday'])}）{' ― 初回観測' if d.get('firstObservation') else ''}</div>
    <div class="top">トップトレンド：<strong>{esc(t['name'] if t else '')}</strong>{'（' + esc(fmt_posts(t['posts'])) + ' posts）' if t and t.get('posts') else ''}</div>
    <p class="imp">示唆：{esc(imp)}</p>
    <a class="more" href="days/{esc(d['date'])}.html">この日の記事を読む →</a>
  </div>
</article>""")

    body = f"""
<header class="site-head"><div class="wrap">
  <h1>{esc(data['site']['title'])}</h1>
  <p>{esc(data['site']['description'])}</p>
</div></header>
<div class="wrap">
{kpis}
<section class="panel">
  <h2>日ごとのトップトレンド投稿数</h2>
  {svg_bar_chart(days)}
</section>
<section class="panel">
  <h2>継続テーマ・トラッカー</h2>
  {''.join(themes_html)}
</section>
<section class="panel">
  <h2>日別記事</h2>
  <div class="daycards">{''.join(cards)}</div>
</section>
<p class="note-box">{esc(data['site']['note'])}</p>
</div>"""
    return page_shell(data["site"]["title"], body, depth=0)


def build_day(data, day, idx, days):
    accent = ACCENTS[idx % len(ACCENTS)]
    d = day
    max_posts = max([t["posts"] for t in d["trends"] if t.get("posts")] or [0])

    trend_rows = []
    for t in d["trends"]:
        badge = '<span class="badge badge-new">新規</span>' if t["status"] == "新規" else '<span class="badge badge-cont">継続</span>'
        if t.get("posts"):
            pct = max(4, round(t["posts"] / max_posts * 100)) if max_posts else 0
            bar = f'<div class="t-bar"><div style="width:{pct}%"></div></div>'
            posts_txt = esc(t.get("postsLabel") or (fmt_posts(t["posts"]) + " posts"))
        else:
            bar = '<div class="t-bar unknown"><div style="width:100%"></div></div>'
            posts_txt = esc(t.get("postsLabel") or "投稿数不明")
        src_link = ""
        if t.get("url"):
            src_link = f' <a class="t-src" href="{esc(t["url"])}" target="_blank" rel="noopener">投稿を見る</a>'
        trend_rows.append(f"""
<div class="trend-row">
  <div class="t-head"><span class="t-name">{esc(t['name'])} {badge}{src_link}</span><span class="t-posts">{posts_txt}</span></div>
  {bar}
  <p>{esc(t['summary'])}</p>
</div>""")

    deep = "".join(
        f"<h3>{esc(x['title'])}</h3><p>{esc(x['summary'])}</p>" for x in d["deepDive"]
    ) or "<p>この日の深掘りはありません。</p>"

    if d["postNotes"]:
        notes = []
        for pn in d["postNotes"]:
            author = f'<div class="author">{esc(pn["author"])}</div>' if pn.get("author") else ""
            note_link = ""
            if pn.get("url"):
                note_link = f'\n  <p class="note-link"><a href="{esc(pn["url"])}" target="_blank" rel="noopener">投稿を見る →</a></p>'
            notes.append(f"""
<blockquote class="post-note">
  <h3>{esc(pn['topic'])}</h3>{author}
  <p>{esc(pn['summary'])}</p>
  <p class="feeling">{esc(pn['feeling'])}</p>{note_link}
</blockquote>""")
        notes_html = "".join(notes)
    else:
        notes_html = "<p>この日は個別投稿ノートの記録がありません（観測初期のため、定性観測まとめのみ）。</p>"

    if d["controversies"]:
        contro_html = "".join(
            f'<div class="contro"><h3>{esc(c["title"])}</h3><p>{esc(c["summary"])}</p></div>'
            for c in d["controversies"]
        )
    else:
        contro_html = "<p>この日は論争・愚痴として特記された記録がありません。</p>"

    impl_html = "".join(
        f'<div class="callout"><p><span class="no">示唆 {i + 1}.</span> {esc(s)}</p></div>'
        for i, s in enumerate(d["implications"])
    )

    observer = ""
    if d.get("observerNote"):
        observer = f"""
<section class="panel">
  <h2>観測者の所感（もっとこうすれば良いのに）</h2>
  <div class="note-box"><p>{esc(d['observerNote'])}</p></div>
</section>"""

    prev_link = ""
    next_link = ""
    if idx > 0:
        p = days[idx - 1]
        prev_link = f'<a href="{esc(p["date"])}.html">← 前の日 {esc(p["date"])}（{esc(p["weekday"])}）</a>'
    if idx < len(days) - 1:
        nx = days[idx + 1]
        next_link = f'<a href="{esc(nx["date"])}.html">{esc(nx["date"])}（{esc(nx["weekday"])}） 次の日 →</a>'

    first = " ― 初回観測" if d.get("firstObservation") else ""
    body = f"""
<div class="wrap">
<p style="margin:18px 0"><a href="../index.html">← ダッシュボードに戻る</a></p>
<div class="hero {accent}">
  {cover_html(d['date'], from_day_page=True)}
  <div class="hero-body">
    <h1>{esc(d['date'])}（{esc(d['weekday'])}）の観測{first}</h1>
    <p class="meta">観測の起点：{esc(d['source'])}</p>
  </div>
</div>
<section class="panel">
  <h2>今日のトレンド（Threads）</h2>
  {''.join(trend_rows)}
</section>
<section class="panel">
  <h2>日替わり深掘り</h2>
  {deep}
</section>
<section class="panel">
  <h2>個別投稿から見えたこと</h2>
  {notes_html}
</section>
<section class="panel">
  <h2>論争・愚痴</h2>
  {contro_html}
</section>
<section class="panel">
  <h2>定性観測</h2>
  <div class="kv">
    <div class="item"><h3>論調</h3><p>{esc(d['tone'])}</p></div>
    <div class="item"><h3>話している層の傾向</h3><p>{esc(d['audience'])}</p></div>
  </div>
</section>
{observer}
<section class="panel">
  <h2>示唆</h2>
  {impl_html}
</section>
<nav class="pager">{prev_link}{next_link}</nav>
</div>"""
    title = f"{d['date']}（{d['weekday']}）の観測 | {data['site']['title']}"
    return page_shell(title, body, depth=1)


def fmt_dt_jst(iso):
    """ISO日時（UTC）を 'YYYY-MM-DD HH:MM JST' に整形する。失敗時は日付部分を返す。"""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST")
    except Exception:
        return str(iso)[:10]


def build_marketing(mk):
    ins = mk["insight"]
    arts = mk["articles"]

    # --- 今の見立て ---
    trend_cards = []
    for tr in ins.get("trends", []):
        kw = "".join(f'<span class="chip">{esc(k)}</span>' for k in tr.get("keywords", []))
        mt = "".join(f'<span class="chip media">{esc(m)}</span>' for m in tr.get("mediaTypes", []))
        trend_cards.append(f"""
<div class="trend-card">
  <h3>{esc(tr['title'])}</h3>
  <p>{esc(tr['description'])}</p>
  <div class="chips">{kw}{mt}</div>
</div>""")

    impl_html = []
    for im in ins.get("implications", []):
        impl_html.append(f"""
<div class="impl">
  <span class="cat">{esc(im['category'])}</span>
  <p>{esc(im['insight'])}</p>
  <p class="imp">{esc(im['implication'])}</p>
</div>""")

    mitate = f"""
<section class="panel">
  <h2>今の見立て</h2>
  <p class="mitate-lead">{esc(ins['headline'])}</p>
  <p class="meta-line">見立ての生成：{esc(fmt_dt_jst(ins.get('generatedAt')))}／もとにした記事：{esc(ins.get('basedOn', ''))}件</p>
  <p>{esc(ins['overview'])}</p>
  <div class="trend-cards">{''.join(trend_cards)}</div>
  <h3>カテゴリ別の示唆</h3>
  {''.join(impl_html)}
  <h3>メディア横断メモ</h3>
  <div class="note-box"><p>{esc(ins['crossMedia'])}</p></div>
</section>"""

    # --- 注目レポート ---
    feat_html = []
    for ft in mk.get("featured", []):
        points = "".join(f"<li>{esc(p)}</li>" for p in ft.get("points", []))
        tags = "".join(f'<span class="chip">{esc(t)}</span>' for t in ft.get("tags", []))
        feat_html.append(f"""
<div class="feat">
  <h3>{esc(ft['title'])}</h3>
  <p class="pub">{esc(ft['publisher'])}／公開：{esc(ft['publishedDate'])}</p>
  <p>{esc(ft['summary'])}</p>
  <ul>{points}</ul>
  <p class="survey">調査概要：{esc(ft['survey'])}</p>
  <div class="chips">{tags}</div>
  <p class="srcs">出典：<a href="{esc(ft['sourceUrl'])}" target="_blank" rel="noopener">{esc(ft['sourceLabel'])}</a>／<a href="{esc(ft['secondaryUrl'])}" target="_blank" rel="noopener">{esc(ft['secondaryLabel'])}</a></p>
</div>""")
    featured = ""
    if feat_html:
        featured = f"""
<section class="panel">
  <h2>注目レポート</h2>
  {''.join(feat_html)}
</section>"""

    # --- 収録サマリー ---
    pc = Counter(a["pillar"] for a in arts)
    mc = Counter(a["mediaLabel"] for a in arts)
    cc = Counter(a["category"] for a in arts)

    def count_rows(counter, labels=None):
        out = []
        for k, v in counter.most_common():
            name = labels.get(k, k) if labels else k
            out.append(f'<tr><td>{esc(name)}</td><td class="n">{v}</td></tr>')
        return "".join(out)

    kw_chips = "".join(
        f'<span class="chip">{esc(k["keyword"])} <span class="cnt">{esc(k["count"])}</span></span>'
        for k in mk.get("keywords", [])
    )
    summary_panel = f"""
<section class="panel">
  <h2>収録サマリー</h2>
  <div class="kpis">
    <div class="kpi"><div class="num">{esc(mk['spaceTotal'])}</div><div class="lbl">スペースの総収録数（件）</div></div>
    <div class="kpi"><div class="num">{len(arts)}</div><div class="lbl">このページに掲載している記事（件）</div></div>
    <div class="kpi"><div class="num">{len(mk.get('featured', []))}</div><div class="lbl">注目レポート（件）</div></div>
  </div>
  <p class="meta-line">スペースのデータ更新：{esc(fmt_dt_jst(mk.get('updatedAt')))}（総収録{esc(mk['spaceTotal'])}件のうち、最新{len(arts)}件を掲載しています）</p>
  <div class="counts">
    <div class="item"><h3>柱別</h3><table>{count_rows(pc, PILLAR_LABELS)}</table></div>
    <div class="item"><h3>メディア種別</h3><table>{count_rows(mc)}</table></div>
    <div class="item"><h3>カテゴリ別</h3><table>{count_rows(cc)}</table></div>
  </div>
  <h3>注目キーワード</h3>
  <div class="chips">{kw_chips}</div>
</section>"""

    # --- フィルターバー ---
    FILTER_PILLAR_ORDER = ["stats", "theory", "sns", "category"]
    FILTER_MEDIA_ORDER = ["research", "official", "media", "sns", "global"]
    FILTER_CATEGORY_ORDER = ["BtoB", "D2C", "飲食", "小売", "化粧品", "医療", "製造・メーカー", "総合"]
    media_label_by_type = {}
    for a in arts:
        media_label_by_type.setdefault(a["mediaType"], a["mediaLabel"])
    present_pillars = {a["pillar"] for a in arts}
    present_media = {a["mediaType"] for a in arts}
    present_cats = {a["category"] for a in arts}

    def chip_row(group, items, active_value):
        out = []
        for v, label in items:
            cls = "fchip active" if v == active_value else "fchip"
            out.append(
                f'<button type="button" class="{cls}" data-filter-group="{group}" '
                f'data-filter-value="{esc(v)}">{esc(label)}</button>'
            )
        return "".join(out)

    pillar_items = [("", "すべて")] + [
        (p, PILLAR_LABELS[p]) for p in FILTER_PILLAR_ORDER if p in present_pillars
    ]
    media_items = [("", "すべて")] + [
        (m, media_label_by_type.get(m, m)) for m in FILTER_MEDIA_ORDER if m in present_media
    ]
    cat_items = [("", "すべて")] + [
        (c, c) for c in FILTER_CATEGORY_ORDER if c in present_cats
    ] + [(c, c) for c in sorted(present_cats) if c not in FILTER_CATEGORY_ORDER]
    initial_count = sum(1 for a in arts if a["pillar"] == "stats")
    filterbar = f"""
<div class="filterbar" id="filterbar">
  <div class="fgroup"><span class="flabel">柱</span><div class="fchips">{chip_row('pillar', pillar_items, 'stats')}</div></div>
  <div class="fgroup"><span class="flabel">メディア</span><div class="fchips">{chip_row('media', media_items, '')}</div></div>
  <div class="fgroup"><span class="flabel">カテゴリ</span><div class="fchips">{chip_row('category', cat_items, '')}</div></div>
  <div class="frow">
    <input type="search" class="fsearch" id="fsearch" placeholder="キーワードで絞り込む（タイトル・要約・タグ）" aria-label="キーワード検索">
    <p class="fcount"><span class="n" id="fcount-num">{initial_count}</span>件を表示中</p>
    <button type="button" class="freset" id="freset">リセット</button>
  </div>
</div>"""

    # --- 記事フィード（単一フィード＋クライアントサイド・フィルター） ---
    cards = []
    for a in arts:
        chips = [
            f'<span class="chip pillar">{esc(PILLAR_LABELS.get(a["pillar"], a["pillar"]))}</span>',
            f'<span class="chip media">{esc(a["mediaLabel"])}</span>',
        ]
        if a.get("category") and a["category"] != "総合":
            chips.append(f'<span class="chip cat">{esc(a["category"])}</span>')
        for t in a.get("tags", []):
            chips.append(f'<span class="chip">{esc(t)}</span>')
        date = a.get("publishedDate") or (a.get("fetchedAt") or "")[:10]
        search_text = esc(" ".join(
            (a["title"] + " " + a["summary"] + " " + " ".join(a.get("tags", []))).lower().split()
        ))
        cards.append(f"""
<article class="artcard" data-pillar="{esc(a['pillar'])}" data-media="{esc(a['mediaType'])}" data-category="{esc(a['category'])}" data-search="{search_text}">
  <h3><a href="{esc(a['sourceUrl'])}" target="_blank" rel="noopener">{esc(a['title'])}</a></h3>
  <p>{esc(a['summary'])}</p>
  <div class="chips">{''.join(chips)}</div>
  <p class="src">{esc(a['sourceName'])}／{esc(date)}</p>
</article>""")
    feed = f"""
<section class="panel">
  <h2>記事フィード（{len(arts)}件）</h2>
  <div id="ffeed">{''.join(cards)}</div>
  <p class="fempty" id="fempty" hidden>条件に合う記事がありません。フィルターやキーワードを変えてお試しください。</p>
</section>"""

    filter_script = """
<script>
(function () {
  var INITIAL = { pillar: "stats", media: "", category: "", q: "" };
  var state = { pillar: INITIAL.pillar, media: INITIAL.media, category: INITIAL.category, q: INITIAL.q };
  var cards = Array.prototype.slice.call(document.querySelectorAll(".artcard[data-pillar]"));
  var countEl = document.getElementById("fcount-num");
  var emptyEl = document.getElementById("fempty");
  function apply() {
    var n = 0;
    for (var i = 0; i < cards.length; i++) {
      var c = cards[i];
      var ok = (!state.pillar || c.getAttribute("data-pillar") === state.pillar)
        && (!state.media || c.getAttribute("data-media") === state.media)
        && (!state.category || c.getAttribute("data-category") === state.category)
        && (!state.q || (c.getAttribute("data-search") || "").indexOf(state.q) !== -1);
      c.style.display = ok ? "" : "none";
      if (ok) n++;
    }
    if (countEl) countEl.textContent = n;
    if (emptyEl) emptyEl.hidden = n !== 0;
  }
  function syncChips() {
    var chips = document.querySelectorAll(".fchip");
    for (var i = 0; i < chips.length; i++) {
      var g = chips[i].getAttribute("data-filter-group");
      chips[i].classList.toggle("active", chips[i].getAttribute("data-filter-value") === state[g]);
    }
  }
  var allChips = document.querySelectorAll(".fchip");
  for (var j = 0; j < allChips.length; j++) {
    allChips[j].addEventListener("click", function () {
      state[this.getAttribute("data-filter-group")] = this.getAttribute("data-filter-value");
      syncChips();
      apply();
    });
  }
  var input = document.getElementById("fsearch");
  if (input) {
    input.addEventListener("input", function () {
      state.q = input.value.trim().toLowerCase();
      apply();
    });
  }
  var reset = document.getElementById("freset");
  if (reset) {
    reset.addEventListener("click", function () {
      state = { pillar: INITIAL.pillar, media: INITIAL.media, category: INITIAL.category, q: INITIAL.q };
      if (input) input.value = "";
      syncChips();
      apply();
    });
  }
  syncChips();
  apply();
})();
</script>"""

    body = f"""
<header class="site-head"><div class="wrap">
  <h1>マーケティング最新情報</h1>
  <p>マーケティングスペース「マーケティング最新情報」のミラー：今の見立て、注目レポート、収録記事フィード。</p>
</div></header>
<div class="wrap">
{filterbar}
{mitate}
{featured}
{summary_panel}
{feed}
</div>
{filter_script}"""
    return page_shell("マーケティング最新情報 | SNS FIELD NOTES", body, depth=1, section="marketing")


PHASE_CLASSES = {
    "芽生え": "phase-sprout",
    "拡大中": "phase-growing",
    "定着": "phase-settled",
    "冷静化": "phase-cooling",
    "観測中": "phase-watching",
}


def build_communities(cm):
    cats = cm.get("categories", [])
    active = [c for c in cats if c.get("entries")]
    total_entries = sum(len(c.get("entries", [])) for c in cats)

    cards = []
    for c in cats:
        phase = c.get("phase", "観測中")
        phase_cls = PHASE_CLASSES.get(phase, "phase-watching")
        mech = ""
        if c.get("mechanics"):
            mech = f'<p class="mech"><span class="mech-lbl">ハマり方・コミュニティの型</span>{esc(c["mechanics"])}</p>'
        entries = sorted(c.get("entries", []), key=lambda e: e["date"], reverse=True)
        if entries:
            rows = "".join(
                f'<li><span class="d">{esc(e["date"])}</span><span class="nt">{esc(e["note"])}</span></li>'
                for e in entries
            )
            entries_html = f'<ul class="timeline">{rows}</ul>'
        else:
            entries_html = '<p class="comm-empty">まだ目立った動きなし</p>'
        cards.append(f"""
<article class="comm-card">
  <div class="comm-head"><h3>{esc(c['name'])}</h3><span class="phase-badge {phase_cls}">{esc(phase)}</span></div>
  <p class="scope">{esc(c['scope'])}</p>
  {mech}
  {entries_html}
</article>""")

    body = f"""
<header class="site-head"><div class="wrap">
  <h1>界隈マップ</h1>
  <p>SNS観測で拾った話題を、大きな界隈カテゴリごとに定点観測するページ。</p>
</div></header>
<div class="wrap">
<section class="panel">
  <h2>このページについて</h2>
  <p>個別の話題の細部ではなく、「物がどうハマっていくか（広がり方の型）」と「コミュニティがどう作られていくか」を、界隈カテゴリごとに追いかけます。日々の観測で目立った動きがあったカテゴリに、その日の記録と型の気づきを足していきます。本格的にリサーチしたい界隈が出てきたときに、ここからすぐ振り返れるようにするための台帳です。</p>
  <p class="meta-line">カテゴリ：{len(cats)}／動きを記録したカテゴリ：{len(active)}／記録件数：{total_entries}件／最終更新：{esc(cm.get('updatedAt', ''))}</p>
</section>
<div class="comm-grid">{''.join(cards)}</div>
</div>"""
    return page_shell("界隈マップ | SNS FIELD NOTES", body, depth=1, section="communities")


def build_companies(cp):
    sectors = cp.get("sectors", [])
    active = [s for s in sectors if s.get("entries")]
    total_entries = sum(len(s.get("entries", [])) for s in sectors)

    cards = []
    for s in sectors:
        watch = ""
        if s.get("watchPoints"):
            watch = f'<p class="watch"><span class="watch-lbl">追う観点</span>{esc(s["watchPoints"])}</p>'
        entries = sorted(s.get("entries", []), key=lambda e: e["date"], reverse=True)
        if entries:
            rows = []
            for e in entries:
                ttl = esc(e["title"])
                if e.get("sourceUrl"):
                    ttl = f'<a href="{esc(e["sourceUrl"])}" target="_blank" rel="noopener">{ttl}</a>'
                src = f'<span class="src">出典：{esc(e["sourceName"])}</span>' if e.get("sourceName") else ""
                rows.append(
                    f'<li><span class="d">{esc(e["date"])}</span>'
                    f'<span class="ttl">{ttl}</span>{src}</li>'
                )
            entries_html = f'<ul class="comp-entries">{"".join(rows)}</ul>'
        else:
            entries_html = '<p class="comp-empty">まだ記録なし</p>'
        cards.append(f"""
<article class="comp-card">
  <h3>{esc(s['name'])}</h3>
  <p class="scope">{esc(s['scope'])}</p>
  {watch}
  {entries_html}
</article>""")

    body = f"""
<header class="site-head"><div class="wrap">
  <h1>企業・業界マップ</h1>
  <p>企業同士の関係の変化を、セクターごとに定点観測するページ。</p>
</div></header>
<div class="wrap">
<section class="panel">
  <h2>このページについて</h2>
  <p>提携・協業・出資・買収・人材移動・共同キャンペーン・サービス連携など、企業同士の関係の変化をセクター別に追いかけます。個別のニュースの細部ではなく、業界の中でどの企業とどの企業が結びつき、離れていくのかというエコシステムの動きを、出典つきで時系列に記録します。</p>
  <p class="meta-line">セクター：{len(sectors)}／記録のあるセクター：{len(active)}／記録件数：{total_entries}件／最終更新：{esc(cp.get('updatedAt', ''))}</p>
</section>
<div class="comp-grid">{''.join(cards)}</div>
</div>"""
    return page_shell("企業・業界マップ | SNS FIELD NOTES", body, depth=1, section="companies")


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    days = sorted(data["days"], key=lambda x: x["date"])

    os.makedirs(os.path.join(SITE_DIR, "assets"), exist_ok=True)
    os.makedirs(os.path.join(SITE_DIR, "days"), exist_ok=True)

    with open(os.path.join(SITE_DIR, "assets", "style.css"), "w", encoding="utf-8") as f:
        f.write(CSS)

    # カバー画像があれば docs/assets/covers/ へコピーする（無くても落ちない）
    copied = []
    for d in days:
        src = os.path.join(COVERS_DIR, d["date"] + ".jpg")
        if os.path.isfile(src):
            dst_dir = os.path.join(SITE_DIR, "assets", "covers")
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copyfile(src, os.path.join(dst_dir, d["date"] + ".jpg"))
            copied.append(d["date"])

    with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_index(data, days))

    for i, d in enumerate(days):
        path = os.path.join(SITE_DIR, "days", d["date"] + ".html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_day(data, d, i, days))

    # マーケティングセクション（data/marketing.json があれば生成する）
    mkt_msg = "marketing: skipped (data/marketing.json なし)"
    if os.path.isfile(MARKETING_PATH):
        with open(MARKETING_PATH, encoding="utf-8") as f:
            mk = json.load(f)
        os.makedirs(os.path.join(SITE_DIR, "marketing"), exist_ok=True)
        with open(os.path.join(SITE_DIR, "marketing", "index.html"), "w", encoding="utf-8") as f:
            f.write(build_marketing(mk))
        mkt_msg = f"marketing: built ({len(mk['articles'])} articles, {len(mk.get('featured', []))} featured)"

    # 界隈マップ（data/communities.json があれば生成する）
    comm_msg = "communities: skipped (data/communities.json なし)"
    if os.path.isfile(COMMUNITIES_PATH):
        with open(COMMUNITIES_PATH, encoding="utf-8") as f:
            cm = json.load(f)
        os.makedirs(os.path.join(SITE_DIR, "communities"), exist_ok=True)
        with open(os.path.join(SITE_DIR, "communities", "index.html"), "w", encoding="utf-8") as f:
            f.write(build_communities(cm))
        comm_msg = f"communities: built ({len(cm.get('categories', []))} categories)"

    # 企業・業界マップ（data/companies.json があれば生成する）
    comp_msg = "companies: skipped (data/companies.json なし)"
    if os.path.isfile(COMPANIES_PATH):
        with open(COMPANIES_PATH, encoding="utf-8") as f:
            cp = json.load(f)
        os.makedirs(os.path.join(SITE_DIR, "companies"), exist_ok=True)
        with open(os.path.join(SITE_DIR, "companies", "index.html"), "w", encoding="utf-8") as f:
            f.write(build_companies(cp))
        comp_msg = f"companies: built ({len(cp.get('sectors', []))} sectors)"

    print(f"built: index.html + {len(days)} day pages; covers copied: {copied or 'none'}; {mkt_msg}; {comm_msg}; {comp_msg}")


if __name__ == "__main__":
    main()
