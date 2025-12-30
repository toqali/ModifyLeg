"""
نظام مقارنة التشريعات القانونية
مع تسجيل دخول (يوزر + باسورد) + حفظ دائم للنتائج والتقدم لكل مستخدم
جاهز للعمل 100% - ديسمبر 2025
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os
import gspread
from google.oauth2.service_account import Credentials
import hashlib
import time  # للتأخير ضد rate limit

# ==================== ربط Google Sheets ====================
try:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=scopes)
    client = gspread.authorize(creds)
   
    SPREADSHEET_NAME = "Diwan_Legs"
   
    st.info("جاري محاولة الاتصال بـ Google Sheets باسم 'Diwan_Legs'...")
    spreadsheet = client.open(SPREADSHEET_NAME)
    st.success("✔️ تم الاتصال بنجاح! التطبيق شغال دلوقتي.")
   
except gspread.exceptions.SpreadsheetNotFound:
    st.error("❌ الملف 'Diwan_Legs' مش موجود أو الاسم غلط بالحرف.")
    st.stop()
   
except gspread.exceptions.APIError as e:
    st.error("❌ خطأ في الصلاحيات أو الـ API")
    st.code(str(e))
    st.stop()
   
except Exception as e:
    st.error("❌ خطأ غير متوقع")
    st.code(str(e))
    st.stop()

# ==================== دوال تسجيل الدخول ====================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username: str, password: str) -> bool:
    try:
        users_ws = spreadsheet.worksheet("Users")
        records = users_ws.get_all_records()
        if not records:
            return False
        users_df = pd.DataFrame(records)
        users_df.columns = users_df.columns.str.strip()
        if 'Username' not in users_df.columns or 'Password' not in users_df.columns:
            return False
        user_row = users_df[users_df['Username'] == username]
        if user_row.empty:
            return False
        stored_password = user_row['Password'].iloc[0]
        return password == stored_password  # مقارنة مباشرة
    except:
        return False

# ==================== جلسة تسجيل الدخول ====================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_name = None

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center; color: #667eea;'>🔐 تسجيل الدخول إلى النظام</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>أدخل اسم المستخدم وكلمة المرور للمتابعة</p>", unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("اسم المستخدم", placeholder="مثال: diwan")
        password = st.text_input("كلمة المرور", type="password", placeholder="أدخل كلمة المرور")
        submit = st.form_submit_button("دخول", use_container_width=True)
        if submit:
            if authenticate(username, password):
                st.session_state.authenticated = True
                st.session_state.user_name = username
                st.success(f"✅ مرحباً {username}! تم تسجيل الدخول بنجاح")
                st.rerun()
            else:
                st.error("❌ اسم مستخدم أو كلمة مرور غير صحيحة")
    st.stop()

# المستخدم مسجل دخول
user_name = st.session_state.user_name
st.sidebar.success(f"👤 المستخدم: {user_name}")

# زر تسجيل الخروج
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.authenticated = False
    st.session_state.user_name = None
    st.rerun()

WORKSHEET_NAMES = {
    'نظام': 'نظام',
    'قانون': 'قانون',
    'تعليمات': 'تعليمات',
    'اتفاقيات': 'اتفاقيات',
}

# ==================== إعدادات الصفحة ====================
st.set_page_config(
    page_title="نظام مقارنة التشريعات القانونية",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.header("📋 نوع التشريع")
option = st.sidebar.radio("اختر نوع البيانات:", ["نظام", "قانون", "تعليمات", "اتفاقيات"])

# ==================== دوال Google Sheets ====================
def get_worksheet(base_name: str, suffix: str = ""):
    sheet_title = f"{user_name}_{base_name}"
    if suffix:
        sheet_title += f"_{suffix}"
    try:
        return spreadsheet.worksheet(sheet_title)
    except gspread.exceptions.WorksheetNotFound:
        st.info(f"إنشاء شيت جديد: {sheet_title}")
        return spreadsheet.add_worksheet(title=sheet_title, rows=1000, cols=30)

def save_to_gsheet(data: list, base_name: str):
    ws = get_worksheet(base_name)
    
    if not data or len(data) == 0:
        ws.clear()
        ws.append_row(["لا توجد بيانات محفوظة بعد"])
        return
    
    df = pd.DataFrame(data)
    df = df.fillna("")
    df = df.replace({None: "", pd.NaT: ""})
    df = df.astype(str)
    
    try:
        ws.clear()
        ws.update([df.columns.values.tolist()] + df.values.tolist())
        time.sleep(2)
    except Exception as e:
        st.error("خطأ أثناء الحفظ على Google Sheets")
        st.code(str(e))

def load_from_gsheet(base_name: str) -> list:
    try:
        ws = get_worksheet(base_name)
        records = ws.get_all_records()
        return records if records else []
    except:
        return []

def save_missing_to_gsheet(data: list):
    if not data or len(data) == 0:
        ws = get_worksheet(WORKSHEET_NAMES[option] + "_مفقودة")
        ws.clear()
        ws.append_row(["لا توجد بيانات محفوظة بعد"])
        return
    
    df = pd.DataFrame(data)
    df = df.fillna("")
    df = df.replace({None: "", pd.NaT: ""})
    df = df.astype(str)
    
    ws = get_worksheet(WORKSHEET_NAMES[option] + "_مفقودة")
    try:
        ws.clear()
        ws.update([df.columns.values.tolist()] + df.values.tolist())
        time.sleep(2)
    except Exception as e:
        st.error("خطأ أثناء حفظ القيم المفقودة")
        st.code(str(e))

def load_missing_from_gsheet() -> list:
    return load_from_gsheet(WORKSHEET_NAMES[option] + "_مفقودة")

# ==================== حفظ واسترجاع التقدم دائمًا ====================
def get_progress_worksheet():
    sheet_title = f"{user_name}_تقدم_{option}"
    try:
        return spreadsheet.worksheet(sheet_title)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=sheet_title, rows=100, cols=3)
        ws.append_row(["current_index", "max_reached_idx", "last_updated"])
        ws.append_row(["0", "0", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        return ws

def save_progress(current_idx: int, max_reached: int):
    ws = get_progress_worksheet()
    try:
        ws.clear()
        ws.append_row(["current_index", "max_reached_idx", "last_updated"])
        ws.append_row([str(current_idx), str(max_reached), datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        time.sleep(2)
    except Exception as e:
        st.warning("خطأ في حفظ التقدم (بس البيانات محفوظة)")

def load_progress() -> tuple[int, int]:
    try:
        ws = get_progress_worksheet()
        records = ws.get_all_records()
        if records:
            last = records[-1]
            current = int(last.get("current_index", 0))
            max_r = int(last.get("max_reached_idx", 0))
            return current, max_r
        else:
            return 0, 0
    except Exception as e:
        st.warning("خطأ في تحميل التقدم، هيبدأ من الصفر")
        return 0, 0

# ==================== Session Manager ====================
class SessionManager:
    @staticmethod
    def get_unique_key(base: str) -> str:
        return f"{base}_{option}_{user_name}"

    @staticmethod
    def initialize():
        comp_key = SessionManager.get_unique_key("comparison_data")
        idx_key = SessionManager.get_unique_key("current_index")
        max_key = SessionManager.get_unique_key("max_reached_idx")
        form_key = SessionManager.get_unique_key("show_custom_form")
        next_key = SessionManager.get_unique_key("show_next_in_review")
        malq_key = SessionManager.get_unique_key("malq_completed")

        if comp_key not in st.session_state:
            st.session_state[comp_key] = load_from_gsheet(WORKSHEET_NAMES[option])

        if malq_key not in st.session_state:
            st.session_state[malq_key] = load_missing_from_gsheet()

        current_idx, max_reached = load_progress()
        st.session_state[idx_key] = current_idx
        st.session_state[max_key] = max_reached
        st.session_state[next_key] = False
        st.session_state[form_key] = False

        save_progress(current_idx, max_reached)

    @staticmethod
    def save_persistent():
        comp_key = SessionManager.get_unique_key("comparison_data")
        save_to_gsheet(st.session_state[comp_key], WORKSHEET_NAMES[option])

def initialize_session_state():
    SessionManager.initialize()

def save_persistent_data():
    SessionManager.save_persistent()

def save_comparison_record(data: dict, source: str) -> None:
    comp_key = SessionManager.get_unique_key("comparison_data")
    new_record = {
        'تاريخ الإدخال': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'المصدر الصحيح': source,
        'المعدل بواسطة': user_name,
        **data
    }
    st.session_state[comp_key].append(new_record)
    save_persistent_data()

def move_to_next_record(total_records: int, current_index: int) -> None:
    idx_key = SessionManager.get_unique_key("current_index")
    max_key = SessionManager.get_unique_key("max_reached_idx")
    next_key = SessionManager.get_unique_key("show_next_in_review")

    if current_index + 1 < total_records:
        new_index = current_index + 1
        st.session_state[idx_key] = new_index
        new_max = max(st.session_state.get(max_key, 0), new_index)
        st.session_state[max_key] = new_max
        st.session_state[next_key] = False
        
        save_progress(new_index, new_max)
        save_persistent_data()
        st.rerun()
    else:
        st.balloons()
        st.success("تم الانتهاء من جميع السجلات!")
        save_progress(current_index + 1, current_index + 1)

# ==================== تحميل البيانات الأصلية ====================
@st.cache_data
def load_csv_data(kind: str):
    PATHS = {
        'نظام': {'qis': r'extData/Bylaws/Qis_ByLaws_V2.xlsx', 'diwan': r'extData/Bylaws/Diwan_ByLaws_V2.xlsx'},
        'قانون': {'qis': r'extData/Laws/Qis_Laws_V2.xlsx', 'diwan': r'extData/Laws/Diwan_Laws_V2.xlsx'},
        'تعليمات': {'qis': r'extData/Instructions/Qis_Instructions.xlsx', 'diwan': r'extData/Instructions/Diwan_Instructions.xlsx'},
        'اتفاقيات': {'qis': r'extData/Agreements/Qis_Agreements.xlsx', 'diwan': r'extData/Agreements/Diwan_Agreements.xlsx'},
    }
    if kind not in PATHS:
        st.error(f"النوع '{kind}' غير مدعوم.")
        return None, None
    def read_excel_safely(path, name):
        if not os.path.exists(path):
            st.error(f"الملف غير موجود: {path}")
            return None
        try:
            df = pd.read_excel(path)
            st.sidebar.success(f"✅ {name}")
            return df
        except Exception as e:
            st.error(f"خطأ في تحميل {name}: {e}")
            return None
    qis_df = read_excel_safely(PATHS[kind]['qis'], "قسطاس")
    diwan_df = read_excel_safely(PATHS[kind]['diwan'], "الديوان")
    if qis_df is None or diwan_df is None:
        st.stop()
    return qis_df, diwan_df

# ==================== التنسيقات ====================
def apply_styles():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
        * {font-family: 'Cairo', sans-serif; direction: rtl;}
        body, .stApp {font-size: 18px;}
        .main {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem;}
        .stApp {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);}
        .main > div > div > div > div, .main h1, .main h2, .main h3:not(.comparison-card h3) {color: white !important;}
        .css-1d391kg, [data-testid="stSidebar"] {background: rgba(255, 255, 255, 0.1) !important;}
        [data-testid="stSidebar"] * {color: white !important;}
        .title-container {background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); text-align: center; margin-bottom: 2rem;}
        .comparison-card {background: rgba(255, 255, 255, 0.95); padding: 1.5rem; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin: 1rem 0;}
        .comparison-card * {color: #2d3748 !important;}
        .comparison-card h3, .comparison-card h4 {color: #667eea !important;}
        .stButton>button {width: 100%; background: white !important; color: #667eea !important; border: 3px solid #667eea !important; padding: 1rem; border-radius: 10px; font-weight: 700; font-size: 1.2em; box-shadow: 0 4px 15px rgba(0,0,0,0.2);}
        .stButton>button:hover {transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.3); background: #667eea !important; color: white !important;}
        .wizard-container {background: white; padding: 2rem; border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 5px 20px rgba(0,0,0,0.15);}
        .cmp-wrapper {max-height: 300px; overflow: auto; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.12); border: 1px solid #e2e8f0; background: white !important; margin: 1.5rem 0;}
        .cmp-table {width: 100%; border-collapse: separate; border-spacing: 0; direction: rtl; font-size: 0.94rem; table-layout: fixed; background: white !important;}
        .cmp-table thead th {background: #1e40af !important; color: white !important; padding: 16px 12px; text-align: center; font-weight: 700; font-size: 1.05em;}
        .cmp-table tbody td {padding: 14px 12px; vertical-align: middle; text-align: center; background: white !important; border-bottom: 1px solid #e2e8f0;}
        .cmp-table tbody td:first-child {text-align: right !important; font-weight: 700; color: #1f2937; background: #f8fafc !important;}
        .cmp-table tbody tr:hover td {background: #dbeafe !important;}
        .cmp-diff {background: #fee2e2 !important; font-weight: 600; color: #991b1b;}
        </style>
    """, unsafe_allow_html=True)

