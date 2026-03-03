import streamlit as st
import json
import html as html_lib
from datetime import datetime
import random
import os
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from db import get_cursor, init_db
import gspread
from google.oauth2.service_account import Credentials
import time
import pandas as pd

# =====================================================
# Google Sheets Setup (من الكود الأول)
# =====================================================
try:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=scopes)
    client = gspread.authorize(creds)
    SPREADSHEET_NAME = "Diwan_Legs"   #غيّر الاسم إذا أردت
    spreadsheet = client.open(SPREADSHEET_NAME)
except Exception as e:
    st.error("خطأ في الاتصال بـ Google Sheets")
    st.code(str(e))
    st.stop()

# =====================================================
# CONSTANTS
# =====================================================
AMEND_TYPES = ["تعديل مادة", "إضافة مادة", "إلغاء مادة"]
AMEND_BADGE_CSS = {
    "تعديل مادة": "badge-edit",
    "إضافة مادة": "badge-add",
    "إلغاء مادة": "badge-del",
}
LAW_KINDS = ["قانون ج1", "قانون ج2"]
KIND_TO_TABLE = {
    "قانون ج1": {"original": "laws_p1_original", "modified": "laws_p1_modified"},
    "قانون ج2": {"original": "laws_p2_original", "modified": "laws_p2_modified"},
}

SAVE_MESSAGES = [
    "عييييش! كفو عليك يا أسد 🦁", "الله يعطيك العافية يا غالي! شغل نظيف 👏",
    "يا زلمة إبداع! استمر هيك 💪", "هيييه! تمام يا بطل الأردن 🇯🇴",
    "والله فخورين فيك! يلا عالتالي 🚀", "كفو والله! دير بالك أنت صاروخ ⚡",
    "يا سلام عليك! 🌟", "ايوااا هيك! أنت الأفضل 😎",
]

FINAL_MESSAGES = [
    "🎉 يا سلام عليك! خلّصت {kind} كلها، والله إنك قوي!",
    "👏 الله يعطيك العافية يا غالي! مراجعة نظيفة 100%!",
    "💪 دير بالك، أنت أسد اليوم! خلّصت كل {kind} زي الحلاوة!",
]

# =====================================================
# AUTH (باقي كما هو)
# =====================================================
credentials_str = os.environ.get("CREDENTIALS_YAML")
if not credentials_str:
    st.error("لم يتم العثور على CREDENTIALS_YAML")
    st.stop()

try:
    config = yaml.safe_load(credentials_str)
except Exception as e:
    st.error(f"خطأ في تحليل بيانات المستخدمين: {str(e)}")
    st.stop()

authenticator = stauth.Authenticate(
    credentials=config['credentials'],
    cookie_name=config['cookie']['name'],
    cookie_key=config['cookie']['key'],
    cookie_expiry_days=config['cookie']['expiry_days'],
)

name, authentication_status, username = authenticator.login('تسجيل الدخول', 'main')

if authentication_status:
    st.session_state.authenticated = True
    st.session_state.user_name = name or username
elif authentication_status is False:
    st.error('اسم المستخدم أو كلمة المرور غير صحيحة')
    st.stop()
elif authentication_status is None:
    st.warning('الرجاء إدخال اسم المستخدم وكلمة المرور')
    st.stop()

# =====================================================
# Google Sheets Helpers (من الكود الأول – معدل)
# =====================================================
def get_worksheet(base_name: str) -> gspread.Worksheet:
    sheet_title = f"{st.session_state.user_name}_{base_name}"
    try:
        return spreadsheet.worksheet(sheet_title)
    except gspread.exceptions.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=sheet_title, rows=1000, cols=30)

