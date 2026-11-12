# ====================================================================
#  Khmer Video AI — Hongguo ONLY
#  កំណែនេះមានតែផ្នែក Hongguo: ស្វែងរករឿង · ប្រភេទ · មើលភាគ · ទាញយក ZIP · យកតំណផ្ទាល់ច្រើនភាគ
# ====================================================================
import os
import io
import re
import json
import time
import hmac
import base64
import shutil
import hashlib
import secrets
import zipfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from html import escape as _esc
from concurrent.futures import ThreadPoolExecutor

import threading
from datetime import datetime, timezone, timedelta

import requests
import streamlit as st
import streamlit.components.v1 as components

# ---- កត់ត្រាកំហុសដែលធ្លាប់ត្រូវបានលាក់ ----
_SWALLOW_SEEN = {}


def _log_swallowed(err):
    try:
        import sys as _sys
        _key = (type(err).__name__, str(err)[:80])
        _SWALLOW_SEEN[_key] = _SWALLOW_SEEN.get(_key, 0) + 1
        if _SWALLOW_SEEN[_key] <= 2:
            print(f"[KVAI warn] {type(err).__name__}: {str(err)[:200]}", file=_sys.stderr, flush=True)
    except Exception:
        pass


st.set_page_config(page_title="Hongguo — Khmer Video AI", page_icon="🍎", layout="wide")

import re as _re_hd
_orig_st_markdown = st.markdown
_HD_SIZES = {1: 1.7, 2: 1.45, 3: 1.25, 4: 1.1, 5: 1.0, 6: 0.95}


def _no_heading_markdown(body, *args, **kwargs):
    try:
        if isinstance(body, str) and "<style" not in body and _re_hd.search(r"(?m)^\s{0,3}#{1,6}\s+\S", body):
            def _sub(m):
                lvl = len(m.group(1))
                txt = m.group(2).strip()
                return (f'<span style="font-size:{_HD_SIZES[lvl]}em;font-weight:700;line-height:1.6;display:inline-block;margin:.35em 0">'
                        f'{txt}</span>\n')
            body = _re_hd.sub(r"(?m)^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", _sub, body)
            kwargs["unsafe_allow_html"] = True
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)
    return _orig_st_markdown(body, *args, **kwargs)


st.markdown = _no_heading_markdown


def _no_heading_subheader(body, *args, **kwargs):
    _no_heading_markdown(f"### {body}")


st.subheader = _no_heading_subheader



def get_secret(name, default=""):
    val = os.environ.get(name)
    if val:
        return val
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")

try:
    ST_VER = tuple(int(x) for x in re.findall(r"\d+", st.__version__)[:2])
except Exception:
    ST_VER = (1, 0)

MAX_ZIP_MB = 600
MAX_DOWNLOAD_MB = 200000
LINK_RETRIES = 4


def safe_filename(name):
    base = os.path.splitext(str(name))[0]
    base = re.sub(r"[^\w\-]+", "_", base).strip("_")[:40]
    return base or "video"


def split_keys(value):
    if isinstance(value, (list, tuple)):
        value = "\n".join("\n".join(split_keys(v)) for v in value)
    out = []
    for k in re.split(r"[\s,;]+", str(value or "")):
        k = k.strip().strip("[]()").strip('"').strip("'")
        if k and k not in out:
            out.append(k)
    return out


def _google_once(text):
    query = urllib.parse.urlencode({"client": "gtx", "sl": "auto", "tl": "km", "dt": "t"})
    url = "https://translate.googleapis.com/translate_a/single?" + query
    body = urllib.parse.urlencode({"q": text}).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        data = json.loads(response.read().decode("utf-8"))
    return "".join(part[0] for part in (data[0] or []) if part and part[0])


def google_translate_request(text, retries=3):
    for attempt in range(retries):
        try:
            return _google_once(text)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise


def dl_button(label, data, file_name, mime, key, **kwargs):
    if ST_VER >= (1, 43):
        return st.download_button(label, data=data, file_name=file_name, mime=mime, key=key, on_click="ignore", **kwargs)
    return st.download_button(label, data=data, file_name=file_name, mime=mime, key=key, **kwargs)