# ==================== دوال أخرى ====================
def parse_status(val):
    if val is None: return None
    if isinstance(val, (int, float)):
        try: return int(val)
        except: return None
    try:
        v = str(val).strip()
        if v == '': return None
        if v == 'غير ساري': return 2
        if v.isdigit(): return int(v)
        f = float(v.replace(',', '.'))
        return int(f)
    except:
        return None

def get_legislation_data(index: int, source_df: pd.DataFrame) -> dict:
    if index >= len(source_df):
        return {}
    row = source_df.iloc[index]
    return {k: ('' if pd.isna(v) else v) for k, v in row.to_dict().items()}

def render_wizard_steps(current_index: int, total_records: int):
    steps_to_show = min(5, total_records)
    cols = st.columns(steps_to_show)
    for i in range(steps_to_show):
        if total_records <= 5:
            actual_index = i
        else:
            if current_index < 2:
                actual_index = i
            elif current_index >= total_records - 3:
                actual_index = total_records - 5 + i
            else:
                actual_index = current_index - 2 + i
        with cols[i]:
            if actual_index < current_index:
                circle_color = '#48bb78'
                icon = '✓'
                label_text = 'مكتمل'
            elif actual_index == current_index:
                circle_color = '#f97316'
                icon = '▶'
                label_text = 'الحالي'
            else:
                circle_color = '#e2e8f0'
                icon = str(actual_index + 1)
                label_text = 'قادم'
            animation_style = "animation: pulse 2s infinite;" if actual_index == current_index else ""
            st.markdown(f"""
                <div style="text-align: center; margin-bottom: 1rem;">
                    <div style="width: 60px; height: 60px; border-radius: 50%; background: {circle_color}; color: white; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.5rem auto; font-weight: bold; font-size: 1.3em; box-shadow: 0 4px 10px rgba(0,0,0,0.2); {animation_style}">
                        {icon}
                    </div>
                    <div style="color: {circle_color}; font-size: 0.9em; font-weight: 600;">{label_text}</div>
                </div>
            """, unsafe_allow_html=True)

