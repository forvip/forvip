# (Hongguo និង រឿងឥតគិតថ្លៃ ត្រូវបានបំបែកទៅ hongguo_app.py និង free_drama_app.py)
# ====================================================================
# 📖 មាតិកា (INDEX) — ឯកសារនេះវែង ប្រើ Ctrl+F ស្វែងរក «ពាក្យស្វែងរក» ដើម្បីរកផ្នែក
# (លេខបន្ទាត់ប្រហែល ព្រោះពេលកែអាចរំកិល)
# ====================================================================
#  ~   143  កំពុង UPDATE (MAINTENANCE_MODE)   → ស្វែងរក: MAINTENANCE_MODE
#  ~   592  រូបរាង / Theme / CSS   → ស្វែងរក: apply_theme
#  ~  1851  Secrets, Setting, ffmpeg, ទាញវីដេអូ (TikTok/Link)   → ស្វែងរក: def download_video
#  ~  1903  Gemini ច្រើន Key   → ស្វែងរក: _GEM_COOL
#  ~  2441  ស្តាប់សំឡេង → អត្ថបទ (Transcribe)   → ស្វែងរក: def transcribe
#  ~  3169  បកប្រែ (Google, Groq, Claude, CodeCraft)   → ស្វែងរក: def groq_translate_chunk
#  ~  3329  បកប្រែខ្មែរ / កែសម្រួលភាសា   → ស្វែងរក: def gemini_translate_khmer
#  ~  5584  Logo + Blur លើវីដេអូ   → ស្វែងរក: def out_dims
#  ~  6623  API Key ផ្ទាល់ខ្លួនរបស់អ្នកប្រើ   → ស្វែងរក: API Key ផ្ទាល់ខ្លួន
#  ~  7618  Login / Admin / គណនី VIP   → ស្វែងរក: ADMIN_USERNAME
#  ~  7950  ផ្ទាំង ១: វីដេអូ   → ស្វែងរក: ផ្ទាំង ១: វីដេអូ
#  ~  8122  ផ្ទាំង កាត់វីដេអូ   → ស្វែងរក: ផ្ទាំង កាត់វីដេអូ
#  ~  8319  ផ្ទាំង ២: បកប្រែ / ៣: សំឡេង / ៤: អក្សរ   → ស្វែងរក: ផ្ទាំង ២: បកប្រែ
#  ~  8401  ផ្ទាំង Logo + Blur   → ស្វែងរក: ផ្ទាំង Logo + Blur
#  ~  8623  ប៊ូតុងចាប់ផ្តើម + ផ្ទាំង ៥: ធ្វើការ/ទាញយក   → ស្វែងរក: ប៊ូតុងចាប់ផ្តើម
#  ~  8968  CSS ចុងក្រោយ (Mobile/Desktop layout)   → ស្វែងរក: FINAL MOBILE
# ====================================================================
# ចំណាំ៖ នេះជា comment ទាំងអស់ — មិនប៉ះពាល់ដំណើរការ app ទេ


import os
import io
import re
import json
import gc
import time
import uuid
import hmac
import hashlib
import secrets
import requests
import shutil
import asyncio
import zipfile
import base64
import tempfile
import threading
import statistics
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

import streamlit as st
import streamlit.components.v1 as components
import imageio_ffmpeg
import edge_tts

# ---- កត់ត្រាកំហុសដែលធ្លាប់ត្រូវបានលាក់ (មើលក្នុង Logs របស់ Posit) ----
_SWALLOW_SEEN = {}


def _log_swallowed(err):
    """មិនធ្វើឱ្យ app គាំង តែសរសេរមូលហេតុទៅ Logs (ម្តងគត់ក្នុងមួយប្រភេទ ជៀសវាងពេញ Logs)។"""
    try:
        import traceback as _tb
        _frame = _tb.extract_tb(err.__traceback__)[-1] if err.__traceback__ else None
        _where = f"line {_frame.lineno} in {_frame.name}" if _frame else "?"
        _key = (type(err).__name__, _where)
        _SWALLOW_SEEN[_key] = _SWALLOW_SEEN.get(_key, 0) + 1
        if _SWALLOW_SEEN[_key] <= 2:
            print(f"[KVAI warn] {type(err).__name__}: {str(err)[:200]} @ {_where}", file=sys.stderr, flush=True)
    except Exception:
        pass


st.set_page_config(
    page_title="បកប្រែរឿង",
    page_icon="🎬",
    layout="wide",
)


# ---- សម្អាតឯកសារបណ្តោះអាសន្នចាស់ៗ (ចាស់ជាង ៣ ម៉ោង) ម្តងពេល app ចាប់ផ្តើម ----
@st.cache_resource(show_spinner=False)
def _sweep_old_temp():
    _prefixes = ("kac_", "hongguo_batch_", "free_batch_", "kcut_", "kclone_", "kfx_", "kfxu_")
    _now = time.time()
    _removed = 0
    try:
        _root = tempfile.gettempdir()
        for _name in os.listdir(_root):
            if not _name.startswith(_prefixes):
                continue
            _full = os.path.join(_root, _name)
            try:
                if os.path.isdir(_full) and _now - os.path.getmtime(_full) > 3 * 3600:
                    shutil.rmtree(_full, ignore_errors=True)
                    _removed += 1
            except Exception as _swallow_e:
                _log_swallowed(_swallow_e)
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)
    return _removed


_sweep_old_temp()

# ---- ជៀសវាង heading ក្នុង Markdown (កំណែ Streamlit ថ្មីលើ Posit បាន SyntaxError លើ heading) ----
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


# =====================================================================
#  MODE កំពុង UPDATE
#  ► ពេលកំពុង update: ទុក MAINTENANCE_MODE = True  (អ្នកប្រើនឹងឃើញតែសារ «កំពុង Update»)
#  ► ពេល update ចប់: ប្តូរទៅ False  (ឬដាក់ MAINTENANCE_MODE = "0" ក្នុង Secrets)
# =====================================================================
MAINTENANCE_MODE = False
_maint_env = str(os.environ.get("MAINTENANCE_MODE", "")).strip().lower()
if _maint_env in ("0", "false", "off", "no"):
    MAINTENANCE_MODE = False
elif _maint_env in ("1", "true", "on", "yes"):
    MAINTENANCE_MODE = True

# លេខសម្ងាត់អ្នកគ្រប់គ្រង (ចូលកែ/សាកល្បងពេលកំពុង update)។ ប្តូរបាន ឬដាក់ MAINTENANCE_KEY ក្នុង Secrets
MAINTENANCE_ADMIN_KEY = os.environ.get("MAINTENANCE_KEY", "").strip()
_is_admin = False
if MAINTENANCE_MODE:
    _qk = st.query_params.get("admin")
    if isinstance(_qk, list):
        _qk = _qk[0] if _qk else ""
    if st.session_state.get("_maint_admin") or (_qk and _qk == MAINTENANCE_ADMIN_KEY):
        st.session_state["_maint_admin"] = True
        _is_admin = True

if MAINTENANCE_MODE and not _is_admin:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Kantumruy+Pro:wght@400;700&display=swap');
.stApp { background: radial-gradient(circle at 50% 0%, #E4DCFF 0%, #F4F7FF 60%) !important; }
header, [data-testid="stToolbar"], [data-testid="stSidebar"] { display: none !important; }
.kvai-maint {
  max-width: 460px; margin: 18vh auto 0; padding: 36px 26px; text-align: center;
  border: 1px solid rgba(177,60,255,.45); border-radius: 26px;
  background: rgba(255,255,255,.95); box-shadow: 0 8px 36px rgba(100,80,200,.18);
  font-family: 'Kantumruy Pro', 'Battambang', sans-serif; color: #1F2A44;
}
.kvai-maint .ic { font-size: 64px; line-height: 1; animation: kvai-spin 3.2s linear infinite; display: inline-block; }
.kvai-maint h1 { font-size: 28px; margin: 18px 0 8px; color: #1F2A44; }
.kvai-maint p { font-size: 17px; line-height: 1.7; margin: 6px 0; color: #44506E; }
.kvai-maint .dots span { animation: kvai-blink 1.4s infinite both; font-size: 30px; color: #B13CFF; }
.kvai-maint .dots span:nth-child(2) { animation-delay: .2s; }
.kvai-maint .dots span:nth-child(3) { animation-delay: .4s; }
@keyframes kvai-spin { to { transform: rotate(360deg); } }
@keyframes kvai-blink { 0%, 80%, 100% { opacity: .15; } 40% { opacity: 1; } }
</style>
<div class="kvai-maint">
  <div class="ic">⚙️</div>
  <h1>កំពុង Update</h1>
  <p>យើងកំពុងធ្វើបច្ចុប្បន្នភាពកម្មវិធី ដើម្បីឱ្យប្រសើរជាងមុន។</p>
  <p>សូមអត់ធ្មត់ ហើយត្រឡប់មកវិញនៅពេលក្រោយ។ សូមអរគុណ 🙏</p>
  <div class="dots"><span>●</span><span>●</span><span>●</span></div>
</div>
""",
        unsafe_allow_html=True,
    )
    with st.expander("🔑 អ្នកគ្រប់គ្រង"):
        _pw = st.text_input("លេខសម្ងាត់", type="password", key="_maint_pw")
        if _pw and _pw == MAINTENANCE_ADMIN_KEY:
            st.session_state["_maint_admin"] = True
            st.rerun()
        elif _pw:
            st.error("លេខសម្ងាត់មិនត្រឹមត្រូវ")
    st.stop()

if MAINTENANCE_MODE and _is_admin:
    st.warning("⚙️ កំពុងស្ថិតក្នុង Mode Update — មានតែអ្នក (អ្នកគ្រប់គ្រង) ទេដែលឃើញកម្មវិធីពេញលេញ។ អ្នកដទៃឃើញតែទំព័រ «កំពុង Update»។")

# ---- Streamlit Cloud ----
# លំនាំដើម: អនុញ្ញាតឱ្យរត់លើ Cloud (មិនចាំបាច់ដាក់ Secrets អ្វីទេ)
# បើចង់បិទមិនឱ្យរត់លើ Cloud (ឱ្យរត់តែលើម៉ាស៊ីនមេខ្លួនឯង) កំណត់ BLOCK_STREAMLIT_CLOUD=1
def _running_on_streamlit_cloud():
    return os.path.isdir("/mount/src") or os.environ.get("HOME", "") == "/home/appuser"


IS_STREAMLIT_CLOUD = _running_on_streamlit_cloud()

if IS_STREAMLIT_CLOUD and os.environ.get("BLOCK_STREAMLIT_CLOUD") == "1":
    st.error("🚫 កម្មវិធីនេះមិនអនុញ្ញាតឱ្យរត់លើ Streamlit Cloud ទេ។ សូមប្រើម៉ាស៊ីនមេផ្ទាល់ខ្លួន។")
    st.stop()

# =====================================================================
#  THEME (Khmer Video AI — light)
# =====================================================================
for _k, _v in {
    "theme.base": "dark",
    "theme.primaryColor": "#FF2DAA",
    "theme.backgroundColor": "#070B22",
    "theme.secondaryBackgroundColor": "#10183D",
    "theme.textColor": "#F5F7FF",
    "server.maxUploadSize": int(os.environ.get("MAX_UPLOAD_MB", "1000000000") or 1000000000),
}.items():
    try:
        st._config.set_option(_k, _v)
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)

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



def render_header():
    st.markdown(
        """
        <div class="kvai-head btr-cinematic-header">
          <div class="kvai-logo btr-clapper-logo">🎬</div>
          <div class="kvai-title btr-header-center">
            <div class="kvai-h1 btr-main-title"><span>បកប្រែរឿង</span></div>
            <p class="btr-sub-pill">ទាញយក • បកប្រែ • ដាក់សំឡេង • ដាក់អក្សរខ្មែរ • កែវីដេអូ</p>
          </div>
          <div class="kvai-badge btr-vip-badge">👑 VIP</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ទីតាំងអក្សរ (ASS alignment: 1-9 តាមលេខក្តារចុច)
POS_MAP = {
    "↖": 7, "↑": 8, "↗": 9,
    "←": 4, "●": 5, "→": 6,
    "↙": 1, "↓": 2, "↘": 3,
}
# (ឈ្មោះ, ពណ៌ ASS (BGR), ពណ៌ HTML)
COLOR_OPTIONS = {
    "⚪ ស": ("&H00FFFFFF", "#FFFFFF"),
    "🟡 លឿង": ("&H0000FFFF", "#FFE600"),
    "🟢 បៃតង": ("&H0000FF00", "#00E640"),
    "🔵 ខៀវ": ("&H00FF6B2F", "#2F6BFF"),
    "🔴 ក្រហម": ("&H000000FF", "#FF2D2D"),
    "🟣 ស្វាយ": ("&H00FF3CB1", "#B13CFF"),
    "🟠 ទឹកក្រូច": ("&H000095FF", "#FF9500"),
    "⚫ ខ្មៅ": ("&H00000000", "#000000"),
}
BOX_OPTIONS = {
    "🚫 គ្មាន": "none",
    "◼ ស្រអាប់": "soft",
    "⬛ ខ្មៅ": "black",
    "⬜ ស": "white",
}
STYLE_OPTIONS = {
    "ធម្មតា": (False, False),
    "ដិត": (True, False),
    "ទ្រេត": (False, True),
    "ដិត+ទ្រេត": (True, True),
}
PREVIEW_TEXT = "ខ្ញុំមិនអាចបាត់បង់អ្នកបានទេ"


def render_preview(font_size, color_hex, align, bold, italic, box):
    jc = {1: "flex-start", 2: "center", 3: "flex-end", 4: "flex-start", 5: "center",
          6: "flex-end", 7: "flex-start", 8: "center", 9: "flex-end"}[align]
    ai = {1: "flex-end", 2: "flex-end", 3: "flex-end", 4: "center", 5: "center",
          6: "center", 7: "flex-start", 8: "flex-start", 9: "flex-start"}[align]
    px = max(10, int(font_size * 300 / 288))
    bg = {"none": "transparent", "soft": "rgba(0,0,0,.6)", "black": "#000", "white": "#fff"}[box]
    shadow = ""
    if box == "none":
        shadow = "text-shadow:-1px -1px 0 #000,1px -1px 0 #000,-1px 1px 0 #000,1px 1px 0 #000;"
    weight = 700 if bold else 400
    fstyle = "italic" if italic else "normal"
    st.markdown(
        f'<div class="kvai-prev" style="justify-content:{jc};align-items:{ai}">'
        f'<span style="font-size:{px}px;color:{color_hex};background:{bg};'
        f'font-weight:{weight};font-style:{fstyle};{shadow}">{PREVIEW_TEXT}</span></div>',
        unsafe_allow_html=True,
    )


def srt_time(sec):
    ms = max(0, int(round(float(sec) * 1000)))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


apply_theme()
apply_neon_theme()
st.markdown(CINEMATIC_DASHBOARD_CSS, unsafe_allow_html=True)

# ---------- Final responsive polish: real full-page Angkor background + usable controls ----------
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

# Background video is initialized once at the end of this file to avoid duplicate layers.

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


def server_ram_info():
    """បង្ហាញ RAM របស់ម៉ាស៊ីនដែលកំពុងដំណើរការ (គាំទ្រ Windows និង Linux)។"""
    try:
        if os.name == "nt":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
                return ""
            total = mem.ullTotalPhys / (1024 ** 3)
            free = mem.ullAvailPhys / (1024 ** 3)
            host = os.environ.get("COMPUTERNAME", "Windows PC")
        else:
            info = {}
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    info[k] = int(v.strip().split()[0])  # kB
            total = info["MemTotal"] / 1024 / 1024
            free = info.get("MemAvailable", info.get("MemFree", 0)) / 1024 / 1024
            host = os.uname().nodename
        return f"🖥️ ម៉ាស៊ីន: {host} · RAM សរុប {total:.1f}GB · នៅសល់ {free:.1f}GB"
    except Exception:
        return ""


def get_secret(name, default=""):
    """អាន secret ពី Environment Variable (Hugging Face Spaces) ឬ Streamlit secrets។"""
    val = os.environ.get(name)
    if val:
        return val
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


# បង្ហាញព័ត៌មានលម្អិត (DEBUG) ជានិច្ច ដល់អ្នកប្រើទាំងអស់
DEBUG = True

REQUEST_TIMEOUT_MS = 120000
TRANSLATE_TIMEOUT_MS = 40000   # ការបកប្រែអត្ថបទ: មិនរង់ចាំលើសពី ៤០ វិនាទី
MAX_CAPTION_CHARS = 26
def _env_int(name, default):
    """អាន Environment Variable ឬ Streamlit Secrets។ ដាក់ 0 = គ្មានកំណត់។"""
    try:
        v = int(float(get_secret(name, default) or default))
        return 10 ** 9 if v <= 0 else v
    except Exception:
        return default


# Streamlit Cloud (RAM តូច) = 200MB · ម៉ាស៊ីនមេផ្ទាល់ខ្លួន = 2GB (ប្រើ RAM របស់ម៉ាស៊ីនខ្លួនឯង)
# អាចប្តូរបានតាម Environment Variable MAX_UPLOAD_MB
MAX_UPLOAD_MB = _env_int("MAX_UPLOAD_MB", 10 ** 9)   # Upload: មិនកំណត់ដោយ app (ដាក់ MAX_UPLOAD_MB=0)
MAX_DOWNLOAD_MB = _env_int("MAX_DOWNLOAD_MB", 200000)   # តំណវីដេអូ: ទំហំប៉ុន្មានក៏បាន (ចំនួនធំណាស់)
_UNLIMITED = 10 ** 9   # គ្មានកំណត់ (ប្តូរបានតាម Environment Variable MAX_VIDEOS / MAX_VIDEOS_AT_ONCE)
MAX_VIDEOS = _UNLIMITED   # គ្មានកំណត់ចំនួនវីដេអូដោយ App
_MAX_VIDEOS_TXT = "គ្មានកំណត់" if MAX_VIDEOS >= _UNLIMITED else str(MAX_VIDEOS)
MAX_ZIP_MB = _env_int("MAX_ZIP_MB", 10 ** 6)   # ទំហំ ZIP: គ្មានកំណត់
MOBILE_COPY = os.environ.get("MOBILE_COPY", "0") == "1"   # បង្កើតកំណែតូចសម្រាប់ទូរស័ព្ទ (encode ម្តងទៀត → យឺត) លំនាំដើមបិទ
REFRESH_SECONDS = 2
MAX_RENDER_AT_ONCE = _env_int("MAX_RENDER_AT_ONCE", _UNLIMITED)   # encode ស្របគ្នា: គ្មានកំណត់
MAX_VIDEOS_AT_ONCE = _UNLIMITED   # ដំណើរការវីដេអូដែលបានជ្រើសស្របគ្នា ដោយគ្មានកំណត់ក្នុង App
_PIPELINE_SLOTS = threading.Semaphore(MAX_VIDEOS_AT_ONCE)
MAX_DURATION_MIN = _env_int("MAX_DURATION_MIN", 10 ** 6)   # ប្រវែងវីដេអូ: គ្មានកំណត់
_MAX_DUR_TXT = "គ្មានកំណត់" if MAX_DURATION_MIN >= 10 ** 6 else f"{MAX_DURATION_MIN // 60} ម៉ោង"

CHUNK_TARGET = 20.0
CHUNK_MAX = 28.0
MAX_CHUNK_WORKERS = _env_int("MAX_CHUNK_WORKERS", _UNLIMITED)   # បំបែកជាផ្នែកស្របគ្នា: គ្មានកំណត់

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODELS = ["whisper-large-v3", "whisper-large-v3-turbo"]   # large-v3 មុន = ស្តាប់ត្រូវជាង

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
GROQ_CHAT_PREFERRED = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "llama-3.1-8b-instant",
]
_groq_chat_cache = {"models": None, "good": None}

WHISPER_LANG = {
    "Khmer": "km", "English": "en", "Thai": "th", "Vietnamese": "vi",
    "Chinese": "zh", "Japanese": "ja", "Korean": "ko", "French": "fr",
}

CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")

try:
    ST_VER = tuple(int(x) for x in re.findall(r"\d+", st.__version__)[:2])
except Exception:
    ST_VER = (1, 0)

# Gemini models are no longer used. CodeCraft handles text translation; Groq handles STT.
PREFERRED_MODELS = []

GF = "https://raw.githubusercontent.com/google/fonts/main/ofl/"

FONT_SOURCES = [
    ("Battambang.ttf", GF + "battambang/Battambang-Regular.ttf", "Battambang"),
    ("Content.ttf", GF + "content/Content-Regular.ttf", "Content"),
    ("Siemreap.ttf", GF + "siemreap/Siemreap-Regular.ttf", "Siemreap"),
    ("Bokor.ttf", GF + "bokor/Bokor-Regular.ttf", "Bokor"),
]

QUALITY = {
    "⚡ លឿន 480p": (480, 30, "ultrafast"),
    "✨ ល្អ 720p": (720, 28, "ultrafast"),
    "💎 ខ្ពស់ (ដើម)": (0, 25, "ultrafast"),
}

# កំណត់ bitrate អតិបរមា ដើម្បីកុំឱ្យឯកសារធំពេក (ទាញយកលើទូរស័ព្ទបានលឿន)
RATE_CAP = {480: ("1200k", "2400k"), 720: ("2500k", "5000k"), 0: ("6000k", "12000k")}


LANGUAGES = {
    "🌐 ស្វ័យប្រវត្តិ (ភាសាអ្វីក៏បាន)": None,
    "ខ្មែរ": "Khmer", "អង់គ្លេស": "English", "ថៃ": "Thai",
    "វៀតណាម": "Vietnamese", "ចិន": "Chinese", "ជប៉ុន": "Japanese",
    "កូរ៉េ": "Korean", "បារាំង": "French",
}

TTS_VOICES = {
    "👩 ស្រី (Sreymom)": "km-KH-SreymomNeural",
    "👨 ប្រុស (Piseth)": "km-KH-PisethNeural",
}


class UserError(RuntimeError):
    pass


def friendly_message(error):
    if isinstance(error, UserError):
        return str(error)
    low = str(error).lower()
    if "429" in low or "resource_exhausted" in low or "quota" in low:
        return "មានអ្នកប្រើច្រើនពេក ឬ API អស់កូតា។ សូមរង់ចាំមួយភ្លែត ឬដាក់ API Key ផ្ទាល់ខ្លួននៅផ្ទាំង «🌐 បកប្រែ»។"
    if any(x in low for x in ("503", "unavailable", "high demand", "overloaded", "timeout", "timed out")):
        return "ប្រព័ន្ធ AI កំពុងរវល់។ សូមសាកម្តងទៀត។"
    if "api key" in low or "api_key" in low or "permission" in low:
        return "សេវា AI មានបញ្ហា។ សូមទាក់ទងម្ចាស់កម្មវិធី។"
    if any(x in low for x in ("offline", "whisper large-v3", "madlad-400", "voxcpm", "faster-whisper", "ctranslate2")):
        return str(error)[:900]
    return "ការបង្កើតវីដេអូមិនបានសម្រេច។ សូមសាកម្តងទៀត។"


def fix_khmer(text):
    if not text:
        return ""
    text = unicodedata.normalize("NFC", str(text))
    text = re.sub(r"(\u17D2)\s+", r"\1", text)
    text = re.sub(r"\s+([\u17B6-\u17D3])", r"\1", text)
    text = re.sub(r"([\u17B6-\u17D3])\s+([\u17B6-\u17D3])", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def has_khmer(text):
    return bool(re.search(r"[\u1780-\u17FF]", text or ""))


def khmer_dominant(text, min_ratio=0.6):
    """អក្សរខ្មែរត្រូវមានច្រើនជាងអក្សរឡាតាំង (មិនអនុញ្ញាតឱ្យនៅសល់អង់គ្លេស/ចិនច្រើន)។"""
    t = str(text or "")
    kh = len(re.findall(r"[\u1780-\u17FF]", t))
    lat = len(re.findall(r"[A-Za-z]", t))
    if kh == 0:
        return False
    return kh / float(kh + lat) >= min_ratio


def tts_clean(text):
    """សម្អាតអត្ថបទមុនអាន ដើម្បីកុំឱ្យ TTS ផ្អាកដាច់ៗ ដោយសារសញ្ញាចម្លែកៗ។"""
    t = fix_khmer(text)
    t = re.sub(r"[\"\u201c\u201d\u2018\u2019'\u00ab\u00bb()\[\]{}<>*_#~`^|\\/]", " ", t)
    t = re.sub(r"(\.{2,}|\u2026+|[-\u2013\u2014]+)", " ", t)
    t = re.sub(r"[,;:\u060c]+", " ", t)
    t = re.sub(r"([!?\u17D4])\1+", r"\1", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t or fix_khmer(text)


def khmer_ratio(segments):
    if not segments:
        return 0.0
    return sum(1 for _, _, t in segments if has_khmer(t)) / len(segments)


def safe_filename(name):
    base = os.path.splitext(str(name))[0]
    base = re.sub(r"[^\w\-]+", "_", base).strip("_")[:40]
    return base or "video"


def run_ffmpeg(args, cwd=None, verbose=False, env=None):
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [exe, "-y"]
    if verbose:
        cmd += ["-loglevel", "verbose"]
    cmd += args
    full_env = None
    if env:
        full_env = os.environ.copy()
        full_env.update(env)
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True, cwd=cwd, env=full_env,
        )
    except subprocess.CalledProcessError as e:
        err = (e.stderr or b"").decode("utf-8", "ignore")[-1500:]
        raise RuntimeError("FFmpeg បរាជ័យ:\n" + err)
    return (result.stderr or b"").decode("utf-8", "ignore")


def run_ffmpeg_progress(args, cwd=None, env=None, total=0.0, on_pct=None):
    """រត់ ffmpeg ហើយរាយការណ៍ភាគរយ (មិនចាំបាច់រង់ចាំងងឹតរហូតចប់)។"""
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [exe, "-y", "-nostats", "-progress", "pipe:1"] + args
    full_env = None
    if env:
        full_env = os.environ.copy()
        full_env.update(env)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, env=full_env,
                            text=True, encoding="utf-8", errors="ignore")
    err_buf = []

    def _drain():
        for line in proc.stderr:
            err_buf.append(line)
            if len(err_buf) > 400:
                del err_buf[:200]

    th = threading.Thread(target=_drain, daemon=True)
    th.start()
    t0 = time.time()
    last_cb = 0.0
    for line in proc.stdout:
        if not line.startswith("out_time_us="):
            continue
        try:
            sec = int(line.split("=", 1)[1]) / 1e6
        except Exception:
            continue
        now = time.time()
        if total > 0 and on_pct and now - last_cb >= 1.0:
            last_cb = now
            try:
                on_pct(max(0.0, min(0.99, sec / total)), now - t0)
            except Exception as _swallow_e:
                _log_swallowed(_swallow_e)
    proc.wait()
    th.join(timeout=3)
    if proc.returncode != 0:
        raise RuntimeError("FFmpeg បរាជ័យ:\n" + "".join(err_buf)[-1500:])


def probe_media(path):
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [exe, "-i", path], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )
    err = result.stderr
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", err)
    if not match:
        raise UserError("មិនអាចអានឯកសារនេះបានទេ។")
    h, m, s = match.groups()
    duration = int(h) * 3600 + int(m) * 60 + float(s)
    width, height = 16, 9
    size = re.search(r"Video:.*?,\s*(\d{2,5})x(\d{2,5})", err)
    if size:
        width, height = int(size.group(1)), int(size.group(2))
    rot = re.search(r"rotation of (-?\d+(?:\.\d+)?)", err)
    if rot and abs(float(rot.group(1))) % 180 == 90:
        width, height = height, width
    return duration, width, height


def probe_video(path):
    return probe_media(path)


def time_ass(seconds):
    cs = max(0, int(round(float(seconds) * 100)))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def _font_bytes_are_valid(data):
    """Reject HTML error pages, truncated files, and fonts without Khmer glyphs."""
    if not isinstance(data, (bytes, bytearray)) or len(data) < 10_000:
        return False
    if bytes(data[:4]) not in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf"):
        return False
    try:
        from fontTools.ttLib import TTFont
        font = TTFont(io.BytesIO(data), lazy=True)
        try:
            cmap = set()
            for table in font["cmap"].tables:
                cmap.update(table.cmap.keys())
            return any(0x1780 <= codepoint <= 0x17FF for codepoint in cmap)
        finally:
            font.close()
    except ImportError:
        # fontTools is optional for validation; SFNT signature and size still checked.
        return True
    except Exception:
        return False


def _find_installed_khmer_font():
    """Use an already-installed Khmer TTF/OTF if the computer cannot reach GitHub."""
    win_dir = os.environ.get("WINDIR", r"C:\Windows")
    local_app = os.environ.get("LOCALAPPDATA", "")
    roots = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"),
        os.path.join(win_dir, "Fonts"),
        os.path.join(local_app, "Microsoft", "Windows", "Fonts") if local_app else "",
        os.path.join(os.path.expanduser("~"), ".fonts"),
    ]
    tokens = ("khmer", "battambang", "content", "siemreap", "bokor", "noto")
    candidates = []
    seen = set()
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        try:
            names = os.listdir(root)
        except OSError:
            continue
        for name in names:
            low = name.lower()
            full = os.path.join(root, name)
            if low.endswith((".ttf", ".otf")) and any(token in low for token in tokens) and full not in seen:
                seen.add(full)
                # Prefer actual Battambang, then Noto Khmer, then any installed Khmer font.
                rank = 0 if "battambang" in low else 1 if "noto" in low else 2
                candidates.append((rank, full))
    for _, path in sorted(candidates):
        try:
            with open(path, "rb") as fh:
                data = fh.read()
            if _font_bytes_are_valid(data):
                return (os.path.basename(path), bytes(data), "Battambang")
        except OSError:
            continue
    return None


def _font_url_alternates(url):
    """Return official Google Fonts URLs with the GitHub raw-page fallback."""
    urls = [url]
    prefix = "https://raw.githubusercontent.com/google/fonts/main/"
    if url.startswith(prefix):
        relative = url[len(prefix):]
        urls.extend([
            "https://github.com/google/fonts/raw/refs/heads/main/" + relative,
            "https://github.com/google/fonts/raw/main/" + relative,
        ])
    # Preserve order while removing duplicates.
    return list(dict.fromkeys(urls))


@st.cache_resource(show_spinner=False)
def load_font_bytes():
    out = []
    cache_dir = os.path.join(os.path.expanduser("~"), ".khmer_dubbing_cache", "fonts")
    os.makedirs(cache_dir, exist_ok=True)

    # Keep previously downloaded, verified fonts. Invalid cached HTML/error files are removed.
    for filename, _url, default_name in FONT_SOURCES:
        cache_path = os.path.join(cache_dir, filename)
        if os.path.isfile(cache_path):
            try:
                with open(cache_path, "rb") as fh:
                    cached = fh.read()
                if _font_bytes_are_valid(cached):
                    out.append((filename, cached, default_name))
                else:
                    os.remove(cache_path)
            except OSError as cache_error:
                _log_swallowed(cache_error)

    if out:
        return out

    # Offline/local fallback: Windows Khmer OS / Noto / other Khmer fonts.
    local_font = _find_installed_khmer_font()
    if local_font:
        filename, data, default_name = local_font
        # Use a predictable filename for FFmpeg, while retaining the actual TTF bytes.
        cache_path = os.path.join(cache_dir, "Battambang.ttf")
        try:
            with open(cache_path, "wb") as fh:
                fh.write(data)
            return [("Battambang.ttf", data, default_name)]
        except OSError as cache_error:
            _log_swallowed(cache_error)
            return [(filename, data, default_name)]

    # No local Khmer font found: try the official Google Fonts source and GitHub raw mirrors.
    failures = []
    for filename, url, default_name in FONT_SOURCES:
        cache_path = os.path.join(cache_dir, filename)
        data = None
        for candidate_url in _font_url_alternates(url):
            try:
                response = requests.get(
                    candidate_url,
                    headers={"User-Agent": "Mozilla/5.0 Khmer-Dubbing/1.0"},
                    timeout=(8, 18),
                )
                response.raise_for_status()
                candidate_data = response.content
                if not _font_bytes_are_valid(candidate_data):
                    raise RuntimeError("Server មិនបានផ្ញើឯកសារ Font TTF ត្រឹមត្រូវទេ")
                data = candidate_data
                break
            except Exception as download_error:
                failures.append(f"{candidate_url}: {str(download_error)[:120]}")
        if data is not None:
            try:
                with open(cache_path, "wb") as fh:
                    fh.write(data)
            except OSError as cache_error:
                _log_swallowed(cache_error)
            out.append((filename, data, default_name))

    if not out:
        local_font = _find_installed_khmer_font()
        if local_font:
            filename, data, default_name = local_font
            return [(filename, data, default_name)]
        detail = failures[-1] if failures else "មិនមានប្រភព Font ដែលអាចប្រើបានទេ"
        raise RuntimeError(
            "មិនអាចទាញយក Font ខ្មែរពី Google Fonts បានទេ ហើយមិនរកឃើញ Font ខ្មែរដែលបានដំឡើងក្នុង Windows ដែរ។ "
            "សូមពិនិត្យ Internet ឬដំឡើង Khmer OS / Noto Sans Khmer ជាមុន។ ព័ត៌មាន៖ " + detail
        )
    return out


def prepare_home_font(fonts_data):
    try:
        home_fonts = os.path.expanduser("~/.fonts")
        os.makedirs(home_fonts, exist_ok=True)
        dst = os.path.join(home_fonts, "Battambang-Regular.ttf")
        if not os.path.exists(dst):
            with open(dst, "wb") as f:
                f.write(fonts_data[0][1])
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)


def install_fonts(folder, fonts_data):
    fonts = []
    for filename, data, default_name in fonts_data:
        path = os.path.join(folder, filename)
        with open(path, "wb") as f:
            f.write(data)
        fonts.append((path, default_name))
    return fonts


def get_font_family(path, default):
    try:
        from fontTools.ttLib import TTFont
        font = TTFont(path)
        for record in font["name"].names:
            if record.nameID == 1:
                name = record.toUnicode().strip()
                if name:
                    return name
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)
    return default


def make_fontconfig_env(folder):
    cache_dir = os.path.join(folder, "fc-cache")
    os.makedirs(cache_dir, exist_ok=True)
    conf_path = os.path.join(folder, "fonts.conf")
    # Windows មិនមាន /etc/fonts/fonts.conf ឬ ~/.fonts ដូច Linux ទេ។
    # បន្ថែមតែ folder ដែលមាន Font របស់ការងារបច្ចុប្បន្ន ដើម្បីកុំឱ្យ FFmpeg រក path ខុស។
    if os.name == "nt":
        import html as _html_xml
        font_dir = _html_xml.escape(folder.replace("\\", "/"))
        cache_dir_xml = _html_xml.escape(cache_dir.replace("\\", "/"))
        conf = (
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
            "<fontconfig>\n"
            f"  <dir>{font_dir}</dir>\n"
            f"  <cachedir>{cache_dir_xml}</cachedir>\n"
            "</fontconfig>\n"
        )
    else:
        conf = (
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
            "<fontconfig>\n"
            '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
            f"  <dir>{folder}</dir>\n"
            "  <dir>~/.fonts</dir>\n"
            f"  <cachedir>{cache_dir}</cachedir>\n"
            "</fontconfig>\n"
        )
    with open(conf_path, "w", encoding="utf-8") as f:
        f.write(conf)
    return {"FONTCONFIG_FILE": conf_path, "FONTCONFIG_PATH": folder}


def font_was_used(log, keys):
    lines = [l for l in log.splitlines() if "fontselect" in l.lower()]
    if not lines:
        return True
    for line in lines:
        right = line.split("->", 1)[-1].lower()
        if any(k in right for k in keys):
            return True
    return False


def normalize_link(url):
    url = url.strip()
    match = re.search(r"drive\.google\.com/file/d/([\w-]+)", url)
    if not match:
        match = re.search(r"drive\.google\.com/open\?id=([\w-]+)", url)
    if match:
        return "https://drive.google.com/uc?export=download&id=" + match.group(1)
    return url


SOCIAL_HOSTS = ("tiktok.com", "douyin.com", "iesdouyin.com")


def is_social_link(url):
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return any(host == h or host.endswith("." + h) for h in SOCIAL_HOSTS)


SSSTIK_BASE = "https://ssstik.io"
_SS_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_SS_HEADERS = {"User-Agent": _SS_UA, "Accept-Language": "en-US,en;q=0.9"}


def _ss_decode_link(u):
    if "ssscdn.io" not in u:
        return u
    try:
        parts = u.split("/")
        decoded = base64.b64decode("/".join(parts[5:])).decode("utf-8")
        if decoded.startswith("http"):
            return decoded
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)
    return u


def _ss_parse(page):
    import html as _html
    video_links = []
    for attrs in re.findall(r'<a\b([^>]*?)>', page, flags=re.I):
        cm = re.search(r'class=["\']([^"\']*)["\']', attrs, flags=re.I)
        hm = re.search(r'href=["\']([^"\']+)["\']', attrs, flags=re.I)
        if not hm:
            continue
        href = _html.unescape(hm.group(1))
        if not href.startswith("http"):
            continue
        css = cm.group(1) if cm else ""
        if "without_watermark" in css or "download_link" in css or "dl-button" in css:
            href = _ss_decode_link(href)
            if href not in video_links:
                video_links.append(href)
    if not video_links:
        for href in re.findall(r'href=["\'](https?://[^"\']+)["\']', page, flags=re.I):
            href = _html.unescape(href)
            low = href.lower()
            if ".mp4" in low or "ssscdn" in low or "tikcdn" in low:
                href = _ss_decode_link(href)
                if href not in video_links:
                    video_links.append(href)
    return video_links


def _ssstik_links(url):
    import requests
    sess = requests.Session()
    sess.headers.update(_SS_HEADERS)
    try:
        r = sess.get(SSSTIK_BASE + "/en", headers={**_SS_HEADERS, "Referer": SSSTIK_BASE + "/"}, timeout=30)
        r.raise_for_status()
        page = r.text
        m = (re.search(r"s_tt\s*=\s*['\"]([^'\"]+)['\"]", page)
             or re.search(r"tt\s*:\s*['\"]([^'\"]+)['\"]", page))
        if not m:
            raise RuntimeError("SSSTik token not found")
        token = m.group(1)
        fm = re.search(r"s_furl\s*=\s*['\"]([^'\"]+)['\"]", page)
        endpoint = fm.group(1) if fm else "abc"
        headers = {
            **_SS_HEADERS,
            "Origin": SSSTIK_BASE,
            "Referer": SSSTIK_BASE + "/en",
            "HX-Current-URL": SSSTIK_BASE + "/en",
            "HX-Request": "true",
            "HX-Target": "target",
            "HX-Trigger": "_gcaptcha_pt",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        r = sess.post(f"{SSSTIK_BASE}/{endpoint}?url=dl",
                      data={"id": url, "locale": "en", "tt": token}, headers=headers, timeout=60)
        r.raise_for_status()
        links = _ss_parse(r.text)
        if not links:
            raise RuntimeError("SSSTik returned no video link")
        return links
    finally:
        sess.close()


def _download_with_ssstik(url, path, progress):
    import requests
    limit = MAX_DOWNLOAD_MB * 1024 * 1024
    last = None
    for vurl in _ssstik_links(url):
        try:
            with requests.get(vurl, headers={"User-Agent": _SS_UA, "Referer": SSSTIK_BASE + "/"},
                              stream=True, timeout=120) as r:
                r.raise_for_status()
                ct = (r.headers.get("Content-Type") or "").lower()
                if "text/html" in ct or "json" in ct or ct.startswith("audio"):
                    raise RuntimeError("not a video file")
                total = int(r.headers.get("Content-Length") or 0)
                if total > limit:
                    raise RuntimeError(f"video larger than {MAX_DOWNLOAD_MB}MB")
                done = 0
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=256 * 1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        done += len(chunk)
                        if done > limit:
                            raise RuntimeError(f"video larger than {MAX_DOWNLOAD_MB}MB")
                        if total:
                            progress.progress(min(1.0, done / total))
            if os.path.getsize(path) < 1000:
                raise RuntimeError("empty video file")
            progress.progress(1.0)
            return
        except Exception as e:
            last = e
            try:
                os.remove(path)
            except Exception as _swallow_e:
                _log_swallowed(_swallow_e)
    raise last or RuntimeError("no downloadable link")


def _resolve_social_url(url):
    """តំណខ្លី (vt.tiktok.com ...) → តំណពេញ https://www.tiktok.com/@x/video/ID ដើម្បីឱ្យ tikwm/yt-dlp អានបាន។"""
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception:
        return url
    if not (host.endswith("tiktok.com")):
        return url
    if re.search(r"/video/\d+", url):
        return url.split("?")[0]
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"})
        with urllib.request.urlopen(req, timeout=15) as r:
            final = r.geturl() or ""
            m = re.search(r"/video/(\d+)", final)
            if m:
                return final.split("?")[0]
            body = r.read(200000).decode("utf-8", "ignore")
        m = re.search(r"tiktok\.com/@[^/\"'\s]+/video/\d+", body)
        if m:
            return "https://www." + m.group(0)
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)
    return url


def download_social_video(url, path, progress):
    """ទាញវីដេអូ TikTok ដោយសាក SSSTik / yt-dlp / tikwm ស្របគ្នា — មួយណាបានមុន យកមួយនោះ (លឿនជាងសាកម្តងមួយៗ)។"""
    try:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception:
        host = ""
    full_url = _resolve_social_url(url)
    methods = []
    if host == "tiktok.com" or host.endswith(".tiktok.com"):
        methods.append(("ssstik", _download_with_ssstik))
    methods.append(("yt-dlp", _download_with_ytdlp))
    methods.append(("tikwm", _download_with_tikwm))

    import queue
    results = queue.Queue()
    work_dirs = []

    def _run(name, fn):
        d = tempfile.mkdtemp(prefix="kac_race_")
        work_dirs.append(d)
        target = os.path.join(d, "video.mp4")
        try:
            try:
                fn(full_url, target, _NoProgress())
            except Exception:
                if full_url != url:
                    fn(url, target, _NoProgress())
                else:
                    raise
            if os.path.isfile(target) and os.path.getsize(target) > 1000:
                results.put((name, target, None))
            else:
                results.put((name, None, "empty file"))
        except Exception as e:
            results.put((name, None, str(e) or type(e).__name__))

    for name, fn in methods:
        threading.Thread(target=_run, args=(name, fn), daemon=True).start()

    reasons = []
    deadline = time.time() + 150
    got = 0
    while got < len(methods) and time.time() < deadline:
        try:
            name, target, err = results.get(timeout=2)
        except queue.Empty:
            continue
        got += 1
        if target:
            try:
                shutil.move(target, path)
            except Exception:
                shutil.copyfile(target, path)
            progress.progress(1.0)
            for d in work_dirs:
                shutil.rmtree(d, ignore_errors=True)
            return
        reasons.append(f"{name}: {err}")
    for d in work_dirs:
        shutil.rmtree(d, ignore_errors=True)
    raise UserError(" | ".join(reasons) or "ទាញយកវីដេអូមិនបាន (អស់ពេល)។")


def _download_with_tikwm(url, path, progress):
    data = {}
    for _mode in ("post", "get"):
        try:
            if _mode == "post":
                req = urllib.request.Request(
                    "https://www.tikwm.com/api/",
                    data=urllib.parse.urlencode({"url": url, "hd": 1}).encode(),
                    headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
            else:
                req = urllib.request.Request(
                    "https://www.tikwm.com/api/?" + urllib.parse.urlencode({"url": url, "hd": 1}),
                    headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8", "ignore"))
            if ((data or {}).get("data") or {}).get("play") or ((data or {}).get("data") or {}).get("hdplay"):
                break
        except Exception:
            data = {}
    d = (data or {}).get("data") or {}
    play = d.get("hdplay") or d.get("play")
    if not play:
        raise RuntimeError("no video in response: " + str((data or {}).get("msg", ""))[:80])
    if play.startswith("/"):
        play = "https://www.tikwm.com" + play
    download_video(play, path, progress)


def _download_with_ytdlp(url, path, progress):
    try:
        import yt_dlp
    except Exception:
        raise UserError("yt-dlp មិនទាន់ដំឡើង")
    limit = MAX_DOWNLOAD_MB * 1024 * 1024
    base = os.path.splitext(path)[0]

    def hook(d):
        try:
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                if total:
                    progress.progress(min(1.0, (d.get("downloaded_bytes") or 0) / total))
        except Exception as _swallow_e:
            _log_swallowed(_swallow_e)

    opts = {
        "outtmpl": base + ".%(ext)s",
        "format": "best[ext=mp4]/best",
        "max_filesize": limit,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "socket_timeout": 30,
        "retries": 3,
        "progress_hooks": [hook],
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    found = None
    folder = os.path.dirname(base)
    prefix = os.path.basename(base) + "."
    for fn in os.listdir(folder):
        if fn.startswith(prefix):
            found = os.path.join(folder, fn)
            break
    if not found or os.path.getsize(found) < 1000:
        raise UserError(f"ទាញយកវីដេអូមិនបាន ឬវីដេអូធំជាង {MAX_DOWNLOAD_MB}MB។")
    if found != path:
        os.replace(found, path)
    progress.progress(1.0)


class _HtmlPage(Exception):
    pass


def _urlopen_robust(request, timeout=30):
    """urlopen ដែលប្រើ certifi (ដោះស្រាយ CERTIFICATE_VERIFY_FAILED លើ Windows)។
    បើនៅតែបរាជ័យដោយសារ certificate នឹងព្យាយាមម្តងទៀតដោយមិនផ្ទៀងផ្ទាត់ (សម្រាប់តែការទាញវីដេអូសាធារណៈ)។"""
    import ssl
    try:
        import certifi
        _ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        _ctx = ssl.create_default_context()
    try:
        return urllib.request.urlopen(request, timeout=timeout, context=_ctx)
    except urllib.error.URLError as _ue:
        if isinstance(getattr(_ue, "reason", None), ssl.SSLCertVerificationError):
            return urllib.request.urlopen(request, timeout=timeout, context=ssl._create_unverified_context())
        raise


def download_video(url, path, progress):
    url = normalize_link(url)
    if is_social_link(url):
        return download_social_video(url, path, progress)
    limit = MAX_DOWNLOAD_MB * 1024 * 1024
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _urlopen_robust(request, timeout=30) as response:
            ctype = (response.headers.get("Content-Type") or "").lower()
            if "text/html" in ctype:
                raise _HtmlPage()
            total = int(response.headers.get("Content-Length") or 0)
            if total > limit:
                raise UserError(f"វីដេអូធំជាង {MAX_DOWNLOAD_MB}MB។")
            done = 0
            with open(path, "wb") as f:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if done > limit:
                        raise UserError(f"វីដេអូធំជាង {MAX_DOWNLOAD_MB}MB។")
                    if total:
                        progress.progress(min(1.0, done / total))
    except _HtmlPage:
        _download_with_ytdlp(url, path, progress)
        return
    except UserError:
        raise
    except Exception as _dl_exc:
        raise UserError("ទាញយកវីដេអូពីតំណមិនបានទេ។ (" + type(_dl_exc).__name__ + ": " + str(_dl_exc)[:150] + ")")
    if os.path.getsize(path) < 1000:
        raise UserError("ទាញយកវីដេអូមិនបាន។")
    progress.progress(1.0)


def extract_audio(video_path, audio_path, master_path):
    try:
        run_ffmpeg([
            "-i", video_path,
            "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", audio_path,
            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "flac", master_path,
        ])
    except RuntimeError:
        raise UserError("មិនអាចដកសំឡេងពីវីដេអូនេះបានទេ។")


# =====================================================================
#  Gemini ច្រើន Key: ប្តូរស្វ័យប្រវត្តិពេល Key មួយអស់កូតា ឬមិនត្រឹមត្រូវ
# =====================================================================
_GEM_COOL = {}          # key -> ម៉ោងដែលអាចប្រើបានវិញ
_GEM_LOCK = threading.Lock()
GEM_COOLDOWN = 65       # វិនាទី


def split_keys(value):
    if isinstance(value, (list, tuple)):
        value = "\n".join("\n".join(split_keys(v)) for v in value)
    elif value is not None and not isinstance(value, str) and hasattr(value, "__iter__"):
        value = "\n".join("\n".join(split_keys(v)) for v in value)
    out = []
    for k in re.split(r"[\s,;]+", str(value or "")):
        k = k.strip().strip("[]()").strip('"').strip("'").strip("[]()").strip('"').strip("'")
        if k and k not in out:
            out.append(k)
    return out


def _gem_retryable(err):
    low = str(err).lower()
    return any(x in low for x in ("429", "resource_exhausted", "quota", "rate limit",
                                  "api key not valid", "api_key_invalid", "permission_denied", "403"))


class _RotModels:
    def __init__(self, clients):
        self.clients = clients  # [(key, client)]

    def _order(self):
        now = time.time()
        with _GEM_LOCK:
            ready = [kc for kc in self.clients if _GEM_COOL.get(kc[0], 0) <= now]
            cooling = [kc for kc in self.clients if _GEM_COOL.get(kc[0], 0) > now]
        cooling.sort(key=lambda kc: _GEM_COOL.get(kc[0], 0))
        return ready + cooling

    def _call(self, name, *args, **kwargs):
        last = None
        order = self._order()
        for n, (key, client) in enumerate(order):
            try:
                return getattr(client.models, name)(*args, **kwargs)
            except Exception as e:
                last = e
                if _gem_retryable(e) and n < len(order) - 1:
                    with _GEM_LOCK:
                        _GEM_COOL[key] = time.time() + GEM_COOLDOWN
                    continue
                raise
        raise last

    def generate_content(self, *args, **kwargs):
        return self._call("generate_content", *args, **kwargs)

    def list(self, *args, **kwargs):
        return self._call("list", *args, **kwargs)


class RotatingGemini:
    def __init__(self, keys, http_options=None):
        self.models = _RotModels([(k, genai.Client(api_key=k, http_options=http_options)) for k in keys])


def make_gemini_client(api_key, http_options=None):
    keys = split_keys(api_key)
    if len(keys) <= 1:
        return genai.Client(api_key=(keys[0] if keys else api_key), http_options=http_options)
    return RotatingGemini(keys, http_options)


_GROQ_COOL = {}
GROQ_COOLDOWN = 60


def groq_first(api_key):
    keys = split_keys(api_key)
    return keys[0] if keys else str(api_key or "")


def groq_urlopen(request, api_key, timeout=60):
    """urlopen សម្រាប់ Groq: ប្តូរ key ស្វ័យប្រវត្តិពេល 429/401/403 (ពេលមាន key ច្រើន)។"""
    keys = split_keys(api_key)
    if len(keys) <= 1:
        return urllib.request.urlopen(request, timeout=timeout)
    now = time.time()
    with _GEM_LOCK:
        ready = [k for k in keys if _GROQ_COOL.get(k, 0) <= now]
        cooling = sorted([k for k in keys if _GROQ_COOL.get(k, 0) > now], key=lambda k: _GROQ_COOL[k])
    order = ready + cooling
    last = None
    for n, key in enumerate(order):
        request.headers["Authorization"] = f"Bearer {key}"
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 401, 403) and n < len(order) - 1:
                with _GEM_LOCK:
                    _GROQ_COOL[key] = time.time() + GROQ_COOLDOWN
                continue
            raise
    raise last


_MODEL_COOL = {}     # model -> ម៉ោងដែលអាចសាកម្តងទៀត
_GROQ_LIMIT = {"t": 0.0}   # ម៉ោងចុងក្រោយដែលជួប 429 (អស់កូតា)
_MODEL_GOOD = {}     # provider -> ម៉ូដែលដែលបានជោគជ័យចុងក្រោយ


def model_cool(model, error_text):
    """កត់ត្រាថ្នាក់ម៉ូដែលខូច/ពេញកូតា ដើម្បីប្តូរទៅម៉ូដែលផ្សេងដោយស្វ័យប្រវត្តិ។"""
    low = str(error_text).lower()
    if "429" in low or "rate limit" in low:
        _GROQ_LIMIT["t"] = time.time()
    if any(x in low for x in ("404", "not found", "decommission", "does not exist", "no longer", "deprecated", "model_not_found", "not supported")):
        secs = 3600
    elif any(x in low for x in ("per day", "daily", "tokens per day", "requests per day")):
        secs = 1800
    elif "429" in low or "quota" in low or "resource_exhausted" in low or "rate limit" in low:
        secs = 90
    elif any(x in low for x in ("500", "502", "503", "504", "overloaded", "unavailable", "timeout", "timed out", "high demand")):
        secs = 30
    else:
        secs = 15
    with _GEM_LOCK:
        _MODEL_COOL[model] = time.time() + secs


def model_order(models, provider=None):
    """ម៉ូដែលល្អនៅមុខ ម៉ូដែលកំពុងសម្រាកនៅក្រោយ (មិនលុបចោលទាំងស្រុង)។"""
    now = time.time()
    models = list(models)
    with _GEM_LOCK:
        ready = [m for m in models if _MODEL_COOL.get(m, 0) <= now]
        cooling = sorted([m for m in models if _MODEL_COOL.get(m, 0) > now], key=lambda m: _MODEL_COOL[m])
        good = _MODEL_GOOD.get(provider)
    if good in ready:
        ready = [good] + [m for m in ready if m != good]
    return ready + cooling


def model_good(provider, model):
    with _GEM_LOCK:
        _MODEL_GOOD[provider] = model
        _MODEL_COOL.pop(model, None)


_MODELS_CACHE = {"t": 0.0, "v": None}


def get_available_models(client):
    if _MODELS_CACHE["v"] and time.time() - _MODELS_CACHE["t"] < 600:
        return list(_MODELS_CACHE["v"])
    res = _get_available_models_uncached(client)
    if res:
        _MODELS_CACHE["v"], _MODELS_CACHE["t"] = list(res), time.time()
    return res


def _get_available_models_uncached(client):
    found = []
    try:
        for m in client.models.list():
            name = (getattr(m, "name", "") or "").replace("models/", "")
            actions = getattr(m, "supported_actions", None) or []
            low = name.lower()
            if not name or "generateContent" not in actions:
                continue
            if "flash" not in low and "pro" not in low:
                continue
            if any(x in low for x in ("tts", "live", "embedding", "image", "imagen", "veo", "robotics")):
                continue
            found.append(name)
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)
    ordered = [m for m in PREFERRED_MODELS if m in found]
    rest = [m for m in found if m not in ordered]
    rest.sort(key=lambda m: ("lite" in m.lower(), "flash" not in m.lower()))
    ordered += rest
    ordered = (
        [m for m in ordered if "lite" not in m.lower()]
        + [m for m in ordered if "lite" in m.lower()]
    )
    return ordered[:6]


def parse_segments(raw, duration):
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except Exception:
        match = re.search(r"\[.*\]", raw, re.S)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except Exception:
            return []
    if isinstance(data, dict):
        data = data.get("segments") or data.get("captions") or []
    segments = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = fix_khmer(item.get("text", ""))
        try:
            start = float(item.get("start", 0))
            end = float(item.get("end", 0))
        except Exception:
            continue
        if not text:
            continue
        start = min(max(0.0, start), duration)
        end = min(max(end, start + 0.4), duration + 0.5)
        segments.append([start, end, text])
    segments.sort(key=lambda s: s[0])
    for i in range(len(segments) - 1):
        if segments[i][1] > segments[i + 1][0]:
            segments[i][1] = max(segments[i][0] + 0.2, segments[i + 1][0] - 0.02)
    return [(s, e, t) for s, e, t in segments]


def plain_to_segments(text, duration):
    text = fix_khmer(text)
    if not text:
        return []
    sentences = [fix_khmer(p) for p in re.split(r"(?<=[។.!?])\s+|\n+", text) if fix_khmer(p)]
    if not sentences:
        return [(0.0, max(duration, 0.4), text)]
    total = sum(max(1, len(p)) for p in sentences)
    cursor = 0.0
    out = []
    for i, piece in enumerate(sentences):
        if i == len(sentences) - 1:
            end = max(duration, cursor + 0.4)
        else:
            end = cursor + duration * max(1, len(piece)) / total
        out.append((cursor, end, piece))
        cursor = end
    return out


def safe_split(word, n):
    chunks = []
    while len(word) > n:
        cut = n
        while cut > 1 and ("\u17B6" <= word[cut] <= "\u17D3" or word[cut - 1] == "\u17D2"):
            cut -= 1
        if cut <= 1:
            cut = n
        chunks.append(word[:cut])
        word = word[cut:]
    if word:
        chunks.append(word)
    return chunks


def split_display(text, max_chars=MAX_CAPTION_CHARS):
    text = fix_khmer(text)
    if not text:
        return []
    pieces = []
    current = ""
    for word in text.split():
        if len(word) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(safe_split(word, max_chars))
            continue
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars:
            pieces.append(current)
            current = word
        else:
            current = candidate
    if current:
        pieces.append(current)
    return [fix_khmer(p) for p in pieces if fix_khmer(p)]


def detect_speech(audio_path, duration):
    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        result = subprocess.run(
            [exe, "-i", audio_path, "-af", "silencedetect=noise=-32dB:d=0.35", "-f", "null", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        err = result.stderr
        starts = [max(0.0, float(x)) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", err)]
        ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", err)]
        silences = []
        for i, s in enumerate(starts):
            e = ends[i] if i < len(ends) else duration
            silences.append((s, min(e, duration)))
        speech = []
        cursor = 0.0
        for s, e in silences:
            if s - cursor >= 0.2:
                speech.append((cursor, s))
            cursor = max(cursor, e)
        if duration - cursor >= 0.2:
            speech.append((cursor, duration))
        return speech
    except Exception:
        return []


def snap_segments(segments, speech, duration):
    segs = sorted([[s, e, t] for s, e, t in segments], key=lambda x: x[0])
    total_speech = sum(b - a for a, b in speech)
    if not speech or duration <= 0 or total_speech / duration >= 0.9:
        return [(s, e, t) for s, e, t in segs]
    for sg in segs:
        s, e = sg[0], sg[1]
        near_starts = [a for a, b in speech if abs(a - s) <= 0.8]
        ns = min(near_starts, key=lambda a: abs(a - s)) if near_starts else s
        near_ends = [b for a, b in speech if abs(b - e) <= 0.8 and b > ns + 0.3]
        ne = min(near_ends, key=lambda b: abs(b - e)) if near_ends else e
        sg[0], sg[1] = ns, max(ne, ns + 0.4)
    segs.sort(key=lambda x: x[0])
    for i in range(len(segs) - 1):
        if segs[i][1] > segs[i + 1][0]:
            segs[i][1] = max(segs[i][0] + 0.2, segs[i + 1][0] - 0.02)
    out = []
    for s, e, t in segs:
        s = min(max(0.0, s), duration)
        e = max(min(e, duration), s + 0.2)
        out.append((s, e, t))
    return out


def build_captions(segments, duration):
    items = []
    for s, e, t in segments:
        parts = split_display(t)
        if not parts:
            continue
        total = sum(max(1, len(p)) for p in parts)
        cur = s
        for p in parts:
            d = (e - s) * max(1, len(p)) / total
            items.append((cur, cur + d, p))
            cur += d
    if not items:
        return [], ""
    return items, "តាមម៉ោងពី AI (កែតម្រឹមតាមសំឡេង)"


def write_ass(path, captions, font_family, font_size, outline_size, primary_color, width, height, style=None):
    play_res_y = 288
    play_res_x = max(100, int(round(play_res_y * width / max(1, height))))
    style = style or {}
    align = int(style.get("align", 2))
    bold = -1 if style.get("bold") else 0
    italic = -1 if style.get("italic") else 0
    box = style.get("box", "none")
    box_cols = {"soft": "&H99000000", "black": "&H00000000", "white": "&H00FFFFFF"}
    if box in box_cols:
        border_style, outline_col, back_col, shadow = 3, box_cols[box], "&H00000000", 0
    else:
        border_style, outline_col, back_col, shadow = 1, "&H00000000", "&H64000000", 1
    header = [
        "[Script Info]", "ScriptType: v4.00+",
        f"PlayResX: {play_res_x}", f"PlayResY: {play_res_y}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font_family},{font_size},{primary_color},"
        f"&H000000FF,{outline_col},{back_col},{bold},{italic},0,0,100,100,0,0,{border_style},"
        f"{outline_size},{shadow},{align},20,20,35,1", "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text",
    ]
    events = []
    for start, end, text in captions:
        clean = fix_khmer(text).replace("{", "").replace("}", "")
        clean = clean.replace("\n", " ")
        events.append(
            f"Dialogue: 0,{time_ass(start)},"
            f"{time_ass(max(start + 0.25, end))},Default,,0,0,0,,{clean}"
        )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(header + events) + "\n")


class Reporter:
    def __init__(self, item):
        self.item = item
    def write(self, message):
        self.item["stage"] = message
        _t0 = self.item.get("t0")
        self.item["log"].append((f"[{int(time.time() - _t0)}s] " if _t0 else "") + str(message))
        if len(self.item["log"]) > 200:
            del self.item["log"][:100]
        m = re.search(r"(\d+)/(\d+) ឃ្លា", str(message))
        if m and int(m.group(2)) > 0:
            frac = min(1.0, int(m.group(1)) / int(m.group(2)))
            self.item["pct"] = max(self.item.get("pct", 0.0), 0.25 + 0.28 * frac)
    def progress(self, value):
        self.item["pct"] = 0.03 + 0.09 * max(0.0, min(1.0, value))


def dbg(status, message):
    if DEBUG:
        status.write(message)


def call_with_retry(client, model, prompt, audio_bytes, mime, config, status):
    for attempt in range(3):
        try:
            kwargs = dict(
                model=model,
                contents=[prompt, types.Part.from_bytes(data=audio_bytes, mime_type=mime)],
            )
            if config is not None:
                kwargs["config"] = config
            return client.models.generate_content(**kwargs)
        except Exception as e:
            low = str(e).lower()
            busy = any(x in low for x in ("503", "unavailable", "high demand", "overloaded", "timeout", "timed out"))
            quota = "429" in low or "resource_exhausted" in low
            if busy and attempt < 2:
                wait = 4 * (attempt + 1)
                status.write("ប្រព័ន្ធរវល់បន្តិច កំពុងសាកម្តងទៀត...")
                dbg(status, f"[{model}] busy, wait {wait}s")
                time.sleep(wait)
                continue
            if quota and attempt < 1:
                status.write("ប្រព័ន្ធរវល់បន្តិច កំពុងសាកម្តងទៀត...")
                dbg(status, f"[{model}] quota, wait 20s")
                time.sleep(20)
                continue
            raise


def build_prompt(clip_duration, source_language, concise=False):
    if source_language == "Khmer":
        task = (
            "The speech or singing is in Khmer (Cambodian). Transcribe it "
            "faithfully, word for word, in Khmer script with correct "
            "standard Khmer spelling. Do not translate, summarize or "
            "paraphrase. Do not confuse Khmer with Thai or Lao. "
            "If a word is unclear, choose the most likely Khmer word from the context."
        )
    elif source_language:
        task = (
            f"The speech or singing is in {source_language}. "
            "Listen very carefully. First write exactly what is said in "
            "the original language, then translate the meaning into "
            "natural, fluent, easy-to-understand Khmer, written in Khmer script. "
            "Translate the meaning, not word for word."
        )
    else:
        task = (
            "First detect the spoken or sung language. "
            "If it is Khmer (Cambodian), transcribe it faithfully, word "
            "for word, in Khmer script with correct standard Khmer "
            "spelling, and do not confuse it with Thai or Lao. "
            "If it is any other language, first write exactly what is "
            "said in the original language, then translate the meaning "
            "into natural, fluent, easy-to-understand Khmer written in Khmer script."
        )
    concise_rule = ""
    if concise:
        concise_rule = (
            "Each Khmer line must be short enough to be spoken naturally "
            "within its own time range: at most about 11 Khmer "
            "characters per second of that segment. Prefer concise wording. "
        )
    return (
        task
        + " The field \"text\" of every segment MUST be written only in "
        "Khmer script (names of people, places, brands may stay as they "
        "are or be transliterated into Khmer). Never put romanization or "
        "explanations in \"text\". "
        "Put a normal space between Khmer phrases so lines can wrap. "
        "Split into short subtitle segments, each about 1.5 to 4 seconds "
        "long, and the Khmer \"text\" of each segment at most 26 characters. "
        + concise_rule
        + "Timestamps are in seconds, measured from the very beginning "
        f"of THIS audio clip (0 to {clip_duration:.1f}). "
        "Each segment must start exactly when its first word is heard "
        "and end exactly when its last word ends. "
        "Return ONLY a JSON array. Each item must be an object: "
        '{"start": <seconds as number>, "end": <seconds as number>, '
        '"original": "<what was said in the original language>", '
        '"text": "<Khmer text>"}. '
        "If there is no speech or singing, return an empty array []."
    )


def build_prompt_original(clip_duration, source_language):
    lang = (f"The speech or singing is in {source_language}. " if source_language
            else "First detect the spoken or sung language. ")
    return (
        lang + "Transcribe it faithfully, word for word, in its ORIGINAL language and original script "
        "with correct spelling and punctuation. Do NOT translate, summarize or paraphrase. "
        "If a word is unclear, choose the most likely word from the context. "
        "Split into natural sentence-level segments, each about 2 to 6 seconds long. "
        "Timestamps are in seconds, measured from the very beginning "
        f"of THIS audio clip (0 to {clip_duration:.1f}). "
        "Each segment must start exactly when its first word is heard and end exactly when its last word ends. "
        "Return ONLY a JSON array. Each item must be an object: "
        '{"start": <seconds as number>, "end": <seconds as number>, "text": "<original-language transcript>"}. '
        "If there is no speech or singing, return an empty array []."
    )


def plan_chunks(duration, speech):
    if duration <= CHUNK_MAX:
        return [(0.0, duration)]
    cuts = []
    for (a1, b1), (a2, b2) in zip(speech, speech[1:]):
        if a2 - b1 >= 0.15:
            cuts.append((b1 + a2) / 2.0)
    chunks = []
    start = 0.0
    while duration - start > CHUNK_MAX:
        target = start + CHUNK_TARGET
        limit = start + CHUNK_MAX
        cands = [c for c in cuts if start + 8.0 <= c <= limit]
        cut = min(cands, key=lambda c: abs(c - target)) if cands else target
        chunks.append((start, cut))
        start = cut
    chunks.append((start, duration))
    return chunks


def is_empty_json(raw):
    return bool(re.fullmatch(r"\s*(```(?:json)?)?\s*\[\s*\]\s*(```)?\s*", raw or ""))


def transcribe_clip(client, models, audio_bytes, mime, clip_duration, source_language, concise, status, original_only=False):
    prompt = build_prompt_original(clip_duration, source_language) if original_only else build_prompt(clip_duration, source_language, concise)
    configs = [
        types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
        types.GenerateContentConfig(
            temperature=0, response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
        None,
    ]
    errors = []
    weak = None
    for model in models:
        for config in configs:
            dbg(status, f"កំពុងសាកម៉ូដែល {model}...")
            try:
                response = call_with_retry(client, model, prompt, audio_bytes, mime, config, status)
            except Exception as e:
                message = str(e)
                low = message.lower()
                errors.append(f"{model}: {message}")
                if "400" in message or "invalid_argument" in low:
                    continue
                break
            raw = getattr(response, "text", None) or ""
            segments = parse_segments(raw, clip_duration)
            if segments:
                ratio = khmer_ratio(segments)
                dbg(status, f"[{model}] khmer ratio = {ratio:.2f}")
                if original_only or ratio >= 0.6:
                    return segments, model, errors
                kept = [s for s in segments if has_khmer(s[2])]
                if kept and (weak is None or len(kept) > len(weak[0])):
                    weak = (kept, model)
                errors.append(f"{model}: មិនមែនអក្សរខ្មែរ")
                break
            if is_empty_json(raw):
                return [], model, []
            plain = fix_khmer(re.sub(r"[\[\]{}\"]", " ", raw))
            if plain and (has_khmer(plain) or original_only):
                return plain_to_segments(plain, clip_duration), model, errors
            errors.append(f"{model}: មិនមានអត្ថបទ")
            break
    if weak:
        return weak[0], weak[1], errors
    return [], None, errors


def transcribe(api_key, audio_path, duration, source_language, status, concise=False, speech=None, original_only=False):
    client = make_gemini_client(api_key, types.HttpOptions(timeout=REQUEST_TIMEOUT_MS))
    models = get_available_models(client)
    if not models:
        raise RuntimeError("API Key មើលមិនឃើញម៉ូដែលណាមួយទេ។ api key")
    dbg(status, "ម៉ូដែលដែលរកឃើញ: " + ", ".join(models))
    chunks = plan_chunks(duration, speech or [])
    total = len(chunks)
    folder = os.path.dirname(audio_path)
    base = os.path.basename(audio_path)
    done_counter = {"n": 0}
    dbg(status, f"បែងចែកជា {total} ផ្នែក")
    def work(i, start, end):
        out_name = f"chunk_{i}.flac"
        run_ffmpeg(["-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", base, "-c:a", "flac", out_name], cwd=folder)
        with open(os.path.join(folder, out_name), "rb") as f:
            data = f.read()
        if len(data) > 15 * 1024 * 1024:
            raise UserError("សំឡេងធំពេក។")
        segs, model, errors = transcribe_clip(client, models, data, "audio/flac", end - start, source_language, concise, status, original_only=original_only)
        done_counter["n"] += 1
        if total > 1:
            status.write(f"៣/៤ កំពុងស្តាប់ និងបកប្រែ... ({done_counter['n']}/{total})")
        return start, segs, model, errors
    all_segments = []
    used_models = []
    failed = 0
    fatal_errors = []
    fatal_keys = ("429", "503", "404", "500", "resource_exhausted")
    workers = max(1, min(MAX_CHUNK_WORKERS, total))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(work, i, s, e) for i, (s, e) in enumerate(chunks)]
        for fut in futures:
            try:
                start, segs, model, errors = fut.result()
            except UserError:
                raise
            except Exception as e:
                failed += 1
                fatal_errors.append(str(e))
                continue
            if segs:
                used_models.append(model)
                for s, e, t in segs:
                    all_segments.append((min(s + start, duration), min(e + start, duration + 0.5), t))
            elif any(k in err.lower() for err in errors for k in fatal_keys):
                failed += 1
                fatal_errors.extend(errors)
    if not all_segments:
        if fatal_errors:
            raise RuntimeError("ម៉ូដែលទាំងអស់បរាជ័យ។\n\n" + "\n\n".join(fatal_errors))
        raise UserError("រកមិនឃើញសំឡេងនិយាយក្នុងវីដេអូនេះទេ។")
    all_segments.sort(key=lambda x: x[0])
    main_model = Counter(used_models).most_common(1)[0][0]
    return all_segments, main_model, failed


def groq_request(api_key, audio_path, model, language, words=True):
    boundary = "----kac" + uuid.uuid4().hex
    fields = [
        ("model", model), ("response_format", "verbose_json"),
        ("temperature", "0"), ("timestamp_granularities[]", "segment"),
    ]
    if words:
        fields.append(("timestamp_granularities[]", "word"))
    if language:
        fields.append(("language", language))
    parts = []
    for name, value in fields:
        parts.append((f"--{boundary}\r\n" f'Content-Disposition: form-data; name="{name}"\r\n\r\n' f"{value}\r\n").encode("utf-8"))
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    parts.append((f"--{boundary}\r\n" 'Content-Disposition: form-data; name="file"; ' 'filename="audio.mp3"\r\n' "Content-Type: audio/mpeg\r\n\r\n").encode("utf-8"))
    parts.append(audio_data)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)
    request = urllib.request.Request(
        GROQ_URL, data=body, method="POST",
        headers={"Authorization": f"Bearer {groq_first(api_key)}", "Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "Mozilla/5.0"},
    )
    try:
        with groq_urlopen(request, api_key, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:500]
        if words and e.code == 400:
            # This model/API refused word timestamps: retry with segment timestamps only.
            return groq_request(api_key, audio_path, model, language, words=False)
        raise RuntimeError(f"Groq HTTP {e.code}: {detail}")


def groq_transcribe(api_key, audio_path, language, status):
    last = None
    for model in model_order(GROQ_MODELS, None):  # whisper-large-v3 មុនជានិច្ច; turbo ជាបម្រុងពេល large-v3 រវល់
        for attempt in range(2):
            try:
                res_ = groq_request(api_key, audio_path, model, language)
                model_good("whisper", model)
                return res_, model
            except RuntimeError as e:
                last = e
                text = str(e)
                if ("429" in text or "503" in text) and attempt == 0:
                    status.write("ប្រព័ន្ធរវល់បន្តិច កំពុងសាកម្តងទៀត...")
                    time.sleep(12)
                    continue
                model_cool(model, text)
                break
            except Exception as e:
                last = e
                break
    raise last or RuntimeError("Groq បរាជ័យ: មិនដឹងមូលហេតុ")


def _google_once(text):
    query = urllib.parse.urlencode({"client": "gtx", "sl": "auto", "tl": "km", "dt": "t"})
    url = "https://translate.googleapis.com/translate_a/single?" + query
    body = urllib.parse.urlencode({"q": text}).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) " "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"), "Content-Type": "application/x-www-form-urlencoded"},
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


_LEAK_TAG_RE = re.compile(r"\[\s*(?:speaker|max|SPEAKER)[^\]]*\]\s*", re.I)


def spk_tag(g):
    """ស្លាកភេទអ្នកនិយាយ ដែលផ្ញើទៅអ្នកបកប្រែ (M=ប្រុស, F=ស្រី)។ មិនស្គាល់ = គ្មានស្លាក។"""
    return {"M": "[speaker: male] ", "F": "[speaker: female] "}.get(g, "")


def _spk_differs(fn, a0, a1, b0, b1):
    """True ប្រសិនបើឃ្លាពីរមានអ្នកនិយាយផ្សេងភេទគ្នាច្បាស់លាស់ (មិនត្រូវបញ្ចូលគ្នា)។"""
    if fn is None:
        return False
    try:
        ga, gb = fn(a0, a1), fn(b0, b1)
    except Exception:
        return False
    return bool(ga and gb and ga != gb)


def clean_translation(out):
    out = str(out or "")
    out = _LEAK_TAG_RE.sub("", out)
    out = CJK_RE.sub("", out)
    out = fix_khmer(out)
    if out and not khmer_dominant(out):
        return None
    return out or None


def http_detail(e):
    try:
        body = e.read().decode("utf-8", "ignore")[:200]
    except Exception:
        body = ""
    return f"HTTP {e.code}: {body}".strip()


def groq_chat_models(api_key):
    if _groq_chat_cache["models"]:
        return _groq_chat_cache["models"]
    found = []
    try:
        request = urllib.request.Request(GROQ_MODELS_URL, headers={"Authorization": f"Bearer {groq_first(api_key)}", "User-Agent": "Mozilla/5.0"})
        with groq_urlopen(request, api_key, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        for m in data.get("data") or []:
            mid = str(m.get("id", ""))
            low = mid.lower()
            if not mid or m.get("active") is False:
                continue
            if any(x in low for x in ("whisper", "tts", "guard", "prompt", "orpheus", "allam", "safeguard")):
                continue
            found.append(mid)
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)
    if found:
        ordered = [m for m in GROQ_CHAT_PREFERRED if m in found]
        ordered += [m for m in found if m not in ordered]
    else:
        ordered = list(GROQ_CHAT_PREFERRED)
    _groq_chat_cache["models"] = ordered
    return ordered


TRANS_SYSTEM_FULL = (
    "You are an expert Cambodian Khmer dubbing translator and script editor. Translate the dialogue into natural, "
    "everyday SPOKEN Khmer exactly as a native Phnom Penh speaker would say it in a film or drama, not written/news Khmer "
    "and not word-for-word. The numbered lines are consecutive lines from ONE video: read ALL of them first to understand "
    "the story, who is speaking to whom, relationships, mood and running jokes, then translate each line with that context. "
    "Rules: (1) Keep the exact meaning, names, numbers and facts; never add or drop information. "
    "(2) Choose pronouns and politeness that fit the relationship (friends: ឯង/អ្នក/ខ្ញុំ; elders: ទូលបង្គំ/លោក/អ្នកស្រី etc.) and keep them consistent across lines. "
    "(3) Keep the speaker's emotion: anger, sadness, fear, joy, sarcasm, tenderness must be audible in word choice "
    "(use natural particles such as ណា, ហើយ, ទេ, ហ្នឹង, នែ៎ where a native would) and keep ! ? … punctuation. "
    "(4) Translate idioms, slang and jokes by their intended meaning, never literally. "
    "(5) Flowing, connected spoken sentences that sound like a real person talking (join clauses naturally, do not chop into tiny fragments); no stiff foreign word order; no repeated words; "
    "no word salad. Write numbers and units the way Khmer speakers say them. Transliterate foreign names naturally. "
    "(6) If a line is garbled or uncertain, keep the closest clear meaning, do not invent dialogue. "
    "(7) A [max N chars] tag is the SPEAKING-TIME budget of the on-screen speaker's mouth (Khmer TTS speaks about 12 characters per second). "
    "Make the dubbed line end when the mouth stops, so treat N as a TARGET length (aim for 80-105% of N): if your natural Khmer is longer than N, use the shortest everyday wording and drop fillers; "
    "if it is clearly shorter than ~70% of N (the speaker talks for a long time), make it fuller and more natural with common connecting words, polite particles and a fuller phrasing of the SAME meaning, without inventing any new fact. "
    "NEVER drop a fact, name, number, negation or the emotional point just to fit; if the meaning truly cannot fit, keep the meaning and exceed the budget slightly. Never output the tag. "
    "(8) Every numbered line is ONE complete spoken sentence unit: translate it into exactly one complete, grammatical Khmer "
    "sentence; never merge lines, split lines, or move content between lines. Never leave source-language words untranslated except names. "
    "(9) The output will be read aloud by a TTS voice: use plain natural Khmer, put ។ (or ? !) only at the end of a sentence, and avoid "
    "commas, brackets, quotes, dashes, ellipses, emojis and symbols so the speech flows smoothly without choppy pauses. "
    "(10) If an English meaning is given, use it only as a hint; the original line is the authority for facts, names and numbers. "
    "(11) Translate MEANING, not words: never copy the source sentence structure or idioms literally. Use common everyday Khmer vocabulary "
    "(avoid stiff Pali/Sanskrit-heavy or royal words unless the speaker is a king/monk), drop pronouns that Khmer speakers would omit, "
    "and make sure every sentence is something a native Khmer person would really say and instantly understand. "
    "(12) Double-check every line against the original before answering: a wrong meaning, a missed negation (not, never, មិន, គ្មាន), swapped subject and object, or a wrong number is the worst mistake. "
    "(13) Match the DELIVERY of the original: a short sharp exclamation, shout or one-word reply stays short and punchy in Khmer; a slow, soft, sad or "
    "thoughtful line becomes a calm, flowing Khmer sentence with natural softening particles; a fast angry or excited burst uses clipped, energetic words. "
    "Keep each speaker's pronouns, politeness level and vocabulary consistent across all lines of the video. "
    "(14) ACCURACY: before answering each line, check who does what to whom, when, how many and why; keep every negation, question, condition and number exactly. "
    "Chinese/foreign personal names: transliterate by SOUND the same way every time across all lines, never translate their meaning. Kinship words (older brother, aunt, boss, teacher) must match the real relationship. "
    "Chinese address terms depend on the relationship: 哥/大哥/姐 = បង, 弟/妹 = ប្អូន, 老板 = ថៅកែ, 老公 = ប្តី, 老婆 = ប្រពន្ធ, 妈 = ម៉ែ/ម៉ាក់, 爸 = ប៉ា/ឪពុក, 少爷/小姐 = ប្រើតាមបរិបទ; choose the Khmer word a real family or friend would use, never a stiff dictionary word. "
    "Preserve the feeling: crying, pleading, shouting, laughing and sighing lines must sound emotional in Khmer (short broken sentences for panic, soft long sentences for sadness) while still being one clean grammatical sentence. "
    "If an English hint and the original disagree, the original wins. If a word is unclear choose the most common meaning that fits the scene, never invent or censor content, and never output nonsense words. "
    "(15) SPEAKER GENDER: a line may start with the tag [speaker: male] or [speaker: female]. It is the TRUE gender of the person speaking, "
    "measured from the audio, so trust it over any guess from the text. Write Khmer that fits that speaker: the polite answer yes is បាទ for a man and ចាស for a woman; "
    "formal I is ខ្ញុំបាទ for a man and នាងខ្ញុំ for a woman (ordinary I is ខ្ញុំ for both); a man ends polite sentences with បាទ and a woman with ចាស. "
    "Never give a woman male-only words or a man female-only words, and keep each speaker consistent across all lines. If a line has no tag, stay gender-neutral. Never output the tag. "
    "Output Khmer script only (no English, no Chinese, no romanization). "
    "Return JSON {\"translations\": [...]} with exactly one item per input, same order."
)


# លំនាំដើម = prompt ខ្លីដែលរក្សាភាពត្រឹមត្រូវ ដើម្បីកាត់បន្ថយ token និងពេលឆ្លើយ។ អាចដាក់ LITE_PROMPT=0 ដើម្បីប្រើ prompt ពេញ។
TRANS_SYSTEM_LITE = (
    "You are a Cambodian Khmer dubbing translator. Translate the numbered lines (consecutive lines of ONE video) into natural "
    "everyday SPOKEN Khmer (Phnom Penh), not written/news Khmer and not word-for-word. "
    "Rules: keep exact meaning, names, numbers, negations and emotion; never add or drop facts; pick pronouns/politeness by relationship "
    "and keep them consistent; transliterate foreign names by sound the same way every time; translate idioms by meaning; "
    "one input line = exactly one complete Khmer sentence, same order, never merge or split. "
    "A [max N chars] tag is the TARGET length (aim for 80-105% of N): shorten with simpler wording if too long; if clearly under ~70% of N, phrase it fuller with natural connecting words but never invent facts; never drop a fact; never output the tag. "
    "Output is read by TTS: Khmer script only, end with ។ ? or !, no commas, brackets, quotes, dashes, ellipses, emojis or symbols. "
    "A [speaker: male] or [speaker: female] tag is the true gender of the speaker: use បាទ / ខ្ញុំបាទ for a man and ចាស / នាងខ្ញុំ (formal) for a woman, never swap them; never output the tag. "
    "An English hint, if given, is only a hint; the original wins. "
    'Return JSON {"translations": [...]} with exactly one item per input.'
)
LITE_PROMPT = str(get_secret("LITE_PROMPT", "1")).strip().lower() in ("1", "true", "yes", "on")
TRANS_ACCURACY_NOTE = (
    " FAITHFULNESS FIRST (overrides any length or style wish): the source lines come from automatic speech recognition, so a word may be a "
    "homophone or a mis-heard name. Use the VIDEO SUMMARY and the surrounding lines to pick the reading that fits the story (who is speaking to whom, "
    "the relationship, what just happened), but never invent dialogue. Translate what is actually SAID in each line: keep every fact, "
    "question, negation, number, name, threat, promise and joke, and keep the speaker's attitude (respect, contempt, anger, love). "
    "Do not summarise, soften, embellish or replace a line with a generic sentence. Keep the same person called by the same Khmer name and the same "
    "kinship or title word in every line. If a line has no [max N chars] tag there is NO length limit: translate it fully. "
    "Even when a [max N chars] tag is present, meaning and story fit always win over length."
    " CONNECTED SPEECH (very important): the viewer must hear ONE continuous story, not broken pieces. Make each Khmer line flow naturally from the previous line into the next: "
    "use everyday connecting words (ព្រោះ, ដូច្នេះ, ប៉ុន្តែ, ហើយ, រួចហើយ, ទើប, បើ, តែ) exactly where the logic needs them, keep the same pronouns, names and tense across neighbouring lines, "
    "and never output a line that sounds like an isolated word or label when the original is part of a longer sentence; if a source line is only a fragment of a longer sentence, translate it so it joins smoothly with the lines around it. "
    "Never translate word by word: first understand what the speaker really means in this scene, then say it the way a native Khmer person would say the same thing in the same situation."
    " GLOSSARY: if the context contains a GLOSSARY, use its Khmer renderings exactly for every name and term. "
    "SELF-CHECK before answering: for each line, silently back-translate your Khmer into English and compare it with the source; fix any difference in who did what to whom, negation, question, number, tense or emotion. "
    "A Khmer line that is fluent but says something different from the source is a FAILURE; accuracy first, then naturalness."
)
TRANS_COMEDY_STYLE_NOTE = (
    " KHMER DRAMA DUB HOUSE STYLE: Use natural, lively Phnom Penh spoken Khmer with a slightly cheeky, "
    "mischievous and mildly rude edge when the scene supports it. The target feel is playful drama-comedy banter: "
    "bold, quick-witted, teasing, a little insolent, and conversational rather than polite textbook Khmer. "
    "When characters are arguing, boasting, mocking, flirting, teasing or being sarcastic, choose punchy everyday "
    "phrasing and familiar pronouns such as ឯង, អញ, ហ្អែង or វា only when their relationship and the original tone justify them. "
    "Match the strength of the original insult or joke; keep it mildly cheeky, not needlessly vulgar. "
    "Do not force rude words into every line, do not invent insults, curses, punchlines or reactions, and do not change facts. "
    "Respectful characters remain respectful; serious, sad, dangerous or emotional scenes stay serious. "
    "Keep every line concise enough for its original speaking time while preserving all meaning, names, numbers and negations. "
    "Make the humor sound like something a real Cambodian friend would say, not a literal translation or a forced meme."
)
TRANS_SYSTEM = (TRANS_SYSTEM_LITE if LITE_PROMPT else TRANS_SYSTEM_FULL) + TRANS_ACCURACY_NOTE + TRANS_COMEDY_STYLE_NOTE

# ---- User-selectable translation style (API translation only) ----
@st.cache_resource(show_spinner=False)
def _trans_style_store():
    return {"base": "std", "tails": False}


TRANS_STYLE_CREATIVE_NOTE = (
    " TRANSLATION STYLE = CREATIVE (MANDATORY, applies to EVERY line): do not give a plain literal translation. "
    "Enrich each line with the speaker's real attitude and emotion by choosing vivid, colorful, idiomatic everyday Khmer "
    "words and expressions, and where it helps add a short extra phrase that makes the implied meaning, mood or "
    "emphasis explicit. Localize idioms, jokes and metaphors into things a Cambodian would really say, and vary the "
    "wording so no two lines sound alike. Keep every fact, name, number and negation exactly the same and never "
    "invent new events or information. Keep each line within its speaking-time budget."
)
TRANS_STYLE_SMOOTH_NOTE = (
    " TRANSLATION STYLE = SMOOTH (MANDATORY, applies to EVERY line, and overrides the cheeky/rude house style above): "
    "write calm, well-edited spoken Khmer that flows naturally. Where a source line is short or choppy, add the small "
    "connecting words or a brief clarifying phrase so the dialogue reads as one continuous conversation. No forced "
    "slang or insults; clean, rhythmic sentences that are easy to listen to; keep the original meaning and emotion; "
    "keep each line within its speaking-time budget."
)
TRANS_STYLE_TAILS_NOTE = (
    " SENTENCE TAILS (MANDATORY): end EVERY statement line with a natural Khmer sentence-final particle chosen to fit "
    "the speaker's tone and relationship (soft and friendly, firm, teasing, or surprised), and vary the particle between "
    "lines. Question lines may keep their question word as the ending. Never change the meaning, and keep each line "
    "within its speaking-time budget."
)


_TAIL_SET = ("ណា", "ណាស់", "ហ្នឹងហើយ", "ណ៎ា", "ផង", "សោះ", "ទេតើ", "ហ្ន៎ា", "អ៊ីចឹង", "ហើយ")
_TAIL_NO = ("?", "\uff1f", "ទេ", "អត់", "អី", "ឬ")


def _apply_tails(outs, budgets=None):
    """Guarantee sentence tails: if the user enabled them and a statement line has no
    final particle (the AI may skip some), append one -- unless it would break timing."""
    try:
        if not _trans_style_store().get("tails"):
            return outs
    except Exception:
        return outs
    cyc = ("ណា", "ណ៎ា")   # soft particles only: they never change the meaning
    res = []
    for i, o in enumerate(outs):
        t = (o or "").strip() if isinstance(o, str) else o
        if not t or not has_khmer(str(t)):
            res.append(o)
            continue
        core = str(t).rstrip("។!?\uff01\uff1f .\u2026")
        tail_punct = str(t)[len(core):]
        if not core or core.endswith(_TAIL_SET) or core.endswith(_TAIL_NO) or "?" in tail_punct or "\uff1f" in tail_punct:
            res.append(o)
            continue
        tail = cyc[i % len(cyc)]
        bud = budgets[i] if budgets and i < len(budgets) else None
        if bud and len(core.replace(" ", "")) + len(tail) > int(bud * 1.1):
            res.append(o)
            continue
        res.append(core + " " + tail + tail_punct)
    return res


def _trans_style_extra():
    try:
        st_ = _trans_style_store()
        extra = ""
        if st_.get("base") == "creative":
            extra += TRANS_STYLE_CREATIVE_NOTE
        elif st_.get("base") == "smooth":
            extra += TRANS_STYLE_SMOOTH_NOTE
        if st_.get("tails"):
            extra += TRANS_STYLE_TAILS_NOTE
        return extra
    except Exception:
        return ""


def _trans_sys():
    """Base translation system prompt plus the style the user chose in the UI."""
    return TRANS_SYSTEM + _trans_style_extra()


def _groq_is_too_large(msg):
    low = str(msg).lower()
    return "request too large" in low or "reduce your message size" in low or "413" in low or "context_length" in low


def _groq_shrink_system(system):
    """បង្រួម prompt: ប្តូរ prompt ពេញទៅ LITE ហើយកាត់បរិបទរឿង (STORY/SUMMARY) ឱ្យខ្លី។"""
    sys_ = system or _trans_sys()
    sys_ = sys_.replace(TRANS_SYSTEM_FULL, TRANS_SYSTEM_LITE)
    for tag in (" STORY SO FAR", "VIDEO SUMMARY:"):
        i = sys_.find(tag)
        if i > 0 and len(sys_) - i > 1500:
            sys_ = sys_[:i + 1500]
            break
    return sys_


def _groq_translate_chunk_impl(api_key, texts, budgets=None, system=None, to_english=False, rotate=False, _depth=0):
    try:
        return _groq_translate_chunk_core(api_key, texts, budgets, system, to_english, rotate)
    except Exception as e:
        if not _groq_is_too_large(e) or _depth >= 3:
            raise
        # ជំហាន ១: បង្រួម prompt រួចសាកម្តងទៀត
        if _depth == 0:
            small = _groq_shrink_system(system)
            if small != (system or _trans_sys()):
                try:
                    return _groq_translate_chunk_core(api_key, texts, budgets, small, to_english, rotate)
                except Exception as e2:
                    if not _groq_is_too_large(e2):
                        raise
                system = small
        # ជំហាន ២: ចែកបាច់ជាពាក់កណ្តាល
        if len(texts) < 2:
            raise
        mid = len(texts) // 2
        b1 = budgets[:mid] if budgets else None
        b2 = budgets[mid:] if budgets else None
        left = _groq_translate_chunk_impl(api_key, texts[:mid], b1, system, to_english, rotate, _depth + 1)
        right = _groq_translate_chunk_impl(api_key, texts[mid:], b2, system, to_english, rotate, _depth + 1)
        return list(left) + list(right)


def _groq_translate_chunk_core(api_key, texts, budgets=None, system=None, to_english=False, rotate=False):
    numbered = "\n".join(
        f"{i + 1}. " + (f"[max {budgets[i]} chars] " if budgets and budgets[i] else "") + str(t)
        for i, t in enumerate(texts)
    )
    models = groq_chat_models(api_key)
    _strong = [m for m in models if not any(x in m.lower() for x in ("8b", "instant", "scout", "20b"))]
    models = model_order(_strong or models, "groq")
    if rotate and len(models) > 1:
        _shift = (int(rotate) if not isinstance(rotate, bool) else 1) % len(models)
        models = models[_shift:] + models[:_shift]   # ឱ្យម៉ូដែលផ្សេងពីអ្នកបកដំបូង មកពិនិត្យ
    last = "មិនមានម៉ូដែល"
    for model in models[:8]:
        body = json.dumps({
            "model": model, "temperature": 0.05,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system or _trans_sys()},
                {"role": "user", "content": numbered},
            ],
        }).encode("utf-8")
        for attempt in range(2):
            request = urllib.request.Request(GROQ_CHAT_URL, data=body, method="POST", headers={"Authorization": f"Bearer {groq_first(api_key)}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            try:
                with groq_urlopen(request, api_key, timeout=60) as r:
                    data = json.loads(r.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
                items = json.loads(content).get("translations") or []
                if len(items) == len(texts):
                    _groq_chat_cache["good"] = model
                    model_good("groq", model)
                    return [((str(x).strip() or None) if to_english else clean_translation(x)) for x in items]
                last = f"{model}: ចំនួនបន្ទាត់មិនត្រូវគ្នា"
                model_cool(model, last)
                break
            except urllib.error.HTTPError as e:
                last = f"{model}: {http_detail(e)}"
                if _groq_is_too_large(last):
                    break   # ធំពេក → កុំសម្រាកម៉ូដែល កុំរង់ចាំ (ឱ្យ caller បង្រួម/ចែកបាច់)
                if e.code == 429 and attempt == 0:
                    time.sleep(6)
                    continue
                model_cool(model, last)
                break
            except Exception as e:
                last = f"{model}: {e}"
                model_cool(model, last)
                break
    _groq_chat_cache["models"] = None  # បញ្ជីម៉ូដែលអាចហួសសម័យ ទាញថ្មីលើកក្រោយ
    raise RuntimeError(last[:300])


# =====================================================================
#  CodeCraft API (OpenAI-compatible) — សម្រាប់ការងារអត្ថបទ/បកប្រែ (ជំនួស CodeCraft)
#  Secrets: CODECRAFT_API_KEY, CODECRAFT_BASE_URL (ចាំបាច់ បញ្ចប់ត្រឹម /v1), CODECRAFT_MODEL (ចាំបាច់)
# =====================================================================
OAI_KEY = get_secret("CODECRAFT_API_KEY", "").strip()
# CodeCraft API documentation default. Can still be overridden in Secrets.
OAI_BASE = (get_secret("CODECRAFT_BASE_URL", "https://codecraftapi.com/v1") or
            "https://codecraftapi.com/v1").strip().rstrip("/")
OAI_MODEL = get_secret("CODECRAFT_MODEL", "").strip()


# =====================================================================
#  Claude (Anthropic) API — ម៉ាស៊ីនបកប្រែល្អបំផុត (ត្រូវបានសាកមុនគេ បើមាន Key)
#  Secrets:
#    ANTHROPIC_API_KEY  (ឬ CLAUDE_API_KEY)  ← ដាក់បានច្រើន Key: ANTHROPIC_API_KEYS ឬ ANTHROPIC_API_KEY_1, _2 ...
#    ANTHROPIC_BASE_URL (មិនចាំបាច់ — លំនាំដើម https://api.laalaa.me
#                        បើប្រើ Claude Code API ពីហាង/proxy សូមដាក់ Base URL ដែលហាងផ្តល់ឱ្យ)
#    ANTHROPIC_MODEL    (មិនចាំបាច់ — លំនាំដើម claude-sonnet-5-5)
# =====================================================================
_claude_vals = [
    get_secret("ANTHROPIC_API_KEY", ""), get_secret("ANTHROPIC_API_KEYS", ""),
    get_secret("CLAUDE_API_KEY", ""), get_secret("CLAUDE_API_KEYS", ""),
]
for _ci in range(1, 21):
    _claude_vals.append(get_secret(f"ANTHROPIC_API_KEY_{_ci}", ""))
CLAUDE_KEYS = split_keys(_claude_vals)
CLAUDE_BASE = (str(get_secret("ANTHROPIC_BASE_URL", "https://api.laalaa.me") or "").strip().rstrip("/")
               or "https://api.laalaa.me")
CLAUDE_MODEL = (str(get_secret("ANTHROPIC_MODEL", "claude-sonnet-5-5") or "").strip() or "claude-sonnet-5-5")
_CLAUDE_SECRET_PROVIDERS = [(f"Claude #{_i}", (_k, CLAUDE_BASE, CLAUDE_MODEL)) for _i, _k in enumerate(CLAUDE_KEYS, start=1)]
_CLAUDE_PROVIDERS = list(_CLAUDE_SECRET_PROVIDERS)   # បញ្ជីដែលកំពុងប្រើ (Key ផ្ទាល់ខ្លួនមុន រួច Secrets) — ធ្វើបច្ចុប្បន្នភាពពេលចុច «ចាប់ផ្តើម»
_CLAUDE_COOL = {}


def claude_enabled():
    return bool(_CLAUDE_PROVIDERS)


_CLAUDE_FALLBACK_MODELS = ["claude-sonnet-5-5", "claude-sonnet-5"]   # ដក Opus ចេញ (ថ្លៃជាង ៥ដង)
_CLAUDE_GOOD_MODEL = {}
_CLAUDE_LAST_CALL = {}
_CLAUDE_MIN_GAP = 1.2   # laalaa មាន 30 request/នាទី → ទុកគម្លាត ≥2.2វិ រវាងការហៅ


_CLAUDE_LOCK = threading.Lock()


def _claude_throttle(key="default"):
    """throttle ដាច់ដោយឡែកសម្រាប់ Key នីមួយៗ — Key ច្រើន = ហៅស្របគ្នាបាន (លឿនជាង)។"""
    with _CLAUDE_LOCK:
        now = time.time()
        slot = max(now, _CLAUDE_LAST_CALL.get(key, 0.0) + _CLAUDE_MIN_GAP)
        _CLAUDE_LAST_CALL[key] = slot
    wait = slot - now
    if wait > 0:
        time.sleep(wait)


def claude_translate_chunk(texts, budgets=None, system=None, to_english=False, cfg=None, raw=False):
    """ហៅ Claude តាម Anthropic Messages API (/v1/messages) ហើយទទួលលទ្ធផល JSON {"translations": [...]}។"""
    _key, _base, _model = cfg
    if not (_key and _base and _model):
        raise RuntimeError("Claude: សូមកំណត់ ANTHROPIC_API_KEY ក្នុង Secrets។")
    numbered = "\n".join(
        f"{i + 1}. " + (f"[max {budgets[i]} chars] " if budgets and i < len(budgets) and budgets[i] else "") + str(t)
        for i, t in enumerate(texts)
    )
    sys_text = (system or _trans_sys()) + ' Return ONLY the JSON object {"translations": [...]} with no other text.'
    url = _base + ("/messages" if _base.endswith("/v1") else "/v1/messages")
    use_temp = True
    _first = _CLAUDE_GOOD_MODEL.get(_key) or _model
    models = [_first] + [m for m in [_model] + _CLAUDE_FALLBACK_MODELS if m != _first]
    mi = 0
    last = "Claude: មិនទាន់ទទួលបានចម្លើយ"
    for attempt in range(3):
        payload = {
            "model": models[mi],
            "max_tokens": min(5000, 400 + 200 * len(texts)),
            "system": sys_text,
            "messages": [{"role": "user", "content": numbered}],
        }
        if use_temp:
            payload["temperature"] = 0.1
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url, data=body, method="POST",
            headers={
                "x-api-key": _key,
                "Authorization": f"Bearer {_key}",
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
        )
        _claude_throttle(_key)
        try:
            with urllib.request.urlopen(request, timeout=45) as r:
                data = json.loads(r.read().decode("utf-8"))
            content = "".join(b.get("text", "") for b in (data.get("content") or []) if b.get("type") == "text")
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
            content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.M).strip()
            match = re.search(r"\{.*\}", content, flags=re.S)
            parsed = json.loads(match.group(0) if match else content)
            items = parsed.get("translations") or []
            if len(items) == len(texts):
                _CLAUDE_GOOD_MODEL[_key] = models[mi]
                if raw:
                    return list(items)
                return [((str(x).strip() or None) if to_english else clean_translation(x)) for x in items]
            last = "Claude: ឆ្លើយតបមិនគ្រប់ចំនួនបន្ទាត់"
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "ignore")[:220]
            except Exception as _swallow_e:
                _log_swallowed(_swallow_e)
            last = f"Claude HTTP {e.code}: {detail}".strip()
            if e.code == 400 and use_temp and attempt < 2:
                use_temp = False          # ម៉ូដែលខ្លះមិនទទួល temperature → សាកដោយគ្មាន
                continue
            if e.code in (404, 503, 529) and mi + 1 < len(models):
                mi += 1                   # model នេះគ្មាន account ទំនេរ → សាក model បន្ទាប់
                time.sleep(0.5)
                continue
            if e.code in (429, 500, 502, 503, 504, 529) and attempt < 2:
                _wait = 0.0
                try:
                    _wait = float(e.headers.get("Retry-After", "0") or 0)
                except Exception:
                    _wait = 0.0
                time.sleep(min(max(_wait, 2.0 * (attempt + 1)), 8.0))   # រង់ចាំកើនឡើង 3,6,9,12វិ
                continue
            raise RuntimeError(last)
        except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
            last = f"Claude បណ្តាញ/Timeout: {e}"
            if attempt < 1:
                time.sleep(2)
                continue
            raise RuntimeError(last)
        except Exception as e:
            last = f"Claude: {e}"
    raise RuntimeError(last[:400])


# Additional OpenAI-compatible providers. Add only providers for which the owner
# has supplied a key. Free-tier availability/quota is controlled by each provider.
# Cloudflare BASE_URL must include the account id, e.g. .../accounts/<ID>/ai/v1.
_EXTRA_PROVIDER_SPECS = [
    ("OpenRouter", "OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "OPENROUTER_MODEL", "https://openrouter.ai/api/v1", "openrouter/free"),
    ("Cloudflare Workers AI", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_BASE_URL", "CLOUDFLARE_MODEL", "", "@cf/meta/llama-3.1-8b-instruct"),
    ("Mistral AI", "MISTRAL_API_KEY", "MISTRAL_BASE_URL", "MISTRAL_MODEL", "https://api.mistral.ai/v1", "mistral-small-latest"),
    ("NVIDIA NIM", "NVIDIA_API_KEY", "NVIDIA_BASE_URL", "NVIDIA_MODEL", "https://integrate.api.nvidia.com/v1", "meta/llama-3.3-70b-instruct"),
    ("Cohere Compatibility", "COHERE_API_KEY", "COHERE_BASE_URL", "COHERE_MODEL", "https://api.cohere.com/compatibility/v1", "command-r7b-12-2024"),
    ("SambaNova", "SAMBANOVA_API_KEY", "SAMBANOVA_BASE_URL", "SAMBANOVA_MODEL", "https://api.sambanova.ai/v1", "Meta-Llama-3.3-70B-Instruct"),
]
_EXTRA_PROVIDERS = []
for _pname, _pkey, _pbase, _pmodel, _default_base, _default_model in _EXTRA_PROVIDER_SPECS:
    _pb = str(get_secret(_pbase, _default_base) or _default_base).strip().rstrip("/")
    _pm = str(get_secret(_pmodel, _default_model) or _default_model).strip()

    # OpenRouter supports a list of keys. Try every configured key as its own
    # provider entry, so one 429/invalid key does not stop the other keys.
    if _pname == "OpenRouter":
        _key_values = [
            get_secret("OPENROUTER_API_KEY", ""),
            get_secret("OPENROUTER_API_KEYS", ""),
        ]
        for _key_i in range(1, 21):
            _key_values.append(get_secret(f"OPENROUTER_API_KEY_{_key_i}", ""))
        _keys = split_keys(_key_values)
        if _pb.startswith("https://") and _pm:
            for _idx, _pk in enumerate(_keys, start=1):
                if _pk:
                    _EXTRA_PROVIDERS.append((f"OpenRouter #{_idx}", (_pk, _pb, _pm)))
        continue

    _pk = str(get_secret(_pkey, "") or "").strip()
    if _pk and _pb.startswith("https://") and _pm:
        _EXTRA_PROVIDERS.append((_pname, (_pk, _pb, _pm)))


def extra_provider_enabled():
    return bool(_EXTRA_PROVIDERS)


_API_LOCAL = threading.local()

def oai_cfg():
    # Worker ម្នាក់ៗប្រើ Key របស់ session ខ្លួនឯង មិនចែករំលែក Key រវាងអ្នកប្រើ។
    c = getattr(_API_LOCAL, "xk_cfg", None)
    if c is not None:
        return c
    return (OAI_KEY, OAI_BASE.rstrip("/"), OAI_MODEL)


def xk_enabled():
    k, b, m = oai_cfg()
    return bool(k and b and m)


def oai_enabled():
    """មានម៉ាស៊ីនបកប្រែ OpenAI-compatible យ៉ាងហោចណាស់មួយ។"""
    return claude_enabled() or xk_enabled() or extra_provider_enabled()


def oai_translate_chunk(texts, budgets=None, system=None, to_english=False, cfg=None, raw=False):
    """ការបកប្រែ CodeCraft ដោយសន្សំ token និងកាត់បន្ថយ API calls។"""
    _key, _base, _model = cfg if cfg else oai_cfg()
    if not (_key and _base and _model):
        raise RuntimeError("សូមបញ្ចូល CodeCraft API Key ផ្ទាល់ខ្លួន។")
    numbered = "\\n".join(
        f"{i + 1}. " + (f"[max {budgets[i]} chars] " if budgets and i < len(budgets) and budgets[i] else "") + str(t)
        for i, t in enumerate(texts)
    )
    payload = {
        "model": _model,
        "temperature": 0,
        "max_tokens": min(4096, max(256, sum(len(str(t)) for t in texts) * 3 + 160)),
        "messages": [
            {"role": "system", "content": system or _trans_sys()},
            {"role": "user", "content": numbered},
        ],
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    last = "CodeCraft: មិនទាន់ទទួលបានចម្លើយ"
    for attempt in range(2):
        request = urllib.request.Request(
            _base.rstrip("/") + "/chat/completions", data=body, method="POST",
            headers={"Authorization": f"Bearer {_key}", "Content-Type": "application/json",
                     "Accept": "application/json",
                     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"},
        )
        try:
            with urllib.request.urlopen(request, timeout=35) as r:
                data = json.loads(r.read().decode("utf-8"))
            content = data["choices"][0]["message"].get("content") or ""
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
            content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.M).strip()
            match = re.search(r"\\{.*\\}", content, flags=re.S)
            parsed = json.loads(match.group(0) if match else content)
            items = parsed.get("translations") or []
            if len(items) != len(texts):
                raise RuntimeError("CodeCraft: ម៉ូដែលឆ្លើយតបមិនគ្រប់ចំនួនបន្ទាត់")
            if raw:
                return list(items)
            return [((str(x).strip() or None) if to_english else clean_translation(x)) for x in items]
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:180]
            last = f"CodeCraft HTTP {e.code}: {detail}"
            if e.code in (429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(1)
                continue
            raise RuntimeError(last)
        except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
            raise RuntimeError(f"CodeCraft បណ្តាញ/Timeout: {e}")
    raise RuntimeError(last)


def fetch_codecraft_models(key, base, timeout=18):
    """ទាញបញ្ជី Model ID ពី CodeCraft GET /v1/models។"""
    key = str(key or "").strip()
    base = str(base or "https://codecraftapi.com/v1").strip().rstrip("/")
    if not key:
        raise RuntimeError("សូមបញ្ចូល CodeCraft API Key ជាមុន។")
    if not base.startswith("https://"):
        raise RuntimeError("Base URL ត្រូវចាប់ផ្តើមដោយ https://")
    req = urllib.request.Request(
        base + "/models",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json",
                 "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    models = []
    for row in rows:
        if isinstance(row, dict):
            mid = str(row.get("id") or row.get("model") or "").strip()
            if mid and mid not in models:
                models.append(mid)
    if not models:
        raise RuntimeError("API ឆ្លើយតបបាន ប៉ុន្តែមិនមាន Model ID ក្នុង data។")
    return sorted(models)


def oai_test(key, base, model):
    """សាកល្បង CodeCraft: ត្រឡប់ (True/False, សារ)។"""
    key, base, model = str(key).strip(), str(base).strip().rstrip("/"), str(model).strip()
    if not (key and base and model):
        return False, "សូមបំពេញ Key, Base URL និងឈ្មោះម៉ូដែលឱ្យគ្រប់។"
    if not base.startswith("http"):
        return False, "Base URL ត្រូវចាប់ផ្តើមដោយ https://"
    try:
        out = oai_translate_chunk(["hello"], None, 'Translate each line to Khmer. Return JSON {"translations": [...]} only.', cfg=(key, base, model))
        return (True, "") if out else (False, "មិនមានចម្លើយ")
    except Exception as e:
        return False, "សាកមិនបាន៖ " + str(e)[:220]


def _claude_tier(texts, budgets, system, to_english):
    """ម៉ាស៊ីនសំខាន់ #1: Claude (គ្រប់ Key ដែលមាន)។"""
    if not claude_enabled():
        return None
    for _cn, _cc in _CLAUDE_PROVIDERS:
        _cl = _CLAUDE_COOL.setdefault(_cn, {"until": 0.0})
        if _cl.get("until", 0) > time.time():
            continue
        _cr = _try_provider(_cl, _cc, texts, budgets, system, to_english, False, name=_cn, fn=claude_translate_chunk)
        if _cr is not None:
            return _cr
    return None


def groq_translate_chunk(api_key, texts, budgets=None, system=None, to_english=False, rotate=False):
    """លំដាប់ថ្មី៖
       ម៉ាស៊ីនសំខាន់ = Claude + Groq (CLAUDE_FIRST=1 → Claude មុន; =0 → Groq មុន)
       ម៉ាស៊ីនបម្រុង = OpenRouter / Mistral / NVIDIA / ... / CodeCraft (ប្រើតែពេលសំខាន់ទាំងពីរបរាជ័យ)"""
    groq_err = None

    def _groq():
        nonlocal groq_err
        if not api_key:
            return None
        try:
            return _groq_translate_chunk_impl(api_key, texts, budgets, system, to_english, rotate)
        except Exception as e:
            groq_err = e
            _LAST_AI_ERR["Groq"] = str(e)[:260]
            return None

    primaries = [lambda: _claude_tier(texts, budgets, system, to_english), _groq]
    if not CLAUDE_FIRST:
        primaries.reverse()
    for _p in primaries:
        _r = _p()
        if _r is not None:
            return _r

    # ---- ម៉ាស៊ីនបម្រុង (មិនរាប់ Claude ម្តងទៀត) ----
    if extra_provider_enabled() or xk_enabled():
        _r = oai_try(texts, budgets, system, to_english, skip_claude=True)
        if _r is not None:
            return _r

    parts = [f"Groq: {str(groq_err)[:150]}"] if groq_err else []
    if _LAST_AI_ERR:
        parts.append("; ".join(f"{k}: {v}"[:110] for k, v in list(_LAST_AI_ERR.items())[:4]))
    parts.append("ស្ថានភាព៖ " + provider_status())
    raise RuntimeError(" | ".join(parts))


_OAI_COOL = {"until": 0.0}
_EXTRA_COOL = {}


_LAST_AI_ERR = {}


def _try_provider(cool, cfg, texts, budgets, system, to_english, raw, name="CodeCraft", fn=None):
    for attempt in range(2):
        try:
            return (fn or oai_translate_chunk)(texts, budgets, system, to_english, cfg=cfg, raw=raw)
        except Exception as e:
            _LAST_AI_ERR[name] = str(e)[:260]   # ទុកមូលហេតុពិត ដើម្បីបង្ហាញអ្នកប្រើ
            if "ចំនួនបន្ទាត់" in str(e):
                continue   # ម៉ូដែលឆ្លើយខុសចំនួនបន្ទាត់ → សាកម្តងទៀត មិនសម្រាកទាំងមូល
            _m = str(e)
            if any(f"HTTP {c}" in _m for c in (401, 402, 403, 404)):
                _cd = 600      # Key/URL/model ខុស → សម្រាកយូរ
            elif any(f"HTTP {c}" in _m for c in (429, 503, 529)):
                _cd = 10       # Rate limit បណ្តោះអាសន្ន → សម្រាកខ្លី រួចសាកវិញ
            else:
                _cd = 60       # server/បណ្តាញមានបញ្ហា
            cool["until"] = time.time() + _cd
            return None
    return None


def provider_status():
    """សង្ខេបស្ថានភាពម៉ាស៊ីន AI នីមួយៗ (បានកំណត់ឬអត់ / កំពុងសម្រាក) ដើម្បីបង្ហាញក្នុងសារកំហុស។"""
    now = time.time()
    def _cool(c):
        left = int(c.get("until", 0) - now)
        return f" (សម្រាក {left}វិ)" if left > 0 else ""
    out = []
    try:
        out.append("Groq ✓" if (GROQ_KEY or has_user_keys()) else "Groq ✗ (គ្មាន key)")
    except Exception:
        out.append("Groq ?")
    if claude_enabled():
        out.append(f"Claude ×{len(_CLAUDE_PROVIDERS)} ✓")
    else:
        out.append("Claude ✗ (គ្មាន ANTHROPIC_API_KEY)")
    names = [n for n, _ in _EXTRA_PROVIDERS]
    n_or = sum(1 for n in names if n.startswith("OpenRouter"))
    out.append(f"OpenRouter ×{n_or}" if n_or else "OpenRouter ✗ (គ្មាន key)")
    for n in names:
        if not n.startswith("OpenRouter"):
            out.append(f"{n} ✓" + _cool(_EXTRA_COOL.get(n, {})))
    if xk_enabled():
        out.append("CodeCraft ✓" + _cool(_OAI_COOL))
    else:
        _k, _b, _m = oai_cfg()
        miss = [n for n, v in (("API_KEY", _k), ("BASE_URL", _b.startswith("http") and _b), ("MODEL", _m)) if not v]
        out.append("CodeCraft ✗ (ខ្វះ CODECRAFT_" + ", CODECRAFT_".join(miss) + ")")
    return " · ".join(out)


def oai_try(texts, budgets=None, system=None, to_english=False, raw=False, skip_claude=False):
    """ម៉ាស៊ីនបម្រុងក្រៅពី Groq តាមលំដាប់៖ OpenRouter(+ផ្សេងៗ) → CodeCraft
    (មានកំណត់ពេលសរុប ១២០ វិនាទីក្នុងមួយបាច់)។"""
    if getattr(_API_LOCAL, "isolated", False):
        _cfg = oai_cfg()
        if not all(_cfg):
            return None
        try:
            return oai_translate_chunk(texts, budgets, system, to_english, cfg=_cfg, raw=raw)
        except Exception as e:
            _API_LOCAL.last_error = str(e)[:200]
            return None
    t_end = time.time() + 60
    def _claude_pass():
        for _name, _cfg in _CLAUDE_PROVIDERS:
            if time.time() >= t_end:
                break
            _cool = _CLAUDE_COOL.setdefault(_name, {"until": 0.0})
            if _cool.get("until", 0) > time.time():
                continue
            r = _try_provider(_cool, _cfg, texts, budgets, system, to_english, raw, name=_name, fn=claude_translate_chunk)
            if r is not None:
                return r
        return None
    if CLAUDE_FIRST and not skip_claude:
        r = _claude_pass()
        if r is not None:
            return r
    for _name, _cfg in []:
        if time.time() >= t_end:
            break
        _cool = _CLAUDE_COOL.setdefault(_name, {"until": 0.0})
        if _cool.get("until", 0) > time.time():
            continue
        r = _try_provider(_cool, _cfg, texts, budgets, system, to_english, raw, name=_name, fn=claude_translate_chunk)
        if r is not None:
            return r
    for _name, _cfg in _EXTRA_PROVIDERS:
        if time.time() >= t_end:
            break
        _cool = _EXTRA_COOL.setdefault(_name, {"until": 0.0})
        if _cool.get("until", 0) > time.time():
            continue
        r = _try_provider(_cool, _cfg, texts, budgets, system, to_english, raw, name=_name)
        if r is not None:
            return r
    if xk_enabled() and _OAI_COOL.get("until", 0) <= time.time() and time.time() < t_end:
        r = _try_provider(_OAI_COOL, oai_cfg(), texts, budgets, system, to_english, raw, name="CodeCraft")
        if r is not None:
            return r
    if not CLAUDE_FIRST and not skip_claude:
        return _claude_pass()
    return None


EN_SYSTEM = (
    "You are a careful transcription-correction and meaning bridge for dubbing. The numbered lines are consecutive lines from ONE video; "
    "use surrounding context to resolve only obvious Whisper errors, speaker references, slang, and idioms. Render each line as clear, "
    "faithful English that preserves every meaningful detail, emotion and tone (anger, sarcasm, sadness, affection). Do not translate beyond what the audio supports, add explanations, "
    "embellish, or guess at unclear words; mark genuinely unclear audio as [unclear]. "
    "mark genuinely unclear audio as [unclear] rather than making up dialogue. Keep exactly one output for each input line, same order. "
    "Return JSON {\"translations\": [...]} only."
)


def gemini_translate_khmer(api_key, texts, english=None, budgets=None, story=None, groq_key=None, speakers=None):
    """បកជាខ្មែរ៖ Claude ជាមុនគេ (តាម CLAUDE_FIRST) រួច provider បម្រុង។"""
    rows = []
    for i, text in enumerate(texts):
        row = spk_tag(speakers[i] if speakers and i < len(speakers) else None) + str(text)
        if english and i < len(english) and english[i] and "[unclear]" not in str(english[i]):
            row += f" (English meaning: {english[i]})"
        rows.append(row)
    system = (
        _trans_sys()
        + " The ORIGINAL source-language transcript is authoritative; English in parentheses is only a secondary meaning hint. "
          "Translate every line into accurate, natural spoken Cambodian Khmer. Preserve all facts, names, relationships, pronouns, numbers, negation, conditions, subject/object roles, intent, humor, sarcasm and emotion. "
          "Use the surrounding story only to resolve ambiguity; never invent missing dialogue. Never omit or add meaning. Output Khmer only; never output English text or tags."
        + ((" STORY SO FAR (context only, do NOT translate): " + story) if story else "")
    )
    # កុំទុកឱ្យចម្លើយភាសាអង់គ្លេស/ចម្លើយខ្វះបន្ទាត់ឆ្លងទៅ Subtitle។
    # សាកម៉ាស៊ីនសំខាន់ រួចម៉ាស៊ីនបម្រុងដោយផ្ទាល់ និងពិនិត្យ Khmer មុន return។
    _attempt_errors = []
    _candidates = []
    if groq_key:
        _candidates.append(("Groq + providers", lambda: groq_translate_chunk(groq_key, rows, budgets, system=system)))
    if oai_enabled():
        # បើគ្មាន Groq key → Claude ជាសំខាន់ (oai_try រួមទាំង Claude); បើមាន Groq key → groq_translate_chunk ធ្វើរួចហើយ
        _candidates.append(("Claude/បម្រុង", lambda: oai_try(rows, budgets, system, skip_claude=bool(groq_key))))
    for _name, _call in _candidates:
        try:
            _result = _call()
            if not isinstance(_result, (list, tuple)) or len(_result) != len(rows):
                raise RuntimeError("ចំនួនបន្ទាត់ចម្លើយមិនត្រូវនឹងអត្ថបទដើម")
            _cleaned = [clean_translation(x) for x in _result]
            _bad = [i + 1 for i, x in enumerate(_cleaned) if not x or not has_khmer(str(x)) or not khmer_dominant(str(x))]
            if _bad:
                raise RuntimeError("ចម្លើយមិនមែនជាភាសាខ្មែរត្រឹមត្រូវ នៅបន្ទាត់ " + ",".join(map(str, _bad[:12])))
            return _cleaned
        except Exception as _e:
            _attempt_errors.append(f"{_name}: {str(_e)[:180]}")
    _why = " | ".join(_attempt_errors) or " | ".join(f"{k}: {v}" for k, v in _LAST_AI_ERR.items()) or "គ្មាន API Key ដែលអាចប្រើបាន"
    raise RuntimeError("ម៉ាស៊ីន AI បកប្រែមិនបាន។ មូលហេតុ៖ " + _why + " | ស្ថានភាព៖ " + provider_status())


REFINE_SYSTEM = (
    "You are a senior Khmer (Cambodian) dubbing editor and bilingual proofreader. For EVERY item first back-translate the KHMER DRAFT into English in your head and compare it with the ORIGINAL: any difference in meaning (an idea added or missing, a lost negation, wrong subject or object, wrong number or name, wrong tense or mood, changed emotion or tone) must be fixed. Each numbered item has an ORIGINAL line, "
    "sometimes an ENGLISH meaning, and a KHMER DRAFT. Check the KHMER DRAFT against the ORIGINAL: fix wrong or missing meaning, "
    "mistranslated words, wrong pronouns/politeness, literal word-for-word phrasing, unnatural or ungrammatical Khmer, and any leftover "
    "foreign words (except names). Rewrite into natural everyday SPOKEN Khmer that a native Phnom Penh speaker would say and instantly understand, "
    "keeping exactly the same facts, names, numbers, emotion and tone. Do not add or remove information. If the draft is already correct and natural, "
    "return it unchanged. Use the neighbouring items as story context (who speaks to whom). One complete sentence per item, same order, "
    "Khmer script only, end with ។ (or ? !), no commas, brackets, quotes, dashes, ellipses, emojis or symbols. "
    "Also verify: every negation, question, number, name (same transliteration in every line), kinship word and who-does-what-to-whom is exactly right, and the Khmer has no invented or nonsense words. "
    "Also make the whole script sound like ONE connected story told by real people: fix choppy, isolated or label-like lines by joining them naturally with the neighbouring lines using everyday connecting words (ព្រោះ, ដូច្នេះ, ប៉ុន្តែ, ហើយ, ទើប), while keeping one sentence per item and the same meaning. "
    "Return JSON {\"translations\": [...]} with exactly one item per input."
    " COMEDY DUB STYLE: preserve a slightly cheeky, mildly insolent Phnom Penh banter style when the ORIGINAL is teasing, sarcastic, "
    "boastful or argumentative. Familiar rough pronouns and playful jabs are allowed only when the relationship and original tone support them. "
    "Match the original insult strength; never add insults, curses, jokes, facts or reactions that were not spoken. "
    "Keep respectful lines respectful and serious or sad scenes serious. Accuracy always comes before comedy."
)


def refine_khmer(texts, englishes, drafts, gemini_key, groq_key, progress=None, shift=1, speakers=None):
    """ពិនិត្យការបកប្រែខ្មែរម្តងទៀតប្រៀបធៀបនឹងអត្ថបទដើម ហើយកែឱ្យត្រូវន័យ និងស្ទួនភាសាខ្មែរធម្មជាតិ។"""
    n = len(drafts)
    result = list(drafts)
    groups = [list(range(k, min(k + LLM_GROUP, n))) for k in range(0, n, LLM_GROUP)]

    def rows_for(idxs):
        rows = []
        for i in idxs:
            row = f"ORIGINAL: {str(texts[i]).strip()}"
            if englishes[i] and "[unclear]" not in englishes[i]:
                row += f" | ENGLISH: {englishes[i]}"
            if speakers and i < len(speakers) and speakers[i]:
                row += " | SPEAKER: " + ("male" if speakers[i] == "M" else "female")
            row += f" | KHMER DRAFT: {drafts[i]}"
            rows.append(row)
        return rows

    def story_for(idxs):
        prev = [str(drafts[j]) for j in range(max(0, idxs[0] - 8), idxs[0]) if drafts[j]]
        nxt = [str(drafts[j]) for j in range(idxs[-1] + 1, min(n, idxs[-1] + 5)) if drafts[j]]
        s = ""
        if prev:
            s += "PREVIOUS LINES (context only): " + " / ".join(prev) + "\n"
        if nxt:
            s += "NEXT LINES (context only): " + " / ".join(nxt) + "\n"
        return s

    def work(idxs):
        rows = rows_for(idxs)
        story = story_for(idxs)
        _r = oai_try(rows, None, REFINE_SYSTEM + _trans_style_extra() + " " + story)
        if _r is not None:
            return idxs, _r
        if gemini_key:
            try:
                client = make_gemini_client(gemini_key, types.HttpOptions(timeout=TRANSLATE_TIMEOUT_MS))
                avail = get_available_models(client)
                models = [m for m in avail if "pro" in m.lower()] + [m for m in avail if "pro" not in m.lower()]
                models = model_order(models[:5], "gemini-refine")
                numbered = "\n".join(f"{k + 1}. {r}" for k, r in enumerate(rows))
                prompt = REFINE_SYSTEM + _trans_style_extra() + "\n\n" + story + "\nITEMS:\n" + numbered
                for model in models:
                    try:
                        resp = client.models.generate_content(
                            model=model, contents=prompt,
                            config=types.GenerateContentConfig(temperature=0.15, response_mime_type="application/json"),
                        )
                        raw = (getattr(resp, "text", "") or "").strip()
                        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
                        data = json.loads(raw)
                        items = data.get("translations") if isinstance(data, dict) else data
                        if isinstance(items, list) and len(items) == len(idxs):
                            model_good("gemini-refine", model)
                            return idxs, [clean_translation(x) for x in items]
                        model_cool(model, "ចំនួនបន្ទាត់មិនត្រូវគ្នា")
                    except Exception as e:
                        model_cool(model, str(e))
            except Exception as _swallow_e:
                _log_swallowed(_swallow_e)
        if groq_key:
            try:
                res = groq_translate_chunk(groq_key, rows, None, system=REFINE_SYSTEM + _trans_style_extra() + " " + story, rotate=shift)
                return idxs, res
            except Exception as _swallow_e:
                _log_swallowed(_swallow_e)
        return idxs, None

    done = 0
    with ThreadPoolExecutor(max_workers=5) as pool:
        for idxs, res in pool.map(work, groups):
            if res:
                for i, r in zip(idxs, res):
                    if r and has_khmer(str(r)) and khmer_dominant(str(r)):
                        result[i] = r
            done += len(idxs)
            if progress:
                try:
                    progress(f"កំពុងកែសម្រួលអត្ថន័យខ្មែរ {done}/{n} ឃ្លា...")
                except Exception as _swallow_e:
                    _log_swallowed(_swallow_e)
    return result


JUDGE_SYSTEM = (
    "You are the final Khmer (Cambodian) dubbing judge. For each candidate first back-translate it into English in your head and compare it with the ORIGINAL; a candidate that changes, adds or drops any meaning, negation, number, name or emotion loses. Each item has the ORIGINAL line, sometimes an ENGLISH meaning, and two Khmer candidates A and B. "
    "Decide which candidate is MORE FAITHFUL to the original (every fact, name, number, negation, who-does-what-to-whom, tone) AND sounds like natural everyday spoken Khmer. "
    "Then output the best final Khmer line: you may pick A, pick B, or fix/merge them if both have a flaw. Never add information that is not in the original, never drop a negation or a number. "
    "Use neighbouring lines for context (speakers, pronouns, politeness) and keep pronouns consistent. Do not make it longer than needed. "
    "One complete sentence per item, Khmer script only, end with ។ (or ? !), no commas, brackets, quotes, dashes, ellipses, emojis or symbols. "
    "Return JSON {\"translations\": [...]} with exactly one item per input, same order."
)


SPEAKER_NOTE = (
    " If an item has SPEAKER: male or SPEAKER: female, that is the TRUE gender of the speaker measured from the audio. "
    "The Khmer must fit it: male uses បាទ and ខ្ញុំបាទ (formal I); female uses ចាស and នាងខ្ញុំ (formal I); never use the other gender's polite words. "
    "Fix any line where the particles do not match the speaker. Never output the SPEAKER field."
)
REFINE_SYSTEM = REFINE_SYSTEM + SPEAKER_NOTE
JUDGE_SYSTEM = JUDGE_SYSTEM + SPEAKER_NOTE


def judge_khmer(texts, englishes, cand_a, cand_b, gemini_key, groq_key, progress=None, shift=2, speakers=None):
    """ប្រៀបធៀបឃ្លាបកពីរបែប ហើយជ្រើស/កែយកមួយល្អបំផុត (ត្រឹមត្រូវតាមអត្ថន័យដើម និងធម្មជាតិ)។"""
    n = len(cand_a)
    result = list(cand_a)
    groups = [list(range(k, min(k + LLM_GROUP, n))) for k in range(0, n, LLM_GROUP)]

    def work(idxs):
        rows = []
        for i in idxs:
            row = f"ORIGINAL: {str(texts[i]).strip()}"
            if englishes[i] and "[unclear]" not in englishes[i]:
                row += f" | ENGLISH: {englishes[i]}"
            if speakers and i < len(speakers) and speakers[i]:
                row += " | SPEAKER: " + ("male" if speakers[i] == "M" else "female")
            row += f" | A: {cand_a[i]} | B: {cand_b[i]}"
            rows.append(row)
        prev = [str(cand_a[j]) for j in range(max(0, idxs[0] - 3), idxs[0]) if cand_a[j]]
        nxt = [str(cand_a[j]) for j in range(idxs[-1] + 1, min(n, idxs[-1] + 3)) if cand_a[j]]
        ctx = ""
        if prev:
            ctx += "PREVIOUS LINES (context only): " + " / ".join(prev) + " "
        if nxt:
            ctx += "NEXT LINES (context only): " + " / ".join(nxt)
        _r = oai_try(rows, None, JUDGE_SYSTEM + " " + ctx)
        if _r is not None:
            return idxs, _r
        if gemini_key:
            try:
                res = gemini_lines(gemini_key, JUDGE_SYSTEM + " " + ctx, rows)
                if res:
                    return idxs, res
            except Exception as _swallow_e:
                _log_swallowed(_swallow_e)
        if groq_key:
            try:
                return idxs, groq_translate_chunk(groq_key, rows, None, system=JUDGE_SYSTEM + " " + ctx, rotate=shift)
            except Exception as _swallow_e:
                _log_swallowed(_swallow_e)
        return idxs, None

    done = 0
    with ThreadPoolExecutor(max_workers=5) as pool:
        for idxs, res in pool.map(work, groups):
            if res:
                for i, r in zip(idxs, res):
                    if r and has_khmer(str(r)) and khmer_dominant(str(r)):
                        result[i] = r
            done += len(idxs)
            if progress:
                try:
                    progress(f"កំពុងជ្រើសការបកប្រែល្អបំផុត {done}/{n} ឃ្លា...")
                except Exception as _swallow_e:
                    _log_swallowed(_swallow_e)
    return result


def make_synopsis(english, texts, gemini_key, groq_key):
    """បង្កើតបរិបទរឿង និងតារាងឈ្មោះខ្មែរក្នុងការហៅ AI តែមួយ។"""
    body = " ".join((english[i] or str(texts[i])) for i in range(len(texts)))[:9000]
    instruction = (
        "You are a careful Chinese/Asian drama continuity editor helping a Cambodian Khmer dubbing translator. "
        "The transcript is machine-generated and may contain recognition errors. Read the entire transcript and return a compact context note with exactly these parts: "
        "STORY: 2-4 short English sentences describing the plot, setting, mood, and who is speaking to whom; "
        "CHARACTERS: recurring names and clearly supported relationships only; "
        "GLOSSARY: recurring original names/terms mapped to ONE stable natural Khmer rendering, formatted original = Khmer. "
        "Transliterate personal names consistently by sound; translate kinship/title terms by relationship and meaning. "
        "Do not guess unclear relationships, invent plot details, or add jokes. Keep the whole note concise (under 180 words). "
        'Return JSON {"translations": ["STORY: ...\nCHARACTERS: ...\nGLOSSARY: ..."]} only.'
    )
    ask = instruction + "\n\nTRANSCRIPT:\n" + body
    try:
        result = oai_try([body], None, instruction, to_english=True)
        if result and result[0]:
            return str(result[0]).strip()[:1800]
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)
    # Keep Groq as a real fallback when the user has only a Groq key configured.
    if groq_key:
        try:
            result = groq_translate_chunk(groq_key, [body], None, system=instruction, to_english=True)
            if result and result[0]:
                return str(result[0]).strip()[:1800]
        except Exception as _swallow_e:
            _log_swallowed(_swallow_e)
    if gemini_key:
        try:
            client = make_gemini_client(gemini_key, types.HttpOptions(timeout=TRANSLATE_TIMEOUT_MS))
            models = model_order(get_available_models(client)[:4], "gemini-context")
            for model in models[:2]:
                try:
                    response = client.models.generate_content(
                        model=model, contents=ask,
                        config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json"),
                    )
                    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", (getattr(response, "text", "") or "").strip())
                    data = json.loads(raw)
                    items = data.get("translations") if isinstance(data, dict) else data
                    if isinstance(items, list) and items and items[0]:
                        model_good("gemini-context", model)
                        return str(items[0]).strip()[:1800]
                except Exception as e:
                    model_cool(model, str(e))
        except Exception as _swallow_e:
            _log_swallowed(_swallow_e)
    return ""


def make_glossary(english, texts, gemini_key, groq_key):
    """ស្រង់ឈ្មោះតួអង្គ/កន្លែង/ពាក្យពិសេស រួចកំណត់ពាក្យខ្មែរតែមួយ ដើម្បីបាច់ទាំងអស់បកដូចគ្នា។"""
    body = " ".join((str(texts[i]).strip() + " (" + (english[i] or "") + ")") for i in range(len(texts)))[:9000]
    sys_ = ("From this machine-transcribed video script, list ONLY recurring proper names (people, places, sects, titles, items, skills) and key terms. "
            "Fix obvious ASR spelling mistakes using the context. For each, give ONE fixed Khmer rendering: transliterate names by SOUND (never translate their meaning), "
            "and choose the single Khmer word for each title or kinship term. Format each entry as: original = Khmer. Max 25 entries, separated by ' ; '. "
            'If there are none, return an empty string. Return JSON {"translations": ["<glossary>"]}.')
    try:
        r = llm_lines([body], sys_, gemini_key, groq_key, khmer=False)
        if r and r[0]:
            return str(r[0]).strip()[:1200]
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)
    return ""


def gemini_lines(api_key, system, rows, temperature=0.15, khmer=True):
    """ផ្ញើបន្ទាត់ទៅ Gemini ហើយទទួលបញ្ជី JSON ត្រឡប់វិញ (ចំនួនស្មើគ្នា)។"""
    client = make_gemini_client(api_key, types.HttpOptions(timeout=TRANSLATE_TIMEOUT_MS))
    avail = get_available_models(client)
    avail = [m for m in avail if "pro" in m.lower()] + [m for m in avail if "pro" not in m.lower()]
    models = model_order(avail[:5], "gemini")
    prompt = system + "\n\nITEMS:\n" + "\n".join(f"{k + 1}. {r}" for k, r in enumerate(rows))
    last = None
    for model in models:
        try:
            resp = client.models.generate_content(
                model=model, contents=prompt,
                config=types.GenerateContentConfig(temperature=temperature, response_mime_type="application/json"),
            )
            raw = (getattr(resp, "text", "") or "").strip()
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
            data = json.loads(raw)
            items = data.get("translations") if isinstance(data, dict) else data
            if isinstance(items, list) and len(items) == len(rows):
                model_good("gemini", model)
                return [(clean_translation(x) if khmer else (str(x).strip() or None)) for x in items]
            last = f"{model}: ចំនួនបន្ទាត់មិនត្រូវគ្នា"
            model_cool(model, last)
        except Exception as e:
            last = f"{model}: {e}"
            model_cool(model, last)
    raise RuntimeError(str(last)[:300])


def llm_lines(rows, system, gemini_key=None, groq_key=None, khmer=True):
    """សាក Gemini មុន បើមិនបានសាក Groq (ឬបញ្ច្រាស់ពេលមានតែមួយ)។ ត្រឡប់ None បើទាំងពីរបរាជ័យ។"""
    _r = oai_try(rows, None, system, to_english=(not khmer))
    if _r is not None:
        return _r
    if gemini_key:
        try:
            return gemini_lines(gemini_key, system, rows, khmer=khmer)
        except Exception as _swallow_e:
            _log_swallowed(_swallow_e)
    if groq_key:
        try:
            return groq_translate_chunk(groq_key, rows, None, system=system, to_english=(not khmer), rotate=True)
        except Exception as _swallow_e:
            _log_swallowed(_swallow_e)
    return None


FIT_SYSTEM = (
    "You are a Khmer dubbing editor doing lip-sync timing. Each numbered item has an ORIGINAL line, the current KHMER line and a MAX number "
    "of characters (the time the speaker's mouth is moving). Rewrite the KHMER line so it is at most MAX characters and still sounds like natural "
    "everyday spoken Khmer: use shorter common words, drop filler words, repeated words and pronouns a native would omit. "
    "Keep every fact, name, number, negation and the emotion. Do not add anything new. If the KHMER line already fits, return it unchanged. "
    "Khmer script only, one sentence per item ending with ។ (or ? !), no commas, brackets, quotes, dashes, ellipses or symbols. "
    "Return JSON {\"translations\": [...]} with exactly one item per input, same order."
)


EXPAND_SYSTEM = (
    "You are a Khmer dubbing editor doing lip-sync timing. Each numbered item has an ORIGINAL line, the current KHMER line and a TARGET number "
    "of characters (the time the speaker's mouth is moving). The KHMER line is too short, so the voice would end long before the mouth stops. "
    "Rewrite it to about TARGET characters (not more than 120% of TARGET) with fuller natural spoken Khmer: use complete everyday phrasing, "
    "natural connecting words and polite particles. Keep exactly the same meaning; never add new facts, names or numbers. "
    "Khmer script only, one sentence per item ending with ។ (or ? !), no commas, brackets, quotes, dashes, ellipses or symbols. "
    "Return JSON {\"translations\": [...]} with exactly one item per input, same order."
)


def fit_to_budget(texts, outs, budgets, gemini_key, groq_key, progress=None):
    """បង្រួមឃ្លាខ្មែរដែលវែងជាងពេលមាត់និយាយ ដោយរក្សាអត្ថន័យ (ឱ្យសំឡេងចប់ត្រូវមាត់)។"""
    n = len(outs)
    result = list(outs)
    over = [i for i in range(n)
            if budgets[i] and len(str(outs[i])) > budgets[i] * 1.15 and len(str(outs[i])) > 14]
    short = [i for i in range(n)
             if EXPAND_MODE and budgets[i] and budgets[i] >= 28 and 0 < len(str(outs[i])) < budgets[i] * 0.55]
    if short:
        def _exp(idxs):
            rows = [f"ORIGINAL: {str(texts[i]).strip()} | KHMER: {outs[i]} | TARGET: {budgets[i]}" for i in idxs]
            try:
                return idxs, llm_lines(rows, EXPAND_SYSTEM, gemini_key, groq_key)
            except Exception:
                return idxs, None
        try:
            egroups = [short[k:k + LLM_GROUP] for k in range(0, len(short), LLM_GROUP)]
            with ThreadPoolExecutor(max_workers=10) as _ep:
                for idxs, res in _ep.map(_exp, egroups):
                    if res:
                        for i, r in zip(idxs, res):
                            r = str(r or "")
                            if (has_khmer(r) and khmer_dominant(r) and len(r) > len(str(outs[i]))
                                    and len(r) <= budgets[i] * 1.4):
                                result[i] = r
        except Exception as _swallow_e:
            _log_swallowed(_swallow_e)
    if not over:
        return result
    groups = [over[k:k + LLM_GROUP] for k in range(0, len(over), LLM_GROUP)]

    def work(idxs):
        rows = [f"ORIGINAL: {str(texts[i]).strip()} | KHMER: {outs[i]} | MAX: {budgets[i]}" for i in idxs]
        return idxs, llm_lines(rows, FIT_SYSTEM, gemini_key, groq_key)

    done = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for idxs, res in pool.map(work, groups):
            if res:
                for i, r in zip(idxs, res):
                    if (r and has_khmer(str(r)) and khmer_dominant(str(r))
                            and len(r) < len(str(outs[i])) and len(r) >= 0.4 * len(str(outs[i]))):
                        result[i] = r
            done += len(idxs)
            if progress:
                try:
                    progress(f"កំពុងតម្រឹមប្រវែងឃ្លាឱ្យត្រូវមាត់ {done}/{len(over)} ឃ្លា...")
                except Exception as _swallow_e:
                    _log_swallowed(_swallow_e)
    return result


try:
    TRANS_BATCH = max(8, min(16, int(get_secret("TRANS_BATCH", "12") or 12)))
except Exception:
    TRANS_BATCH = 12
LLM_GROUP = 12   # ចំនួនឃ្លាក្នុងមួយការហៅ AI ពេលកែ/ជ្រើស/តម្រឹម (ធំជាង = ហៅតិចជាង = លឿនជាង)
# REVIEW_MODE: off = បកម្តងគត់ | refine = បក+ពិនិត្យកែ ១ជុំ (លំនាំដើម) | full = បក+កែ+ជ្រើស ២ជុំ
REVIEW_MODE = str(get_secret("REVIEW_MODE", "refine")).strip().lower()   # លំនាំដើមពិនិត្យកែ ១ជុំ; ដាក់ "full" ដើម្បីពិនិត្យ ២ជុំ (យឺតជាង)
# CLAUDE_FIRST=1 (លំនាំដើម): Claude ជាម៉ាស៊ីនបកប្រែសំខាន់ | 0 = ប្រើ Provider ផ្សេងមុន
CLAUDE_FIRST = str(get_secret("CLAUDE_FIRST", "1")).strip().lower() in ("1", "true", "yes", "on")
# FIT_MODE=1 (លំនាំដើម): បង្រួមឃ្លាវែងដោយ AI ដើម្បីសមពេលនិយាយ
FIT_MODE = str(get_secret("FIT_MODE", "1")).strip().lower() in ("1", "true", "yes", "on")
# EXPAND_MODE=1: ពង្រីកឃ្លាខ្លីឱ្យវែង (អាចបន្ថែមពាក្យមិនមាននៅដើម) — លំនាំដើមបិទ ដើម្បីរក្សាភាពត្រឹមត្រូវ
EXPAND_MODE = str(get_secret("EXPAND_MODE", "0")).strip().lower() in ("1", "true", "yes", "on")
# 1 = បកពីភាសាដើមទៅខ្មែរដោយផ្ទាល់; 0 = បកអង់គ្លេសជាមុន (យឺតជាង ប៉ុន្តែអាចប្រើជាជម្រើសសាកល្បង)។
FAST_TRANSLATE = str(get_secret("FAST_TRANSLATE", "1")).strip().lower() not in ("0", "false", "no", "off")


def translate_texts(texts, groq_key=None, budgets=None, gemini_key=None, progress=None, speakers=None, fit=True):
    n = len(texts)
    errors = []
    outs = [None] * n
    english = [None] * n
    # បកជាបាច់តូច ដើម្បីកុំឱ្យ AI ខកឃ្លា ឬច្រឡំលំដាប់
    batches = [list(range(k, min(k + TRANS_BATCH, n))) for k in range(0, n, TRANS_BATCH)]
    def _say(msg):
        if progress:
            try:
                progress(msg)
            except Exception as _swallow_e:
                _log_swallowed(_swallow_e)

    # ជំហាន ១: បកទៅអង់គ្លេសជាមុន (ធ្វើស្របគ្នា ៣ បាច់ក្នុងពេលតែមួយ)
    if (groq_key or oai_enabled()) and not FAST_TRANSLATE:
        def _en(idxs):
            rows_ = [str(texts[i]).strip() for i in idxs]
            try:
                return idxs, groq_translate_chunk(groq_key, rows_, None, system=EN_SYSTEM, to_english=True), None
            except Exception as e:
                # Groq ពេញកូតា/មានបញ្ហា → Gemini ជួយបម្រុង
                if gemini_key:
                    res_ = llm_lines(rows_, EN_SYSTEM, gemini_key, None, khmer=False)
                    if res_:
                        return idxs, res_, None
                return idxs, None, e
        done = 0
        with ThreadPoolExecutor(max_workers=5) as pool:
            for idxs, res, err in pool.map(_en, batches):
                if err:
                    errors.append(f"groq-en: {err}"[:200])
                else:
                    for i, r in zip(idxs, res):
                        english[i] = r
                done += len(idxs)
                _say(f"កំពុងស្ដាប់អត្ថន័យ {done}/{n} ឃ្លា...")
    synopsis = ""
    if n > 2 and str(get_secret("SYNOPSIS", "1")).strip().lower() in ("1", "true", "yes", "on"):
        if groq_key or oai_enabled():
            synopsis = make_synopsis(english, texts, None, groq_key)
        if not synopsis and gemini_key:
            synopsis = make_synopsis(english, texts, gemini_key, None)
    # ឈ្មោះ និងពាក្យសំខាន់ៗត្រូវបានបញ្ចូលជាមួយសេចក្តីសង្ខេបក្នុងការហៅ AI តែមួយ ដើម្បីកាត់បន្ថយការរង់ចាំ។
    # ជំហាន ២: Gemini បកជាខ្មែរមុន (ល្អបំផុតសម្រាប់ខ្មែរ) ដោយមានបរិបទមុន/ក្រោយ
    missing = [i for i, o in enumerate(outs) if o is None]
    batches = [missing[k:k + TRANS_BATCH] for k in range(0, len(missing), TRANS_BATCH)]
    if (gemini_key or oai_enabled()) and missing:
        def _km(idxs):
            try:
                prev_ctx = [english[j] or str(texts[j]) for j in range(max(0, idxs[0] - 8), idxs[0])]
                story = " / ".join(str(x).strip() for x in prev_ctx if x)[-1600:] or None
                if synopsis:
                    story = "VIDEO SUMMARY: " + synopsis + " || " + (story or "")
                nxt_ctx = [english[j] or str(texts[j]) for j in range(idxs[-1] + 1, min(n, idxs[-1] + 9))]
                if nxt_ctx:
                    story = (story or "") + " || NEXT LINES (context only): " + " / ".join(str(x).strip() for x in nxt_ctx if x)[:1200]
                return idxs, gemini_translate_khmer(
                    gemini_key, [str(texts[i]).strip() for i in idxs],
                    [english[i] for i in idxs], [budgets[i] for i in idxs] if budgets else None,
                    story=story, groq_key=groq_key,
                    speakers=[speakers[i] for i in idxs] if speakers else None,
                ), None
            except Exception as e:
                return idxs, None, e
        done = 0
        with ThreadPoolExecutor(max_workers=6) as pool:
            for idxs, res, err in pool.map(_km, batches):
                if err:
                    errors.append(f"CodeCraft: {err}"[:200])
                else:
                    for i, r in zip(idxs, res):
                        outs[i] = r
                done += len(idxs)
                _say(f"កំពុងបកជាខ្មែរ {done}/{n} ឃ្លា...")
    cc_ok = {i for i, o in enumerate(outs) if o is not None}
    # ជំហាន ២ខ: Groq ជាបម្រុង ប្រសិនបើ CodeCraft មិនបាន
    missing = [i for i, o in enumerate(outs) if o is None]
    if missing and groq_key:
        _say(f"កំពុងបកជាខ្មែរតាមសាច់រឿង (Groq ជាបម្រុង) 0/{len(missing)} ឃ្លា...")
        groups = [missing[k:k + TRANS_BATCH] for k in range(0, len(missing), TRANS_BATCH)]
        def _gkm(idxs):
            try:
                prev = [english[j] or str(texts[j]) for j in range(max(0, idxs[0] - 15), idxs[0])]
                story = " / ".join(str(x).strip() for x in prev if x)
                if synopsis:
                    story = "VIDEO SUMMARY: " + synopsis + " || " + story
                lines_ = []
                for i in idxs:
                    row = spk_tag(speakers[i] if speakers else None) + str(texts[i]).strip()
                    if english[i] and "[unclear]" not in english[i]:
                        row += f" (English meaning: {english[i]})"
                    lines_.append(row)
                sys_ = (
                    _trans_sys()
                    + " Some lines include an English meaning in parentheses to help you understand; translate the true meaning "
                    "into Khmer and never output the English text or any tags."
                    + ((" STORY SO FAR (context only, do NOT translate): " + story) if story else "")
                )
                bud_ = [budgets[i] for i in idxs] if budgets else None
                return idxs, groq_translate_chunk(groq_key, lines_, bud_, system=sys_), None
            except Exception as e:
                return idxs, None, e
        done_ = 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            for idxs, res, err in pool.map(_gkm, groups):
                if err:
                    errors.append(f"groq-km-ctx: {err}"[:200])
                else:
                    for i, r in zip(idxs, res):
                        if r and has_khmer(str(r)):
                            outs[i] = r
                done_ += len(idxs)
                _say(f"កំពុងបកជាខ្មែរតាមសាច់រឿង (Groq ជាបម្រុង) {done_}/{len(missing)} ឃ្លា...")
    # បម្រុង: Google Translate លើអត្ថបទអង់គ្លេស (ត្រឹមត្រូវជាងបកពីចិន/ថៃ/វៀតណាមផ្ទាល់)
    missing = [i for i, o in enumerate(outs) if o is None]
    if missing:
        src = [english[i] or str(texts[i]) for i in missing]
        g_outs, g_errs = _translate_texts_old(src, None)
        errors += g_errs
        for i, o in zip(missing, g_outs):
            outs[i] = o
    # ជំហាន ៣: សាកបកប្រែឡើងវិញសម្រាប់ឃ្លាដែលលទ្ធផលទទេ/មិនមានអក្សរខ្មែរ
    missing = [i for i, o in enumerate(outs) if not o or not has_khmer(str(o))]
    if missing and (gemini_key or oai_enabled()):
        for k in range(0, len(missing), 8):
            idxs = missing[k:k + 8]
            try:
                res = gemini_translate_khmer(
                    gemini_key, [str(texts[i]).strip() for i in idxs],
                    [english[i] for i in idxs],
                    [budgets[i] for i in idxs] if budgets else None,
                    groq_key=groq_key,
                    speakers=[speakers[i] for i in idxs] if speakers else None,
                )
                for i, r in zip(idxs, res):
                    if r and has_khmer(str(r)):
                        outs[i] = r
            except Exception as e:
                errors.append(f"gemini-retry: {e}"[:200])
    # ជំហាន ៤: បម្រុងចុងក្រោយ បកផ្ទាល់ទៅខ្មែរ ដោយ Groq
    missing = [i for i, o in enumerate(outs) if not o or not has_khmer(str(o))]
    if missing and groq_key:
        for k in range(0, len(missing), 8):
            idxs = missing[k:k + 8]
            try:
                res = groq_translate_chunk(
                    groq_key, [spk_tag(speakers[i] if speakers else None) + str(texts[i]).strip() for i in idxs],
                    [budgets[i] for i in idxs] if budgets else None,
                )
                for i, r in zip(idxs, res):
                    if r and has_khmer(str(r)):
                        outs[i] = r
            except Exception as e:
                errors.append(f"groq-km-retry: {e}"[:200])
            time.sleep(0.5)
    # ជំហានចុងក្រោយ: បកម្តងមួយឃ្លាៗ (មិនអាចខុសចំនួនបន្ទាត់) ជាមួយ Gemini/Groq រួចទើប Google
    missing = [i for i, o in enumerate(outs) if not o or not has_khmer(str(o))]
    if missing:
        _say(f"កំពុងបកឃ្លាដែលនៅខ្វះ {len(missing)} ឃ្លា...")
        # ធ្វើស្របគ្នា + ឈប់សាកម៉ាស៊ីនដែលខូចជាប់ៗគ្នា + កំណត់ពេលអតិបរមា ដើម្បីកុំឱ្យរង់ចាំយូរដូចគាំង
        dead = {"gemini": 0, "groq": 0, "google": 0}
        t_end = time.time() + 40
        lock = threading.Lock()

        def _fail(name, msg):
            with lock:
                dead[name] += 1
                errors.append(msg[:200])

        def _one_line(i):
            if time.time() > t_end:
                return i, None
            one = [str(texts[i]).strip()]
            bud = [budgets[i]] if budgets else None
            spk_ = [speakers[i]] if speakers else None
            r = None
            if (gemini_key or oai_enabled()) and dead["gemini"] < 2:
                try:
                    r = gemini_translate_khmer(gemini_key, one, [english[i]], bud, groq_key=groq_key, speakers=spk_)[0]
                    dead["gemini"] = 0
                except Exception as e:
                    _fail("gemini", f"gemini-1: {e}")
            if (not r or not has_khmer(str(r))) and groq_key and dead["groq"] < 2 and time.time() < t_end:
                try:
                    r = groq_translate_chunk(groq_key, [spk_tag(spk_[0] if spk_ else None) + one[0]], bud)[0]
                    dead["groq"] = 0
                except Exception as e:
                    _fail("groq", f"groq-1: {e}")
            if (not r or not has_khmer(str(r))) and dead["google"] < 2 and time.time() < t_end:
                try:
                    r = clean_translation(google_translate_request(english[i] or one[0], retries=1))
                    dead["google"] = 0
                except Exception as e:
                    _fail("google", f"google-1: {e}")
            return i, r

        with ThreadPoolExecutor(max_workers=4) as pool:
            for i, r in pool.map(_one_line, missing):
                if r and has_khmer(str(r)):
                    outs[i] = r
    # ជំហានកែសម្រួលចុងក្រោយ: ពិនិត្យអត្ថន័យខ្មែរប្រៀបនឹងអត្ថបទដើម
    # ពិនិត្យ ២ ជុំ ដោយម៉ូដែលផ្សេងគ្នា លើគ្រប់ឃ្លា (ជុំទី២ ពិនិត្យអត្ថន័យ និងភាពស៊ីសង្វាក់ម្តងទៀត)
    allidx = list(range(n))
    only_groq = not (gemini_key or oai_enabled())
    _quota_ok = time.time() - _GROQ_LIMIT["t"] > 900   # មិនជួប 429 ក្នុង ១៥ នាទីចុងក្រោយ
    if REVIEW_MODE in ("refine", "full") and allidx and (groq_key or gemini_key or oai_enabled()) and (not only_groq or _quota_ok) and all(o and has_khmer(str(o)) for o in outs):
        try:
            cand_a = list(outs)
            cand_b = refine_khmer([texts[i] for i in allidx], [english[i] for i in allidx], cand_a,
                                  gemini_key, groq_key, progress=progress, shift=1, speakers=speakers)
            cand_b = [b or a for a, b in zip(cand_a, cand_b)]
            if REVIEW_MODE == "full":
                outs = judge_khmer([texts[i] for i in allidx], [english[i] for i in allidx], cand_a, cand_b,
                                   gemini_key, groq_key, progress=progress, shift=2, speakers=speakers)
            else:
                outs = cand_b
        except Exception as e:
            errors.append(f"refine/judge: {e}"[:200])
    # តម្រឹមប្រវែងឃ្លាខ្មែរឱ្យសមនឹងពេលមាត់តួអង្គនិយាយ (lip-sync)
    if fit and FIT_MODE and budgets and all(o and has_khmer(str(o)) for o in outs):
        try:
            outs = fit_to_budget(texts, outs, budgets, gemini_key, groq_key, progress=progress)
        except Exception as e:
            errors.append(f"fit: {e}"[:200])
    # កុំទុកលទ្ធផលទទេ ឬអង់គ្លេសសុទ្ធឱ្យបន្តជាសំឡេង dubbing
    for i, o in enumerate(outs):
        if not o or not has_khmer(str(o)):
            outs[i] = None
    outs = _apply_tails(outs, budgets)
    return outs, errors


def _translate_texts_prev(texts, groq_key=None, budgets=None):
    errors = []
    outs = [None] * len(texts)
    if groq_key:
        for k in range(0, len(texts), 12):
            idxs = list(range(k, min(k + 12, len(texts))))
            try:
                res = groq_translate_chunk(
                    groq_key, [str(texts[i]).strip() for i in idxs],
                    [budgets[i] for i in idxs] if budgets else None,
                )
                for i, r in zip(idxs, res):
                    outs[i] = r
            except Exception as e:
                errors.append(f"groq-llm: {e}"[:200])
            time.sleep(0.4)
    missing = [i for i, o in enumerate(outs) if o is None]
    if missing:
        g_outs, g_errs = _translate_texts_old([texts[i] for i in missing], None)
        errors += g_errs
        for i, o in zip(missing, g_outs):
            outs[i] = o
    return outs, errors


def _translate_texts_old(texts, groq_key=None):
    errors = []
    outs = [None] * len(texts)
    google_blocked = False
    batches, cur, size = [], [], 0
    for i, t in enumerate(texts):
        flat = str(t).replace("\n", " ").strip()
        if cur and size + len(flat) > 1200:
            batches.append(cur)
            cur, size = [], 0
        cur.append((i, flat))
        size += len(flat) + 1
    if cur:
        batches.append(cur)
    fails = 0
    for batch in batches:
        if fails >= 2:
            break
        try:
            raw = google_translate_request("\n".join(t for _, t in batch))
            lines = (raw or "").strip("\n").split("\n")
            if len(lines) == len(batch):
                for (i, _), line in zip(batch, lines):
                    outs[i] = clean_translation(line)
            else:
                # line count differs: translate each line on its own
                for i, flat in batch:
                    try:
                        outs[i] = clean_translation(google_translate_request(flat))
                    except Exception as _swallow_e:
                        _log_swallowed(_swallow_e)
                    time.sleep(0.4)
            fails = 0
        except Exception as e:
            errors.append(f"google: {e}"[:200])
            fails += 1
            time.sleep(3)
        time.sleep(0.5)
    missing = [i for i, o in enumerate(outs) if o is None]
    if missing and groq_key:
        for k in range(0, len(missing), 20):
            idxs = missing[k:k + 20]
            try:
                res = groq_translate_chunk(groq_key, [str(texts[i]).strip() for i in idxs])
                for i, r in zip(idxs, res):
                    outs[i] = r
            except Exception as e:
                errors.append(f"groq-llm: {e}"[:200])
            time.sleep(1)
    return outs, errors


def retime_by_speech(segs, speech, duration, pad=0.6):
    if not speech or duration <= 0:
        return segs
    total_all = sum(b - a for a, b in speech)
    if total_all / duration >= 0.9 or total_all < 1.0:
        return segs
    out = []
    for s, e, text in segs:
        pieces = split_display(text)
        if not pieces:
            continue
        lo, hi = max(0.0, s - pad), min(duration, e + pad)
        win = []
        for a, b in speech:
            a2, b2 = max(a, lo), min(b, hi)
            if b2 - a2 >= 0.1:
                win.append((a2, b2))
        win_total = sum(b - a for a, b in win)
        if win_total < 0.5:
            win = [(s, max(e, s + 0.4))]
            win_total = win[0][1] - win[0][0]
        def to_real(x, is_end):
            acc = 0.0
            for a, b in win:
                d = b - a
                if (x <= acc + d) if is_end else (x < acc + d):
                    return a + max(0.0, x - acc)
                acc += d
            return win[-1][1]
        weights = [max(1, len(p)) for p in pieces]
        total_w = float(sum(weights))
        cum = 0
        for piece, w in zip(pieces, weights):
            x0 = win_total * cum / total_w
            cum += w
            x1 = win_total * cum / total_w
            ps, pe = to_real(x0, False), to_real(x1, True)
            out.append((ps, max(pe, ps + 0.3), piece))
    out.sort(key=lambda x: x[0])
    return out or segs


def plan_short_chunks(duration, speech, target=10.0, limit=14.0):
    cuts = []
    for (a1, b1), (a2, b2) in zip(speech or [], (speech or [])[1:]):
        if a2 - b1 >= 0.15:
            cuts.append((b1 + a2) / 2.0)
    chunks = []
    start = 0.0
    while duration - start > limit:
        want = start + target
        cands = [c for c in cuts if start + 4.0 <= c <= start + limit]
        cut = min(cands, key=lambda c: abs(c - want)) if cands else want
        chunks.append((start, cut))
        start = cut
    chunks.append((start, duration))
    return chunks


def transcribe_khmer_chunks(groq_key, audio_path, duration, speech, status):
    folder = os.path.dirname(audio_path)
    base = os.path.basename(audio_path)
    chunks = plan_short_chunks(duration, speech)
    out = []
    for i, (a, b) in enumerate(chunks):
        if b - a < 0.5:
            continue
        t0 = time.time()
        name = f"kchunk_{i}.mp3"
        try:
            run_ffmpeg(["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", base, "-c:a", "libmp3lame", "-b:a", "64k", name], cwd=folder)
            data, _ = groq_transcribe(groq_key, os.path.join(folder, name), "km", status)
            texts = []
            for sg in data.get("segments") or []:
                text = fix_khmer(sg.get("text", ""))
                if not text or not has_khmer(text):
                    continue
                if (float(sg.get("no_speech_prob", 0) or 0) > 0.6 and float(sg.get("avg_logprob", 0) or 0) < -0.8):
                    continue
                texts.append(text)
            text = fix_khmer(" ".join(texts))
            if text:
                out.extend(retime_by_speech([(a, b, text)], speech, duration, pad=0.0))
        except Exception as _swallow_e:
            _log_swallowed(_swallow_e)
        status.write(f"៣/៤ កំពុងស្តាប់ភាសាខ្មែរ... ({i + 1}/{len(chunks)})")
        wait = 3.2 - (time.time() - t0)
        if wait > 0:
            time.sleep(wait)
    out.sort(key=lambda x: x[0])
    return out


GSPEECH_KEY = get_secret("GSPEECH_KEY", "")


def google_speech_request(flac_bytes, lang="km-KH"):
    query = urllib.parse.urlencode({"client": "chromium", "lang": lang, "key": GSPEECH_KEY, "pFilter": "0"})
    request = urllib.request.Request(
        "https://www.google.com/speech-api/v2/recognize?" + query,
        data=flac_bytes, method="POST",
        headers={"Content-Type": "audio/x-flac; rate=16000", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        body = response.read().decode("utf-8", "ignore")
    for line in body.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        results = obj.get("result") or []
        if results:
            alts = results[0].get("alternative") or []
            if alts:
                return fix_khmer(alts[0].get("transcript", ""))
    return ""


def transcribe_khmer_google(audio_path, duration, speech, status):
    folder = os.path.dirname(audio_path)
    base = os.path.basename(audio_path)
    chunks = plan_short_chunks(duration, speech)
    todo = [(i, a, b) for i, (a, b) in enumerate(chunks) if b - a >= 0.5]
    counter = {"n": 0}

    def one(item):
        i, a, b = item
        name = f"gs_{i}.flac"
        try:
            run_ffmpeg(["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", base, "-ac", "1", "-ar", "16000", "-c:a", "flac", name], cwd=folder)
            with open(os.path.join(folder, name), "rb") as f:
                data = f.read()
            text = ""
            for attempt in range(2):
                try:
                    text = google_speech_request(data)
                    break
                except urllib.error.HTTPError as e:
                    if e.code in (429, 503) and attempt == 0:
                        time.sleep(3)
                        continue
                    raise
            res = retime_by_speech([(a, b, text)], speech, duration, pad=0.0) if text else []
            return res, None
        except Exception as ex_:
            return [], ex_
        finally:
            counter["n"] += 1
            status.write(f"៣/៤ កំពុងស្តាប់ភាសាខ្មែរ... ({counter['n']}/{len(todo)})")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(one, todo))
    out = []
    got = 0
    errs = 0
    for res, err in results:
        if err is not None:
            errs += 1
        if res:
            got += 1
            out.extend(res)
    if got == 0:
        if errs >= 3:
            raise RuntimeError("Google Speech បរាជ័យ")
        return []
    out.sort(key=lambda x: x[0])
    return out


KHMER_CPS = 14.0   # តួអក្សរខ្មែរដែលសំឡេង AI អានបានក្នុង ១ វិនាទី (ប្រហែល)


def lip_budgets(segs):
    """ប្រវែងអក្សរខ្មែរអតិបរមា តាមពេលដែលតួអង្គបើកមាត់និយាយ (ដើម្បីឱ្យសំឡេងចប់ត្រូវមាត់)។"""
    out = []
    for s_, e_, _t in segs:
        dur = max(0.0, float(e_) - float(s_))
        out.append(max(10, int(dur * KHMER_CPS)))
    return out


def merge_for_translate(segs, max_chars=180, max_gap=1.2, max_len=9.0, gender_fn=None):
    """បញ្ចូលបំណែក Whisper ដែលដាច់កណ្តាលប្រយោគ ឱ្យទៅជាប្រយោគពេញ មុនបកប្រែ
    (បកទាំងប្រយោគ ត្រឹមត្រូវជាងបកបំណែកខ្លីៗ)។"""
    strong_end = ".!?។…。！？"
    out = []
    for s, e, t in segs:
        t = str(t).strip()
        if not t:
            continue
        if out:
            ps, pe, pt = out[-1]
            last = pt.rstrip()[-1:]
            ended = last in strong_end
            tiny_prev = len(pt.strip()) < 24           # បំណែកខ្លីពេក មិនអាចបកឱ្យត្រូវ
            tiny_cur = len(t) < 12
            starts_lower = t[:1].islower()              # ចាប់ផ្តើមអក្សរតូច = បន្តប្រយោគមុន
            cont = (not ended) or tiny_prev or tiny_cur or starts_lower
            if _spk_differs(gender_fn, ps, pe, s, e):
                cont = False   # អ្នកនិយាយប្តូរភេទ → មិនបញ្ចូលគ្នា (ឃ្លានីមួយៗមានសំឡេងតែមួយ)
            gap_ok = (s - pe) <= (max_gap if not ended else 0.5)
            if cont and gap_ok and len(pt) + len(t) + 1 <= max_chars and e - ps <= max_len:
                out[-1] = (ps, max(pe, e), (pt + " " + t).strip())
                continue
        out.append((s, e, t))
    return out


def transcribe_free(groq_key, audio_path, duration, source_language, status, speech=None, khmer_ok=True, dub=False, gemini_key=None, keep_failed=False, gender_fn=None):
    code = WHISPER_LANG.get(source_language) if source_language else None
    if source_language == "Khmer" and khmer_ok:
        try:
            gs = transcribe_khmer_google(audio_path, duration, speech or [], status)
        except Exception:
            gs = []
        if gs:
            return gs, "Google Speech (km-KH)", 0
    data, model = groq_transcribe(groq_key, audio_path, code, status)
    detected = str(data.get("language", "") or "").lower()
    keep = []
    _words = [w_ for w_ in (data.get("words") or []) if isinstance(w_, dict)]
    for sg in data.get("segments") or []:
        text = str(sg.get("text", "")).strip()
        if not text:
            continue
        if (float(sg.get("no_speech_prob", 0) or 0) > 0.6 and float(sg.get("avg_logprob", 0) or 0) < -0.8):
            continue
        if float(sg.get("compression_ratio", 0) or 0) > 2.4:
            continue
        try:
            s = float(sg.get("start", 0))
            e = float(sg.get("end", 0))
        except Exception:
            continue
        # Word-level refinement: start at the first spoken word and end at the last one
        # (Whisper segment boundaries alone are often off by 0.3-1.5 s).
        if _words:
            try:
                _in = [w_ for w_ in _words
                       if float(w_.get("end", 0)) > s - 0.05 and float(w_.get("start", 0)) < e + 0.05]
                if _in:
                    s = float(_in[0].get("start", s))
                    e = float(_in[-1].get("end", e))
            except Exception as _w_err:
                _log_swallowed(_w_err)
        s = min(max(0.0, s), duration)
        e = min(max(e, s + 0.4), duration + 0.5)
        if keep and keep[-1][2].strip().lower() == text.strip().lower():
            keep[-1] = (keep[-1][0], max(keep[-1][1], e), keep[-1][2])
            continue
        keep.append((s, e, text))
    if not keep:
        raise UserError("រកមិនឃើញសំឡេងនិយាយក្នុងវីដេអូនេះទេ។")
    failed = 0
    is_khmer = detected in ("khmer", "km") or source_language == "Khmer"
    if is_khmer:
        segs = []
        if source_language != "Khmer":
            try:
                segs = transcribe_khmer_google(audio_path, duration, speech or [], status)
            except Exception:
                segs = []
            if segs:
                return segs, "Google Speech (km-KH)", 0
        if not segs and duration > 12:
            try:
                segs = transcribe_khmer_chunks(groq_key, audio_path, duration, speech or [], status)
            except Exception:
                segs = []
        if not segs:
            segs = [(s, e, fix_khmer(t)) for s, e, t in keep if has_khmer(t)]
            segs = retime_by_speech(segs, speech, duration)
    else:
        status.write("៣/៤ កំពុងបកប្រែជាភាសាខ្មែរ...")
        keep = merge_for_translate(keep, gender_fn=gender_fn)
        speakers = None
        if gender_fn is not None:
            try:
                speakers = [gender_fn(_s, _e) for _s, _e, _t in keep]
                if not any(speakers):
                    speakers = None
            except Exception:
                speakers = None
        # បកប្រែតាមប្រវែងឃ្លាចិន៖ ឃ្លាខ្លីអាចពន្យល់ខ្មែរបន្ថែម,
        # ឃ្លាវែងត្រូវសង្ខេបខ្មែរឱ្យខ្លី ដើម្បីសមនឹងចន្លោះសំឡេង។
        # ប្រវែងគោល (soft hint): ~១០ តួអក្សរខ្មែរ/វិនាទី តាមពេលមាត់និយាយ ឱ្យស្របចង្វាក់ lip-sync
        # (prompt ហាមកាត់អត្ថន័យ ដូច្នេះនេះគ្រាន់តែជាការណែនាំ)
        budgets = lip_budgets(keep) if dub else None  # ប្រវែងកំណត់ប្រើតែពេល dubbing; Caption ធម្មតាបកពេញន័យ មិនកាត់
        outs, errs = translate_texts([t for _, _, t in keep], groq_key, budgets, gemini_key, progress=lambda m: status.write("៣/៤ " + m), speakers=speakers, fit=bool(dub))
        segs = []
        for (s, e, orig), out in zip(keep, outs):
            if out:
                segs.append((s, e, out))
            elif keep_failed:
                # មានទំព័រកែអត្ថបទ: ទុកឃ្លាដើមដាក់ស្លាក ⚠️ ឱ្យអ្នកកែដោយដៃ
                segs.append((s, e, "⚠️ " + str(orig)))
                failed += 1
            else:
                failed += 1
        # កុំបង្កើតវីដេអូដែលមានឃ្លាបាត់សំឡេងបកប្រែស្ងាត់ៗ
        if not keep_failed and (failed > 0 or len(segs) != len(keep)):
            reason = " | ".join(errs[:3]) or "AI មិនបានផ្តល់អត្ថបទខ្មែរសម្រាប់ឃ្លាខ្លះ"
            raise RuntimeError(
                "ការបកប្រែមិនគ្រប់ឃ្លា ដូច្នេះបានបញ្ឈប់ដើម្បីកុំឱ្យវីដេអូបាត់អត្ថបទ។ "
                f"(ស្តាប់បាន {len(keep)} ឃ្លា បកបាន {len(segs)} ឃ្លា) មូលហេតុ: {reason}"
            )
    if not segs:
        raise UserError("រកមិនឃើញអត្ថបទខ្មែរក្នុងសំឡេងនេះទេ។")
    segs.sort(key=lambda x: x[0])
    return segs, f"Groq {model} + Translate", failed


def transcribe_gemini_text(gemini_key, groq_key, audio_path, duration, source_language, status, speech=None, keep_failed=False):
    """Gemini ទាញអត្ថបទដើមពីសំឡេងតែប៉ុណ្ណោះ (មិនបកប្រែ)។ ការបកជាខ្មែរធ្វើដោយ Groq/Google។"""
    if source_language == "Khmer":
        return transcribe(gemini_key, audio_path, duration, source_language, status, concise=False, speech=speech)
    raw, model, failed = transcribe(gemini_key, audio_path, duration, source_language, status, speech=speech, original_only=True)
    if khmer_ratio(raw) >= 0.6:
        return raw, f"Gemini {model}", failed
    status.write("៣/៤ Gemini ទាញអត្ថបទរួច កំពុងបកប្រែជាភាសាខ្មែរ...")
    keep = merge_for_translate([(a, b, t) for a, b, t in raw if str(t).strip()])
    outs, errs = translate_texts([t for _, _, t in keep], groq_key, lip_budgets(keep), gemini_key, progress=lambda m: status.write("៣/៤ " + m))
    segs = []
    for (a, b, orig), out in zip(keep, outs):
        if out:
            segs.append((a, b, out))
        elif keep_failed:
            segs.append((a, b, "⚠️ " + str(orig)))
            failed += 1
        else:
            failed += 1
    if not keep_failed and (failed > 0 or len(segs) != len(keep)):
        reason = " | ".join(errs[:3]) or "មិនបានអត្ថបទខ្មែរសម្រាប់ឃ្លាខ្លះ"
        raise RuntimeError(f"ការបកប្រែមិនគ្រប់ឃ្លា (ទាញបាន {len(keep)} បកបាន {len(segs)}) មូលហេតុ: {reason}")
    if not segs:
        raise UserError("រកមិនឃើញអត្ថបទខ្មែរក្នុងសំឡេងនេះទេ។")
    segs.sort(key=lambda x: x[0])
    return segs, f"Gemini {model} (ទាញអត្ថបទ) + Translate", failed


def tts_segment(text, voice, path, prosody=None):
    async def _go(p):
        # Keep every Khmer line at the normal TTS rate (1.0x): no forced slowing or speeding.
        # Emotion is still expressed through pitch and volume, not speech-rate changes.
        kw = {"rate": "+0%", "pitch": "+0Hz"}
        if p:
            kw = {"rate": "+0%", "volume": p.get("volume", "+0%"),
                  "pitch": p.get("pitch", "+0Hz")}
        await edge_tts.Communicate(tts_clean(text), voice, **kw).save(path)

    try:
        asyncio.run(_go(prosody))
    except Exception:
        if prosody:
            asyncio.run(_go(None))
        else:
            raise


def shorten_khmer(client, model, text, max_seconds):
    limit = max(6, int(max_seconds * 11))
    try:
        response = client.models.generate_content(
            model=model,
            contents=(
                f"Shorten this Khmer sentence to at most {limit} "
                "characters. Keep the meaning. Khmer script only. "
                f"Return only the sentence.\n{text}"
            ),
        )
        out = fix_khmer(getattr(response, "text", "") or "")
        return out if has_khmer(out) else text
    except Exception:
        return text


VOICE_MALE = "km-KH-PisethNeural"
VOICE_FEMALE = "km-KH-SreymomNeural"

BIN = 0.1
MIN_TURN = 2.0


def load_pcm(path):
    import numpy as np
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [exe, "-i", path, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    raw = result.stdout
    result = None
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    raw = None
    data /= 32768.0
    return data


def pitch_track(samples, sr=16000):
    import numpy as np
    n = int(0.04 * sr)
    hop = int(0.02 * sr)
    lag_min = int(sr / 400)
    lag_max = int(sr / 70)
    empty = np.array([])
    if len(samples) < n * 3:
        return empty, empty, empty
    count = 1 + (len(samples) - n) // hop
    times = (np.arange(count) * hop + n / 2) / sr
    f0 = np.zeros(count, dtype=np.float64)
    rms = np.zeros(count, dtype=np.float64)
    peaks = np.zeros(count, dtype=np.float64)
    lags = np.arange(n)
    overlap_fix = n / np.maximum(n - lags, 1)
    step = 1500
    for b0 in range(0, count, step):
        b1 = min(count, b0 + step)
        idx = (np.arange(b0, b1) * hop)[:, None] + np.arange(n)[None, :]
        frames = samples[idx].astype(np.float64)
        rms[b0:b1] = np.sqrt(np.mean(frames ** 2, axis=1))
        frames = frames - frames.mean(axis=1, keepdims=True)
        spec = np.fft.rfft(frames, 2 * n, axis=1)
        ac = np.fft.irfft(spec * np.conj(spec), axis=1)[:, :n]
        ac = ac / np.maximum(ac[:, :1], 1e-9)
        ac = ac * overlap_fix[None, :]
        seg = ac[:, lag_min - 1:lag_max + 2]
        core = seg[:, 1:-1]
        is_peak = (core >= seg[:, :-2]) & (core >= seg[:, 2:])
        pk = core.max(axis=1)
        cand = is_peak & (core >= 0.9 * pk[:, None])
        first = np.argmax(cand, axis=1)
        lag = lag_min + first
        f0[b0:b1] = sr / np.maximum(lag, 1)
        peaks[b0:b1] = core[np.arange(len(first)), first]
    thr = max(0.004, 0.12 * float(np.percentile(rms, 95)))
    voiced = (rms >= thr) & (peaks >= 0.45)
    f0 = np.where(voiced, f0, 0.0)
    return times, f0, rms


def median_pitch(info, a, b):
    import numpy as np
    t = info.get("times")
    f = info.get("f0")
    if t is None or len(t) == 0:
        return None
    m = (t >= a) & (t <= b) & (f > 0)
    if int(m.sum()) < 3:
        return None
    return float(np.median(f[m]))


def merge_short_runs(runs, min_len):
    runs = [list(r) for r in runs]
    while len(runs) > 1:
        idx = min(range(len(runs)), key=lambda k: runs[k][1] - runs[k][0])
        if runs[idx][1] - runs[idx][0] >= min_len:
            break
        left = runs[idx - 1] if idx > 0 else None
        right = runs[idx + 1] if idx < len(runs) - 1 else None
        if left is not None and right is not None:
            target = left if (left[1] - left[0]) >= (right[1] - right[0]) else right
        else:
            target = left if left is not None else right
        if target is left:
            left[1] = runs[idx][1]
        else:
            right[0] = runs[idx][0]
        runs.pop(idx)
        merged = [runs[0]]
        for r in runs[1:]:
            if r[2] == merged[-1][2]:
                merged[-1][1] = r[1]
            else:
                merged.append(r)
        runs = merged
    return runs


def gender_timeline(pcm, duration, default_voice, sr=16000, tracks=None):
    import numpy as np
    if tracks is not None:
        times, f0, rms = tracks
    else:
        times, f0, rms = pitch_track(pcm, sr)
    info = {"times": times, "f0": f0, "rms": rms, "summary": ""}
    mask = f0 > 0
    if int(mask.sum()) < 25:
        info["summary"] = "វាស់កម្រិតសំឡេងមិនបាន ប្រើសំឡេងដែលបានជ្រើស"
        return None, info
    tv = times[mask]
    hz = f0[mask]
    lg = np.log2(hz)
    c0 = float(np.percentile(lg, 20))
    c1 = float(np.percentile(lg, 80))
    for _ in range(30):
        hi = np.abs(lg - c1) < np.abs(lg - c0)
        if hi.all() or (~hi).all():
            break
        n0 = float(lg[~hi].mean())
        n1 = float(lg[hi].mean())
        done = abs(n0 - c0) < 1e-4 and abs(n1 - c1) < 1e-4
        c0, c1 = n0, n1
        if done:
            break
    hi = np.abs(lg - c1) < np.abs(lg - c0)
    n_hi = int(hi.sum())
    n_lo = int(len(lg) - n_hi)
    hz0, hz1 = float(2 ** c0), float(2 ** c1)
    two = False
    single = None
    g0 = g1 = None
    if n_hi >= 30 and n_lo >= 30 and c1 > c0:
        s0 = float(lg[~hi].std())
        s1 = float(lg[hi].std())
        sep = (c1 - c0) / (0.5 * (s0 + s1) + 1e-6)
        if hz1 / hz0 >= 1.3 and sep >= 2.0:
            g0, g1 = _label_clusters(hz0, hz1)
            if g0 != g1:
                two = True
            else:
                single = g0
    if not two and single is None:
        med = float(np.median(hz))
        if med < 150:
            single = "M"
        elif med > 190:
            single = "F"
        else:
            single = "M" if default_voice == VOICE_MALE else "F"
            info["summary"] = f"កម្រិតសំឡេង ~{int(med)}Hz មិនច្បាស់ ប្រើសំឡេងដែលបានជ្រើស"
    names = {"M": "ប្រុស", "F": "ស្រី"}
    if not two:
        med = float(np.median(hz))
        if not info["summary"]:
            info["summary"] = f"ស្គាល់ឃើញអ្នកនិយាយ ១ នាក់៖ {names[single]} (~{int(med)}Hz)"
        info.update({"two": False, "single": single})
        return [(0.0, duration + 1.0, single)], info
    nb = int(duration / BIN) + 2
    isf = np.where(hi, 1 if g1 == "F" else 0, 1 if g0 == "F" else 0)
    bins = np.minimum((tv / BIN).astype(int), nb - 1)
    vf = np.zeros(nb)
    vm = np.zeros(nb)
    np.add.at(vf, bins, isf)
    np.add.at(vm, bins, 1 - isf)
    lab = np.full(nb, -1, dtype=int)
    lab[vf > vm] = 1
    lab[vm > vf] = 0
    last = -1
    for i in range(nb):
        if lab[i] >= 0:
            last = lab[i]
        elif last >= 0:
            lab[i] = last
    nxt = -1
    for i in range(nb - 1, -1, -1):
        if lab[i] >= 0:
            nxt = lab[i]
        elif nxt >= 0:
            lab[i] = nxt
    pad = np.pad(lab, 2, mode="edge")
    sm = np.array([1 if pad[i:i + 5].sum() >= 3 else 0 for i in range(nb)])
    runs = []
    start = 0
    for i in range(1, nb + 1):
        if i == nb or sm[i] != sm[start]:
            runs.append([start * BIN, i * BIN, "F" if sm[start] else "M"])
            start = i
    runs = merge_short_runs(runs, MIN_TURN)
    runs[-1][1] = max(runs[-1][1], duration + 1.0)
    hz_m = hz0 if g0 == "M" else hz1
    hz_f = hz0 if g0 == "F" else hz1
    info["summary"] = (
        "ស្គាល់ឃើញអ្នកនិយាយ ២ នាក់៖ "
        f"ប្រុស (~{int(hz_m)}Hz) និងស្រី (~{int(hz_f)}Hz) "
        f"ប្តូរអ្នកនិយាយ {len(runs) - 1} ដង"
    )
    info.update({"two": True, "hz_m": hz_m, "hz_f": hz_f})
    return [(a, b, g) for a, b, g in runs], info


def safe_cut(text, pos):
    n = len(text)
    pos = max(0, min(n, pos))
    for d in range(0, 9):
        for p in (pos - d, pos + d):
            if 0 < p < n and text[p] == " ":
                return p
    p = pos
    while 0 < p < n and ("\u17B6" <= text[p] <= "\u17D3" or text[p - 1] == "\u17D2"):
        p -= 1
    return p


def split_text_by_shares(text, shares):
    text = fix_khmer(text)
    n = len(text)
    total = float(sum(shares)) or 1.0
    cuts = []
    acc = 0.0
    for sh in shares[:-1]:
        acc += sh
        cuts.append(safe_cut(text, int(round(n * acc / total))))
    pieces = []
    prev = 0
    for c in cuts + [n]:
        c = max(c, prev)
        pieces.append(fix_khmer(text[prev:c]))
        prev = c
    return pieces


def split_by_speaker(segments, runs, default_voice):
    voice_of = {"M": VOICE_MALE, "F": VOICE_FEMALE}
    out = []
    for s, e, text in segments:
        parts = []
        for rs, re_, g in runs:
            a, b = max(s, rs), min(e, re_)
            if b - a > 0.01:
                parts.append([a, b, g])
        if not parts:
            out.append((s, e, text, default_voice))
            continue
        parts = merge_short_runs(parts, 2.0)
        if len(parts) == 1:
            out.append((s, e, text, voice_of[parts[0][2]]))
            continue
        shares = [p[1] - p[0] for p in parts]
        pieces = split_text_by_shares(text, shares)
        for (a, b, g), piece in zip(parts, pieces):
            if piece:
                out.append((a, b, piece, voice_of[g]))
    return out


def dominant_voice(a, b, runs, default_voice):
    """ជ្រើសសំឡេងតែមួយក្នុងមួយឃ្លា តាមអ្នកនិយាយដែលនិយាយយូរជាងគេ (កុំកាត់ប្រយោគ)។"""
    tot = {"M": 0.0, "F": 0.0}
    for rs, re_, g in runs:
        ov = min(b, re_) - max(a, rs)
        if ov > 0 and g in tot:
            tot[g] += ov
    if tot["M"] <= 0 and tot["F"] <= 0:
        return default_voice
    return VOICE_MALE if tot["M"] >= tot["F"] else VOICE_FEMALE


def plan_dub_voices(segments, pcm, default_voice, duration, tracks=None):
    runs, info = gender_timeline(pcm, duration, default_voice, tracks=tracks)
    if runs is None:
        return [(s, e, t, default_voice) for s, e, t in segments], [], info, None
    dub = split_by_speaker(segments, runs, default_voice)
    lines = []
    for a, b, t, v in dub:
        hz = median_pitch(info, a, b)
        mark = "♂" if v == VOICE_MALE else "♀"
        lines.append(f"{mark} {int(hz) if hz else '?'}Hz  {t}")
    return dub, lines, info, runs


def _label_clusters(hz0, hz1):
    """កំណត់ភេទនៃក្រុមសំឡេង ២ (ទាប/ខ្ពស់)។ មិនយកក្រុមខ្ពស់ជាស្រី ប្រសិនបើប្រុស ២ នាក់ដែលសំឡេងខុសគ្នាបន្តិច
    (ឧ. ប្រុស 130Hz + ប្រុស 170Hz ត្រូវតែនៅជាប្រុសទាំងពីរ)។"""
    r = hz1 / max(hz0, 1.0)
    if hz0 <= 150:
        g0 = "M"
    elif hz0 >= 185:
        g0 = "F"
    else:
        g0 = "M" if (r >= 1.3 and hz1 >= 190) else "F"
    if hz1 >= 180:
        g1 = "F"
    elif hz1 <= 150:
        g1 = "M"
    else:
        g1 = "F" if (hz0 <= 150 and r >= 1.4) else g0
    return g0, g1


class SpeakerMap:
    """ផែនទីអ្នកនិយាយ ប្រុស/ស្រី តាមពេលវេលា។ វាស់តាមឃ្លានីមួយៗ (មិនត្រូវការ MIN_TURN ២វិ ដូច timeline)
    ដូច្នេះប្រុស/ស្រីឆ្លើយគ្នាលឿនៗ ក៏មិនច្រឡំសំឡេងដែរ។ អ្នកប្រើអាចបង្ខំភេទបាន (overrides)។"""

    def __init__(self, times=None, f0=None, mode="none", hz_m=None, hz_f=None, single=None):
        self.t = times
        self.f0 = f0
        self.mode = mode          # "two" | "single" | "none"
        self.hz_m = hz_m
        self.hz_f = hz_f
        self.single = single
        self.over = []
        self.summary = ""
        self._cache = {}

    def set_overrides(self, items):
        self.over = [(float(a), float(b), g) for a, b, g in (items or []) if g in ("M", "F")]
        self._cache = {}

    def _forced(self, a, b):
        if not self.over:
            return None
        tot = {"M": 0.0, "F": 0.0}
        for x, y, g in self.over:
            ov = min(b, y) - max(a, x)
            if ov > 0:
                tot[g] += ov
        best = "M" if tot["M"] >= tot["F"] else "F"
        span = max(0.05, b - a)
        return best if tot[best] >= 0.4 * span else None

    def _measure(self, a, b):
        if self.mode == "single":
            return self.single
        if self.mode != "two" or self.t is None or len(self.t) == 0:
            return None
        import numpy as np
        m = (self.t >= a) & (self.t <= b) & (self.f0 > 0)
        n = int(m.sum())
        if n < 4:
            return None
        lg = np.log2(self.f0[m])
        cut = 0.5 * (np.log2(self.hz_m) + np.log2(self.hz_f))
        nf = int((lg > cut).sum())
        nm = n - nf
        if abs(nf - nm) / float(n) < 0.2:
            return None
        return "F" if nf > nm else "M"

    def gender_at(self, a, b):
        key = (round(float(a), 2), round(float(b), 2))
        if key in self._cache:
            return self._cache[key]
        g = self._forced(a, b)
        if g is None:
            g = self._measure(a, b)
        self._cache[key] = g
        return g

    def fill(self, segs, default=None, max_gap=2.5):
        """ភេទរបស់ឃ្លានីមួយៗ។ ឃ្លាខ្លីពេកដែលវាស់មិនបាន ប្រើអ្នកនិយាយជិតបំផុតតាមពេល។"""
        raw = [self.gender_at(sg[0], sg[1]) for sg in segs]
        out = list(raw)
        for i in range(len(segs)):
            if out[i] is not None:
                continue
            best, bd = None, 1e9
            for j in range(len(segs)):
                if raw[j] is None:
                    continue
                d = max(segs[i][0] - segs[j][1], segs[j][0] - segs[i][1], 0.0)
                if d < bd:
                    best, bd = raw[j], d
            out[i] = best if (best and bd <= max_gap) else default
        return out


def build_speaker_map(tracks, duration, default_voice):
    try:
        times, f0, rms = tracks
        runs, info = gender_timeline(None, duration, default_voice, tracks=tracks)
    except Exception:
        return None
    if runs is None or "two" not in info:
        return None
    if info["two"]:
        sm = SpeakerMap(times, f0, "two", hz_m=info["hz_m"], hz_f=info["hz_f"])
    else:
        sm = SpeakerMap(times, f0, "single", single=info["single"])
    sm.summary = info.get("summary", "")
    return sm


def voices_from_map(smap, segs, default_voice, runs=None):
    """សំឡេង (ប្រុស/ស្រី) សម្រាប់ឃ្លានីមួយៗ។ ប្រុស → Piseth, ស្រី → Sreymom ជានិច្ច។"""
    if smap is None:
        if runs is None:
            return None
        return [dominant_voice(a, b, runs, default_voice) for a, b, _t in segs]
    out = []
    for g, (a, b, _t) in zip(smap.fill(segs, default=None), segs):
        if g == "M":
            out.append(VOICE_MALE)
        elif g == "F":
            out.append(VOICE_FEMALE)
        elif runs is not None:
            out.append(dominant_voice(a, b, runs, default_voice))
        else:
            out.append(default_voice)
    return out


MATCH_MIN = 0.8
MATCH_MAX = 1.25


def gender_medians(info, runs):
    import numpy as np
    t = info.get("times")
    f = info.get("f0")
    out = {}
    if t is None or len(t) == 0 or not runs:
        return out
    for g in ("M", "F"):
        m = np.zeros(len(t), dtype=bool)
        for a, b, gg in runs:
            if gg == g:
                m |= (t >= a) & (t < b)
        m &= f > 0
        if int(m.sum()) >= 10:
            out[g] = float(np.median(f[m]))
    return out


def compute_targets(dub_segments, seg_voices, info, runs):
    import numpy as np
    meds = gender_medians(info, runs) if runs else {}
    allmed = None
    f = info.get("f0")
    if f is not None and len(f):
        voiced = f[f > 0]
        if len(voiced) >= 25:
            allmed = float(np.median(voiced))
    voices = seg_voices or [None] * len(dub_segments)
    targets = []
    for seg, v in zip(dub_segments, voices):
        s, e = seg[0], seg[1]
        g = "M" if v == VOICE_MALE else ("F" if v == VOICE_FEMALE else None)
        base = meds.get(g) or allmed
        own = median_pitch(info, s, e)
        if base and own:
            t = 0.5 * base + 0.5 * own
        else:
            t = base or own
        targets.append(t)
    return targets


def tts_median_pitch(path):
    try:
        import numpy as np
        pcm = load_pcm(path)
        _, f, _ = pitch_track(pcm)
        if len(f) == 0:
            return None
        voiced = f[f > 0]
        if len(voiced) < 8:
            return None
        return float(np.median(voiced))
    except Exception:
        return None


def atempo_chain(x):
    parts = []
    while x > 2.0:
        parts.append("atempo=2.0")
        x /= 2.0
    while x < 0.5:
        parts.append("atempo=0.5")
        x *= 2.0
    parts.append(f"atempo={x:.4f}")
    return ",".join(parts)


EMO_LABELS = ["neutral", "happy", "excited", "angry", "sad", "fear", "whisper",
              "shout", "tender", "surprised", "worried", "sarcastic"]
EMO_HIGH = ("happy", "excited", "angry", "fear", "shout", "surprised")
EMO_LOW = ("sad", "whisper", "tender", "worried")

# (rate %, pitch Hz, volume %) ត្រូវគុណនឹងកម្លាំងអារម្មណ៍ (intensity)
EMO_PRESETS = {
    "neutral": (0, 0, 0),
    "happy": (8, 12, 6),
    "excited": (14, 18, 14),
    "angry": (12, 6, 28),
    "sad": (-16, -12, -20),
    "fear": (12, 18, -6),
    "whisper": (-10, -5, -45),
    "shout": (10, 10, 40),
    "tender": (-10, -4, -18),
    "surprised": (10, 20, 12),
    "worried": (-4, 6, -10),
    "sarcastic": (-8, 4, 0),
}

EMO_NAMES = {
    "neutral": "😐 ធម្មតា", "happy": "😊 សប្បាយ", "excited": "🤩 រំភើប",
    "angry": "😠 ខឹង", "sad": "😢 ក្រៀមក្រំ", "fear": "😨 ភ័យ",
    "whisper": "🤫 ខ្សឹប", "shout": "📢 ស្រែក", "tender": "🥰 ទន់ភ្លន់",
    "surprised": "😲 ភ្ញាក់ផ្អើល", "worried": "😟 បារម្ភ", "sarcastic": "😏 ចំអក",
}

EMO_SYSTEM = (
    "You are a film dubbing director. Each numbered Khmer line is spoken by a character. Decide the emotion the voice actor must PERFORM "
    "for that line so the dubbed voice sounds like a real, feeling human, not a reading machine. Use the neighbouring/context lines to understand "
    "the scene, who is speaking to whom and the mood. Allowed labels ONLY: neutral, happy, excited, angry, sad, fear, whisper, shout, tender, "
    "surprised, worried, sarcastic. Judge from the meaning, word choice, particles, punctuation (! ? ...), insults, pleading, crying, laughing, "
    "teasing, commands and exclamations. Do NOT default to neutral: use neutral only when the line is truly flat or purely informational. "
    "Also give intensity from 0.2 (slight) to 1.0 (very strong). "
    "Return JSON {\"emotions\": [{\"label\": \"angry\", \"intensity\": 0.8}, ...]} with exactly the same number of items, in the same order."
)


def norm_emotion(x):
    x = str(x or "").strip().lower()
    return x if x in EMO_LABELS else "neutral"


def parse_emo_item(x):
    """ទទួលទាំង {"label","intensity"} និងអក្សរសុទ្ធ → (label, intensity)។"""
    if isinstance(x, dict):
        lab = norm_emotion(x.get("label") or x.get("emotion"))
        try:
            inten = float(x.get("intensity", 0.7))
        except Exception:
            inten = 0.7
        return lab, max(0.2, min(1.0, inten))
    return norm_emotion(x), 0.7


def groq_emotion_chunk(api_key, texts, context=""):
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    user = (("CONTEXT (previous lines, do NOT label them): " + context + "\n\n") if context else "") + "LINES TO LABEL:\n" + numbered
    models = groq_chat_models(api_key)
    good = _groq_chat_cache["good"]
    if good in models:
        models = [good] + [m for m in models if m != good]
    last = "មិនមានម៉ូដែល"
    for model in models[:6]:
        body = json.dumps({
            "model": model, "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": EMO_SYSTEM},
                {"role": "user", "content": user},
            ],
        }).encode("utf-8")
        for attempt in range(2):
            request = urllib.request.Request(
                GROQ_CHAT_URL, data=body, method="POST",
                headers={"Authorization": f"Bearer {groq_first(api_key)}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            )
            try:
                with groq_urlopen(request, api_key, timeout=60) as r:
                    data = json.loads(r.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
                items = json.loads(content).get("emotions") or []
                if len(items) == len(texts):
                    _groq_chat_cache["good"] = model
                    return [parse_emo_item(x) for x in items]
                last = f"{model}: ចំនួនមិនត្រូវគ្នា"
                break
            except urllib.error.HTTPError as e:
                last = f"{model}: {http_detail(e)}"
                if e.code == 429 and attempt == 0:
                    time.sleep(6)
                    continue
                break
            except Exception as e:
                last = f"{model}: {e}"
                break
    raise RuntimeError(last[:300])


def gemini_emotion_labels(api_key, texts):
    client = make_gemini_client(api_key, types.HttpOptions(timeout=TRANSLATE_TIMEOUT_MS))
    avail = get_available_models(client)
    avail = [m for m in avail if "pro" in m.lower()] + [m for m in avail if "pro" not in m.lower()]
    models = avail[:3]
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    prompt = EMO_SYSTEM + "\n\nLINES TO LABEL:\n" + numbered
    last = None
    for model in models:
        try:
            resp = client.models.generate_content(
                model=model, contents=prompt,
                config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
            )
            raw = (getattr(resp, "text", "") or "").strip()
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
            data = json.loads(raw)
            items = data.get("emotions") if isinstance(data, dict) else data
            if isinstance(items, list) and len(items) == len(texts):
                return [parse_emo_item(x) for x in items]
        except Exception as e:
            last = e
    raise RuntimeError(f"Gemini emotion: {last}")


def label_emotions(texts, groq_key, gemini_key):
    """ត្រឡប់បញ្ជី (label, intensity) ឬ None។ ហៅស្របគ្នា មានកំណត់ពេល — Claude/CodeCraft → Groq → Gemini (ចុងក្រោយ)។"""
    if not texts:
        return None
    t_end = time.time() + 40
    step = 30
    parts = [(k, texts[k:k + step]) for k in range(0, len(texts), step)]

    def _run(fn):
        out = [None] * len(texts)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for k, part, r in pool.map(fn, parts):
                if r is None or len(r) != len(part):
                    return None
                for j, x in enumerate(r):
                    out[k + j] = parse_emo_item(x)
        return out

    _esys = EMO_SYSTEM.replace('"emotions"', '"translations"')

    def _via_oai(p):
        k, part = p
        try:
            return k, part, oai_try(part, None, _esys, to_english=True, raw=True)
        except Exception:
            return k, part, None

    try:
        out = _run(_via_oai)
        if out:
            return out
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)

    if groq_key and time.time() < t_end:
        def _via_groq(p):
            k, part = p
            ctx = " / ".join(str(t) for t in texts[max(0, k - 3):k])
            try:
                return k, part, groq_emotion_chunk(groq_key, part, ctx)
            except Exception:
                return k, part, None
        try:
            out = _run(_via_groq)
            if out:
                return out
        except Exception as _swallow_e:
            _log_swallowed(_swallow_e)

    if gemini_key and not groq_key and time.time() < t_end:
        try:
            out = gemini_emotion_labels(gemini_key, texts)
            if out and len(out) == len(texts):
                return out
        except Exception as _swallow_e:
            _log_swallowed(_swallow_e)
    return None


def combine_emotion(text_label, arousal, text_inten=None):
    """ผสมอารម្មណ៍ពីអត្ថបទ (AI) និងកម្លាំងសំឡេងដើម (arousal)។"""
    ti = 0.7 if text_inten is None else max(0.2, min(1.0, float(text_inten)))
    base = 0.4 + 1.0 * ti            # 0.6 .. 1.4
    if text_label in EMO_HIGH:
        return text_label, max(0.4, min(1.7, base + 0.5 * arousal))
    if text_label in EMO_LOW:
        return text_label, max(0.4, min(1.7, base - 0.3 * arousal))
    if text_label == "sarcastic":
        return text_label, max(0.5, min(1.3, base))
    if arousal > 0.3:
        return "excited", min(1.4, 0.5 + (arousal - 0.3) * 1.1)
    if arousal < -0.3:
        return "sad", min(1.4, 0.5 + (-arousal - 0.3) * 1.1)
    return "neutral", 0.0


def plan_emotions(dub_segments, seg_voices, info, runs, groq_key, gemini_key, labels="auto"):
    import numpy as np
    texts = [seg[2] for seg in dub_segments]
    if isinstance(labels, str):   # "auto" = គណនាខ្លួនឯង
        labels = label_emotions(texts, groq_key, gemini_key)
    if labels is not None and len(labels) != len(texts):
        labels = None
    t = f = r = None
    if info:
        t, f, r = info.get("times"), info.get("f0"), info.get("rms")
    have_audio = (t is not None and f is not None and r is not None and len(t) > 0)
    all_f = base_rms = None
    meds = {}
    if have_audio:
        voiced = f > 0
        if int(voiced.sum()) >= 25:
            all_f = float(np.median(f[voiced]))
            base_rms = float(np.median(r[voiced]))
        if runs:
            meds = gender_medians(info, runs)
    def clip(x):
        return float(np.clip(x, -1.5, 1.5))
    voices = seg_voices or [None] * len(dub_segments)
    result = []
    for i, seg in enumerate(dub_segments):
        s, e = seg[0], seg[1]
        v = voices[i]
        g = "M" if v == VOICE_MALE else ("F" if v == VOICE_FEMALE else None)
        arousal = 0.0
        if have_audio and all_f and base_rms:
            m = (t >= s) & (t <= e) & (f > 0)
            if int(m.sum()) >= 5:
                own = float(np.median(f[m]))
                base_f = meds.get(g) or all_f
                loud_db = 20.0 * np.log10(max(float(np.mean(r[m])), 1e-6) / max(base_rms, 1e-6))
                pitch_st = 12.0 * np.log2(own / base_f)
                std_st = float(np.std(12.0 * np.log2(f[m] / own)))
                arousal = (0.5 * clip(loud_db / 6.0) + 0.3 * clip(pitch_st / 4.0) + 0.2 * clip((std_st - 2.5) / 2.0))
        text_label, text_inten = (labels[i] if labels else (None, None))
        result.append(combine_emotion(text_label, arousal, text_inten))
    counts = Counter(lab for lab, _ in result)
    source = ("តាមអត្ថបទ + សំឡេងដើម" if labels and have_audio else "តាមអត្ថបទតែប៉ុណ្ណោះ" if labels else "តាមសំឡេងដើមតែប៉ុណ្ណោះ" if have_audio else "មិនមានទិន្នន័យ")
    summary = (f"🎭 អារម្មណ៍ ({source})៖ " + " · ".join(f"{EMO_NAMES[k]} {counts[k]}" for k in EMO_LABELS if counts.get(k)))
    lines = [summary]
    shown = 0
    for (lab, inten), text in zip(result, texts):
        if lab == "neutral":
            continue
        lines.append(f"{EMO_NAMES[lab]} ×{inten:.1f}  {text}")
        shown += 1
        if shown >= 40:
            break
    return result, lines


def emotion_prosody(label, intensity, use_pitch=True):
    rate, pitch, vol = EMO_PRESETS.get(label, (0, 0, 0))
    k = max(0.0, float(intensity))
    # រក្សាល្បឿនធម្មតា៖ អារម្មណ៍អាចប្តូរ pitch/volume ប៉ុន្តែមិនបង្កើនល្បឿននិយាយ។
    rate = int(max(-8, min(0, rate * k * 1.1)))
    pitch = int(max(-20, min(20, pitch * k * 0.95))) if use_pitch else 0
    vol = int(max(-35, min(35, vol * k * 0.8)))
    if rate == 0 and pitch == 0 and vol == 0:
        return None
    return {"rate": f"{rate:+d}%", "pitch": f"{pitch:+d}Hz", "volume": f"{vol:+d}%"}





EQ_CENTERS = [150, 250, 400, 630, 1000, 1600, 2500, 4000, 6300]


def band_levels(pcm, sr=16000):
    """វាស់ 'ពណ៌សំឡេង' ជាកម្រិត dB ក្នុងចន្លោះប្រេកង់ ៩ (ឥតគិតថ្លៃ គ្មាន API)"""
    import numpy as np
    n = 1024
    if pcm is None or len(pcm) < n * 8:
        return None
    hop = max(512, (len(pcm) - n) // 6000)
    count = 1 + (len(pcm) - n) // hop
    idx = (np.arange(count) * hop)[:, None] + np.arange(n)[None, :]
    frames = pcm[idx].astype(np.float64)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    thr = max(1e-4, 0.15 * float(np.percentile(rms, 90)))
    frames = frames[rms >= thr]
    if len(frames) < 10:
        return None
    pw = (np.abs(np.fft.rfft(frames * np.hanning(n), axis=1)) ** 2).mean(axis=0)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    out = []
    for c in EQ_CENTERS:
        m = (freqs >= c / 1.41) & (freqs < c * 1.41)
        out.append(10.0 * np.log10(float(pw[m].mean()) + 1e-12))
    return out


def eq_filters(ref, tts, limit=6.0):
    if not ref or not tts:
        return ""
    import numpy as np
    r = np.array(ref, dtype=np.float64)
    t = np.array(tts, dtype=np.float64)
    d = np.clip((r - r.mean()) - (t - t.mean()), -limit, limit)
    parts = [f"equalizer=f={c}:t=q:w=1.0:g={g:.1f}" for c, g in zip(EQ_CENTERS, d) if abs(g) >= 0.8]
    return ",".join(parts)


MERGE_TIGHT = (50, 0.4, 5.0)


def merge_for_dub(segments, max_chars=110, max_gap=0.35, max_len=5.5, gender_fn=None):
    """បញ្ចូលតែបំណែកខ្លីៗដែលដាច់កណ្តាលប្រយោគ ដើម្បីអានរលូន ហើយនៅជិតម៉ោងសំឡេងដើម"""
    out = []
    for s, e, t in segments:
        t = fix_khmer(t)
        if not t:
            continue
        if out:
            ps, pe, pt = out[-1]
            ended = pt.rstrip()[-1:] in "។.!?…"
            tiny_prev = len(pt) < 18
            tiny_cur = len(t) < 10
            if ((not ended) or tiny_prev or tiny_cur) and (s - pe) <= max_gap \
                    and len(pt) + len(t) + 1 <= max_chars and e - ps <= max_len \
                    and not _spk_differs(gender_fn, ps, pe, s, e):
                out[-1] = (ps, max(pe, e), fix_khmer(pt + " " + t))
                continue
        out.append((s, e, t))
    return out


def tts_retry(text, voice, path, prosody=None, tries=3):
    last = None
    for k in range(tries):
        try:
            tts_segment(text, voice, path, prosody)
            if os.path.exists(path) and os.path.getsize(path) > 200:
                return True
        except Exception as e:
            last = e
        # Retry without optional prosody as a recovery path; keep the same full text.
        if prosody and k >= 1:
            try:
                tts_segment(text, voice, path, None)
                if os.path.exists(path) and os.path.getsize(path) > 200:
                    return True
            except Exception as e:
                last = e
        time.sleep(0.08 * (k + 1))
    return False


def shorten_groq(api_key, text, max_seconds):
    limit = max(6, int(max_seconds * 11))
    try:
        models = groq_chat_models(api_key)[:3]
    except Exception:
        return text
    for model in models:
        try:
            body = json.dumps({
                "model": model, "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": f"Shorten the Khmer sentence to at most {limit} characters. Keep the meaning. Khmer script only. Return only the sentence."},
                    {"role": "user", "content": text},
                ],
            }).encode("utf-8")
            request = urllib.request.Request(
                GROQ_CHAT_URL, data=body, method="POST",
                headers={"Authorization": f"Bearer {groq_first(api_key)}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            )
            with groq_urlopen(request, api_key, timeout=40) as r:
                data = json.loads(r.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
            out = clean_translation(content)
            if out and has_khmer(out) and len(out) < len(text):
                return out
        except Exception:
            continue
    return text


def condense_for_slot(text, slot, client, model, groq_key):
    """បង្រួមប្រយោគខ្មែរឱ្យខ្លី (រក្សាអត្ថន័យ) ពេលវែងជាងមាត់និយាយច្រើនពេក។ បើមិនបានលទ្ធផលល្អ ត្រឡប់អត្ថបទដើម។"""
    try:
        _lim = max(6, int(slot * 11))
        _r = oai_try([text], None, "Shorten the Khmer sentence to at most " + str(_lim)
                     + " characters. Keep the meaning. Khmer script only. "
                     'Return JSON {"translations": ["<sentence>"]}.')
        if _r and _r[0] and has_khmer(_r[0]) and len(_r[0]) < len(text):
            return _r[0]
        if client is not None and model:
            out = shorten_khmer(client, model, text, slot)
            if out and out != text and has_khmer(out) and len(out) < len(text):
                return out
        if groq_key:
            out = shorten_groq(groq_key, text, slot)
            if out and out != text and has_khmer(out) and len(out) < len(text):
                return out
    except Exception as _swallow_e:
        _log_swallowed(_swallow_e)
    return text


# ធ្វើឱ្យសំឡេងស្តាប់ទន់ ក្តៅ និងដូចមនុស្សនិយាយក្នុងបន្ទប់ (មិនស្ងួតដូចម៉ាស៊ីន)
VOICE_POLISH = ("highpass=f=70,"
                "acompressor=threshold=0.14:ratio=2:attack=12:release=180,"
                "equalizer=f=180:t=q:w=1:g=1.5,"
                "equalizer=f=3200:t=q:w=1.2:g=2.0")

# ល្បឿនសំឡេងសម្រាប់កំណែ Khmer Dubbing៖ មិនបង្កើនល្បឿន TTS ឬកាត់ពាក្យដើម្បីប្រញាប់ឱ្យទាន់មាត់ទេ។
# ប្រយោគពេញមានអាទិភាពជាងល្បឿន; អាចយឺតតិចតួចតាមអារម្មណ៍ ប៉ុន្តែមិនលឿនជាងធម្មតា។
MAX_DUB_SPEEDUP = 1.0
MAX_TTS_RATE = 0
# ចាប់ផ្តើមសំឡេងខ្មែរមុន timestamp មាត់ប្រហែល 160ms ដើម្បីទូទាត់ latency របស់ TTS/ASR។
# អាចកែតាម .streamlit/secrets.toml ដោយ DUB_AUDIO_LEAD_SECONDS = 0.16 (កំណត់ចន្លោះ 0–0.35s)។
try:
    DUB_AUDIO_LEAD_SECONDS = float(get_secret("DUB_AUDIO_LEAD_SECONDS", "0.16") or 0.16)
except Exception:
    DUB_AUDIO_LEAD_SECONDS = 0.16
DUB_AUDIO_LEAD_SECONDS = max(0.0, min(0.35, DUB_AUDIO_LEAD_SECONDS))
# បិទការបង្កើត TTS ម្តងទៀតសម្រាប់កែ rate ដោយស្វ័យប្រវត្តិ៖ រក្សាល្បឿនធម្មជាតិ និងកាត់បន្ថយពេល។
TTS_AUTO_RATE_FIT = str(get_secret("TTS_AUTO_RATE_FIT", "0")).strip().lower() in ("1", "true", "yes", "on")
# TIME_SHORTEN=1: measure the REAL synthesized length of every line and, when it is clearly longer than
# the character's speaking time, ask the AI to rewrite it shorter and synthesize it again.
TIME_SHORTEN = str(get_secret("TIME_SHORTEN", "1")).strip().lower() in ("1", "true", "yes", "on")


def assign_characters(dub_segments, chars, info, names=None):
    """បែងចែកឃ្លាទៅសំឡេងគំរូតាម pitch (ទាប→ខ្ពស់)។
    names ត្រូវតែត្រូវនឹងលំដាប់ chars ដែលបាន validate រួច។
    ត្រឡប់ (seg_voices, targets, seg_char, char_bands, notes)។"""
    import numpy as np
    k = len(chars)
    n = len(dub_segments)
    order = sorted(range(k), key=lambda i: chars[i]["f0"])
    own = [median_pitch(info, sg[0], sg[1]) if info else None for sg in dub_segments]
    idx = [i for i, o in enumerate(own) if o]
    label = [None] * n
    if k == 1 or len(idx) < 2:
        label = [0] * n
    else:
        x = np.log2(np.array([own[i] for i in idx]))
        cen = np.percentile(x, np.linspace(10, 90, k))
        for _ in range(30):
            lab = np.argmin(np.abs(x[:, None] - cen[None, :]), axis=1)
            new = np.array([x[lab == c].mean() if np.any(lab == c) else cen[c] for c in range(k)])
            if np.allclose(new, cen, atol=1e-4):
                break
            cen = new
        rank = {int(c): r for r, c in enumerate(np.argsort(cen))}
        lab = np.argmin(np.abs(x[:, None] - cen[None, :]), axis=1)
        for i, l_ in zip(idx, lab):
            label[i] = rank[int(l_)]
        last = None
        for i in range(n):
            if label[i] is None:
                label[i] = last
            else:
                last = label[i]
        nxt = None
        for i in range(n - 1, -1, -1):
            if label[i] is None:
                label[i] = nxt if nxt is not None else 0
            else:
                nxt = label[i]
    seg_voices, targets, seg_char = [], [], []
    for l_ in label:
        ci = order[min(int(l_), k - 1)]
        c = chars[ci]
        seg_voices.append(VOICE_FEMALE if c["f0"] >= 165 else VOICE_MALE)
        targets.append(c["f0"])
        seg_char.append(ci)
    notes = []
    for ci, c in enumerate(chars):
        cnt = sum(1 for v in seg_char if v == ci)
        who = "ស្រី" if c["f0"] >= 165 else "ប្រុស"
        display_name = (names[ci] if names and ci < len(names) and str(names[ci]).strip()
                        else f"តួអង្គទី {c['n']}")
        notes.append(f"🎤 {display_name}: ~{int(c['f0'])}Hz → សំឡេង{who} ({cnt} ឃ្លា)")
    return seg_voices, targets, seg_char, [c["bands"] for c in chars], notes


def make_dub(folder, segments, voice, duration, keep_bg, client, model,
             seg_voices=None, targets=None, notes=None, emotions=None, groq_key=None,
             ref_bands=None, offset=0.0, tight=True, hard_cut=True, bg_vol=0.08,
             seg_char=None, char_bands=None, timbre_refs=None, timbre_names=None,
             clone_enabled=False, offline_voice=False):
    inputs, filters = [], []
    n = 0
    if keep_bg:
        inputs += ["-i", "audio.mp3"]
        filters.append(f"[0:a]volume={float(bg_vol):.3f}[bg]")
        n = 1
    first_voice = n
    n_seg = len(segments)
    voices_ = [seg_voices[i] if seg_voices else voice for i in range(n_seg)]
    pros = []
    clone_lock = threading.Lock()
    clone_stats = {"ok": 0, "failed": 0}
    for i in range(n_seg):
        p = None
        if emotions is not None and i < len(emotions):
            label, inten = emotions[i]
            p = emotion_prosody(label, inten, use_pitch=(targets is None))
        pros.append(p)

    def gen(i):
        s_, e_, t_ = segments[i]
        next_s_ = segments[i + 1][0] if i + 1 < n_seg else duration
        slot0 = max(0.6, min(next_s_ - 0.08, e_ + (0.4 if tight else 1.0)) - s_)
        path_ = os.path.join(folder, f"tts_{i}.mp3")
        try:
            if offline_voice:
                _offline_wav = os.path.join(folder, f"tts_{i}_offline.wav")
                _ref_wav = None
                if timbre_refs:
                    if seg_char and i < len(seg_char):
                        _ci = int(seg_char[i])
                        if 0 <= _ci < len(timbre_refs):
                            _ref_wav = timbre_refs[_ci]
                    if _ref_wav is None and len(timbre_refs) == 1:
                        _ref_wav = timbre_refs[0]
                _style_ = ""
                if emotions is not None and i < len(emotions):
                    _style_ = vox_style_prefix(*emotions[i])
                if not offline_voxcpm_synthesize(t_, _offline_wav, _ref_wav, _style_):
                    return None
                run_ffmpeg(["-i", _offline_wav, "-vn", "-ac", "1", "-ar", "24000",
                            "-c:a", "libmp3lame", "-b:a", "128k", path_], cwd=folder)
                if not os.path.isfile(path_) or os.path.getsize(path_) < 500:
                    return None
            else:
                if not tts_retry(t_, voices_[i], path_, pros[i]):
                    return None

            # Measure-and-rewrite loop: if the REAL audio is much longer than the speaking time
            # (more than the 1.3x speed-up can absorb), rewrite the line shorter and synthesize again.
            if TIME_SHORTEN and (not offline_voice) and (groq_key or oai_enabled()):
                try:
                    _d0, _, _ = probe_media(path_)
                    if _d0 and _d0 > slot0 * 1.3 and len(str(t_)) > 14:
                        _goal = max(8, int(len(str(t_)) * (slot0 * 1.1) / _d0))
                        _rows = [f"ORIGINAL: (not available) | KHMER: {t_} | MAX: {_goal}"]
                        _new = llm_lines(_rows, FIT_SYSTEM, None, groq_key)
                        _nt = str(_new[0]).strip() if _new else ""
                        if (_nt and has_khmer(_nt) and khmer_dominant(_nt)
                                and 0.3 * len(str(t_)) <= len(_nt) < len(str(t_))):
                            _p2 = os.path.join(folder, f"tts_{i}_s.mp3")
                            if tts_retry(_nt, voices_[i], _p2, pros[i], tries=2):
                                _d2, _, _ = probe_media(_p2)
                                if _d2 and _d2 < _d0 * 0.95:
                                    shutil.move(_p2, path_)
                                    t_ = _nt
                except Exception as _shorten_error:
                    _log_swallowed(_shorten_error)

            # Convert the generated Khmer TTS line to the assigned character's reference voice.
            # OpenVoice loads once and protects its shared PyTorch model with an internal lock.
            if (not offline_voice) and clone_enabled and timbre_refs and seg_char and i < len(seg_char):
                _char_idx = int(seg_char[i])
                if 0 <= _char_idx < len(timbre_refs) and timbre_refs[_char_idx]:
                    _clone_src_wav = os.path.join(folder, f"tts_{i}_source.wav")
                    _clone_wav = os.path.join(folder, f"tts_{i}_clone.wav")
                    _clone_mp3 = os.path.join(folder, f"tts_{i}_clone.mp3")
                    try:
                        # Normalize generated TTS to PCM WAV before librosa/OpenVoice reads it.
                        run_ffmpeg(["-i", path_, "-vn", "-ac", "1", "-ar", "24000", _clone_src_wav], cwd=folder)
                        import voice_clone as _voice_clone_runtime
                        with clone_lock:
                            _cloned = _voice_clone_runtime.clone_to(
                                _clone_src_wav, timbre_refs[_char_idx], _clone_wav
                            )
                        if _cloned and os.path.exists(_clone_wav) and os.path.getsize(_clone_wav) > 1000:
                            run_ffmpeg(["-i", _clone_wav, "-vn", "-ac", "1", "-ar", "24000",
                                        "-c:a", "libmp3lame", "-b:a", "96k", _clone_mp3], cwd=folder)
                            if os.path.exists(_clone_mp3) and os.path.getsize(_clone_mp3) > 500:
                                shutil.move(_clone_mp3, path_)
                                with clone_lock:
                                    clone_stats["ok"] += 1
                            else:
                                with clone_lock:
                                    clone_stats["failed"] += 1
                        else:
                            with clone_lock:
                                clone_stats["failed"] += 1
                    except Exception as _clone_error:
                        _log_swallowed(_clone_error)
                        with clone_lock:
                            clone_stats["failed"] += 1

            d_, _, _ = probe_media(path_)
            # តម្រឹមល្បឿនអាន ឱ្យចប់ត្រូវពេលមាត់តួអង្គ (មិនលឿនពេក មិនយឺតពេក)
            mouth_ = max(0.5, e_ - s_)
            lo_ = min(mouth_ * 0.88, slot0)
            hi_ = slot0

            def _miss(x):
                return max(0.0, x - hi_ * 1.03) + max(0.0, lo_ - x)

            def _fit_rate(text_, d_cur, p_cur):
                for _k in range(1):
                    if _miss(d_cur) <= 0:
                        break
                    try:
                        try:
                            base_ = int(str((p_cur or {}).get("rate", "-4%")).replace("%", "").replace("+", ""))
                        except Exception:
                            base_ = -4
                        goal_ = hi_ * 0.97 if d_cur > hi_ * 1.03 else min(hi_, mouth_ * 0.95)
                        mult_ = (1.0 + base_ / 100.0) * (d_cur / max(0.3, goal_))
                        new_rate = int(round(max(-30, min(MAX_TTS_RATE, (mult_ - 1.0) * 100))))
                        if new_rate == base_:
                            break
                        p2_ = {"rate": f"{new_rate:+d}%",
                               "volume": (p_cur or {}).get("volume", "+0%"),
                               "pitch": (p_cur or {}).get("pitch", "+0Hz")}
                        path2_ = os.path.join(folder, f"tts_{i}_f.mp3")
                        if not tts_retry(text_, voices_[i], path2_, p2_, tries=2):
                            break
                        d2_, _, _ = probe_media(path2_)
                        if _miss(d2_) < _miss(d_cur):
                            shutil.move(path2_, path_)
                            d_cur, p_cur = d2_, p2_
                        else:
                            break
                    except Exception:
                        break
                return d_cur, p_cur

            p_cur_ = pros[i]
            if TTS_AUTO_RATE_FIT and not offline_voice:
                d_, p_cur_ = _fit_rate(t_, d_, p_cur_)
            # មិនបង្រួមប្រយោគស្វ័យប្រវត្តិទេ៖ រក្សាពាក្យ និងអត្ថន័យឱ្យពេញ។
            # បើឃ្លាវែងជាងចន្លោះមាត់ នឹងទុកសំឡេងធម្មជាតិ មិនបង្ខំឱ្យ TTS និយាយលឿន។
            f0_ = None
            if (not clone_enabled) and targets is not None and i < len(targets) and targets[i]:
                f0_ = tts_median_pitch(path_)
            tb_ = None
            if (not clone_enabled) and (ref_bands or char_bands):
                try:
                    tb_ = band_levels(load_pcm(path_))
                except Exception:
                    tb_ = None
            return d_, f0_, tb_
        except Exception as _gen_error:
            # Offline model errors must remain visible; do not silently produce a video without dubbing.
            if offline_voice:
                raise
            return None

    _tts_workers = 1 if offline_voice else max(4, min(16, int(get_secret("TTS_WORKERS", "14") or 14)))
    with ThreadPoolExecutor(max_workers=_tts_workers) as pool:
        results = list(pool.map(gen, range(n_seg)))

    voice_eq = {}
    if ref_bands and not clone_enabled:
        import numpy as np
        for v_ in set(voices_):
            arrs = [r_[2] for k_, r_ in enumerate(results) if r_ and r_[2] and voices_[k_] == v_]
            if arrs:
                eqs = eq_filters(ref_bands, np.mean(arrs, axis=0).tolist())
                if eqs:
                    voice_eq[v_] = eqs
        if notes is not None and voice_eq:
            notes.append("🎚 ផ្គូផ្គងពណ៌សំឡេងស្រដៀងសំឡេងគំរូ")
    char_eq = {}
    if char_bands and seg_char and not clone_enabled:
        import numpy as np
        for c_ in set(seg_char):
            arrs = [r_[2] for k_, r_ in enumerate(results)
                    if r_ and r_[2] and k_ < len(seg_char) and seg_char[k_] == c_]
            if arrs and char_bands[c_]:
                eqs = eq_filters(char_bands[c_], np.mean(arrs, axis=0).tolist())
                if eqs:
                    char_eq[c_] = eqs
        if notes is not None and char_eq:
            notes.append("🎚 ផ្គូផ្គងពណ៌សំឡេងតាមតួអង្គនីមួយៗ")
    cursor = 0.0
    plan = []
    skipped = 0
    for i, res in enumerate(results):
        s, e, t = segments[i]
        if res is None:
            skipped += 1
            continue
        d, f0, _tb = res
        next_s = segments[i + 1][0] if i + 1 < n_seg else duration
        prev_end = segments[i - 1][1] if i > 0 else 0.0
        # ខ្សែសំឡេង TTS/ASR ជាទូទៅចាប់ផ្តើមយឺតជាងចលនាមាត់បន្តិច។
        # លើកសំឡេងមកមុន 160ms តិចៗ ដើម្បីឱ្យពាក្យចាប់ផ្តើមត្រូវនឹងមាត់ មិនឱ្យរូបភាពទៅមុខសំឡេង។
        lead = DUB_AUDIO_LEAD_SECONDS
        start = max(s + offset - lead, 0.0)
        if start >= duration - 0.3:
            break
        slot = max(0.6, min(next_s - 0.04, e + (0.4 if tight else 1.2)) - start)
        # Fit the complete generated sentence into its available slot when
        # possible. atempo > 1 speeds up; < 1 slows down. Avoid extreme rates
        # that make Khmer hard to understand.
        # Previous line still talking? Start right after it, never overlap.
        # Anchor every dub line to its own detected source-speech start.
        # Do not shift later lines forward when a previous TTS line is long;
        # that creates cumulative audio/video drift. The speed/slot logic below
        # handles overlap locally while keeping the original start timestamp.
        # រក្សា TTS នៅល្បឿនធម្មជាតិ 1.0x។ ការបកប្រែមាន timing budget ជួយឱ្យប្រយោគមិនវែងលើសចន្លោះ។
        # កុំបង្ខំឱ្យនិយាយលឿន ឬកាត់សំឡេងចោល; ចាប់ផ្តើមមុនតិចៗតាម DUB_AUDIO_LEAD_SECONDS។
        speed = d / slot if d > slot else 1.0
        speed = min(MAX_DUB_SPEEDUP, max(1.0, speed))
        # Match the character's speaking time (all voice modes): speed up long lines
        # (max 1.3x) and slow very short ones (min 0.9x) so speech stays clear.
        _r = d / slot
        if _r > 1.0:
            speed = min(1.3, _r)
        elif _r < 0.85:
            speed = max(0.9, _r)
        else:
            speed = 1.0
        # មិនបង្ខំឱ្យលឿន ឬយឺតដោយ atempo ទេ៖ ប្រើល្បឿនធម្មជាតិ 1.0x។
        cursor = max(cursor, start + d / speed + 0.02)
        target = targets[i] if (targets is not None and i < len(targets) and targets[i]) else None
        maxdur = None
        if hard_cut and MAX_DUB_SPEEDUP > 1.0 and d / speed > slot * 1.2:
            maxdur = slot
        plan.append({"name": f"tts_{i}.mp3", "start": start, "speed": speed, "maxdur": maxdur,
                     "voice": voices_[i], "f0": f0 if target else None, "target": target,
                     "eq": (char_eq.get(seg_char[i], "") if (seg_char and i < len(seg_char)) else voice_eq.get(voices_[i], ""))})
    if notes is not None and clone_enabled:
        if clone_stats["ok"]:
            notes.append(f"🧬 ក្លូនសំឡេងបាន {clone_stats['ok']} ឃ្លា តាមតួអង្គនីមួយៗ")
        if clone_stats["failed"]:
            notes.append(f"⚠️ ក្លូនសំឡេងមិនបាន {clone_stats['failed']} ឃ្លា — ប្រើសំឡេង TTS មូលដ្ឋានជំនួស")
    if notes is not None and skipped:
        notes.append(f"⚠️ មិនអាចបង្កើតសំឡេង {skipped} ឃ្លា")
    if not plan:
        return False
    base = {}
    for v in set(p["voice"] for p in plan):
        vals = [p["f0"] for p in plan if p["voice"] == v and p["f0"]]
        if vals:
            base[v] = float(statistics.median(vals))
    stats = {}
    for p in plan:
        ratio = 1.0
        if p["target"] and base.get(p["voice"]):
            ratio = p["target"] / base[p["voice"]]
            ratio = max(MATCH_MIN, min(MATCH_MAX, ratio))
            if abs(ratio - 1.0) < 0.03:
                ratio = 1.0
            rec = stats.setdefault(p["voice"], [[], []])
            rec[0].append(ratio)
            rec[1].append(p["target"])
        delay = int(p["start"] * 1000)
        inputs += ["-i", p["name"]]
        if ratio == 1.0:
            chain = atempo_chain(p["speed"])
        else:
            chain = ("aresample=24000," f"asetrate={int(24000 * ratio)}," "aresample=24000," + atempo_chain(p["speed"] / ratio))
        if hard_cut:
            # កាត់ស្ងាត់ដើមឃ្លា ដើម្បីឱ្យសំឡេងចាប់ផ្តើមត្រូវពេលមាត់
            chain = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03," + chain
        if p.get("eq"):
            chain += "," + p["eq"]
        chain += "," + VOICE_POLISH
        if p.get("maxdur"):
            md = max(0.3, float(p["maxdur"]))
            chain += f",atrim=0:{md:.3f},afade=t=out:st={max(0.0, md - 0.08):.3f}:d=0.08"
        filters.append(f"[{n}:a]{chain},afade=t=in:d=0.03,adelay={delay}:all=1[a{n}]")
        n += 1
    if notes is not None:
        for v, (ratios, tgts) in stats.items():
            who = "ប្រុស" if v == VOICE_MALE else "ស្រី"
            notes.append(f"🧬 សំឡេង AI {who}៖ ~{int(base[v])}Hz → " f"សំឡេងដើម ~{int(statistics.median(tgts))}Hz " f"(កែ ×{statistics.mean(ratios):.2f})")
    labels = "[bg]" if keep_bg else ""
    labels += "".join(f"[a{k}]" for k in range(first_voice, n))
    limiter = ",alimiter=limit=0.95" if emotions is not None else ""
    fc = (";".join(filters) + f";{labels}amix=inputs={n}:dropout_transition=0," f"volume={n}{limiter}[out]")
    run_ffmpeg(inputs + ["-filter_complex", fc + ";[out]aresample=24000:async=1:first_pts=0,apad[outp]", "-map", "[outp]", "-t", f"{duration:.3f}", "-ar", "24000", "dub.wav"], cwd=folder)
    return os.path.exists(os.path.join(folder, "dub.wav"))


def build_video_filter(max_side, subs=True):
    parts = []
    if max_side and max_side > 0:
        parts.append(f"scale=w='if(gt(iw,ih),-2,min({max_side},iw))':" f"h='if(gt(iw,ih),min({max_side},ih),-2)':flags=fast_bilinear")
    if subs:
        parts.append("ass=filename=captions.ass:fontsdir=.")
    parts.append("format=yuv420p")
    return ",".join(parts)



# =====================================================================
#  Logo + Blur (បិទបាំង) លើវីដេអូ
# =====================================================================
def out_dims(w, h, max_side):
    """ទំហំវីដេអូលទ្ធផល ក្រោយ scale (ដូចក្នុង build_video_filter)។"""
    if not max_side or max_side <= 0:
        return w, h

    def ev(x):
        return max(2, int(round(x / 2.0)) * 2)

    if w > h:
        h2 = min(max_side, h)
        return ev(w * h2 / float(h)), h2
    w2 = min(max_side, w)
    return w2, ev(h * w2 / float(w))


def prepare_fx(folder, fx, vid_w, vid_h, max_side):
    """រៀបចំ logo.png (ទំហំ/ពណ៌/ភាពថ្លា) និងបញ្ជី blur សម្រាប់ ffmpeg។"""
    if not fx:
        return None
    spec = {"blurs": [], "logo": None}
    for b in fx.get("blurs") or []:
        w = max(0.02, min(1.0, float(b["w"])))
        h = max(0.02, min(1.0, float(b["h"])))
        x = max(0.0, min(1.0 - w, float(b["x"])))
        y = max(0.0, min(1.0 - h, float(b["y"])))
        spec["blurs"].append({"x": x, "y": y, "w": w, "h": h,
                              "sigma": max(2, int(b.get("sigma", 25))),
                              "t0": b.get("t0"), "t1": b.get("t1")})
    if fx.get("logo_bytes"):
        try:
            from PIL import Image
            out_w, _out_h = out_dims(vid_w, vid_h, max_side)
            im = Image.open(io.BytesIO(fx["logo_bytes"])).convert("RGBA")
            tw = max(8, int(out_w * float(fx.get("logo_size", 15)) / 100.0))
            th = max(8, int(im.height * tw / float(im.width)))
            im = im.resize((tw, th), Image.LANCZOS)
            r, g, b_, a = im.split()
            if fx.get("logo_color"):
                solid = Image.new("RGBA", im.size, fx["logo_color"])
                r, g, b_, _ = solid.split()
            op = max(0.05, min(1.0, float(fx.get("logo_opacity", 1.0))))
            a = a.point(lambda v: int(v * op))
            Image.merge("RGBA", (r, g, b_, a)).save(os.path.join(folder, "logo.png"))
            spec["logo"] = {"x": max(0.0, min(1.0, float(fx.get("logo_x", 0.9)))),
                            "y": max(0.0, min(1.0, float(fx.get("logo_y", 0.1))))}
        except Exception:
            spec["logo"] = None
    if not spec["blurs"] and not spec["logo"]:
        return None
    return spec


def video_filter_args(max_side, subs, dub, spec, vid_w=None, vid_h=None):
    """ត្រឡប់ (input បន្ថែម, ជម្រើស filter+map) សម្រាប់ ffmpeg។"""
    if not spec:
        a = ["-vf", build_video_filter(max_side, subs)]
        if dub:
            a += ["-map", "0:v:0", "-map", "1:a:0"]
        return [], a
    nodes = []
    cur = "[0:v]"
    cnt = [0]

    def nxt():
        cnt[0] += 1
        return f"[v{cnt[0]}]"

    if max_side and max_side > 0:
        out = nxt()
        nodes.append(
            f"{cur}scale=w='if(gt(iw,ih),-2,min({max_side},iw))':"
            f"h='if(gt(iw,ih),min({max_side},ih),-2)':flags=fast_bilinear{out}")
        cur = out
    for i, b in enumerate(spec["blurs"]):
        out = nxt()
        nodes.append(f"{cur}split=2[ba{i}][bb{i}]")
        nodes.append(
            f"[bb{i}]crop=w='trunc(iw*{b['w']:.4f}/2)*2':h='trunc(ih*{b['h']:.4f}/2)*2':"
            f"x='trunc(iw*{b['x']:.4f}/2)*2':y='trunc(ih*{b['y']:.4f}/2)*2',"
            f"gblur=sigma={b['sigma']}:steps=2[bc{i}]")
        en = ""
        if b.get("t0") is not None and b.get("t1") is not None:
            en = f":enable='between(t,{float(b['t0']):.2f},{float(b['t1']):.2f})'"
        nodes.append(
            f"[ba{i}][bc{i}]overlay=x='trunc(W*{b['x']:.4f}/2)*2':y='trunc(H*{b['y']:.4f}/2)*2'{en}{out}")
        cur = out
    extra_in = []
    if spec.get("logo"):
        lg = spec["logo"]
        idx = 2 if dub else 1
        extra_in = ["-i", "logo.png"]
        out = nxt()
        nodes.append(
            f"{cur}[{idx}:v]overlay=x='max(0,min(W-w,W*{lg['x']:.4f}-w/2))':"
            f"y='max(0,min(H-h,H*{lg['y']:.4f}-h/2))'{out}")
        cur = out
    if subs:
        out = nxt()
        nodes.append(f"{cur}ass=filename=captions.ass:fontsdir=.{out}")
        cur = out
    nodes.append(f"{cur}format=yuv420p[vout]")
    maps = ["-map", "[vout]"] + (["-map", "1:a:0"] if dub else ["-map", "0:a:0?"])
    return extra_in, ["-filter_complex", ";".join(nodes)] + maps


def render_with_fonts(folder, fonts, captions, font_size, outline_size,
                      color, vid_w, vid_h, quality, status, dub=False, style=None, subs=True, fx=None):
    ass_path = os.path.join(folder, "captions.ass")
    output_path = os.path.join(folder, "output.mp4")
    max_side, crf, preset = quality
    fx_spec = prepare_fx(folder, fx, vid_w, vid_h, max_side)
    if not subs:
        args = ["-i", "input.mp4"]
        if dub:
            args += ["-i", "dub.wav"]
        fast_copy = not (max_side and max_side > 0) and not fx_spec
        if not fast_copy:
            extra_in, vf_args = video_filter_args(max_side, False, dub, fx_spec, vid_w, vid_h)
            args += extra_in + vf_args
        elif dub:
            args += ["-map", "0:v:0", "-map", "1:a:0"]
        if fast_copy:
            args += ["-c:v", "copy"]
        else:
            args += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                     "-maxrate", RATE_CAP.get(max_side, RATE_CAP[0])[0], "-bufsize", RATE_CAP.get(max_side, RATE_CAP[0])[1]]
        args += ["-c:a", "aac", "-b:a", "128k", "-af", "aresample=async=1:first_pts=0", "-shortest", "-movflags", "+faststart", "output.mp4"]
        log = run_ffmpeg(args, cwd=folder)
        return output_path, "-", log, ["មិនដាក់អក្សរ"]
    conf_env = make_fontconfig_env(folder)
    plan = [(0, False), (0, True)]
    plan += [(i, True) for i in range(1, len(fonts))]
    attempts = []
    chosen = None
    fallback = None
    # ជំហាន ១: សាក Font លើក្លីបខ្លី ១.៥ វិនាទី (លឿន) ជំនួសឱ្យ render ទាំងមូលច្រើនដង
    for font_index, use_conf in plan:
        font_path, default_name = fonts[font_index]
        family = get_font_family(font_path, default_name)
        keys = [family.lower(), default_name.lower()]
        write_ass(ass_path, [(0.0, 3.0, "ខ្ញុំស្រឡាញ់អ្នក")], family, font_size, outline_size, color, vid_w, vid_h, style)
        try:
            log = run_ffmpeg(
                ["-i", "input.mp4", "-t", "1.5", "-an",
                 "-vf", "ass=filename=captions.ass:fontsdir=.,format=yuv420p",
                 "-c:v", "libx264", "-preset", "ultrafast", "-crf", "40", "font_test.mp4"],
                cwd=folder, verbose=True, env=conf_env if use_conf else None)
        except RuntimeError:
            attempts.append(f"{family} conf={use_conf}: ffmpeg error")
            continue
        ok = font_was_used(log, keys)
        attempts.append(f"{family} conf={use_conf}: ok={ok}")
        if fallback is None:
            fallback = (font_index, use_conf, family, log)
        if ok:
            chosen = (font_index, use_conf, family, log)
            break
        dbg(status, f"Font {family} មិនត្រូវបានប្រើ កំពុងសាកវិធីផ្សេង...")
    if chosen is None:
        chosen = fallback
    if chosen is None:
        raise RuntimeError("Render មិនបាន។\n" + "\n".join(attempts))
    font_index, use_conf, family, test_log = chosen
    # ជំហាន ២: render ពេញមួយដងតែប៉ុណ្ណោះ ជាមួយ Font ដែលបានជ្រើស
    write_ass(ass_path, captions, family, font_size, outline_size, color, vid_w, vid_h, style)
    args = ["-i", "input.mp4"]
    if dub:
        args += ["-i", "dub.wav"]
    extra_in, vf_args = video_filter_args(max_side, True, dub, fx_spec, vid_w, vid_h)
    args += extra_in + vf_args
    args += ["-c:v", "libx264", "-preset", preset, "-threads", "0", "-crf", str(crf),
             "-maxrate", RATE_CAP.get(max_side, RATE_CAP[0])[0], "-bufsize", RATE_CAP.get(max_side, RATE_CAP[0])[1],
             "-c:a", "aac", "-b:a", "96k", "-af", "aresample=async=1:first_pts=0", "-shortest", "-movflags", "+faststart", "output.mp4"]
    try:
        total_dur = probe_media(os.path.join(folder, "input.mp4"))[0]
    except Exception:
        total_dur = 0.0
    item_ = getattr(status, "item", None)

    def _on_pct(frac, elapsed):
        if item_ is None:
            return
        item_["pct"] = max(item_.get("pct", 0.0), 0.82 + 0.17 * frac)
        msg = f"៤/៤ កំពុងដាក់អក្សរចូលវីដេអូ... {int(frac * 100)}%"
        if frac > 0.03:
            msg += f" · នៅសល់ប្រហែល {int(elapsed / frac - elapsed)} វិនាទី"
        item_["stage"] = msg

    run_ffmpeg_progress(args, cwd=folder, env=conf_env if use_conf else None, total=total_dur, on_pct=_on_pct)
    return output_path, family, test_log, attempts


def new_item(name, path=None, url=None):
    return {
        "name": name, "path": path, "url": url, "state": "queued",
        "stage": "ក្នុងជួររង់ចាំ...", "pct": 0.0, "warn": [], "log": [],
        "video_path": None, "captions": [], "voice_lines": [], "error": None,
        "raw_error": "", "debug": {}, "t0": None, "elapsed": None,
        "srt": "", "srt_on": False,
        "review_segments": None, "review_final": None, "review_event": None,
    }


class Job:
    def __init__(self, items, folder):
        self.id = uuid.uuid4().hex[:8]
        self.items = items
        self.folder = folder
        self.render_slots = threading.Semaphore(MAX_RENDER_AT_ONCE)
        self.zip = None
        self.zip_done = False
        self.merged = None
        self.scrolled = False
        self.turn = 0
        self.turn_cv = threading.Condition()
    def running(self):
        return any(it["state"] in ("queued", "running", "review") for it in self.items)
    def reviewing(self):
        return any(it["state"] == "review" for it in self.items)


TITLE_SYSTEM = (
    "You are a Cambodian social-media editor. Read the Khmer script of a short video and write 6 DIFFERENT catchy video titles "
    "in natural everyday Khmer for TikTok or Facebook. Each title is 15 to 60 Khmer characters, makes viewers curious or emotional, "
    "and is 100 percent true to what really happens in the script: never invent events, names or facts. "
    "Vary the style: question, emotional, suspense, short punchy, storytelling, funny. "
    "Khmer script only (names may stay), no emojis, no hashtags, no quotes, no numbering. "
    'Return JSON {"translations": ["<title1> | <title2> | <title3> | <title4> | <title5> | <title6>"]} '
    "with EXACTLY ONE item that contains the 6 titles separated by the | character."
)


def suggest_titles(lines, groq_key):
    """ស្នើចំណងជើងខ្មែរ ៦ ប្រភេទ ពីអត្ថបទបកប្រែ ឱ្យអ្នកប្រើជ្រើសយកទៅដាក់ (មិនចាំបាច់នឹកខ្លួនឯង)។"""
    script = " ".join(str(t).strip() for t in lines if str(t).strip())
    if len(script) > 3200:
        script = script[:2000] + " ... " + script[-1000:]
    if not script:
        return []
    res = groq_translate_chunk(groq_key, [script], None, system=TITLE_SYSTEM, to_english=True)
    raw = str((res or [""])[0] or "")
    out, seen = [], set()
    for part in re.split(r"[|\n]", raw):
        t = re.sub(r"^\s*(?:\d+[.)]|[-•*])\s*", "", part).strip().strip("\"'“”«»")
        if t and has_khmer(t) and t not in seen:
            seen.add(t)
            out.append(t)
    return out[:6]


def engine_name(engine):
    return "Claude + Groq (បម្រុង៖ OpenRouter/CodeCraft)"



# =====================================================================
#  LOCAL OFFLINE AI (no API keys): Whisper large-v3 + MADLAD-400 3B INT8
#  + VoxCPM2 2B Khmer TTS/voice cloning. Loaded lazily; online path untouched.
# =====================================================================
_OFFLINE_JOB_LOCK = threading.Lock()
_OFFLINE_TTS_LOCK = threading.RLock()
_OFFLINE_VOXCPM_MODEL = None


OFFLINE_WHISPER_REPOS = {
    "large-v3 (ធំបំផុត · ត្រឹមត្រូវបំផុត)": "Systran/faster-whisper-large-v3",
    "medium (លឿនជាង)": "Systran/faster-whisper-medium",
    "small (លឿនបំផុត)": "Systran/faster-whisper-small",
}


def _offline_whisper_transcribe(audio_path, source_language, status, whisper_choice=None):
    """Local ASR using the multilingual Whisper large-v3 model."""
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        raise UserError(
            "Offline ASR មិនទាន់ដំឡើងទេ។ សូមបើក Terminal/CMD (ក្នុង Environment ដែលដំណើរការ Streamlit) "
            "ហើយរត់ពាក្យបញ្ជា៖  pip install faster-whisper sentencepiece soundfile  "
            "រួចបិទ-បើកកម្មវិធីឡើងវិញ។ "
            f"មូលហេតុ: {e}"
        )
    import ctranslate2
    _wh_repo = OFFLINE_WHISPER_REPOS.get(whisper_choice) or "Systran/faster-whisper-large-v3"
    device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    cpu_threads = max(2, min(8, (os.cpu_count() or 4) - 1))
    status.write(
        "🧠 Offline AI: កំពុងផ្ទុក Whisper large-v3 "
        f"({'GPU' if device == 'cuda' else 'CPU INT8'})... (ទាញយកលើកដំបូងប្រហែល 3GB)"
    )
    model = None
    try:
        # Resolve the model folder ourselves (cache first, then download) so faster-whisper's
        # own downloader -- which breaks with some huggingface_hub versions
        # ("open() got an unexpected keyword argument 'metadata_errors'") -- is bypassed.
        _wh_src = "large-v3"
        try:
            from huggingface_hub import snapshot_download as _snap
            try:
                _wh_src = _snap(_wh_repo, local_files_only=True)
            except Exception:
                _wh_src = _snap(_wh_repo, local_files_only=False)
        except Exception:
            _wh_src = "large-v3"
        model = WhisperModel(
            _wh_src, device=device, compute_type=compute_type,
            cpu_threads=cpu_threads, num_workers=1,
        )
        language = WHISPER_LANG.get(source_language) if source_language else None
        raw_segments, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=(5 if device == "cuda" else 2),
            best_of=(5 if device == "cuda" else 2),
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 350, "speech_pad_ms": 150},
            condition_on_previous_text=False,
            temperature=[0.0, 0.2, 0.4],
            no_speech_threshold=0.6,
            word_timestamps=False,
        )
        output = []
        for sg in raw_segments:
            text = str(getattr(sg, "text", "") or "").strip()
            if not text:
                continue
            try:
                start = max(0.0, float(sg.start))
                end = max(start + 0.25, float(sg.end))
            except Exception:
                continue
            if output and output[-1][2].strip().lower() == text.lower():
                output[-1] = (output[-1][0], max(output[-1][1], end), output[-1][2])
            else:
                output.append((start, end, text))
        detected = str(getattr(info, "language", "") or "").lower()
        return output, detected, device
    except UserError:
        raise
    except Exception as e:
        _hint = ""
        if "metadata_errors" in str(e):
            _hint = (" | ដំណោះស្រាយ៖ កញ្ចប់ huggingface_hub/faster-whisper មិនត្រូវគ្នា។ "
                     "រត់៖ python -m pip install -U huggingface_hub faster-whisper  រួចបិទ-បើកកម្មវិធីឡើងវិញ។")
        raise RuntimeError(f"Whisper large-v3 Offline ស្តាប់មិនបាន: {e}{_hint}") from e
    finally:
        # Do not keep Whisper resident while the 3B translation model loads.
        try:
            del model
        except Exception:
            pass
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass


def _pick_by_budget(cands, budget):
    """Offline 'add/remove words': among beam candidates choose the Khmer line whose
    length best fits the speaking-time budget of the original character line."""
    best, best_score = None, None
    for rank, c in enumerate(cands):
        c = fix_khmer((c or "").strip())
        if not c or not has_khmer(c):
            continue
        n = len(c.replace(" ", ""))
        over = max(0, n - budget)
        under = max(0, int(budget * 0.6) - n)
        score = over * 1.0 + under * 0.5 + rank * 2
        if best_score is None or score < best_score:
            best, best_score = c, score
    return best


def _offline_madlad_translate(texts, status, budgets=None):
    """Local Chinese/multilingual -> Khmer translation using MADLAD-400 3B INT8 CT2."""
    if not texts:
        return []
    try:
        import ctranslate2
        import sentencepiece as spm
        from huggingface_hub import snapshot_download
    except Exception as e:
        raise UserError(
            "Offline Translator មិនទាន់ដំឡើងទេ។ ត្រូវការ ctranslate2, sentencepiece និង huggingface_hub។ "
            f"មូលហេតុ: {e}"
        )

    repo_id = "cstr/madlad400-3b-ct2-int8"
    status.write("🌏 Offline AI: កំពុងផ្ទុក MADLAD-400 3B INT8... (ទាញយកលើកដំបូងប្រហែល 3GB)")
    try:
        try:
            model_dir = snapshot_download(repo_id=repo_id, local_files_only=True)
        except Exception:
            model_dir = snapshot_download(repo_id=repo_id, local_files_only=False)
        sp_path = os.path.join(model_dir, "spiece.model")
        if not os.path.isfile(sp_path):
            raise RuntimeError("មិនឃើញ spiece.model ក្នុងឯកសារម៉ូដែល")
        sp = spm.SentencePieceProcessor(model_file=sp_path)
        device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        compute_type = "int8_float16" if device == "cuda" else "int8"
        translator = ctranslate2.Translator(
            model_dir, device=device, compute_type=compute_type,
            inter_threads=1, intra_threads=max(2, min(8, os.cpu_count() or 4)),
        )
        result = []
        batch_size = 32 if device == "cuda" else 12
        total = len(texts)
        for offset in range(0, total, batch_size):
            batch = [str(x or "").strip() for x in texts[offset:offset + batch_size]]
            source_tokens = [sp.encode("<2km> " + x, out_type=str) for x in batch]
            _beam = 5 if device == "cuda" else 4
            translated = translator.translate_batch(
                source_tokens,
                beam_size=_beam,
                num_hypotheses=_beam,
                max_decoding_length=192,
                length_penalty=1.0,
                repetition_penalty=1.15,
                no_repeat_ngram_size=4,
            )
            for _ri, row in enumerate(translated):
                hyp = row.hypotheses[0] if row.hypotheses else []
                value = fix_khmer(sp.decode(hyp).strip()) if hyp else ""
                _budget = budgets[offset + _ri] if budgets and (offset + _ri) < len(budgets) else None
                if _budget and row.hypotheses:
                    _cands = [sp.decode(h_).strip() for h_ in row.hypotheses if h_]
                    value = _pick_by_budget(_cands, _budget) or value
                if not value or not has_khmer(value):
                    raise RuntimeError("ម៉ូដែល MADLAD មិនបានបញ្ចេញអក្សរខ្មែរត្រឹមត្រូវសម្រាប់ឃ្លាមួយ")
                result.append(value)
            status.write(f"🌏 Offline AI: បកប្រែរួច {min(offset + len(batch), total)}/{total} ឃ្លា...")
        del translator, sp
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        return result
    except UserError:
        raise
    except Exception as e:
        raise RuntimeError(f"MADLAD-400 Offline បកប្រែមិនបាន: {e}") from e


def transcribe_offline(audio_path, duration, source_language, status, gender_fn=None, whisper_choice=None):
    """End-to-end local ASR + Khmer MT. Never calls an external inference API."""
    original, detected, _device = _offline_whisper_transcribe(audio_path, source_language, status, whisper_choice)
    if not original:
        raise UserError("Offline Whisper មិនរកឃើញសំឡេងនិយាយក្នុងវីដេអូនេះទេ។")
    if source_language == "Khmer" or detected in ("km", "khm"):
        khmer_segments = [(a, min(b, duration + 0.5), fix_khmer(t))
                          for a, b, t in original if has_khmer(t)]
        if not khmer_segments:
            raise UserError("Whisper មិនអាចស្តាប់អត្ថបទខ្មែរបានច្បាស់ទេ។")
        return khmer_segments, "Offline Whisper large-v3 (Khmer source)", 0

    source_segments = merge_for_translate(original, gender_fn=gender_fn)
    if not source_segments:
        raise UserError("មិនមានឃ្លាសម្រាប់បកប្រែទេ។")
    translated = _offline_madlad_translate([t for _, _, t in source_segments], status,
                                           budgets=lip_budgets(source_segments))
    if len(translated) != len(source_segments):
        raise RuntimeError("ចំនួនឃ្លាបកប្រែមិនត្រូវនឹងឃ្លាដើម។")
    output = []
    for (start, end, _source), khmer in zip(source_segments, translated):
        khmer = fix_khmer(khmer)
        if khmer:
            output.append((start, min(end, duration + 0.5), khmer))
    if len(output) != len(source_segments):
        raise RuntimeError("Offline AI បកប្រែមិនបានគ្រប់ឃ្លា ដើម្បីការពារកុំឱ្យបាត់សំឡេង/អត្ថបទ។")
    output.sort(key=lambda x: x[0])
    return output, "Offline Whisper large-v3 + MADLAD-400 3B INT8", 0


_OFF_EMO_KEYWORDS = [
    ("angry", ("ស្អប់", "ខឹង", "ឆ្កួត", "ចោទ", "កុហក", "អាក្រក់", "ហ៊ានម៉េច", "ស្លាប់ទៅ", "ឈប់!")),
    ("fear", ("ខ្លាច", "ជួយផង", "កុំ!", "គ្រោះថ្នាក់", "រត់ទៅ", "ភ័យ")),
    ("sad", ("សុំទោស", "ស្រណោះ", "ឈឺចាប់", "យំ", "ឯកា", "ចាកចេញ", "ស្លាប់", "ខកចិត្ត", "សោកស្តាយ")),
    ("happy", ("សប្បាយ", "អរគុណ", "ស្រលាញ់", "ល្អណាស់", "ជោគជ័យ", "ហាហា", "អបអរ")),
    ("surprised", ("ហ៊ាះ", "មិនអាចទៅរួច", "ម៉េចក៏", "ពិតមែន", "ទេ?!")),
    ("worried", ("បារម្ភ", "ព្រួយ", "ប្រយ័ត្ន", "ប្រុងប្រយ័ត្ន", "មិនអីទេ")),
    ("tender", ("ទូលបង្គំ", "កូនសម្លាញ់", "សម្លាញ់", "អូន", "បងសូម", "សូមមេត្តា")),
]


def offline_emotion_labels(texts):
    """គ្មាន API៖ ទាយអារម្មណ៍ពីអក្សរខ្មែរ (សញ្ញា ! ? ... និងពាក្យគន្លឹះ) → [(label, intensity)]។"""
    out = []
    for t in texts:
        t = str(t or "")
        label, inten = "neutral", 0.0
        for lab, words in _OFF_EMO_KEYWORDS:
            if any(w in t for w in words):
                label, inten = lab, 0.7
                break
        n_ex = t.count("!") + t.count("！")
        if n_ex >= 2 and label in ("neutral", "angry"):
            label, inten = ("angry" if label == "angry" else "shout"), 0.9
        elif n_ex == 1 and label == "neutral":
            label, inten = "excited", 0.6
        elif ("?" in t or "？" in t) and label == "neutral":
            label, inten = "surprised", 0.4
        elif ("..." in t or "…" in t) and label == "neutral":
            label, inten = "sad", 0.4
        out.append((label, inten))
    return out


_VOX_STYLE = {
    "happy": "cheerful, warm and bright tone",
    "excited": "excited, energetic, lively voice",
    "angry": "angry, forceful, intense voice",
    "sad": "sad, sorrowful, slow and soft voice",
    "fear": "frightened, trembling, breathy voice",
    "whisper": "whispering softly, intimate",
    "shout": "shouting loudly with strong emotion",
    "tender": "tender, gentle and affectionate voice",
    "surprised": "surprised, expressive rising intonation",
    "worried": "worried, anxious, uneasy tone",
    "sarcastic": "sarcastic, teasing tone",
}


def vox_style_prefix(label, intensity):
    """បង្កើតការណែនាំរចនាប័ទ្មសម្រាប់ VoxCPM2 ក្នុងវង់ក្រចក (បុរាណ៖ '(angry voice)អត្ថបទ')។"""
    desc = _VOX_STYLE.get(label)
    if not desc or float(intensity or 0) < 0.25:
        return ""
    strength = "very " if float(intensity) >= 1.1 else ("slightly " if float(intensity) < 0.6 else "")
    return f"({strength}{desc})"


def _get_offline_voxcpm_model():
    global _OFFLINE_VOXCPM_MODEL
    with _OFFLINE_TTS_LOCK:
        if _OFFLINE_VOXCPM_MODEL is None:
            try:
                from voxcpm import VoxCPM
            except Exception as e:
                raise UserError(
                    "Offline Khmer Voice មិនទាន់ដំឡើងទេ។ ត្រូវការ voxcpm, PyTorch >= 2.5 និង soundfile។ "
                    f"មូលហេតុ: {e}"
                )
            if not (3, 10) <= sys.version_info[:2] <= (3, 12):
                raise UserError("VoxCPM2 ត្រូវការ Python 3.10–3.12។ សូមប្រើ Python 3.11 ដូច Environment របស់អ្នក។")
            try:
                import torch
                _dev = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                _dev = "cpu"
            try:
                from huggingface_hub import snapshot_download
                try:
                    _voxcpm_path = snapshot_download("openbmb/VoxCPM2", local_files_only=True)
                except Exception:
                    _voxcpm_path = snapshot_download("openbmb/VoxCPM2", local_files_only=False)
            except Exception as e:
                raise UserError(f"ទាញយក VoxCPM2 Model មិនបាន៖ {e}") from e
            _OFFLINE_VOXCPM_MODEL = VoxCPM.from_pretrained(
                _voxcpm_path,
                device=_dev,
                optimize=False,
                load_denoiser=False,
            )
        return _OFFLINE_VOXCPM_MODEL


def offline_voxcpm_synthesize(text, output_wav, reference_wav=None, style=""):
    """Generate Khmer speech locally; optional reference audio clones one character's voice."""
    try:
        import soundfile as sf
    except Exception as e:
        raise UserError(f"មិនទាន់ដំឡើង soundfile: {e}")
    with _OFFLINE_TTS_LOCK:
        model = _get_offline_voxcpm_model()
        clean = (style or "") + tts_clean(text)
        try:
            import torch
            _steps = 12 if torch.cuda.is_available() else 8
        except Exception:
            _steps = 8
        if reference_wav and os.path.isfile(reference_wav):
            wav = model.generate(
                text=clean,
                reference_wav_path=reference_wav,
                cfg_value=2.0,
                inference_timesteps=_steps,
            )
        else:
            wav = model.generate(
                text=clean,
                cfg_value=2.0,
                inference_timesteps=_steps,
            )
        sf.write(output_wav, wav, model.tts_model.sample_rate)
    return os.path.isfile(output_wav) and os.path.getsize(output_wav) > 1000


def _release_offline_voxcpm_model():
    """Free the large local TTS model after one video to leave RAM for queued models."""
    global _OFFLINE_VOXCPM_MODEL
    with _OFFLINE_TTS_LOCK:
        model = _OFFLINE_VOXCPM_MODEL
        _OFFLINE_VOXCPM_MODEL = None
        try:
            del model
        except Exception:
            pass
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def run_worker(job, item, settings, fonts_data):
    _API_LOCAL.isolated = True
    _API_LOCAL.xk_cfg = tuple(settings.get("user_xk_cfg") or ("", "", ""))
    rep = Reporter(item)
    item["stage"] = "ក្នុងជួររង់ចាំ..."
    _seq = item.get("seq")
    if _seq is not None:
        # ចាប់ផ្តើមតាមលំដាប់លំដោយ: ផ្នែកទី១ មុន រួចផ្នែកទី២ ...
        with job.turn_cv:
            while job.turn != _seq:
                job.turn_cv.wait(timeout=5)
    _PIPELINE_SLOTS.acquire()
    if _seq is not None:
        with job.turn_cv:
            job.turn = _seq + 1
            job.turn_cv.notify_all()
    item["t0"] = time.time()
    item["state"] = "running"
    _offline_lock_acquired = False
    try:
        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, "input.mp4")
            audio_path = os.path.join(folder, "audio.mp3")
            master_path = os.path.join(folder, "master.flac")
            if item.get("path"):
                shutil.move(item["path"], source)
                item["path"] = None
            else:
                item["pct"] = 0.03
                rep.write("កំពុងទាញយកវីដេអូ...")
                download_video(item["url"], source, rep)
            item["pct"] = 0.12
            rep.write("១/៤ កំពុងរៀបចំ...")
            fonts = install_fonts(folder, fonts_data)
            item["pct"] = 0.18
            rep.write("២/៤ កំពុងដកសំឡេង...")
            extract_audio(source, audio_path, master_path)
            duration, vid_w, vid_h = probe_media(source)
            if duration > MAX_DURATION_MIN * 60:
                raise UserError(f"វីដេអូវែងពេក។ សូមប្រើវីដេអូខ្លីជាង {MAX_DURATION_MIN} នាទី។")
            speech = detect_speech(master_path, duration)
            analysis_pool = None
            analysis_future = None
            if (duration <= 600
                    and (settings["auto_gender"]
                         or (settings["dub_on"] and (settings["voice_match"] or settings["emotion"] or settings.get("timbre"))))):
                analysis_pool = ThreadPoolExecutor(max_workers=1)
                def _analyze():
                    pcm_ = load_pcm(master_path)
                    return pcm_, pitch_track(pcm_)
                analysis_future = analysis_pool.submit(_analyze)
            _smap_cache = {}

            def get_smap():
                """ផែនទីអ្នកនិយាយ (ប្រុស/ស្រី) សាងសង់ម្តងគត់ ពីការវិភាគ pitch ដែលរត់ស្របពេលស្តាប់សំឡេង។"""
                if "v" not in _smap_cache:
                    v_ = None
                    if analysis_future is not None and settings["auto_gender"]:
                        try:
                            _pcm_, _trk_ = analysis_future.result()
                            v_ = build_speaker_map(_trk_, duration, settings["voice"])
                        except Exception:
                            v_ = None
                    _smap_cache["v"] = v_
                return _smap_cache["v"]

            def _gender_fn(a_, b_):
                sm_ = get_smap()
                return sm_.gender_at(a_, b_) if sm_ is not None else None

            item["pct"] = 0.25
            rep.write("៣/៤ កំពុងស្តាប់ និងបកប្រែជាភាសាខ្មែរ...")
            segments = None
            used_engine = ""
            used_model = ""
            failed_chunks = 0
            engine_errors = []
            if settings.get("offline_on"):
                # Keep large offline models from colliding in RAM/VRAM when several videos are queued.
                rep.write("🔒 Offline AI កំពុងរង់ចាំម៉ូដែលទំនេរ...")
                _OFFLINE_JOB_LOCK.acquire()
                _offline_lock_acquired = True
                segments, used_model, failed_chunks = transcribe_offline(
                    audio_path, duration, settings["language"], rep, gender_fn=_gender_fn,
                    whisper_choice=settings.get("offline_whisper"),
                )
                used_engine = "offline"
            else:
                order = ["free"] if settings["groq_key"] else []
                for idx, engine in enumerate(order):
                    try:
                        if engine == "free":
                            segments, used_model, failed_chunks = transcribe_free(settings["groq_key"], audio_path, duration, settings["language"], rep, speech=speech, dub=settings["dub_on"], gemini_key=settings["gemini_key"], keep_failed=False, gender_fn=_gender_fn)
                        else:
                            raise RuntimeError("ម៉ាស៊ីនសម្គាល់សំឡេងនេះត្រូវបានបិទ។")
                        used_engine = engine
                        break
                    except UserError:
                        raise
                    except Exception as e:
                        reason = f"{engine_name(engine)}: {str(e)[:400]}"
                        engine_errors.append(reason)
                        if idx + 1 < len(order):
                            item["warn"].append("ម៉ាស៊ីនទីមួយមានបញ្ហា កម្មវិធីបានប្តូរទៅម៉ាស៊ីនបម្រុងដោយស្វ័យប្រវត្តិ។" f"\n\nមូលហេតុ → {reason}")
                            rep.write("កំពុងប្តូរទៅម៉ាស៊ីនបម្រុង...")
                if segments is None:
                    raise UserError("ម៉ាស៊ីនបកប្រែទាំងអស់បរាជ័យ។\n\n" + "\n\n".join(engine_errors))
            if failed_chunks:
                item["warn"].append("ផ្នែកខ្លះនៃវីដេអូមិនអាចបកប្រែបាន។ សូមសាកម្តងទៀតពេលក្រោយ។")
            item["pct"] = 0.55
            segments = snap_segments(segments, speech, duration)
            if settings.get("review_on"):
                item["pct"] = 0.56
                _sm_r = get_smap()
                _gens_r = [(_sm_r.gender_at(a_, b_) if _sm_r is not None else None) for a_, b_, _t_ in segments]
                segments = review_segments_wait(item, segments, genders=_gens_r)
                _forced_r = item.pop("forced_voices", None)
                if _forced_r:
                    if get_smap() is None:
                        _smap_cache["v"] = SpeakerMap()
                    get_smap().set_overrides(_forced_r)
                rep.write("កំពុងបន្តជាមួយអក្សរដែលអ្នកបានកែ...")
            captions, sync_mode = build_captions(segments, duration)
            if not captions:
                raise UserError("រកមិនឃើញសំឡេងនិយាយក្នុងវីដេអូនេះទេ។")
            _title_box = {}
            _title_thread = None
            if not settings.get("offline_on"):
                def _do_titles():
                    try:
                        _title_box["v"] = suggest_titles([t_ for _, _, t_ in segments], settings["groq_key"])
                    except Exception:
                        _title_box["v"] = []
                _title_thread = threading.Thread(target=_do_titles, daemon=True)
                _title_thread.start()   # ស្នើចំណងជើងស្របពេល dubbing/render មិនបន្ថែមពេល
            dub_ok = False
            if settings["dub_on"]:
                item["pct"] = 0.6
                rep.write("🎙 កំពុងបង្កើតសំឡេងខ្មែរ...")
                try:
                    client = None
                    dub_model = used_model
                    _sm_d = get_smap()
                    dub_segments = merge_for_dub(segments, gender_fn=(_sm_d.gender_at if _sm_d is not None else None))
                    _emo_box = {}
                    _emo_thread = None
                    if settings["emotion"] and settings.get("offline_on"):
                        _emo_box["v"] = offline_emotion_labels([sg_[2] for sg_ in dub_segments])
                    elif settings["emotion"]:
                        def _do_emo(_segs=dub_segments):
                            try:
                                _emo_box["v"] = label_emotions([sg_[2] for sg_ in _segs], settings["groq_key"], settings["gemini_key"])
                            except Exception:
                                _emo_box["v"] = None
                        _emo_thread = threading.Thread(target=_do_emo, daemon=True)
                        _emo_thread.start()   # វិភាគអារម្មណ៍ស្របពេលវិភាគសំឡេង មិនរង់ចាំគ្នា
                    seg_voices = None
                    targets = None
                    emotions = None
                    voice_notes = []
                    pitch_inf = None
                    runs_ = None
                    ref_bands = None
                    seg_char = None
                    char_bands = None
                    clone_ref_paths = []
                    clone_ref_names = []
                    need_audio = (settings["auto_gender"] or settings["voice_match"] or settings["emotion"] or settings.get("timbre"))
                    if need_audio:
                        try:
                            rep.write("🔍 កំពុងវិភាគសំឡេងអ្នកនិយាយដើម...")
                            if analysis_future is not None:
                                pcm, tracks = analysis_future.result()
                            else:
                                pcm = load_pcm(master_path)
                                tracks = pitch_track(pcm)
                            pitch_inf = {"times": tracks[0], "f0": tracks[1], "rms": tracks[2]}
                            if settings["auto_gender"]:
                                try:
                                    runs_, _info = gender_timeline(pcm, duration, settings["voice"], tracks=tracks)
                                    if runs_ is not None:
                                        seg_voices = voices_from_map(get_smap(), dub_segments, settings["voice"], runs_)
                                        voice_notes = voice_notes + [f"🗣 ប្រុស {sum(1 for v_ in seg_voices if v_ == VOICE_MALE)} / ស្រី {sum(1 for v_ in seg_voices if v_ == VOICE_FEMALE)} ឃ្លា"]
                                except Exception:
                                    seg_voices = None
                                    runs_ = None
                            if settings["voice_match"]:
                                targets = compute_targets(dub_segments, seg_voices, pitch_inf, runs_)
                            if settings.get("timbre_samples"):
                                import numpy as np
                                chars_raw_ = []
                                refs_raw_ = []
                                names_raw_ = []
                                _sample_names = settings.get("timbre_names") or []
                                for _n_, _raw_ in enumerate(settings["timbre_samples"]):
                                    try:
                                        _sp = os.path.join(folder, f"timbre_{_n_}.wav")
                                        with open(_sp, "wb") as _f:
                                            _f.write(_raw_)
                                        _pc = load_pcm(_sp)
                                        _t_, _f0_, _r_ = pitch_track(_pc)
                                        _vv = _f0_[_f0_ > 0]
                                        _med = float(np.median(_vv)) if len(_vv) >= 25 else None
                                        chars_raw_.append({"f0": _med, "bands": band_levels(_pc), "n": _n_ + 1})
                                        refs_raw_.append(_sp)
                                        names_raw_.append(str(_sample_names[_n_]) if _n_ < len(_sample_names) else f"តួអង្គ {_n_ + 1}")
                                    except Exception:
                                        continue
                                _pc = None
                                valid_chars_ = [(c_, r_, nm_) for c_, r_, nm_ in zip(chars_raw_, refs_raw_, names_raw_) if c_["f0"]]
                                chars_ = [x_[0] for x_ in valid_chars_]
                                clone_ref_paths = [x_[1] for x_ in valid_chars_]
                                clone_ref_names = [x_[2] for x_ in valid_chars_]
                                if len(chars_) < len(settings["timbre_samples"]):
                                    item["warn"].append("សំឡេងគំរូខ្លះមិនអាចវាស់ pitch បាន (ខ្លី ឬមិនច្បាស់) ត្រូវបានរំលង។")
                                if chars_:
                                    seg_voices, targets, seg_char, char_bands, _cn = assign_characters(
                                        dub_segments, chars_, pitch_inf, names=clone_ref_names
                                    )
                                    voice_notes = voice_notes + _cn
                            pcm = None
                            ref_pcm = None
                            tracks = None
                            gc.collect()
                        except Exception:
                            dub_segments = merge_for_dub(segments)
                            seg_voices = None
                            targets = None
                            voice_notes = []
                            pitch_inf = None
                            runs_ = None
                            seg_char = None
                            char_bands = None
                            clone_ref_paths = []
                            clone_ref_names = []
                            item["warn"].append("វិភាគសំឡេងអ្នកនិយាយមិនបាន ប្រើសំឡេងតែមួយតាមដែលបានជ្រើស។")
                    if seg_voices is None:
                        _smf = get_smap()
                        if _smf is not None and (_smf.over or _smf.mode != "none"):
                            seg_voices = voices_from_map(_smf, dub_segments, settings["voice"], None)
                    if settings["emotion"]:
                        try:
                            rep.write("🎭 កំពុងវិភាគអារម្មណ៍...")
                            if _emo_thread is not None:
                                _emo_thread.join(timeout=30)   # យូរជាង ៣០វិ → ប្រើតែសំឡេងដើមវិភាគ មិនរង់ចាំទៀត
                            emotions, emo_lines = plan_emotions(dub_segments, seg_voices, pitch_inf, runs_, settings["groq_key"], settings["gemini_key"], labels=_emo_box.get("v"))
                            voice_notes = voice_notes + emo_lines
                        except Exception:
                            emotions = None
                            item["warn"].append("វិភាគអារម្មណ៍មិនបាន ប្រើសំឡេងធម្មតា។")
                    rep.write("🎙 កំពុងបង្កើតសំឡេងខ្មែរ...")
                    match_notes = []
                    dub_ok = make_dub(
                        folder, dub_segments, settings["voice"], duration, settings["keep_bg"], client, dub_model,
                        seg_voices=seg_voices, targets=targets, notes=match_notes, emotions=emotions,
                        groq_key=settings["groq_key"], ref_bands=ref_bands,
                        offset=float(settings.get("dub_offset", 0.0) or 0.0), tight=False,
                        hard_cut=bool(settings.get("tight_sync", True)), bg_vol=settings.get("bg_vol", 0.08),
                        seg_char=seg_char, char_bands=char_bands,
                        timbre_refs=clone_ref_paths, timbre_names=clone_ref_names,
                        clone_enabled=bool(settings.get("timbre_clone_enabled", False) and clone_ref_paths),
                        offline_voice=bool(settings.get("offline_on")),
                    )
                    item["voice_lines"] = match_notes + voice_notes
                except Exception as _dub_error:
                    dub_ok = False
                    if settings.get("offline_on"):
                        item["warn"].append("Offline Voice/TTS បង្កើតមិនបាន៖ " + str(_dub_error)[:350])
                if not dub_ok:
                    item["warn"].append("បង្កើតសំឡេងអានមិនបានទេ។ វីដេអូមានតែអក្សរ។")
            if settings.get("offline_on"):
                _release_offline_voxcpm_model()
                if _offline_lock_acquired:
                    _OFFLINE_JOB_LOCK.release()
                    _offline_lock_acquired = False
            if analysis_pool is not None:
                analysis_pool.shutdown(wait=False)
                analysis_future = None
            item["pct"] = 0.75
            rep.write("៤/៤ កំពុងរង់ចាំដាក់អក្សរចូលវីដេអូ...")
            with job.render_slots:
                item["pct"] = 0.82
                rep.write("៤/៤ កំពុងដាក់អក្សរចូលវីដេអូ...")
                out_path, used_font, ffmpeg_log, attempts = render_with_fonts(folder, fonts, captions, settings["font_size"], settings["outline_size"], settings["color"], vid_w, vid_h, settings["quality"], rep, dub=dub_ok, style=settings["style"], subs=settings["sub_on"], fx=settings.get("fx"))
            final_path = os.path.join(job.folder, f"out_{uuid.uuid4().hex[:8]}.mp4")
            shutil.move(out_path, final_path)
            item["video_path"] = final_path
            # Auto-save every finished video into a folder, numbered in the original order
            # (001_..., 002_...) no matter which one finishes first.
            try:
                _auto_dir = str(get_secret("AUTO_SAVE_DIR", "") or "").strip() or os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "Khmer_Output")
                os.makedirs(_auto_dir, exist_ok=True)
                _stem = os.path.splitext(str(item.get("name") or "video"))[0]
                _dest = os.path.join(_auto_dir, f"{int(item.get('seq', 0)) + 1:03d}_{safe_filename(_stem)}_khmer.mp4")
                if os.path.exists(_dest):
                    _dest = _dest[:-4] + f"_{uuid.uuid4().hex[:4]}.mp4"
                shutil.copy2(final_path, _dest)
                item["saved_to"] = _dest
                print(f"[AUTO-SAVE] {_dest}", flush=True)
            except Exception as _auto_e:
                _log_swallowed(_auto_e)
            out_size = os.path.getsize(final_path)
            if MOBILE_COPY and out_size > 40 * 1024 * 1024:
                try:
                    rep.write("📱 កំពុងបង្កើតកំណែតូចសម្រាប់ទូរស័ព្ទ...")
                    item["small_path"] = make_mobile_copy(final_path, os.path.join(job.folder, f"mobile_{uuid.uuid4().hex[:8]}.mp4"))
                except Exception:
                    item["small_path"] = None
            item["captions"] = [t for _, _, t in captions]
            # Title suggestions are optional; do not hold the finished video for up to 45 seconds.
            if _title_thread is not None:
                _title_thread.join(timeout=1.0)
            item["titles"] = _title_box.get("v") or []
            item["debug"] = {
                "ម៉ាស៊ីន": used_engine, "ម៉ូដែល": used_model,
                "ការតម្រឹម": sync_mode, "ផ្នែកបរាជ័យ": failed_chunks,
                "Font ដែលប្រើ": used_font, "Dubbing": dub_ok,
                "អ្នកនិយាយ": (item["voice_lines"][0] if item["voice_lines"] else ""),
                "ទំហំលទ្ធផល": f"{out_size / (1024 * 1024):.1f}MB",
                "ការសាក Font": "\n".join(attempts),
                "fontselect": "\n".join(line for line in ffmpeg_log.splitlines() if "fontselect" in line.lower())[:1500],
                "ម៉ោងអក្សរ": "\n".join(f"[{s:.1f}-{e:.1f}] {t}" for s, e, t in captions),
            }
            item["pct"] = 1.0
            item["stage"] = "រួចរាល់"
            item["elapsed"] = time.time() - item["t0"]
            item["state"] = "done"
    except Exception as error:
        item["error"] = friendly_message(error)
        item["raw_error"] = str(error)
        item["elapsed"] = time.time() - (item["t0"] or time.time())
        item["state"] = "error"
    finally:
        if item["state"] == "running":
            item["error"] = "ការបង្កើតវីដេអូមិនបានសម្រេច។ សូមសាកម្តងទៀត។"
            item["state"] = "error"
        try:
            if item.get("path") and os.path.exists(item["path"]):
                os.remove(item["path"])
        except Exception as _swallow_e:
            _log_swallowed(_swallow_e)
        if settings.get("offline_on"):
            _release_offline_voxcpm_model()
        if _offline_lock_acquired:
            try:
                _OFFLINE_JOB_LOCK.release()
            except Exception as _offline_release_error:
                _log_swallowed(_offline_release_error)
        _PIPELINE_SLOTS.release()
        gc.collect()


def review_segments_wait(item, segments, timeout=900, genders=None):
    """ផ្អាកដើម្បីឱ្យអ្នកប្រើកែអក្សរ Subtitle (ខ្មែរ) មុនបង្កើតសំឡេង និងដាក់ចូលវីដេអូ។"""
    ev = threading.Event()
    item["review_final"] = None
    item["review_final_genders"] = None
    item["review_genders"] = list(genders) if genders else [None] * len(segments)
    item["review_segments"] = [[float(a), float(b), str(t)] for a, b, t in segments]
    item["review_event"] = ev
    item["stage"] = "✏️ រង់ចាំអ្នកពិនិត្យ និងកែអក្សរ..."
    item["state"] = "review"
    _PIPELINE_SLOTS.release()   # ដោះជួរ ឱ្យវីដេអូផ្សេងធ្វើបានពេលរង់ចាំ
    try:
        got = ev.wait(timeout=timeout)
    finally:
        _PIPELINE_SLOTS.acquire()
    final = item.get("review_final")
    item["review_segments"] = None
    item["review_event"] = None
    item["review_final"] = None
    item["state"] = "running"
    if not got or not final:
        return segments
    out = []
    forced = []
    picks = item.get("review_final_genders") or []
    for k_, (a, b, t) in enumerate(final):
        t = fix_khmer(t)
        if t:
            out.append((float(a), float(b), t))
            g_ = picks[k_] if k_ < len(picks) else None
            if g_ in ("M", "F"):
                forced.append((float(a), float(b), g_))
    item["forced_voices"] = forced
    item["review_genders"] = None
    item["review_final_genders"] = None
    return out or segments


def build_zip(items, folder):
    ok = [it for it in items if it["state"] == "done" and it.get("video_path")]
    if len(ok) < 2:
        return None
    total = sum(os.path.getsize(it["video_path"]) for it in ok if os.path.isfile(it["video_path"]))
    if total > MAX_ZIP_MB * 1024 * 1024:
        return None
    zip_path = os.path.join(folder, "khmer_videos.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as z:
        for i, it in enumerate(ok, start=1):
            if os.path.isfile(it["video_path"]):
                z.write(it["video_path"], f"{i:02d}_{safe_filename(it['name'])}_khmer.mp4")
    return zip_path


def _video_size_and_audio(path):
    """ត្រឡប់ (width, height, has_audio) តាម ffmpeg -i។"""
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    r = subprocess.run([exe, "-i", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    err = r.stderr or ""
    w = h = 0
    m = re.search(r"Video:.*?,\s*(\d{2,5})x(\d{2,5})", err)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
    return w, h, ("Audio:" in err)


def build_merged(items, folder):
    """រួមវីដេអូដែលធ្វើរួចទាំងអស់ (តាមលំដាប់) ជាវីដេអូតែមួយ។ ត្រឡប់ path ឬ None។"""
    ok = [it for it in items if it["state"] == "done" and it.get("video_path")
          and os.path.isfile(it["video_path"])]
    if len(ok) < 2:
        return None
    try:
        paths = [it["video_path"] for it in ok]
        sizes = [_video_size_and_audio(p) for p in paths]
        W, H = sizes[0][0] or 720, sizes[0][1] or 1280
        W -= W % 2
        H -= H % 2
        out = os.path.join(folder, "khmer_merged.mp4")
        args = []
        for p in paths:
            args += ["-i", p]
        parts = []
        for i, (_w, _h, has_a) in enumerate(sizes):
            parts.append(
                f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[v{i}]"
            )
            if has_a:
                parts.append(f"[{i}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]")
            else:
                parts.append(f"anullsrc=r=44100:cl=stereo,atrim=duration=0.1[a{i}]")
        n = len(paths)
        concat_in = "".join(f"[v{i}][a{i}]" for i in range(n))
        parts.append(f"{concat_in}concat=n={n}:v=1:a=1[outv][outa]")
        args += ["-filter_complex", ";".join(parts), "-map", "[outv]", "-map", "[outa]",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                 "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out]
        run_ffmpeg(args)
        return out if os.path.isfile(out) else None
    except Exception:
        return None


class _NoProgress:
    def progress(self, *a, **k):
        pass

    def write(self, *a, **k):
        pass


def extract_links(text):
    """ទាញតំណ http/https ទាំងអស់ពីអត្ថបទ (បំបែកដោយបន្ទាត់ ដកឃ្លា ឬក្បៀស ក៏បាន) ហើយលុបតំណស្ទួន។"""
    found = re.findall(r"https?://[^\s<>\"'\u3000\uff0c\u3002]+", text or "", flags=re.I)
    out = []
    for u in found:
        u = u.rstrip(".,;:!?)]}\u00bb\u17d4")
        if len(u) > 10 and u not in out:
            out.append(u)
    return out


LINK_RETRIES = _env_int("LINK_RETRIES", 4)   # ចំនួនលើកព្យាយាមអតិបរមាក្នុងមួយតំណ


def _fetch_one(url, on_try=None):
    """ទាញវីដេអូមួយតំណ ហើយព្យាយាមម្តងទៀតដោយស្វ័យប្រវត្តិរហូតរកឃើញ (មិនប៉ះ st.session_state)។"""
    last = ""
    for attempt in range(1, LINK_RETRIES + 1):
        if on_try:
            try:
                on_try(attempt)
            except Exception as _swallow_e:
                _log_swallowed(_swallow_e)
        folder = tempfile.mkdtemp(prefix="kac_link_")
        path = os.path.join(folder, "video.mp4")
        try:
            download_video(url, path, _NoProgress())
            return {"path": path, "ok": True, "tries": attempt}
        except Exception as e:
            shutil.rmtree(folder, ignore_errors=True)
            last = re.sub(r"https?://\S+", "[link]", str(e) or type(e).__name__)[:600]
            if attempt < LINK_RETRIES:
                time.sleep(min(2 * attempt, 8))
    return {"path": None, "ok": False, "err": last, "tries": LINK_RETRIES}


def fetch_link_preview(url):
    """ទាញវីដេអូពីតំណមកទុកជាមុន (ដើម្បីបង្ហាញ មើល ទាញយក និងបកប្រែ)។"""
    cache = st.session_state.setdefault("link_cache", {})
    ent = cache.get(url)
    if ent is None:
        ent = _fetch_one(url)
        cache[url] = ent
    return ent


def fetch_links_preview(urls, status=None):
    """រកតំណម្តងមួយៗតាមលំដាប់ (ទី១ រួចទី២ ...) តំណណារកមិនឃើញ ព្យាយាមម្តងទៀតរហូតរកឃើញ ទើបទៅតំណបន្ទាប់។"""
    cache = st.session_state.setdefault("link_cache", {})
    for u in [u for u in urls if u not in cache]:
        num = urls.index(u) + 1

        def _cb(attempt, num=num):
            if status is not None:
                status.info(f"⏳ កំពុងរកវីដេអូទី {num} / {len(urls)} · ព្យាយាមលើកទី {attempt}/{LINK_RETRIES}")

        cache[u] = _fetch_one(u, _cb)
    return {u: cache[u] for u in urls}


SPLIT_SECONDS = 6 * 60   # លំនាំដើម: បំបែកវីដេអូជាផ្នែកប្រវែង ៦ នាទី
SPLIT_PRESETS = {
    "៣០ វិនាទី": 30, "១ នាទី": 60, "២ នាទី": 120, "៣ នាទី": 180,
    "៥ នាទី": 300, "៦ នាទី": 360, "១០ នាទី": 600, "១៥ នាទី": 900,
}
SPLIT_QUEUE_MAX = 10 ** 9   # គ្មានកំណត់ដោយ App: ផ្ញើគ្រប់ផ្នែកទៅបកប្រែ


def get_split_seconds():
    """ប្រវែងមួយផ្នែក (វិនាទី) តាមការកំណត់ក្នុងផ្ទាំងវីដេអូ។ 0 = មិនបំបែក។"""
    if not st.session_state.get("auto_split_toggle", True):
        return 0
    return SPLIT_PRESETS.get(st.session_state.get("split_len_pick"), SPLIT_SECONDS)


def fmt_len(sec):
    sec = int(sec)
    return f"{sec // 60} នាទី" if sec >= 60 and sec % 60 == 0 else f"{sec} វិនាទី"


def fmt_clock(sec):
    sec = int(round(sec))
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def link_or_copy(src, dst):
    """បង្កើត hard link (លឿន មិនចំណាយទំហំថ្មី) បើមិនបានទើបចម្លង។"""
    try:
        os.link(src, dst)
    except Exception:
        shutil.copyfile(src, dst)


LOCAL_VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".avi", ".webm")


def resolve_local_videos(text):
    """ទទួលផ្លូវឯកសារ/ថតពីក្នុងម៉ាស៊ីនផ្ទាល់ (មួយបន្ទាត់ ១) → (បញ្ជីវីដេអូដែលមាន, បញ្ជីផ្លូវខុស)។ មិនអានវីដេអូចូល RAM ទេ។"""
    files, bad, seen = [], [], set()
    for raw in str(text or "").splitlines():
        pth = raw.strip().strip('"').strip("'").strip()
        if not pth:
            continue
        pth = os.path.expanduser(pth)
        if os.path.isdir(pth):
            try:
                names = sorted(os.listdir(pth), key=lambda x: x.lower())
            except OSError:
                bad.append(raw.strip())
                continue
            cands = [os.path.join(pth, nm) for nm in names if nm.lower().endswith(LOCAL_VIDEO_EXTS)]
            if not cands:
                bad.append(raw.strip())
            for c in cands:
                if os.path.isfile(c) and c not in seen:
                    seen.add(c); files.append(c)
        elif os.path.isfile(pth) and pth.lower().endswith(LOCAL_VIDEO_EXTS):
            if pth not in seen:
                seen.add(pth); files.append(pth)
        else:
            bad.append(raw.strip())
    return files, bad


def _local_browse_cb():
    """បើកប្រអប់ជ្រើសឯកសាររបស់ Windows/Mac (ដំណើរការតែពេលកម្មវិធីរត់លើកុំព្យូទ័រខ្លួនឯង)។"""
    if getattr(sys, "frozen", False):
        st.session_state["_local_browse_err"] = True
        return
    code = (
        "import tkinter as tk\nfrom tkinter import filedialog\n"
        "r = tk.Tk(); r.withdraw(); r.attributes('-topmost', True)\n"
        "fs = filedialog.askopenfilenames(title='Choose videos', filetypes=[('Video', '*.mp4 *.mov *.mkv *.avi *.webm'), ('All', '*.*')])\n"
        "import sys\nsys.stdout.buffer.write('\\n'.join(fs).encode('utf-8'))\n"
    )
    try:
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=600).stdout.decode("utf-8", "ignore")
        paths = [x.strip() for x in out.splitlines() if x.strip()]
        if paths:
            st.session_state["local_path_text"] = "\n".join(paths)
        st.session_state["_local_browse_err"] = False
    except Exception as _e:
        _log_swallowed(_e)
        st.session_state["_local_browse_err"] = True


def cut_clips(src, folder, prefix, seg_seconds, exact=False):
    """កាត់វីដេអូជាផ្នែកប្រវែង seg_seconds។
    លំនាំដើម: កាត់ដោយមិន encode (លឿន) ហើយបើបរាជ័យ ប្តូរទៅ encode ឡើងវិញដោយស្វ័យប្រវត្តិ។
    exact=True: encode ឡើងវិញជានិច្ច ដើម្បីកាត់ឱ្យចំពេលវេលា។
    ត្រឡប់បញ្ជីឯកសារតាមលំដាប់ (អាចទទេ)។"""
    seg = max(5, int(seg_seconds))
    pattern = os.path.join(folder, f"{prefix}%03d.mp4")

    def _list():
        out = sorted(os.path.join(folder, fn) for fn in os.listdir(folder)
                     if fn.startswith(prefix) and fn.endswith(".mp4"))
        return [pp for pp in out if os.path.getsize(pp) > 1000]

    def _clean():
        for fn in os.listdir(folder):
            if fn.startswith(prefix) and fn.endswith(".mp4"):
                try:
                    os.remove(os.path.join(folder, fn))
                except OSError:
                    pass

    base = ["-i", src, "-map", "0:v:0", "-map", "0:a:0?"]
    tail = ["-f", "segment", "-segment_time", str(seg), "-reset_timestamps", "1", pattern]
    copy_args = base + ["-c", "copy"] + tail
    enc_args = base + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "128k",
                       "-force_key_frames", f"expr:gte(t,n_forced*{seg})"] + tail
    for args in ([enc_args] if exact else [copy_args, enc_args]):
        _clean()
        try:
            run_ffmpeg(args)
        except Exception:
            continue
        parts = _list()
        if parts:
            return parts
    return []


def split_video_parts(src, folder, idx, seg_seconds=None, exact=False):
    """បំបែកវីដេអូវែងជាផ្នែកខ្លីៗ ត្រឡប់បញ្ជីផ្លូវឯកសារតាមលំដាប់ ឬ None បើមិនចាំបាច់/បរាជ័យ។"""
    seg = int(seg_seconds or SPLIT_SECONDS)
    try:
        duration, _w, _h = probe_media(src)
    except Exception:
        return None
    if duration <= seg + 20:
        return None
    parts = cut_clips(src, folder, f"part_{idx}_", seg, exact)
    return parts if len(parts) > 1 else None


def drop_link_cache(keep=()):
    cache = st.session_state.get("link_cache", {})
    for k in list(cache.keys()):
        if k not in keep:
            ent = cache.pop(k)
            if ent.get("path"):
                shutil.rmtree(os.path.dirname(ent["path"]), ignore_errors=True)


def _request_origin():
    """ទាញយក origin (https://host) និង User-Agent របស់អ្នកប្រើ ដើម្បីបង្កើតតំណពេញលេញ។"""
    try:
        h = st.context.headers
        host = h.get("X-Forwarded-Host") or h.get("Host") or ""
        proto = (h.get("X-Forwarded-Proto") or "").split(",")[0].strip()
        ua = h.get("User-Agent") or ""
        if host:
            _host0 = host.split(",")[0].strip()
            if not proto:
                # ម៉ាស៊ីនក្នុងកុំព្យូទ័រ (exe/localhost) ប្រើ http មិនមែន https ទេ
                _hn = _host0.split(":")[0].lower()
                local = _hn in ("localhost", "127.0.0.1", "0.0.0.0") or _hn.startswith(("192.168.", "10.", "172."))
                proto = "http" if local else "https"
            return f"{proto}://{_host0}", ua
        origin = h.get("Origin") or ""
        return origin, ua
    except Exception:
        return "", ""


def browser_dl_link(label, path, file_name, mime, key):
    """ប៊ូតុងទាញយកដែលលោតចេញទៅបើកក្នុង Browser ពិតប្រាកដ (មិនទាញក្នុង webview/app)។
    Android: ប្រើ intent:// បើក Chrome ផ្ទាល់ · iPhone: តំណពេញលេញ + Chrome/Safari។"""
    try:
        from streamlit.runtime import get_instance
        mgr = get_instance().media_file_mgr
        coord = f"khmer_browser_dl_{key}"
        try:
            url = mgr.add(path, mime, coord, file_name=file_name, is_for_static_download=True)
        except TypeError:
            url = mgr.add(path, mime, coord, file_name=file_name)
        if not url:
            return False
        import html as _html, urllib.parse as _up
        origin, ua = _request_origin()
        url = str(url)
        full = url if url.startswith("http") else (origin + url if origin else url)
        low = ua.lower()
        href = full
        if full.startswith("http") and "android" in low:
            rest = full.split("://", 1)[1]
            fb = _up.quote(full, safe="")
            href = f"intent://{rest}#Intent;scheme=https;package=com.android.chrome;S.browser_fallback_url={fb};end"
        elif full.startswith("http") and ("iphone" in low or "ipad" in low):
            href = "googlechromes://" + full.split("://", 1)[1]
        st.markdown(
            f'<a href="{_html.escape(href, quote=True)}" target="_blank" rel="noopener noreferrer" '
            'style="display:block;text-align:center;padding:0.65rem 1rem;border-radius:0.6rem;'
            'font-weight:600;text-decoration:none;color:#fff;margin:0.25rem 0;'
            'background:linear-gradient(90deg,#ff1493,#8a2be2,#00bfff);">'
            f'{_html.escape(label)}</a>',
            unsafe_allow_html=True,
        )
        if href != full:
            st.markdown(
                f'<div style="text-align:center;font-size:0.8rem;opacity:.8;margin-bottom:.3rem;">'
                f'បើមិនបើក៖ <a href="{_html.escape(full, quote=True)}" target="_blank" rel="noopener noreferrer">'
                'ចុចទីនេះ (តំណផ្ទាល់)</a></div>',
                unsafe_allow_html=True,
            )
        return True
    except Exception:
        return False


def dl_button(label, data, file_name, mime, key, **kwargs):
    if ST_VER >= (1, 43):
        return st.download_button(label, data=data, file_name=file_name, mime=mime, key=key, on_click="ignore", **kwargs)
    return st.download_button(label, data=data, file_name=file_name, mime=mime, key=key, **kwargs)


KM_UNITS = ["", "មួយ", "ពីរ", "បី", "បួន", "ប្រាំ", "ប្រាំមួយ", "ប្រាំពីរ", "ប្រាំបី", "ប្រាំបួន"]
KM_TENS = {1: "ដប់", 2: "ម្ភៃ", 3: "សាមសិប", 4: "សែសិប", 5: "ហាសិប",
           6: "ហុកសិប", 7: "ចិតសិប", 8: "ប៉ែតសិប", 9: "កៅសិប"}
ANN_VOICE = "km-KH-SreymomNeural"
_ANN_CACHE = {}


def khmer_number_word(n):
    n = int(n)
    if n <= 0 or n >= 100:
        return str(n)
    t, u = divmod(n, 10)
    return (KM_TENS[t] if t else "") + KM_UNITS[u]


def done_announcement_b64(n):
    """សំឡេងខ្មែរប្រកាសថាវីដេអូទី n បានធ្វើរួច (mp3 → base64) ។ រក្សាទុកក្នុង cache។"""
    text = f"វីដេអូទី{khmer_number_word(n)} បានធ្វើរួចហើយ។ អ្នកស្រី លោកម្ចាស់ អាចដោនឡូតបានហើយ។"
    if text in _ANN_CACHE:
        return _ANN_CACHE[text]
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        if not tts_retry(text, ANN_VOICE, path, tries=3):
            return None
        with open(path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    _ANN_CACHE[text] = b64
    return b64


def announce_html(ann_id, b64):
    """លេងសំឡេងដោយស្វ័យប្រវត្តិ (ប្រើ Audio របស់ទំព័រមេ ដូច្នេះមិនដាច់ពេល element ត្រូវ refresh) ។
    បើ browser ហាមលេងស្វ័យប្រវត្តិ នឹងបង្ហាញប៊ូតុង «🔊» ឱ្យចុច។"""
    return """<script>
(function(){
  var P = window.parent || window;
  try {
    P.__kvPlayed = P.__kvPlayed || {};
    P.__kvQ = P.__kvQ || [];
    var id = "__ID__";
    if (P.__kvPlayed[id]) return;
    P.__kvPlayed[id] = 1;
    P.__kvQ.push("data:audio/mpeg;base64,__B64__");
    var next = function(){
      if (P.__kvBusy) return;
      var s = P.__kvQ.shift();
      if (!s) return;
      P.__kvBusy = true;
      var a = new P.Audio(s);
      var done = function(){ P.__kvBusy = false; next(); };
      a.onended = done; a.onerror = done;
      var pr = a.play();
      if (pr && pr.catch) pr.catch(function(){
        var d = P.document;
        if (d.getElementById("kv-ann-btn")) { P.__kvBusy = false; P.__kvQ.unshift(s); return; }
        var b = d.createElement("button");
        b.id = "kv-ann-btn";
        b.textContent = "🔊 ចុចដើម្បីស្តាប់សារ";
        b.style.cssText = "position:fixed;left:50%;bottom:90px;transform:translateX(-50%);z-index:99999;padding:14px 22px;border:0;border-radius:999px;background:#7C3AED;color:#fff;font-size:16px;font-weight:700;box-shadow:0 6px 20px rgba(0,0,0,.3)";
        b.onclick = function(){
          b.remove();
          a.onended = done; a.onerror = done;
          a.play().catch(done);
        };
        d.body.appendChild(b);
      });
    };
    next();
  } catch (e) {}
})();
</script>""".replace("__ID__", str(ann_id)).replace("__B64__", b64)


def announce_new_done(job):
    """ប្រកាសសំឡេងសម្រាប់វីដេអូដែលទើបធ្វើរួច (ម្តងមួយដង)។ ត្រឡប់ True បើមានការប្រកាស។"""
    if not st.session_state.get("announce_toggle", True):
        return False
    played = False
    for i, it in enumerate(job.items, start=1):
        if it["state"] == "done" and not it.get("announced"):
            it["announced"] = True
            try:
                b64 = done_announcement_b64(i)
            except Exception:
                b64 = None
            if b64:
                components.html(announce_html(f"{job.id}_{i}", b64), height=0)
                played = True
    return played



# ជំហានលម្អិត: (ឈ្មោះ, pct ចាប់ផ្តើម, pct បញ្ចប់) — ប្រើបង្ហាញភាគរយ និងពេលវេលាតាមជំហាននីមួយៗ
PIPE_STAGES = [
    ("ទាញយកវីដេអូ", 0.00, 0.12),
    ("រៀបចំឯកសារ", 0.12, 0.18),
    ("ដកសំឡេងចេញពីវីដេអូ", 0.18, 0.25),
    ("ស្តាប់ និងបកប្រែជាខ្មែរ", 0.25, 0.55),
    ("បង្កើតសំឡេងខ្មែរ / រៀបចំអក្សរ", 0.55, 0.75),
    ("ដាក់អក្សរចូលវីដេអូ", 0.75, 1.00),
]


def _fmt_secs(x):
    x = int(max(0, x))
    return f"{x // 60} នាទី {x % 60} វិ" if x >= 60 else f"{x} វិ"


def stage_panel(it):
    """បង្ហាញបញ្ជីជំហាន: ✅ ចប់ (ប្រើពេលប៉ុន្មាន) · 🔄 កំពុងធ្វើ (ភាគរយក្នុងជំហាន) · ⏳ រង់ចាំ។"""
    pct = max(0.0, min(1.0, float(it.get("pct", 0.0))))
    now = time.time()
    t0 = it.get("t0") or now
    times = it.setdefault("stage_times", {})
    cur = 0
    for k, (_n, lo, hi) in enumerate(PIPE_STAGES):
        if pct >= lo:
            cur = k
    for k in range(cur + 1):
        times.setdefault(k, now)
    elapsed = now - t0
    head = f"**សរុប {int(pct * 100)}%** · ចំណាយពេល {_fmt_secs(elapsed)}"
    if pct > 0.08 and elapsed > 5:
        head += f" · នៅសល់ប្រហែល {_fmt_secs(elapsed / pct - elapsed)}"
    lines = [head, ""]
    for k, (name, lo, hi) in enumerate(PIPE_STAGES):
        if k < cur:
            dur = times.get(k + 1, now) - times.get(k, now)
            lines.append(f"✅ {k + 1}. {name} — ចប់ ១០០% ({_fmt_secs(dur)})")
        elif k == cur:
            frac = max(0.0, min(1.0, (pct - lo) / (hi - lo))) if hi > lo else 0.0
            lines.append(f"🔄 **{k + 1}. {name} — {int(frac * 100)}%** ({_fmt_secs(now - times.get(k, now))})")
        else:
            lines.append(f"⏳ {k + 1}. {name} — រង់ចាំ")
    st.markdown("  \n".join(lines))


def work_area(job, was_running, reviewing=False):
    items = job.items
    total = len(items)
    done = sum(1 for it in items if it["state"] == "done")
    failed = sum(1 for it in items if it["state"] == "error")
    working = total - done - failed
    c1, c2, c3 = st.columns(3)
    c1.metric("⏳ កំពុងធ្វើ", working)
    c2.metric("✅ រួចរាល់", done)
    c3.metric("❌ បរាជ័យ", failed)
    st.progress((done + failed) / total, text=f"សរុប {done + failed} / {total}")
    # ---- តាមដានបែបបង្រួម៖ ១ វីដេអូ = ១ ជួរតូច · ជំហានលម្អិតលាក់ក្នុង expander ----
    _many = total > 5
    _ICON = {"done": "✅", "error": "❌", "review": "✏️", "running": "🔄", "queued": "⏳"}
    _done_rows = []
    for i, it in enumerate(items, start=1):
        if _many and it["state"] == "done":
            _secs = it["elapsed"] if it["elapsed"] is not None else (time.time() - it["t0"] if it["t0"] else 0)
            _done_rows.append(f"✅ {i}. {it['name']} — ⏱ {int(_secs)} វិ")
            for w in it["warn"]:
                st.warning(f"{i}. {w}")
            continue
        with st.container(border=True):
            _pct = max(0.0, min(1.0, float(it.get("pct") or 0.0)))
            _secs = None
            if it["t0"]:
                _secs = it["elapsed"] if it["elapsed"] is not None else time.time() - it["t0"]
            _tail = f" · ⏱ {int(_secs)} វិ" if _secs is not None else ""
            if it["state"] in ("running", "queued"):
                st.markdown(f"{_ICON.get(it['state'], '🔄')} **{i}. {it['name']}** — {int(_pct * 100)}%{_tail}")
            else:
                st.markdown(f"{_ICON.get(it['state'], '')} **{i}. {it['name']}**{_tail}")
            if it["state"] == "done":
                st.caption("រួចរាល់ — ទាញយកបាននៅផ្នែកខាងក្រោម ⬇️")
            elif it["state"] == "error":
                st.error(it["error"] or "មិនបានសម្រេច។")
                if not any(_k in str(it["error"] or "").lower() for _k in ("offline", "whisper", "madlad", "voxcpm", "faster", "ctranslate2")):
                    st.info("💡 បើបញ្ហាដោយសារ API អស់កូតា សូមដាក់ API Key ផ្ទាល់ខ្លួននៅផ្ទាំង «🌐 បកប្រែ» រួចសាកម្តងទៀត។")
                if DEBUG and it["raw_error"]:
                    st.text(it["raw_error"])
            elif it["state"] == "review" and it.get("review_segments") is not None:
                st.info("✏️ ពិនិត្យ និងកែអក្សរខ្មែរ រួចចុច «បន្ត» ដើម្បីបង្កើតសំឡេង និងដាក់អក្សរចូលវីដេអូ។ លុបអក្សរឃ្លាណាឱ្យទទេ ដើម្បីរំលងឃ្លានោះ។")
                with st.form(key=f"rvform_{job.id}_{i}"):
                    _edited = []
                    _picks = []
                    _gl = it.get("review_genders") or []
                    _gopts = ["🤖 ស្វ័យប្រវត្តិ", "♂ សំឡេងប្រុស", "♀ សំឡេងស្រី"]
                    for _k, (_a, _b, _t) in enumerate(it["review_segments"]):
                        _new = st.text_area(f"{_k + 1}. {fmt_clock(_a)} → {fmt_clock(_b)}", value=_t,
                                            key=f"rv_{job.id}_{i}_{_k}", height=80)
                        _g0 = _gl[_k] if _k < len(_gl) else None
                        _pick = st.selectbox("🎙 សំឡេងអាន (ប្រុស/ស្រី)", _gopts,
                                             index={"M": 1, "F": 2}.get(_g0, 0),
                                             key=f"rvg_{job.id}_{i}_{_k}")
                        _picks.append({"♂ សំឡេងប្រុស": "M", "♀ សំឡេងស្រី": "F"}.get(_pick))
                        _edited.append((_a, _b, _new))
                    _fc1, _fc2 = st.columns(2)
                    _go = _fc1.form_submit_button("✅ បន្ត (ប្រើអក្សរដែលកែ)", type="primary", use_container_width=True)
                    _skip = _fc2.form_submit_button("⏭ បន្តដោយមិនកែ", use_container_width=True)
                if _go or _skip:
                    it["review_final"] = _edited if _go else None
                    it["review_final_genders"] = _picks if _go else None
                    it["state"] = "running"
                    it["stage"] = "កំពុងបន្តជាមួយអក្សរដែលបានកែ..."
                    _ev = it.get("review_event")
                    if _ev is not None:
                        _ev.set()
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.progress(_pct, text=f"{it['stage']}")
                if it["state"] in ("running", "queued"):
                    with st.expander("📋 ជំហានលម្អិត", expanded=False):
                        stage_panel(it)
            for w in it["warn"]:
                st.warning(w)
    if _done_rows:
        with st.expander(f"✅ វីដេអូដែលរួចរាល់ ({len(_done_rows)}) — ទាញយកនៅខាងក្រោម", expanded=False):
            for _r in _done_rows:
                st.caption(_r)
    _played = announce_new_done(job)
    if (was_running and not job.running()) or (reviewing != job.reviewing()):
        if _played:
            time.sleep(1.5)   # ឱ្យ browser ទទួលនិងចាប់ផ្តើមលេងសំឡេងសិន មុន rerun
        st.rerun()


def make_mobile_copy(src, dst):
    """បង្កើតវីដេអូតូច (720p, bitrate ទាប) សម្រាប់ទាញយក/រក្សាទុកលើទូរស័ព្ទ។"""
    run_ffmpeg([
        "-i", src,
        "-vf", "scale=w='if(gt(iw,ih),min(1280,iw),-2)':h='if(gt(iw,ih),-2,min(1280,ih))',format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
        "-maxrate", "1500k", "-bufsize", "3000k",
        "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", dst,
    ])
    return dst


PREVIEW_MAX_MB = 60   # វីដេអូធំជាងនេះ មិនបង្ហាញ preview


SHARE_MAX_MB = 30


def share_button(path, fname):
    """បង្ហោះវីដេអូទៅ TikTok តាមបញ្ជី Share ក្នុងទូរស័ព្ទ (មិនបាច់ទាញយក)។"""
    try:
        size = os.path.getsize(path)
    except Exception:
        return False
    if size > SHARE_MAX_MB * 1024 * 1024:
        return False
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    components.html(
        """
<button id="b" style="width:100%;padding:14px;font-size:17px;font-weight:700;color:#fff;border:0;
border-radius:14px;background:linear-gradient(90deg,#B13CFF,#3C6BFF);cursor:pointer;
font-family:system-ui,sans-serif;">🎵 បង្ហោះទៅ TikTok</button>
<div id="m" style="color:#B42318;font-size:14px;margin-top:6px;font-family:system-ui,sans-serif;"></div>
<script>
const B64 = "__B64__";
const NAME = __NAME__;
document.getElementById("b").onclick = async () => {
  const m = document.getElementById("m");
  m.textContent = "";
  try {
    const bin = atob(B64);
    const arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    const targets = [];
    try { if (window.parent && window.parent.navigator && window.parent.File) targets.push([window.parent.navigator, window.parent.File]); } catch (e) {}
    targets.push([navigator, File]);
    for (const [nav, F] of targets) {
      try {
        const file = new F([arr], NAME, {type: "video/mp4"});
        if (nav.canShare && nav.canShare({files: [file]})) {
          await nav.share({files: [file]});
          return;
        }
      } catch (e) {
        if (e && e.name === "AbortError") return;
      }
    }
    m.innerHTML = "ឧបករណ៍ ឬកម្មវិធីរុករកនេះមិនគាំទ្រការបង្ហោះផ្ទាល់ទេ។ សូមទាញយកវីដេអូ រួច "
      + '<a href="https://www.tiktok.com/tiktokstudio/upload" target="_blank" style="color:#1D4ED8">បើកទំព័រ TikTok</a>';
  } catch (e) {
    m.textContent = "មិនអាចបង្ហោះបានទេ។ សូមទាញយកវីដេអូជាមុន។";
  }
};
</script>
""".replace("__B64__", b64).replace("__NAME__", json.dumps(fname)),
        height=84,
    )
    return True


def download_area(job):
    done = [(i, it) for i, it in enumerate(job.items, start=1) if it["state"] == "done"]
    if not done:
        st.info("វីដេអូណាដែលរួចរាល់ នឹងលេចឡើងនៅទីនេះភ្លាមៗ ហើយអាចទាញយកបានតែម្តង។")
        return
    st.caption("📱 iPhone: ចុចប៊ូតុងទាញយក → ចុច «Download» → បើក Safari បង្ហាញរូបព្រួញ ⬇️ ខាងលើ ចុចវា → ជ្រើសវីដេអូ → Share → Save Video។ សូមប្រើ Safari។")
    for i, it in done:
        with st.container(border=True):
            if getattr(job, "text_only", False):
                st.markdown(f"**🎬 {it['name']}**")
                _vp0 = it.get("video_path")
                if _vp0 and os.path.isfile(_vp0):
                    if not browser_dl_link("🌐 ទាញយកក្នុង Browser", _vp0, f"{safe_filename(it['name'])}_khmer.mp4", "video/mp4", f"dl_{job.id}_{i}"):
                        with open(_vp0, "rb") as _vf0:
                            dl_button("⬇️ ទាញយកវីដេអូ", _vf0, f"{safe_filename(it['name'])}_khmer.mp4", "video/mp4",
                                      key=f"dl_{job.id}_{i}", use_container_width=True)
                for text in it["captions"]:
                    st.write(text)
                continue
            vp = it.get("video_path")
            if vp and os.path.isfile(vp):
                fname = f"{safe_filename(it['name'])}_khmer.mp4"
                size_mb = os.path.getsize(vp) / (1024 * 1024)
                # វីដេអូធំ: ប្រើកំណែតូច (ដែលបង្កើតស្វ័យប្រវត្តិ) ដើម្បីឱ្យ iPhone ទាញយកបានលឿន
                small = it.get("small_path")
                if small and os.path.isfile(small):
                    vp = small
                    fname = fname.replace("_khmer.mp4", "_khmer_mobile.mp4")
                    size_mb = os.path.getsize(vp) / (1024 * 1024)
                st.markdown(f"**✅ {os.path.splitext(it['name'])[0]}.mp4** · {size_mb:.0f}MB")
                if not browser_dl_link("🌐 ទាញយកក្នុង Browser", vp, fname, "video/mp4", f"dl_{job.id}_{i}"):
                    with open(vp, "rb") as vf:
                        dl_button("⬇️ ទាញយកវីដេអូ", vf, fname, "video/mp4",
                                  key=f"dl_{job.id}_{i}", type="primary", use_container_width=True)
                if not share_button(vp, fname):
                    if hasattr(st, "link_button"):
                        st.link_button("🎵 បង្ហោះទៅ TikTok", "https://www.tiktok.com/tiktokstudio/upload",
                                       use_container_width=True)
                if size_mb <= PREVIEW_MAX_MB:
                    with st.expander("▶️ មើលវីដេអូ"):
                        st.video(vp)
            else:
                st.caption("ឯកសារវីដេអូត្រូវបានលុបចេញពីម៉ាស៊ីនហើយ។")
            if it.get("titles"):
                with st.expander("🏷 ចំណងជើងខ្មែរសម្រាប់ជ្រើសរើស (ចុចរូបចម្លង)", expanded=True):
                    for _ti, _tt in enumerate(it["titles"], start=1):
                        st.code(_tt, language=None)
            with st.expander("📝 មើលអត្ថបទខ្មែរ"):
                for text in it["captions"]:
                    st.write(text)
            if it.get("voice_lines"):
                with st.expander("👫 ព័ត៌មានសំឡេងអាន"):
                    for line in it["voice_lines"]:
                        st.write(line)
            if DEBUG:
                with st.expander("🛠 DEBUG"):
                    for key, value in it["debug"].items():
                        st.text(f"{key}: {value}")
                    st.text("\\n".join(it["log"][-30:]))
    if getattr(job, "text_only", False) and done:
        _all_txt = "\n\n".join(f"== {_it['name']} ==\n" + "\n".join(_it["captions"]) for _i, _it in done)
        dl_button("📝 ទាញយកអក្សរបកប្រែទាំងអស់ (.txt)", _all_txt.encode("utf-8"), "khmer_text.txt", "text/plain",
                  key=f"txt_{job.id}", use_container_width=True)
    if getattr(job, "merged", None) and os.path.isfile(job.merged):
        st.markdown("### 🎞 វីដេអូរួមតែមួយ")
        st.video(job.merged)
        if not browser_dl_link("🌐 🎞 ទាញយកវីដេអូរួម ក្នុង Browser", job.merged, "khmer_merged.mp4", "video/mp4", f"merged_{job.id}"):
            with open(job.merged, "rb") as mf:
                dl_button("🎞 ទាញយកវីដេអូរួមតែមួយ", mf, "khmer_merged.mp4", "video/mp4", key=f"merged_{job.id}", use_container_width=True)
    if job.zip and os.path.isfile(job.zip):
        if not browser_dl_link("🌐 📦 ទាញយកទាំងអស់ (ZIP) ក្នុង Browser", job.zip, "khmer_videos.zip", "application/zip", f"zip_{job.id}"):
            with open(job.zip, "rb") as zf:
                dl_button("📦 ទាញយកទាំងអស់ (ZIP)", zf, "khmer_videos.zip", "application/zip", key=f"zip_{job.id}", use_container_width=True)


def scroll_to_downloads():
    components.html(
        f"""
        <script>
        // {time.time()}
        const go = () => {{
          try {{
            const doc = window.parent.document;
            const el = doc.getElementById("download-area");
            if (el) {{ el.scrollIntoView({{behavior: "smooth", block: "start"}}); return true; }}
          }} catch (e) {{}}
          return false;
        }};
        let tries = 0;
        const timer = setInterval(() => {{
          if (go() || ++tries > 24) clearInterval(timer);
        }}, 250);
        </script>
        """,
        height=0,
    )


# API keys: អាចដាក់ច្រើនក្នុង Secret តែមួយដោយបំបែកជាក្បៀស ឬបន្ទាត់ថ្មី។
# អាចប្រើ GROQ_API_KEY_1, GROQ_API_KEY_2 ... បាន។
def collect_api_keys(prefix):
    values = [get_secret(prefix, ""), get_secret(prefix + "S", "")]
    # អាន numbered secrets រហូតដល់ 20 keys; ឈប់ពេលជួប 5 លេខទទេជាប់គ្នា។
    empty_streak = 0
    for i in range(1, 21):
        value = get_secret(f"{prefix}_{i}", "")
        if value:
            values.append(value)
            empty_streak = 0
        else:
            empty_streak += 1
            if empty_streak >= 5 and i >= 5:
                break
    return "\n".join(split_keys(values))


# =====================================================================
#  API Key ផ្ទាល់ខ្លួនរបស់អ្នកប្រើ (ពេល API របស់កម្មវិធីអស់)
#  Key រក្សាទុកតែក្នុង session របស់អ្នកប្រើប៉ុណ្ណោះ (មិនសរសេរចូលឯកសារ)
#  វាបាត់ដោយស្វ័យប្រវត្តិពេលបិទទំព័រ ឬចុច «ឈប់ប្រើ»
# =====================================================================
def validate_groq_key(key):
    """ពិនិត្យ Groq key ថាប្រើបានឬអត់។ ត្រឡប់ (True/False, សារ)។"""
    key = str(key or "").strip()
    if not key or len(key) < 20 or any(c.isspace() for c in key):
        return False, "Key មិនត្រឹមត្រូវ (ត្រូវចាប់ផ្តើមដោយ gsk_ ហើយគ្មានដកឃ្លា)។"
    try:
        req = urllib.request.Request(GROQ_MODELS_URL, headers={"Authorization": f"Bearer {key}", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            r.read()
        return True, "Key ប្រើបាន ✅"
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return True, "Key ត្រឹមត្រូវ (ប៉ុន្តែកំពុងអស់កូតាបណ្តោះអាសន្ន) ✅"
        if e.code in (401, 403):
            return False, "Key មិនត្រឹមត្រូវ ឬត្រូវបានបិទ។"
        return False, f"ពិនិត្យ Key មិនបាន (HTTP {e.code})។"
    except Exception:
        return False, "ពិនិត្យ Key មិនបាន (បញ្ហាបណ្តាញ)។ សូមសាកម្តងទៀត។"


def validate_gemini_key(key):
    """ពិនិត្យ Gemini key ថាប្រើបានឬអត់។ ត្រឡប់ (True/False, សារ)។"""
    key = str(key or "").strip()
    if not key or len(key) < 20 or any(c.isspace() for c in key):
        return False, "Key មិនត្រឹមត្រូវ (ត្រូវចាប់ផ្តើមដោយ AIza ហើយគ្មានដកឃ្លា)។"
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1&key=" + urllib.parse.quote(key)
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
            r.read()
        return True, "Key ប្រើបាន ✅"
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return True, "Key ត្រឹមត្រូវ (ប៉ុន្តែកំពុងអស់កូតាបណ្តោះអាសន្ន) ✅"
        if e.code in (400, 401, 403):
            return False, "Key មិនត្រឹមត្រូវ ឬត្រូវបានបិទ។"
        return False, f"ពិនិត្យ Key មិនបាន (HTTP {e.code})។"
    except Exception:
        return False, "ពិនិត្យ Key មិនបាន (បញ្ហាបណ្តាញ)។ សូមសាកម្តងទៀត។"


# =====================================================================
#  API Key ផ្ទាល់ខ្លួនរបស់អ្នកប្រើ — ដាក់បានច្រើន Key + សេវទុកក្នុង Browser
#  Key រក្សាទុកក្នុង localStorage របស់ Browser អ្នកប្រើផ្ទាល់ (មិនផ្ញើទៅរក្សាទុកលើម៉ាស៊ីនមេទេ)
#  ពេលចូលលើកក្រោយ កម្មវិធីអានវិញដោយស្វ័យប្រវត្តិ
# =====================================================================
_LS_HTML = """<!doctype html><html><body><script>
(function () {
  var KEY = "kvai_user_keys_v1", lastNonce = null, sent = false;
  function send(type, data) {
    window.parent.postMessage(Object.assign({isStreamlitMessage: true, type: type}, data), "*");
  }
  function readStore() { try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; } }
  window.addEventListener("message", function (ev) {
    var d = ev.data;
    if (!d || d.type !== "streamlit:render") return;
    var a = d.args || {};
    if (a.nonce !== undefined && a.nonce !== lastNonce) {
      lastNonce = a.nonce;
      if (a.save !== null && a.save !== undefined) {
        try {
          if (a.save === "") localStorage.removeItem(KEY); else localStorage.setItem(KEY, a.save);
        } catch (e) {}
      }
    }
    if (!sent) {
      sent = true;
      send("streamlit:setComponentValue", {value: {data: readStore()}, dataType: "json"});
    }
  });
  send("streamlit:componentReady", {apiVersion: 1});
  send("streamlit:setFrameHeight", {height: 0});
})();
</script></body></html>"""


@st.cache_resource(show_spinner=False)
def _kv_component():
    folder = os.path.join(tempfile.gettempdir(), "kvai_ls_component")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "index.html"), "w", encoding="utf-8") as f:
        f.write(_LS_HTML)
    return components.declare_component("kvai_local_storage", path=folder)


GEMINI_OAI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
GEMINI_DEFAULT_MODEL = "gemini-3.6-flash"   # gemini-2.5-flash លែងបើកឱ្យអ្នកប្រើថ្មី (HTTP 404)
_GEMINI_RETIRED = ("gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0", "gemini-1.5", "gemini-1.0", "gemini-pro")


def _gm_fix(name):
    """ប្តូរឈ្មោះម៉ូដែល Gemini ចាស់ៗដែលបិទហើយ ទៅម៉ូដែលលំនាំដើមថ្មី (រួមទាំងដែលចងចាំក្នុង Browser)។"""
    n = str(name or "").strip()
    if not n:
        return GEMINI_DEFAULT_MODEL
    base = n.replace("models/", "")
    if base in ("gemini-2.5-flash", "gemini-2.5-pro") or base.startswith(("gemini-2.0", "gemini-1.5", "gemini-1.0")) or base == "gemini-pro":
        return GEMINI_DEFAULT_MODEL
    return n
GEMINI_LABEL = "Gemini ⚠️ មិនណែនាំ"


def xk_cfg_for_session():
    """CodeCraft Key មុន បើគ្មាន ប្រើ Gemini Key (តាមរយៈ OpenAI-compatible endpoint របស់ Google)។"""
    ss = st.session_state
    if ss.get("user_oai_key"):
        return (ss.get("user_oai_key", ""), ss.get("user_oai_base", ""), ss.get("user_oai_model", ""))
    if ss.get("user_gemini_key"):
        return (ss["user_gemini_key"], GEMINI_OAI_BASE, _gm_fix(ss.get("user_gemini_model")))
    return ("", "", "")


def _ls_persist():
    """រៀបចំទិន្នន័យ Key ដើម្បីសរសេរចូល localStorage នៅពេល rerun បន្ទាប់។"""
    ss = st.session_state
    groq = list(ss.get("user_groq_keys", []))
    oai = {"key": ss.get("user_oai_key", ""), "base": ss.get("user_oai_base", ""),
           "model": ss.get("user_oai_model", "")}
    claude = {"keys": list(ss.get("user_claude_keys", [])),
              "base": ss.get("user_claude_base", "https://api.laalaa.me"),
              "model": ss.get("user_claude_model", "claude-sonnet-5-5")}
    hongguo = {"app_id": ss.get("user_hg_app_id", ""),
               "app_secret": ss.get("user_hg_app_secret", ""),
               "apify_token": ss.get("user_hg_apify", "")}
    gemini = {"key": ss.get("user_gemini_key", ""), "model": ss.get("user_gemini_model", "")}
    if not ss.get("remember_keys", True) or not (groq or oai["key"] or claude["keys"] or gemini["key"] or hongguo["app_id"] or hongguo["app_secret"] or hongguo["apify_token"]):
        payload = ""
    else:
        payload = json.dumps({"groq": groq, "oai": oai, "claude": claude, "hongguo": hongguo, "gemini": gemini})
    ss["_ls_payload"] = payload
    ss["_ls_nonce"] = ss.get("_ls_nonce", 0) + 1


def ls_sync():
    """ហៅមួយដងក្នុងមួយ run: សរសេរ Key ថ្មីចូល Browser និងអាន Key ដែលបានរក្សាទុកពីមុនមកវិញ។"""
    try:
        res = _kv_component()(save=st.session_state.get("_ls_payload"),
                              nonce=st.session_state.get("_ls_nonce", 0),
                              default=None, key="kv_ls")
    except Exception:
        return
    if not res or st.session_state.get("_ls_loaded"):
        return
    st.session_state["_ls_loaded"] = True
    raw = (res.get("data") if isinstance(res, dict) else "") or ""
    try:
        data = json.loads(raw) if raw else {}
    except Exception:
        data = {}
    if not isinstance(data, dict):
        return
    sk, name = "user_groq_keys", "groq"
    merged = split_keys([st.session_state.get(sk, []), data.get(name) or []])
    if merged:
        st.session_state[sk] = merged
    oai = data.get("oai") or {}
    if isinstance(oai, dict) and oai.get("key") and not st.session_state.get("user_oai_key"):
        st.session_state["user_oai_key"] = str(oai.get("key", "")).strip()
        st.session_state["user_oai_base"] = str(oai.get("base", "")).strip()
        st.session_state["user_oai_model"] = str(oai.get("model", "")).strip()
    cl = data.get("claude") or {}
    if isinstance(cl, dict) and cl.get("keys"):
        _merged_c = split_keys([st.session_state.get("user_claude_keys", []), cl.get("keys") or []])
        if _merged_c:
            st.session_state["user_claude_keys"] = _merged_c
            if cl.get("base") and not st.session_state.get("user_claude_base"):
                st.session_state["user_claude_base"] = str(cl.get("base")).strip()
            if cl.get("model") and not st.session_state.get("user_claude_model"):
                st.session_state["user_claude_model"] = str(cl.get("model")).strip()
    gm = data.get("gemini") or {}
    if isinstance(gm, dict) and gm.get("key") and not st.session_state.get("user_gemini_key"):
        st.session_state["user_gemini_key"] = str(gm.get("key", "")).strip()
        st.session_state["user_gemini_model"] = _gm_fix(gm.get("model", ""))
    hg = data.get("hongguo") or {}
    if isinstance(hg, dict):
        if hg.get("app_id") and not st.session_state.get("user_hg_app_id"):
            st.session_state["user_hg_app_id"] = str(hg.get("app_id")).strip()
        if hg.get("app_secret") and not st.session_state.get("user_hg_app_secret"):
            st.session_state["user_hg_app_secret"] = str(hg.get("app_secret")).strip()
        if hg.get("apify_token") and not st.session_state.get("user_hg_apify"):
            st.session_state["user_hg_apify"] = str(hg.get("apify_token")).strip()


def has_user_keys():
    ss = st.session_state
    return bool(ss.get("user_groq_keys") or ss.get("user_oai_key") or ss.get("user_claude_keys") or ss.get("user_gemini_key"))


def effective_groq_key():
    """Key របស់អ្នកប្រើ (បើមាន) មុន ហើយ key របស់កម្មវិធីជាបម្រុង។"""
    mine = st.session_state.get("user_groq_keys", [])
    return "\n".join(split_keys([mine, GROQ_KEY])) if mine else GROQ_KEY


def effective_gemini_key():
    # Gemini removed by request. Do not load or call Gemini keys/models.
    return ""


def mask_key(k):
    k = str(k)
    return (k[:4] + "…" + k[-4:]) if len(k) > 10 else "…"


def _classify_http(code):
    if code == 200:
        return "ok", "ប្រើបាន"
    if code in (401, 403):
        return "bad", "Key មិនត្រឹមត្រូវ ឬត្រូវបានបិទ"
    if code == 402:
        return "bad", "អស់ credit / ត្រូវបង់ប្រាក់"
    if code == 404:
        return "bad", "URL ឬឈ្មោះម៉ូដែលខុស"
    if code in (503, 529):
        return "limit", "Key ត្រឹមត្រូវ តែម៉ាស៊ីនមេរវល់ ឬគ្មាន account ទំនេរបណ្តោះអាសន្ន"
    if code == 429:
        return "limit", "Key ត្រឹមត្រូវ តែអស់កូតា ឬ Rate limit បណ្តោះអាសន្ន"
    return "error", f"HTTP {code}"


def _http_probe(url, headers, payload=None, timeout=30, secret=""):
    """ហៅម្តង (គ្មាន retry) ហើយត្រឡប់ (state, សារ, ms)។ មិនបង្ហាញ Key ក្នុងសារ។"""
    t0 = time.time()
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, method="POST" if body else "GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(2000)
        return "ok", "ប្រើបាន", int((time.time() - t0) * 1000)
    except urllib.error.HTTPError as e:
        state, msg = _classify_http(e.code)
        detail = ""
        try:
            detail = e.read().decode("utf-8", "ignore")[:160].replace("\n", " ")
        except Exception as _swallow_e:
            _log_swallowed(_swallow_e)
        if secret:
            detail = detail.replace(secret, "***")
        if detail and state in ("error", "bad", "limit"):
            msg += " · HTTP " + str(e.code) + " · " + detail
        return state, msg, int((time.time() - t0) * 1000)
    except Exception as e:
        return "error", "បណ្តាញ/Timeout: " + str(e)[:120], int((time.time() - t0) * 1000)


def check_groq_key(cfg):
    key = cfg[0]
    return _http_probe(GROQ_MODELS_URL, {"Authorization": f"Bearer {key}", "User-Agent": "Mozilla/5.0"}, secret=key)


def check_claude_key(cfg):
    key, base, model = cfg
    base = str(base).rstrip("/")
    url = base + ("/messages" if base.endswith("/v1") else "/v1/messages")
    headers = {"x-api-key": key, "Authorization": f"Bearer {key}", "anthropic-version": "2023-06-01",
               "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    models = [model] + [m for m in _CLAUDE_FALLBACK_MODELS if m != model]
    res = ("error", "មិនទាន់សាក", 0)
    for m in models:
        payload = {"model": m, "max_tokens": 8, "messages": [{"role": "user", "content": "hi"}]}
        res = _http_probe(url, headers, payload, secret=key)
        if res[0] == "ok":
            _CLAUDE_GOOD_MODEL[key] = m
            if m != model:
                return "ok", f"ប្រើបាន (model «{m}» ដំណើរការ — សូមដាក់ឈ្មោះនេះក្នុងប្រអប់ Model)", res[2]
            return res
        if res[0] == "bad" and "មិនត្រឹមត្រូវ" in res[1]:
            return res      # Key ខុស — មិនបាច់សាក model ផ្សេង
        time.sleep(1.2)
    return res[0], res[1] + " · (សាកគ្រប់ model ហើយ៖ " + ", ".join(models) + ")", res[2]


def check_openai_key(cfg):
    key, base, model = cfg
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    payload = {"model": model, "max_tokens": 8, "messages": [{"role": "user", "content": "hi"}]}
    return _http_probe(str(base).rstrip("/") + "/chat/completions", headers, payload, secret=key)


def key_check_targets():
    """ពិនិត្យតែ API Key ផ្ទាល់ខ្លួនរបស់ session នេះប៉ុណ្ណោះ។"""
    ss = st.session_state
    rows = []
    for i, k in enumerate(ss.get("user_claude_keys", []), start=1):
        _b = ss.get("user_claude_base", "https://api.laalaa.me")
        _m = ss.get("user_claude_model", "claude-sonnet-5-5")
        rows.append((f"Claude ផ្ទាល់ខ្លួន #{i}", mask_key(k), "claude", (k, _b, _m), _m))
    for i, k in enumerate(ss.get("user_groq_keys", []), start=1):
        rows.append((f"Groq ផ្ទាល់ខ្លួន #{i}", mask_key(k), "groq", (k,), "whisper + chat"))
    if ss.get("user_oai_key"):
        _cfg = (ss["user_oai_key"], ss.get("user_oai_base", ""),
                ss.get("user_oai_model", ""))
        rows.append(("CodeCraft ផ្ទាល់ខ្លួន", mask_key(_cfg[0]), "openai", _cfg, _cfg[2]))
    if ss.get("user_gemini_key"):
        _gm = _gm_fix(ss.get("user_gemini_model"))
        rows.append(("Gemini ផ្ទាល់ខ្លួន (មិនណែនាំ)", mask_key(ss["user_gemini_key"]), "openai",
                     (ss["user_gemini_key"], GEMINI_OAI_BASE, _gm), _gm))
    return rows


def run_key_checks():
    targets = key_check_targets()
    fn = {"groq": check_groq_key, "claude": check_claude_key, "openai": check_openai_key}

    def one(t):
        name, masked, kind, cfg, model = t
        try:
            state, msg, ms = fn[kind](cfg)
        except Exception as e:
            state, msg, ms = "error", str(e)[:140], 0
        return {"name": name, "key": masked, "model": model, "state": state, "msg": msg, "ms": ms}

    if not targets:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(targets))) as pool:
        return list(pool.map(one, targets))


def user_key_box():
    """ប្រអប់ឱ្យអ្នកប្រើដាក់ API Key ផ្ទាល់ខ្លួនបានច្រើន (Groq / CodeCraft) ហើយសេវទុកក្នុង Browser។"""
    if st.session_state.pop("_clear_key_input", False):
        st.session_state.pop("user_key_input", None)
        st.session_state.pop("user_keys_bulk", None)
        st.session_state.pop("user_claude_bulk", None)
        st.session_state.pop("user_gemini_input", None)
        st.session_state.pop("user_hg_app_id_input", None)
        st.session_state.pop("user_hg_app_secret_input", None)
        st.session_state.pop("user_hg_apify_input", None)
    with st.container(border=True):
        st.markdown("**🔑 API Key ផ្ទាល់ខ្លួន (ដាក់បានច្រើន Key)**")
        st.caption("បើ API របស់កម្មវិធីអស់កូតា ឬបរាជ័យ សូមដាក់ Groq Key សម្រាប់សម្គាល់សំឡេង និង CodeCraft Key សម្រាប់បកប្រែ។ "
                   "ដាក់បានច្រើន Key — Key មួយអស់កូតា កម្មវិធីប្តូរទៅ Key បន្ទាប់ដោយស្វ័យប្រវត្តិ។")
        _msg = st.session_state.pop("_key_msg", None)
        if _msg:
            (st.success if _msg[0] == "ok" else st.warning)(_msg[1])
        any_saved = False
        for name, sk in (("Claude", "user_claude_keys"), ("Groq", "user_groq_keys")):
            lst = list(st.session_state.get(sk, []))
            if not lst:
                continue
            any_saved = True
            st.markdown(f"✅ **{name}** · {len(lst)} Key")
            for n, k in enumerate(lst):
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"`{mask_key(k)}`")
                if c2.button("🗑", key=f"del_{sk}_{n}", help="លុប Key នេះ"):
                    st.session_state[sk] = [x for i, x in enumerate(lst) if i != n]
                    _ls_persist()
                    st.rerun()
        if st.session_state.get("user_oai_key"):
            any_saved = True
            st.success(f"✅ កំពុងប្រើ CodeCraft Key របស់អ្នក (…{st.session_state['user_oai_key'][-4:]})")
            if st.button("🗑 ឈប់ប្រើ CodeCraft Key", key="remove_user_oai_key"):
                for _k in ("user_oai_key", "user_oai_base", "user_oai_model"):
                    st.session_state.pop(_k, None)
                _ls_persist()
                st.rerun()
        if st.session_state.get("user_gemini_key"):
            any_saved = True
            st.warning(f"⚠️ កំពុងប្រើ Gemini Key (…{st.session_state['user_gemini_key'][-4:]}) — មិនណែនាំឱ្យប្រើ")
            if st.button("🗑 ឈប់ប្រើ Gemini Key", key="remove_user_gemini_key"):
                for _k in ("user_gemini_key", "user_gemini_model"):
                    st.session_state.pop(_k, None)
                _ls_persist()
                st.rerun()
        provider = st.radio("ប្រភេទ Key", ["Claude", "Groq", "CodeCraft", GEMINI_LABEL], horizontal=True, key="user_key_provider")
        oai_base_in = oai_model_in = ""
        typed = ""
        if provider == "Claude":
            typed = st.text_area("Claude API Key (មួយបន្ទាត់ ១ Key — ដាក់បានច្រើន)",
                                 placeholder="sk-...", height=100, key="user_claude_bulk")
            oai_base_in = st.text_input("Base URL (ដាក់តាមហាង បើមិនមាន ទុកលំនាំដើម)",
                                        value=st.session_state.get("user_claude_base", "https://api.laalaa.me"),
                                        key="user_claude_base_input")
            oai_model_in = st.text_input("ឈ្មោះម៉ូដែល",
                                         value=st.session_state.get("user_claude_model", "claude-sonnet-5-5"),
                                         key="user_claude_model_input")
            st.caption("Claude ប្រើសម្រាប់បកប្រែ និងកែសម្រួលអត្ថបទជាខ្មែរ (សាកមុនគេ)។ ការស្តាប់សំឡេងនៅតែត្រូវការ Groq Key ព្រោះ Claude មិនស្តាប់សំឡេងទេ។")
        elif provider == "CodeCraft":
            typed = st.text_input("CodeCraft API Key", type="password",
                                  placeholder="cc_...", key="user_key_input")
            oai_base_in = st.text_input(
                "Base URL",
                value=st.session_state.get("user_oai_base") or OAI_BASE or "https://codecraftapi.com/v1",
                key="user_oai_base_input",
                help="តាមឯកសារ CodeCraft៖ https://codecraftapi.com/v1",
            )
            _fetch_col, _model_col = st.columns([1, 2])
            with _fetch_col:
                if st.button("📥 ទាញ Model", key="codecraft_fetch_models", use_container_width=True):
                    _fetch_key = (typed or st.session_state.get("user_oai_key", "")).strip()
                    try:
                        with st.spinner("កំពុងទាញបញ្ជី Model ពី CodeCraft..."):
                            st.session_state["_codecraft_models"] = fetch_codecraft_models(_fetch_key, oai_base_in)
                            st.session_state["_codecraft_models_base"] = oai_base_in.strip().rstrip("/")
                        st.success(f"រកឃើញ {len(st.session_state['_codecraft_models'])} Model")
                    except Exception as _e:
                        st.error("ទាញ Model មិនបាន៖ " + str(_e)[:220])
            _cc_models = st.session_state.get("_codecraft_models", [])
            if _cc_models and st.session_state.get("_codecraft_models_base") == oai_base_in.strip().rstrip("/"):
                _old_model = st.session_state.get("user_oai_model") or OAI_MODEL
                _default_idx = _cc_models.index(_old_model) if _old_model in _cc_models else 0
                oai_model_in = st.selectbox(
                    "ជ្រើសរើស Model ID", _cc_models, index=_default_idx,
                    key="codecraft_model_select",
                )
            else:
                oai_model_in = st.text_input(
                    "Model ID (ចុច «ទាញ Model» ដើម្បីជ្រើសពីបញ្ជី)",
                    value=st.session_state.get("user_oai_model") or OAI_MODEL,
                    placeholder="ឧ. claude-opus-4.8",
                    key="user_oai_model_input",
                )
            st.caption("CodeCraft ប្រើសម្រាប់បកប្រែ និងកែសម្រួលអត្ថបទ។ ការសម្គាល់សំឡេងវីដេអូនៅតែត្រូវការ Groq ព្រោះ CodeCraft មិនមាន Speech-to-Text API។")
        elif provider == GEMINI_LABEL:
            st.warning("⚠️ **មិនណែនាំឱ្យប្រើ Gemini** — ការបកប្រែជាភាសាខ្មែរមិនសូវត្រឹមត្រូវ និងមិនធម្មជាតិដូច Claude ឬ CodeCraft ទេ "
                       "ហើយ Key ឥតគិតថ្លៃអាចអស់កូតាលឿន។ សូមប្រើ Claude ឬ CodeCraft ជំនួស បើអាច។ "
                       "ប្រើ Gemini ក្នុងករណីគ្មាន Key ផ្សេងប៉ុណ្ណោះ។")
            typed = st.text_input("Gemini API Key", type="password", placeholder="AIza...", key="user_gemini_input")
            if st.session_state.get("user_gemini_model_input"):
                st.session_state["user_gemini_model_input"] = _gm_fix(st.session_state["user_gemini_model_input"])
            oai_model_in = st.text_input("ឈ្មោះម៉ូដែល Gemini",
                                         value=_gm_fix(st.session_state.get("user_gemini_model", GEMINI_DEFAULT_MODEL)),
                                         key="user_gemini_model_input")
            st.caption("Gemini ប្រើសម្រាប់បកប្រែ និងកែសម្រួលអត្ថបទប៉ុណ្ណោះ។ ការស្តាប់សំឡេងនៅតែត្រូវការ Groq Key។ "
                       "បើមាន CodeCraft Key រួចហើយ កម្មវិធីប្រើ CodeCraft មុន។")
        else:
            typed = st.text_area("Groq API Key (មួយបន្ទាត់ ១ Key ឬបំបែកដោយក្បៀស — ដាក់បានច្រើន)",
                                 placeholder="gsk_...\ngsk_...", height=120, key="user_keys_bulk")
        st.toggle("💾 ចងចាំ Key ក្នុងឧបករណ៍/Browser នេះ (ចូលលើកក្រោយមិនបាច់ដាក់ម្តងទៀត)", value=True,
                  key="remember_keys", on_change=_ls_persist)
        st.caption("🔒 Key រក្សាទុកក្នុង Browser របស់អ្នក (localStorage)។ ពេលហៅ API កម្មវិធីប្រើ Key ក្នុង Session របស់អ្នកដើម្បីផ្ញើសំណើទៅ Provider។ "
                   "កុំប្រើលើឧបករណ៍សាធារណៈ។ បើលុបទិន្នន័យ Browser Key អាចបាត់។")
        if st.button("✅ ពិនិត្យ និងបន្ថែម Key", key="user_key_save", use_container_width=True):
            if provider == "Claude":
                _new = [_x for _x in split_keys(typed) if _x.startswith("sk-") and "=" not in _x][:20]
                _base = (oai_base_in or "https://api.laalaa.me").strip().rstrip("/")
                _model = (oai_model_in or "claude-sonnet-5-5").strip()
                _have = list(st.session_state.get("user_claude_keys", []))
                if not _new:
                    st.error("សូមបិទភ្ជាប់ Key យ៉ាងតិច ១។")
                elif not _base.startswith("http"):
                    st.error("Base URL ត្រូវចាប់ផ្តើមដោយ https://")
                else:
                    _added, _dup, _bad = 0, 0, []
                    with st.spinner("កំពុងពិនិត្យ Key..."):
                        for _k in _new:
                            if _k in _have:
                                _dup += 1
                                continue
                            _st, _msg, _ms = check_claude_key((_k, _base, _model))
                            if _st in ("ok", "limit"):
                                _have.append(_k)
                                _added += 1
                            else:
                                _bad.append(f"{mask_key(_k)}: {_msg}")
                    if _added:
                        st.session_state["user_claude_keys"] = _have
                        st.session_state["user_claude_base"] = _base
                        st.session_state["user_claude_model"] = _model
                        _ls_persist()
                    _text = f"បានបន្ថែម {_added} Claude Key ✅"
                    if _dup:
                        _text += f" · ស្ទួន {_dup}"
                    if _bad:
                        _text += f" · មិនត្រឹមត្រូវ {len(_bad)}:\n\n" + "\n\n".join(_bad)
                    st.session_state["_key_msg"] = ("ok" if _added else "warn", _text)
                    if _added:
                        st.session_state["_clear_key_input"] = True
                    st.rerun()
            elif provider == GEMINI_LABEL:
                _gk = str(typed or "").strip()
                _gm = _gm_fix(oai_model_in or GEMINI_DEFAULT_MODEL)
                if len(_gk) < 20 or any(_c.isspace() for _c in _gk):
                    st.error("Gemini Key មិនត្រឹមត្រូវ។ សូមបិទភ្ជាប់ Key ឱ្យពេញ (ចាប់ផ្តើមដោយ AIza)។")
                else:
                    with st.spinner("កំពុងពិនិត្យ Gemini Key..."):
                        _gst, _gmsg, _gms = check_openai_key((_gk, GEMINI_OAI_BASE, _gm))
                    if _gst in ("ok", "limit"):
                        st.session_state["user_gemini_key"] = _gk
                        st.session_state["user_gemini_model"] = _gm
                        _ls_persist()
                        st.session_state["_clear_key_input"] = True
                        st.session_state["_key_msg"] = ("ok", "បានបន្ថែម Gemini Key ✅ (⚠️ មិនណែនាំឱ្យប្រើ)")
                        st.rerun()
                    else:
                        st.error("Gemini Key ប្រើមិនបាន៖ " + str(_gmsg))
            elif provider == "CodeCraft":
                _cc_base = (oai_base_in or "https://codecraftapi.com/v1").strip().rstrip("/")
                ok, msg = oai_test(typed, _cc_base, oai_model_in or "")
                if ok:
                    st.session_state["user_oai_key"] = typed.strip()
                    st.session_state["user_oai_base"] = _cc_base
                    st.session_state["user_oai_model"] = (oai_model_in or "").strip()
                    _ls_persist()
                    st.session_state["_clear_key_input"] = True
                    st.session_state["_key_msg"] = ("ok", "បានបន្ថែម CodeCraft Key ✅")
                    st.rerun()
                else:
                    st.error(msg)
            else:
                sk = "user_groq_keys"
                check = validate_groq_key
                new_keys = split_keys(typed)[:20]
                have = list(st.session_state.get(sk, []))
                if not new_keys:
                    st.error("សូមបិទភ្ជាប់ Key យ៉ាងតិច ១។")
                else:
                    added, dup, bad = 0, 0, []
                    with st.spinner("កំពុងពិនិត្យ Key..."):
                        for k in new_keys:
                            if k in have:
                                dup += 1
                                continue
                            ok, msg = check(k)
                            if ok:
                                have.append(k)
                                added += 1
                            else:
                                bad.append(f"{mask_key(k)}: {msg}")
                    if added:
                        st.session_state[sk] = have
                        _ls_persist()
                    text = f"បានបន្ថែម {added} Key ✅"
                    if dup:
                        text += f" · ស្ទួន {dup}"
                    if bad:
                        text += f" · មិនត្រឹមត្រូវ {len(bad)}:\n\n" + "\n\n".join(bad)
                    st.session_state["_key_msg"] = ("ok" if added else "warn", text)
                    if added:
                        st.session_state["_clear_key_input"] = True
                    st.rerun()
        if st.button("🔍 ពិនិត្យ Key ទាំងអស់ — ណាប្រើបាន ណាប្រើមិនបាន", key="user_key_check_all", use_container_width=True):
            with st.spinner("កំពុងពិនិត្យ..."):
                st.session_state["_key_check"] = {"t": time.time(), "rows": run_key_checks()}
        _kc = st.session_state.get("_key_check")
        if _kc:
            if not _kc["rows"]:
                st.info("មិនទាន់មាន Key ណាមួយទេ។")
            else:
                _icon = {"ok": "✅ ប្រើបាន", "limit": "⚠️ Limit/រវល់", "bad": "❌ មិនត្រឹមត្រូវ", "error": "❌ កំហុស"}
                _c1, _c2, _c3 = st.columns(3)
                _c1.metric("✅ ប្រើបាន", sum(1 for r in _kc["rows"] if r["state"] == "ok"))
                _c2.metric("⚠️ Limit/រវល់", sum(1 for r in _kc["rows"] if r["state"] == "limit"))
                _c3.metric("❌ ប្រើមិនបាន", sum(1 for r in _kc["rows"] if r["state"] in ("bad", "error")))
                st.dataframe(
                    [{"ស្ថានភាព": _icon[r["state"]], "Provider": r["name"], "Key": r["key"],
                      "ម៉ូដែល": r["model"], "ms": r["ms"], "ព័ត៌មាន": r["msg"]} for r in _kc["rows"]],
                    use_container_width=True, hide_index=True)
                for _r in _kc["rows"]:
                    if _r["state"] != "ok":
                        st.warning(f"{_r['name']} · {_r['key']} · {_r['model']}\n\n{_r['msg']}")
                st.caption("ពិនិត្យនៅម៉ោង " + time.strftime("%H:%M:%S", time.localtime(_kc["t"]))
                           + " · ⚠️ = Key ត្រឹមត្រូវ តែ Rate limit/ម៉ាស៊ីនមេរវល់បណ្តោះអាសន្ន (មិនទាន់ច្បាស់ថាអស់កូតាទេ)។")
        if any_saved and st.button("🧹 លុប Key ផ្ទាល់ខ្លួនទាំងអស់ (រួមទាំងក្នុង Browser)", key="user_key_clear_all", use_container_width=True):
            for _k in ("user_groq_keys", "user_oai_key", "user_oai_base", "user_oai_model",
                       "user_claude_keys", "user_claude_base", "user_claude_model",
                       "user_gemini_key", "user_gemini_model", "user_hg_app_id", "user_hg_app_secret", "user_hg_apify"):
                st.session_state.pop(_k, None)
            _ls_persist()
            st.rerun()


# ============================ Hongguo VIP Access ============================
# All VIP checks and management use the server-only Supabase service key.

# ---- Login/VIP system removed per user request ----
def _is_admin_session():
    return True


GEMINI_KEY = ""  # Gemini API ត្រូវបានបិទ និងមិនត្រូវបានប្រើ។
GROQ_KEY = collect_api_keys("GROQ_API_KEY")

ENGINE_FREE = "⭐ Groq សម្គាល់សំឡេង + AI API បកប្រែ (Fallback ស្វ័យប្រវត្តិ)"
ENGINE_OFFLINE = "🧠 Offline AI (គ្មាន API Key)"


st.markdown('<style>\n/* ===== BAK TRAE RUEANG: neon cinematic dashboard refresh ===== */\n:root{--ink:#f6f4ff;--soft:#c4c9f2;--bg:#070a24;--card:#12183b;--card2:#1b2250;--line:rgba(117,130,255,.34);--p1:#d72bff;--p2:#00cfff;--gold:#ffd45a;--r-lg:24px;--r-md:18px;--r-sm:13px}\nhtml,body,[data-testid="stAppViewContainer"]{background:radial-gradient(ellipse at 15% 0%,rgba(31,113,255,.28),transparent 38%),radial-gradient(ellipse at 85% 8%,rgba(193,32,255,.24),transparent 35%),linear-gradient(145deg,#080a25 0%,#10133b 48%,#07152d 100%)!important;color:#f7f5ff!important}\n[data-testid="stHeader"]{background:transparent!important}\n.block-container{max-width:1600px!important;padding:1.15rem 1.4rem 4rem!important}\n.kvai-head{position:relative;overflow:hidden;border:1px solid rgba(0,220,255,.65)!important;border-radius:23px!important;padding:17px 22px!important;background:linear-gradient(100deg,rgba(17,20,59,.96),rgba(41,19,91,.84),rgba(5,68,116,.72))!important;box-shadow:0 0 24px rgba(0,207,255,.19),inset 0 0 30px rgba(211,40,255,.13)!important}\n.kvai-head:after{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(110deg,transparent 35%,rgba(255,255,255,.08) 48%,transparent 60%);background-size:220% 100%;animation:kvai-sweep 8s linear infinite}\n.kvai-title .kvai-h1{color:#fff!important;text-shadow:0 0 14px rgba(0,213,255,.5)!important;font-size:clamp(1.45rem,2.5vw,2.1rem)!important;font-weight:800!important}\n.kvai-title .kvai-h1 span{background:linear-gradient(90deg,#00eaff,#e83bff,#ffcc52);-webkit-background-clip:text;background-clip:text;color:transparent!important}\n.kvai-logo{box-shadow:0 0 17px rgba(221,45,255,.6),0 0 28px rgba(0,210,255,.25)!important;border:1px solid rgba(255,255,255,.28)!important}\n.kvai-badge{border:1px solid #ffd65a!important;background:linear-gradient(120deg,rgba(255,190,30,.2),rgba(255,70,150,.12))!important;color:#ffe17b!important;border-radius:999px!important}\n[data-baseweb="tab-list"]{gap:8px!important;border-bottom:1px solid rgba(127,147,255,.3)!important;padding:5px 2px 12px!important}\nbutton[data-baseweb="tab"]{border:1px solid rgba(115,133,255,.35)!important;border-radius:14px!important;background:linear-gradient(145deg,rgba(26,32,77,.92),rgba(15,20,53,.92))!important;color:#e7e9ff!important;padding:10px 17px!important;min-height:44px!important;transition:all .22s ease!important}\nbutton[data-baseweb="tab"]:hover{border-color:#00d9ff!important;box-shadow:0 0 16px rgba(0,213,255,.25)!important;transform:translateY(-2px)}\nbutton[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(105deg,#d51cff,#6552ff,#00cfff)!important;color:#fff!important;border-color:#a6f5ff!important;box-shadow:0 0 20px rgba(190,44,255,.45),0 0 13px rgba(0,211,255,.25)!important}\n[data-testid="stVerticalBlockBorderWrapper"],.stContainer,[data-testid="stExpander"]{border:1px solid rgba(113,137,255,.35)!important;border-radius:19px!important;background:linear-gradient(145deg,rgba(25,31,76,.88),rgba(12,18,49,.94))!important;box-shadow:0 8px 24px rgba(0,0,0,.16),inset 0 1px rgba(255,255,255,.035)!important}\n.kvai-panel-title{border:1px solid rgba(0,213,255,.45)!important;border-radius:15px!important;background:linear-gradient(100deg,rgba(0,196,255,.17),rgba(190,40,255,.17))!important;padding:9px 13px!important;color:#fff!important;box-shadow:0 0 12px rgba(0,205,255,.1)!important}\n[data-testid="stFileUploaderDropzone"]{border:2px dashed #00dfff!important;border-radius:20px!important;background:linear-gradient(130deg,rgba(0,205,255,.12),rgba(202,37,255,.15))!important;min-height:115px!important;box-shadow:inset 0 0 25px rgba(0,210,255,.09),0 0 16px rgba(0,210,255,.1)!important}\n[data-testid="stFileUploaderDropzone"] *{color:#fff!important}\n.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"] button{border:1px solid rgba(255,255,255,.36)!important;border-radius:15px!important;background:linear-gradient(100deg,#d91cff 0%,#7449ff 48%,#00cfff 100%)!important;color:#fff!important;font-weight:750!important;min-height:43px!important;box-shadow:0 0 17px rgba(190,40,255,.24)!important;transition:transform .2s ease,box-shadow .2s ease!important}\n.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stFormSubmitButton"] button:hover{transform:translateY(-2px)!important;box-shadow:0 0 22px rgba(0,215,255,.42),0 0 18px rgba(214,30,255,.32)!important;border-color:#fff!important}\ninput,textarea,[data-baseweb="select"]>div{background:rgba(20,27,66,.92)!important;color:#fff!important;border-color:rgba(126,144,255,.4)!important;border-radius:12px!important}\n[data-testid="stWidgetLabel"] p,label{color:#e9eaff!important}\n[data-testid="stCaptionContainer"],.stCaption{color:#b9c4ef!important}\n[data-testid="stVideo"] video{border:1px solid rgba(0,220,255,.5)!important;border-radius:17px!important;box-shadow:0 0 18px rgba(0,205,255,.12)!important;max-height:340px!important}\n[data-testid="stSlider"] [role="slider"]{background:#ff35d3!important;box-shadow:0 0 12px #ff35d3!important}\nhr{border-color:rgba(126,144,255,.22)!important}\n@keyframes kvai-sweep{0%{background-position:200% 0}100%{background-position:-200% 0}}\n@media(max-width:850px){.block-container{padding:.65rem .65rem 3rem!important}.kvai-head{padding:12px!important}.kvai-title .kvai-h1{font-size:1.2rem!important}button[data-baseweb="tab"]{padding:8px 10px!important;min-height:39px!important}}\n@media(prefers-reduced-motion:reduce){.kvai-head:after{animation:none!important}*{transition:none!important}}\n</style>\n', unsafe_allow_html=True)

render_header()
# auth_bootstrap()  # login removed
# Mobile-first interface: landscape/fullscreen rotation control intentionally removed.
ls_sync()

if (not GROQ_KEY and not oai_enabled() and not has_user_keys()
        and st.session_state.get("translate_engine_mode") != ENGINE_OFFLINE):
    # Keep the missing-key notice compact so it does not push the dashboard below the fold.
    st.caption("⚠️ មិនទាន់មាន API Key — ជ្រើស Offline AI នៅផ្ទាំង «🌐 បកប្រែ» ដើម្បីប្រើម៉ូដែលក្នុងម៉ាស៊ីន។")

current_job = st.session_state.get("job")
busy = bool(current_job and current_job.running())

voice_label = list(TTS_VOICES.keys())[0]
# មុខងារដែលបើកដោយស្វ័យប្រវត្តិជានិច្ច (គ្មានប៊ូតុងបិទបើក)
sub_on = True
dub_on = True
emotion_on = True
keep_bg = True
auto_gender = True
srt_on = False
narrate_on = False
review_on = False
voice_match = False
emotion = False
clone_on = False
timbre = False
timbre_file = None
dub_offset = 0.0
tight_sync = False

# ប៊ូតុងចាប់ផ្តើម៖ បង្កើត placeholder ក្រោយផ្ទាំងមុខងារ ដើម្បីកុំឱ្យវាទុកចន្លោះទទេនៅលើ Dashboard។

tab_vid, tab_cut, tab_trans, tab_voice, tab_text, tab_fx, tab_out = st.tabs(
    ["🏠 វីដេអូ", "✂️ កាត់", "🌐 បកប្រែ", "🎙 សំឡេង", "🔤 អក្សរ", "🖼 Logo", "⬇️ ទាញយក"]
)


# ============================ ផ្ទាំង ១: វីដេអូ ============================
link_limit = MAX_VIDEOS
with tab_vid:
    col_upload, col_preview, col_controls = st.columns([1.02, 1.05, 1.02], gap="small")
    with col_upload:
        st.markdown('<div class="kvai-panel-title"><span class="kvai-step pink">1</span> បញ្ចូលវីដេអូ</div>', unsafe_allow_html=True)
        with st.container(border=True):
            mode = st.radio("វិធីបញ្ចូលវីដេអូ", ["📁 Upload", "💻 ក្នុងម៉ាស៊ីន", "🔗 Link"], horizontal=True,
                            label_visibility="collapsed", key="mode_pick")
            uploaded_files = []
            local_files = []
            link_text = ""
            link_translate = False
            if mode.startswith("📁"):
                st.markdown(
                    '<div class="btr-upload-hero">'
                    '<div class="btr-upload-SideIcon">🎬</div>'
                    '<div class="btr-upload-center">'
                    '<div class="btr-cloud-icon">☁️⬆️</div>'
                    '<div class="btr-upload-title">បញ្ចូលវីដេអូ (Upload Video)</div>'
                    '<div class="btr-upload- pill-formats">MP4, MOV, MKV, AVI, WEBM (គ្មានកំណត់តាម App)</div>'
                    '</div>'
                    '<div class="btr-upload-SideIcon">🎞️</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                uploaded_files = st.file_uploader(
                    "📂 ជ្រើសរើសវីដេអូ (ជ្រើសបានច្រើន)", type=["mp4", "mov", "mkv", "avi", "webm"],
                    accept_multiple_files=True) or []
            elif mode.startswith("💻"):
                st.caption("💻 រត់លើម៉ាស៊ីនខ្លួនឯង៖ ប្រើវីដេអូពីក្នុងកុំព្យូទ័រដោយផ្ទាល់ មិនបាច់ Upload មិនចូល RAM")
                st.button("📂 រកវីដេអូក្នុងកុំព្យូទ័រ", use_container_width=True, key="local_browse_btn",
                          on_click=_local_browse_cb)
                if st.session_state.get("_local_browse_err"):
                    st.caption("⚠️ មិនអាចបើកប្រអប់រកឯកសារបានទេ។ សូមបិទភ្ជាប់ផ្លូវឯកសារខាងក្រោមជំនួស។")
                local_text = st.text_area(
                    "ផ្លូវឯកសារ ឬថតវីដេអូ", key="local_path_text", height=68,
                    placeholder="C:\\Users\\...\\video.mp4\nមួយបន្ទាត់ ១ ឯកសារ ឬ ១ ថត (ថតនឹងយកវីដេអូទាំងអស់ក្នុងថតនោះ)")
                local_files, _local_bad = resolve_local_videos(local_text)
                if local_files:
                    try:
                        _tot = sum(os.path.getsize(x) for x in local_files) / (1024 ** 3)
                    except OSError:
                        _tot = 0.0
                    _info = f"✅ {len(local_files)} វីដេអូ · 📦 {_tot:.2f}GB"
                    if len(local_files) == 1:
                        try:
                            _dur, _w0, _h0 = probe_media(local_files[0])
                            _info += f" · ⏱ {_dur / 60:.1f} នាទី"
                        except Exception as _swallow_e:
                            _log_swallowed(_swallow_e)
                    st.caption(_info)
                if _local_bad:
                    st.warning("រកមិនឃើញវីដេអូ៖ " + " | ".join(_local_bad[:3]))
            else:
                st.caption("ក្នុង TikTok ចុច Share → Copy link រួចបិទភ្ជាប់តំណក្នុងប្រអប់ខាងក្រោម។")
                link_text = st.text_area(
                    "តំណវីដេអូ (TikTok ឬភាគ Hongguo ដែលបានជ្រើស)",
                    key="link_text_area",
                    placeholder="បិទភ្ជាប់តំណវីដេអូនៅទីនេះ\nដាក់បានច្រើនតំណម្តងតែមួយ (មួយបន្ទាត់ ១ តំណ)",
                    height=68)
                if st.session_state.pop("_hg_imported_caption_notice", False):
                    st.success("បានទទួលភាគ Hongguo ហើយ។ កម្មវិធីនឹងស្វែងរក និងចាប់ផ្ដើមបកប្រែដោយស្វ័យប្រវត្តិ បើតំណវីដេអូអាចទាញយកបាន។")
                _all_links = extract_links(link_text)
                _link_lines = _all_links
                if _all_links:
                    st.caption(f"🔗 រកឃើញ {len(_all_links)} តំណ · គ្មានកំណត់ចំនួនតំណដោយ App")
                _search_label = "🔍 ស្វែងរក" + (f" ({len(_link_lines)} តំណ)" if len(_link_lines) > 1 else "")
                if st.button(_search_label, type="primary", use_container_width=True, key="link_search_btn",
                             disabled=(not _link_lines)):
                    _cache0 = st.session_state.get("link_cache", {})
                    for _u0 in _link_lines:
                        if _u0 in _cache0 and not _cache0[_u0].get("ok"):
                            _cache0.pop(_u0, None)
                    st.session_state["link_searched"] = list(_link_lines)
                _searched = [u for u in st.session_state.get("link_searched", []) if u in _link_lines]
                drop_link_cache(keep=_searched)
                _link_lines = _searched
                if _link_lines:
                    _need = [u for u in _link_lines if u not in st.session_state.get("link_cache", {})]
                    if _need:
                        _ph = st.empty()
                        fetch_links_preview(_link_lines, _ph)
                        _ph.empty()
                _n_ok = 0
                _multi = len(_link_lines) > 1
                for _n, _u in enumerate(_link_lines, start=1):
                    _ent = fetch_link_preview(_u)
                    _box = (st.expander(f"🎬 វីដេអូទី {_n}", expanded=(_n == 1)) if _multi else st.container())
                    with _box:
                        if _ent["ok"] and _ent["path"] and os.path.isfile(_ent["path"]):
                            _n_ok += 1
                            _mb = os.path.getsize(_ent["path"]) / (1024 * 1024)
                            _info = f"📦 {_mb:.0f}MB"
                            try:
                                _dur, _w0, _h0 = probe_media(_ent["path"])
                                _info += f" · ⏱ {_dur / 60:.1f} នាទី"
                                _ssec = get_split_seconds()
                                if _ssec and _dur > _ssec + 20:
                                    _np = int(-(-_dur // _ssec))
                                    _info += f" · ✂️ នឹងបំបែកជា {_np} ផ្នែក (ក្នុងមួយផ្នែក {fmt_len(_ssec)})"
                            except Exception as _swallow_e:
                                _log_swallowed(_swallow_e)
                            st.caption(_info)
                            if _mb <= PREVIEW_MAX_MB:
                                try:
                                    st.video(_ent["path"])
                                except Exception as _swallow_e:
                                    _log_swallowed(_swallow_e)
                            if _mb <= 300:
                                with open(_ent["path"], "rb") as _fh:
                                    dl_button(f"⬇️ ទាញយកវីដេអូទី {_n}", _fh, f"video_{_n}.mp4", "video/mp4",
                                              key=f"dl_link_{_n}", use_container_width=True)
                        else:
                            st.error("រកតំណមិនឃើញទេ ទោះបានព្យាយាមច្រើនលើកហើយ។ សូមចុចព្យាយាមម្តងទៀត។")
                            if _ent.get("err"):
                                st.caption(f"ព័ត៌មានបច្ចេកទេស (បានព្យាយាម {_ent.get('tries', 1)} លើក)")
                                st.code(_ent["err"])
                            if st.button("🔄 ព្យាយាមម្តងទៀត", key=f"retry_link_{_n}", use_container_width=True):
                                st.session_state.get("link_cache", {}).pop(_u, None)
                                st.rerun()
                if _multi:
                    st.caption(f"✅ រកឃើញ {_n_ok} / {len(_link_lines)} វីដេអូ")
                if _n_ok:
                    link_translate = st.button(
                        f"✨ បកប្រែ ({_n_ok} វីដេអូ)" if _n_ok > 1 else "✨ បកប្រែ",
                        type="primary", use_container_width=True, disabled=busy, key="link_translate_btn")
                    if st.session_state.get("_auto_translate") and not busy:
                        st.session_state["_auto_translate"] = False
                        link_translate = True
                elif _link_lines and st.session_state.get("_auto_translate"):
                    st.session_state["_auto_translate"] = False
            if mode.startswith("📁"):
                st.caption(f"ចំនួនវីដេអូ៖ {_MAX_VIDEOS_TXT} · ប្រវែង៖ {_MAX_DUR_TXT}")
            elif mode.startswith("🔗"):
                st.caption(f"ចំនួនតំណ៖ {_MAX_VIDEOS_TXT} · ប្រវែង និងទំហំប៉ុន្មានក៏បាន · វីដេអូវែងអាចបំបែកជាផ្នែកខ្លីៗ (មើលការកំណត់ខាងក្រោម) ហើយធ្វើតាមលំដាប់")
            _ram_txt = server_ram_info()
            if _ram_txt:
                st.caption(_ram_txt)
        with st.expander("⚙️ ការកំណត់វីដេអូបន្ថែម", expanded=False):
            with st.container(border=True):
                quality_label = st.radio("📈 គុណភាពវីដេអូ", list(QUALITY.keys()), index=1,
                                         horizontal=True, key="quality_pick")
            with st.container(border=True):
                st.markdown("**✂️ កាត់វីដេអូវែងជាផ្នែកខ្លីៗ មុនបកប្រែ**")
                auto_split = st.toggle("បំបែកវីដេអូវែងជាផ្នែកខ្លីៗ ហើយបកប្រែម្តងមួយផ្នែក",
                                       value=False, key="auto_split_toggle")
                split_sec = 0
                split_exact = False
                if auto_split:
                    _split_labels = list(SPLIT_PRESETS.keys())
                    _split_lbl = st.selectbox("ប្រវែងមួយផ្នែក", _split_labels,
                                              index=_split_labels.index("៦ នាទី"), key="split_len_pick")
                    split_sec = SPLIT_PRESETS[_split_lbl]
                    split_exact = st.checkbox("🎯 កាត់ឱ្យចំពេលវេលា (យឺតជាង — encode ឡើងវិញ)", key="split_exact_pick")
                    st.caption(f"វីដេអូវែងជាង {fmt_len(split_sec + 20)} នឹងត្រូវបំបែក ហើយផ្នែកនីមួយៗបកប្រែតាមលំដាប់។ "
                               "ចង់កាត់ទាញយកទុកតែមួយៗ សូមប្រើផ្ទាំង «✂️ កាត់»។")

 
    with col_preview:
        st.markdown('<div class="kvai-panel-title"><span class="kvai-step blue">2</span> មើលជាមុន</div>', unsafe_allow_html=True)
        _dash_preview = uploaded_files[0] if uploaded_files else None
        _prev_note = None
        # វីដេអូធំ → មិនបង្ហាញ Preview ដើម្បីសន្សំ RAM (getvalue() ចម្លងទាំងមូលចូល RAM)
        if _dash_preview is not None and getattr(_dash_preview, "size", 0) > PREVIEW_MAX_MB * 1024 * 1024:
            _prev_note = f"🎬 {_dash_preview.name} · {_dash_preview.size / (1024 * 1024):.0f}MB — ធំពេក មិនបង្ហាញ Preview ដើម្បីសន្សំ RAM"
            _dash_preview = None
        elif _dash_preview is None and local_files:
            _lp = local_files[0]
            try:
                _lmb = os.path.getsize(_lp) / (1024 * 1024)
            except OSError:
                _lmb = 0
            if _lmb <= PREVIEW_MAX_MB:
                _dash_preview = _lp
            else:
                _prev_note = f"🎬 {os.path.basename(_lp)} · {_lmb:.0f}MB — ធំពេក មិនបង្ហាញ Preview ដើម្បីសន្សំ RAM"
        if _dash_preview is None and not _prev_note:
            _dash_cache = st.session_state.get("link_cache", {})
            for _u in st.session_state.get("link_searched", []):
                _ent = _dash_cache.get(_u, {})
                if _ent.get("ok") and _ent.get("path") and os.path.isfile(_ent["path"]):
                    _dash_preview = _ent["path"]
                    break
        if _dash_preview is not None:
            try:
                # Use stable bytes for UploadedFile previews so the player can load reliably.
                _preview_payload = (_dash_preview.getvalue()
                                    if hasattr(_dash_preview, "getvalue") else _dash_preview)
                st.video(_preview_payload)
                if uploaded_files:
                    st.caption(f"🎬 {uploaded_files[0].name}")
                elif local_files:
                    st.caption(f"🎬 {os.path.basename(local_files[0])}")
            except Exception:
                st.info("មិនអាចបង្ហាញ Preview បានទេ។")
        elif _prev_note:
            st.info(_prev_note)
        else:
            st.markdown('<div class="kvai-empty-preview"><div class="kvai-play">▶</div><b>វីដេអូរបស់អ្នកនឹងបង្ហាញនៅទីនេះ</b><small>Upload ឬដាក់ Link ដើម្បីមើលជាមុន</small></div>', unsafe_allow_html=True)
        st.markdown('<div class="kvai-filmstrip">🎞️　✨　🎬　✨　🎞️</div>', unsafe_allow_html=True)
        st.caption("គាំទ្រ MP4 · MOV · MKV · AVI · WEBM")
    with col_controls:
        st.markdown('<div class="kvai-panel-title"><span class="kvai-step pink">3</span> កំណត់ AI</div>', unsafe_allow_html=True)
        with st.container(border=True):
            voice_label = st.radio("🎙 សំឡេងនិយាយ", list(TTS_VOICES.keys()), horizontal=True, key="voice_pick")
            # រក្សាសំឡេងដើមបើកជាលំនាំដើម ដើម្បីកុំឱ្យសំឡេងវីដេអូដើមបាត់ក្នុងលទ្ធផល។
            # ប្រើ key ថ្មី ដើម្បីឱ្យ session ចាស់ដែលធ្លាប់រក្សា False មិនបិទវាដោយស្វ័យប្រវត្តិ។
            keep_bg = st.toggle("🎵 រក្សាសំឡេងដើម", value=True, key="keep_bg_toggle_v2")
            dub_offset = st.slider(
                "⏱️ រំកិលពេលសំឡេង (វិនាទី)", -3.0, 3.0, 0.0, 0.1, key="dub_offset_pick",
                help="ប្រសិនបើសំឡេងមកយឺតជាងកាយវិការជានិច្ច សូមដាក់លេខអវិជ្ជមាន (សំឡេងមកមុន)។ បើមកលឿនពេក សូមដាក់លេខវិជ្ជមាន។")
            bg_level = st.slider("កម្រិតសំឡេងដើម (%)", 2, 60, 15, key="bg_level_pick_v2") if keep_bg else 8
            _GM_AUTO = "🤖 AI ស្វែងរកស្វ័យប្រវត្តិ"
            _GM_FEMALE = "👩 ស្រីទាំងអស់"
            _GM_MALE = "👨 ប្រុសទាំងអស់"
            _GM_MANUAL = "✋ ជ្រើសរើសខ្លួនឯង (រៀងបន្ទាត់)"
            gender_mode = st.radio(
                "🎭 សំឡេងប្រុស/ស្រី", [_GM_AUTO, _GM_FEMALE, _GM_MALE, _GM_MANUAL],
                index=0, key="gender_mode_pick",
                help="ស្វ័យប្រវត្តិ៖ AI ទាយ។ ស្រី/ប្រុសទាំងអស់៖ ប្រើសំឡេងតែមួយ។ ជ្រើសរើសខ្លួនឯង៖ មុនដាក់សំឡេង app នឹងបង្ហាញបញ្ជីឃ្លា ឱ្យអ្នកកំណត់ប្រុស/ស្រីរៀងបន្ទាត់។")
            auto_gender = gender_mode in (_GM_AUTO, _GM_MANUAL)
            if gender_mode == _GM_FEMALE:
                voice_label = next(k for k, v in TTS_VOICES.items() if v == VOICE_FEMALE)
            elif gender_mode == _GM_MALE:
                voice_label = next(k for k, v in TTS_VOICES.items() if v == VOICE_MALE)
            if gender_mode == _GM_MANUAL:
                st.caption("✋ App នឹងឈប់រង់ចាំអ្នកមុនដាក់សំឡេង ដើម្បីកំណត់ប្រុស/ស្រីរៀងបន្ទាត់ (AI ដាក់ការទាយឱ្យជាមុន)។")
            st.caption("AI បង្កើតសំឡេងខ្មែរដោយស្វ័យប្រវត្តិ")
        with st.expander("🔤 កំណត់ Subtitle និងរូបរាងអក្សរ", expanded=False):
            _review_toggle = st.toggle("✏️ ពិនិត្យអក្សរមុនបង្កើត", value=False, key="review_toggle")
            review_on = bool(_review_toggle) or (gender_mode == _GM_MANUAL)
            _f1, _f2 = st.columns(2)
            with _f1:
                font_name = st.selectbox("Font", [f[2] for f in FONT_SOURCES], index=0, key="font_pick")
                color_pick = st.selectbox("ពណ៌អក្សរ", list(COLOR_OPTIONS.keys()), index=0, key="color_pick")
            with _f2:
                box_pick = st.selectbox("ផ្ទៃក្រោយ", list(BOX_OPTIONS.keys()), index=0, key="box_pick")
                style_pick = st.selectbox("បែបអក្សរ", list(STYLE_OPTIONS.keys()), index=0, key="style_pick")
            font_size_on = st.toggle("កែទំហំអក្សរ", value=False, key="font_size_on")
            font_size = st.slider("ទំហំអក្សរ", 16, 36, 16, key="font_size_pick") if font_size_on else 16
            outline_size = st.slider("គែមអក្សរ", 1, 5, 2, key="outline_size_pick")
            pos_pick = st.radio("ទីតាំងអក្សរ", list(POS_MAP.keys()), index=7, horizontal=True, key="pos")
        bold_, italic_ = STYLE_OPTIONS[style_pick]
# ============================ ផ្ទាំង កាត់វីដេអូ ============================
with tab_cut:
    with st.container(border=True):
        st.markdown("**✂️ កាត់វីដេអូវែងជាវីដេអូខ្លីៗ**")
        st.caption("កាត់វីដេអូវែងជាផ្នែកខ្លីៗ រួចទាញយកទុក ឬផ្ញើទៅបកប្រែម្តងមួយផ្នែក។")
        _cache_c = st.session_state.get("link_cache", {})
        _link_src = [(u, _cache_c[u]["path"]) for u in st.session_state.get("link_searched", [])
                     if _cache_c.get(u, {}).get("ok") and _cache_c[u].get("path")
                     and os.path.isfile(_cache_c[u]["path"])]
        _src_opts = ["📁 Upload", "🔗 Link"] + (["🎬 ពីផ្ទាំងវីដេអូ"] if _link_src else [])
        cut_src_mode = st.radio("ប្រភព", _src_opts, horizontal=True,
                                key="cut_src_mode", label_visibility="collapsed")
        cut_path = None
        cut_name = "video"
        cut_up = None
        if cut_src_mode.startswith("📁"):
            cut_up = st.file_uploader("ជ្រើសវីដេអូវែង", type=["mp4", "mov", "mkv", "avi", "webm"],
                                      key="cut_upload")
            if cut_up is not None:
                cut_name = os.path.splitext(cut_up.name)[0]
        elif cut_src_mode.startswith("🔗"):
            st.caption("បិទភ្ជាប់តំណវីដេអូ (TikTok ឬតំណផ្សេង) ១ តំណ រួចចុច «ស្វែងរកវីដេអូ» — ទំហំនិងប្រវែងប៉ុន្មានក៏បាន។")
            _cut_url_text = st.text_area("តំណវីដេអូ", key="cut_link_text", height=90,
                                         placeholder="បិទភ្ជាប់តំណវីដេអូនៅទីនេះ")
            _cut_urls = extract_links(_cut_url_text)
            _cl = st.session_state.get("cut_link")
            if st.button("🔍 ស្វែងរកវីដេអូ", use_container_width=True, disabled=not _cut_urls,
                         key="cut_link_search"):
                if _cl and _cl.get("path"):
                    shutil.rmtree(os.path.dirname(_cl["path"]), ignore_errors=True)
                _ph_c = st.empty()

                def _cb_c(attempt):
                    _ph_c.info(f"⏳ កំពុងរកវីដេអូ · ព្យាយាមលើកទី {attempt}/{LINK_RETRIES}")

                _ent_c = _fetch_one(_cut_urls[0], _cb_c)
                _ph_c.empty()
                st.session_state["cut_link"] = dict(_ent_c, url=_cut_urls[0])
                _cl = st.session_state["cut_link"]
            if _cl and _cl.get("url") in _cut_urls:
                if _cl.get("ok") and _cl.get("path") and os.path.isfile(_cl["path"]):
                    cut_path = _cl["path"]
                    cut_name = "video_link"
                    _info_c = f"📦 {os.path.getsize(cut_path) / (1024 * 1024):.0f}MB"
                    try:
                        _info_c += f" · ⏱ {fmt_clock(probe_media(cut_path)[0])}"
                    except Exception as _swallow_e:
                        _log_swallowed(_swallow_e)
                    st.success("✅ រកឃើញវីដេអូហើយ · " + _info_c)
                else:
                    st.error("រកតំណមិនឃើញទេ។ សូមសាកម្តងទៀត។")
                    if _cl.get("err"):
                        st.code(_cl["err"])
            elif _cut_urls:
                st.caption("ចុច «ស្វែងរកវីដេអូ» ជាមុនសិន។")
        else:
            _pick = st.selectbox("ជ្រើសវីដេអូ", list(range(len(_link_src))),
                                 format_func=lambda i: f"វីដេអូទី {i + 1}", key="cut_link_pick")
            cut_path = _link_src[_pick][1]
            cut_name = f"video_{_pick + 1}"
            try:
                _cd, _cw, _ch = probe_media(cut_path)
                st.caption(f"⏱ {fmt_clock(_cd)}")
            except Exception as _swallow_e:
                _log_swallowed(_swallow_e)
        _cut_opts = list(SPLIT_PRESETS.keys()) + ["✏️ កំណត់ខ្លួនឯង"]
        _cut_default = next((i for i, v in enumerate(_cut_opts) if "១ នាទី" in v or "1 នាទី" in v or "60" in v), 0)
        _cut_lbl = st.selectbox("ប្រវែងមួយផ្នែក", _cut_opts, index=_cut_default, key="cut_len_pick")
        if _cut_lbl.startswith("✏️"):
            cut_sec = int(st.number_input("ប្រវែងមួយផ្នែក (វិនាទី)", min_value=5, max_value=3600,
                                          value=90, step=5, key="cut_len_custom"))
        else:
            cut_sec = SPLIT_PRESETS[_cut_lbl]
        cut_exact = st.checkbox("🎯 កាត់ឱ្យចំពេលវេលា (យឺតជាង — encode ឡើងវិញ)", key="cut_exact_pick")
        st.caption("លំនាំដើមកាត់ដោយមិន encode ដូច្នេះលឿនណាស់ តែចុងផ្នែកអាចខុសពីប្រវែងដែលជ្រើសបន្តិច (កាត់តាម keyframe)។")
        _can_cut = (cut_up is not None) or bool(cut_path)
        _gc1, _gc2 = st.columns(2)
        with _gc1:
            _go_cut = st.button("✂️ កាត់ទុក", type="primary", use_container_width=True,
                                disabled=not _can_cut, key="cut_go_btn")
        with _gc2:
            _go_cut_tr = st.button("✂️✨ កាត់ ហើយបកប្រែតែម្តង", type="primary", use_container_width=True,
                                   disabled=(not _can_cut) or busy, key="cut_go_tr_btn")
        if _go_cut or _go_cut_tr:
            _old = st.session_state.pop("cut_result", None)
            if _old:
                shutil.rmtree(_old["folder"], ignore_errors=True)
            st.session_state.pop("_cut_sent", None)
            st.session_state.pop("_split_queue", None)
            _fold = tempfile.mkdtemp(prefix="kcut_")
            try:
                with st.spinner("កំពុងកាត់វីដេអូ..."):
                    _own = False
                    if cut_up is not None and cut_src_mode.startswith("📁"):
                        _csrc = os.path.join(_fold, "src.bin")
                        with open(_csrc, "wb") as _fh:
                            _fh.write(cut_up.getbuffer())
                        _own = True
                    else:
                        _csrc = cut_path
                    _cdur = probe_media(_csrc)[0]
                    if _cdur <= cut_sec + 1:
                        raise UserError("វីដេអូខ្លីជាងប្រវែងដែលបានជ្រើស។ សូមជ្រើសប្រវែងខ្លីជាងនេះ។")
                    _files = cut_clips(_csrc, _fold, "clip_", cut_sec, cut_exact)
                    if _own:
                        try:
                            os.remove(_csrc)
                        except OSError:
                            pass
                    if not _files:
                        raise UserError("កាត់វីដេអូមិនបានទេ។ សូមសាកម្តងទៀត ឬបើក «កាត់ឱ្យចំពេលវេលា»។")
                    _parts, _t = [], 0.0
                    for _k, _pp in enumerate(_files, start=1):
                        try:
                            _d = probe_media(_pp)[0]
                        except Exception:
                            _d = float(cut_sec)
                        _parts.append({"name": f"{safe_filename(cut_name)}_part{_k:02d}.mp4",
                                       "label": f"ផ្នែក {_k}", "path": _pp, "start": _t, "dur": _d,
                                       "mb": os.path.getsize(_pp) / (1024 * 1024)})
                        _t += _d
                    _zip = None
                    if sum(x["mb"] for x in _parts) <= MAX_ZIP_MB:
                        _zip = os.path.join(_fold, "clips.zip")
                        with zipfile.ZipFile(_zip, "w", zipfile.ZIP_STORED) as _z:
                            for x in _parts:
                                _z.write(x["path"], x["name"])
                    st.session_state["cut_result"] = {"folder": _fold, "parts": _parts,
                                                      "zip": _zip, "base": cut_name}
            except Exception as _e:
                shutil.rmtree(_fold, ignore_errors=True)
                st.error(str(_e) if isinstance(_e, UserError) else friendly_message(_e))
            _cr = st.session_state.get("cut_result")
            if _go_cut_tr and _cr:
                _nn = len(_cr["parts"])
                st.session_state["_split_queue"] = [
                    {"name": f"{_cr['base']} · ផ្នែក {k}/{_nn}", "path": x["path"]}
                    for k, x in enumerate(_cr["parts"], start=1)]
                st.session_state["_run_split"] = True
                st.session_state["_cut_sent"] = min(_nn, SPLIT_QUEUE_MAX)
                st.rerun()

    if st.session_state.get("_cut_sent") and st.session_state.get("job"):
        st.info(f"✅ បានផ្ញើ {st.session_state['_cut_sent']} ផ្នែកទៅបកប្រែហើយ — មើលនៅផ្ទាំង ⬇️ ទាញយក។")

    _res = st.session_state.get("cut_result")
    if _res and all(os.path.isfile(x["path"]) for x in _res["parts"]):
        _n = len(_res["parts"])
        with st.container(border=True):
            st.markdown(f"**✅ កាត់បាន {_n} ផ្នែក**")
            for _i, x in enumerate(_res["parts"], start=1):
                with st.container(border=True):
                    st.markdown(f"**{x['label']}** · {fmt_clock(x['start'])} → "
                                f"{fmt_clock(x['start'] + x['dur'])} · {x['mb']:.0f}MB")
                    _bc1, _bc2 = st.columns(2)
                    with _bc1:
                        with open(x["path"], "rb") as _fh:
                            dl_button("⬇️ ទាញយក", _fh, x["name"], "video/mp4",
                                      key=f"cutdl_{_i}", use_container_width=True)
                    with _bc2:
                        if st.button("✨ បកប្រែ", type="primary", use_container_width=True,
                                     disabled=busy, key=f"cut_tr_{_i}"):
                            st.session_state["_split_queue"] = [
                                {"name": f"{_res['base']} · {x['label']}/{_n}", "path": x["path"]}]
                            st.session_state["_run_split"] = True
                            st.session_state["_cut_sent"] = 1
                            st.rerun()
                    if x["mb"] <= PREVIEW_MAX_MB:
                        with st.expander("▶️ មើលវីដេអូ"):
                            st.video(x["path"])
            if _res.get("zip") and os.path.isfile(_res["zip"]):
                with open(_res["zip"], "rb") as _zf:
                    dl_button("📦 ទាញយកទាំងអស់ (ZIP)", _zf, f"{safe_filename(_res['base'])}_parts.zip",
                              "application/zip", key="cut_zip_dl", use_container_width=True)
            _c1, _c2 = st.columns(2)
            with _c1:
                _lbl_tr = f"✨ បកប្រែ {_n} ផ្នែកនេះ"
                if st.button(_lbl_tr, type="primary", use_container_width=True, disabled=busy,
                             key="cut_translate_btn"):
                    st.session_state["_split_queue"] = [
                        {"name": f"{_res['base']} · ផ្នែក {k}/{_n}", "path": x["path"]}
                        for k, x in enumerate(_res["parts"], start=1)]
                    st.session_state["_run_split"] = True
                    st.session_state["_cut_sent"] = min(_n, SPLIT_QUEUE_MAX)
                    st.rerun()
            with _c2:
                if st.button("🗑 លុបលទ្ធផលកាត់", use_container_width=True, key="cut_clear_btn"):
                    shutil.rmtree(_res["folder"], ignore_errors=True)
                    st.session_state.pop("cut_result", None)
                    st.session_state.pop("_split_queue", None)
                    st.session_state.pop("_cut_sent", None)
                    st.rerun()
    elif _res:
        st.session_state.pop("cut_result", None)

# ============================ ផ្ទាំង ២: បកប្រែ ============================
with tab_trans:
    with st.container(border=True):
        engine_options = [ENGINE_OFFLINE, ENGINE_FREE]  # Offline = default (no API key)
        engine_label = st.selectbox(
            "ម៉ាស៊ីនដំណើរការ", engine_options, index=0,
            key="translate_engine_mode",
        )
        offline_on = engine_label == ENGINE_OFFLINE
        if not offline_on and not effective_groq_key():
            st.warning("សូមដាក់ Groq API Key សម្រាប់សម្គាល់សំឡេង និងកំណត់ API បកប្រែយ៉ាងហោចណាស់មួយក្នុង Secrets ឬបញ្ចូល CodeCraft Key ផ្ទាល់ខ្លួន។ ឬប្តូរទៅ Offline AI។")
        _TS_STD = "⚖️ ស្តង់ដារ (ស្ទីលដើមរបស់ app)"
        _TS_CRE = "🎨 បកបែកកប្លែង (ច្នៃប្រឌិត)"
        _TS_SMO = "🌊 បកបែប Smooth (រលូន)"
        _ts_pick = st.radio("✍️ របៀបបកប្រែ", [_TS_STD, _TS_CRE, _TS_SMO], index=0,
                            horizontal=True, key="trans_style_pick")
        _ts_tails = st.toggle("🐾 បន្ថែមកន្ទុយប្រយោគ (ណា, ហ្នឹងហើយ, ទេតើ...)", value=False, key="trans_tails_pick")
        _trans_style_store().update({
            "base": {_TS_CRE: "creative", _TS_SMO: "smooth"}.get(_ts_pick, "std"),
            "tails": bool(_ts_tails),
        })
        if offline_on and (_ts_pick != _TS_STD or _ts_tails):
            st.caption("ℹ️ របៀបបកប្រែនេះប្រើបានតែជាមួយម៉ាស៊ីន API ប៉ុណ្ណោះ។ ម៉ាស៊ីន Offline (MADLAD) មិនគាំទ្រស្ទីលទេ។")
        offline_whisper_choice = None
        if offline_on:
            offline_whisper_choice = st.selectbox(
                "ម៉ូដែលស្តាប់សំឡេង (Whisper)", list(OFFLINE_WHISPER_REPOS.keys()), index=0,
                key="offline_whisper_choice",
            )
            st.success("🧠 Offline Mode បានជ្រើសរើស៖ ស្តាប់ បកប្រែ និងបង្កើតសំឡេងក្នុងកុំព្យូទ័រ ដោយមិនហៅ Groq/Claude/Gemini ឬ API Key។")
            st.markdown("""
**ម៉ូដែលគុណភាពខ្ពស់ដែល Offline Mode ប្រើ**
- **Whisper large-v3** — សម្គាល់សំឡេងច្រើនភាសា និងពេលវេលាឃ្លា (ទាញយកប្រហែល 3.1GB)។
- **MADLAD-400 3B INT8** — បកប្រែអត្ថបទទៅខ្មែរ (ទាញយកប្រហែល 3GB)។
- **VoxCPM2 2B** — បង្កើតសំឡេងខ្មែរ និងក្លូនសំឡេងតាមគំរូតួអង្គ (ត្រូវការម៉ូដែលច្រើន GB បន្ថែម)។

ម៉ូដែលត្រូវទាញយកតាមអ៊ីនធឺណិតម្តងដំបូង។ ពេលទាញយករួច វាអាចដំណើរការដោយគ្មាន API និងគ្មានអ៊ីនធឺណិត។ ម៉ាស៊ីន Offline នឹងដំណើរការ AI ម្តងមួយវីដេអូ ដើម្បីកាត់បន្ថយការប្រើ RAM/VRAM ខ្លាំង។
            """)
            st.warning("⚠️ ម៉ូដែលធំៗនេះត្រូវការ RAM/VRAM និងទំហំ Disk ច្រើន។ បើគ្មាន GPU ការដំណើរការលើ CPU អាចយឺតខ្លាំង។ VoxCPM2 ត្រូវការ Python 3.10–3.12 និង PyTorch 2.5+។ សូមកុំដំឡើង PyTorch ជំនួស Environment ចាស់ដោយមិន Backup ព្រោះវាអាចប៉ះពាល់ OpenVoice ចាស់។")
            with st.expander("🛠️ Dependencies សម្រាប់ Offline AI (មិនដំឡើងស្វ័យប្រវត្តិ ដើម្បីរក្សា Environment ចាស់)"):
                st.code("pip install faster-whisper ctranslate2 sentencepiece huggingface_hub\npip install voxcpm soundfile", language="powershell")
                st.caption("ណែនាំឱ្យ Backup ឬបង្កើត Python 3.11 venv ដាច់ដោយឡែកមុនដំឡើង។ ប្រសិនបើ voxcpm ធ្វើឱ្យ PyTorch ឬ OpenVoice ចាស់មានបញ្ហា សូមកុំដំឡើងលើ Environment ដើម។")
        else:
            st.caption("Groq ប្រើសម្រាប់សម្គាល់សំឡេង។ Claude ជាម៉ាស៊ីនបកប្រែសំខាន់ (ត្រូវការ Claude API Key) រួចបន្តទៅ Provider បម្រុងដែលម្ចាស់កម្មវិធីបានកំណត់ក្នុង Secrets។")
            with st.expander("🌐 API ដែលអាចភ្ជាប់តាម Secrets"):
                st.markdown("""
                - `ANTHROPIC_API_KEY` (ឬ `ANTHROPIC_API_KEYS = ["key1", "key2"]` / `ANTHROPIC_API_KEY_1`, `_2`), `ANTHROPIC_BASE_URL` (មិនចាំបាច់), `ANTHROPIC_MODEL` (មិនចាំបាច់)
                - `CODECRAFT_API_KEY`, `CODECRAFT_BASE_URL`, `CODECRAFT_MODEL`
                - `OPENROUTER_API_KEYS = ["key1", "key2", ...]` ឬ `OPENROUTER_API_KEY_1`, `OPENROUTER_API_KEY_2` និង `OPENROUTER_MODEL` (Base URL លំនាំដើម `https://openrouter.ai/api/v1`)
                - `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_BASE_URL`, `CLOUDFLARE_MODEL` (Base URL ត្រូវមាន Account ID)
                - `MISTRAL_API_KEY`, `MISTRAL_MODEL`
                - `NVIDIA_API_KEY`, `NVIDIA_MODEL`
                - `COHERE_API_KEY`, `COHERE_MODEL`
                - `SAMBANOVA_API_KEY`, `SAMBANOVA_MODEL`

                Provider នឹងត្រូវបានរំលងដោយស្វ័យប្រវត្តិ ប្រសិនបើគ្មាន Key។ API Key មិនត្រូវបង្ហាញដល់អ្នកប្រើធម្មតាទេ។
                """)
        lc1, lc2 = st.columns(2)
        with lc1:
            language_label = st.selectbox("ភាសាដើម", list(LANGUAGES.keys()), index=0)
        with lc2:
            st.selectbox("បកប្រែទៅ", ["🇰🇭 ខ្មែរ"], disabled=True, key="target_lang")
    with st.container(border=True):
        st.caption("✅ អក្សររត់ខ្មែរ និងសំឡេងអានខ្មែរ ត្រូវបានបើកដោយស្វ័យប្រវត្តិ។")
        st.caption("🎙️ សំឡេងត្រូវបានតម្រឹមតាមពេលវេលានិយាយដើម។")
    if not offline_on:
        user_key_box()

def clone_sample_bytes(upload):
    """បម្លែងសំឡេងគំរូជា wav 16kHz mono (ត្រឹម ៩០ វិនាទី)។ ត្រឡប់ None បើមិនបាន។"""
    if upload is None:
        return None
    raw = upload.getvalue()
    tmp = tempfile.mkdtemp(prefix="kclone_")
    try:
        src = os.path.join(tmp, "in.bin")
        dst = os.path.join(tmp, "out.wav")
        with open(src, "wb") as fh:
            fh.write(raw)
        run_ffmpeg(["-i", src, "-vn", "-ac", "1", "-ar", "16000", "-t", "90", dst])
        with open(dst, "rb") as fh:
            return fh.read()
    except Exception:
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================ ផ្ទាំង ៣: សំឡេង ============================
with tab_voice:
    try:
        import voice_clone as _vc
        _mode, _mode_msg = _vc.status()
    except Exception as _vc_import_error:
        _vc = None
        _mode = "install"
        _mode_msg = "មិនទាន់ដំឡើង OpenVoice Engine ទេ។ អ្នកនៅតែអាចដាក់សំឡេងគំរូ និងប្រើការផ្គូផ្គង pitch/EQ; សម្រាប់ការក្លូនសំឡេងពិត សូមដំឡើង OpenVoice Engine ក្នុង Folder Dubbing។"

    st.markdown("### 🎭 ក្លូនសំឡេងច្រើនតួអង្គ")
    st.caption("ដាក់សំឡេងគំរូដាច់ដោយឡែកសម្រាប់តួអង្គនីមួយៗ។ ប្រព័ន្ធវិភាគ pitch ដើម្បីផ្គូផ្គងឃ្លាទៅតួអង្គ ហើយ Offline Mode ប្រើ VoxCPM2 ក្លូនសំឡេងដោយផ្ទាល់។")
    with st.container(border=True):
        if offline_on:
            st.success("🧠 Offline Mode៖ ការក្លូនសំឡេងតួអង្គនឹងប្រើ VoxCPM2 2B ដោយផ្ទាល់។ មិនចាំបាច់ដំឡើង OpenVoice V1 ទេ។")
        elif _mode == "real":
            st.success(_mode_msg)
        elif _mode == "needs_model":
            st.warning(_mode_msg)
            if st.button("⬇️ ទាញយក Voice Clone Model (ប្រហែល 131MB)", key="clone_download_model"):
                try:
                    _bar = st.progress(0.0)
                    def _clone_dl_progress(done, total):
                        if total:
                            _bar.progress(min(1.0, done / total))
                    with st.spinner("កំពុងទាញយក OpenVoice model..."):
                        _vc.download_model(progress=_clone_dl_progress)
                    st.success("ទាញយក Voice Clone Model បានរួចរាល់។ សូម Refresh App ម្តង។")
                    st.rerun()
                except Exception as _download_error:
                    st.error(f"ទាញយក Model មិនបាន៖ {_download_error}")
        else:
            st.info(_mode_msg)
            st.caption("ដំឡើង Engine ម្តងគត់ដោយបើក INSTALL_VOICE_CLONE.bat។ វានឹងដំឡើង PyTorch CPU, OpenVoice និងឯកសារចាំបាច់។")

        clone_consent = st.checkbox(
            "ខ្ញុំមានសិទ្ធិប្រើសំឡេងគំរូទាំងនេះ ឬបានការយល់ព្រមពីម្ចាស់សំឡេង។",
            value=False, key="clone_voice_consent"
        )
        clone_on = st.toggle(
            "ប្រើសំឡេងគំរូដាច់ដោយឡែកសម្រាប់តួអង្គនីមួយៗ",
            value=False, key="clone_toggle", disabled=(not clone_consent)
        )
        if clone_on and offline_on:
            st.info("VoxCPM2 នឹងយកសំឡេងគំរូរបស់តួអង្គនីមួយៗ ដើម្បីបង្កើតសំឡេងខ្មែរដោយផ្ទាល់។ ត្រូវទាញយក VoxCPM2 Model មុនប្រើលើកដំបូង។")
        elif clone_on and _mode != "real":
            st.info(
                "អាចដាក់សំឡេងគំរូបាន។ កម្មវិធីនឹងប្រើការផ្គូផ្គង pitch និងពណ៌សំឡេង (EQ) តាមតួអង្គ។ "
                "ការក្លូនសំឡេងពិតក្នុង Online Mode ត្រូវការដំឡើង OpenVoice Engine បន្ថែម។"
            )
        clone_files = []
        clone_names = []
        if clone_on:
            _n_chars = st.slider("ចំនួនតួអង្គ / សំឡេងគំរូ", 1, 12, 2, key="clone_n")
            for _ci in range(_n_chars):
                with st.container(border=True):
                    _cname = st.text_input(
                        f"ឈ្មោះតួអង្គទី {_ci + 1}", value=f"តួអង្គ {_ci + 1}", key=f"clone_name_{_ci}"
                    )
                    _cf = st.file_uploader(
                        "🎭 សំឡេងគំរូ (mp3 / wav / m4a / mp4)",
                        type=["mp3", "wav", "m4a", "mp4", "ogg", "flac"], key=f"clone_upl_{_ci}"
                    )
                    if _cf is not None:
                        st.audio(_cf.getvalue())
                        clone_files.append(_cf)
                        clone_names.append(_cname.strip() or f"តួអង្គ {_ci + 1}")
            st.caption(
                "សំឡេងគំរូគួរតែមានអ្នកនិយាយម្នាក់ឯង 10–30 វិនាទីឡើងទៅ ច្បាស់ គ្មានភ្លេងខ្លាំង។ "
                "សម្រាប់ការផ្គូផ្គងល្អ សូមយកសំឡេងតួអង្គដែល pitch ខុសគ្នាច្បាស់ៗ។ "
                + ("Offline VoxCPM2 នឹងក្លូនសំឡេងគំរូដោយផ្ទាល់។" if offline_on else
                   "Online Mode ប្រើ OpenVoice V1 ប្រសិនបើ Engine និង Model បានដំឡើង; បើមិនទាន់ដំឡើង នឹងប្រើ EQ profile ជំនួស។")
                + " CPU-only អាចយឺតជាង GPU។"
            )

            with st.expander("🧪 សាកល្បងសំឡេងតួអង្គ"):
                _t_text = st.text_input("អក្សរសាកល្បង", value="សួស្តី នេះគឺជាសំឡេងសាកល្បង", key="clone_test_text")
                _t_voice = st.radio("សំឡេងមូលដ្ឋាន", list(TTS_VOICES.keys()), horizontal=True, key="clone_test_voice")
                _t_idx = st.selectbox(
                    "យកគំរូរបស់តួអង្គ", list(range(len(clone_files))) or [0],
                    format_func=lambda i: clone_names[i] if i < len(clone_names) else f"តួអង្គទី {i + 1}",
                    key="clone_test_idx"
                )
                if st.button("▶️ បង្កើតសំឡេងសាកល្បង", key="clone_test_btn", disabled=(not clone_files or (_mode != "real" and not offline_on))):
                    _td = tempfile.mkdtemp(prefix="kclone_t_")
                    try:
                        _ref = os.path.join(_td, "ref.wav")
                        _rb = clone_sample_bytes(clone_files[min(_t_idx, len(clone_files) - 1)])
                        if not _rb:
                            raise RuntimeError("សំឡេងគំរូមិនអាចបម្លែងបាន។ សូមប្រើឯកសារសំឡេងច្បាស់ជាងនេះ។")
                        with open(_ref, "wb") as _fh:
                            _fh.write(_rb)
                        _res = os.path.join(_td, "cloned.wav")
                        if offline_on:
                            if offline_voxcpm_synthesize(_t_text, _res, _ref):
                                with open(_res, "rb") as _fh:
                                    st.audio(_fh.read(), format="audio/wav")
                                st.success("សាកល្បង VoxCPM2 Offline Voice Clone បានជោគជ័យ។")
                            else:
                                st.error("VoxCPM2 មិនអាចបង្កើតសំឡេងបាន។")
                            _release_offline_voxcpm_model()
                        else:
                            _base = os.path.join(_td, "base.mp3")
                            asyncio.run(edge_tts.Communicate(tts_clean(_t_text), TTS_VOICES[_t_voice], rate="+0%").save(_base))
                            _wav = os.path.join(_td, "base.wav")
                            run_ffmpeg(["-i", _base, "-ar", "22050", "-ac", "1", _wav])
                            if _vc.clone_to(_wav, _ref, _res):
                                with open(_res, "rb") as _fh:
                                    st.audio(_fh.read(), format="audio/wav")
                                st.success("សាកល្បង Voice Clone បានជោគជ័យ។")
                            else:
                                st.error("OpenVoice មិនអាចក្លូនសំឡេងនេះបានទេ។ សូមសាក sample ផ្សេងដែលច្បាស់ និងវែងជាងនេះ។")
                    except Exception as _e:
                        if offline_on:
                            _release_offline_voxcpm_model()
                        st.error(f"សាកល្បងមិនបាន៖ {_e}")
                    finally:
                        shutil.rmtree(_td, ignore_errors=True)
        else:
            clone_files = []
            clone_names = []


# ============================ ផ្ទាំង ៤: អក្សរ ============================
with tab_text:
    st.markdown("### 🔤 ការកំណត់ Subtitle")
    st.caption("ការកំណត់ Font, ពណ៌, ទំហំ, គែមអក្សរ និងទីតាំង ត្រូវបានដាក់នៅជួរទី ៣ លើ Dashboard ដើម្បីមើលឃើញភ្លាមៗពេលបើកកម្មវិធី។")
    bold_, italic_ = STYLE_OPTIONS[style_pick]
    render_preview(font_size, COLOR_OPTIONS[color_pick][1], POS_MAP[pos_pick],
                   bold_, italic_, BOX_OPTIONS[box_pick])


# ============================ ផ្ទាំង Logo + Blur ============================
BLUR_COLORS = ["#FF2D2D", "#FFE600", "#00E640", "#2F6BFF"]


def logo_preview_data(raw):
    """រូបតូចសម្រាប់ preview (មិនប៉ះឯកសារដើម)។"""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(raw)).convert("RGBA")
        iw, ih = im.size
        im.thumbnail((300, 300))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii"), iw, ih
    except Exception:
        return None, 1, 1


def render_fx_preview(aspect, logo, lx, ly, lsize, lop, tint, blurs, frame=None):
    """frame = (data_uri, ទទឹង, កម្ពស់) ស៊ុមពិតពីវីដេអូ។ បើមាន ប្រើទំហំពិតរបស់វីដេអូ (អូតូ)។"""
    bg = "linear-gradient(160deg,#3A2C6E 0%,#1B2A5E 60%,#0E1636 100%)"
    if frame and frame[0]:
        fw, fh = max(1, frame[1]), max(1, frame[2])
        ratio = fw / float(fh)
        bg = f"#000 url({frame[0]}) center/cover no-repeat"
        if aspect == "auto":
            if ratio >= 1.0:
                box = f"width:100%;aspect-ratio:{fw}/{fh};margin:6px 0;"
            else:
                box = f"height:460px;max-width:100%;aspect-ratio:{fw}/{fh};margin:6px auto;"
    if not (frame and frame[0] and aspect == "auto"):
        if aspect == "9:16":
            box = "height:260px;aspect-ratio:9/16;margin:6px auto;"
        elif aspect == "1:1":
            box = "height:240px;aspect-ratio:1/1;margin:6px auto;"
        else:
            box = "width:100%;aspect-ratio:16/9;margin:6px 0;"
    html = [f'<div style="position:relative;overflow:hidden;border-radius:14px;border:1px solid rgba(125,145,255,.22);'
            f'background:{bg};{box}">']
    for i, b in enumerate(blurs, start=1):
        c = BLUR_COLORS[(i - 1) % len(BLUR_COLORS)]
        html.append(
            f'<div style="position:absolute;left:{b["x"] * 100:.1f}%;top:{b["y"] * 100:.1f}%;width:{b["w"] * 100:.1f}%;height:{b["h"] * 100:.1f}%;'
            f'border:2px dashed {c};background:rgba(255,255,255,.14);backdrop-filter:blur(4px);display:flex;'
            f'align-items:center;justify-content:center;color:{c};font-weight:800;">{i}</div>')
    if logo and logo[0]:
        uri, iw, ih = logo
        pos = f"position:absolute;left:{lx}%;top:{ly}%;transform:translate(-50%,-50%);width:{lsize}%;opacity:{lop};"
        if tint:
            html.append(f'<div style="{pos}aspect-ratio:{iw}/{ih};background:{tint};'
                        f'-webkit-mask:url({uri}) center/contain no-repeat;mask:url({uri}) center/contain no-repeat;"></div>')
        else:
            html.append(f'<img src="{uri}" style="{pos}height:auto;">')
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def fx_frame_for(path, key):
    """ដកស៊ុមមួយពីវីដេអូ (cache តាម key) → (data_uri, w, h) ឬ None។"""
    c = st.session_state.get("_fx_frame")
    if c and c.get("key") == key:
        return c.get("val")
    val = None
    tmp = tempfile.mkdtemp(prefix="kfx_")
    try:
        out = os.path.join(tmp, "f.jpg")
        for ss in ("1", "0"):
            try:
                run_ffmpeg(["-ss", ss, "-i", path, "-frames:v", "1", "-vf", "scale='min(640,iw)':-2", "-q:v", "4", out])
                if os.path.isfile(out) and os.path.getsize(out) > 0:
                    break
            except Exception:
                continue
        if os.path.isfile(out):
            from PIL import Image
            with open(out, "rb") as fh:
                raw = fh.read()
            w_, h_ = Image.open(io.BytesIO(raw)).size
            val = ("data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii"), w_, h_)
    except Exception:
        val = None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    st.session_state["_fx_frame"] = {"key": key, "val": val}
    return val


def fx_current_frame():
    """រកវីដេអូដំបូងដែលបានជ្រើស/រកឃើញ (Upload, Link, ឬផ្នែកដែលកាត់) ហើយត្រឡប់ស៊ុមរបស់វា។"""
    try:
        if uploaded_files:
            f0 = uploaded_files[0]
            key = f"up:{f0.name}:{f0.size}"
            c = st.session_state.get("_fx_frame")
            if c and c.get("key") == key:
                return c.get("val")
            tmpd = tempfile.mkdtemp(prefix="kfxu_")
            try:
                pth = os.path.join(tmpd, "v.bin")
                with open(pth, "wb") as fh:
                    fh.write(f0.getbuffer())
                return fx_frame_for(pth, key)
            finally:
                shutil.rmtree(tmpd, ignore_errors=True)
        _cache = st.session_state.get("link_cache", {})
        for u in extract_links(link_text):
            ent = _cache.get(u, {})
            if ent.get("ok") and ent.get("path") and os.path.isfile(ent["path"]):
                return fx_frame_for(ent["path"], f"ln:{ent['path']}")
        _sq0 = st.session_state.get("_split_queue") or []
        for q in _sq0:
            if os.path.isfile(q["path"]):
                return fx_frame_for(q["path"], f"sq:{q['path']}")
    except Exception:
        return None
    return None


fx_settings = None
with tab_fx:
    prev_fx = st.container()
    with st.container(border=True):
        st.markdown("**🖼 Logo**")
        logo_file = st.file_uploader("Upload logo (PNG ផ្ទៃថ្លាល្អបំផុត)", type=["png", "jpg", "jpeg", "webp"], key="logo_up")
        logo_x, logo_y, logo_size, logo_op, logo_tint = 90, 10, 15, 100, None
        if logo_file is not None:
            g1, g2 = st.columns(2)
            with g1:
                logo_x = st.slider("ទីតាំងឆ្វេង↔ស្តាំ (%)", 0, 100, 90, key="logo_x")
            with g2:
                logo_y = st.slider("ទីតាំងលើ↕ក្រោម (%)", 0, 100, 10, key="logo_y")
            g3, g4 = st.columns(2)
            with g3:
                logo_size = st.slider("ទំហំ (% នៃទទឹងវីដេអូ)", 3, 80, 15, key="logo_size")
            with g4:
                logo_op = st.slider("ភាពច្បាស់ (%)", 10, 100, 100, key="logo_op")
            if st.checkbox("🎨 ប្តូរពណ៌ Logo (ល្អសម្រាប់ logo ពណ៌តែមួយ)", key="logo_tint_on"):
                logo_tint = st.color_picker("ពណ៌ Logo", "#FFFFFF", key="logo_tint_col")
    with st.container(border=True):
        st.markdown("**🌫 Blur បិទបាំង**")
        n_blur = st.slider("ចំនួនកន្លែងត្រូវ Blur", 0, 4, 0, key="n_blur")
        blur_list = []
        for i in range(n_blur):
            c = BLUR_COLORS[i % len(BLUR_COLORS)]
            with st.expander(f"កន្លែងទី {i + 1}", expanded=(n_blur <= 2)):
                d = [(35, 80, 30, 12), (5, 5, 25, 12), (65, 5, 30, 12), (35, 40, 30, 20)][i]
                b1, b2 = st.columns(2)
                with b1:
                    bx = st.slider("ឆ្វេង (%)", 0, 95, d[0], key=f"bx{i}")
                with b2:
                    by = st.slider("ពីលើ (%)", 0, 95, d[1], key=f"by{i}")
                b3, b4 = st.columns(2)
                with b3:
                    bw = st.slider("ទទឹង (%)", 3, 100, d[2], key=f"bw{i}")
                with b4:
                    bh = st.slider("កម្ពស់ (%)", 3, 100, d[3], key=f"bh{i}")
                bs = st.slider("កម្លាំង Blur", 5, 60, 25, key=f"bs{i}")
                t0 = t1 = None
                if not st.checkbox("Blur ពេញមួយវីដេអូ", value=True, key=f"ball{i}"):
                    t1c, t2c = st.columns(2)
                    with t1c:
                        t0 = st.number_input("ចាប់ពី (វិនាទី)", min_value=0.0, value=0.0, step=0.5, key=f"bt0{i}")
                    with t2c:
                        t1 = st.number_input("ដល់ (វិនាទី)", min_value=0.5, value=5.0, step=0.5, key=f"bt1{i}")
                bw = min(bw, 100 - bx)
                bh = min(bh, 100 - by)
                blur_list.append({"x": bx / 100.0, "y": by / 100.0, "w": bw / 100.0, "h": bh / 100.0,
                                  "sigma": bs, "t0": t0, "t1": t1})
    if logo_file is not None or blur_list:
        fx_settings = {
            "blurs": blur_list,
            "logo_bytes": logo_file.getvalue() if logo_file is not None else None,
            "logo_x": logo_x / 100.0, "logo_y": logo_y / 100.0,
            "logo_size": logo_size, "logo_opacity": logo_op / 100.0,
            "logo_color": logo_tint,
        }
    with prev_fx:
        _frame = fx_current_frame()
        _asp_opts = ["🔄 អូតូ (តាមវីដេអូ)", "16:9", "9:16", "1:1"]
        _asp = st.radio("ទម្រង់មើលជាមុន", _asp_opts, horizontal=True, key="fx_aspect_v2")
        aspect = "auto" if _asp.startswith("🔄") else _asp
        render_fx_preview(aspect, logo_preview_data(logo_file.getvalue()) if logo_file is not None else None,
                          logo_x, logo_y, logo_size, logo_op / 100.0, logo_tint, blur_list, frame=_frame)
        if _frame is None:
            st.caption("🎞 ជ្រើសវីដេអូ ឬរកតំណឃើញជាមុន នោះនឹងបង្ហាញរូបពិតពីវីដេអូនៅទីនេះ ដើម្បីដាក់ Logo/Blur ឱ្យចំកន្លែង។")
        if logo_file is None and not blur_list:
            st.caption("Upload logo ឬបន្ថែមកន្លែង Blur ដើម្បីមើលជាមុន។ បើមិនប្រើ វីដេអូមិនមានការផ្លាស់ប្តូរទេ។")

# ============================ បញ្ជីវីដេអូ ============================
items = []
if uploaded_files:
    # App-level count/size filtering is disabled: keep every selected video.
    # The browser/hosting platform may still enforce its own upload limits.
    for f in uploaded_files:
        items.append({"name": f.name, "file": f, "url": None})
elif local_files:
    for _lp in local_files:
        items.append({"name": os.path.basename(_lp), "file": None, "url": None, "cached": _lp})
else:
    lines = extract_links(link_text)
    _cache = st.session_state.get("link_cache", {})
    lines = [u for u in lines if _cache.get(u, {}).get("ok")]
    for i, url in enumerate(lines, start=1):
        items.append({"name": f"វីដេអូទី {i}", "file": None, "url": url, "cached": _cache[url]["path"]})

# ផ្នែកដែលបានកាត់ពីផ្ទាំង «✂️ កាត់» ហើយបានចុច «បកប្រែ» → ជំនួសបញ្ជីវីដេអូ
_sq = st.session_state.get("_split_queue")
if _sq and st.session_state.get("_run_split"):
    _sq = [q for q in _sq if os.path.isfile(q["path"])]
    items = [{"name": q["name"], "file": None, "url": None, "cached": q["path"], "presplit": True}
             for q in _sq]

# ============================ ប៊ូតុងចាប់ផ្តើម (ជាប់ខាងក្រោម) ============================
# Place the action slot AFTER all tabs so Streamlit does not reserve a tall empty block above the dashboard.
start_slot = st.container(key="startbar")
run = False
with start_slot:
    if busy:
        st.button("⏳ កំពុងធ្វើការ... មើលនៅផ្ទាំង ⬇️", disabled=True, use_container_width=True)
    elif not items:
        st.button("▶ ចាប់ផ្តើមបកប្រែរឿង (សូមជ្រើសវីដេអូជាមុនសិន)", disabled=True, use_container_width=True)
    else:
        label = "▶ ចាប់ផ្តើមបកប្រែរឿង"
        if len(items) > 1:
            label += f" ({len(items)})"
        run = st.button(label, type="primary", use_container_width=True)

if link_translate and items and not busy:
    run = True
if st.session_state.get("_run_split") and not busy:
    if items:
        run = True
    else:
        st.session_state["_run_split"] = False

if run:
    try:
        with st.spinner("កំពុងពិនិត្យ Font ខ្មែរ និងរៀបចំ Font ដែលអាចប្រើបាន..."):
            fonts_data = load_font_bytes()
    except Exception as font_error:
        st.error("ទាញយក ឬរក Font ខ្មែរមិនបាន។")
        st.caption(str(font_error)[:700])
        st.info("កម្មវិធីសាកប្រើ Font ដែលមានក្នុង Windows ជាមុន រួចទើបសាកទាញយកពី Google Fonts។ សូមដំឡើង Khmer OS / Noto Sans Khmer ឬពិនិត្យ Internet។")
        st.stop()
    prepare_home_font(fonts_data)
    fonts_data = sorted(fonts_data, key=lambda f: 0 if f[2] == font_name else 1)
    clone_samples = []
    clone_names_ready = []
    if clone_on:
        for _sample_file, _sample_name in zip(clone_files, clone_names):
            _sample_bytes = clone_sample_bytes(_sample_file)
            if _sample_bytes:
                clone_samples.append(_sample_bytes)
                clone_names_ready.append(_sample_name)
    settings = {
        "engine": "offline" if offline_on else "free",
        "offline_on": bool(offline_on),
        "offline_whisper": offline_whisper_choice,
        "gemini_key": "", "groq_key": ("" if offline_on else effective_groq_key()), "fx": fx_settings,
        "user_xk_cfg": xk_cfg_for_session(),
        "language": LANGUAGES[language_label], "quality": QUALITY[quality_label],
        "dub_on": dub_on, "voice": TTS_VOICES[voice_label],
        # Fixed internal defaults; no extra voice-tuning controls in the UI.
        "keep_bg": keep_bg, "bg_vol": (bg_level / 100.0 if keep_bg else 0.0), "dub_offset": float(dub_offset), "tight_sync": bool(tight_sync), "auto_gender": auto_gender,
        "voice_match": False, "emotion": bool(emotion_on),
        "timbre": bool(clone_samples), "timbre_samples": clone_samples,
        "timbre_names": (clone_names_ready if clone_on else []),
        "timbre_clone_enabled": bool(clone_on and clone_samples and (offline_on or _mode == "real")),
        "font_size": font_size, "outline_size": outline_size,
        "color": COLOR_OPTIONS[color_pick][0],
        "sub_on": sub_on, "srt_on": srt_on,
        "narrate_on": False, "review_on": review_on,
        "style": {"align": POS_MAP[pos_pick], "bold": bold_, "italic": italic_, "box": BOX_OPTIONS[box_pick]},
    }
    st.session_state["_run_split"] = False
    old = st.session_state.get("job")
    if old:
        shutil.rmtree(old.folder, ignore_errors=True)
        st.session_state.pop("job", None)
        old = None
        gc.collect()
    _CLAUDE_PROVIDERS[:] = []
    for _i, _k in enumerate(st.session_state.get("user_claude_keys", []), start=1):
        _CLAUDE_PROVIDERS.append((f"Claude ផ្ទាល់ខ្លួន #{_i}", (
            _k, st.session_state.get("user_claude_base", "https://api.laalaa.me"),
            st.session_state.get("user_claude_model", "claude-sonnet-5-5"))))
    _CLAUDE_PROVIDERS.extend(_CLAUDE_SECRET_PROVIDERS)
    _CLAUDE_COOL.clear()
    job_folder = tempfile.mkdtemp(prefix="kac_")
    job_items = []
    for idx, it in enumerate(items, start=1):
        if it["file"] is not None:
            p = os.path.join(job_folder, f"upload_{idx}.bin")
            with open(p, "wb") as f:
                f.write(it["file"].getbuffer())
            parts = None
            if split_sec:
                with st.spinner(f"កំពុងកាត់វីដេអូទី {idx} ជាផ្នែកខ្លីៗ..."):
                    parts = split_video_parts(p, job_folder, idx, split_sec, split_exact)
            if parts:
                try:
                    os.remove(p)
                except OSError:
                    pass
                for k, pp in enumerate(parts, start=1):
                    item = new_item(f"{it['name']} · ផ្នែក {k}/{len(parts)}")
                    item["path"] = pp
                    job_items.append(item)
            else:
                item = new_item(it["name"], url=it["url"])
                item["path"] = p
                job_items.append(item)
        elif it.get("presplit"):
            item = new_item(it["name"])
            p = os.path.join(job_folder, f"upload_{idx}.bin")
            link_or_copy(it["cached"], p)
            item["path"] = p
            job_items.append(item)
        elif it.get("cached") and os.path.isfile(it["cached"]):
            parts = None
            if split_sec:
                with st.spinner(f"កំពុងរៀបចំវីដេអូទី {idx}..."):
                    parts = split_video_parts(it["cached"], job_folder, idx, split_sec, split_exact)
            if parts:
                for k, pp in enumerate(parts, start=1):
                    item = new_item(f"{it['name']} · ផ្នែក {k}/{len(parts)}")
                    item["path"] = pp
                    job_items.append(item)
            else:
                item = new_item(it["name"], url=it["url"])
                p = os.path.join(job_folder, f"upload_{idx}.bin")
                link_or_copy(it["cached"], p)
                item["path"] = p
                job_items.append(item)
        else:
            job_items.append(new_item(it["name"], url=it["url"]))
    for _k, _it in enumerate(job_items):
        _it["seq"] = _k
    job = Job(job_items, job_folder)
    st.session_state["job"] = job
    for item in job.items:
        threading.Thread(target=run_worker, args=(job, item, settings, fonts_data), daemon=True).start()
    st.rerun()

# ============================ ផ្ទាំង ៥: ធ្វើការ + ទាញយក ============================
job = st.session_state.get("job")
with tab_out:
    if not job:
        st.info("មិនទាន់មានលទ្ធផលទេ។ ជ្រើសវីដេអូ រួចចុច «ចាប់ផ្តើម» ខាងក្រោម។")
    else:
        running = job.running()
        if not running and not job.zip_done:
            job.zip = build_zip(job.items, job.folder)
            job.zip_done = True
        reviewing = job.reviewing()
        refresh = REFRESH_SECONDS if (running and not reviewing) else None
        st.fragment(run_every=refresh)(work_area)(job, running, reviewing)
        st.markdown('<div id="download-area"></div>', unsafe_allow_html=True)
        st.fragment(run_every=(6 if refresh else None))(download_area)(job)
        if not running:
            if st.button("🗑 លុបលទ្ធផលទាំងអស់"):
                shutil.rmtree(job.folder, ignore_errors=True)
                st.session_state.pop("job", None)
                gc.collect()
                st.rerun()


# ---------- Screenshot-specific correction: remove clipping and footer overlay ----------
# The previous final CSS accidentally re-enabled overflow:hidden and a fixed footer.
# Keep every Streamlit widget reachable; the action button is placed in normal flow.
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

# ── មិនឱ្យ keyboard លោតចេញពេលចុច selectbox (ធ្វើឱ្យ input ក្នុង selectbox ជា readonly) ──
components.html(
    """
<script>
(function(){
  try {
    const doc = window.parent.document;
    if (doc.__kvaiNoKb) return;
    doc.__kvaiNoKb = true;
    const fix = () => {
      doc.querySelectorAll('[data-testid="stSelectbox"] input').forEach(i => {
        if (i.dataset.nokb) return;
        i.dataset.nokb = "1";
        i.setAttribute('inputmode', 'none');
        i.setAttribute('readonly', 'readonly');
        i.style.caretColor = 'transparent';
      });
    };
    fix();
    new MutationObserver(fix).observe(doc.body, {childList: true, subtree: true});
  } catch (e) {}
})();
</script>
""",
    height=0,
)


# =====================================================================
# MODERN UI REFRESH — clean glass panels, softer gradients, clearer controls
# UI-only override; preserves app logic and existing features.
# =====================================================================
MODERN_UI_REFRESH_CSS = r"""
<style>
:root {
  --kvai-ui-bg: #080d20;
  --kvai-ui-panel: rgba(15, 24, 48, .88);
  --kvai-ui-line: rgba(130, 165, 255, .19);
  --kvai-ui-text: #edf3ff;
  --kvai-ui-muted: #a8b5d3;
  --kvai-ui-pink: #f044b5;
  --kvai-ui-cyan: #54d8f2;
}
.stApp {
  background:
    radial-gradient(ellipse at 8% 0%, rgba(90, 65, 180, .20), transparent 34%),
    radial-gradient(ellipse at 95% 12%, rgba(0, 185, 220, .12), transparent 28%),
    linear-gradient(145deg, #070b1b 0%, #0b1228 52%, #080d20 100%) !important;
  color: var(--kvai-ui-text) !important;
}
[data-testid="stMainBlockContainer"] {
  max-width: 1500px !important;
  padding-top: 1.15rem !important;
  padding-bottom: 2.3rem !important;
}
[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--kvai-ui-line) !important;
  border-radius: 18px !important;
}
[data-testid="stExpander"] {
  border: 1px solid var(--kvai-ui-line) !important;
  border-radius: 15px !important;
  background: rgba(12, 20, 42, .66) !important;
  overflow: hidden !important;
}
[data-testid="stExpander"] summary {
  font-weight: 650 !important;
  letter-spacing: .01em !important;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: 7px !important;
  padding: 6px !important;
  border: 1px solid rgba(115, 155, 240, .17) !important;
  border-radius: 15px !important;
  background: rgba(8, 14, 32, .82) !important;
}
[data-testid="stTabs"] button[data-baseweb="tab"] {
  border-radius: 11px !important;
  min-height: 40px !important;
  padding: 7px 14px !important;
  color: #b9c6e4 !important;
  transition: background .18s ease, color .18s ease, transform .18s ease !important;
}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
  color: #fff !important;
  background: linear-gradient(115deg, rgba(240, 68, 181, .25), rgba(84, 216, 242, .18)) !important;
  border: 1px solid rgba(84, 216, 242, .32) !important;
  box-shadow: 0 4px 18px rgba(20, 170, 220, .10) !important;
}
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
  min-height: 42px !important;
  border-radius: 12px !important;
  border: 1px solid rgba(105, 210, 245, .28) !important;
  background: linear-gradient(120deg, #b52c91 0%, #713fcb 48%, #187eae 100%) !important;
  color: #fff !important;
  font-weight: 700 !important;
  letter-spacing: .01em !important;
  box-shadow: 0 5px 18px rgba(75, 65, 180, .16) !important;
  transition: transform .16s ease, filter .16s ease, box-shadow .16s ease !important;
}
.stButton > button:hover, .stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
  transform: translateY(-1px) !important;
  filter: brightness(1.09) !important;
  box-shadow: 0 8px 24px rgba(45, 160, 220, .22) !important;
}
.stButton > button:focus, .stDownloadButton > button:focus {
  outline: 2px solid rgba(84, 216, 242, .5) !important;
  outline-offset: 2px !important;
}
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input, [data-testid="stDateInput"] input {
  border-radius: 11px !important;
  border: 1px solid rgba(130, 165, 255, .23) !important;
  background: rgba(7, 13, 30, .78) !important;
  color: #f3f6ff !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  border-radius: 11px !important;
  border-color: rgba(130, 165, 255, .23) !important;
  background: rgba(7, 13, 30, .78) !important;
}
[data-testid="stFileUploader"] section {
  border: 1.5px dashed rgba(84, 216, 242, .36) !important;
  border-radius: 16px !important;
  background: linear-gradient(135deg, rgba(20, 35, 67, .62), rgba(12, 20, 42, .62)) !important;
  padding: 14px !important;
}
[data-testid="stFileUploader"] section:hover {
  border-color: rgba(240, 68, 181, .55) !important;
  background: rgba(25, 35, 70, .78) !important;
}
[data-testid="stAlert"] {
  border-radius: 13px !important;
  border: 1px solid rgba(130, 165, 255, .20) !important;
}
[data-testid="stProgress"] > div > div {
  border-radius: 999px !important;
}
[data-testid="stMetric"] {
  padding: 13px 15px !important;
  border-radius: 14px !important;
  border: 1px solid rgba(130, 165, 255, .18) !important;
  background: rgba(15, 24, 48, .68) !important;
}
hr {
  border-color: rgba(130, 165, 255, .16) !important;
}
.stCaption, [data-testid="stCaptionContainer"] {
  color: var(--kvai-ui-muted) !important;
}
@media (max-width: 759px) {
  [data-testid="stMainBlockContainer"] {
    padding: .65rem .65rem 1.5rem !important;
  }
  [data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 4px !important;
    padding: 4px !important;
    overflow-x: auto !important;
  }
  [data-testid="stTabs"] button[data-baseweb="tab"] {
    min-height: 36px !important;
    padding: 6px 9px !important;
    font-size: .82rem !important;
    white-space: nowrap !important;
  }
  .stButton > button, .stDownloadButton > button {
    min-height: 40px !important;
  }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
  }
}
</style>
"""
st.markdown(MODERN_UI_REFRESH_CSS, unsafe_allow_html=True)


# ---- Vibrant neon cinematic UI polish (visual-only; preserve app logic) ----
VIBRANT_DRAMA_UI_CSS = r"""
<style>
:root { --drama-cyan:#00eaff; --drama-blue:#267bff; --drama-violet:#7b2cff; --drama-pink:#ff19d5; --drama-gold:#ffcf38; --drama-green:#00f5a0; }
html, body, [data-testid="stAppViewContainer"] { background: radial-gradient(ellipse at 8% 8%,rgba(0,234,255,.18),transparent 32%),radial-gradient(ellipse at 92% 15%,rgba(255,25,213,.20),transparent 34%),radial-gradient(ellipse at 52% 100%,rgba(123,44,255,.20),transparent 42%),linear-gradient(135deg,#03091f 0%,#07164b 48%,#13052e 100%) !important; color:#f7f9ff !important; }
[data-testid="stHeader"] { background:linear-gradient(90deg,rgba(0,234,255,.10),rgba(123,44,255,.12),rgba(255,25,213,.10)) !important; border-bottom:1px solid rgba(0,234,255,.22) !important; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,rgba(5,12,43,.98),rgba(20,7,62,.98) 58%,rgba(4,26,73,.98)) !important; border-right:1px solid rgba(0,234,255,.40) !important; box-shadow:5px 0 28px rgba(123,44,255,.16) !important; }
[data-testid="stSidebar"] * { color:#f6f7ff; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-color:rgba(105,150,255,.35) !important; background:linear-gradient(145deg,rgba(19,39,100,.72),rgba(23,10,68,.72)) !important; box-shadow:inset 0 1px 0 rgba(255,255,255,.06),0 8px 26px rgba(0,0,0,.14) !important; border-radius:18px !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { background:rgba(5,13,45,.66) !important; border:1px solid rgba(0,234,255,.22) !important; border-radius:16px !important; padding:5px !important; gap:7px !important; }
[data-testid="stTabs"] button[data-baseweb="tab"] { color:#e8edff !important; border-radius:12px !important; transition:transform .18s ease,filter .18s ease,box-shadow .18s ease !important; }
[data-testid="stTabs"] button[data-baseweb="tab"]:hover { transform:translateY(-2px) !important; box-shadow:0 0 16px rgba(0,234,255,.25) !important; }
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] { background:linear-gradient(110deg,#ff18cf 0%,#782cff 52%,#00cfff 100%) !important; color:white !important; box-shadow:0 0 20px rgba(255,25,213,.30),0 0 28px rgba(0,234,255,.18) !important; border:1px solid rgba(255,255,255,.34) !important; }
.stButton > button,.stDownloadButton > button,[data-testid="stFormSubmitButton"] button { border:1px solid rgba(255,255,255,.35) !important; background:linear-gradient(105deg,#ffbd27 0%,#ff19d5 36%,#762bff 68%,#00dfff 100%) !important; color:#fff !important; border-radius:14px !important; font-weight:750 !important; text-shadow:0 1px 4px rgba(0,0,0,.28) !important; box-shadow:0 0 12px rgba(255,25,213,.30),0 0 24px rgba(0,234,255,.16) !important; transition:transform .18s ease,filter .18s ease,box-shadow .18s ease !important; }
.stButton > button:hover,.stDownloadButton > button:hover,[data-testid="stFormSubmitButton"] button:hover { transform:translateY(-2px) scale(1.01) !important; filter:brightness(1.13) saturate(1.15) !important; box-shadow:0 0 18px rgba(255,25,213,.48),0 0 32px rgba(0,234,255,.30) !important; }
.stDownloadButton > button { background:linear-gradient(110deg,#00e88f,#00bdff) !important; box-shadow:0 0 16px rgba(0,245,160,.25) !important; }
[data-testid="stFileUploader"] section { border:2px dashed rgba(0,234,255,.76) !important; border-radius:20px !important; background:linear-gradient(130deg,rgba(0,90,255,.20),rgba(123,44,255,.24),rgba(255,25,213,.14)) !important; box-shadow:inset 0 0 22px rgba(0,234,255,.07),0 0 20px rgba(123,44,255,.15) !important; transition:border-color .2s ease,box-shadow .2s ease !important; }
[data-testid="stFileUploader"] section:hover { border-color:#ff19d5 !important; box-shadow:inset 0 0 25px rgba(255,25,213,.10),0 0 24px rgba(0,234,255,.22) !important; }
[data-testid="stSelectbox"] [data-baseweb="select"] > div,[data-testid="stMultiSelect"] [data-baseweb="select"] > div { border-color:rgba(0,234,255,.34) !important; background:rgba(4,14,48,.84) !important; border-radius:12px !important; }
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stNumberInput"] input { border-color:rgba(0,234,255,.30) !important; background:rgba(4,14,48,.84) !important; color:#fff !important; border-radius:12px !important; }
[data-testid="stProgress"] > div > div { background:linear-gradient(90deg,#ff19d5,#762bff,#00eaff) !important; box-shadow:0 0 12px rgba(0,234,255,.30) !important; }
[data-testid="stMetric"] { background:linear-gradient(135deg,rgba(0,87,255,.18),rgba(255,25,213,.14)) !important; border:1px solid rgba(0,234,255,.30) !important; border-radius:16px !important; box-shadow:0 0 16px rgba(123,44,255,.12) !important; }
hr { border-color:rgba(0,234,255,.24) !important; }
@keyframes drama-neon-breathe { 0%,100%{box-shadow:0 0 10px rgba(0,234,255,.16)} 50%{box-shadow:0 0 18px rgba(255,25,213,.23)} }
[data-testid="stVerticalBlockBorderWrapper"] > div { animation:drama-neon-breathe 5.5s ease-in-out infinite; }
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none !important;transition:none !important}}
@media(max-width:759px){[data-testid="stMainBlockContainer"]{padding:.65rem .65rem 1.3rem !important}[data-testid="stTabs"] [data-baseweb="tab-list"]{overflow-x:auto !important}}
</style>
"""
st.markdown(VIBRANT_DRAMA_UI_CSS, unsafe_allow_html=True)



# =====================================================================
# 🌟 MASTER UI: បកប្រែរឿង — NEON CINEMATIC GRADIENT & GLOW THEME
# ផ្ទៃខាងក្រោយ Gradient ពណ៌ខៀវ ស្វាយ និងផ្កាឈូក | Neon Glow | ពន្លឺរត់ | Cinematic Header & Upload
# =====================================================================
BAK_TRAE_RUEANG_NEON_UI_CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Kantumruy+Pro:wght@400;600;700;800&family=Moul&family=Battambang:wght@400;700&display=swap');

:root {
  --btr-blue: #00e5ff;
  --btr-deep-blue: #09133a;
  --btr-purple: #8a2be2;
  --btr-pink: #ff1493;
  --btr-gold: #ffd700;
  --btr-green: #00f59b;
}

/* 1. ផ្ទៃខាងក្រោយ Gradient ពណ៌ខៀវ ស្វាយ និងផ្កាឈូក */
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"] {
  background:
    radial-gradient(circle at 12% 14%, rgba(255, 20, 147, 0.30) 0%, transparent 38%),
    radial-gradient(circle at 88% 16%, rgba(0, 229, 255, 0.28) 0%, transparent 40%),
    radial-gradient(circle at 50% 88%, rgba(138, 43, 226, 0.35) 0%, transparent 48%),
    linear-gradient(135deg, #040924 0%, #0d1648 32%, #200b4b 68%, #35083d 100%) !important;
  background-attachment: fixed !important;
  color: #f8faff !important;
}

/* ពន្លឺរត់កាត់ផ្ទៃខាងក្រោយស្រទន់ */
.stApp::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background:
    linear-gradient(115deg, transparent 30%, rgba(0, 229, 255, 0.08) 45%, rgba(255, 20, 147, 0.09) 55%, transparent 70%);
  background-size: 250% 100%;
  animation: btr-bg-shimmer 9s linear infinite !important;
}

@keyframes btr-bg-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -100% 0; }
}

@keyframes btr-btn-shimmer {
  0% { left: -120%; }
  100% { left: 160%; }
}

@keyframes btr-neon-pulse {
  0%, 100% {
    box-shadow: 0 0 14px rgba(0, 229, 255, 0.35), 0 0 28px rgba(138, 43, 226, 0.25), inset 0 0 14px rgba(255, 20, 147, 0.14);
  }
  50% {
    box-shadow: 0 0 22px rgba(255, 20, 147, 0.45), 0 0 38px rgba(0, 229, 255, 0.35), inset 0 0 20px rgba(0, 229, 255, 0.20);
  }
}

/* 2. 🎬 កែ Header ឱ្យមានស្ទីល Cinematic និងឈ្មោះ «បកប្រែរឿង» */
.kvai-head.btr-cinematic-header {
  position: relative !important;
  overflow: hidden !important;
  height: auto !important;
  min-height: 92px !important;
  max-height: none !important;
  padding: 14px 22px !important;
  margin: 4px 0 14px !important;
  border-radius: 22px !important;
  border: 2px solid rgba(0, 229, 255, 0.78) !important;
  background:
    radial-gradient(circle at 50% 0%, rgba(255, 20, 147, 0.32), transparent 65%),
    linear-gradient(95deg, rgba(8, 17, 58, 0.95) 0%, rgba(42, 11, 84, 0.92) 50%, rgba(9, 24, 72, 0.95) 100%) !important;
  box-shadow:
    0 0 25px rgba(0, 229, 255, 0.42),
    0 0 45px rgba(255, 20, 147, 0.28),
    inset 0 0 28px rgba(138, 43, 226, 0.35) !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 14px !important;
}

.kvai-head.btr-cinematic-header::after {
  content: "";
  position: absolute;
  top: 0;
  left: -120%;
  width: 75%;
  height: 100%;
  background: linear-gradient(100deg, transparent, rgba(255, 255, 255, 0.22), rgba(0, 229, 255, 0.25), transparent);
  transform: skewX(-22deg);
  animation: btr-btn-shimmer 4.8s ease-in-out infinite !important;
  pointer-events: none;
}

.kvai-logo.btr-clapper-logo {
  width: 60px !important;
  height: 60px !important;
  flex: 0 0 60px !important;
  font-size: 32px !important;
  border-radius: 18px !important;
  border: 2px solid rgba(255, 255, 255, 0.65) !important;
  background: linear-gradient(135deg, #ff1493 0%, #8a2be2 50%, #00e5ff 100%) !important;
  box-shadow: 0 0 22px rgba(255, 20, 147, 0.8), 0 0 32px rgba(0, 229, 255, 0.55) !important;
}

.kvai-title.btr-header-center {
  text-align: center !important;
  flex: 1 1 auto !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
}

.kvai-title .kvai-h1.btr-main-title {
  font-family: 'Moul', 'Kantumruy Pro', sans-serif !important;
  font-size: clamp(1.5rem, 3.6vw, 2.35rem) !important;
  font-weight: 800 !important;
  letter-spacing: 1px !important;
  margin: 0 !important;
  line-height: 1.3 !important;
  filter: drop-shadow(0 0 12px rgba(255, 20, 147, 0.85)) drop-shadow(0 0 24px rgba(0, 229, 255, 0.6));
}

.kvai-title .kvai-h1.btr-main-title span {
  background: linear-gradient(180deg, #fff6b7 0%, #ffd700 45%, #ff8c00 85%, #ff1493 100%) !important;
  -webkit-background-clip: text !important;
  background-clip: text !important;
  color: transparent !important;
  -webkit-text-fill-color: transparent !important;
}

.kvai-title p.btr-sub-pill {
  display: inline-block !important;
  margin-top: 6px !important;
  padding: 4px 18px !important;
  border-radius: 999px !important;
  border: 1.5px solid rgba(0, 229, 255, 0.7) !important;
  background: linear-gradient(90deg, rgba(13, 27, 82, 0.9), rgba(74, 18, 120, 0.88), rgba(13, 27, 82, 0.9)) !important;
  color: #eaf8ff !important;
  font-size: clamp(0.68rem, 1.5vw, 0.88rem) !important;
  font-weight: 600 !important;
  box-shadow: 0 0 14px rgba(0, 229, 255, 0.35) !important;
}

.kvai-badge.btr-vip-badge {
  border: 2px solid #ffd700 !important;
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.28), rgba(255, 20, 147, 0.35)) !important;
  color: #fff3a1 !important;
  font-weight: 800 !important;
  padding: 7px 15px !important;
  border-radius: 999px !important;
  box-shadow: 0 0 18px rgba(255, 215, 0, 0.55) !important;
}

/* 3. 💡 បន្ថែម Neon Glow លើផ្ទាំង (Panels / Cards / Expanders / Tabs) */
div[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stExpander"] {
  border: 1.8px solid rgba(0, 229, 255, 0.62) !important;
  border-radius: 18px !important;
  background: linear-gradient(145deg, rgba(11, 22, 68, 0.88) 0%, rgba(30, 11, 74, 0.88) 55%, rgba(12, 18, 56, 0.92) 100%) !important;
  box-shadow:
    0 0 18px rgba(0, 229, 255, 0.25),
    0 0 32px rgba(138, 43, 226, 0.22),
    inset 0 0 18px rgba(255, 20, 147, 0.12) !important;
  animation: btr-neon-pulse 6s ease-in-out infinite !important;
}

.kvai-panel-title {
  position: relative !important;
  overflow: hidden !important;
  border: 1.5px solid rgba(255, 20, 147, 0.72) !important;
  border-radius: 14px !important;
  background: linear-gradient(95deg, rgba(255, 20, 147, 0.30), rgba(138, 43, 226, 0.36), rgba(0, 229, 255, 0.28)) !important;
  box-shadow: 0 0 18px rgba(255, 20, 147, 0.35), 0 0 14px rgba(0, 229, 255, 0.25) !important;
  color: #ffffff !important;
  font-weight: 800 !important;
}

/* Tabs Navigation Neon Pills */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: linear-gradient(90deg, rgba(7, 15, 50, 0.92), rgba(29, 10, 68, 0.92), rgba(7, 15, 50, 0.92)) !important;
  border: 1.5px solid rgba(0, 229, 255, 0.58) !important;
  border-radius: 18px !important;
  padding: 6px !important;
  box-shadow: 0 0 22px rgba(0, 229, 255, 0.24), inset 0 0 16px rgba(255, 20, 147, 0.15) !important;
}

[data-testid="stTabs"] button[data-baseweb="tab"] {
  position: relative !important;
  overflow: hidden !important;
  border: 1.5px solid rgba(0, 229, 255, 0.45) !important;
  border-radius: 999px !important;
  background: linear-gradient(145deg, rgba(16, 32, 88, 0.92), rgba(35, 14, 78, 0.92)) !important;
  color: #e6f4ff !important;
  font-weight: 700 !important;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.18) !important;
  transition: all 0.24s ease !important;
}

[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
  transform: translateY(-2px) scale(1.02) !important;
  border-color: #ff1493 !important;
  box-shadow: 0 0 18px rgba(255, 20, 147, 0.65), 0 0 24px rgba(0, 229, 255, 0.45) !important;
}

[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
  background: linear-gradient(100deg, #ff9900 0%, #ff1493 42%, #8a2be2 76%, #00e5ff 100%) !important;
  border: 1.8px solid #ffffff !important;
  color: #ffffff !important;
  box-shadow: 0 0 22px rgba(255, 20, 147, 0.8), 0 0 34px rgba(0, 229, 255, 0.5) !important;
}

/* 4. 📂 កែផ្ទាំង Upload ឱ្យលេចធ្លោជាងមុន */
.btr-upload-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  margin-bottom: 8px;
  border-radius: 18px;
  border: 2px dashed rgba(0, 229, 255, 0.85);
  background:
    radial-gradient(circle at 50% 0%, rgba(0, 229, 255, 0.25), transparent 68%),
    linear-gradient(135deg, rgba(10, 26, 86, 0.92) 0%, rgba(56, 12, 108, 0.90) 52%, rgba(88, 10, 92, 0.88) 100%);
  box-shadow:
    0 0 24px rgba(0, 229, 255, 0.36),
    0 0 36px rgba(255, 20, 147, 0.26),
    inset 0 0 22px rgba(0, 229, 255, 0.18);
  text-align: center;
}

.btr-upload-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}

.btr-cloud-icon {
  font-size: 1.55rem;
  line-height: 1.1;
  filter: drop-shadow(0 0 10px #00e5ff);
}

.btr-upload-title {
  font-size: clamp(0.82rem, 2.2vw, 1.05rem);
  font-weight: 800;
  color: #ffffff;
  text-shadow: 0 0 12px rgba(0, 229, 255, 0.8);
}

.btr-upload-pill-formats, .btr-upload-\ pill-formats {
  font-size: clamp(0.60rem, 1.6vw, 0.75rem);
  color: #d6ecff;
  background: rgba(5, 14, 48, 0.78);
  border: 1px solid rgba(0, 229, 255, 0.55);
  border-radius: 999px;
  padding: 2px 10px;
}

.btr-upload-SideIcon {
  font-size: clamp(1.4rem, 3vw, 2.1rem);
  filter: drop-shadow(0 0 12px rgba(255, 20, 147, 0.85)) drop-shadow(0 0 18px rgba(0, 229, 255, 0.65));
}

[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {
  position: relative !important;
  overflow: hidden !important;
  border: 2.5px dashed #00e5ff !important;
  border-radius: 20px !important;
  background:
    radial-gradient(circle at 50% 50%, rgba(255, 20, 147, 0.22), transparent 72%),
    linear-gradient(135deg, rgba(8, 25, 84, 0.90), rgba(58, 12, 112, 0.90), rgba(14, 34, 96, 0.90)) !important;
  box-shadow:
    0 0 22px rgba(0, 229, 255, 0.38),
    0 0 38px rgba(255, 20, 147, 0.25),
    inset 0 0 26px rgba(0, 229, 255, 0.22) !important;
  padding: 14px 12px !important;
  min-height: 82px !important;
  transition: all 0.28s ease !important;
}

[data-testid="stFileUploader"] section:hover,
[data-testid="stFileUploaderDropzone"]:hover {
  border-color: #ff1493 !important;
  transform: translateY(-2px) !important;
  box-shadow:
    0 0 28px rgba(255, 20, 147, 0.68),
    0 0 44px rgba(0, 229, 255, 0.52),
    inset 0 0 30px rgba(255, 20, 147, 0.28) !important;
}

[data-testid="stFileUploaderDropzone"] button {
  position: relative !important;
  overflow: hidden !important;
  border-radius: 999px !important;
  border: 2px solid #ffffff !important;
  background: linear-gradient(95deg, #ffb300 0%, #ff1493 48%, #9c27b0 82%, #00e5ff 100%) !important;
  color: #ffffff !important;
  font-weight: 800 !important;
  padding: 6px 18px !important;
  box-shadow: 0 0 20px rgba(255, 20, 147, 0.75), 0 0 28px rgba(255, 179, 0, 0.45) !important;
}

/* 5. ⚡ ប៊ូតុងមាន Hover Effect និងពន្លឺរត់ (Running Light Shimmer) */
.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] button {
  position: relative !important;
  overflow: hidden !important;
  border-radius: 999px !important;
  border: 2px solid rgba(255, 255, 255, 0.65) !important;
  background: linear-gradient(95deg, #ff9a00 0%, #ff1493 38%, #8a2be2 72%, #00e5ff 100%) !important;
  color: #ffffff !important;
  font-weight: 800 !important;
  box-shadow:
    0 0 18px rgba(255, 20, 147, 0.58),
    0 0 30px rgba(0, 229, 255, 0.35),
    inset 0 1px 2px rgba(255, 255, 255, 0.45) !important;
  transition: transform 0.22s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.22s ease, filter 0.22s ease !important;
}

/* ពន្លឺរត់កាត់ប៊ូតុងទាំងអស់ */
.stButton > button::after,
.stDownloadButton > button::after,
[data-testid="stFormSubmitButton"] button::after,
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"]::after {
  content: "";
  position: absolute;
  top: 0;
  left: -130%;
  width: 65%;
  height: 100%;
  background: linear-gradient(
    105deg,
    transparent 0%,
    rgba(255, 255, 255, 0.12) 30%,
    rgba(255, 255, 255, 0.62) 50%,
    rgba(0, 229, 255, 0.25) 70%,
    transparent 100%
  );
  transform: skewX(-24deg);
  animation: btr-btn-shimmer 3.2s infinite !important;
  pointer-events: none;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
  transform: translateY(-3px) scale(1.02) !important;
  filter: brightness(1.15) saturate(1.2) !important;
  border-color: #ffffff !important;
  box-shadow:
    0 0 26px rgba(255, 20, 147, 0.90),
    0 0 44px rgba(0, 229, 255, 0.70),
    0 0 60px rgba(138, 43, 226, 0.50) !important;
}

/* ប៊ូតុងទាញយក ពណ៌បៃតង Neon ភ្លឺដូចក្នុងរូបគំរូ */
.stDownloadButton > button {
  background: linear-gradient(95deg, #00c853 0%, #00f59b 52%, #00e5ff 100%) !important;
  border-color: #b9ffdf !important;
  box-shadow: 0 0 20px rgba(0, 245, 155, 0.65), 0 0 34px rgba(0, 229, 255, 0.38) !important;
}

/* ប៊ូតុងធំ «▶ ចាប់ផ្តើមបកប្រែរឿង» */
.st-key-startbar {
  border-radius: 999px !important;
  border: 2px solid rgba(0, 229, 255, 0.78) !important;
  padding: 5px 8px !important;
  background: linear-gradient(90deg, rgba(255, 20, 147, 0.30), rgba(20, 12, 64, 0.95), rgba(0, 229, 255, 0.30)) !important;
  box-shadow: 0 0 26px rgba(255, 20, 147, 0.50), 0 0 38px rgba(0, 229, 255, 0.38) !important;
}

.st-key-startbar .stButton > button,
.st-key-startbar .stButton > button:disabled {
  min-height: 52px !important;
  font-size: clamp(0.95rem, 2.5vw, 1.2rem) !important;
  letter-spacing: 0.5px !important;
  border-radius: 999px !important;
  border: 2px solid #ffffff !important;
  background: linear-gradient(95deg, #ff1493 0%, #8a2be2 48%, #3a4eff 80%, #00e5ff 100%) !important;
  box-shadow:
    0 0 24px rgba(255, 20, 147, 0.78),
    0 0 42px rgba(138, 43, 226, 0.55),
    0 0 56px rgba(0, 229, 255, 0.42) !important;
}

/* Radio Pills, Sliders, Toggles & Selectboxes Neon */
[data-testid="stRadio"] label {
  border-radius: 999px !important;
  border: 1.5px solid rgba(0, 229, 255, 0.55) !important;
  background: linear-gradient(145deg, rgba(12, 28, 82, 0.90), rgba(32, 12, 74, 0.90)) !important;
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.20) !important;
  transition: all 0.2s ease !important;
}

[data-testid="stRadio"] label:has(input:checked) {
  background: linear-gradient(95deg, #ff1493 0%, #8a2be2 55%, #00e5ff 100%) !important;
  border-color: #ffffff !important;
  box-shadow: 0 0 18px rgba(255, 20, 147, 0.75), 0 0 24px rgba(0, 229, 255, 0.50) !important;
}

[data-testid="stToggle"] label:has(input:checked) > div:first-child {
  background: linear-gradient(90deg, #ff1493, #00e5ff) !important;
  box-shadow: 0 0 14px rgba(255, 20, 147, 0.85) !important;
}

[data-testid="stSelectbox"] [data-baseweb="select"] > div,
.stTextInput input, .stTextArea textarea, .stNumberInput input {
  border: 1.5px solid rgba(0, 229, 255, 0.58) !important;
  background: rgba(8, 18, 58, 0.90) !important;
  box-shadow: inset 0 0 12px rgba(0, 229, 255, 0.14), 0 0 10px rgba(138, 43, 226, 0.18) !important;
}
</style>
"""
st.markdown(BAK_TRAE_RUEANG_NEON_UI_CSS, unsafe_allow_html=True)


# =====================================================================
# 🖼️ HEADER IMAGE — Wang Lin (Renegade Immortal) banner behind the title
#   ► ប្តូររូប: ជំនួស _HEADER_IMG_B64 ដោយ base64 នៃរូបថ្មី
#   ► ប្តូរទីតាំងរូប: កែ background-position (ឧ. "center 22%" → "center 40%")
#   ► ងងឹត/ភ្លឺ: កែតម្លៃ rgba(...) ក្នុង linear-gradient (តម្លៃធំ = ងងឹតជាង)
# =====================================================================
_HEADER_IMG_B64 = "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"
_HEADER_IMG_CSS = (
    "<style>\n"
    ".kvai-head.btr-cinematic-header {\n"
    "  background:\n"
    "    linear-gradient(95deg, rgba(4,8,30,.62) 0%, rgba(10,6,36,.34) 50%, rgba(4,8,30,.62) 100%),\n"
    "    url('data:image/jpeg;base64," + _HEADER_IMG_B64 + "') !important;\n"
    "  background-size: cover !important;\n"
    "  background-position: center 22% !important;\n"
    "  background-repeat: no-repeat !important;\n"
    "}\n"
    ".kvai-head.btr-cinematic-header .kvai-title { position: relative; z-index: 1; }\n"
    ".kvai-head.btr-cinematic-header .kvai-h1 { text-shadow: 0 2px 10px rgba(0,0,0,.85) !important; }\n"
    ".kvai-head.btr-cinematic-header p.btr-sub-pill { background: rgba(6,10,40,.78) !important; }\n"
    "</style>"
)
st.markdown(_HEADER_IMG_CSS, unsafe_allow_html=True)


# =====================================================================
# 🧿 LOGO IMAGE — រូបមុខ Vương Lâm ជំនួសរូប 🎬 ក្នុង Header
#   ► ប្តូររូប: ជំនួស _LOGO_IMG_B64 ដោយ base64 នៃរូបថ្មី (ការ៉េ)
# =====================================================================
_LOGO_IMG_B64 = "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"
_LOGO_IMG_CSS = (
    "<style>\n"
    ".kvai-logo.btr-clapper-logo {\n"
    "  font-size: 0 !important;\n"
    "  color: transparent !important;\n"
    "  background: url('data:image/jpeg;base64," + _LOGO_IMG_B64 + "') center / cover no-repeat !important;\n"
    "  overflow: hidden !important;\n"
    "}\n"
    "</style>"
)
st.markdown(_LOGO_IMG_CSS, unsafe_allow_html=True)


# =====================================================================
# 🔥⚔️ REAL FIRE (canvas particles) + SWORD CLICK EFFECT  (ជំនួសឈាម)
#   ► ភ្លើងពិត: particle ស-លឿង→ទឹកក្រូច→ក្រហម រាំតាមខ្យល់ (គូរដោយ canvas ក្នុង parent page)
#   ► ចំណងជើង «បកប្រែរឿង» ឆេះខ្លាំង, ស៊ុម/ប៊ូតុង ភ្លើងតូចលើគែមលើ
#   ► ប្តូរកម្លាំងភ្លើង: កែលេខ spawn(...) ក្នុង emit() (size, ល្បឿន, a=ភ្លឺ), MAX = ចំនួន particle ខ្ពស់បំផុត
# =====================================================================
_FIRE_SWORD_CSS = r"""
<style>
/* ===== 🔥 FIRE (canvas particles) — គ្មាន CSS ស៊ុមភ្លើងទៀតទេ ភ្លើងគូរដោយ JS ===== */
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"], [data-testid="stForm"] { overflow: visible !important; }

/* ===== 🚫 លាក់អក្សរ debug "PLAYING clip..." ===== */
#btr-debug { display: none !important; visibility: hidden !important; }

#btr-fire-canvas { position: fixed !important; left: 0; top: 0; pointer-events: none !important; z-index: 2147482000 !important; }

@keyframes btr-burn-flash {
  0%   { filter: brightness(1.6) saturate(1.5); box-shadow: 0 0 30px rgba(255,120,0,.95), inset 0 0 18px rgba(255,170,0,.55); }
  100% { filter: none; }
}
.btr-burning { animation: btr-burn-flash .7s ease-out !important; }

/* ===== ⚔️ SWORD SLASH — ពេលចុចប៊ូតុង ===== */
.btr-sword-fx { position: fixed; z-index: 2147483000; width: 0; height: 0; pointer-events: none; }
.btr-sword {
  position: absolute; left: 0; top: 0; width: var(--sz); height: auto; opacity: 0;
  animation: btr-sword-swing .8s cubic-bezier(.2,.8,.2,1) forwards;
  filter: drop-shadow(0 0 6px rgba(255,240,180,.85)) drop-shadow(0 0 12px rgba(255,110,0,.9));
}
@keyframes btr-sword-swing {
  0%   { transform: translate(-50%,-50%) translate(70px,-70px) rotate(135deg) scale(.6); opacity: 0; }
  20%  { opacity: 1; }
  55%  { transform: translate(-50%,-50%) translate(-10px,10px) rotate(135deg) scale(1.05); opacity: 1; }
  100% { transform: translate(-50%,-50%) translate(-45px,45px) rotate(135deg) scale(1); opacity: 0; }
}
.btr-slash {
  position: absolute; top: -2px; left: calc(var(--sz) * -.55); width: calc(var(--sz) * 1.1); height: 4px;
  transform: rotate(135deg); opacity: 0; border-radius: 4px;
  background: linear-gradient(90deg, transparent, #ff6a00 15%, #fff3a0 50%, #ff6a00 85%, transparent);
  box-shadow: 0 0 10px #ff8a00, 0 0 20px rgba(255,70,0,.65);
  animation: btr-slash-cut .6s ease-out .08s forwards;
}
@keyframes btr-slash-cut {
  0%   { clip-path: inset(0 100% 0 0); opacity: 1; }
  40%  { clip-path: inset(0 0 0 0); opacity: 1; }
  100% { clip-path: inset(0 0 0 0); opacity: 0; }
}

/* ===== 🔥 ចំណងជើង «បកប្រែរឿង» — អក្សរក្តៅឆេះ (ភ្លើងគូរដោយ canvas) ===== */
.kvai-title .kvai-h1.btr-main-title {
  position: relative !important; display: inline-block !important; filter: none !important;
}
.kvai-title .kvai-h1.btr-main-title span {
  display: inline-block !important;
  background: linear-gradient(180deg, #ff9a8a 0%, #ff2a2a 48%, #a80000 100%) !important;
  -webkit-background-clip: text !important; background-clip: text !important;
  color: transparent !important; -webkit-text-fill-color: transparent !important;
  filter: drop-shadow(0 0 5px rgba(255,30,30,.85)) drop-shadow(0 -3px 10px rgba(220,0,0,.7));
  animation: btr-title-heat .6s ease-in-out infinite alternate !important;
}
@keyframes btr-title-heat {
  0%   { filter: drop-shadow(0 0 4px rgba(255,30,30,.7)) drop-shadow(0 -2px 8px rgba(200,0,0,.55)); }
  100% { filter: drop-shadow(0 0 8px rgba(255,60,50,.95)) drop-shadow(0 -4px 15px rgba(230,0,0,.8)); }
}
@media (prefers-reduced-motion: reduce) { .kvai-title .kvai-h1.btr-main-title span { animation: none !important; } }
</style>
"""
st.markdown(_FIRE_SWORD_CSS, unsafe_allow_html=True)

_FIRE_SWORD_JS = r"""
<script>
(() => {
  const SWORD = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHdpZHRoPScyMjAnIGhlaWdodD0nNDQnIHZpZXdCb3g9JzAgMCAyMjAgNDQnPjxkZWZzPjxsaW5lYXJHcmFkaWVudCBpZD0nYicgeDE9JzAnIHkxPScwJyB4Mj0nMCcgeTI9JzEnPjxzdG9wIG9mZnNldD0nMCcgc3RvcC1jb2xvcj0nI2ZmZmZmZicvPjxzdG9wIG9mZnNldD0nLjUnIHN0b3AtY29sb3I9JyNjNmQwZTQnLz48c3RvcCBvZmZzZXQ9JzEnIHN0b3AtY29sb3I9JyM2ODc1OGYnLz48L2xpbmVhckdyYWRpZW50PjxsaW5lYXJHcmFkaWVudCBpZD0nZCcgeDE9JzAnIHkxPScwJyB4Mj0nMCcgeTI9JzEnPjxzdG9wIG9mZnNldD0nMCcgc3RvcC1jb2xvcj0nI2ZmZTI3YScvPjxzdG9wIG9mZnNldD0nMScgc3RvcC1jb2xvcj0nI2E4NmEwMCcvPjwvbGluZWFyR3JhZGllbnQ+PC9kZWZzPjxwb2x5Z29uIHBvaW50cz0nNjIsMTUgMjA0LDE5IDIxOSwyMiAyMDQsMjUgNjIsMjknIGZpbGw9J3VybCgjYiknIHN0cm9rZT0nIzI3MzA0YScgc3Ryb2tlLXdpZHRoPScxJy8+PGxpbmUgeDE9JzY0JyB5MT0nMjInIHgyPScyMTAnIHkyPScyMicgc3Ryb2tlPScjODc5NGIwJyBzdHJva2Utd2lkdGg9JzEnLz48cGF0aCBkPSdNMTUwIDE4TDIwNCAxOS41TDIxOSAyMkwyMDQgMjQuNUwxNTAgMjZaJyBmaWxsPScjZmY3YTAwJyBmaWxsLW9wYWNpdHk9Jy44NScvPjxwYXRoIGQ9J00xNjggMjZMMTcwIDMzTDE3MiAyNlonIGZpbGw9JyNmZmMyMWEnLz48cmVjdCB4PSc1MCcgeT0nNScgd2lkdGg9JzEyJyBoZWlnaHQ9JzM0JyByeD0nNCcgZmlsbD0ndXJsKCNkKScgc3Ryb2tlPScjNWEzYjAwJy8+PHJlY3QgeD0nMTcnIHk9JzE4JyB3aWR0aD0nMzQnIGhlaWdodD0nOCcgcng9JzMnIGZpbGw9JyMzYTE4MTgnIHN0cm9rZT0nIzE1MDgwOCcvPjxwYXRoIGQ9J00yMiAxOEwyNiAyNk0zMCAxOEwzNCAyNk0zOCAxOEw0MiAyNicgc3Ryb2tlPScjN2EzYTNhJyBzdHJva2Utd2lkdGg9JzEuMicvPjxjaXJjbGUgY3g9JzEyJyBjeT0nMjInIHI9JzcuNScgZmlsbD0ndXJsKCNkKScgc3Ryb2tlPScjNWEzYjAwJy8+PC9zdmc+";

  function driver(win, sword) {
    if (win.__btrFireOn) return;
    win.__btrFireOn = true;
    const doc = win.document;
    const reduce = !!(win.matchMedia && win.matchMedia('(prefers-reduced-motion: reduce)').matches);

    // ---------- ពណ៌ភ្លើងតាមអាយុ: ស-លឿង -> ទឹកក្រូច -> ក្រហម -> ងងឹតរលាយ ----------
    const KEYS = [[0, 255, 226, 120], [.20, 255, 168, 36], [.46, 255, 96, 8], [.74, 185, 28, 0], [1, 55, 6, 0]];
    function ramp(t) {
      for (let i = 1; i < KEYS.length; i++) {
        if (t <= KEYS[i][0]) {
          const a = KEYS[i - 1], b = KEYS[i], f = (t - a[0]) / (b[0] - a[0]);
          return [a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f].map(Math.round);
        }
      }
      return [70, 8, 0];
    }
    const STAGES = 28, SP = 64, sprites = [];
    for (let i = 0; i < STAGES; i++) {
      const c = doc.createElement('canvas'); c.width = c.height = SP;
      const g = c.getContext('2d'), col = ramp(i / (STAGES - 1)), rgb = col.join(',');
      const gr = g.createRadialGradient(SP / 2, SP / 2, 0, SP / 2, SP / 2, SP / 2);
      gr.addColorStop(0, 'rgba(' + rgb + ',1)');
      gr.addColorStop(.35, 'rgba(' + rgb + ',.55)');
      gr.addColorStop(1, 'rgba(' + rgb + ',0)');
      g.fillStyle = gr; g.fillRect(0, 0, SP, SP);
      sprites.push(c);
    }

    // ---------- ភ្លើងក្រហម (សម្រាប់ចំណងជើង) ----------
    const RKEYS = [[0, 255, 130, 100], [.2, 255, 60, 40], [.46, 235, 20, 20], [.74, 150, 0, 10], [1, 40, 0, 0]];
    function rramp(t) {
      for (let i = 1; i < RKEYS.length; i++) {
        if (t <= RKEYS[i][0]) {
          const a = RKEYS[i - 1], b = RKEYS[i], f = (t - a[0]) / (b[0] - a[0]);
          return [a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f].map(Math.round);
        }
      }
      return [40, 0, 0];
    }
    const spritesRed = [];
    for (let i = 0; i < STAGES; i++) {
      const c = doc.createElement('canvas'); c.width = c.height = SP;
      const g = c.getContext('2d'), rgb = rramp(i / (STAGES - 1)).join(',');
      const gr = g.createRadialGradient(SP / 2, SP / 2, 0, SP / 2, SP / 2, SP / 2);
      gr.addColorStop(0, 'rgba(' + rgb + ',1)');
      gr.addColorStop(.35, 'rgba(' + rgb + ',.55)');
      gr.addColorStop(1, 'rgba(' + rgb + ',0)');
      g.fillStyle = gr; g.fillRect(0, 0, SP, SP);
      spritesRed.push(c);
    }

    const old = doc.getElementById('btr-fire-canvas'); if (old) old.remove();
    const cv = doc.createElement('canvas'); cv.id = 'btr-fire-canvas';
    cv.setAttribute('aria-hidden', 'true');
    doc.body.appendChild(cv);
    const ctx = cv.getContext('2d');
    function resize() { cv.width = win.innerWidth; cv.height = win.innerHeight; }
    resize(); win.addEventListener('resize', resize);

    // ---------- particles ----------
    // ===== 🎛️ ប្តូរកម្លាំងភ្លើងនៅទីនេះ =====
    const FIRE = { title: 0.85,   // ចំណងជើង (ភ្លើងក្រហម): 0 = បិទ, 1 = ខ្លាំងបំផុត
                   frame: 0.8,    // ស៊ុម
                   btn: 0.8 };    // ប៊ូតុង
    const P = [], MAX = 1000;
    const rnd = (a, b) => a + Math.random() * (b - a);
    function spawn(x, y, size, vyMin, vyMax, dMin, dMax, spread, a, red) {
      if (P.length >= MAX) return;
      P.push({ x: x, y: y, vx: (Math.random() - .5) * spread, vy: -rnd(vyMin, vyMax),
               s: size * rnd(.7, 1.3), t: 0, d: rnd(dMin, dMax), ph: rnd(0, 6.28), wob: rnd(.2, .8), a: a, r: !!red });
    }
    function burst(cx, cy, w) {
      for (let i = 0; i < 80; i++) spawn(cx + rnd(-w / 2, w / 2), cy + rnd(-6, 6), rnd(9, 20), 1.5, 6.5, .022, .045, 7, .9);
    }

    // ---------- emitters ----------
    const FRAME_SEL = '[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"], [data-testid="stForm"]';
    const BTN_SEL = '.stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button';
    let titles = [], frames = [], btns = [], lastScan = 0;
    function scan() {
      titles = Array.from(doc.querySelectorAll('.btr-main-title'));
      frames = Array.from(doc.querySelectorAll(FRAME_SEL));
      btns = Array.from(doc.querySelectorAll(BTN_SEL));
      hdrEl = doc.querySelector('.kvai-head') || doc.querySelector('.btr-cinematic-header');
    }
    function visible(r, minW, minH) {
      return r.width > minW && r.height > minH && r.top > 4 && r.top < win.innerHeight - 4 && r.bottom > 0;
    }
    function emit() {
      // ចំណងជើង — អណ្ដាតភ្លើងស្តើងៗ ឆេះលើគែមអក្សរ (មិនបាំងអក្សរ)
      titles.forEach((el) => {
        const r = el.getBoundingClientRect();
        if (!visible(r, 40, 10) || FIRE.title <= 0) return;
        const k = Math.max(.7, Math.min(1.6, r.height / 46));
        const n = Math.max(1, Math.round(Math.min(10, r.width / 22) * FIRE.title));
        for (let i = 0; i < n; i++) {
          // ចាប់ផ្តើមពីគែមលើនៃអក្សរ ហើយហក់ឡើងលើ
          spawn(r.left + r.width * rnd(.04, .96), r.top + r.height * rnd(.12, .38),
                7.5 * k, 1.3 * k, 3.4 * k, .02, .034, .9, .6 * Math.min(1, FIRE.title + .3), true);
        }
        // អណ្ដាតវែងៗ ម្តងម្កាល
        if (Math.random() < .35 * FIRE.title) spawn(r.left + r.width * rnd(.08, .92), r.top + r.height * .2,
                5.5 * k, 2.6 * k, 4.6 * k, .016, .026, .8, .5, true);
      });
      // ស៊ុម — ភ្លើងតូចឆេះលើគែមលើ
      let cnt = 0;
      for (let i = 0; i < frames.length && cnt < 10; i++) {
        const r = frames[i].getBoundingClientRect();
        if (!visible(r, 120, 40)) continue;
        cnt++;
        const n = Math.min(3, Math.max(1, Math.round(r.width / 160)));
        for (let j = 0; j < n; j++) if (Math.random() < FIRE.frame) spawn(r.left + 16 + Math.random() * (r.width - 32), r.top + 2, 7, .8, 1.9, .03, .05, 1, .42);
      }
      // ប៊ូតុង — ភ្លើងតូចបំផុត
      cnt = 0;
      for (let i = 0; i < btns.length && cnt < 10; i++) {
        const r = btns[i].getBoundingClientRect();
        if (!visible(r, 60, 20)) continue;
        cnt++;
        if (Math.random() < .6 * FIRE.btn) spawn(r.left + 10 + Math.random() * (r.width - 20), r.top + 3, 5, .6, 1.5, .035, .06, .8, .42);
      }
    }

    // ---------- 🐉 នាគ ២ (ស + ខ្មៅ) ហោះពីចំហៀង មកបុកគ្នាកណ្ដាល header បែកភ្លើង ----------
    //   ប្តូរ: cycle = រយៈពេលម្ដងៗ (ms), fly = ពេលហោះមកដល់កណ្ដាល (ms), enabled:false = បិទនាគ
    const DRAGON = { enabled: true, cycle: 9000, fly: 2200, segs: 40, vmax: .92 };
    let dT0 = null, dCycle = -1, blast = null, hdrEl = null;
    const easeIn = (x) => Math.pow(Math.max(0, Math.min(1, x)), 1.45);

    function dPt(side, v, H) {
      const x0 = side < 0 ? H.l - 50 : H.r + 50;
      const x = x0 + (H.cx - x0) * v;
      const amp = H.h * 0.30 * Math.min(1, Math.max(0, 1 - v));
      const y = H.cy + (side < 0 ? 1 : -1) * amp * Math.sin(v * 13.5 + (side < 0 ? 0 : 0.9));
      return [x, y];
    }
    function dragonPts(side, vh, H, rB) {
      const span = H.w / 2 + 50, dv = (rB * 1.1) / span, pts = [];
      for (let i = 0; i <= DRAGON.segs; i++) pts.push(dPt(side, vh - i * dv, H));
      return pts;
    }
    function drawDragon(pts, white, alpha, rB, ts) {
      const n = pts.length - 1;
      const C = white ? {
        body: '#dde5f1', hi: '#ffffff', sc: 'rgba(120,140,178,.75)', rim: 'rgba(205,228,255,.95)',
        gold: '#e9b84c', eye: '#ffc23a', mane: 'rgba(255,255,255,.92)', mane2: 'rgba(200,225,255,.7)', mouth: '#ff9a3a', crack: null
      } : {
        body: '#0f0b15', hi: '#2c2236', sc: 'rgba(150,35,50,.85)', rim: 'rgba(255,40,60,.95)',
        gold: '#8c1424', eye: '#ff2222', mane: 'rgba(255,70,80,.9)', mane2: 'rgba(120,10,30,.85)', mouth: '#ff2a2a', crack: '#ff3a2a'
      };
      const rad = (i) => rB * (i < 5 ? .74 + .052 * i : 1 - .8 * Math.pow((i - 5) / (n - 5), .85));
      const tan = (i) => {            // ទិសទៅរកក្បាល
        const a = pts[Math.max(0, i - 1)], b = pts[Math.min(n, i + 1)];
        const x = a[0] - b[0], y = a[1] - b[1], l = Math.hypot(x, y) || 1; return [x / l, y / l];
      };
      const up = (t) => { let nx = t[1], ny = -t[0]; if (ny > 0) { nx = -nx; ny = -ny; } return [nx, ny]; };
      ctx.save();
      ctx.globalAlpha = alpha; ctx.lineCap = 'round'; ctx.lineJoin = 'round';

      // 1) សក់/រោមស្ងួតតាមខ្នង (នៅក្រោយខ្លួន)
      ctx.shadowColor = C.rim; ctx.shadowBlur = 8; ctx.lineWidth = 1.3;
      const mEnd = Math.floor(n * .85);
      for (let i = 1; i < mEnd; i++) {
        const t = tan(i), nu = up(t), r = rad(i), c = pts[i];
        for (let k = 0; k < 2; k++) {
          const len = rB * (2.6 + 2.4 * Math.abs(Math.sin(i * 1.7 + k * 2.1))) * (1 - .55 * i / n);
          const fl = Math.sin(ts * .008 + i * .55 + k) * rB * .9;
          const bx = c[0] + nu[0] * r * .85, by = c[1] + nu[1] * r * .85;
          const ex = bx - t[0] * len * 1.1 + nu[0] * (len * .5 + fl), ey = by - t[1] * len * 1.1 + nu[1] * (len * .5 + fl);
          ctx.strokeStyle = k ? C.mane2 : C.mane;
          ctx.beginPath(); ctx.moveTo(bx, by);
          ctx.quadraticCurveTo(bx + nu[0] * len * .9, by + nu[1] * len * .9, ex, ey); ctx.stroke();
        }
      }

      // 2) ខ្លួន: rim glow → ពណ៌ដើម → ឆ្នូតភ្លឺកណ្ដាល
      ctx.shadowColor = C.rim; ctx.shadowBlur = 16;
      for (let i = n - 1; i >= 0; i--) {
        ctx.strokeStyle = C.rim; ctx.lineWidth = rad(i) * 2 + 3;
        ctx.beginPath(); ctx.moveTo(pts[i + 1][0], pts[i + 1][1]); ctx.lineTo(pts[i][0], pts[i][1]); ctx.stroke();
      }
      ctx.shadowBlur = 0;
      for (let i = n - 1; i >= 0; i--) {
        ctx.strokeStyle = C.body; ctx.lineWidth = rad(i) * 2;
        ctx.beginPath(); ctx.moveTo(pts[i + 1][0], pts[i + 1][1]); ctx.lineTo(pts[i][0], pts[i][1]); ctx.stroke();
      }
      ctx.globalAlpha = alpha * .65;
      for (let i = n - 1; i >= 0; i--) {
        ctx.strokeStyle = C.hi; ctx.lineWidth = rad(i) * .55;
        ctx.beginPath(); ctx.moveTo(pts[i + 1][0], pts[i + 1][1]); ctx.lineTo(pts[i][0], pts[i][1]); ctx.stroke();
      }
      ctx.globalAlpha = alpha;

      // 3) ស្រកា (scales)
      ctx.strokeStyle = C.sc; ctx.lineWidth = 1;
      for (let i = 2; i < n - 1; i++) {
        const t = tan(i), nu = up(t), r = rad(i), c = pts[i];
        const ang = Math.atan2(-t[1], -t[0]);
        for (let k = -1; k <= 1; k++) {
          const off = (k + ((i & 1) ? .5 : 0)) * r * .62;
          if (Math.abs(off) > r * .85) continue;
          ctx.beginPath(); ctx.arc(c[0] + nu[0] * off, c[1] + nu[1] * off, r * .5, ang - 1.1, ang + 1.1); ctx.stroke();
        }
      }
      // 4) ស្នាមលាវាក្រហម (នាគខ្មៅ)
      if (C.crack) {
        ctx.shadowColor = C.crack; ctx.shadowBlur = 6; ctx.lineWidth = 1.2; ctx.strokeStyle = C.crack;
        for (let i = 3; i < n - 2; i += 2) {
          const t = tan(i), nu = up(t), r = rad(i), c = pts[i];
          const j1 = Math.sin(i * 12.9) * .4, j2 = Math.sin(i * 7.3) * .4;
          ctx.globalAlpha = alpha * (.45 + .4 * Math.sin(ts * .006 + i));
          ctx.beginPath();
          ctx.moveTo(c[0] - nu[0] * r * .8, c[1] - nu[1] * r * .8);
          ctx.lineTo(c[0] - nu[0] * r * .25 + t[0] * r * j1, c[1] - nu[1] * r * .25 + t[1] * r * j1);
          ctx.lineTo(c[0] + nu[0] * r * .3 + t[0] * r * j2, c[1] + nu[1] * r * .3 + t[1] * r * j2);
          ctx.lineTo(c[0] + nu[0] * r * .8, c[1] + nu[1] * r * .8);
          ctx.stroke();
        }
        ctx.globalAlpha = alpha; ctx.shadowBlur = 0;
      }
      // 5) ព្រុយតូចៗលើខ្នង
      ctx.fillStyle = C.gold; ctx.shadowColor = C.gold; ctx.shadowBlur = 5;
      for (let i = 4; i < n - 2; i += 3) {
        const t = tan(i), nu = up(t), r = rad(i), c = pts[i];
        ctx.beginPath();
        ctx.moveTo(c[0] + nu[0] * r * .9 + t[0] * r * .5, c[1] + nu[1] * r * .9 + t[1] * r * .5);
        ctx.lineTo(c[0] + nu[0] * r * 1.8 - t[0] * r * .6, c[1] + nu[1] * r * 1.8 - t[1] * r * .6);
        ctx.lineTo(c[0] + nu[0] * r * .9 - t[0] * r * .7, c[1] + nu[1] * r * .9 - t[1] * r * .7);
        ctx.closePath(); ctx.fill();
      }
      ctx.shadowBlur = 0;

      // 6) ក្បាល
      const hd = pts[0], h2 = pts[2];
      const ang = Math.atan2(hd[1] - h2[1], hd[0] - h2[0]);
      const u = rB * 1.15;
      ctx.translate(hd[0], hd[1]); ctx.rotate(ang);
      if (Math.cos(ang) < 0) ctx.scale(1, -1);
      const wv = Math.sin(ts * .009) * u * .7;
      // ពុកមាត់វែង ៣ ខ្សែ
      ctx.shadowColor = C.rim; ctx.shadowBlur = 6; ctx.strokeStyle = C.mane; ctx.lineWidth = Math.max(1, u * .12);
      ctx.beginPath(); ctx.moveTo(3.2 * u, .15 * u); ctx.bezierCurveTo(4.8 * u, 1.2 * u + wv, 2.6 * u, 2.8 * u - wv, -1 * u, 2.6 * u + wv * .6); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(3 * u, .3 * u); ctx.bezierCurveTo(4.2 * u, 2 * u - wv, 1.6 * u, 3.8 * u + wv, -2.2 * u, 3.6 * u - wv * .6); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(3.3 * u, -.45 * u); ctx.bezierCurveTo(5 * u, -1.2 * u - wv, 3 * u, -3 * u + wv, -.6 * u, -3.1 * u - wv * .6); ctx.stroke();
      // ពុកចង្កា
      ctx.strokeStyle = C.mane2; ctx.lineWidth = u * .2;
      ctx.beginPath(); ctx.moveTo(1.6 * u, .9 * u); ctx.quadraticCurveTo(.8 * u, 2.1 * u + wv, -1.4 * u, 2.2 * u); ctx.stroke();
      // ស្នែងមានមែក
      ctx.strokeStyle = C.gold; ctx.shadowColor = C.gold; ctx.lineWidth = u * .5;
      ctx.beginPath(); ctx.moveTo(-.4 * u, -.9 * u); ctx.bezierCurveTo(-1.5 * u, -2.2 * u, -3 * u, -2.4 * u, -4.6 * u, -1.6 * u); ctx.stroke();
      ctx.lineWidth = u * .28;
      ctx.beginPath(); ctx.moveTo(-1.6 * u, -1.95 * u); ctx.quadraticCurveTo(-2 * u, -3.2 * u, -1.2 * u, -3.9 * u); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(-3 * u, -2.15 * u); ctx.quadraticCurveTo(-3.5 * u, -3.2 * u, -2.7 * u, -3.7 * u); ctx.stroke();
      // ក្នុងមាត់ឆេះ
      ctx.shadowBlur = 12; ctx.shadowColor = C.mouth; ctx.fillStyle = C.mouth;
      ctx.beginPath(); ctx.ellipse(2.3 * u, .75 * u, 1.2 * u, .5 * u, .2, 0, 6.283); ctx.fill();
      // ថ្គាមក្រោម
      ctx.shadowColor = C.rim; ctx.shadowBlur = 10;
      ctx.save(); ctx.translate(1.2 * u, .35 * u); ctx.rotate(.42);
      ctx.fillStyle = C.body; ctx.strokeStyle = C.rim; ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(2.6 * u, .05 * u); ctx.lineTo(2.5 * u, .45 * u); ctx.quadraticCurveTo(1 * u, .75 * u, 0, .6 * u); ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.restore();
      // ក្បាលលើ (ច្រមុះវែង)
      ctx.beginPath(); ctx.moveTo(-1.4 * u, -.9 * u);
      ctx.quadraticCurveTo(0, -1.4 * u, 1.4 * u, -1.1 * u);
      ctx.lineTo(3.4 * u, -.7 * u); ctx.quadraticCurveTo(3.9 * u, -.55 * u, 3.8 * u, -.2 * u);
      ctx.lineTo(2.2 * u, .1 * u); ctx.quadraticCurveTo(.5 * u, .4 * u, -1.4 * u, .8 * u); ctx.closePath();
      ctx.fillStyle = C.body; ctx.fill(); ctx.stroke();
      ctx.shadowBlur = 0;
      // គែមចិញ្ចើមមាស/ក្រហម
      ctx.strokeStyle = C.gold; ctx.lineWidth = u * .22; ctx.shadowColor = C.gold; ctx.shadowBlur = 6;
      ctx.beginPath(); ctx.moveTo(-1 * u, -1 * u); ctx.quadraticCurveTo(0, -1.3 * u, 1.4 * u, -1 * u); ctx.lineTo(3.3 * u, -.65 * u); ctx.stroke();
      ctx.shadowBlur = 0;
      // ចង្កូមធ្មេញ + រន្ធច្រមុះ
      ctx.fillStyle = '#fff';
      [2.5, 3.2].forEach((x0) => { ctx.beginPath(); ctx.moveTo(x0 * u, .05 * u); ctx.lineTo((x0 + .22) * u, .02 * u); ctx.lineTo((x0 + .1) * u, .65 * u); ctx.closePath(); ctx.fill(); });
      ctx.fillStyle = C.gold; ctx.beginPath(); ctx.arc(3.5 * u, -.42 * u, .13 * u, 0, 6.283); ctx.fill();
      // ភ្នែក
      ctx.save(); ctx.translate(.75 * u, -.45 * u); ctx.rotate(-.3);
      ctx.shadowColor = C.eye; ctx.shadowBlur = 12; ctx.fillStyle = C.eye;
      ctx.beginPath(); ctx.ellipse(0, 0, .38 * u, .19 * u, 0, 0, 6.283); ctx.fill();
      ctx.shadowBlur = 0; ctx.fillStyle = '#000';
      ctx.beginPath(); ctx.ellipse(0, 0, .09 * u, .15 * u, 0, 0, 6.283); ctx.fill();
      ctx.restore();
      ctx.restore();
    }

    function spawnR(x, y, size, sp, dMin, dMax, a, drag) {
      if (P.length >= 1600) return;
      const ang = rnd(0, 6.283), v = sp * rnd(.35, 1);
      P.push({ x: x, y: y, vx: Math.cos(ang) * v, vy: Math.sin(ang) * v, s: size * rnd(.7, 1.3),
               t: 0, d: rnd(dMin, dMax), ph: rnd(0, 6.28), wob: .15, a: a, dx: drag });
    }
    function startBlast(ts, H, rB) {
      blast = { t0: ts, x: H.cx, y: H.cy, R: Math.max(170, H.w * .26) };
      // ផ្ទុះកណ្ដាល
      for (let i = 0; i < 150; i++) spawnR(H.cx, H.cy, rnd(10, 26), 11, .014, .03, .95, .93);
      for (let i = 0; i < 70; i++) spawn(H.cx + rnd(-70, 70), H.cy + rnd(-12, 12), rnd(12, 26), 2, 6.5, .014, .03, 4, .9);
      // នាគបែកជាភ្លើងតាមខ្លួន
      [-1, 1].forEach((side) => {
        dragonPts(side, DRAGON.vmax, H, rB).forEach((pt, i) => {
          for (let k = 0; k < 3; k++) spawnR(pt[0], pt[1], rnd(7, 15), 6, .018, .04, .85, .94);
          if (i % 3 === 0) spawn(pt[0], pt[1], rnd(9, 16), 1.5, 4.5, .018, .035, 3, .8);
        });
      });
    }
    function hdrRect() {
      if (!hdrEl || !hdrEl.isConnected) return null;
      const r = hdrEl.getBoundingClientRect();
      if (r.width < 200 || r.height < 30 || r.bottom < 0 || r.top > win.innerHeight) return null;
      return { l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2 };
    }
    function drawDragons(ts) {
      if (!DRAGON.enabled) return;
      const H = hdrRect(); if (!H) return;
      if (dT0 === null) dT0 = ts + 800;
      const el = ts - dT0; if (el < 0) return;
      const cyc = Math.floor(el / DRAGON.cycle), ph = el - cyc * DRAGON.cycle;
      const rB = Math.max(5, Math.min(16, H.h * .105));
      if (ph >= DRAGON.fly && dCycle !== cyc) { dCycle = cyc; startBlast(ts, H, rB); }
      const fade = ph < DRAGON.fly ? 1 : 1 - (ph - DRAGON.fly) / 160;
      if (fade <= 0) return;
      const vh = DRAGON.vmax * easeIn(ph / DRAGON.fly);
      ctx.save();
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(H.l, H.t - H.h * .5, H.w, H.h * 2, 22); else ctx.rect(H.l, H.t - H.h * .5, H.w, H.h * 2);
      ctx.clip();
      drawDragon(dragonPts(1, vh, H, rB), false, fade, rB, ts);
      const pw = dragonPts(-1, vh, H, rB);
      drawDragon(pw, true, fade, rB, ts);
      ctx.restore();
      // ផេះភ្លើងតូចៗធ្លាក់តាមខ្លួននាគ (ខ្មៅ = ក្រហម, ស = មាស)
      if (ph < DRAGON.fly) {
        const pb = dragonPts(1, vh, H, rB);
        for (let k = 0; k < 2; k++) {
          const a = pb[(Math.random() * pb.length) | 0], b = pw[(Math.random() * pw.length) | 0];
          spawn(a[0], a[1], rnd(5, 9), .2, 1.1, .03, .05, 1.4, .5, true);
          spawn(b[0], b[1], rnd(4, 8), .2, 1, .03, .05, 1.4, .4, false);
        }
      }
    }
    function drawBlast(ts) {
      if (!blast) { if (hdrEl && hdrEl.style.transform) hdrEl.style.transform = ''; return; }
      const e = ts - blast.t0, k = e / 900;
      if (hdrEl) hdrEl.style.transform = e < 350 ? 'translate(' + (rnd(-1, 1) * 5 * (1 - e / 350)).toFixed(1) + 'px,' + (rnd(-1, 1) * 3 * (1 - e / 350)).toFixed(1) + 'px)' : '';
      if (k >= 1) { blast = null; return; }
      const R = blast.R * (1 - Math.pow(1 - k, 3));
      ctx.save(); ctx.globalCompositeOperation = 'lighter';
      const fa = Math.max(0, 1 - k * 2.4);
      if (fa > 0) {
        const g = ctx.createRadialGradient(blast.x, blast.y, 0, blast.x, blast.y, Math.max(10, R * .9));
        g.addColorStop(0, 'rgba(255,245,210,' + (.9 * fa) + ')');
        g.addColorStop(.45, 'rgba(255,140,30,' + (.5 * fa) + ')');
        g.addColorStop(1, 'rgba(255,60,0,0)');
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(blast.x, blast.y, Math.max(10, R * .9), 0, 6.283); ctx.fill();
      }
      ctx.globalAlpha = 1 - k; ctx.shadowColor = '#ff7a00'; ctx.shadowBlur = 18;
      ctx.strokeStyle = 'rgb(255,175,60)'; ctx.lineWidth = 8 * (1 - k) + 1;
      ctx.beginPath(); ctx.arc(blast.x, blast.y, R, 0, 6.283); ctx.stroke();
      ctx.strokeStyle = 'rgb(190,225,255)'; ctx.lineWidth = 4 * (1 - k) + .5;
      ctx.beginPath(); ctx.arc(blast.x, blast.y, R * .68, 0, 6.283); ctx.stroke();
      ctx.restore();
    }

    // ---------- main loop ----------
    let last = 0;
    function frame(ts) {
      win.requestAnimationFrame(frame);
      if (doc.hidden || reduce) return;
      if (ts - last < 26) return;
      last = ts;
      if (ts - lastScan > 500) { scan(); lastScan = ts; }
      emit();
      ctx.clearRect(0, 0, cv.width, cv.height);
      ctx.globalCompositeOperation = 'source-over';
      drawDragons(ts);
      ctx.globalCompositeOperation = 'lighter';
      const wind = Math.sin(ts * .0013) * .35;
      for (let i = P.length - 1; i >= 0; i--) {
        const p = P[i];
        p.t += p.d;
        if (p.t >= 1) { P[i] = P[P.length - 1]; P.pop(); continue; }
        p.x += p.vx + wind + Math.sin(p.ph + p.t * 9) * p.wob;
        p.y += p.vy; p.vy *= (p.dx || .992); if (p.dx) p.vx *= p.dx;
        const size = p.s * (p.t < .12 ? .6 + p.t * 3.3 : 1 - (p.t - .12) * .85);
        if (size < .5) continue;
        ctx.globalAlpha = Math.min(1, (1 - p.t) * 1.5) * p.a;
        ctx.drawImage((p.r ? spritesRed : sprites)[(p.t * (STAGES - 1)) | 0], p.x - size, p.y - size, size * 2, size * 2);
      }
      ctx.globalAlpha = 1;
      drawBlast(ts);
    }
    win.requestAnimationFrame(frame);

    // ---------- ចុចប៊ូតុង: ដាវកាត់ + ភ្លើងផ្ទុះ ----------
    const SEL = '.stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button, ' +
                'button[data-baseweb="tab"], button[data-testid^="stBaseButton"]';
    function fx(btn) {
      const r = btn.getBoundingClientRect();
      const size = Math.max(110, Math.min(230, r.width * 1.1));
      const wrap = doc.createElement('div');
      wrap.className = 'btr-sword-fx';
      wrap.style.cssText = 'left:' + (r.left + r.width / 2) + 'px;top:' + (r.top + r.height / 2) + 'px;--sz:' + size + 'px';
      const line = doc.createElement('i'); line.className = 'btr-slash';
      const img = doc.createElement('img'); img.className = 'btr-sword'; img.src = sword; img.alt = '';
      wrap.appendChild(line); wrap.appendChild(img);
      doc.body.appendChild(wrap);
      burst(r.left + r.width / 2, r.top + r.height / 2, Math.min(r.width, 240));
      btn.classList.add('btr-burning');
      win.setTimeout(() => btn.classList.remove('btr-burning'), 800);
      win.setTimeout(() => { if (wrap.parentNode) wrap.parentNode.removeChild(wrap); }, 1100);
    }
    doc.addEventListener('pointerdown', (e) => {
      const b = e.target && e.target.closest ? e.target.closest(SEL) : null;
      if (!b || b.disabled) return;
      fx(b);
    }, true);
  }

  let PW;
  try { PW = window.parent; void PW.document; } catch (e) { return; }
  if (PW.__btrFireOn) return;
  try {
    const s = PW.document.createElement('script');
    s.textContent = '(' + driver.toString() + ')(window,' + JSON.stringify(SWORD) + ');';
    PW.document.head.appendChild(s);
    s.remove();
  } catch (e) {}
  if (!PW.__btrFireOn) driver(PW, SWORD);
})();
</script>
"""
components.html(_FIRE_SWORD_JS, height=1)


# =====================================================================
# 🎞️ TWO-CLIP CINEMATIC VIDEO BACKGROUND (reliable alternating playback)
# Required repository layout:
#   app.py
#   .streamlit/config.toml  -> [server] / enableStaticServing = true
#   static/drama_bg_1.mp4
#   static/drama_bg_2.mp4
# =====================================================================
BTR_VIDEO_BACKGROUND_CSS = r"""
<style>
/* Make the video visible behind Streamlit without changing widget behavior. */
html, body, #root, .stApp,
[data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stMainBlockContainer"], [data-testid="stHeader"] {
  background: transparent !important;
  background-color: transparent !important;
}
html, body { min-height: 100% !important; }
body { overflow-x: hidden !important; }
#root { position: relative !important; z-index: 1 !important; }
.stApp { position: relative !important; z-index: 1 !important; isolation: auto !important; }
[data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stMainBlockContainer"], .block-container {
  position: relative !important;
  z-index: 1 !important;
}
[data-testid="stHeader"] { background: transparent !important; }
#btr-video-bg-layer {
  position: fixed !important;
  inset: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  height: 100dvh !important;
  overflow: hidden !important;
  z-index: 0 !important;
  pointer-events: none !important;
  background: #030719 !important;
}
#btr-video-bg-layer video {
  position: absolute !important;
  inset: 0 !important;
  display: block !important;
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
  object-position: center center !important;
  opacity: 0 !important;
  transition: opacity 1.2s ease-in-out !important;
  filter: brightness(.88) saturate(1.1) contrast(1.05) !important;
}
#btr-video-bg-layer video.btr-active { opacity: 1 !important; }
#btr-video-bg-layer .btr-video-shade {
  position: absolute !important;
  inset: 0 !important;
  background:
    radial-gradient(ellipse at 10% 12%, rgba(0,185,255,.17), transparent 38%),
    radial-gradient(ellipse at 90% 18%, rgba(255,20,147,.19), transparent 40%),
    linear-gradient(120deg, rgba(2,6,24,.20), rgba(7,8,38,.08) 50%, rgba(22,4,35,.20)) !important;
  pointer-events: none !important;
}
@media (prefers-reduced-motion: reduce) {
  #btr-video-bg-layer video { transition: none !important; }
}
</style>
"""
st.markdown(BTR_VIDEO_BACKGROUND_CSS, unsafe_allow_html=True)

# Mount the video layer in the parent page (not inside the component iframe),
# then switch clips only when the current MP4 fires its real `ended` event.
# The tiny iframe uses height=1 so browsers consistently execute its script.
def _btr_background_sources():
    """Fallback URLs (blob-embedded copies are tried first by the script)."""
    import json as _json
    return _json.dumps([
        ["/app/static/drama_bg_1.mp4", "/static/drama_bg_1.mp4"],
        ["/app/static/drama_bg_2.mp4", "/static/drama_bg_2.mp4"],
    ])


def _btr_background_asset_signature():
    """File size + modification time makes the cached payload refresh when static clips are added."""
    base = os.path.dirname(os.path.abspath(__file__))
    signature = []
    for i in (1, 2):
        path = os.path.join(base, "static", f"drama_bg_{i}.mp4")
        try:
            st_info = os.stat(path)
            signature.append((os.path.basename(path), st_info.st_size, st_info.st_mtime_ns))
        except OSError:
            signature.append((os.path.basename(path), 0, 0))
    return tuple(signature)


@st.cache_resource(show_spinner=False)
def _btr_background_b64(asset_signature):
    """Encode the local background clips. The signature is part of the cache key so
    adding/replacing MP4s after the first app launch cannot leave an empty cached value."""
    import base64 as _b64, json as _json
    base = os.path.dirname(os.path.abspath(__file__))
    out = []
    for i in (1, 2):
        path = os.path.join(base, "static", f"drama_bg_{i}.mp4")
        try:
            with open(path, "rb") as _f:
                out.append(_b64.b64encode(_f.read()).decode("ascii"))
        except Exception as _e:
            print(f"[Dubbing background] Cannot read {path}: {_e}", file=sys.stderr, flush=True)
            out.append("")
    return _json.dumps(out)


# The player runs INSIDE THE PARENT PAGE (injected <script>), not in the tiny iframe,
# because Streamlit can remount that iframe on reruns and kill iframe-owned timers.
# A watchdog (every 400 ms) keeps the playlist going forever: clip1 -> clip2 -> clip1 ...
_BTR_BG_HTML = r"""
<script>
(() => {
  const DATA = { sources: __BTR_SOURCES__, b64: __BTR_B64__ };

  function driver(win, data) {
    const doc = win.document;
    if (win.__btrBeat && Date.now() - win.__btrBeat < 3000) return;   // already alive
    if (win.__btrTimer) { try { win.clearInterval(win.__btrTimer); } catch (e) {} }
    const old = doc.getElementById('btr-video-bg-layer');
    if (old) old.remove();

    function dbg(msg, sticky) {
      return;   // បិទអក្សរ debug (PLAYING clip...) មិនឱ្យបង្ហាញលើអេក្រង់
      try {
        let d = doc.getElementById('btr-debug');
        if (!d) {
          d = doc.createElement('div');
          d.id = 'btr-debug';
          d.style.cssText = 'position:fixed;left:6px;bottom:6px;z-index:2147483647;max-width:70vw;font:12px monospace;color:#0f0;background:rgba(0,0,0,.8);padding:4px 8px;border-radius:6px;pointer-events:none;white-space:pre-wrap;word-break:break-all';
          doc.body.appendChild(d);
        }
        const lines = d.textContent ? d.textContent.split('\n') : [];
        lines.push(msg);
        d.textContent = lines.slice(-5).join('\n');
        if (!sticky) {
          win.clearTimeout(win.__btrDbgT);
          win.__btrDbgT = win.setTimeout(() => { const x = doc.getElementById('btr-debug'); if (x) x.remove(); }, 8000);
        }
      } catch (e) {}
    }

    function blobUrl(b64) {
      try {
        if (!b64) return null;
        const bin = win.atob(b64);
        const arr = new win.Uint8Array(bin.length);
        for (let k = 0; k < bin.length; k++) arr[k] = bin.charCodeAt(k);
        return win.URL.createObjectURL(new win.Blob([arr], { type: 'video/mp4' }));
      } catch (e) { return null; }
    }

    const layer = doc.createElement('div');
    layer.id = 'btr-video-bg-layer';
    layer.setAttribute('aria-hidden', 'true');

    const cand = data.sources.map((c, i) => {
      if (!win.__btrBlobs) win.__btrBlobs = [];
      if (!win.__btrBlobs[i]) win.__btrBlobs[i] = blobUrl(data.b64[i]);
      return win.__btrBlobs[i] ? [win.__btrBlobs[i]].concat(c) : c;
    });

    const failed = [false, false];
    const videos = cand.map((list, i) => {
      const v = doc.createElement('video');
      v.className = 'btr-background-video';
      v.muted = true; v.defaultMuted = true; v.volume = 0;
      v.playsInline = true; v.preload = 'auto'; v.controls = false; v.loop = false;
      v.setAttribute('muted', ''); v.setAttribute('playsinline', '');
      v.disablePictureInPicture = true;
      let n = 0;
      const load = () => {
        if (n >= list.length) { failed[i] = true; dbg('clip' + (i + 1) + ' FAILED all sources', true); return; }
        v.src = new win.URL(list[n], doc.location.href).href;
        v.load();
      };
      v.addEventListener('error', () => {
        dbg('clip' + (i + 1) + ' error code ' + (v.error && v.error.code) + ' (src ' + n + ')', true);
        n += 1; load();
      });
      // Wake the playlist as soon as the first decoded frame is available.
      v.addEventListener('loadeddata', () => {
        if (cur < 0 && i === 0) {
          try { playIdx(0); } catch (e) { dbg('initial play error: ' + e, true); }
        }
      });
      load();
      layer.appendChild(v);
      return v;
    });
    const shade = doc.createElement('div');
    shade.className = 'btr-video-shade';
    layer.appendChild(shade);
    doc.body.insertBefore(layer, doc.body.firstChild);
    dbg('BG layer ok; embedded=' + (data.b64[0] ? 'yes' : 'NO'));

    let cur = -1;
    function good(i) { return !failed[i]; }
    function playIdx(i) {
      const v = videos[i];
      try { v.currentTime = 0; } catch (e) {}
      const pr = v.play();
      if (pr && pr.catch) pr.catch((err) => { dbg('play blocked: ' + err, true); });
      const prev = cur;
      cur = i;
      videos.forEach((x, k) => x.classList.toggle('btr-active', k === i));
      if (prev >= 0 && prev !== i) {
        win.setTimeout(() => { if (cur !== prev) { try { videos[prev].pause(); } catch (e) {} } }, 1400);
      }
      dbg('PLAYING clip' + (i + 1));
    }
    function nextIdx() {
      const other = 1 - cur;
      if (good(other)) return other;
      return good(cur) ? cur : -1;
    }

    videos.forEach((v, i) => {
      v.addEventListener('ended', () => { if (i === cur) { const n = nextIdx(); if (n >= 0) playIdx(n); } });
    });

    function tick() {
      win.__btrBeat = Date.now();
      if (!doc.getElementById('btr-video-bg-layer')) { doc.body.insertBefore(layer, doc.body.firstChild); }
      if (cur < 0) {
        const first = good(0) ? 0 : (good(1) ? 1 : -1);
        if (first >= 0 && videos[first].readyState >= 2) playIdx(first);
        return;
      }
      const v = videos[cur];
      const d = v.duration;
      if (v.ended || (d && isFinite(d) && v.currentTime >= d - 0.15)) {
        const n = nextIdx();
        if (n >= 0) playIdx(n);
        return;
      }
      if (v.paused) { const pr = v.play(); if (pr && pr.catch) pr.catch(() => {}); }
    }
    win.__btrTimer = win.setInterval(tick, 400);

    const kick = () => { if (cur >= 0) { const v = videos[cur]; if (v.paused) v.play().catch(() => {}); } };
    doc.addEventListener('pointerdown', kick, { passive: true });
    doc.addEventListener('keydown', kick);
    doc.addEventListener('visibilitychange', kick);
    tick();
  }

  function boot(tries) {
    let P;
    try { P = window.parent; void P.document; } catch (e) { return; }
    if (!P.document.getElementById('root') && !P.document.querySelector('.stApp')) {
      if (tries < 40) window.setTimeout(() => boot(tries + 1), 250);
      return;
    }
    if (P.__btrBeat && Date.now() - P.__btrBeat < 3000) return;       // already running
    try {
      const s = P.document.createElement('script');
      s.textContent = '(' + driver.toString() + ')(window,' + JSON.stringify(DATA) + ');';
      P.document.head.appendChild(s);
      s.remove();
    } catch (e) {}
    if (!(P.__btrBeat && Date.now() - P.__btrBeat < 3000)) {
      driver(P, DATA);                                                // fallback if inline script is blocked
    }
  }
  boot(0);
})();
</script>
"""
_BTR_BG_SIGNATURE = _btr_background_asset_signature()
_BTR_BG_DATA = _btr_background_b64(_BTR_BG_SIGNATURE)
if not any(size > 0 for _name, size, _mtime in _BTR_BG_SIGNATURE):
    st.warning("រកមិនឃើញ Background MP4 ទេ។ សូមដាក់ drama_bg_1.mp4 និង drama_bg_2.mp4 ក្នុង Folder static ក្បែរ app.py ហើយ Refresh App។")
components.html(
    _BTR_BG_HTML.replace("__BTR_SOURCES__", _btr_background_sources()).replace("__BTR_B64__", _BTR_BG_DATA),
    height=1,
)