def _fetch_one(url, on_try=None):
    """ទាញវីដេអូមួយតំណមក temp folder (ព្យាយាមម្តងទៀតដោយស្វ័យប្រវត្តិ)។"""
    last = ""
    limit = MAX_DOWNLOAD_MB * 1024 * 1024
    for attempt in range(1, LINK_RETRIES + 1):
        folder = tempfile.mkdtemp(prefix="hongguo_batch_")
        path = os.path.join(folder, "video.mp4")
        try:
            req = urllib.request.Request(str(url).strip(), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                ctype = (resp.headers.get("Content-Type") or "").lower()
                if "text/html" in ctype:
                    raise RuntimeError("តំណនេះជាទំព័រគេហទំព័រ មិនមែនវីដេអូ")
                done = 0
                with open(path, "wb") as f:
                    while True:
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if done > limit:
                            raise RuntimeError("វីដេអូធំពេក")
            if os.path.getsize(path) < 1000:
                raise RuntimeError("ឯកសារតូចពេក / ទាញមិនបាន")
            return {"path": path, "ok": True, "tries": attempt}
        except Exception as e:
            shutil.rmtree(folder, ignore_errors=True)
            last = re.sub(r"https?://\S+", "[link]", str(e) or type(e).__name__)[:300]
            if attempt < LINK_RETRIES:
                time.sleep(min(2 * attempt, 8))
    return {"path": None, "ok": False, "err": last, "tries": LINK_RETRIES}


# ---- Key ផ្ទាល់ខ្លួន: រក្សាទុកក្នុង folder User របស់កុំព្យូទ័រនេះ ----
_HG_KEY_FILE = os.path.join(os.path.expanduser("~"), ".khmervideoai_hongguo.json")


def _hg_load_keys():
    try:
        with open(_HG_KEY_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return str(d.get("app_id") or "").strip(), str(d.get("app_secret") or "").strip()
    except Exception:
        return "", ""


def _hg_save_keys(app_id, app_secret):
    app_id = str(app_id or "").strip()
    app_secret = str(app_secret or "").strip()
    st.session_state["user_hg_app_id"] = app_id
    st.session_state["user_hg_app_secret"] = app_secret
    try:
        if app_id or app_secret:
            with open(_HG_KEY_FILE, "w", encoding="utf-8") as f:
                json.dump({"app_id": app_id, "app_secret": app_secret}, f)
        elif os.path.exists(_HG_KEY_FILE):
            os.remove(_HG_KEY_FILE)
    except Exception as _e:
        _log_swallowed(_e)
    for _name in ("_hg_category_tree", "_hg_rank_all", "_hg_rank", "_hg_categories", "_hg_category_all", "_hg_search", "_hg_detail"):
        _fn = globals().get(_name)
        try:
            if _fn is not None and hasattr(_fn, "clear"):
                _fn.clear()
        except Exception as _e:
            _log_swallowed(_e)
    st.session_state.pop("_hg_good_prefix", None)
    st.session_state["_hg_rows"] = []
    st.session_state.pop("_hg_selected", None)


_saved_id, _saved_secret = _hg_load_keys()
if _saved_id and not st.session_state.get("user_hg_app_id"):
    st.session_state["user_hg_app_id"] = _saved_id
if _saved_secret and not st.session_state.get("user_hg_app_secret"):
    st.session_state["user_hg_app_secret"] = _saved_secret



THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Kantumruy+Pro:wght@400;500;600;700;800&family=Battambang:wght@400;700&family=Noto+Sans+Khmer:wght@400;500;600;700;800&display=swap');

:root {
  --ink: #1F2A44;
  --soft: #55627F;
  --bg: #F4F7FF;
  --card: #FFFFFF;
  --card2: #F1F5FF;
  --line: rgba(80,100,190,.25);
  --p1: #7C3AED;
  --p2: #2563EB;
  --gold: #B45309;
  --r-lg: 20px;
  --r-md: 14px;
  --r-sm: 12px;
}

#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
.stDeployButton, [data-testid="stStatusWidget"], [class*="viewerBadge"],
[data-testid="manage-app-button"] { display: none !important; }

html, body, .stApp, [data-testid="stAppViewContainer"] {
  background: radial-gradient(900px 480px at 15% -8%, #E4DCFF 0%, rgba(244,247,255,0) 60%), #F4F7FF !important;
  color: var(--ink);
  font-family: 'Kantumruy Pro', 'Noto Sans Khmer', 'Battambang', system-ui, sans-serif !important;
  color-scheme: light;
}
.stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp li, .stApp small,
.stApp textarea, .stApp input, .stApp button p, .stApp a,
.stApp [data-baseweb="select"] div, .stApp [data-testid="stMarkdownContainer"] {
  font-family: 'Kantumruy Pro', 'Battambang', system-ui, sans-serif;
}
[data-testid="stIconMaterial"], [class*="material-symbols"], .material-icons {
  font-family: 'Material Symbols Rounded', 'Material Icons' !important;
}
[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1240px; padding: 1rem 1.2rem 4rem; }

.stMarkdown, .stMarkdown p, [data-testid="stText"], h1, h2, h3,
label, [data-testid="stWidgetLabel"] p, [data-testid="stCheckbox"] p,
[data-testid="stToggle"] p {
  color: var(--ink) !important;
}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--soft) !important; }

/* ---------- Header ---------- */
.kvai-head { display: flex; align-items: center; gap: 14px; margin: 4px 0 16px; flex-wrap: wrap; }
.kvai-logo {
  width: 54px; height: 54px; border-radius: 16px;
  background: linear-gradient(135deg, #3C6BFF, #B13CFF);
  display: flex; align-items: center; justify-content: center; font-size: 28px;
  box-shadow: 0 8px 22px rgba(60,107,255,.45);
}
.kvai-title { flex: 1; min-width: 190px; }
.kvai-title .kvai-h1 {
  margin: 0 !important; padding: 0 !important;
  font-size: clamp(1.5rem, 6vw, 2rem) !important;
  font-weight: 800 !important; line-height: 1.2 !important; color: var(--ink) !important;
}
.kvai-title .kvai-h1 span {
  background: linear-gradient(90deg, #B13CFF, #3C6BFF);
  -webkit-background-clip: text; background-clip: text;
  color: transparent !important; -webkit-text-fill-color: transparent;
}
.kvai-title p { margin: 2px 0 0; color: var(--soft) !important; font-size: .9rem; }
.kvai-badge {
  border: 1.5px solid var(--p2); color: var(--gold) !important;
  padding: 8px 14px; border-radius: 999px; font-weight: 700; font-size: .9rem;
  background: rgba(60,107,255,.12);
}

/* ---------- Nav ---------- */
.kvai-nav {
  display: flex; gap: 4px; padding: 4px; margin-bottom: 8px; overflow-x: auto;
  background: var(--card); border: 1px solid var(--line); border-radius: 16px;
}
.kvai-nav a {
  flex: 1; text-align: center; padding: 11px 14px; border-radius: 12px; white-space: nowrap;
  color: var(--soft) !important; text-decoration: none !important; font-weight: 600;
}
.kvai-nav a.on { background: linear-gradient(135deg, var(--p1), var(--p2)); color: #fff !important; }
.kvai-nav a:hover { color: var(--ink) !important; }

/* ---------- Tabs ---------- */
[data-baseweb="tab-list"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 16px; padding: 4px; gap: 2px;
}
button[data-baseweb="tab"] {
  flex: 1; height: 46px; border-radius: 12px;
  background: transparent !important; color: var(--soft) !important;
}
button[data-baseweb="tab"] [data-testid="stMarkdownContainer"] p { color: inherit !important; font-weight: 600; }
button[data-baseweb="tab"][aria-selected="true"] {
  background: linear-gradient(135deg, var(--p1), var(--p2)) !important;
  color: #fff !important;
}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }

/* ---------- Section headings ---------- */
[data-testid="stHeading"] h3, .stApp h3 {
  font-size: 1.1rem !important; font-weight: 600 !important;
  margin: 1.4rem 0 .6rem !important; padding: 0 !important; border: none !important;
}
[data-testid="stHeading"] h3::after {
  content: ""; display: block; width: 34px; height: 4px; border-radius: 4px;
  background: linear-gradient(90deg, var(--p1), var(--p2)); margin-top: 6px;
}

/* ---------- Cards ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(255,255,255,.94) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--r-lg) !important;
  box-shadow: 0 6px 22px rgba(70,90,170,.14);
  padding: 6px 4px;
}
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlockBorderWrapper"] {
  box-shadow: none; background: #F7F9FF !important;
}

/* ---------- Select ---------- */
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-baseweb="select"] > div {
  background-color: var(--card2) !important;
  border: 1.5px solid var(--line) !important;
  border-radius: var(--r-sm) !important;
  color: var(--ink) !important;
  min-height: 48px;
}
[data-baseweb="select"] > div:focus-within, [data-baseweb="select"] > div:hover {
  border-color: var(--p2) !important;
  box-shadow: 0 0 0 3px rgba(60,107,255,.2) !important;
}
[data-baseweb="select"] * { color: var(--ink) !important; }
[data-baseweb="select"] svg { fill: var(--ink) !important; }
[data-baseweb="popover"] ul, [data-baseweb="popover"] li, [data-baseweb="menu"] {
  background: #FFFFFF !important; color: var(--ink) !important;
}
[data-baseweb="popover"] li:hover { background: rgba(124,58,237,.12) !important; }
/* បង្ហាញឈ្មោះប្រភេទពេញ មិនកាត់ជាសញ្ញា ... លើទូរស័ព្ទ */
[data-baseweb="popover"] [role="option"],
[data-baseweb="menu"] [role="option"] {
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  line-height: 1.55 !important;
  min-height: 44px !important;
  height: auto !important;
  align-items: center !important;
}
[data-baseweb="popover"] [role="option"] > div,
[data-baseweb="menu"] [role="option"] > div {
  white-space: normal !important;
  overflow-wrap: anywhere !important;
  text-overflow: clip !important;
}

/* ---------- Text area ---------- */
.stTextArea textarea, [data-baseweb="textarea"], [data-baseweb="textarea"] > div {
  background: var(--card2) !important;
  border: 1.5px solid var(--line) !important;
  border-radius: var(--r-sm) !important;
  color: var(--ink) !important;
}
.stTextArea textarea:focus { border-color: var(--p2) !important; box-shadow: 0 0 0 3px rgba(60,107,255,.2) !important; }

/* ---------- Radio => pills ---------- */
[data-testid="stRadio"] [role="radiogroup"] { gap: 8px; flex-wrap: wrap; width: 100%; }
[data-testid="stRadio"] label {
  flex: 1 1 auto;
  justify-content: center;
  background: var(--card2);
  border: 1.5px solid var(--line);
  border-radius: 999px;
  padding: 8px 14px !important;
  margin: 0 !important;
  cursor: pointer;
}
[data-testid="stRadio"] label > div:first-child { display: none !important; }
[data-testid="stRadio"] label:has(input:checked) {
  background: linear-gradient(135deg, var(--p1), var(--p2));
  border-color: transparent;
  box-shadow: 0 4px 14px rgba(60,107,255,.35);
}
[data-testid="stRadio"] label:has(input:checked) *,
[data-testid="stRadio"] label:has(input:checked) p { color: #fff !important; }
.st-key-pos [role="radiogroup"] {
  display: grid !important; grid-template-columns: repeat(3, 1fr); max-width: 260px;
}

/* ---------- Checkbox / Toggle ---------- */
[data-testid="stCheckbox"] label > span:first-child,
[data-baseweb="checkbox"] > span:first-child {
  border-radius: 7px !important;
  border: 1.5px solid #8C97C8 !important;
  background-color: var(--card2) !important;
}
[data-testid="stCheckbox"] label:has(input:checked) > span:first-child,
[data-baseweb="checkbox"]:has(input:checked) > span:first-child {
  background: linear-gradient(135deg, var(--p1), var(--p2)) !important;
  border-color: transparent !important;
}
[data-testid="stToggle"] label > div:first-child { background: #C3CBE6 !important; }
[data-testid="stToggle"] label:has(input:checked) > div:first-child {
  background: linear-gradient(90deg, var(--p1), var(--p2)) !important;
}

/* ---------- Slider ---------- */
[data-testid="stSlider"] [role="slider"] { background: #fff !important; border-color: var(--p1) !important; }
[data-testid="stSlider"] [data-testid="stThumbValue"] { color: var(--ink) !important; }
[data-testid="stSlider"] [data-testid="stTickBarMin"], [data-testid="stSlider"] [data-testid="stTickBarMax"] { color: var(--soft) !important; }

/* ---------- Uploader ---------- */
[data-testid="stFileUploaderDropzone"] {
  background: rgba(124,58,237,.06);
  border: 2px dashed var(--p2);
  border-radius: var(--r-lg);
  padding: 22px 16px;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--p1); background: rgba(124,58,237,.12); }
[data-testid="stFileUploaderDropzone"] * { color: var(--ink) !important; }
[data-testid="stFileUploaderDropzoneInstructions"] small,
[data-testid="stFileUploaderDropzoneInstructions"] span + span,
[data-testid="stFileUploaderDropzoneInstructions"] div > span:nth-of-type(2) { display: none !important; }
[data-testid="stFileUploaderDropzone"] button {
  background: linear-gradient(135deg, var(--p1), var(--p2)) !important; color: #fff !important;
  border-radius: var(--r-sm) !important; border: none !important;
}
[data-testid="stFileUploaderDropzone"] button * { color: #fff !important; }
[data-testid="stFileUploaderFile"] * { color: var(--ink) !important; }

/* ---------- Buttons ---------- */
.stButton > button, .stDownloadButton > button {
  border-radius: var(--r-md);
  border: 1.5px solid var(--line);
  background: var(--card);
  color: var(--ink);
  font-weight: 700;
  min-height: 50px;
  transition: transform .12s ease, box-shadow .12s ease;
}
.stButton > button *, .stDownloadButton > button * { color: inherit !important; }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
  background: linear-gradient(90deg, var(--p1), var(--p2)) !important;
  border: none !important;
  color: #fff !important;
  min-height: 58px;
  font-size: 1.08rem;
  box-shadow: 0 10px 26px rgba(120,60,255,.4);
}
.stButton > button[kind="primary"] *, .stDownloadButton > button[kind="primary"] * { color: #fff !important; }
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); border-color: var(--p2); }
.stButton > button:focus-visible { outline: 3px solid var(--gold); outline-offset: 2px; }
.stButton > button:disabled { background: #E3E8F5 !important; color: #7A85A6 !important; box-shadow: none; transform: none; }

/* ---------- Progress ---------- */
[data-testid="stProgress"] > div > div { background: #E3E8F5 !important; border-radius: 999px; }
[data-testid="stProgress"] > div > div > div { background: linear-gradient(90deg, var(--p1), var(--p2)) !important; border-radius: 999px; }

/* ---------- Metrics ---------- */
[data-testid="stMetric"] {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  padding: 12px 14px;
}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * { font-weight: 800; color: var(--ink) !important; }
[data-testid="stMetricLabel"] p { color: var(--soft) !important; font-weight: 500; }

/* ---------- Alerts ---------- */
[data-testid="stAlert"] { border-radius: var(--r-md); border: none; }
[data-testid="stAlert"] * { color: var(--ink) !important; }

/* ---------- Expander ---------- */
[data-testid="stExpander"] {
  background: #FFFFFF;
  border: 1.5px solid var(--line) !important;
  border-radius: var(--r-md);
}
[data-testid="stExpander"] * { color: var(--ink) !important; }

[data-testid="stVideo"] video { border-radius: var(--r-md); background: #000; }
hr { border-color: var(--line) !important; margin: 1.6rem 0 !important; }

/* ---------- Subtitle preview ---------- */
.kvai-prev {
  height: 300px; border-radius: 16px; border: 1px solid var(--line);
  background: linear-gradient(160deg, #3A2C6E 0%, #1B2A5E 60%, #0E1636 100%);
  display: flex; padding: 14px 18px; margin: 6px 0 10px;
}
.kvai-prev span {
  font-family: 'Battambang', 'Kantumruy Pro', sans-serif;
  padding: 3px 10px; border-radius: 6px; line-height: 1.5;
}

/* ---------- Light theme extras: input / code / placeholder ---------- */
.stTextInput input, .stNumberInput input, [data-baseweb="input"], [data-baseweb="input"] > div,
[data-baseweb="base-input"] {
  background: var(--card2) !important; color: var(--ink) !important;
  border-color: var(--line) !important; border-radius: var(--r-sm) !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #7A85A6 !important; opacity: 1; }
[data-testid="stCodeBlock"] pre, .stCode pre { background: #EEF2FF !important; }
[data-testid="stCodeBlock"] code, .stCode code { color: #1F2A44 !important; }
[data-testid="stFileUploaderDropzone"] { background: rgba(124,58,237,.06) !important; }
</style>
"""

COMPACT_CSS = """
<style>
.block-container { padding: .6rem .8rem 5.5rem !important; }
[data-testid="stVerticalBlock"] { gap: .55rem; }

/* header តូច */
.kvai-head { margin: 0 0 8px; gap: 10px; flex-wrap: nowrap; }
.kvai-logo { width: 42px; height: 42px; font-size: 22px; border-radius: 13px; }
.kvai-title { min-width: 0; }
.kvai-title .kvai-h1 { font-size: 1.35rem !important; }
.kvai-title p { font-size: .75rem; margin: 0; }
.kvai-badge { padding: 5px 10px; font-size: .75rem; white-space: nowrap; }

/* tabs */
[data-baseweb="tab-list"] { overflow-x: auto; }
button[data-baseweb="tab"] { height: 40px; padding: 0 4px !important; min-width: 0; }
button[data-baseweb="tab"] p { font-size: .8rem !important; white-space: nowrap; }

/* ជួរឈរមិនបត់ចុះក្រោមលើទូរស័ព្ទ */
[data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .6rem !important; }
[data-testid="stColumn"] { min-width: 0 !important; }

/* សមាសភាគតូចជាង */
[data-testid="stWidgetLabel"] p { font-size: .85rem; }
[data-testid="stSelectbox"] [data-baseweb="select"] > div { min-height: 42px; }
[data-testid="stRadio"] label { padding: 5px 10px !important; font-size: .85rem; }
[data-testid="stFileUploaderDropzone"] { padding: 10px; }
[data-testid="stVideo"] video { max-height: 150px; }
div[data-testid="stVerticalBlockBorderWrapper"] { padding: 4px 2px; }
.kvai-prev { height: 120px; padding: 8px 12px; margin: 0; }
.st-key-pos [role="radiogroup"] { max-width: 100%; }

/* ប៊ូតុងចាប់ផ្តើមជាប់ខាងក្រោម */
.st-key-startbar {
  position: fixed; bottom: 0; left: 50%; transform: translateX(-50%);
  width: min(100%, 1240px); z-index: 999;
  padding: 18px 12px calc(10px + env(safe-area-inset-bottom));
  background: linear-gradient(180deg, rgba(244,247,255,0), #F4F7FF 35%);
}
.st-key-startbar .stButton > button { min-height: 52px; }
</style>
"""


def apply_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    st.markdown(COMPACT_CSS, unsafe_allow_html=True)


LANDSCAPE_NEON_CSS = """
<style>
:root{--ink:#F5F7FF;--soft:#B9C7F5;--bg:#070B22;--card:#10183D;--card2:#151F4B;--line:rgba(91,184,255,.42);--p1:#FF2DAA;--p2:#16CFFF;--gold:#FFD34E}
html,body,.stApp,[data-testid="stAppViewContainer"]{background:radial-gradient(ellipse at 8% 5%,rgba(255,34,170,.23),transparent 34%),radial-gradient(ellipse at 92% 8%,rgba(0,213,255,.22),transparent 34%),linear-gradient(135deg,#05091D,#10143B 48%,#080D29)!important;color:#F5F7FF!important}
.stApp:before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background:linear-gradient(110deg,transparent,rgba(20,210,255,.04),transparent);background-size:220% 100%;animation:kvai-light-run 8s linear infinite}
@keyframes kvai-light-run{from{background-position:200% 0}to{background-position:-20% 0}}
.block-container{max-width:1600px!important;padding:.5rem .8rem 5rem!important;position:relative;z-index:1}
.stApp p,.stApp label,.stApp h1,.stApp h2,.stApp h3,.stApp li,.stApp [data-testid="stMarkdownContainer"],[data-testid="stWidgetLabel"] p{color:#F5F7FF!important}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:#B9C7F5!important}
.kvai-head{padding:8px 13px;border:1px solid rgba(65,195,255,.45);border-radius:18px;background:linear-gradient(105deg,rgba(255,45,170,.2),rgba(14,26,72,.94),rgba(22,207,255,.17));box-shadow:0 0 22px rgba(22,207,255,.15)}
.kvai-logo{background:linear-gradient(135deg,#FF2DAA,#7B42FF,#16CFFF)!important;box-shadow:0 0 22px rgba(255,45,170,.5)!important}
.kvai-title .kvai-h1{color:white!important;text-shadow:0 0 16px rgba(22,207,255,.5)}
.kvai-title .kvai-h1 span{background:linear-gradient(90deg,#FF55C8,#43E7FF,#FFE36A);-webkit-background-clip:text;background-clip:text;color:transparent!important}
.kvai-badge{color:#FFE36A!important;background:rgba(255,211,78,.12)!important;border-color:#FFD34E!important}
[data-baseweb="tab-list"]{display:flex!important;gap:5px!important;padding:5px!important;background:#080F30!important;border:1px solid rgba(70,190,255,.45)!important}
button[data-baseweb="tab"]{flex:1 1 0!important;min-width:max-content!important;height:43px!important;border:1px solid rgba(120,150,255,.22)!important;border-radius:12px!important;background:linear-gradient(145deg,#18234F,#101735)!important;color:#DCE7FF!important}
button[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(110deg,#F52AA7,#783BFF,#08BFEF)!important;box-shadow:0 0 17px rgba(211,45,255,.42)!important;color:white!important}
button[data-baseweb="tab"] p{color:inherit!important;font-weight:800!important;white-space:nowrap}
div[data-testid="stVerticalBlockBorderWrapper"]{background:linear-gradient(145deg,rgba(23,34,82,.97),rgba(10,17,48,.98))!important;border:1px solid rgba(75,190,255,.38)!important;border-radius:16px!important;box-shadow:0 7px 24px rgba(0,0,0,.22)!important}
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlockBorderWrapper"]{background:rgba(25,36,83,.65)!important}
[data-baseweb="select"]>div,.stTextInput input,.stNumberInput input,.stTextArea textarea,[data-baseweb="textarea"]>div{background:#0C1538!important;color:white!important;border:1px solid #3B8FC8!important}
[data-baseweb="select"] *{color:white!important}
[data-baseweb="popover"] ul,[data-baseweb="popover"] li,[data-baseweb="menu"]{background:#101A43!important;color:white!important}
[data-testid="stFileUploaderDropzone"]{background:rgba(28,50,111,.65)!important;border:2px dashed #20D7FF!important;box-shadow:inset 0 0 20px rgba(22,207,255,.08)}
[data-testid="stFileUploaderDropzone"] *{color:white!important}
.stButton>button,.stDownloadButton>button{background:linear-gradient(145deg,#172451,#101735)!important;color:white!important;border:1px solid rgba(68,204,255,.65)!important;border-radius:12px!important;min-height:44px!important}
.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"]{background:linear-gradient(100deg,#FF279F,#853CFF,#08C8EF)!important;color:white!important;border:0!important;box-shadow:0 0 20px rgba(211,45,255,.38)!important}
.stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-2px);border-color:#FFE36A!important;box-shadow:0 0 17px rgba(22,207,255,.35)!important}
[data-testid="stRadio"] label{background:#111D49!important;border-color:#3C75B5!important;color:white!important}
[data-testid="stRadio"] label:has(input:checked){background:linear-gradient(100deg,#E82CA9,#6745FF)!important}
[data-testid="stToggle"] label:has(input:checked)>div:first-child{background:linear-gradient(90deg,#FF2DAA,#16CFFF)!important}
[data-testid="stProgress"]>div>div>div{background:linear-gradient(90deg,#FF2DAA,#8B42FF,#16CFFF)!important}
[data-testid="stMetric"]{background:#111B43!important;border:1px solid #3C8FC5!important}
[data-testid="stMetricValue"],[data-testid="stMetricValue"] *{color:white!important}
[data-testid="stAlert"],[data-testid="stExpander"]{background:#111A40!important;border:1px solid #3B8FC8!important}
[data-testid="stVideo"] video{max-height:190px}
.kvai-prev{border-color:#27D9FF!important;box-shadow:0 0 20px rgba(22,207,255,.18)}
@media(orientation:landscape) and (max-height:600px){.block-container{padding:.25rem .55rem 4rem!important}.kvai-head{padding:5px 10px;margin-bottom:4px}.kvai-logo{width:34px;height:34px;font-size:19px}.kvai-title .kvai-h1{font-size:1.12rem!important}.kvai-title p,.kvai-badge{font-size:.68rem}button[data-baseweb="tab"]{height:35px!important}[data-testid="stVerticalBlock"]{gap:.35rem!important}div[data-testid="stVerticalBlockBorderWrapper"]{padding:2px!important}[data-testid="stVideo"] video{max-height:115px}.kvai-prev{height:105px!important}.stButton>button,.stDownloadButton>button{min-height:35px!important}}
@media(max-width:700px){[data-baseweb="tab-list"]{overflow-x:auto!important}button[data-baseweb="tab"]{flex:0 0 auto!important;padding:0 9px!important}}
</style>
"""
def apply_neon_theme():
    st.markdown(LANDSCAPE_NEON_CSS, unsafe_allow_html=True)


# ---------- Neon cinematic dashboard polish (Angkor-inspired) ----------
CINEMATIC_DASHBOARD_CSS = """
<style>
:root{--ink:#F7F8FF;--soft:#D3DEFF;--bg:#05091F;--card:#091638;--line:rgba(44,213,255,.62);--p1:#FF1493;--p2:#00D9FF;--gold:#FFD84D}
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:radial-gradient(ellipse at 8% 8%,rgba(255,0,153,.22),transparent 28%),radial-gradient(ellipse at 92% 10%,rgba(0,190,255,.22),transparent 30%),linear-gradient(140deg,#020616,#10113D 50%,#06172E)!important;color:#fff!important}
.block-container{max-width:1800px!important;padding:.25rem .55rem 3.1rem!important}
.stApp p,.stApp label,.stApp h1,.stApp h2,.stApp h3,.stApp li,.stApp [data-testid="stMarkdownContainer"],[data-testid="stWidgetLabel"] p{color:#F7F8FF!important}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:#C4D2FF!important}
.kvai-head{position:relative;isolation:isolate;overflow:hidden;min-height:108px;margin:2px 0 7px!important;padding:12px 18px!important;border:1px solid rgba(42,220,255,.8)!important;border-radius:20px!important;background:linear-gradient(90deg,rgba(2,7,28,.92),rgba(4,15,42,.48) 52%,rgba(2,8,28,.72)),url("data:image/jpeg;base64,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") center 52%/cover no-repeat!important;box-shadow:0 0 25px rgba(0,195,255,.28),inset 0 0 24px rgba(0,195,255,.15)!important}
.kvai-head:before{content:"";position:absolute;z-index:-1;inset:0;background:linear-gradient(105deg,transparent 0%,rgba(255,20,147,.0) 28%,rgba(255,20,147,.52) 36%,transparent 43%,rgba(0,220,255,.5) 58%,transparent 67%);background-size:240% 100%;animation:kvai-light-run 5.5s linear infinite;mix-blend-mode:screen}
.kvai-head:after{content:"";position:absolute;z-index:-1;inset:0;background:repeating-linear-gradient(115deg,transparent 0 65px,rgba(0,220,255,.16) 66px 68px,transparent 69px 135px);background-size:220% 100%;animation:kvai-light-run 9s linear infinite;pointer-events:none}
@keyframes kvai-light-run{from{background-position:220% 0}to{background-position:-20% 0}}
.kvai-logo{background:linear-gradient(135deg,#FF1493,#843BFF,#00D9FF)!important;box-shadow:0 0 24px rgba(255,20,147,.7)!important}
.kvai-title .kvai-h1{color:#fff!important;text-shadow:0 0 16px rgba(0,220,255,.75)!important}
.kvai-title .kvai-h1 span{background:linear-gradient(90deg,#FF65C5,#00E5FF,#FFE36A)!important;-webkit-background-clip:text!important;background-clip:text!important}
.kvai-badge{background:rgba(5,13,39,.7)!important;border:1.5px solid #FFD84D!important;color:#FFE36A!important}
[data-baseweb="tab-list"]{display:flex!important;gap:5px!important;padding:4px!important;background:rgba(5,12,40,.96)!important;border:1px solid rgba(0,210,255,.55)!important;box-shadow:0 0 16px rgba(0,210,255,.16)}
button[data-baseweb="tab"]{flex:1 1 0!important;min-width:max-content!important;height:42px!important;border:1px solid rgba(87,165,255,.4)!important;border-radius:12px!important;background:linear-gradient(145deg,#17234F,#0A1435)!important;color:#EAF3FF!important}
button[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(105deg,#FF1493,#843BFF,#00CFFF)!important;box-shadow:0 0 18px rgba(255,20,147,.55)!important;color:white!important}
button[data-baseweb="tab"] p{color:inherit!important;font-weight:800!important;white-space:nowrap}
[data-baseweb="tab-panel"]{padding-top:.25rem!important}
div[data-testid="stVerticalBlockBorderWrapper"]{background:linear-gradient(145deg,rgba(15,29,75,.97),rgba(6,14,43,.98))!important;border:1px solid rgba(43,201,255,.55)!important;border-radius:15px!important;box-shadow:0 7px 22px rgba(0,0,0,.28),0 0 13px rgba(0,180,255,.1)!important;padding:5px!important}
[data-baseweb="select"]>div,.stTextInput input,.stNumberInput input,.stTextArea textarea,[data-baseweb="textarea"]>div{background:#091638!important;color:#fff!important;border:1px solid #328DC4!important}
[data-baseweb="select"] *{color:#fff!important}
[data-baseweb="popover"] ul,[data-baseweb="popover"] li,[data-baseweb="menu"]{background:#101A43!important;color:white!important}
[data-testid="stFileUploaderDropzone"]{background:linear-gradient(135deg,rgba(0,174,255,.16),rgba(174,30,255,.16))!important;border:2px dashed #00D9FF!important;box-shadow:inset 0 0 22px rgba(0,210,255,.13);padding:10px!important}
[data-testid="stFileUploaderDropzone"] *{color:#fff!important}
.stButton>button,.stDownloadButton>button{background:linear-gradient(145deg,#142451,#0A1538)!important;color:white!important;border:1px solid rgba(0,215,255,.7)!important;box-shadow:0 0 10px rgba(0,180,255,.15);min-height:38px!important}
.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"]{background:linear-gradient(100deg,#FF1493,#853BFF,#00CFFF)!important;box-shadow:0 0 22px rgba(255,20,147,.48)!important}
.stButton>button:hover,.stDownloadButton>button:hover{box-shadow:0 0 22px rgba(0,220,255,.65)!important;border-color:#FFE36A!important;transform:translateY(-1px)}
[data-testid="stRadio"] label{background:#111D49!important;border-color:#328DC4!important;color:#fff!important;padding:5px 8px!important}
[data-testid="stRadio"] label:has(input:checked){background:linear-gradient(100deg,#FF1493,#743DFF)!important}
[data-testid="stMetric"]{background:#101B43!important;border:1px solid #328DC4!important}
[data-testid="stMetricValue"],[data-testid="stMetricValue"] *{color:#fff!important}
[data-testid="stAlert"],[data-testid="stExpander"]{background:#101A40!important;border:1px solid #328DC4!important}
.kvai-panel-title{display:flex;align-items:center;gap:9px;margin:0 0 7px;padding:7px 10px;border:1px solid rgba(0,210,255,.55);border-radius:13px;background:linear-gradient(100deg,rgba(255,20,147,.18),rgba(0,190,255,.16));font-weight:800;font-size:1.08rem;text-shadow:0 0 12px #00cfff}
.kvai-step{width:31px;height:31px;display:inline-flex;align-items:center;justify-content:center;border-radius:50%;font-weight:900;font-size:1rem;color:#fff;box-shadow:0 0 15px currentColor}
.kvai-step.pink{background:linear-gradient(135deg,#ff1493,#813cff)}.kvai-step.blue{background:linear-gradient(135deg,#00cfff,#176bff)}
.kvai-empty-preview{height:265px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;border:1px dashed #00d9ff;border-radius:16px;background:radial-gradient(circle at 50% 45%,rgba(0,200,255,.18),transparent 55%),linear-gradient(145deg,#0a1945,#060d28);text-align:center;color:#fff}
.kvai-empty-preview small{color:#a9c9f5}.kvai-play{width:64px;height:64px;display:grid;place-items:center;border-radius:50%;font-size:27px;background:linear-gradient(135deg,#ff1493,#773cff,#00cfff);box-shadow:0 0 25px #00cfff88}
.kvai-filmstrip{text-align:center;margin:8px 0;padding:7px;border-radius:10px;background:linear-gradient(90deg,#111b4a,#25105a,#102c54);border:1px solid #704cff;color:#fff;letter-spacing:7px}
[data-testid="stVideo"] video{max-height:290px!important;object-fit:contain;background:#020617;border:1px solid #00cfff;border-radius:12px}
.st-key-startbar{position:fixed!important;bottom:0!important;left:50%!important;transform:translateX(-50%)!important;width:min(100%,1500px)!important;z-index:999!important;background:linear-gradient(180deg,rgba(5,9,31,0),rgba(5,9,31,.97) 38%)!important;padding:8px 12px calc(7px + env(safe-area-inset-bottom))!important}
.st-key-startbar .stButton>button{min-height:46px!important;font-size:1.02rem!important}
@media (orientation:landscape) and (min-width:700px){
 html,body,.stApp,[data-testid="stAppViewContainer"]{height:100dvh!important;min-height:100dvh!important}
 [data-testid="stMain"]{height:100dvh!important;overflow:hidden!important}
 .block-container{height:100dvh!important;overflow:hidden!important;padding:.18rem .48rem 3.0rem!important}
 .kvai-head{min-height:82px!important;padding:7px 15px!important;margin:0 0 5px!important}
 .kvai-logo{width:42px!important;height:42px!important;font-size:22px!important}
 .kvai-title .kvai-h1{font-size:1.32rem!important}.kvai-title p{font-size:.72rem!important}
 .kvai-badge{padding:4px 9px!important;font-size:.72rem!important}
 [data-baseweb="tab-list"]{padding:3px!important}
 button[data-baseweb="tab"]{height:36px!important}
 [data-testid="stVerticalBlock"]{gap:.28rem!important}
 [data-testid="stHorizontalBlock"]{gap:.45rem!important;flex-wrap:nowrap!important}
 [data-testid="stColumn"]{min-width:0!important}
 [data-baseweb="tab-panel"]{padding-top:.12rem!important}
 div[data-testid="stVerticalBlockBorderWrapper"]{padding:3px!important}
 [data-testid="stWidgetLabel"] p{font-size:.76rem!important;margin-bottom:1px!important}
 [data-testid="stFileUploaderDropzone"]{padding:5px!important;min-height:65px!important}
 [data-testid="stVideo"] video{max-height:210px!important}
 .kvai-empty-preview{height:210px!important}
 .stButton>button,.stDownloadButton>button{min-height:32px!important;font-size:.8rem!important}
 .st-key-startbar{padding:5px 10px calc(4px + env(safe-area-inset-bottom))!important}
 .st-key-startbar .stButton>button{min-height:38px!important}
}
@media(max-width:699px){[data-baseweb="tab-list"]{overflow-x:auto!important}button[data-baseweb="tab"]{flex:0 0 auto!important;padding:0 9px!important}}
</style>
"""


apply_theme()
apply_neon_theme()
st.markdown(CINEMATIC_DASHBOARD_CSS, unsafe_allow_html=True)

_ANGKOR_BG_URL = 'data:image/jpeg;base64,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'
FINAL_RESPONSIVE_CSS = f"""
<style>
/* Use the same Angkor scene as a real full-page background, not only the header banner. */
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"] {{
  background-color:#05091f !important;
  background-image:linear-gradient(115deg,rgba(2,6,24,.82),rgba(5,12,40,.72) 48%,rgba(3,8,29,.84)),
    url("{_ANGKOR_BG_URL}") !important;
  background-size:cover !important; background-position:center center !important;
  background-attachment:fixed !important; background-repeat:no-repeat !important;
  color:#f7f8ff !important;
}}
/* Moving neon beams and small glowing particles across the entire screen. */
.stApp::before {{
  content:""; position:fixed; inset:-20%; z-index:0; pointer-events:none;
  background:repeating-linear-gradient(112deg,transparent 0 13%,rgba(0,221,255,.075) 13.15%,transparent 13.45% 28%),
    linear-gradient(105deg,transparent 38%,rgba(255,35,175,.12) 49%,transparent 60%);
  background-size:180% 100%,220% 100%;
  animation:kvai-beam-run 10s linear infinite; opacity:.8;
}}
@keyframes kvai-beam-run {{ 0% {{background-position:180% 0,180% 0}} 100% {{background-position:-30% 0,-40% 0}} }}
/* Keep all Streamlit content above the animated background. */
[data-testid="stMain"] > div, .block-container {{position:relative;z-index:1}}
/* Compact header and remove the oversized blank gaps. */
.kvai-head {{min-height:82px !important;height:82px !important;max-height:82px !important;
  margin:1px 0 4px !important;padding:6px 13px !important;overflow:hidden !important;}}
.kvai-logo {{width:48px !important;height:48px !important;flex:0 0 48px !important;}}
.kvai-title .kvai-h1 {{font-size:clamp(1.05rem,2.4vw,1.65rem) !important;}}
.kvai-title p {{font-size:clamp(.65rem,1.1vw,.85rem) !important;margin-top:1px !important;}}
[data-testid="stVerticalBlock"] {{gap:.35rem !important}}
[data-testid="stElementContainer"] {{margin-bottom:0 !important}}
/* Remove pale disabled button and the white-looking fixed footer. */
.st-key-startbar {{position:fixed !important;bottom:0 !important;left:50% !important;
  transform:translateX(-50%) !important;width:min(100%,1500px) !important;z-index:1000 !important;
  padding:5px 10px calc(5px + env(safe-area-inset-bottom)) !important;
  background:linear-gradient(180deg,rgba(3,8,29,0),rgba(3,8,29,.94) 35%,rgba(3,8,29,.98)) !important;
  border-top:1px solid rgba(0,220,255,.45) !important;box-shadow:0 -8px 28px rgba(0,0,0,.25) !important;
  backdrop-filter:blur(10px) !important;}}
.st-key-startbar [data-testid="stVerticalBlockBorderWrapper"],
.st-key-startbar [data-testid="stVerticalBlock"] {{background:transparent !important;border:0 !important;box-shadow:none !important;}}
.st-key-startbar .stButton>button,
.st-key-startbar .stButton>button:disabled {{
  min-height:42px !important;border:1px solid #18dfff !important;border-radius:13px !important;
  background:linear-gradient(100deg,#ff1493,#843bff,#00cfff) !important;
  color:#fff !important;opacity:1 !important;filter:none !important;
  box-shadow:0 0 18px rgba(0,207,255,.28),0 0 22px rgba(255,20,147,.2) !important;
}}
.st-key-startbar .stButton>button:disabled {{
  background:linear-gradient(100deg,rgba(255,20,147,.72),rgba(110,55,220,.78),rgba(0,170,220,.78)) !important;
  color:rgba(255,255,255,.94) !important;cursor:not-allowed !important;
}}
/* Inputs and cards remain dark; never let the Streamlit default light surface show through. */
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"],
[data-testid="stAlert"], [data-testid="stMetric"] {{background-color:rgba(7,18,53,.92) !important;}}
[data-baseweb="select"]>div, .stTextInput input, .stNumberInput input,
.stTextArea textarea, [data-baseweb="textarea"]>div {{background:#091638 !important;color:#fff !important;}}
@media (orientation:landscape) and (min-width:700px) {{
  html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"] {{height:100dvh !important;min-height:100dvh !important;}}
  [data-testid="stMain"] {{overflow:hidden !important;}}
  .block-container {{height:100dvh !important;max-width:1800px !important;
    overflow:hidden !important;padding:3px 10px 54px !important;}}
  .kvai-head {{height:76px !important;min-height:76px !important;max-height:76px !important;}}
  .kvai-logo {{width:42px !important;height:42px !important;flex-basis:42px !important;}}
  [data-baseweb="tab-list"] {{margin:2px 0 4px !important;padding:3px !important;}}
  button[data-baseweb="tab"] {{height:38px !important;}}
  [data-baseweb="tab-panel"] {{padding-top:2px !important;}}
  [data-testid="stVerticalBlock"] {{gap:.22rem !important;}}
  [data-testid="stHorizontalBlock"] {{gap:.4rem !important;flex-wrap:nowrap !important;}}
  [data-testid="stColumn"] {{min-width:0 !important;}}
  [data-testid="stWidgetLabel"] p {{font-size:.76rem !important;margin-bottom:0 !important;}}
  [data-testid="stFileUploaderDropzone"] {{min-height:56px !important;padding:4px !important;}}
  .stButton>button,.stDownloadButton>button {{min-height:34px !important;font-size:.78rem !important;}}
  .st-key-startbar .stButton>button {{min-height:38px !important;font-size:.9rem !important;}}
}}
@media (max-width:699px) {{
  .kvai-head {{height:auto !important;min-height:72px !important;max-height:none !important;}}
  .st-key-startbar {{width:100% !important;}}
}}
</style>
"""
st.markdown(FINAL_RESPONSIVE_CSS, unsafe_allow_html=True)

# ---------- Runtime usability fix: never clip Streamlit widgets ----------
# Previous CSS forced the whole app to 100dvh + overflow:hidden. On mobile
# landscape this clipped the tab panel and left controls visible but unusable.
USABILITY_FIX_CSS = """
<style>
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"] {
  height: auto !important; min-height: 100% !important;
  overflow-x: hidden !important; overflow-y: auto !important;
}
[data-testid="stMain"] { overflow: visible !important; }
.block-container {
  height: auto !important; min-height: 100dvh !important;
  max-height: none !important; overflow: visible !important;
  padding: 4px 10px 14px !important;
}
[data-baseweb="tab-panel"] {
  height: auto !important; max-height: none !important;
  overflow: visible !important; padding-bottom: 8px !important;
}
/* Keep the action button in normal layout so it cannot cover controls. */
.st-key-startbar {
  position: relative !important; inset: auto !important;
  transform: none !important; width: 100% !important;
  z-index: 5 !important; margin: 8px 0 4px !important;
  padding: 6px 8px calc(6px + env(safe-area-inset-bottom)) !important;
  background: linear-gradient(90deg,rgba(255,20,147,.22),rgba(8,18,55,.96),rgba(0,210,255,.22)) !important;
  border: 1px solid rgba(0,220,255,.72) !important;
  border-radius: 16px !important; box-shadow: 0 0 18px rgba(0,190,255,.18) !important;
}
.st-key-startbar [data-testid="stVerticalBlockBorderWrapper"],
.st-key-startbar [data-testid="stVerticalBlock"] {
  background: transparent !important; border: 0 !important; box-shadow: none !important;
}
.st-key-startbar .stButton > button,
.st-key-startbar .stButton > button:disabled {
  min-height: 44px !important; opacity: 1 !important;
  color: #fff !important; border: 1px solid #19ddff !important;
  background: linear-gradient(100deg,#ff1493,#843bff,#00cfff) !important;
}
/* API warning should be a compact banner, not consume the whole first screen. */
[data-testid="stAlert"] {
  padding: 7px 12px !important; margin: 4px 0 7px !important;
  border-radius: 12px !important; min-height: 0 !important;
}
[data-testid="stAlert"] p { font-size: .88rem !important; line-height: 1.35 !important; margin: 0 !important; }
/* Remove oversized gaps between header, orientation control and tabs. */
[data-testid="stVerticalBlock"] { gap: .35rem !important; }
[data-testid="stElementContainer"] { margin-bottom: 0 !important; }
@media (orientation: landscape) and (max-height: 700px) {
  .block-container { padding: 3px 8px 8px !important; }
  .kvai-head { height: 68px !important; min-height: 68px !important; max-height: 68px !important;
    margin: 0 0 3px !important; padding: 5px 10px !important; }
  .kvai-logo { width: 40px !important; height: 40px !important; flex-basis: 40px !important; }
  .kvai-title .kvai-h1 { font-size: 1.15rem !important; }
  .kvai-title p { font-size: .68rem !important; }
  [data-baseweb="tab-list"] { margin: 2px 0 !important; padding: 3px !important; }
  button[data-baseweb="tab"] { height: 35px !important; }
  [data-testid="stWidgetLabel"] p { font-size: .74rem !important; }
  .stButton > button, .stDownloadButton > button { min-height: 34px !important; }
}
</style>
"""
st.markdown(USABILITY_FIX_CSS, unsafe_allow_html=True)


# ---------- Final landscape desktop-mode layout (last CSS wins) ----------
LANDSCAPE_DESKTOP_FINAL_CSS = """
<style>
/* Rich full-screen canvas with the Angkor artwork and animated neon beams. */
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"] {
  background-color:#05091d !important;
  background-color:#05091d !important;
  color:#f7f8ff !important;
}
/* The existing page background already embeds the Angkor image in FINAL_RESPONSIVE_CSS;
   keep it visible and animate light streaks above it without blocking clicks. */
.stApp::before {
  content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
  background:repeating-linear-gradient(112deg,transparent 0 14%,rgba(0,220,255,.08) 14.1%,transparent 14.5% 29%),
    linear-gradient(105deg,transparent 34%,rgba(255,25,170,.13) 48%,transparent 61%);
  background-size:220% 100%,240% 100%; animation:kvai-final-beams 8s linear infinite;
}
@keyframes kvai-final-beams { from {background-position:220% 0,200% 0} to {background-position:-20% 0,-40% 0} }
[data-testid="stMain"] > div, .block-container {position:relative;z-index:1}
[data-testid="stHeader"], [data-testid="stToolbar"] {background:transparent !important}
.block-container {max-width:1800px !important;padding:3px 9px 54px !important}
.kvai-head {height:70px !important;min-height:70px !important;max-height:70px !important;
  margin:0 0 3px !important;padding:5px 12px !important}
.kvai-logo {width:43px !important;height:43px !important;flex:0 0 43px !important}
.kvai-title .kvai-h1 {font-size:clamp(1.05rem,2vw,1.55rem) !important}
.kvai-title p {font-size:.72rem !important;margin:0 !important}
.kvai-badge {padding:4px 10px !important;font-size:.72rem !important}
/* Compact orientation button: no large blank band under the header. */
iframe[title="streamlit.components.v1.html"] {max-height:34px !important}
[data-baseweb="tab-list"] {display:flex !important;gap:4px !important;padding:3px !important;margin:2px 0 4px !important}
button[data-baseweb="tab"] {height:37px !important;min-width:0 !important;padding:0 9px !important}
button[data-baseweb="tab"] p {font-size:.82rem !important;white-space:nowrap !important}
[data-baseweb="tab-panel"] {padding:2px 0 6px !important}
[data-testid="stVerticalBlock"] {gap:.28rem !important}
[data-testid="stElementContainer"] {margin-bottom:0 !important}
[data-testid="stHorizontalBlock"] {gap:.45rem !important;flex-wrap:nowrap !important}
[data-testid="stColumn"] {min-width:0 !important}
.kvai-panel-title {margin:0 0 4px !important;padding:5px 8px !important;font-size:.92rem !important}
.kvai-step {width:25px !important;height:25px !important;font-size:.82rem !important}
div[data-testid="stVerticalBlockBorderWrapper"] {padding:3px 4px !important;border-radius:12px !important}
[data-testid="stWidgetLabel"] p, .stApp label {font-size:.76rem !important;margin-bottom:1px !important}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {font-size:.68rem !important;line-height:1.2 !important;margin:1px 0 !important}
[data-testid="stFileUploaderDropzone"] {min-height:48px !important;padding:3px 7px !important}
[data-testid="stFileUploaderDropzoneInstructions"] {padding:0 !important}
[data-testid="stVideo"] video {max-height:145px !important;object-fit:contain !important}
.kvai-empty-preview {height:145px !important;gap:5px !important}
.kvai-play {width:42px !important;height:42px !important;font-size:20px !important}
.kvai-filmstrip {margin:3px 0 !important;padding:3px !important;letter-spacing:3px !important}
[data-baseweb="select"] > div {min-height:34px !important}
.stTextInput input, .stNumberInput input {min-height:32px !important}
.stButton > button, .stDownloadButton > button {min-height:34px !important;padding:3px 8px !important;font-size:.78rem !important}
[data-testid="stRadio"] [role="radiogroup"] {gap:4px !important}
[data-testid="stRadio"] label {padding:4px 7px !important;font-size:.72rem !important}
[data-testid="stToggle"] {padding:0 !important}
[data-testid="stSlider"] {padding-top:0 !important;padding-bottom:0 !important}
[data-testid="stAlert"] {padding:5px 9px !important;margin:2px 0 !important}
[data-testid="stAlert"] p {font-size:.72rem !important;line-height:1.2 !important}
/* The start action stays visible, but its footer never covers the controls. */
.st-key-startbar {position:fixed !important;left:50% !important;bottom:0 !important;
  transform:translateX(-50%) !important;width:min(100%,1800px) !important;z-index:1000 !important;
  margin:0 !important;padding:4px 9px calc(4px + env(safe-area-inset-bottom)) !important;
  background:linear-gradient(180deg,rgba(4,9,30,0),rgba(4,9,30,.96) 35%) !important;
  border-top:1px solid rgba(0,220,255,.5) !important;backdrop-filter:blur(9px) !important}
.st-key-startbar [data-testid="stVerticalBlockBorderWrapper"],
.st-key-startbar [data-testid="stVerticalBlock"] {background:transparent !important;border:0 !important;box-shadow:none !important}
.st-key-startbar .stButton > button {min-height:39px !important;font-size:.9rem !important;
  background:linear-gradient(100deg,#ff1493,#843bff,#00cfff) !important;color:#fff !important;
  border:1px solid #20dfff !important;box-shadow:0 0 15px rgba(0,207,255,.3) !important}
@media (orientation:landscape) and (max-height:600px) {
  .block-container {padding:2px 7px 47px !important}
  .kvai-head {height:58px !important;min-height:58px !important;max-height:58px !important;padding:4px 9px !important}
  .kvai-logo {width:36px !important;height:36px !important;flex-basis:36px !important}
  .kvai-title .kvai-h1 {font-size:1.08rem !important}
  .kvai-title p {display:none !important}
  .kvai-badge {font-size:.64rem !important;padding:3px 7px !important}
  button[data-baseweb="tab"] {height:31px !important;padding:0 6px !important}
  button[data-baseweb="tab"] p {font-size:.7rem !important}
  .kvai-panel-title {font-size:.78rem !important;padding:3px 6px !important}
  .kvai-step {width:21px !important;height:21px !important}
  [data-testid="stVideo"] video, .kvai-empty-preview {max-height:105px !important;height:105px !important}
  [data-testid="stFileUploaderDropzone"] {min-height:38px !important;padding:1px 5px !important}
  [data-testid="stWidgetLabel"] p, .stApp label {font-size:.67rem !important}
  .stButton > button, .stDownloadButton > button {min-height:29px !important;font-size:.68rem !important}
  .st-key-startbar .stButton > button {min-height:34px !important}
}
/* Portrait stays naturally scrollable and usable; landscape is compact desktop mode. */
@media (orientation:portrait) {
  .block-container {padding-bottom:16px !important}
  .st-key-startbar {position:relative !important;left:auto !important;bottom:auto !important;transform:none !important;width:100% !important}
}
</style>
"""
st.markdown(LANDSCAPE_DESKTOP_FINAL_CSS, unsafe_allow_html=True)


# ---------- Mobile landscape: fit the dashboard to one screen ----------
MOBILE_LANDSCAPE_FIT_CSS = """
<style>
@media (orientation: landscape) and (min-width: 600px) and (max-height: 900px) {
  /* Other tabs remain naturally usable; the Home dashboard is locked to one screen below. */
  html, body, .stApp, [data-testid="stAppViewContainer"],
  [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
    height: auto !important; min-height: 100dvh !important;
    overflow-x: hidden !important; overflow-y: auto !important;
  }
  [data-testid="stHeader"], [data-testid="stToolbar"] { height: 0 !important; display: none !important; }
  [data-testid="stMain"] { overflow: visible !important; }
  .block-container {
    height: auto !important; min-height: 100dvh !important; max-height: none !important;
    overflow: visible !important; padding: 2px 7px 43px !important;
    max-width: 1800px !important;
  }
  .kvai-head {
    height: 54px !important; min-height: 54px !important; max-height: 54px !important;
    margin: 0 0 2px !important; padding: 3px 8px !important; gap: 7px !important;
    border-radius: 12px !important;
  }
  .kvai-logo { width: 34px !important; height: 34px !important; flex: 0 0 34px !important; font-size: 18px !important; }
  .kvai-title .kvai-h1 { font-size: clamp(.9rem, 2.1vw, 1.25rem) !important; line-height: 1.05 !important; }
  .kvai-title p { font-size: .58rem !important; line-height: 1 !important; margin: 1px 0 0 !important; }
  .kvai-badge { padding: 3px 7px !important; font-size: .6rem !important; }
  iframe[title="streamlit.components.v1.html"] { height: 24px !important; max-height: 24px !important; }
  [data-baseweb="tab-list"] {
    display: flex !important; flex-wrap: nowrap !important; gap: 3px !important;
    padding: 2px !important; margin: 1px 0 3px !important; overflow: hidden !important;
  }
  button[data-baseweb="tab"] {
    flex: 1 1 0 !important; min-width: 0 !important; height: 30px !important;
    padding: 0 2px !important; border-radius: 7px !important;
  }
  button[data-baseweb="tab"] p {
    font-size: clamp(.55rem, .9vw, .7rem) !important;
    white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;
  }
  [data-baseweb="tab-panel"] {
    height: auto !important; max-height: none !important;
    overflow: visible !important; padding: 0 !important;
  }
  /* Home is a true one-screen dashboard: no page or panel scrolling. */
  html:has(button[data-baseweb="tab"]:first-of-type[aria-selected="true"]),
  body:has(button[data-baseweb="tab"]:first-of-type[aria-selected="true"]),
  html:has(button[data-baseweb="tab"]:first-of-type[aria-selected="true"]) .stApp,
  body:has(button[data-baseweb="tab"]:first-of-type[aria-selected="true"]) .stApp,
  html:has(button[data-baseweb="tab"]:first-of-type[aria-selected="true"]) [data-testid="stAppViewContainer"],
  body:has(button[data-baseweb="tab"]:first-of-type[aria-selected="true"]) [data-testid="stAppViewContainer"],
  html:has(button[data-baseweb="tab"]:first-of-type[aria-selected="true"]) [data-testid="stMain"],
  body:has(button[data-baseweb="tab"]:first-of-type[aria-selected="true"]) [data-testid="stMain"] {
    height: 100dvh !important; min-height: 100dvh !important; overflow: hidden !important;
  }
  html:has(button[data-baseweb="tab"]:first-of-type[aria-selected="true"]) .block-container,
  body:has(button[data-baseweb="tab"]:first-of-type[aria-selected="true"]) .block-container {
    height: 100dvh !important; min-height: 0 !important; max-height: 100dvh !important;
    overflow: hidden !important;
  }
  html:has(button[data-baseweb="tab"]:first-of-type[aria-selected="true"]) [data-baseweb="tab-panel"],
  body:has(button[data-baseweb="tab"]:first-of-type[aria-selected="true"]) [data-baseweb="tab-panel"] {
    height: calc(100dvh - 125px) !important; max-height: calc(100dvh - 125px) !important;
    overflow: hidden !important;
  }
  [data-testid="stVerticalBlock"] { gap: .18rem !important; }
  [data-testid="stElementContainer"] { margin-bottom: 0 !important; }
  [data-testid="stHorizontalBlock"] { gap: .3rem !important; flex-wrap: nowrap !important; }
  [data-testid="stColumn"] { min-width: 0 !important; }
  .kvai-panel-title { margin: 0 0 2px !important; padding: 3px 6px !important; font-size: .72rem !important; }
  .kvai-step { width: 19px !important; height: 19px !important; font-size: .65rem !important; }
  div[data-testid="stVerticalBlockBorderWrapper"] { padding: 2px 3px !important; border-radius: 9px !important; }
  [data-testid="stWidgetLabel"] p, .stApp label { font-size: .62rem !important; margin: 0 !important; }
  [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
    font-size: .56rem !important; line-height: 1.05 !important; margin: 0 !important;
  }
  [data-testid="stFileUploaderDropzone"] { min-height: 35px !important; padding: 1px 4px !important; }
  [data-testid="stFileUploaderDropzoneInstructions"] { padding: 0 !important; }
  [data-testid="stFileUploaderDropzoneInstructions"] span,
  [data-testid="stFileUploaderDropzoneInstructions"] small { font-size: .58rem !important; }
  .stTextArea textarea { min-height: 42px !important; height: 42px !important; }
  [data-testid="stVideo"] video, .kvai-empty-preview { max-height: 92px !important; height: 92px !important; }
  .kvai-play { width: 34px !important; height: 34px !important; font-size: 16px !important; }
  .kvai-filmstrip { display: none !important; }
  [data-baseweb="select"] > div { min-height: 28px !important; }
  .stTextInput input, .stNumberInput input { min-height: 27px !important; }
  .stButton > button, .stDownloadButton > button {
    min-height: 28px !important; padding: 2px 5px !important; font-size: .62rem !important;
  }
  [data-testid="stRadio"] [role="radiogroup"] { gap: 2px !important; }
  [data-testid="stRadio"] label { padding: 2px 5px !important; font-size: .6rem !important; }
  [data-testid="stToggle"], [data-testid="stCheckbox"], [data-testid="stSlider"] { padding: 0 !important; }
  [data-testid="stExpander"] summary { min-height: 26px !important; padding: 3px 7px !important; }
  [data-testid="stExpander"] summary p { font-size: .65rem !important; }
  [data-testid="stAlert"] { padding: 3px 6px !important; margin: 1px 0 !important; }
  [data-testid="stAlert"] p { font-size: .62rem !important; line-height: 1.1 !important; }
  .st-key-startbar {
    position: fixed !important; left: 50% !important; bottom: 0 !important;
    transform: translateX(-50%) !important; width: 100% !important; z-index: 1000 !important;
    margin: 0 !important; padding: 3px 7px !important; border-radius: 0 !important;
    background: linear-gradient(90deg,rgba(255,20,147,.18),rgba(4,9,30,.97),rgba(0,210,255,.18)) !important;
  }
  .st-key-startbar .stButton > button { min-height: 33px !important; font-size: .78rem !important; }
}
@media (orientation: landscape) and (min-width: 600px) and (max-height: 520px) {
  .kvai-head { height: 43px !important; min-height: 43px !important; max-height: 43px !important; }
  .kvai-logo { width: 28px !important; height: 28px !important; flex-basis: 28px !important; }
  .kvai-title p, .kvai-badge { display: none !important; }
  iframe[title="streamlit.components.v1.html"] { height: 19px !important; max-height: 19px !important; }
  button[data-baseweb="tab"] { height: 26px !important; }
  [data-baseweb="tab-panel"] { height: calc(100dvh - 105px) !important; max-height: calc(100dvh - 105px) !important; }
  [data-testid="stVideo"] video, .kvai-empty-preview { max-height: 72px !important; height: 72px !important; }
  .st-key-startbar .stButton > button { min-height: 28px !important; }
}
</style>
"""
st.markdown(MOBILE_LANDSCAPE_FIT_CSS, unsafe_allow_html=True)


# ============================ Hongguo ============================
# ---- Login/VIP system removed per user request ----
def _is_admin_session():
    return False  # debug/API-key panel hidden now that login is removed


def _hg_norm(key):
    return re.sub(r"[^A-Z0-9]", "", str(key).upper())


def _hg_walk_secrets():
    """យក (key, value) ទាំងអស់ពី st.secrets រួមទាំង [section] ខាងក្នុង។"""
    out = []

    def _walk(obj, depth=0):
        if depth > 4:
            return
        try:
            items = list(obj.items())
        except Exception:
            return
        for k, v in items:
            if hasattr(v, "items"):
                _walk(v, depth + 1)
            else:
                out.append((str(k), v))

    try:
        _walk(st.secrets)
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)
    return out


_HG_ID_KEYS = {"XIAOYINGAPPID", "APPID", "HONGGUOAPPID", "XIAOYINGAPIAPPID", "XIAOYINGID"}


_HG_SECRET_KEYS = {"XIAOYINGAPPSECRET", "APPSECRET", "HONGGUOAPPSECRET", "XIAOYINGAPIAPPSECRET", "XIAOYINGSECRET", "APIFYAPITOKEN", "APIFYTOKEN"}


def _hg_secret(*names):
    """អាន Hongguo credentials ពី Streamlit Secrets / Environment។
    មិនប្រកាន់ អក្សរធំតូច, _ ឬ - ហើយរកក្នុង [section] ដែរ។
    """
    wanted = _HG_ID_KEYS if any(_hg_norm(n) in _HG_ID_KEYS for n in names) else _HG_SECRET_KEYS
    # 1) ឈ្មោះដែលបានកំណត់ច្បាស់លាស់ (top-level)
    for name in names:
        try:
            value = st.secrets.get(name, "")
        except Exception:
            value = ""
        if value and not hasattr(value, "items"):
            return str(value).strip().strip('"\'').strip()
        value = os.environ.get(name, "")
        if value:
            return str(value).strip().strip('"\'').strip()
    # 2) ឈ្មោះស្រដៀងគ្នា ឬនៅក្នុង [section]
    for k, v in _hg_walk_secrets():
        if _hg_norm(k) in wanted and v:
            return str(v).strip().strip('"\'').strip()
    for k, v in os.environ.items():
        if _hg_norm(k) in wanted and v:
            return str(v).strip().strip('"\'').strip()
    return ""


_HG_API_BASE = "https://www.xiaoyingapi.com"


def _hg_signed_params(biz=None, method="GET", path=""):
    """Build XiaoYingAPI HMAC-SHA256 auth params per its integration guide."""
    import hashlib, hmac, secrets as _secrets
    def _clean(v):
        v = str(v or "")
        for ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\xa0", "\n", "\r", "\t", " ", '"', "'"):
            v = v.replace(ch, "")
        return v
    # លំដាប់៖ Key ផ្ទាល់ខ្លួនរបស់អ្នកប្រើ → Admin store/Secrets
    app_id = _clean(st.session_state.get("user_hg_app_id") or _HG_APP_ID)
    app_secret = _clean(st.session_state.get("user_hg_app_secret") or _HG_APP_SECRET)
    if not app_id or not app_secret:
        raise RuntimeError("មិនទាន់កំណត់ XiaoYingAPI APPID និង APPSECRET ក្នុង Streamlit Secrets ទេ។")
    params = {str(k): v for k, v in dict(biz or {}).items() if v is not None and v != ""}
    params.update({"app_id": app_id, "timestamp": str(int(time.time())), "nonce": _secrets.token_hex(8)})
    pairs = sorted((k, str(v)) for k, v in params.items() if k != "sign" and v not in (None, ""))
    raw = method.upper() + "\n" + path + "\n" + "&".join(f"{k}={v}" for k, v in pairs)
    params["sign"] = hmac.new(app_secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return params


def _hg_prefixes():
    """Path prefix ដែលអាចកំណត់ដោយខ្លួនឯង (ប្រអប់ក្នុង UI) ឬសាកល្បងស្វ័យប្រវត្តិ។"""
    custom = str(st.session_state.get("hg_path_prefix") or "").strip()
    out = []
    if custom:
        out.append("/" + custom.strip("/") + "/")
    out += ["/api/dramas/hongguo/", "/api/hongguo/", "/api/v1/hongguo/", "/api/v1/dramas/hongguo/",
            "/api/drama/hongguo/", "/hongguo/", "/api/dramas/"]
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x); res.append(x)
    return res


_HG_FAIL = {"until": 0.0, "msg": ""}


def _hg_api(endpoint, params=None, timeout=45):
    """Call XiaoYingAPI Hongguo endpoint and unwrap its {code,msg,data} envelope.
    បើ path 404 (code 20030) សាកល្បង prefix/slash ផ្សេងៗ ហើយចងចាំ path ដែលដំណើរការ។"""
    if _HG_FAIL["until"] > time.time() and not st.session_state.get("_hg_good_prefix"):
        raise RuntimeError(_HG_FAIL["msg"])   # កុំសាកល្បងម្តងទៀតជាប់ៗគ្នា (ធ្វើឱ្យយឺត)
    timeout = min(timeout, 12)
    ep = str(endpoint).strip("/")
    good = st.session_state.get("_hg_good_prefix")
    prefixes = ([good] if good else []) + [x for x in _hg_prefixes() if x != good]
    last_err = None
    tried = []
    for prefix in prefixes:
        for slash in ("/", ""):
            path = prefix + ep + slash
            tried.append(path)
            try:
                response = requests.get(_HG_API_BASE + path, params=_hg_signed_params(params, "GET", path), timeout=timeout,
                                        headers={"Accept": "application/json", "User-Agent": "KhmerVideoAI/1.0"})
            except requests.RequestException as exc:
                raise RuntimeError(f"XiaoYingAPI មិនអាចភ្ជាប់បាន៖ {exc}") from exc
            try:
                payload = response.json()
            except ValueError:
                last_err = f"XiaoYingAPI HTTP {response.status_code}: មិនមែន JSON ត្រឹមត្រូវ។ ({path})"
                continue
            code = payload.get("code") if isinstance(payload, dict) else None
            if response.status_code == 404 or str(code) == "20030":
                last_err = f"XiaoYingAPI HTTP 404: {str(payload)[:300]} ({path})"
                continue
            if not response.ok:
                raise RuntimeError(f"XiaoYingAPI HTTP {response.status_code}: {str(payload)[:500]}")
            if isinstance(payload, dict) and code not in (None, 10000, "10000"):
                msg = payload.get("msg") or "API error"
                if str(code) == "20011":
                    msg += " (សូមពិនិត្យ APPID/APPSECRET, timestamp និង signature)"
                raise RuntimeError(f"XiaoYingAPI {code}: {msg}")
            st.session_state["_hg_good_prefix"] = prefix
            return payload.get("data", payload) if isinstance(payload, dict) else payload
    _msg = ((last_err or "XiaoYingAPI: រកមិនឃើញ endpoint") +
                       " · បានសាកល្បង: " + ", ".join(tried[:6]) +
                       " · សូមសួរអ្នកលក់រក API docs ដើម្បីដឹង path ត្រឹមត្រូវ។")
    _HG_FAIL["until"] = time.time() + 90
    _HG_FAIL["msg"] = _msg
    raise RuntimeError(_msg)


def _hg_results(data):
    if isinstance(data, list): return data
    if isinstance(data, dict):
        for key in ("results", "items", "list", "records"):
            if isinstance(data.get(key), list): return data[key]
    return []


def _hg_normalize_row(item):
    """Normalize Hongguo Actor records while retaining raw fields for compatibility."""
    if not isinstance(item, dict):
        return {}
    nested = item.get("data") if isinstance(item.get("data"), dict) else item

    # Some Actor outputs wrap the series metadata in one more object.
    for key in ("series", "drama", "book", "item", "result"):
        if isinstance(nested.get(key), dict):
            nested = nested[key]
            break

    sid = (nested.get("seriesId") or nested.get("series_id") or nested.get("bookId")
           or nested.get("book_id") or nested.get("id"))
    cover = (
        nested.get("coverUrl") or nested.get("cover_url") or nested.get("cover")
        or nested.get("posterUrl") or nested.get("poster_url") or nested.get("poster")
        or nested.get("coverImage") or nested.get("cover_image")
        or nested.get("imageUrl") or nested.get("image_url")
        or nested.get("image") or nested.get("thumbnail") or nested.get("thumb")
        or nested.get("pic") or nested.get("img") or nested.get("verticalCover")
        or nested.get("vertical_cover") or nested.get("poster")
    )
    if isinstance(cover, dict):
        cover = cover.get("url") or cover.get("src") or cover.get("imageUrl") or ""
    if isinstance(cover, list):
        cover = next((x for x in cover if isinstance(x, str) and x.startswith(("http://", "https://"))), "")
    if not cover:
        def _deep_imgs(o, acc, depth=0):
            if depth > 4:
                return
            if isinstance(o, str):
                if o.startswith(("http://", "https://")):
                    lo = o.lower().split("?")[0]
                    if lo.endswith((".jpg", ".jpeg", ".png", ".webp", ".image", ".heic", ".avif", ".awebp")):
                        acc.append(o)
            elif isinstance(o, dict):
                for v in o.values():
                    _deep_imgs(v, acc, depth + 1)
            elif isinstance(o, list):
                for v in o[:8]:
                    _deep_imgs(v, acc, depth + 1)
        _imgs = []
        _deep_imgs(nested, _imgs)
        _good = [u for u in _imgs if u.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png", ".webp"))]
        cover = (_good or _imgs or [""])[0]

    title = (nested.get("title") or nested.get("name") or nested.get("bookName")
             or nested.get("seriesName") or nested.get("dramaName") or "រឿង Hongguo")
    description = (nested.get("intro") or nested.get("description")
                   or nested.get("summary") or nested.get("synopsis") or "")
    count = (nested.get("episodeCount") or nested.get("episode_cnt")
             or nested.get("totalEpisodes") or nested.get("episode_count") or "")
    return {
        **nested,
        "series_id": str(sid or ""),
        "name": title,
        "cover": str(cover or ""),
        "intro": description,
        "episode_cnt": count,
    }


def _hg_rows_from_items(items, label=""):
    """បម្លែងលទ្ធផល Actor ជា rows។ បើទទេ → raise ដើម្បីកុំ cache លទ្ធផលទទេ ១ ម៉ោង និងបង្ហាញមូលហេតុពិត។"""
    flat = []

    def _collect(o, depth=0):
        if isinstance(o, dict):
            flat.append(o)
            if depth < 2:
                for k in ("results", "items", "list", "dramas", "series", "books", "data"):
                    v = o.get(k)
                    if isinstance(v, list):
                        for x in v:
                            _collect(x, depth + 1)
        elif isinstance(o, list):
            for x in o:
                _collect(x, depth + 1)

    _collect(items)
    rows = [_hg_normalize_row(x) for x in flat]
    rows = [x for x in rows if x.get("series_id")]
    seen, out = set(), []
    for r in rows:
        if r["series_id"] not in seen:
            seen.add(r["series_id"])
            out.append(r)
    if not out:
        n = len(items) if isinstance(items, list) else 0
        keys = ""
        if n and isinstance(items[0], dict):
            keys = " · keys: " + ", ".join(list(items[0].keys())[:10])
        raise RuntimeError(f"Actor ត្រឡប់ {n} records តែគ្មានរឿងដែលប្រើបាន ({label}){keys}")
    return out


_HG_MAX_PAGES = 5   # Actor ផ្តល់អតិបរមា 100 រឿង = 5 ទំព័រ × 20


@st.cache_data(ttl=180, show_spinner=False)
def _hg_rank_all():
    """Fetch first rank page from XiaoYingAPI; cached briefly for responsive paging."""
    data = _hg_api("rank", {"type": "hot-drama", "page": 1})
    return _hg_rows_from_items(_hg_results(data), "hot")


def _hg_rank(page=1):
    """Fetch the requested hot-ranking page from XiaoYingAPI."""
    page = max(1, int(page))
    data = _hg_api("rank", {"type": "hot-drama", "page": page})
    return _hg_rows_from_items(_hg_results(data), "hot")


@st.cache_data(ttl=600, show_spinner=False)
def _hg_categories():
    """Fetch the category tree from XiaoYingAPI and flatten for the existing selector."""
    data = _hg_api("categories", {})
    roots = data.get("categories", []) if isinstance(data, dict) else []
    out = []
    for root in roots:
        if not isinstance(root, dict):
            continue
        root_slug = str(root.get("slug") or "")
        if root_slug:
            out.append({"name": str(root.get("name") or root_slug), "slug": root_slug})
        for child in root.get("children", []) or []:
            if isinstance(child, dict) and child.get("slug"):
                out.append({"name": f"{root.get('name','')} · {child.get('name','')}", "slug": str(child["slug"])})
    return out


def _hg_flat_categories(categories):
    """Flatten category data into a label -> API category ID mapping.

    Apify's currently configured Hongguo Actors do not return categories, so
    an empty list naturally produces an empty mapping and leaves the Hot feed
    available. This helper also tolerates nested category data if an Actor
    starts returning it in a future version.
    """
    flat = {}

    def walk(items, prefix=""):
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, (list, tuple)):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            label = (item.get("name") or item.get("title") or item.get("categoryName")
                     or item.get("label") or "")
            category_id = (item.get("slug") or item.get("categoryId")
                           or item.get("category_id") or item.get("id") or "")
            label = str(label).strip()
            category_id = str(category_id).strip()
            if label and category_id:
                display = f"{prefix}{label}" if prefix else label
                # Avoid overwriting duplicate labels in the visible selector.
                if display in flat:
                    display = f"{display} ({category_id})"
                flat[display] = category_id
            children = (item.get("children") or item.get("categories")
                        or item.get("categoryList") or item.get("category_list") or [])
            walk(children, f"{label} / " if label else prefix)

    walk(categories)
    return flat


@st.cache_data(ttl=600, show_spinner=False)
def _hg_detail(series_id):
    """Fetch normalized Hongguo series detail and full episode list."""
    data = _hg_api("detail", {"series_id": str(series_id)})
    if not isinstance(data, dict):
        return {}
    eps = data.get("episodes", []) or []
    normalized = []
    for i, item in enumerate(eps):
        if not isinstance(item, dict):
            continue
        try:
            epno = int(item.get("ep") or i + 1)
        except (TypeError, ValueError):
            epno = i + 1
        normalized.append({**item, "ep": epno,
                           "video_id": str(item.get("episode_id") or item.get("episodeId") or ""),
                           "url": str(item.get("url") or ""),
                           "playable": bool(item.get("playable", True))})
    try:
        count = int(data.get("episode_cnt") or len(normalized))
    except (TypeError, ValueError):
        count = len(normalized)
    return {**data, "series_id": str(data.get("series_id") or series_id),
            "name": data.get("name") or "រឿង Hongguo", "cover": data.get("cover") or "",
            "intro": data.get("intro") or "", "episode_cnt": count, "episodes": normalized}


def _hg_fetch_cover(url):
    """ទាញរូប poster នៅខាង Server (ដាក់ User-Agent/Referer) ហើយបម្លែងជា JPEG
    ដើម្បីជៀសវាងបញ្ហា hotlink / referrer / ទ្រង់ទ្រាយ heic-avif ក្នុង Browser។ ត្រឡប់ (bytes, error)។"""
    u = str(url or "").strip()
    if u.startswith("//"):
        u = "https:" + u
    if not u.startswith(("http://", "https://")):
        return None, "bad url"
    last = ""
    _cands = [u]
    _base, _, _q = u.partition("?")
    for _ext in (".heic", ".avif", ".awebp", ".image"):
        if _base.lower().endswith(_ext):
            for _alt in (".jpeg", ".webp", ".png"):
                _cands.append(_base[:-len(_ext)] + _alt + (("?" + _q) if _q else ""))
    _tries = [(c, ref) for c in _cands for ref in ("https://hongguoduanju.com/", "")]
    for u, ref in _tries:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36",
                       "Accept": "image/avif,image/webp,image/jpeg,image/*;q=0.8"}
            if ref:
                headers["Referer"] = ref
            r = requests.get(u, headers=headers, timeout=8)
            if r.status_code != 200 or len(r.content) < 500:
                last = f"HTTP {r.status_code}"
                continue
            data = r.content
            try:
                from PIL import Image
                try:
                    import pillow_heif
                    pillow_heif.register_heif_opener()
                except Exception as _swallow_e:
                    _log_swallowed(_swallow_e)
                im = Image.open(io.BytesIO(data))
                im = im.convert("RGB")
                im.thumbnail((480, 640))
                out = io.BytesIO()
                im.save(out, format="JPEG", quality=82)
                return out.getvalue(), ""
            except Exception as e:
                last = "decode: " + (r.headers.get("Content-Type") or "?")[:30] + " " + str(e)[:40]
                ctype = (r.headers.get("Content-Type") or "").lower()
                if ctype.startswith("image/") and any(x in ctype for x in ("jpeg", "png", "webp", "gif")):
                    return data, ""
                continue
        except Exception as e:
            last = str(e)[:80]
    return None, last or "failed"


def _hg_show_cover(url):
    """បង្ហាញ poster តាម Server (មិនពឹង Browser ទាញពី CDN ផ្ទាល់)។"""
    u = str(url or "").strip()
    if not u:
        return
    data, err = _hg_fetch_cover(u)
    if data:
        try:
            st.image(data, use_container_width=True)
            return
        except Exception as _swallow_e:
            _log_swallowed(_swallow_e)
    # Server ទាញមិនបាន (ឧ. CDN រារាំង IP Server) → ឱ្យ Browser របស់អ្នកប្រើសាកទាញផ្ទាល់ (វិធីដើម)
    try:
        st.image(u, use_container_width=True)
    except Exception:
        st.markdown(
            '<div style="aspect-ratio:3/4;border-radius:10px;background:#1a2050;display:flex;'
            'align-items:center;justify-content:center;font-size:34px;">🎬</div>',
            unsafe_allow_html=True,
        )
    if _is_admin_session():
        try:
            _host = urllib.parse.urlparse(u).hostname or "?"
        except Exception:
            _host = "?"
        st.caption(f"🖼 {str(err)[:30]} · {_host[:28]}")


def _hg_enrich_rows(rows):
    """បំពេញ poster/ឈ្មោះ/ចំនួនភាគ ដែលខ្វះ ពី detail actor (ស្របគ្នា)។"""
    def _need(r):
        return (not r.get("cover")) or r.get("name") == "រឿង Hongguo"

    def _fix(r):
        if not _need(r):
            return r
        try:
            d = _hg_detail(r["series_id"])
        except Exception:
            return r
        if not d:
            return r
        out = dict(r)
        if d.get("cover"):
            out["cover"] = d["cover"]
        if d.get("name") and d["name"] != "រឿង Hongguo":
            out["name"] = d["name"]
        if d.get("episode_cnt"):
            out["episode_cnt"] = d["episode_cnt"]
        if d.get("intro"):
            out["intro"] = d["intro"]
        return out

    if not rows:
        return rows
    with ThreadPoolExecutor(max_workers=10) as ex:
        return list(ex.map(_fix, rows))


@st.cache_data(ttl=180, show_spinner=False)
def _hg_category_all(category, page=1):
    data = _hg_api("list", {"category": str(category), "page": int(page or 1)})
    return _hg_rows_from_items(_hg_results(data), str(category))


def _hg_category_list(category, page=1):
    """Fetch a supported category listing via Apify and paginate its returned rows."""
    page = max(1, int(page))
    category = str(category or "").strip()
    if not category:
        return []
    if category.startswith("kw:"):
        return _hg_search(category[3:], page)
    return _hg_category_all(category, page)


@st.cache_data(ttl=180, show_spinner=False)
def _hg_search(keyword, page=1):
    data = _hg_api("search", {"keyword": str(keyword), "page": int(page or 1)})
    return _hg_rows_from_items(_hg_results(data), "search:" + str(keyword))


def _hg_load_page(mode, page):
    """ផ្ទុកទំព័រមួយតាម Mode (hot / category: / search:) — search ត្រូវ slice តាមទំព័រផង។"""
    mode = mode or "hot"
    page = max(1, int(page))
    if mode == "hot":
        return _hg_rank(page)
    if mode.startswith("category:"):
        return _hg_category_list(mode.split(":", 1)[1], page)
    if mode.startswith("search:"):
        return _hg_search(mode.split(":", 1)[1], page)
    return []


def _hg_get(endpoint, params=None, timeout=45):
    """Compatibility adapter for the app UI, now using XiaoYingAPI."""
    params = dict(params or {})
    if endpoint == "play":
        data = _hg_api("play", {"series_id": str(params.get("series_id") or ""),
                                 "ep": int(params.get("ep") or 1),
                                 "q": int(params.get("q") or 1080),
                                 "codec": str(params.get("codec") or "h264"),
                                 "mode": str(params.get("mode") or "pipe")}, timeout=timeout)
        if not isinstance(data, dict) or not str(data.get("url") or "").startswith(("http://", "https://")):
            raise RuntimeError("XiaoYingAPI មិនបានផ្ដល់ URL វីដេអូដែលអាចចាក់បានទេ។")
        return data
    return _hg_api(endpoint, params, timeout=timeout)


def _hg_extract_series_id(value):
    """ទទួលយក URL លម្អិត Hongguo ឬ series_id ដោយផ្ទាល់។"""
    value = str(value or "").strip()
    if not value:
        return ""
    # URL format: https://hongguoduanju.com/detail?series_id=123
    try:
        parsed = urllib.parse.urlparse(value)
        query = urllib.parse.parse_qs(parsed.query)
        ids = query.get("series_id") or query.get("seriesId") or []
        if ids and str(ids[0]).strip().isdigit():
            return str(ids[0]).strip()
        match = re.search(r"/(?:detail|player|series|drama)/(\d+)", parsed.path)
        if match:
            return match.group(1)
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)
    # User may paste only the numeric series_id.
    if value.isdigit():
        return value
    return ""


def _hg_error_khmer(err):
    """សារកំហុស Hongguo ជាខ្មែរ (មុននេះមិនទាន់បានកំណត់ ធ្វើឱ្យ NameError ពេលមានកំហុស)។"""
    return f"មានបញ្ហាក្នុងការទាញយកទិន្នន័យ Hongguo៖ {err}"


_HG_CAT_FN = _hg_categories          # រក្សាទុក function ដើម (ព្រោះ VIP block ប្តូរឈ្មោះនេះជា list)


_HG_KM = {
    "全部": "ទាំងអស់", "真人剧": "រឿងមនុស្សពិត", "漫剧": "រឿងគំនូរជីវចល", "AI剧": "រឿង AI", "漫画": "កំប្លែងគំនូរ",
    "爱情": "ស្នេហា", "年代": "យុគសម័យ", "逆袭": "ងើបតបវិញ", "传奇": "រឿងព្រេង", "成长": "ការលូតលាស់",
    "家庭": "គ្រួសារ", "家族": "ត្រកូល", "萌宝": "ទារកគួរឱ្យស្រលាញ់", "悬疑": "អាថ៌កំបាំង", "惊悚": "រន្ធត់",
    "恐怖": "ភ័យរន្ធត់", "志怪": "រឿងអរូបី", "古装": "ឈុតបុរាណ", "玄幻": "ទេវកថា", "奇幻": "ផ្សងព្រេងអស្ចារ្យ",
    "都市": "ទីក្រុង", "青春": "យុវវ័យ", "喜剧": "កំប្លែង", "科幻": "វិទ្យាសាស្ត្រប្រឌិត", "灾难": "គ្រោះមហន្តរាយ",
    "动作冒险": "សកម្មភាព-ផ្សងព្រេង", "战争": "សង្គ្រាម", "综艺": "កម្សាន្ត", "剧情": "ខ្សែរឿង",
    "穿越": "ឆ្លងកាលវេលា", "重生": "កើតជាថ្មី", "逆袭翻身": "ងើបតបវិញ", "都市爱情": "ស្នេហាទីក្រុង",
    "古风爱情": "ស្នេហាបុរាណ", "异能": "ថាមពលពិសេស", "家庭伦理": "សីលធម៌គ្រួសារ", "家族振兴": "ស្តារត្រកូល",
    "暗恋成真": "ស្នេហាសម្ងាត់បានសម្រេច", "轻喜剧": "កំប្លែងស្រាល", "反转": "ប្រែប្រួលភ្លាមៗ",
    "都市日常": "ជីវិតទីក្រុង", "都市玄幻": "ទីក្រុងទេវកថា", "玄学": "អាថ៌កំបាំងវិញ្ញាណ", "大女主": "ស្រីខ្លាំង",
    "重生逆袭": "កើតថ្មីងើបតប", "奇幻脑洞": "ការស្រមៃអស្ចារ្យ", "闪婚": "រៀបការរហ័ស", "闪婚": "រៀបការរហ័ស",
    "热门": "ពេញនិយម", "推荐": "ណែនាំ", "穿越重生": "ឆ្លងកាលវេលា-កើតថ្មី", "甜宠": "ស្នេហាផ្អែម",
    "虐恋": "ស្នេហាឈឺចាប់", "复仇": "សងសឹក", "总裁": "ប្រធានក្រុមហ៊ុន", "霸总": "ប្រធានក្រុមហ៊ុនអំណាច",
    "战神": "ម្ចាស់សង្គ្រាម", "神医": "គ្រូពេទ្យអច្ឆរិយៈ", "赘婿": "កូនប្រសារស្នាក់នៅ", "宫斗": "ទំនាស់ក្នុងវាំង",
}


@st.cache_resource
def _hg_km_cache():
    return {}


def _hg_km(text, max_len=4500):
    """បកអក្សរចិនជាខ្មែរ (វចនានុក្រមក្នុងកម្មវិធី មុន រួច Google Translate)។ អក្សរមិនមែនចិន → ទុកដដែល។"""
    t = str(text or "").strip()
    if not t or not CJK_RE.search(t):
        return t
    if t in _HG_KM:
        return _HG_KM[t]
    cache = _hg_km_cache()
    if t in cache:
        return cache[t]
    try:
        out = (google_translate_request(t[:max_len], retries=2) or "").strip()
    except Exception:
        return t
    if out:
        cache[t] = out
        return out
    return t


def _hg_km_many(texts):
    """បកច្រើនអត្ថបទស្របគ្នា → dict {ដើម: ខ្មែរ}។"""
    uniq = [t for t in dict.fromkeys(str(x or "").strip() for x in texts) if t]
    try:
        with ThreadPoolExecutor(max_workers=12) as ex:
            return dict(zip(uniq, ex.map(_hg_km, uniq)))
    except Exception:
        return {t: t for t in uniq}


@st.cache_data(ttl=600, show_spinner=False)
def _hg_category_tree():
    """ប្រភេទរឿងជាដើមឈើ: [{name, slug, children:[{name, slug}]}] — សម្រាប់ប៊ូតុងប្រភេទបែប hongguoduanju.com"""
    data = _hg_api("categories", {})
    roots = data.get("categories", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    out = []
    for root in roots:
        if not isinstance(root, dict) or not root.get("slug"):
            continue
        kids = [{"name": str(c.get("name") or c["slug"]), "slug": str(c["slug"])}
                for c in (root.get("children") or []) if isinstance(c, dict) and c.get("slug")]
        out.append({"name": str(root.get("name") or root["slug"]), "slug": str(root["slug"]), "children": kids})
    return out


def _hg_chips(key, options, default=None):
    """ប៊ូតុងជ្រើសរើសមួយ — ប្រើ st.button ធម្មតា (ផ្ទៃងងឹត អក្សរស) រៀបជាជួរតែមួយ អូសចំហៀងបាន។"""
    options = list(options)
    if not options:
        return default
    dflt = default if default in options else options[0]
    sel_key = f"_{key}_sel"
    cur = st.session_state.get(sel_key)
    if cur not in options:
        cur = dflt
        st.session_state[sel_key] = cur
    st.markdown(f"""<style>
.st-key-{key}[data-testid="stVerticalBlock"], .st-key-{key} > div[data-testid="stVerticalBlock"]{{
  display:flex !important; flex-direction:row !important; flex-wrap:nowrap !important;
  overflow-x:auto !important; gap:8px !important; padding:2px 0 8px !important; -webkit-overflow-scrolling:touch;}}
.st-key-{key} > div, .st-key-{key} [data-testid="stElementContainer"], .st-key-{key} [data-testid="stButton"]{{
  width:auto !important; flex:0 0 auto !important; min-width:0 !important;}}
.st-key-{key} button{{white-space:nowrap !important; width:auto !important; padding:6px 16px !important;
  border-radius:999px !important; background:#1d2766 !important; border:1.5px solid #4cc9ff !important;}}
.st-key-{key} button *{{color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; font-weight:700 !important; font-size:15px !important;}}
.st-key-{key} button[kind="primary"]{{background:linear-gradient(90deg,#ff2bb0,#2bb8ff) !important; border-color:transparent !important;}}
</style>""", unsafe_allow_html=True)
    clicked = None
    with st.container(key=key):
        for i, opt in enumerate(options):
            if st.button(str(opt), key=f"{key}__btn_{i}", type="primary" if opt == cur else "secondary"):
                clicked = opt
    if clicked is not None and clicked != cur:
        st.session_state[sel_key] = clicked
        st.rerun()
    st.session_state[f"_{key}_last"] = cur
    return cur


@st.cache_data(ttl=3600, show_spinner=False, max_entries=600)
def _hg_cover_b64(url):
    """ទាញ poster នៅ server រួចដាក់ជា data-URI (cache ១ ម៉ោង) ដើម្បីបង្ហាញក្នុងក្រឡា HTML លឿន។"""
    if not url:
        return ""
    data, _err = _hg_fetch_cover(url)
    return ("data:image/jpeg;base64," + base64.b64encode(data).decode()) if data else ""


def _hg_row_tags(row, limit=2):
    """ទាញស្លាកប្រភេទ (ឧ. 爱情 / 都市爱情) ពី field ណាមួយដែល API ផ្តល់។"""
    for k in ("tags", "tag_list", "tagList", "categories", "category_names", "category_list", "genres", "genre", "category"):
        v = row.get(k)
        if not v:
            continue
        if isinstance(v, str):
            v = [x for x in re.split(r"[,，/|·\s]+", v) if x]
        if isinstance(v, (list, tuple)):
            out = []
            for x in v:
                if isinstance(x, dict):
                    x = x.get("name") or x.get("title") or x.get("label") or ""
                x = str(x).strip()
                if x and x not in out:
                    out.append(x)
            if out:
                return out[:limit]
    return []


def _hg_poster_grid(rows, prefix="hg"):
    """ក្រឡា poster បែប hongguoduanju.com: រូបបញ្ឈរ + «全N集» + ឈ្មោះ (ត្រឹម ១ បន្ទាត់) + ស្លាក។
    ទូរស័ព្ទ ៣ ជួរ · ទំព័រធំ ៦ ជួរ។ ត្រឡប់ row ដែលអ្នកប្រើចុច «📦 ZIP» (ឬ None)។"""
    st.markdown(f"""<style>
.st-key-{prefix}_grid[data-testid="stVerticalBlock"], .st-key-{prefix}_grid > div[data-testid="stVerticalBlock"]{{
  display:grid !important; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px 8px; align-items:start;}}
@media (min-width:640px){{
  .st-key-{prefix}_grid[data-testid="stVerticalBlock"], .st-key-{prefix}_grid > div[data-testid="stVerticalBlock"]{{
    grid-template-columns:repeat(6,minmax(0,1fr)); gap:18px 10px;}} }}
.st-key-{prefix}_grid > *, .st-key-{prefix}_grid [data-testid="stVerticalBlock"]{{min-width:0 !important; gap:.25rem !important;}}
.st-key-{prefix}_grid .hgc{{position:relative; aspect-ratio:3/4; border-radius:8px; overflow:hidden; background:#1a2050;}}
.st-key-{prefix}_grid .hgc img{{width:100%; height:100%; object-fit:cover; display:block;}}
.st-key-{prefix}_grid .hgc .hgb{{position:absolute; right:0; bottom:0; font-size:11px; line-height:1; color:#fff;
  padding:3px 6px; background:linear-gradient(90deg,rgba(0,0,0,0),rgba(0,0,0,.55)); border-top-left-radius:6px;}}
.st-key-{prefix}_grid .hgn{{font-size:13px; font-weight:600; margin-top:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}}
.st-key-{prefix}_grid .hgt{{display:flex; gap:4px; margin-top:4px; overflow:hidden; white-space:nowrap;}}
.st-key-{prefix}_grid .hgt span{{font-size:10px; padding:1px 6px; border-radius:4px; background:rgba(128,128,128,.22); opacity:.85;}}
.st-key-{prefix}_grid button{{min-height:30px !important; padding:2px 6px !important; font-size:12px !important;}}
</style>""", unsafe_allow_html=True)
    rows = [r for r in rows if isinstance(r, dict) and r.get("series_id")]
    try:
        with ThreadPoolExecutor(max_workers=12) as _ex:
            _imgs = list(_ex.map(_hg_cover_b64, [str(r.get("cover") or "") for r in rows]))
    except Exception:
        _imgs = [""] * len(rows)
    _tmap = _hg_km_many([str(r.get('name') or '') for r in rows] + [t for r in rows for t in _hg_row_tags(r)])
    clicked = None
    with st.container(key=f"{prefix}_grid"):
        for r, b64 in zip(rows, _imgs):
            sid = r["series_id"]
            src = b64 or str(r.get("cover") or "")
            cnt = r.get("episode_cnt") or r.get("listed_cnt") or ""
            img = (f'<img src="{_esc(src, quote=True)}" referrerpolicy="no-referrer" loading="lazy">' if src
                   else '<div style="height:100%;display:flex;align-items:center;justify-content:center;font-size:30px">🎬</div>')
            badge = f'<div class="hgb">សរុប {_esc(str(cnt))} ភាគ</div>' if cnt else ""
            tags = "".join(f"<span>{_esc(_tmap.get(t, t))}</span>" for t in _hg_row_tags(r))
            _nm = str(r.get("name") or "រឿង").strip()
            name = _esc(_tmap.get(_nm, _nm))
            with st.container(key=f"{prefix}_card_{sid}"):
                st.markdown(f'<div class="hgc">{img}{badge}</div><div class="hgn" title="{name}">{name}</div>'
                            f'<div class="hgt">{tags}</div>', unsafe_allow_html=True)
                if st.button("📦 ZIP", key=f"{prefix}_select_{sid}", use_container_width=True):
                    clicked = r
    return clicked


def _hg_pager(cur, key="hg_pg"):
    """លេខទំព័របែប ‹ 1 … 4 5 6 ›។ ត្រឡប់លេខទំព័រដែលត្រូវទៅ (ឬ None)។"""
    cur = max(1, int(cur))
    pages = sorted({p for p in (1, cur - 1, cur, cur + 1) if p >= 1})
    tokens = [("‹", cur - 1, cur <= 1, False)]
    prev = 0
    for p in pages:
        if p - prev > 1:
            tokens.append(("…", None, True, False))
        tokens.append((str(p), p, p == cur, p == cur))
        prev = p
    tokens.append(("›", cur + 1, False, False))
    goto = None
    st.markdown("""<style>
.st-key-hg_pager [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important; gap:.25rem !important; max-width:420px; margin:0 auto;}
.st-key-hg_pager [data-testid="stColumn"]{min-width:0 !important; width:auto !important; flex:1 1 0 !important;}
.st-key-hg_pager button{padding:0 !important; min-height:36px !important;}
</style>""", unsafe_allow_html=True)
    with st.container(key="hg_pager"):
        cols = st.columns(len(tokens), gap="small")
        for i, (col, (label, target, disabled, active)) in enumerate(zip(cols, tokens)):
            with col:
                if st.button(label, key=f"{key}_{i}_{label}", use_container_width=True, disabled=disabled,
                             type="primary" if active else "secondary") and target:
                    goto = target
    return goto


# ---- Credentials: Secrets / Environment (ប្រើបានសម្រាប់អ្នកប្រើទាំងអស់) → ឯកសារ (Admin ដាក់) ----
_HG_APP_ID = _hg_secret("XIAOYING_APPID", "APPID", "HONGGUO_APPID") or _saved_id
_HG_APP_SECRET = _hg_secret("XIAOYING_APPSECRET", "APPSECRET", "HONGGUO_APPSECRET") or _saved_secret
_HG_API_READY = bool(_HG_APP_ID and _HG_APP_SECRET)


def _hg_ready():
    ss = st.session_state
    return bool(_HG_API_READY or (ss.get("user_hg_app_id") and ss.get("user_hg_app_secret")))


# auth_bootstrap()  # login removed


st.markdown(
    '<div style="display:flex;align-items:center;gap:12px;margin:2px 0 10px">'
    '<div style="font-size:34px;line-height:1">🍎</div>'
    '<div><div style="font-size:1.5rem;font-weight:800;line-height:1.2">Hongguo</div>'
    '<div style="opacity:.75;font-size:.9rem">ស្វែងរករឿង · ទាញយក ZIP</div></div></div>',
    unsafe_allow_html=True,
)
busy = False
tab_drama = st.container()

with tab_drama:
    _hg_access = True  # login removed: app is always unlocked
    if _hg_access:
        st.markdown("""<style>
/* ===== អក្សរច្បាស់ + scroll តិច ===== */
[data-testid="stPills"] button, [data-testid="stBaseButton-pills"], [data-testid="stBaseButton-pillsActive"]{
  background:#1b2352 !important; color:#ffffff !important; border:1px solid #4cc9ff !important;
  font-size:14px !important; font-weight:600 !important; opacity:1 !important;}
[data-testid="stPills"] button p, [data-testid="stBaseButton-pills"] p, [data-testid="stBaseButton-pillsActive"] p{color:#ffffff !important;}
[data-testid="stBaseButton-pillsActive"]{background:linear-gradient(90deg,#ff2bb0,#2bb8ff) !important; border-color:transparent !important;}
[data-testid="stPills"] > div, [data-testid="stPills"] [role="group"]{flex-wrap:nowrap !important; overflow-x:auto !important; padding-bottom:4px;}
[data-testid="stPills"] button{flex:0 0 auto !important; white-space:nowrap !important;}
[data-testid="stTextInput"] input{color:#ffffff !important; background:#10163a !important; font-size:15px !important;}
[data-testid="stTextInput"] input::placeholder{color:#b9c2ff !important; opacity:1 !important;}
label, [data-testid="stWidgetLabel"] p, .stCaption, [data-testid="stCaptionContainer"]{color:#eef1ff !important; opacity:1 !important;}
[data-baseweb="select"] *{color:#ffffff !important;}
[data-baseweb="select"] > div{background:#10163a !important;}
[data-baseweb="tag"]{background:#2b3a8f !important;} [data-baseweb="tag"] *{color:#fff !important;}
[class*="_grid"] .hgn{font-size:14px !important; color:#ffffff !important; white-space:normal !important;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; line-height:1.3; min-height:2.6em;}
</style>""", unsafe_allow_html=True)
        if _is_admin_session():
          with st.expander("🔑 Admin: ដាក់ API Key ជំនួស Secrets (ជម្រើស)", expanded=not _hg_ready()):
            st.caption("ជាធម្មតា Key ដាក់ក្នុង Streamlit Secrets (XIAOYING_APPID / XIAOYING_APPSECRET) ហើយអ្នកប្រើគ្រប់គ្នាប្រើបាន។ "
                       "ប្រអប់នេះជាជម្រើសបន្ថែម — Secrets មានអាទិភាពជាង ហើយអ្នកប្រើទូទៅមិនឃើញប្រអប់នេះទេ។")
            _hg_in_id = st.text_input("APP ID", key="hg_in_appid",
                                      value=st.session_state.get("user_hg_app_id") or _HG_APP_ID)
            _hg_in_sec = st.text_input("APP SECRET", key="hg_in_appsecret", type="password",
                                       value=st.session_state.get("user_hg_app_secret") or _HG_APP_SECRET)
            _hg_k1, _hg_k2 = st.columns(2)
            with _hg_k1:
                if st.button("💾 រក្សាទុក Key", key="hg_keys_save", type="primary", use_container_width=True):
                    _hg_save_keys(_hg_in_id, _hg_in_sec)
                    st.rerun()
            with _hg_k2:
                if st.button("🗑️ លុប Key", key="hg_keys_clear", use_container_width=True):
                    _hg_save_keys("", "")
                    st.rerun()
        if not _hg_ready():
            st.warning("មិនទាន់កំណត់ APP ID និង APP SECRET ទេ។ សូម Admin ដាក់ក្នុង Streamlit Secrets (XIAOYING_APPID និង XIAOYING_APPSECRET)។")
        _hg_q1, _hg_q2 = st.columns([3, 1])
        with _hg_q1:
            _hg_keyword = st.text_input("ស្វែងរកឈ្មោះរឿង ឬបិទភ្ជាប់ Link / series_id", key="hg_search_text", placeholder="ឈ្មោះរឿង ឬ https://hongguoduanju.com/detail?series_id=...")
        with _hg_q2:
            st.write("")
            _hg_search_click = st.button("🔎 ស្វែងរក", key="hg_search_btn", use_container_width=True)
        if "_hg_rows" not in st.session_state:
            st.session_state["_hg_rows"] = []
        if "_hg_page" not in st.session_state:
            st.session_state["_hg_page"] = 1
        if "_hg_catalog_mode" not in st.session_state:
            st.session_state["_hg_catalog_mode"] = "hot"
        try:
            _hg_tree = _hg_category_tree() if _hg_ready() else []
        except Exception as _cat_err:
            _hg_tree = []
            st.caption(f"មិនអាចទាញយកប្រភេទរឿងបាន៖ {_cat_err}")
        _HG_HOT = "🔥 ពេញនិយម"
        _hg_roots = {_HG_HOT: None}
        for _r in _hg_tree:
            _kn = _hg_km(_r["name"])
            _hg_roots[_kn if _kn not in _hg_roots else f"{_kn} ({_r['slug']})"] = _r
        _hg_root_name = _hg_chips("hg_root_chip", list(_hg_roots), default=_HG_HOT)
        _hg_root = _hg_roots.get(_hg_root_name)
        _hg_mode_new = "hot"
        if _hg_root:
            _hg_all_lbl = _hg_km("全部")
            _hg_subs = {_hg_all_lbl: _hg_root["slug"]}
            _kmap = _hg_km_many([_c["name"] for _c in _hg_root.get("children", [])])
            for _c in _hg_root.get("children", []):
                _kn = _kmap.get(_c["name"].strip(), _c["name"])
                _hg_subs[_kn if _kn not in _hg_subs else f"{_kn} ({_c['slug']})"] = _c["slug"]
            _hg_sub_name = _hg_chips(f"hg_sub_chip_{_hg_root['slug']}", list(_hg_subs), default=_hg_all_lbl)
            _hg_mode_new = "category:" + _hg_subs.get(_hg_sub_name, _hg_root["slug"])
        if st.button("🔄 ផ្ទុកប្រភេទឡើងវិញ", key="hg_refresh_categories"):
            for _fn in (_hg_category_tree, _HG_CAT_FN, _hg_rank_all, _hg_category_all, _hg_search):
                try:
                    _fn.clear()
                except Exception as _swallow_e:
                    _log_swallowed(_swallow_e)
            st.rerun()
        _hg_chip_changed = _hg_mode_new != st.session_state.get("_hg_chip_sig")
        st.session_state["_hg_chip_sig"] = _hg_mode_new
        if _hg_search_click and _hg_keyword.strip():
            st.session_state["_hg_page"] = 1
            st.session_state["_hg_catalog_mode"] = "search:" + _hg_keyword.strip()
            try:
                _direct_series_id = _hg_extract_series_id(_hg_keyword)
                if _direct_series_id:
                    with st.spinner("កំពុងបើករឿងតាម Link..."):
                        _direct_detail = _hg_detail(_direct_series_id)
                    st.session_state["_hg_selected"] = {
                        "series_id": _direct_series_id,
                        "name": _direct_detail.get("name") or "រឿង Hongguo",
                        "cover": _direct_detail.get("cover") or "",
                        "episode_cnt": _direct_detail.get("episode_cnt") or "",
                        "listed_cnt": _direct_detail.get("listed_cnt") or "",
                        "intro": _direct_detail.get("intro") or "",
                    }
                    st.session_state["_hg_rows"] = []
                    st.rerun()
                else:
                    with st.spinner("កំពុងស្វែងរករឿង..."):
                        try:
                            st.session_state["_hg_rows"] = _hg_search(_hg_keyword.strip())
                        except RuntimeError as _se:
                            if "Actor ត្រឡប់" in str(_se):
                                st.session_state["_hg_rows"] = []
                            else:
                                raise
                    st.session_state.pop("_hg_selected", None)
                    if not st.session_state["_hg_rows"]:
                        st.info("រកមិនឃើញរឿងទេ។ សូមបិទភ្ជាប់ Link ទំព័ររឿង (…/detail?series_id=…) ឬ series_id ។ Link /player/… អាចជាលេខភាព មិនមែនលេខរឿង។")
            except Exception as e:
                st.error(str(e))
        elif _hg_ready() and (_hg_chip_changed or (not st.session_state["_hg_rows"]
                                                   and st.session_state.get("_hg_catalog_mode", "hot") == "hot")):
            try:
                st.session_state["_hg_page"] = 1
                st.session_state["_hg_catalog_mode"] = _hg_mode_new
                st.session_state.pop("_hg_selected", None)
                with st.spinner("កំពុងទាញយកបញ្ជីរឿង..."):
                    st.session_state["_hg_rows"] = _hg_load_page(_hg_mode_new, 1)
                if not st.session_state["_hg_rows"]:
                    st.warning("រកមិនឃើញរឿងក្នុងប្រភេទនេះទេ។ សាកប្រភេទផ្សេង។")
            except Exception as e:
                st.session_state["_hg_rows"] = []
                st.error(_hg_error_khmer(e))
        _hg_rows = [r for r in st.session_state.get("_hg_rows", []) if isinstance(r, dict) and r.get("series_id")]
        _hg_selected = st.session_state.get("_hg_selected")
        if _hg_selected:
            if st.button("← ត្រឡប់ទៅបញ្ជីរឿង", key="hg_back", use_container_width=True):
                st.session_state.pop("_hg_selected", None)
                st.rerun()
            st.subheader(_hg_km(_hg_selected.get("name") or "រឿង"))
            try:
                with st.spinner("កំពុងទាញយកបញ្ជីភាគ..."):
                    _hg_d = _hg_detail(_hg_selected["series_id"])
                _hg_eps = [e for e in (_hg_d.get("episodes") or []) if isinstance(e, dict) and (e.get("playable") or e.get("video_id") or e.get("url"))]
                if not _hg_eps:
                    st.info("រឿងនេះមិនទាន់មានភាគដែលអាចចាក់បានទេ។")
                else:
                    _hg_ep_map = {f"ភាគ {int(e.get('ep', i+1))}": int(e.get('ep', i+1)) for i,e in enumerate(_hg_eps)}
                    _hg_c1, _hg_c2 = st.columns(2)
                    with _hg_c1:
                        _hg_quality = st.selectbox("គុណភាព", [360,480,540,720,1080], index=3, key=f"hg_q_{_hg_selected['series_id']}")
                    with _hg_c2:
                        _hg_codec = st.selectbox("Codec", ["h264", "hevc"], key=f"hg_codec_{_hg_selected['series_id']}")

                    # Download multiple Hongguo episodes in one ZIP (all or selected)
                    st.markdown("#### 📦 ទាញយក ZIP")
                    _hg_dl_all = st.checkbox(
                        f"ជ្រើសរើសភាគទាំងអស់ ({len(_hg_ep_map)} ភាគ)",
                        value=False,
                        key=f"hg_dl_all_{_hg_selected['series_id']}"
                    )
                    _hg_dl_labels = st.multiselect(
                        "ឬជ្រើសរើសតែភាគដែលចង់ទាញយក",
                        list(_hg_ep_map.keys()),
                        default=list(_hg_ep_map.keys()) if _hg_dl_all else [],
                        key=f"hg_dl_eps_{_hg_selected['series_id']}"
                    )
                    _hg_dl_max = st.selectbox(
                        "ចំនួនអតិបរមាក្នុងមួយលើក",
                        [5, 10, 20, 50, 100],
                        index=2,
                        key=f"hg_dl_limit_{_hg_selected['series_id']}"
                    )
                    if st.button(
                        f"📦 ទាញយក {_hg_dl_labels.__len__() if _hg_dl_all else len(_hg_dl_labels)} ភាគជា ZIP",
                        key=f"hg_dl_start_{_hg_selected['series_id']}",
                        disabled=(not (_hg_dl_all or _hg_dl_labels) or busy),
                        use_container_width=True
                    ):
                        _chosen_dl_labels = list(_hg_ep_map.keys()) if _hg_dl_all else list(_hg_dl_labels)
                        _chosen_dl_labels = _chosen_dl_labels[:_hg_dl_max]
                        _dl_folder = tempfile.mkdtemp(prefix="hongguo_batch_")
                        _dl_zip_path = os.path.join(_dl_folder, "hongguo_episodes.zip")
                        _dl_errors = []
                        _dl_ok = 0
                        _dl_bar = st.progress(0, text="កំពុងរៀបចំភាគសម្រាប់ទាញយក...")
                        try:
                            with zipfile.ZipFile(_dl_zip_path, "w", compression=zipfile.ZIP_STORED) as _dl_zip:
                                for _di, _dl_label in enumerate(_chosen_dl_labels, start=1):
                                    _dl_ep = _hg_ep_map[_dl_label]
                                    _dl_tmp = None
                                    try:
                                        _dl_play = _hg_get("play", {"series_id": _hg_selected["series_id"], "ep": _dl_ep, "q": _hg_quality, "codec": _hg_codec})
                                        _dl_url = str(_dl_play.get("url") or "").strip()
                                        if not _dl_url:
                                            raise RuntimeError("API មិនបានផ្ដល់តំណវីដេអូ")
                                        _dl_result = _fetch_one(_dl_url)
                                        if not _dl_result.get("ok") or not _dl_result.get("path"):
                                            raise RuntimeError(_dl_result.get("err") or "ទាញយកវីដេអូមិនបាន")
                                        _dl_tmp = _dl_result["path"]
                                        _dl_size = os.path.getsize(_dl_tmp)
                                        _dl_current = sum(x.file_size for x in _dl_zip.filelist)
                                        if _dl_current + _dl_size > MAX_ZIP_MB * 1024 * 1024:
                                            raise RuntimeError(f"ទំហំ ZIP លើសកំណត់ {MAX_ZIP_MB}MB")
                                        _dl_zip.write(_dl_tmp, f"episode_{_dl_ep:04d}.mp4")
                                        _dl_ok += 1
                                    except Exception as _dl_err:
                                        _dl_errors.append(f"ភាគ {_dl_ep}: {str(_dl_err)[:180]}")
                                    finally:
                                        if _dl_tmp:
                                            shutil.rmtree(os.path.dirname(_dl_tmp), ignore_errors=True)
                                    _dl_bar.progress(_di / max(1, len(_chosen_dl_labels)), text=f"ទាញយកបាន {_dl_ok}/{len(_chosen_dl_labels)} ភាគ · កំពុងដំណើរការ {_di}/{len(_chosen_dl_labels)}")
                            _dl_bar.empty()
                            if _dl_ok:
                                st.session_state[f"_hg_dl_ready_{_hg_selected['series_id']}"] = {
                                    "path": _dl_zip_path,
                                    "folder": _dl_folder,
                                    "count": _dl_ok,
                                    "name": safe_filename(_hg_selected.get("name") or "hongguo")
                                }
                                st.success(f"បានរៀបចំទាញយកបាន {_dl_ok} ភាគរួចរាល់។")
                            else:
                                shutil.rmtree(_dl_folder, ignore_errors=True)
                                st.error("មិនអាចទាញយកភាគណាមួយបានទេ។")
                            if _dl_errors:
                                with st.expander(f"មើលភាគដែលមានបញ្ហា ({len(_dl_errors)})"):
                                    for _de in _dl_errors:
                                        st.warning(_de)
                        except Exception as _dl_fatal:
                            shutil.rmtree(_dl_folder, ignore_errors=True)
                            st.error(f"រៀបចំ ZIP មិនបាន៖ {_dl_fatal}")
                    _dl_ready = st.session_state.get(f"_hg_dl_ready_{_hg_selected['series_id']}")
                    if _dl_ready and os.path.isfile(_dl_ready.get("path", "")):
                        with open(_dl_ready["path"], "rb") as _dl_file:
                            dl_button(
                                f"⬇️ ទាញយក ZIP ({_dl_ready['count']} ភាគ)",
                                _dl_file,
                                f"{_dl_ready['name']}_episodes.zip",
                                "application/zip",
                                key=f"hg_dl_file_{_hg_selected['series_id']}",
                                use_container_width=True
                            )


            except Exception as e:
                st.error(str(e))
        elif _hg_rows:
            _hg_clicked = _hg_poster_grid(_hg_rows, "hg")
            if _hg_clicked:
                st.session_state["_hg_selected"] = _hg_clicked
                st.rerun()
            _hg_cur_page = st.session_state.get("_hg_page", 1)
            _hg_goto = _hg_pager(_hg_cur_page)
            if _hg_goto:
                _mode = st.session_state.get("_hg_catalog_mode", "hot")
                _hg_new_rows = None
                try:
                    with st.spinner(f"កំពុងបើកទំព័រ {_hg_goto}... (លើកដំបូងអាចយូរបន្តិច)"):
                        _hg_new_rows = _hg_load_page(_mode, _hg_goto)
                except Exception as e:
                    st.error(str(e))
                if _hg_new_rows:
                    st.session_state["_hg_page"] = _hg_goto
                    st.session_state["_hg_rows"] = _hg_new_rows
                    st.rerun()
                elif _hg_new_rows is not None:
                    st.info("គ្មានរឿងបន្ថែមទៀតទេ។")


SCREENSHOT_LAYOUT_CORRECTION_CSS = """
<style>
/* Restore the Angkor background and animated neon light beams. */
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"] {
  background-color:#05091d !important;
  color:#f7f8ff !important;
}
.stApp::before {
  content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
  background:
    repeating-linear-gradient(112deg,transparent 0 13%,rgba(0,220,255,.10) 13.15%,transparent 13.5% 28%),
    linear-gradient(105deg,transparent 35%,rgba(255,25,170,.16) 48%,transparent 62%);
  background-size:190% 100%,230% 100%;
  animation:kvai-screenshot-lights 7s linear infinite;
}
@keyframes kvai-screenshot-lights {
  from {background-position:190% 0,210% 0}
  to {background-position:-20% 0,-30% 0}
}
[data-testid="stMain"] > div, .block-container {position:relative;z-index:1}

/* Do not lock the document to a short viewport or clip widgets. */
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"] {
  height:auto !important; min-height:100% !important;
  max-height:none !important; overflow-x:hidden !important; overflow-y:auto !important;
}
[data-testid="stMain"] {overflow:visible !important}
.block-container {
  height:auto !important; min-height:100dvh !important; max-height:none !important;
  overflow:visible !important; max-width:1800px !important;
  padding:4px 10px 12px !important;
}

/* Remove the large blank band after the header and compact orientation control. */
.kvai-head {height:76px !important;min-height:76px !important;max-height:76px !important;
  margin:0 0 3px !important;padding:5px 12px !important}
.kvai-logo {width:44px !important;height:44px !important;flex-basis:44px !important}
.kvai-title .kvai-h1 {font-size:clamp(1.05rem,2vw,1.5rem) !important}
.kvai-title p {font-size:.72rem !important;margin:0 !important}
.kvai-badge {font-size:.72rem !important;padding:4px 9px !important}
iframe[title="streamlit.components.v1.html"] {
  display:block !important;height:32px !important;max-height:32px !important;
  margin:0 !important;padding:0 !important;
}
[data-testid="stElementContainer"]:has(iframe[title="streamlit.components.v1.html"]) {
  height:32px !important;min-height:32px !important;margin:0 !important;padding:0 !important;
}
[data-testid="stVerticalBlock"] {gap:.25rem !important}
[data-testid="stElementContainer"] {margin-bottom:0 !important}

/* Tabs and dashboard columns: compact desktop proportions, preserve clickability. */
[data-baseweb="tab-list"] {display:flex !important;gap:4px !important;
  margin:2px 0 4px !important;padding:3px !important}
button[data-baseweb="tab"] {height:36px !important;min-width:0 !important;padding:0 8px !important}
button[data-baseweb="tab"] p {font-size:.78rem !important;white-space:nowrap !important}
[data-baseweb="tab-panel"] {height:auto !important;max-height:none !important;
  overflow:visible !important;padding:2px 0 8px !important}
[data-testid="stHorizontalBlock"] {gap:.4rem !important;flex-wrap:nowrap !important}
[data-testid="stColumn"] {min-width:0 !important}
[data-testid="stWidgetLabel"] p {font-size:.75rem !important;margin-bottom:1px !important}
[data-testid="stFileUploaderDropzone"] {min-height:46px !important;padding:3px 6px !important}
[data-testid="stVideo"] video {max-height:130px !important;object-fit:contain !important}
.kvai-empty-preview {height:130px !important}
.stButton>button,.stDownloadButton>button {min-height:34px !important;font-size:.76rem !important}

/* Critical: never pin the start button over the dashboard. Its container is before tabs,
   so it becomes a compact action strip directly above the tab row. */
.st-key-startbar {
  position:relative !important;inset:auto !important;left:auto !important;bottom:auto !important;
  transform:none !important;width:100% !important;z-index:4 !important;
  margin:2px 0 4px !important;padding:3px 8px !important;
  background:linear-gradient(90deg,rgba(255,20,147,.18),rgba(6,15,48,.94),rgba(0,210,255,.18)) !important;
  border:1px solid rgba(0,220,255,.55) !important;border-radius:12px !important;
  box-shadow:0 0 13px rgba(0,190,255,.15) !important;
}
.st-key-startbar [data-testid="stVerticalBlockBorderWrapper"],
.st-key-startbar [data-testid="stVerticalBlock"] {
  background:transparent !important;border:0 !important;box-shadow:none !important;
}
.st-key-startbar .stButton>button,.st-key-startbar .stButton>button:disabled {
  min-height:38px !important;opacity:1 !important;color:#fff !important;
  border:1px solid #19ddff !important;border-radius:11px !important;
  background:linear-gradient(100deg,#ff1493,#843bff,#00cfff) !important;
  box-shadow:0 0 14px rgba(0,207,255,.25) !important;
}

/* Keep warning compact so it does not push the workspace down. */
[data-testid="stAlert"] {padding:6px 10px !important;margin:3px 0 5px !important}
[data-testid="stAlert"] p {font-size:.78rem !important;line-height:1.25 !important;margin:0 !important}

/* Landscape: fit the desktop-like layout more tightly without clipping the controls.
   If a device has an unusually short viewport, natural scrolling remains available
   rather than making buttons unreachable. */
@media (orientation:landscape) and (min-width:700px) {
  .block-container {padding:3px 8px 8px !important}
  .kvai-head {height:68px !important;min-height:68px !important;max-height:68px !important}
  .kvai-logo {width:39px !important;height:39px !important;flex-basis:39px !important}
  .kvai-title p {font-size:.66rem !important}
  button[data-baseweb="tab"] {height:33px !important}
  [data-testid="stVideo"] video,.kvai-empty-preview {max-height:112px !important;height:112px !important}
  [data-testid="stFileUploaderDropzone"] {min-height:38px !important}
  [data-testid="stWidgetLabel"] p {font-size:.69rem !important}
  .stButton>button,.stDownloadButton>button {min-height:30px !important;font-size:.69rem !important}
  .st-key-startbar .stButton>button {min-height:34px !important}
}
@media (orientation:portrait) {
  .kvai-head {height:auto !important;min-height:68px !important;max-height:none !important}
}
</style>
"""
st.markdown(SCREENSHOT_LAYOUT_CORRECTION_CSS, unsafe_allow_html=True)

# =====================================================================
# FINAL DESKTOP MODE — landscape phone behaves like a compact desktop UI
# Keep the three-column workspace, shrink the whole interface to the viewport,
# collapse optional settings, and reserve a small non-overlapping action bar.
# =====================================================================
DESKTOP_MODE_VIEWPORT_CSS = r"""
<style>
@media screen and (orientation:landscape) and (max-height:700px) and (min-width:600px) {
  html { zoom:.80 !important; }
  html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    width:100% !important; height:100dvh !important; min-height:100dvh !important;
    max-height:100dvh !important; overflow:hidden !important;
  }
  .block-container {
    width:125vw !important; max-width:none !important; height:125dvh !important;
    min-height:0 !important; max-height:125dvh !important; overflow:hidden !important;
    padding:3px 8px 42px !important; margin:0 !important;
  }
  [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
  [data-testid="stStatusWidget"] {display:none !important;height:0 !important}
  [data-testid="stVerticalBlock"] {gap:.16rem !important}
  [data-testid="stElementContainer"] {margin:0 !important;padding:0 !important}
  .kvai-head {height:52px !important;min-height:52px !important;max-height:52px !important;
    margin:0 0 2px !important;padding:3px 8px !important;gap:6px !important}
  .kvai-logo {width:34px !important;height:34px !important;flex:0 0 34px !important;font-size:18px !important}
  .kvai-title .kvai-h1 {font-size:1.08rem !important;line-height:1 !important}
  .kvai-title p {display:none !important}
  .kvai-badge {font-size:.62rem !important;padding:3px 7px !important}
  iframe[title="streamlit.components.v1.html"] {height:20px !important;max-height:20px !important}
  [data-testid="stElementContainer"]:has(iframe[title="streamlit.components.v1.html"]) {
    height:20px !important;min-height:20px !important;margin:0 !important;padding:0 !important}
  /* Desktop-style tabs: all seven stay in one row. */
  [data-baseweb="tab-list"] {display:flex !important;flex-wrap:nowrap !important;gap:3px !important;
    padding:2px !important;margin:1px 0 3px !important;overflow:hidden !important}
  button[data-baseweb="tab"] {flex:1 1 0 !important;min-width:0 !important;height:29px !important;
    padding:0 2px !important;border-radius:7px !important}
  button[data-baseweb="tab"] p {font-size:.66rem !important;white-space:nowrap !important;
    overflow:hidden !important;text-overflow:ellipsis !important}
  [data-baseweb="tab-panel"] {height:calc(100dvh - 112px) !important;max-height:calc(100dvh - 112px) !important;
    overflow:hidden !important;padding:0 !important}
  /* Keep the real 3-column desktop dashboard; never stack the columns. */
  [data-testid="stHorizontalBlock"] {display:flex !important;flex-wrap:nowrap !important;gap:.25rem !important}
  [data-testid="stColumn"] {min-width:0 !important;flex:1 1 0 !important}
  .kvai-panel-title {font-size:.70rem !important;padding:2px 5px !important;margin:0 0 1px !important}
  .kvai-step {width:19px !important;height:19px !important;font-size:.64rem !important}
  div[data-testid="stVerticalBlockBorderWrapper"] {padding:2px !important;border-radius:8px !important}
  [data-testid="stWidgetLabel"] p, .stApp label {font-size:.62rem !important;margin:0 !important;line-height:1.02 !important}
  [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
    font-size:.53rem !important;line-height:1.02 !important;margin:0 !important}
  [data-testid="stFileUploaderDropzone"] {min-height:31px !important;padding:1px 3px !important}
  [data-testid="stFileUploaderDropzoneInstructions"] {padding:0 !important}
  [data-testid="stFileUploaderDropzoneInstructions"] span,
  [data-testid="stFileUploaderDropzoneInstructions"] small {font-size:.53rem !important}
  [data-testid="stVideo"] video, .kvai-empty-preview {height:72px !important;max-height:72px !important}
  .kvai-play {width:29px !important;height:29px !important;font-size:14px !important}
  .kvai-filmstrip {display:none !important}
  [data-baseweb="select"]>div {min-height:25px !important}
  .stTextInput input, .stNumberInput input {min-height:24px !important}
  .stTextArea textarea {height:34px !important;min-height:34px !important}
  .stButton>button, .stDownloadButton>button {min-height:25px !important;padding:1px 4px !important;
    font-size:.60rem !important;border-radius:6px !important}
  [data-testid="stRadio"] [role="radiogroup"] {gap:2px !important;flex-wrap:nowrap !important}
  [data-testid="stRadio"] label {padding:2px 3px !important;font-size:.56rem !important}
  [data-testid="stToggle"], [data-testid="stCheckbox"], [data-testid="stSlider"] {padding:0 !important}
  [data-testid="stExpander"] summary {min-height:22px !important;padding:1px 5px !important}
  [data-testid="stExpander"] summary p {font-size:.60rem !important}
  [data-testid="stAlert"] {padding:2px 5px !important;margin:1px 0 !important}
  [data-testid="stAlert"] p {font-size:.57rem !important;line-height:1.02 !important}
  /* Start button fixed to the screen edge; slot is now at document end, not above the tabs. */
  .st-key-startbar {position:fixed !important;left:0 !important;right:0 !important;bottom:0 !important;
    transform:none !important;width:100% !important;z-index:1000 !important;margin:0 !important;
    padding:2px 6px !important;border-radius:0 !important;
    background:linear-gradient(90deg,rgba(255,20,147,.2),rgba(4,9,30,.97),rgba(0,210,255,.2)) !important;
    border-top:1px solid rgba(0,220,255,.5) !important;backdrop-filter:blur(7px) !important}
  .st-key-startbar [data-testid="stVerticalBlockBorderWrapper"],
  .st-key-startbar [data-testid="stVerticalBlock"] {background:transparent !important;border:0 !important;box-shadow:none !important}
  .st-key-startbar .stButton>button {min-height:28px !important;font-size:.68rem !important;
    padding:1px 5px !important;color:#fff !important;opacity:1 !important}
}
</style>
"""
st.markdown(DESKTOP_MODE_VIEWPORT_CSS, unsafe_allow_html=True)


# =====================================================================
# FINAL MOBILE-FIRST RESTORE — normal phone layout, playable video preview
# Overrides legacy landscape/desktop rules above.
# =====================================================================
MOBILE_NORMAL_NEON_CSS = r"""
<style>
:root { color-scheme: dark; }
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"] {
  width:100% !important; min-height:100% !important; height:auto !important;
  max-height:none !important; overflow-x:hidden !important; overflow-y:auto !important;
  background:radial-gradient(ellipse at 5% 8%,rgba(255,20,147,.22),transparent 32%),
    radial-gradient(ellipse at 95% 12%,rgba(0,210,255,.20),transparent 34%),
    linear-gradient(145deg,#03091e 0%,#10133d 52%,#06172e 100%) !important;
  color:#f7f8ff !important;
}
.stApp::before {content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background:linear-gradient(115deg,transparent 35%,rgba(0,220,255,.08) 48%,rgba(255,20,147,.07) 52%,transparent 65%);
  background-size:240% 100%;animation:kvai-mobile-light 8s linear infinite}
@keyframes kvai-mobile-light {from{background-position:180% 0}to{background-position:-60% 0}}
.block-container {width:100% !important;max-width:100% !important;height:auto !important;
  min-height:0 !important;max-height:none !important;overflow:visible !important;
  padding:.55rem .65rem 1.2rem !important;margin:0 auto !important;position:relative;z-index:1}
[data-testid="stMain"] {height:auto !important;min-height:0 !important;overflow:visible !important}
[data-testid="stVerticalBlock"] {gap:.65rem !important}
[data-testid="stElementContainer"] {margin:0 !important}
.kvai-head {height:auto !important;min-height:66px !important;max-height:none !important;
  margin:0 0 8px !important;padding:8px 10px !important;gap:9px !important;flex-wrap:nowrap !important}
.kvai-logo {width:42px !important;height:42px !important;flex:0 0 42px !important;font-size:22px !important}
.kvai-title {min-width:0 !important}
.kvai-title .kvai-h1 {font-size:clamp(1.05rem,5vw,1.45rem) !important;line-height:1.15 !important}
.kvai-title p {display:block !important;font-size:.68rem !important;line-height:1.25 !important}
.kvai-badge {font-size:.66rem !important;padding:4px 7px !important;white-space:nowrap !important}
[data-baseweb="tab-list"] {display:flex !important;flex-wrap:nowrap !important;overflow-x:auto !important;
  overflow-y:hidden !important;gap:4px !important;scrollbar-width:thin !important}
button[data-baseweb="tab"] {flex:0 0 auto !important;min-width:max-content !important;height:40px !important;padding:0 10px !important}
button[data-baseweb="tab"] p {font-size:.78rem !important;white-space:nowrap !important}
[data-baseweb="tab-panel"] {height:auto !important;max-height:none !important;overflow:visible !important;padding:4px 0 !important}
/* Standard mobile: the three desktop columns become a clean vertical flow. */
[data-testid="stHorizontalBlock"] {display:flex !important;flex-wrap:wrap !important;flex-direction:column !important;
  gap:.65rem !important;align-items:stretch !important}
[data-testid="stColumn"] {width:100% !important;min-width:100% !important;max-width:100% !important;flex:1 1 100% !important}
.kvai-panel-title {font-size:1rem !important;margin:2px 0 5px !important}
div[data-testid="stVerticalBlockBorderWrapper"] {padding:7px 6px !important;border-radius:14px !important}
[data-testid="stWidgetLabel"] p,.stApp label {font-size:.88rem !important;line-height:1.3 !important}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p {font-size:.75rem !important;line-height:1.35 !important}
[data-testid="stFileUploaderDropzone"] {min-height:78px !important;padding:12px !important}
[data-testid="stVideo"] {width:100% !important;max-width:100% !important;overflow:visible !important}
[data-testid="stVideo"] video {display:block !important;width:100% !important;max-height:min(52vh,360px) !important;
  height:auto !important;min-height:150px !important;object-fit:contain !important;pointer-events:auto !important;
  background:#000 !important;border-radius:12px !important}
.kvai-empty-preview {height:190px !important;max-height:none !important;min-height:150px !important}
.kvai-play {width:54px !important;height:54px !important;font-size:24px !important}
.kvai-filmstrip {display:flex !important}
[data-baseweb="select"]>div {min-height:42px !important}
.stTextInput input,.stNumberInput input {min-height:42px !important}
.stTextArea textarea {min-height:76px !important}
.stButton>button,.stDownloadButton>button {min-height:42px !important;font-size:.88rem !important}
[data-testid="stExpander"] {margin:5px 0 !important}
[data-testid="stExpander"] details {overflow:visible !important}
/* Start button is in normal flow, never fixed over the video player. */
.st-key-startbar {position:static !important;left:auto !important;right:auto !important;bottom:auto !important;
  transform:none !important;width:100% !important;z-index:1 !important;margin:8px 0 0 !important;
  padding:5px 0 !important;background:transparent !important;border:0 !important;backdrop-filter:none !important}
.st-key-startbar [data-testid="stVerticalBlockBorderWrapper"],
.st-key-startbar [data-testid="stVerticalBlock"] {background:transparent !important;border:0 !important;box-shadow:none !important}
.st-key-startbar .stButton>button {min-height:48px !important;font-size:.95rem !important}
.stApp::before {pointer-events:none !important}
/* Wider screens keep the original desktop columns; phone widths stay mobile-first. */
@media (min-width:760px) {
  .block-container {max-width:1200px !important;padding:1rem 1.2rem 2rem !important}
  [data-testid="stHorizontalBlock"] {flex-direction:row !important;flex-wrap:nowrap !important}
  [data-testid="stColumn"] {min-width:0 !important;max-width:none !important;flex:1 1 0 !important}
}
</style>
"""
st.markdown(MOBILE_NORMAL_NEON_CSS, unsafe_allow_html=True)


# =====================================================================
# FINAL POLISHED MOBILE LAYOUT
# Keep the existing feature locations and horizontal dashboard grouping.
# No orientation lock, no fixed overlays, and no forced vertical stacking.
# =====================================================================
POLISHED_MOBILE_LAYOUT_CSS = r"""
<style>
/* Always let the normal mobile page size itself naturally; do not clip content. */
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"] {
  height:auto !important; min-height:100% !important; max-height:none !important;
  overflow-x:hidden !important; overflow-y:auto !important;
}
[data-testid="stMain"] { overflow:visible !important; }
.block-container { height:auto !important; max-height:none !important; overflow:visible !important; }

/* Tight, consistent page frame */
.block-container {
  width:100% !important; max-width:100% !important;
  padding: .42rem .5rem .8rem !important;
  margin: 0 auto !important;
}
[data-testid="stVerticalBlock"] { gap:.38rem !important; }
[data-testid="stElementContainer"] { margin:0 !important; }

/* Header: slightly larger, aligned in one row */
.kvai-head {
  display:flex !important; flex-direction:row !important; flex-wrap:nowrap !important;
  align-items:center !important; justify-content:flex-start !important;
  width:100% !important; min-height:78px !important; height:78px !important;
  max-height:78px !important; box-sizing:border-box !important;
  gap:10px !important; margin:0 0 5px !important; padding:7px 10px !important;
}
.kvai-logo {
  flex:0 0 46px !important; width:46px !important; height:46px !important;
  font-size:24px !important;
}
.kvai-title { flex:1 1 auto !important; min-width:0 !important; }
.kvai-title .kvai-h1 {
  font-size:clamp(1.05rem,4.3vw,1.42rem) !important;
  line-height:1.1 !important; white-space:nowrap !important;
}
.kvai-title p {
  display:block !important; font-size:clamp(.58rem,2.3vw,.72rem) !important;
  line-height:1.15 !important; margin:2px 0 0 !important;
  white-space:nowrap !important; overflow:hidden !important; text-overflow:ellipsis !important;
}
.kvai-badge {
  flex:0 0 auto !important; padding:4px 7px !important;
  font-size:clamp(.58rem,2.2vw,.7rem) !important; white-space:nowrap !important;
}

/* Keep all seven feature tabs in their original horizontal navigation row */
[data-baseweb="tab-list"] {
  display:flex !important; flex-direction:row !important; flex-wrap:nowrap !important;
  gap:3px !important; margin:2px 0 4px !important; padding:3px !important;
  overflow-x:auto !important; overflow-y:hidden !important;
  scrollbar-width:thin !important;
}
button[data-baseweb="tab"] {
  flex:0 0 auto !important; min-width:max-content !important;
  height:38px !important; padding:0 9px !important;
}
button[data-baseweb="tab"] p { font-size:.76rem !important; white-space:nowrap !important; }
[data-baseweb="tab-panel"] {
  height:auto !important; max-height:none !important;
  overflow:visible !important; padding:3px 0 5px !important;
}

/* Keep the main upload / preview / AI-control panels side-by-side.
   Other feature controls remain in their original tabs and order. */
[data-testid="stHorizontalBlock"] {
  display:flex !important; flex-direction:row !important; flex-wrap:nowrap !important;
  align-items:stretch !important; gap:.32rem !important; width:100% !important;
}
[data-testid="stColumn"] {
  min-width:0 !important; max-width:none !important;
  flex:1 1 0 !important; width:0 !important;
}
[data-testid="stColumn"] > div { min-width:0 !important; }
.kvai-panel-title {
  display:flex !important; align-items:center !important;
  gap:5px !important; font-size:clamp(.68rem,2.8vw,.9rem) !important;
  line-height:1.15 !important; margin:1px 0 3px !important; padding:5px 6px !important;
}
.kvai-step { width:24px !important; height:24px !important; flex:0 0 24px !important; font-size:.76rem !important; }

/* Compact controls, but preserve usable touch targets */
div[data-testid="stVerticalBlockBorderWrapper"] {
  padding:4px !important; border-radius:11px !important;
}
[data-testid="stWidgetLabel"] p, .stApp label {
  font-size:clamp(.62rem,2.4vw,.78rem) !important;
  line-height:1.15 !important; margin-bottom:2px !important;
}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
  font-size:clamp(.56rem,2.1vw,.68rem) !important;
  line-height:1.2 !important; margin:1px 0 !important;
}
[data-testid="stFileUploaderDropzone"] { min-height:54px !important; padding:5px !important; }
[data-testid="stFileUploaderDropzoneInstructions"] { padding:0 !important; }
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small { font-size:.62rem !important; }
[data-testid="stVideo"] { width:100% !important; max-width:100% !important; }
[data-testid="stVideo"] video {
  width:100% !important; height:auto !important; min-height:90px !important;
  max-height:clamp(105px,30vh,190px) !important; object-fit:contain !important;
  pointer-events:auto !important; background:#000 !important;
}
.kvai-empty-preview { height:clamp(105px,30vh,170px) !important; min-height:100px !important; }
.kvai-play { width:42px !important; height:42px !important; font-size:19px !important; }
.kvai-filmstrip { margin:3px 0 !important; padding:3px !important; font-size:.7rem !important; }
[data-baseweb="select"] > div { min-height:34px !important; }
.stTextInput input, .stNumberInput input { min-height:34px !important; }
.stTextArea textarea { min-height:48px !important; }
.stButton > button, .stDownloadButton > button {
  min-height:36px !important; padding:4px 6px !important;
  font-size:clamp(.65rem,2.5vw,.8rem) !important; white-space:normal !important;
}
[data-testid="stExpander"] { margin:2px 0 !important; }
[data-testid="stExpander"] summary { min-height:34px !important; padding:4px 7px !important; }
[data-testid="stExpander"] details { overflow:visible !important; }

/* Keep start action in normal page flow; never cover other controls */
.st-key-startbar {
  position:static !important; inset:auto !important; transform:none !important;
  width:100% !important; margin:3px 0 5px !important; padding:3px 5px !important;
  z-index:2 !important; border:1px solid rgba(0,220,255,.55) !important;
  border-radius:12px !important;
  background:linear-gradient(100deg,rgba(255,20,147,.20),rgba(8,18,53,.96),rgba(0,210,255,.20)) !important;
  box-shadow:0 0 14px rgba(0,210,255,.16) !important;
}
.st-key-startbar [data-testid="stVerticalBlockBorderWrapper"],
.st-key-startbar [data-testid="stVerticalBlock"] {
  background:transparent !important; border:0 !important; box-shadow:none !important;
}
.st-key-startbar .stButton > button { min-height:42px !important; font-size:.86rem !important; }

/* Very narrow phones: retain row layout and reduce only visual scale */
@media (max-width:420px) {
  .block-container { padding:.3rem .32rem .65rem !important; }
  .kvai-head { min-height:72px !important; height:72px !important; max-height:72px !important;
    gap:6px !important; padding:5px 6px !important; }
  .kvai-logo { flex-basis:38px !important; width:38px !important; height:38px !important; font-size:20px !important; }
  .kvai-title .kvai-h1 { font-size:1rem !important; }
  .kvai-title p { font-size:.55rem !important; }
  .kvai-badge { font-size:.55rem !important; padding:3px 5px !important; }
  [data-testid="stHorizontalBlock"] { gap:.22rem !important; }
  .kvai-panel-title { font-size:.65rem !important; padding:4px !important; }
  .kvai-step { width:20px !important; height:20px !important; flex-basis:20px !important; font-size:.65rem !important; }
  div[data-testid="stVerticalBlockBorderWrapper"] { padding:3px !important; }
  [data-testid="stWidgetLabel"] p, .stApp label { font-size:.59rem !important; }
  [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { font-size:.53rem !important; }
  [data-testid="stFileUploaderDropzone"] { min-height:46px !important; padding:3px !important; }
  [data-testid="stVideo"] video, .kvai-empty-preview { max-height:112px !important; min-height:88px !important; }
  .stButton > button, .stDownloadButton > button { min-height:33px !important; font-size:.61rem !important; }
}
/* On tablets and desktop keep the same feature positions with comfortable sizing */
@media (min-width:760px) {
  .block-container { max-width:1500px !important; padding:.7rem 1rem 1.2rem !important; }
  [data-testid="stHorizontalBlock"] { gap:.55rem !important; }
  .kvai-head { min-height:84px !important; height:84px !important; max-height:84px !important; }
}
</style>
"""
st.markdown(POLISHED_MOBILE_LAYOUT_CSS, unsafe_allow_html=True)


# =====================================================================
# FINAL MOBILE READABILITY PATCH
# Keep the three main workflow panels side-by-side and swipe horizontally
# on phones instead of squeezing all controls into unreadably narrow columns.
# Also improve contrast for labels, captions, inputs, and progress indicators.
# =====================================================================
MOBILE_READABILITY_PATCH_CSS = r"""
<style>
@media (max-width: 759px) {
  /* Only the main Upload / Preview / AI panels: horizontal swipe, not stacking. */
  [data-testid="stHorizontalBlock"]:has(.kvai-panel-title) {
    display:flex !important;
    flex-direction:row !important;
    flex-wrap:nowrap !important;
    align-items:stretch !important;
    gap:10px !important;
    width:100% !important;
    max-width:100% !important;
    overflow-x:auto !important;
    overflow-y:visible !important;
    padding:2px 2px 10px !important;
    scroll-snap-type:x proximity !important;
    -webkit-overflow-scrolling:touch !important;
    scrollbar-width:thin !important;
  }
  [data-testid="stHorizontalBlock"]:has(.kvai-panel-title) > [data-testid="stColumn"] {
    flex:0 0 76vw !important;
    width:76vw !important;
    min-width:76vw !important;
    max-width:76vw !important;
    scroll-snap-align:start !important;
  }
  [data-testid="stHorizontalBlock"]:has(.kvai-panel-title) > [data-testid="stColumn"] > div {
    min-width:0 !important;
  }

  /* Readable type inside the three workflow panels. */
  [data-testid="stHorizontalBlock"]:has(.kvai-panel-title) .kvai-panel-title {
    font-size:clamp(.9rem,3.8vw,1.05rem) !important;
    line-height:1.3 !important;
  }
  [data-testid="stHorizontalBlock"]:has(.kvai-panel-title) [data-testid="stWidgetLabel"] p,
  [data-testid="stHorizontalBlock"]:has(.kvai-panel-title) label {
    color:#FFE7A3 !important;
    font-size:.88rem !important;
    line-height:1.35 !important;
  }
  [data-testid="stHorizontalBlock"]:has(.kvai-panel-title) [data-testid="stCaptionContainer"],
  [data-testid="stHorizontalBlock"]:has(.kvai-panel-title) [data-testid="stCaptionContainer"] p {
    color:#C8DFFF !important;
    font-size:.78rem !important;
    line-height:1.4 !important;
  }
}

/* Strong readable contrast: avoid white text disappearing on pale controls. */
.stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stText"],
.stApp .stMarkdown p,
.stApp li {
  color:#EAF3FF !important;
}
.stApp [data-testid="stWidgetLabel"] p,
.stApp label {
  color:#FFE7A3 !important;
}
.stApp [data-testid="stCaptionContainer"],
.stApp [data-testid="stCaptionContainer"] p {
  color:#C5D9F7 !important;
}
.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
  color:#FFFFFF !important;
  caret-color:#42E6FF !important;
  background:#0B173B !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
  color:#AFC4E8 !important;
  opacity:1 !important;
}
/* Progress track and progress text must not be pale-on-white. */
[data-testid="stProgress"] > div > div {
  background:#26365F !important;
}
[data-testid="stProgress"] [data-testid="stMarkdownContainer"],
[data-testid="stProgress"] p {
  color:#FFE7A3 !important;
}
/* Native metric values remain bright; their labels use a warm readable tone. */
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
  color:#FFFFFF !important;
}
[data-testid="stMetricLabel"] p {
  color:#FFE7A3 !important;
}
</style>
"""
st.markdown(MOBILE_READABILITY_PATCH_CSS, unsafe_allow_html=True)


# =====================================================================
# TITLE BOX FIX: ចំណងជើង (st.code) អក្សរស្រាលលើផ្ទៃស្រាល មើលមិនឃើញ → ដាក់ផ្ទៃងងឹត អក្សរស អាចអានបាន
# =====================================================================
TITLE_CODE_FIX_CSS = r"""
<style>
[data-testid="stCode"], [data-testid="stCode"] > div, [data-testid="stCode"] pre {
  background:#0B173B !important;
  border:1px solid rgba(66,230,255,.45) !important;
  border-radius:12px !important;
}
[data-testid="stCode"] pre, [data-testid="stCode"] code,
[data-testid="stCode"] pre *, [data-testid="stCode"] code * {
  color:#FFFFFF !important;
  background:transparent !important;
  white-space:pre-wrap !important;
  word-break:break-word !important;
  overflow-wrap:anywhere !important;
  font-family:'Kantumruy Pro','Battambang','Noto Sans Khmer',system-ui,sans-serif !important;
  font-size:1rem !important;
  line-height:1.6 !important;
}
[data-testid="stCode"] button, [data-testid="stCode"] button * {
  color:#42E6FF !important;
  background:rgba(11,23,59,.9) !important;
}
</style>
"""
st.markdown(TITLE_CODE_FIX_CSS, unsafe_allow_html=True)


# =====================================================================
# FIX (Nov 2026): 1) hide "trouble loading App.kvai_local_storage" warning
#                 2) make the Hongguo search row fit the phone screen
# The local-storage components only remember keys/login in the browser.
# If the network is slow they may time out; the app still works, so the
# warning box is hidden instead of shown to the user.
# =====================================================================
KVAI_FIX_CSS = r"""
<style>
[data-baseweb="popover"] ul[role="listbox"], [data-baseweb="popover"] [role="listbox"], div[data-baseweb="menu"] {
  max-height: 55vh !important; overflow-y: auto !important; -webkit-overflow-scrolling: touch; overscroll-behavior: contain;
}

.st-key-kv_ls, .st-key-kv_login_ls,
[data-testid="stElementContainer"]:has(iframe[title*="kvai_local_storage"]),
[data-testid="stElementContainer"]:has(iframe[title*="kvai_login_storage"]) {
  position:absolute !important; width:1px !important; height:1px !important;
  overflow:hidden !important; opacity:0 !important; pointer-events:none !important;
  margin:0 !important; padding:0 !important; border:0 !important;
}
@media (max-width: 759px) {
  /* Swipe layout only for the 3 main panels (Upload / Preview / AI).
     Every other row (e.g. Hongguo search box + buttons) fills the screen width. */
  [data-testid="stHorizontalBlock"]:has(.kvai-panel-title):not(:has(> [data-testid="stColumn"]:nth-child(3))) {
    overflow-x:visible !important;
  }
  [data-testid="stHorizontalBlock"]:has(.kvai-panel-title):not(:has(> [data-testid="stColumn"]:nth-child(3))) > [data-testid="stColumn"] {
    flex:1 1 0 !important; min-width:0 !important; width:0 !important; max-width:none !important;
  }
  .block-container, [data-testid="stMainBlockContainer"] { max-width:100vw !important; overflow-x:hidden !important; }
  [data-testid="stTextInput"], [data-testid="stSelectbox"], [data-testid="stButton"] { max-width:100% !important; }
}
</style>
"""
st.markdown(KVAI_FIX_CSS, unsafe_allow_html=True)

# ===== FINAL READABILITY FIX: ផ្ទៃងងឹត + អក្សរសច្បាស់ (ដាក់ចុងក្រោយបំផុត ដើម្បីឈ្នះ CSS ផ្សេង) =====
st.markdown("""<style>
html body .stApp [data-testid="stPills"] button,
html body .stApp [data-testid^="stBaseButton-pills"],
html body .stApp [data-testid="stRadio"] label{
  background:#1d2766 !important; background-color:#1d2766 !important;
  border:1.5px solid #4cc9ff !important; opacity:1 !important; box-shadow:none !important;
  min-height:38px !important;
}
html body .stApp [data-testid="stPills"] button *,
html body .stApp [data-testid^="stBaseButton-pills"] *,
html body .stApp [data-testid="stRadio"] label *{
  color:#ffffff !important; opacity:1 !important; font-size:15px !important; font-weight:700 !important;
  -webkit-text-fill-color:#ffffff !important;
}
html body .stApp [data-testid="stBaseButton-pillsActive"],
html body .stApp [data-testid="stRadio"] label:has(input:checked){
  background:linear-gradient(90deg,#ff2bb0,#2bb8ff) !important; border-color:transparent !important;
}
html body .stApp [data-testid="stPills"] [role="group"], html body .stApp [data-testid="stPills"] > div{
  flex-wrap:nowrap !important; overflow-x:auto !important; padding-bottom:6px !important;
}
html body .stApp [data-testid="stPills"] button{flex:0 0 auto !important; white-space:nowrap !important;}

/* selectbox / multiselect / input = ផ្ទៃងងឹត អក្សរស */
html body .stApp [data-baseweb="select"] > div,
html body .stApp [data-baseweb="select"] input,
html body .stApp [data-testid="stTextInput"] input{
  background:#10183f !important; background-color:#10183f !important;
  color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; border:1.5px solid #4cc9ff !important;
}
html body .stApp [data-baseweb="select"] *{color:#ffffff !important; -webkit-text-fill-color:#ffffff !important;}
html body .stApp [data-baseweb="select"] svg{fill:#ffffff !important;}
html body .stApp [data-testid="stTextInput"] input::placeholder,
html body .stApp [data-baseweb="select"] input::placeholder{color:#c3cbff !important; -webkit-text-fill-color:#c3cbff !important; opacity:1 !important;}
html body [data-baseweb="popover"] ul, html body [data-baseweb="popover"] li, html body [data-baseweb="menu"]{
  background:#10183f !important; color:#ffffff !important;
}
html body [data-baseweb="popover"] li *{color:#ffffff !important;}
html body [data-baseweb="popover"] li:hover, html body [data-baseweb="popover"] li[aria-selected="true"]{background:#2b3a8f !important;}
html body .stApp [data-baseweb="tag"]{background:#2b3a8f !important;}

/* label / checkbox / caption = ស */
html body .stApp [data-testid="stWidgetLabel"] *,
html body .stApp [data-testid="stCheckbox"] *,
html body .stApp [data-testid="stCaptionContainer"] *,
html body .stApp label, html body .stApp label p{
  color:#f2f4ff !important; opacity:1 !important; -webkit-text-fill-color:#f2f4ff !important;
}
html body .stApp [data-testid="stCheckbox"] label > span:first-child{background:#10183f !important; border:2px solid #4cc9ff !important;}

/* ប៊ូតុងទូទៅ + ប៊ូតុង disabled (ZIP) អក្សរត្រូវមើលឃើញ */
html body .stApp .stButton > button,
html body .stApp [data-testid^="stBaseButton-secondary"]{
  background:#142055 !important; border:1.5px solid #4cc9ff !important; opacity:1 !important;
}
html body .stApp .stButton > button *, html body .stApp [data-testid^="stBaseButton-secondary"] *{
  color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; opacity:1 !important; font-weight:700 !important;
}
html body .stApp .stButton > button:disabled,
html body .stApp [data-testid^="stBaseButton-"]:disabled{
  background:#2a3166 !important; border:1.5px dashed #7f8ad6 !important; opacity:1 !important;
}
html body .stApp .stButton > button:disabled *,
html body .stApp [data-testid^="stBaseButton-"]:disabled *{
  color:#d7dcff !important; -webkit-text-fill-color:#d7dcff !important; opacity:1 !important;
}
html body .stApp .stButton > button[kind="primary"]:not(:disabled),
html body .stApp .stDownloadButton > button{
  background:linear-gradient(100deg,#FF279F,#853CFF,#08C8EF) !important; border:0 !important;
}
html body .stApp .stDownloadButton > button *{color:#fff !important; -webkit-text-fill-color:#fff !important;}
</style>""", unsafe_allow_html=True)