def render_law_comparison(qistas_df: pd.DataFrame, diwan_df: pd.DataFrame, current_index: int, total_records: int):
    qistas_data = get_legislation_data(current_index, qistas_df)
    diwan_data = get_legislation_data(current_index, diwan_df)
    st.markdown("<h3 style='color: #667eea !important; text-align: center;'>المقارنة التفصيلية</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    FIELD_MAPPING = {
        "نظام": {"name_qis": "LegName", "name_diw": "ByLawName", "num_qis": "LegNumber", "num_diw": "ByLawNumber"},
        "قانون": {"name_qis": "LegName", "name_diw": "Law_Name", "num_qis": "LegNumber", "num_diw": "Law_Number"},
        "تعليمات": {"name_qis": "LegName", "name_diw": "Instruction_Name", "num_qis": "LegNumber", "num_diw": "Instruction_Number"},
        "اتفاقيات": {"name_qis": "LegName", "name_diw": "Agreement_Name", "num_qis": "LegNumber", "num_diw": "Agreement_Number"},
    }
    mapping = FIELD_MAPPING.get(option, FIELD_MAPPING["نظام"])
    DISPLAY_FIELDS = [
        ("اسم التشريع", mapping["name_qis"], mapping["name_diw"]),
        ("رقم التشريع", mapping["num_qis"], mapping["num_diw"]),
        ("السنة", "Year", "Year"),
        ("يحل محل", "Replaced For", "Replaced_For"),
        ("تاريخ الجريدة", "Magazine_Date", "Magazine_Date"),
        ("تاريخ السريان", "ActiveDate", "Active_Date"),
        ("الحالة", "Status", "Status"),
    ]
    CONDITIONAL_FIELDS = [
        ("ألغي بواسطة", "Canceled By", "Canceled_By"),
        ("تاريخ الانتهاء", "EndDate", "EndDate"),
        ("تم استبداله بواسطة", "Replaced By", "Replaced_By"),
    ]
    status_q_int = parse_status(qistas_data.get('Status'))
    rows = []
    for label, q_key, d_key in DISPLAY_FIELDS:
        qv = qistas_data.get(q_key, '')
        dv = diwan_data.get(d_key, '')
        q_str = '—' if pd.isna(qv) or str(qv).strip() == '' else str(qv)
        d_str = '—' if pd.isna(dv) or str(dv).strip() == '' else str(dv)
        diff_class = 'cmp-diff' if q_str != '—' and d_str != '—' and q_str != d_str else ''
        rows.append((label, q_str, d_str, diff_class))
    if status_q_int == 2:
        for label, q_key, d_key in CONDITIONAL_FIELDS:
            qv = qistas_data.get(q_key, '')
            dv = diwan_data.get(d_key, '') if d_key else qistas_data.get(q_key, '')
            q_str = '—' if pd.isna(qv) or str(qv).strip() == '' else str(qv)
            d_str = '—' if pd.isna(dv) or str(dv).strip() == '' else str(dv)
            if q_str == '—' and d_str == '—':
                continue
            diff_class = 'cmp-diff' if q_str != '—' and d_str != '—' and q_str != d_str else ''
            rows.append((label, q_str, d_str, diff_class))
    if rows:
        html = ["<div class='cmp-wrapper'><table class='cmp-table'>"]
        html.append("<thead><tr><th>اسم الحقل</th><th>قسطاس</th><th>الديوان</th></tr></thead><tbody>")
        for label, qv, dv, cls in rows:
            html.append(f"<tr><td>{label}</td><td class='{cls}'>{qv}</td><td class='{cls}'>{dv}</td></tr>")
        html.append("</tbody></table></div>")
        st.markdown("\n".join(html), unsafe_allow_html=True)
    else:
        st.info("لا توجد بيانات للمقارنة في هذا السجل.")
    render_selection_buttons(qistas_data, diwan_data, current_index, total_records)
    render_navigation_buttons(current_index, total_records)