def save_progress(current_idx: int, max_reached: int, kind: str):
    ws = get_worksheet(f"تقدم_{kind}")
    try:
        ws.clear()
        ws.append_row(["current_index", "max_reached_idx", "last_updated"])
        ws.append_row([str(current_idx), str(max_reached), datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    except:
        pass

def load_progress(kind: str) -> tuple[int, int]:
    try:
        ws = get_worksheet(f"تقدم_{kind}")
        records = ws.get_all_records()
        if records:
            last = records[-1]
            return int(last.get("current_index", 0)), int(last.get("max_reached_idx", 0))
        return 0, 0
    except:
        return 0, 0

# =====================================================
# STYLES (من الكود الأول – معدل ليتناسب مع المحتوى)
# =====================================================
def apply_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    * {font-family: 'Cairo', sans-serif; direction: rtl;}
    .stApp {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);}
    .main h1, .main h2, .main h3 {color: white !important;}
    [data-testid="stSidebar"] {background: rgba(255,255,255,0.1) !important;}
    [data-testid="stSidebar"] * {color: white !important;}
    .law-card {
        background: rgba(255,255,255,0.95);
        padding: 1.8rem;
        border-radius: 12px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        margin: 1.5rem 0;
        color: #1e293b;
    }
    .article-text {
        line-height: 2.0;
        font-size: 1.05rem;
        white-space: pre-wrap;
        color: #334155;
    }
    .amend-section {
        background: rgba(99,102,241,0.08);
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 10px;
        padding: 1.2rem;
        margin: 1rem 0;
    }
    .badge-edit {background:rgba(59,130,246,.15); color:#60a5fa;}
    .badge-add  {background:rgba(34,197,94,.15); color:#4ade80;}
    .badge-del  {background:rgba(239,68,68,.15); color:#f87171;}
    .amend-badge {padding:6px 14px; border-radius:20px; font-size:0.85rem; font-weight:700;}
    .stButton>button {
        width: 100%;
        background: white !important;
        color: #667eea !important;
        border: 2px solid #667eea !important;
        padding: 0.9rem;
        border-radius: 10px;
        font-weight: 700;
    }
    .stButton>button:hover {
        background: #667eea !important;
        color: white !important;
    }
    .wizard-container {
        background: white;
        padding: 1.8rem;
        border-radius: 14px;
        margin: 1.5rem 0;
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

apply_styles()

# باقي الدوال (row_to_law, load_laws, save_law, toast, migrate_...) تبقى كما هي
# ... (انسخها من الكود الأصلي الثاني)

# =====================================================
# دالة عرض القانون مع wizard + celebrate
# =====================================================
def show_law(idx, laws, kind):
    law = laws[idx]
    total = len(laws)
    progress = int(((idx + 1) / total) * 100) if total else 0

    # wizard steps (من الكود الأول)
    steps_to_show = min(5, total)
    cols = st.columns(steps_to_show)
    for i in range(steps_to_show):
        if total <= 5:
            actual = i
        else:
            if idx < 2: actual = i
            elif idx >= total - 3: actual = total - 5 + i
            else: actual = idx - 2 + i
        with cols[i]:
            if actual < idx:
                color, icon, label = '#48bb78', '✓', 'مكتمل'
            elif actual == idx:
                color, icon, label = '#f97316', '▶', 'الحالي'
            else:
                color, icon, label = '#e2e8f0', str(actual+1), 'قادم'
            st.markdown(f"""
            <div style="text-align:center;">
                <div style="width:60px;height:60px;border-radius:50%;background:{color};color:white;
                            display:flex;align-items:center;justify-content:center;margin:0 auto 0.4rem;
                            font-weight:bold;font-size:1.4em;box-shadow:0 4px 10px rgba(0,0,0,0.2);">
                    {icon}
                </div>
                <div style="color:{color};font-weight:600;">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class='wizard-container'>
        <h3 style='color:#667eea;'>مراجعة {kind} – السجل {idx+1} من {total}</h3>
        <div style='background:#e2e8f0;height:14px;border-radius:10px;overflow:hidden;margin:1.5rem 0;'>
            <div style='height:100%;background:linear-gradient(90deg,#667eea,#48bb78);width:{progress}%;'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # عرض القانون (نفس التصميم الأصلي + card جديد)
    st.markdown(f"""
    <div class="law-card">
        <h2 style="color:#1e40af;margin-bottom:0.8rem;">{html_lib.escape(law["Leg_Name"])}</h2>
        <p style="color:#475569;font-size:1.1rem;">
            رقم القانون: <b>{law["Leg_Number"]}</b>  |  السنة: <b>{law["Year"]}</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # باقي عرض المواد + التعديلات + الأزرار (كما في الكود الأصلي)
    # ... (انسخ show_law الأصلية هنا مع التعديلات الطفيفة على الألوان إذا لزم)

    # بعد الحفظ الناجح (في save_law أو بعد تعديل)
    # يمكن استدعاء:
    # celebrate_save()

def celebrate_save():
    st.balloons()
    time.sleep(0.4)
    st.snow()
    msg = random.choice(SAVE_MESSAGES)
    st.markdown(f"""
    <div style="text-align:center; padding:1.6rem; background:linear-gradient(90deg,#48bb78,#1e40af);
                color:white; border-radius:16px; margin:2rem 0; font-size:1.9rem; font-weight:bold;">
        🎉 {msg} 🎉
    </div>
    """, unsafe_allow_html=True)

def celebrate_completion(kind):
    msg = random.choice(FINAL_MESSAGES).format(kind=kind)
    st.balloons()
    st.snow()
    st.balloons()
    st.markdown(f"""
    <div style="text-align:center; padding:3rem; background:linear-gradient(135deg,#667eea,#764ba2);
                border-radius:20px; margin:3rem 0;">
        <h1 style="color:white;">{msg}</h1>
        <p style="color:white; font-size:1.6rem;">مبروك! 🇯🇴 أنت قدها وقدود 💪</p>
    </div>
    """, unsafe_allow_html=True)

# =====================================================
# MAIN – معدل
# =====================================================
def main():
    st.set_page_config("مراجعة التشريعات", layout="wide", page_icon="⚖️")

    try:
        init_db()
    except Exception as e:
        st.error(f"خطأ في تهيئة قاعدة البيانات: {e}")
        return

    # migration (كما هي)
    migration_name = "initial_data_load_v1"
    if not has_migration_run(migration_name):
        # ... (باقي كود الـ migration كما هو)

    st.sidebar.success(f"👤 {st.session_state.user_name}")
    authenticator.logout("تسجيل الخروج", "sidebar")

    st.sidebar.markdown("### نوع القانون")
    kind = st.sidebar.radio("", LAW_KINDS)

    laws = load_laws(kind)
    if not laws:
        st.warning(f"لا توجد بيانات لـ {kind}")
        return

    current_idx, max_reached = load_progress(kind)
    if "current_idx" not in st.session_state:
        st.session_state.current_idx = current_idx

    idx = st.session_state.current_idx
    show_law(idx, laws, kind)

    col1, col2 = st.columns(2)
    with col1:
        if idx > 0 and st.button("⏮️ السابق"):
            st.session_state.current_idx -= 1
            save_progress(st.session_state.current_idx, max_reached, kind)
            st.rerun()
    with col2:
        if idx < len(laws)-1:
            if st.button("التالي ⏭️", type="primary"):
                st.session_state.current_idx += 1
                new_max = max(max_reached, st.session_state.current_idx)
                save_progress(st.session_state.current_idx, new_max, kind)
                if st.session_state.current_idx >= len(laws)-1:
                    celebrate_completion(kind)
                st.rerun()

if __name__ == "__main__":
    main()