def render_selection_buttons(qistas_data: dict, diwan_data: dict, current_index: int, total_records: int):
    st.markdown("---")
    st.markdown("<h3 style='color: white !important; text-align: center; margin-top: 2rem;'>❓ أيهما أكثر دقة؟</h3>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
   
    with col1:
        if st.button("✅ قسطاس صحيح", use_container_width=True):
            save_comparison_record(qistas_data, 'قسطاس')
            st.success("تم حفظ النتيجة من قسطاس!")
            move_to_next_record(total_records, current_index)
   
    with col2:
        if st.button("✅ الديوان صحيح", use_container_width=True):
            save_comparison_record(diwan_data, 'الديوان')
            st.success("تم حفظ النتيجة من الديوان!")
            move_to_next_record(total_records, current_index)
   
    with col3:
        form_key = SessionManager.get_unique_key('show_custom_form')
        if st.button("⚠️ لا أحد منهم", use_container_width=True):
            st.session_state[form_key] = True
            st.rerun()

    # فتح النموذج مع بيانات كاملة
    if st.session_state.get(SessionManager.get_unique_key('show_custom_form'), False):
        # اختيار البيانات الأكثر اكتمالًا
        if len(qistas_data) >= len(diwan_data):
            base_data = qistas_data
        else:
            base_data = diwan_data
        
        # لو الاتنين فاضيين، نستخدم حقول افتراضية
        if not base_data:
            base_data = {
                "LegName": "", "ByLawName": "", "Law_Name": "", "Instruction_Name": "", "Agreement_Name": "",
                "LegNumber": "", "ByLawNumber": "", "Law_Number": "", "Instruction_Number": "", "Agreement_Number": "",
                "Year": "", "Replaced For": "", "Replaced_For": "", "Magazine_Date": "", "ActiveDate": "", "Active_Date": "",
                "Status": "", "Canceled By": "", "Canceled_By": "", "EndDate": "", "Replaced By": "", "Replaced_By": ""
            }
        
        render_custom_form(base_data, current_index, total_records)

def render_custom_form(reference_data: dict, current_index: int, total_records: int):
    st.markdown("---")
    st.markdown("<h3 style='color: white !important; text-align: center;'>✍️ عدّل البيانات الصحيحة (كل الحقول)</h3>", unsafe_allow_html=True)
    
    base_data = reference_data.copy()
    
    with st.form("custom_data_form_full"):
        custom_data = {}
        columns = list(base_data.keys())
        
        num_cols = 3
        for i in range(0, len(columns), num_cols):
            cols = st.columns(num_cols)
            for j, col in enumerate(cols):
                if i + j < len(columns):
                    field_name = columns[i + j]
                    default_value = base_data.get(field_name, "")
                    value_str = str(default_value) if default_value not in [None, "", pd.NaT] else ""
                    custom_data[field_name] = col.text_input(
                        field_name,
                        value=value_str,
                        key=f"custom_{field_name}_{current_index}"
                    )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("حفظ والانتقال للتالي", use_container_width=True, type="primary"):
                cleaned_data = {k: (v.strip() if v.strip() else "") for k, v in custom_data.items()}
                
                save_comparison_record(cleaned_data, 'مصدر آخر (معدل يدويًا)')
                st.success("تم حفظ البيانات المعدلة يدويًا بنجاح!")
                move_to_next_record(total_records, current_index)
        
        with col2:
            if st.form_submit_button("إلغاء", use_container_width=True):
                form_key = SessionManager.get_unique_key('show_custom_form')
                st.session_state[form_key] = False
                st.rerun()

def render_navigation_buttons(current_index: int, total_records: int):
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    idx_key = SessionManager.get_unique_key('current_index')
    form_key = SessionManager.get_unique_key('show_custom_form')
    next_key = SessionManager.get_unique_key('show_next_in_review')
    max_key = SessionManager.get_unique_key('max_reached_idx')
    with col1:
        if current_index > 0:
            if st.button("⏮️ السابق", use_container_width=True):
                new_idx = current_index - 1
                st.session_state[idx_key] = new_idx
                st.session_state[form_key] = False
                st.session_state[next_key] = True
                save_progress(new_idx, st.session_state[max_key])
                save_persistent_data()
                st.rerun()
   
    with col3:
        max_reached = st.session_state.get(max_key, 0)
        show_next = st.session_state.get(next_key, False)
        if current_index < total_records - 1 and show_next and current_index < max_reached:
            if st.button("⏭️ التالي", use_container_width=True, type="primary"):
                new_idx = current_index + 1
                st.session_state[idx_key] = new_idx
                if new_idx >= max_reached:
                    st.session_state[next_key] = False
                save_progress(new_idx, max_reached)
                save_persistent_data()
                st.rerun()

def render_comparison_tab(qistas_df: pd.DataFrame, diwan_df: pd.DataFrame):
    st.markdown("<div class='comparison-card'>", unsafe_allow_html=True)
    form_key = SessionManager.get_unique_key('show_custom_form')
    next_key = SessionManager.get_unique_key('show_next_in_review')
    if st.session_state.get(form_key, False):
        st.session_state[next_key] = False
    total_records = min(len(qistas_df), len(diwan_df))
    idx_key = SessionManager.get_unique_key('current_index')
    current_index = st.session_state[idx_key]
    progress_percentage = int(((current_index + 1) / total_records) * 100) if total_records > 0 else 0
    st.markdown(f"<div class='wizard-container'><h3 style='color: #667eea; text-align: center;'>مقارنة التشريعات</h3><p style='text-align: center;'>{current_index + 1} من {total_records} ({progress_percentage}%)</p></div>", unsafe_allow_html=True)
    if total_records > 0:
        render_wizard_steps(current_index, total_records)
    st.markdown(f"<div style='background: #e2e8f0; height: 15px; border-radius: 10px; overflow: hidden; margin: 1.5rem 0 2rem 0;'><div style='height: 100%; background: linear-gradient(90deg, #667eea 0%, #48bb78 100%); width: {progress_percentage}%;'></div></div>", unsafe_allow_html=True)
    if current_index < total_records:
        render_law_comparison(qistas_df, diwan_df, current_index, total_records)
    else:
        st.success("تم الانتهاء من مراجعة جميع السجلات!")
        if st.button("البدء من جديد"):
            st.session_state[idx_key] = 0
            st.session_state[SessionManager.get_unique_key('show_custom_form')] = False
            save_progress(0, 0)
            save_persistent_data()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def render_missing_malq_tab():
    MALQ_PATHS = {
        'نظام': r'extData/Bylaws/Qis_ByLaws_Missing.xlsx',
        'قانون': r'extData/Laws/Qis_Laws_Missing.xlsx',
        'تعليمات': r'extData/Instructions/Qis_Instructions_Missing.xlsx',
        'اتفاقيات': r'extData/Agreements/Qis_Agreements_Missing.xlsx',
    }
    MALQ_PATH = MALQ_PATHS.get(option)
    if not MALQ_PATH or not os.path.exists(MALQ_PATH):
        st.error(f"ملف القيم المفقودة غير موجود للنوع: **{option}**")
        st.stop()
    if st.session_state.get('malq_current_kind') != option or 'malq_records' not in st.session_state:
        for k in list(st.session_state.keys()):
            if k.startswith('malq_') and k not in ['malq_current_kind']:
                del st.session_state[k]
        df = pd.read_excel(MALQ_PATH).fillna("")
        st.session_state.malq_records = df.to_dict("records")
        st.session_state.malq_current_kind = option
        st.session_state.malq_idx = 0
        st.session_state.malq_saved_records = {}
        st.session_state.malq_max_reached_idx = 0
        st.session_state.show_next_in_review = False
    malq_saved_key = SessionManager.get_unique_key("malq_completed")
    st.session_state[malq_saved_key] = load_missing_from_gsheet()
    records = st.session_state.malq_records
    total = len(records)
    i = st.session_state.malq_idx = max(0, min(st.session_state.malq_idx, total - 1))
    current_record = records[i]
    st.progress((i + 1) / total, text=f"السجل {i + 1} من {total}")
    arabic_labels = {
        "LegName": "اسم التشريع", "DetailedName": "الاسم التفصيلي", "LegNumber": "رقم التشريع",
        "Year": "السنة", "Replaced For": "حل محل", "ActiveDate": "تاريخ السريان",
        "Status": "الحالة", "Canceled By": "ألغي بموجب", "EndDate": "تاريخ الانتهاء",
        "Replaced By": "استبدل بـ"
    }
    status_val = str(current_record.get("Status", "")).strip()
    is_active = status_val in ["ساري", "1", "سارية المفعول", "سارية"]
    display_data = []
    legname_val = current_record.get("LegName")
    if pd.isna(legname_val) or str(legname_val).strip() in ["", "nan"]:
        legname_val = current_record.get("DetailedName", "")
        label_name = arabic_labels["DetailedName"]
    else:
        legname_val = str(legname_val).strip()
        label_name = arabic_labels["LegName"]
    if legname_val:
        display_data.append({"الحقل": f"<strong>{label_name}</strong>", "القيمة": legname_val})
    for key in ["LegNumber", "Year", "Replaced For", "ActiveDate", "Status"]:
        val = current_record.get(key, "")
        clean_val = str(val).strip() if pd.notna(val) else ""
        if key == "Year" and "." in clean_val:
            clean_val = clean_val.split(".")[0]
        if clean_val or key in ["LegNumber", "Year"]:
            display_data.append({"الحقل": f"<strong>{arabic_labels.get(key, key)}</strong>", "القيمة": clean_val})
    if not is_active:
        for key in ["EndDate", "Canceled By", "Replaced By", "Replaced For"]:
            val = current_record.get(key, "")
            if pd.notna(val) and str(val).strip():
                display_data.append({
                    "الحقل": f"<strong style='color:#dc2626;'>{arabic_labels.get(key, key)}</strong>",
                    "القيمة": f"<strong>{str(val).strip()}</strong>"
                })
    st.markdown("""
        <style>
            .compact-malq-container {max-height: 380px; overflow-y: auto; border-radius: 14px; border: 1px solid #c7d2fe;}
            .compact-malq-table {width: 100%; border-collapse: separate; border-spacing: 0; font-size: 14.2px;}
            .compact-malq-table thead th {background: #4f46e5 !important; color: white; padding: 14px; font-weight: 600;}
            .compact-malq-table td {padding: 11px 15px; background: white; border-bottom: 1px solid #e2e8f0;}
            .compact-malq-table td:first-child {font-weight: 700; color: #1e293b; width: 40%; background: #f8fafc;}
        </style>
    """, unsafe_allow_html=True)
    df_display = pd.DataFrame(display_data)
    st.markdown(f"<div class='compact-malq-container'>{df_display.to_html(classes='compact-malq-table', index=False, escape=False)}</div>", unsafe_allow_html=True)
    st.markdown("### هل هذا التشريع صحيح كما هو؟")
    choice = st.radio("", ["نعم، صحيح تمامًا", "لا، يحتاج تعديل"], index=None, label_visibility="collapsed")
    if choice == "نعم، صحيح تمامًا":
        st.session_state.malq_source_choice = True
        st.session_state.malq_manual_entry = False
    elif choice == "لا، يحتاج تعديل":
        st.session_state.malq_manual_entry = True
        st.session_state.malq_source_choice = False
    if st.session_state.get("malq_source_choice"):
        st.markdown("### أكمل القيم الفارغة")
        with st.form(key=f"fill_{i}"):
            required = [f for f in arabic_labels.keys() if str(current_record.get(f, "")).strip() == "" and not (f in ["EndDate", "Canceled By", "Replaced By"] and is_active)]
            for key in required:
                st.text_input(arabic_labels[key], value=current_record.get(key, ""), key=f"f_{key}_{i}")
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("حفظ والانتقال", use_container_width=True, type="primary"):
                    save_data = {key: st.session_state[f"f_{key}_{i}"].strip() for key in required}
                    if all(save_data.values()):
                        for k, v in save_data.items():
                            st.session_state.malq_records[i][k] = v
                        completed_record = {
                            'تاريخ التعديل': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            **st.session_state.malq_records[i]
                        }
                        existing_idx = next((idx for idx, rec in enumerate(st.session_state[malq_saved_key]) if rec.get('LegNumber') == completed_record.get('LegNumber') and rec.get('Year') == completed_record.get('Year')), None)
                        if existing_idx is not None:
                            st.session_state[malq_saved_key][existing_idx] = completed_record
                        else:
                            st.session_state[malq_saved_key].append(completed_record)
                        save_missing_to_gsheet(st.session_state[malq_saved_key])
                        st.session_state.malq_max_reached_idx = max(st.session_state.malq_max_reached_idx, i + 1)
                        st.success("تم الحفظ!")
                        if i + 1 < total:
                            st.session_state.malq_idx = i + 1
                            st.rerun()
                        else:
                            st.balloons()
                            st.success("انتهيت من جميع السجلات!")
            with c2:
                st.form_submit_button("إلغاء", use_container_width=True, on_click=lambda: st.rerun())
    if st.session_state.get("malq_manual_entry"):
        st.markdown("### عدّل جميع الحقول")
        with st.form(key=f"manual_{i}"):
            important = ["LegName", "DetailedName", "LegNumber", "Year", "ActiveDate", "Status"]
            for key in ["LegName", "DetailedName", "LegNumber", "Year", "Replaced For", "ActiveDate", "Status", "Canceled By", "EndDate", "Replaced By"]:
                val = str(current_record.get(key, "") or "").strip()
                if key == "Year" and val.endswith(".0"):
                    val = val[:-2]
                st.text_input(arabic_labels.get(key, key), value=val, key=f"m_{key}_{i}")
            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("حفظ والانتقال", use_container_width=True, type="primary"):
                    save_data = {k: st.session_state[f"m_{k}_{i}"].strip() for k in ["LegName", "DetailedName", "LegNumber", "Year", "Replaced For", "ActiveDate", "Status", "Canceled By", "EndDate", "Replaced By"]}
                    if all(save_data.get(f, "").strip() for f in important):
                        for k, v in save_data.items():
                            st.session_state.malq_records[i][k] = v
                        completed_record = {
                            'تاريخ التعديل': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            **st.session_state.malq_records[i]
                        }
                        existing_idx = next((idx for idx, rec in enumerate(st.session_state[malq_saved_key]) if rec.get('LegNumber') == completed_record.get('LegNumber') and rec.get('Year') == completed_record.get('Year')), None)
                        if existing_idx is not None:
                            st.session_state[malq_saved_key][existing_idx] = completed_record
                        else:
                            st.session_state[malq_saved_key].append(completed_record)
                        save_missing_to_gsheet(st.session_state[malq_saved_key])
                        st.session_state.malq_max_reached_idx = max(st.session_state.malq_max_reached_idx, i + 1)
                        st.success("تم الحفظ!")
                        if i + 1 < total:
                            st.session_state.malq_idx = i + 1
                            st.rerun()
                        else:
                            st.balloons()
                            st.success("انتهيت!")
            with c2:
                st.form_submit_button("إلغاء", use_container_width=True, on_click=lambda: st.rerun())
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        if i > 0:
            st.button("السابق", on_click=lambda: st.session_state.update(malq_idx=i-1, show_next_in_review=True), use_container_width=True, type="secondary")
    with col3:
        if i < total - 1 and st.session_state.get("show_next_in_review", False) and i < st.session_state.malq_max_reached_idx:
            st.button("التالي", on_click=lambda: st.session_state.update(malq_idx=i+1), use_container_width=True, type="primary")

def render_saved_data_tab():
    st.markdown("<div class='comparison-card'>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='color: #667eea !important; text-align: center;'>البيانات المحفوظة - {option} ({user_name})</h2>", unsafe_allow_html=True)
    data = load_from_gsheet(WORKSHEET_NAMES[option])
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        st.download_button("تحميل نتائج المقارنة", buffer, f"{option}_مقارنة_{user_name}.xlsx", use_container_width=True)
    else:
        st.info("لا توجد نتائج محفوظة بعد")
    missing = load_missing_from_gsheet()
    if missing:
        df_miss = pd.DataFrame(missing)
        st.dataframe(df_miss, use_container_width=True, hide_index=True)
        buffer_miss = io.BytesIO()
        df_miss.to_excel(buffer_miss, index=False, engine='openpyxl')
        buffer_miss.seek(0)
        st.download_button("تحميل القيم المفقودة المصححة", buffer_miss, f"{option}_مفقودة_{user_name}.xlsx", use_container_width=True)
    else:
        st.info("لا توجد قيم مفقودة مصححة بعد")
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== main ====================
def main():
    apply_styles()
    st.markdown("""
        <div class="title-container">
            <h1 style='color: #667eea; margin: 0;'>⚖️ نظام التحقق من التشريعات القانونية</h1>
            <p style='color: #718096; margin-top: 0.5rem; font-size: 18px;'>
                مقارنة شاملة بين قسطاس والديوان - حفظ دائم للنتائج والتقدم
            </p>
        </div>
    """, unsafe_allow_html=True)
    initialize_session_state()
    qis_df, diw_df = load_csv_data(option)
    tab1, tab2, tab3 = st.tabs(["🔍 مقارنة تفصيلية", "📁 البيانات المحفوظة", "⚠️ قيم مفقودة"])
    with tab1:
        render_comparison_tab(qis_df, diw_df)
    with tab2:
        render_saved_data_tab()
    with tab3:
        render_missing_malq_tab()

if __name__ == "__main__":
    main()
