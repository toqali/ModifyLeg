"""
نظام مقارنة التشريعات القانونية
مقارنة شاملة بين بيانات قسطاس والديوان التشريعي
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os
import json

# ==================== إعدادات الصفحة ====================
st.set_page_config(
    page_title="نظام مقارنة التشريعات القانونية",
    page_icon="Scale",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("نوع التشريع")
option = st.sidebar.radio(
    "اختر نوع البيانات:",
    ["نظام", "قانون", "تعليمات", "اتفاقيات"],
)

# ==================== الثوابت ====================
QisShownCols = ['LegName', 'LegNumber', 'Year','Replaced For', 'Canceled By','ActiveDate', 'EndDate', 'Replaced By', 'Status','Magazine_Date']
DiwShownCols = ['ByLawName', 'ByLawNumber', 'Year', 'Replaced_For', 'Magazine_Date', 'Active_Date', 'Status']


# ==================== ملفات منفصلة لكل نوع تشريع (جديد تمامًا) ====================
DATA_FILES = {
    'نظام': 'Bylaw_Comparison.json',
    'قانون': 'Law_Comparison.json',
    'تعليمات': 'Instruction_Comparison.json',
    'اتفاقيات': 'Agreement_Comparison.json',
}

PROGRESS_FILES = {
    'نظام': 'Bylaw_Progress.json',
    'قانون': 'Law_Progress.json',
    'تعليمات': 'Instruction_Progress.json',
    'اتفاقيات': 'Agreement_Progress.json',
}


# ملفات القيم المفقودة (تبقى كما هي منفصلة أصلاً)
COMPARISON_OUTPUTS = {
    'نظام': 'Bylaws_Comparison_Saved.xlsx',
    'قانون': 'Laws_Comparison_Saved.xlsx',
    'تعليمات': 'Instructions_Comparison_Saved.xlsx',
    'اتفاقيات': 'Agreements_Comparison_Saved.xlsx',
}
MISSING_OUTPUTS = {
    'نظام': 'Bylaws_Missing_Data.xlsx',
    'قانون': 'Laws_Missing_Data.xlsx',
    'تعليمات': 'Instructions_Missing_Data.xlsx',
    'اتفاقيات': 'Agreements_Missing_Data.xlsx',
}

COMPARISON_FILE = COMPARISON_OUTPUTS[option]
MISSING_FILE = MISSING_OUTPUTS[option]
DATA_FILE = DATA_FILES[option]
PROGRESS_FILE = PROGRESS_FILES[option]

@st.cache_data
def load_csv_data(kind: str):
    """تحميل ملفات Excel من مسارات ثابتة ومحددة بدقة"""
    
    PATHS = {
        'نظام': {
            'qis': r'extData/Bylaws/Qis_ByLaws_V2.xlsx',
            'diwan': r'extData/Bylaws/Diwan_ByLaws_V2.xlsx'
        },
        'قانون': {
            'qis': r'extData/Laws/Qis_Laws_V2.xlsx',
            'diwan': r'extData/Laws/Diwan_Laws_V2.xlsx'
        },
        'تعليمات': {
            'qis': r'extData/Instructions/Qis_Instructions.xlsx',
            'diwan': r'extData/Instructions/Diwan_Instructions.xlsx'
        },
        'اتفاقيات': { 
            'qis': r'extData/Agreements/Qis_Agreements.xlsx',
            'diwan': r'extData/Agreements/Diwan_Agreements.xlsx'
        }
    }

    if kind not in PATHS:
        st.error(f"النوع '{kind}' غير مدعوم بعد.")
        return None, None

    qis_path = PATHS[kind]['qis']
    diwan_path = PATHS[kind]['diwan']

    def read_excel_safely(path, source_name):
        if not os.path.exists(path):
            st.error(f"غير موجود ← {path}")
            return None
        try:
            df = pd.read_excel(path)
            st.sidebar.success(f"{source_name} ({os.path.basename(path)})")
            return df
        except Exception as e:
            st.error(f"فشل تحميل {source_name}:\n{path}\n\n{str(e)}")
            return None

    qis_df = read_excel_safely(qis_path, "قسطاس")
    diwan_df = read_excel_safely(diwan_path, "الديوان")

    if qis_df is None or diwan_df is None:
        st.stop()

    return qis_df, diwan_df

# ==================== باقي الكود كما هو تمامًا (لم يتم حذفه أو تغييره) ====================

def save_to_file(filename: str, data) -> None:
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"خطأ في حفظ البيانات: {str(e)}")

def load_from_file(filename: str):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {str(e)}")
    return None

class SessionManager:
    @staticmethod
    def get_current_files():
        return DATA_FILES[option], PROGRESS_FILES[option]
    
    @staticmethod
    def get_unique_key(base_key: str) -> str:
        """إنشاء مفتاح فريد لكل نوع تشريع"""
        return f"{base_key}_{option.replace(' ', '_')}"

    @staticmethod
    def initialize():
        data_file, progress_file = SessionManager.get_current_files()
        
        # 🔥 مفاتيح منفصلة لكل نوع تشريع
        comp_key = SessionManager.get_unique_key('comparison_data')
        idx_key = SessionManager.get_unique_key('current_index')
        form_key = SessionManager.get_unique_key('show_custom_form')
        del_key = SessionManager.get_unique_key('confirm_delete')
        
        # 🔥 إضافة متغيرات جديدة للتحكم بزر "التالي"
        next_key = SessionManager.get_unique_key('show_next_in_review')
        max_key = SessionManager.get_unique_key('max_reached_idx')
        
        # تحميل البيانات المحفوظة
        if comp_key not in st.session_state:
            saved = load_from_file(data_file)
            st.session_state[comp_key] = saved if saved is not None else []

        # تحميل التقدم
        if idx_key not in st.session_state:
            saved_progress = load_from_file(progress_file)
            if saved_progress and isinstance(saved_progress, dict):
                # 🔥 التنسيق الجديد (dictionary)
                st.session_state[idx_key] = saved_progress.get('current_index', 0)
                st.session_state[max_key] = saved_progress.get('max_reached_idx', 0)
            elif saved_progress is not None:
                # 🔥 التنسيق القديم (رقم فقط) - للتوافق
                st.session_state[idx_key] = saved_progress
                st.session_state[max_key] = saved_progress
            else:
                st.session_state[idx_key] = 0
                st.session_state[max_key] = 0

                if form_key not in st.session_state:
                    st.session_state[form_key] = False
                if del_key not in st.session_state:
                    st.session_state[del_key] = False
                
                # 🔥 الجديد: متغيرات التحكم بالتنقل
                if next_key not in st.session_state:
                    st.session_state[next_key] = False
                if max_key not in st.session_state:
                    st.session_state[max_key] = 0

    @staticmethod
    def save_persistent():
        data_file, progress_file = SessionManager.get_current_files()
        try:
            comp_key = SessionManager.get_unique_key('comparison_data')
            idx_key = SessionManager.get_unique_key('current_index')
            max_key = SessionManager.get_unique_key('max_reached_idx')
            
            # 🔥 حفظ التقدم الكامل
            progress_data = {
                'current_index': st.session_state[idx_key],
                'max_reached_idx': st.session_state.get(max_key, 0)
            }
            
            save_to_file(data_file, st.session_state[comp_key])
            save_to_file(progress_file, progress_data)
        except Exception as e:
            st.error(f"فشل الحفظ التلقائي: {e}")

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
    except Exception:
        return None

def initialize_session_state():
    SessionManager.initialize()

def save_persistent_data():
    SessionManager.save_persistent()

def get_legislation_data(index: int, source_df: pd.DataFrame) -> dict:
    if index >= len(source_df):
        return {}
    row = source_df.iloc[index]
    return {k: ('' if pd.isna(v) else v) for k, v in row.to_dict().items()}

def save_comparison_record(data: dict, source: str) -> None:
    comp_key = SessionManager.get_unique_key('comparison_data')
    new_record = {
        'تاريخ الإدخال': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'المصدر الصحيح': source,
        **data
    }
    st.session_state[comp_key].append(new_record)
    save_persistent_data()

def move_to_next_record(total_records: int, current_index: int) -> None:
    idx_key = SessionManager.get_unique_key('current_index')
    max_key = SessionManager.get_unique_key('max_reached_idx')
    next_key = SessionManager.get_unique_key('show_next_in_review')
    
    if current_index + 1 < total_records:
        st.session_state[idx_key] += 1
        
        # 🔥 تحديث أقصى صفحة وصلنا لها
        st.session_state[max_key] = max(st.session_state.get(max_key, 0), current_index + 1)
        
        # 🔥 إخفاء زر "التالي" لأننا نتقدم للأمام
        st.session_state[next_key] = False
        
        save_persistent_data()
        st.rerun()
    else:
        st.balloons()
        st.success(f"تم الانتهاء من جميع السجلات!")

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
        [data-testid="stSidebar"][aria-expanded="false"] * {
        display: none !important;
        }

        .title-container {background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); text-align: center; margin-bottom: 2rem;}
        .comparison-card {background: rgba(255, 255, 255, 0.95); padding: 1.5rem; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin: 1rem 0;}
        .comparison-card * {color: #2d3748 !important;}
        .comparison-card h3, .comparison-card h4 {color: #667eea !important;}
        .stButton>button {width: 100%; background: white !important; color: #667eea !important; border: 3px solid #667eea !important; padding: 1rem; border-radius: 10px; font-weight: 700; font-size: 1.2em; box-shadow: 0 4px 15px rgba(0,0,0,0.2);}
        .stButton>button:hover {transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.3); background: #667eea !important; color: white !important;}
        .stTabs [data-baseweb="tab-list"] {background: rgba(255, 255, 255, 0.15); border-radius: 10px; padding: 0.5rem;}
        .stTabs [data-baseweb="tab"] {color: white !important; font-size: 1.1em !important; font-weight: 600 !important;}
        .stTabs [aria-selected="true"] {background: rgba(255, 255, 255, 0.3) !important; border-radius: 8px;}
        p, span, label {font-size: 1.1em;}
        .dataframe {direction: rtl !important; text-align: right !important;}
        .dataframe td, .dataframe th {text-align: right !important; padding: 20px 15px !important; font-size: 1.05em !important; border: 2px solid #cbd5e0 !important; white-space: normal !important; word-wrap: break-word !important; min-width: 150px !important; line-height: 1.6 !important; vertical-align: middle !important;}
        .dataframe thead th {background: #667eea !important; color: white !important; font-weight: bold !important;}
        .dataframe tbody tr:nth-child(even) {background-color: #f7fafc !important;}
        .stTextInput label, .stSelectbox label, .stDateInput label {color: #2d3748 !important; font-weight: 600 !important; text-align: right !important;}
        .stTextInput input, .stSelectbox select {background: white !important; color: #2d3748 !important; font-size: 1.1em !important; text-align: right !important; direction: rtl !important;}
        .wizard-container {background: white; padding: 2rem; border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 5px 20px rgba(0,0,0,0.15);}

        /* ==================== الكروت الأصلية (قسطاس والديوان) ==================== */
        .source-card {background: #ffffff; border-radius: 14px; padding: 18px; box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15); direction: rtl; text-align: right; border: 2.5px solid; position: relative; overflow: hidden;}
        .source-card:hover {box-shadow: 0 24px 64px rgba(0, 0, 0, 0.2); transform: translateY(-6px);}
        .qistas-card {background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%); border-color: #3B82F6;}
        .qistas-card h4 {color: #1E40AF !important;}
        .qistas-card::before {content: ''; position: absolute; top: 0; right: 0; width: 5px; height: 100%; background: linear-gradient(180deg, #3B82F6, #1E40AF); border-radius: 14px 0 0 14px;}
        .diwan-card {background: linear-gradient(135deg, #FEF3F2 0%, #FED7AA 100%); border-color: #F97316;}
        .diwan-card h4 {color: #B45309 !important;}
        .diwan-card::before {content: ''; position: absolute; top: 0; right: 0; width: 5px; height: 100%; background: linear-gradient(180deg, #F97316, #B45309); border-radius: 14px 0 0 14px;}
        .info-card {background: #f3f4f6; border-radius: 8px; padding: 10px 12px; border: 1.5px solid #d1d5db; margin-bottom: 8px;}
        .info-card .field-name {font-weight: 700; color: #374151; font-size: 0.92em; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.4px;}
        .qistas-card .info-card .field-name {color: #1E40AF;}
        .diwan-card .info-card .field-name {color: #B45309;}
        .info-card .field-value {color: #1f2937; font-size: 0.96em; word-wrap: break-word; white-space: normal; line-height: 1.6; font-weight: 500;}

        /* ==================== جدول المقارنة - خلفية بيضاء 100% ومظهر أنيق جدًا ==================== */
        .cmp-wrapper {
            max-height: 300px;
            overflow: auto;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.12);
            border: 1px solid #e2e8f0;
            background: white !important;
            margin: 1.5rem 0;
        }
        .cmp-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            direction: rtl;
            font-size: 0.94rem;
            table-layout: fixed;
            background: white !important;
        }
        .cmp-table thead {
            position: sticky;
            top: 0;
            z-index: 10;
        }
        .cmp-table thead tr {
            background: #1e40af !important;  /* أزرق غامق أنيق جدًا */
        }
        .cmp-table thead th {
            color: white !important;
            padding: 16px 12px;
            text-align: center;
            font-weight: 700;
            font-size: 1.05em;
            border-bottom: 4px solid #60a5fa;
        }
        .cmp-table tbody td {
            padding: 14px 12px;
            vertical-align: middle;
            text-align: center;
            background: white !important;
            border-bottom: 1px solid #e2e8f0;
            transition: background 0.2s ease;
        }
        .cmp-table tbody td:first-child {
            text-align: right !important;
            font-weight: 700;
            color: #1f2937;
            background: #f8fafc !important;
            font-size: 0.98em;
        }
        .cmp-table tbody tr:nth-child(even) td {
            background: #ffffff !important;
        }
        .cmp-table tbody tr:nth-child(odd) td {
            background: #f8fafc !important;
        }
        .cmp-table tbody tr:hover td {
            background: #dbeafe !important;  /* أزرق فاتح جدًا عند الـ hover */
        }
        .cmp-diff {
            background: #fee2e2 !important;
            font-weight: 600;
            color: #991b1b;
        }
        .empty {
            color: #94a3b8;
            font-style: italic;
        }
        </style>
    """, unsafe_allow_html=True)


# ==========================================================
# ملف التقدم
# ==========================================================
MALQ_PROGRESS_FILE = 'malq_progress_data.json'

# ==========================================================
# دوال حفظ واستعادة التقدم
# ==========================================================

def save_malq_to_file(filename: str, data) -> None:
    """حفظ بيانات في ملف JSON"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_malq_from_file(filename: str):
    """تحميل بيانات من ملف JSON"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return None

def save_malq_progress(idx, saved_records=None, max_reached=None):
    """حفظ التقدم في ملف JSON دائم"""
    progress_data = {
        'malq_idx': idx,
        'saved_records': saved_records or {},
        'max_reached_idx': max_reached  # 🔥 آخر صفحة وصلنا لها
    }
    save_malq_to_file(MALQ_PROGRESS_FILE, progress_data)

def load_malq_progress():
    """استعادة التقدم من ملف JSON"""
    return load_malq_from_file(MALQ_PROGRESS_FILE)

MALQ_OUTPUT_FILE = 'missing_data.xlsx'

def save_missing_data_to_excel(all_records):
    """حفظ جميع السجلات المكتملة من القيم المفقودة في Excel"""
    try:
        df = pd.DataFrame(all_records)
        df.to_excel(MALQ_OUTPUT_FILE, index=False, engine='openpyxl')
        return True
    except Exception as e:
        st.error(f"خطأ في حفظ الملف: {str(e)}")
        return False

def update_missing_record(record_idx, updated_fields):
    """تحديث سجل من القيم المفقودة وحفظ في Excel"""
    # تحديث السجل في session_state
    for field, value in updated_fields.items():
        st.session_state.malq_records[record_idx][field] = value
    
    # حفظ جميع السجلات في Excel
    return save_missing_data_to_excel(st.session_state.malq_records)

# ==========================================================
# دوال التنقل (محسّنة)
# ==========================================================

def go_prev(current_idx):
    """ينقل إلى السجل السابق مع حفظ التقدم"""
    st.session_state.malq_idx = current_idx - 1
    # 🔥 عند الرجوع للخلف: نسمح بزر "التالي" (وضع المراجعة)
    st.session_state.show_next_in_review = True
    st.session_state.malq_source_choice = False
    st.session_state.malq_manual_entry = False
    
    # حفظ التقدم في ملف JSON
    save_malq_progress(
        current_idx - 1, 
        st.session_state.get('malq_saved_records', {}),
        st.session_state.get('malq_max_reached_idx', 0)
    )
    
def go_next(current_idx):
    """ينقل إلى السجل التالي (للمراجعة فقط)"""
    new_idx = current_idx + 1
    st.session_state.malq_idx = new_idx
    
    # 🔥 إذا وصلنا لآخر صفحة كنا فيها: نخفي زر "التالي"
    max_reached = st.session_state.get('malq_max_reached_idx', 0)
    if new_idx >= max_reached:
        st.session_state.show_next_in_review = False
    
    # حفظ التقدم
    save_malq_progress(
        new_idx, 
        st.session_state.get('malq_saved_records', {}),
        max_reached
    )

# ==========================================================
# الدالة الرئيسية
# ==========================================================

def render_missing_malq_tab():
    # مسارات ملفات القيم المفقودة حسب نوع التشريع
    MALQ_PATHS = {
        'نظام': r'extData/Bylaws/Qis_ByLaws_Missing.xlsx',
        'قانون': r'extData/Laws/Qis_Laws_Missing.xlsx',
        'تعليمات': r'extData/Instructions/Qis_Instructions_Missing.xlsx',
        'اتفاقيات': r'extData/Agreements/Qis_Agreements_Missing.xlsx',
    }

    MALQ_PATH = MALQ_PATHS.get(option)
    if not MALQ_PATH or not os.path.exists(MALQ_PATH):
        st.error(f"ملف القيم المفقودة غير موجود للنوع: **{option}**")
        st.info(f"المسار المتوقع:\n`{MALQ_PATH}`\n\nتأكد من وجود الملف في المجلد الصحيح.")
        st.stop()

    # ملفات منفصلة لكل نوع تشريع
    PROGRESS_FILE = f'malq_progress_{option.replace(" ", "_")}.json'
    OUTPUT_FILE = MISSING_FILE

    # المفتاح السحري: إذا تغير نوع التشريع → نعيد تحميل كل شيء
    if (st.session_state.get('malq_current_kind') != option 
        or st.session_state.get('malq_last_path') != MALQ_PATH
        or 'malq_records' not in st.session_state):

        # مسح البيانات القديمة الخاصة بنوع آخر
        keys_to_remove = [k for k in st.session_state.keys() if k.startswith('malq_') and k not in ['malq_current_kind', 'malq_last_path']]
        for k in keys_to_remove:
            del st.session_state[k]

        # تحميل البيانات الجديدة
        try:
            df = pd.read_excel(MALQ_PATH).fillna("")
            st.session_state.malq_records = df.to_dict("records")
            st.success(f"تم تحميل بيانات **{option}** بنجاح: {len(st.session_state.malq_records)} سجل")
        except Exception as e:
            st.error(f"فشل تحميل الملف: {e}")
            st.stop()

        # تحديث الحالة
        st.session_state.malq_current_kind = option
        st.session_state.malq_last_path = MALQ_PATH

        # تحميل التقدم المحفوظ لهذا النوع فقط
        saved = load_malq_from_file(PROGRESS_FILE)
        if saved:
            st.session_state.malq_idx = saved.get('malq_idx', 0)
            st.session_state.malq_saved_records = saved.get('saved_records', {})
            st.session_state.malq_max_reached_idx = saved.get('max_reached_idx', 0)
            st.info(f"تم استرجاع تقدمك السابق: السجل {st.session_state.malq_idx + 1}")
        else:
            st.session_state.malq_idx = 0
            st.session_state.malq_saved_records = {}
            st.session_state.malq_max_reached_idx = 0

        st.session_state.show_next_in_review = False

    # البيانات الحالية
    # البيانات الحالية
    records = st.session_state.malq_records
    total = len(records)
    i = st.session_state.malq_idx = max(0, min(st.session_state.malq_idx, total - 1))
    current_record = records[i]

    # 🔥 مفتاح لحفظ السجلات المعدّلة فقط (مثل المقارنة التفصيلية)
    malq_saved_key = f'malq_completed_records_{option.replace(" ", "_")}'
    if malq_saved_key not in st.session_state:
        # محاولة تحميل من ملف Excel إذا موجود
        if os.path.exists(MISSING_FILE):
            try:
                df_existing = pd.read_excel(MISSING_FILE)
                st.session_state[malq_saved_key] = df_existing.to_dict('records')
            except:
                st.session_state[malq_saved_key] = []
        else:
            st.session_state[malq_saved_key] = []

    # دوال حفظ محلية
    def save_progress():
        data = {
            'malq_idx': i,
            'saved_records': st.session_state.malq_saved_records,
            'max_reached_idx': st.session_state.malq_max_reached_idx
        }
        save_malq_to_file(PROGRESS_FILE, data)

    def save_to_excel():
        """حفظ السجلات المكتملة فقط (مثل المقارنة التفصيلية)"""
        if st.session_state[malq_saved_key]:
            df_out = pd.DataFrame(st.session_state[malq_saved_key])
            df_out.to_excel(MISSING_FILE, index=False, engine='openpyxl')
        else:
            # لو مافي سجلات محفوظة، احذف الملف
            if os.path.exists(MISSING_FILE):
                os.remove(MISSING_FILE)

    # شريط التقدم
    st.progress((i + 1) / total, text=f"السجل {i + 1} من {total} • النوع: {option}")

    # التسميات
    arabic_labels = {
        "LegName": "اسم التشريع", "DetailedName": "الاسم التفصيلي", "LegNumber": "رقم التشريع",
        "Year": "السنة", "Replaced For": "حل محل", "ActiveDate": "تاريخ السريان",
        "Status": "الحالة", "Canceled By": "ألغي بموجب", "EndDate": "تاريخ الانتهاء",
        "Replaced By": "استبدل بـ"
    }

    status_val = str(current_record.get("Status", "")).strip()
    is_active = status_val in ["ساري", "1", "سارية المفعول", "سارية"]

    # بيانات العرض
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

    # التصميم
    st.markdown("""
        <style>
            .compact-malq-card {background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%); padding: 22px; border-radius: 18px; margin: 20px auto; max-width: 900px; box-shadow: 0 8px 30px rgba(79,70,229,0.18);}
            .compact-malq-table {width: 100%; border-collapse: separate; border-spacing: 0; font-size: 14.2px;}
            .compact-malq-table thead th {background: #4f46e5 !important; color: white; padding: 14px; font-weight: 600;}
            .compact-malq-table td {padding: 11px 15px; background: white; border-bottom: 1px solid #e2e8f0;}
            .compact-malq-table td:first-child {font-weight: 700; color: #1e293b; width: 40%; background: #f8fafc;}
            .compact-malq-container {max-height: 380px; overflow-y: auto; border-radius: 14px; border: 1px solid #c7d2fe;}
            .custom-error-box {background-color: #fee2e2; color: #991b1b; padding: 10px; border-radius: 8px; border: 1px solid #f87171; margin-bottom: 10px; font-weight: bold; text-align: right;}
            .custom-warning-box {background-color: #f97316; color: white !important; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-top: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}
        </style>
    """, unsafe_allow_html=True)

    df_display = pd.DataFrame(display_data)
    st.markdown(f"<div class='compact-malq-container'>{df_display.to_html(classes='compact-malq-table', index=False, escape=False)}</div></div>", unsafe_allow_html=True)

    # حالة الحفظ
    is_saved = st.session_state.malq_saved_records.get(str(i), False)

    if st.session_state.get("show_next_in_review", False):
        st.session_state.malq_source_choice = False
        st.session_state.malq_manual_entry = False

    st.markdown("### هل هذا التشريع صحيح كما هو؟")
    choice = st.radio("", ["نعم، صحيح تمامًا", "لا، يحتاج تعديل"], index=None, key=f"radio_{i}", label_visibility="collapsed")

    if choice == "نعم، صحيح تمامًا":
        st.session_state.malq_source_choice = True
        st.session_state.malq_manual_entry = False
    elif choice == "لا، يحتاج تعديل":
        st.session_state.malq_manual_entry = True
        st.session_state.malq_source_choice = False

    # 1. تعبئة المفقود فقط
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
                        # 🔥 تحديث السجل الحالي
                        for k, v in save_data.items():
                            st.session_state.malq_records[i][k] = v
                        
                        # 🔥 إضافة السجل المكتمل للقائمة المحفوظة
                        completed_record = {
                            'تاريخ التعديل': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            **st.session_state.malq_records[i]
                        }
                        
                        # تحقق إذا السجل موجود مسبقًا (تحديث)
                        existing_idx = None
                        for idx, rec in enumerate(st.session_state[malq_saved_key]):
                            # مقارنة بناءً على LegNumber و Year
                            if (rec.get('LegNumber') == completed_record.get('LegNumber') and 
                                rec.get('Year') == completed_record.get('Year')):
                                existing_idx = idx
                                break
                        
                        if existing_idx is not None:
                            # تحديث السجل الموجود
                            st.session_state[malq_saved_key][existing_idx] = completed_record
                        else:
                            # إضافة سجل جديد
                            st.session_state[malq_saved_key].append(completed_record)
                        
                        save_to_excel()
                        st.session_state.malq_saved_records[str(i)] = True
                        st.session_state.malq_max_reached_idx = max(st.session_state.malq_max_reached_idx, i + 1)
                        save_progress()
                        st.success("تم الحفظ!")
                        if i + 1 < total:
                            st.session_state.malq_idx = i + 1
                            st.session_state.show_next_in_review = False
                            st.rerun()
                        else:
                            st.balloons()
                            st.success("انتهيت من جميع السجلات!")
                    else:
                        st.error("يرجى تعبئة جميع الحقول المطلوبة")

            with c2:
                st.form_submit_button("إلغاء", use_container_width=True, on_click=lambda: st.rerun())

    # 2. تعديل يدوي كامل
    if st.session_state.get("malq_manual_entry"):
        st.markdown("### عدّل جميع الحقول")
        with st.form(key=f"manual_{i}"):
            important = ["LegName", "DetailedName", "LegNumber", "Year", "ActiveDate", "Status"]
            inputs = {}
            for key in ["LegName", "DetailedName", "LegNumber", "Year", "Replaced For", "ActiveDate", "Status", "Canceled By", "EndDate", "Replaced By"]:
                val = str(current_record.get(key, "") or "").strip()
                if key == "Year" and val.endswith(".0"):
                    val = val[:-2]
                inputs[key] = st.text_input(arabic_labels.get(key, key), value=val, key=f"m_{key}_{i}")

            c1, c2 = st.columns(2)
            with c1:
                if st.form_submit_button("حفظ والانتقال", use_container_width=True, type="primary"):
                    save_data = {k: st.session_state[f"m_{k}_{i}"].strip() for k in inputs}
                    if all(save_data.get(f, "").strip() for f in important if f in save_data):
                        # 🔥 تحديث السجل الحالي
                        for k, v in save_data.items():
                            st.session_state.malq_records[i][k] = v
                        
                        # 🔥 إضافة السجل المكتمل للقائمة المحفوظة
                        completed_record = {
                            'تاريخ التعديل': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            **st.session_state.malq_records[i]
                        }
                        
                        # تحقق إذا السجل موجود مسبقًا
                        existing_idx = None
                        for idx, rec in enumerate(st.session_state[malq_saved_key]):
                            if (rec.get('LegNumber') == completed_record.get('LegNumber') and 
                                rec.get('Year') == completed_record.get('Year')):
                                existing_idx = idx
                                break
                        
                        if existing_idx is not None:
                            st.session_state[malq_saved_key][existing_idx] = completed_record
                        else:
                            st.session_state[malq_saved_key].append(completed_record)
                        
                        save_to_excel()
                        st.session_state.malq_saved_records[str(i)] = True
                        st.session_state.malq_max_reached_idx = max(st.session_state.malq_max_reached_idx, i + 1)
                        save_progress()
                        st.success("تم الحفظ!")
                        if i + 1 < total:
                            st.session_state.malq_idx = i + 1
                            st.rerun()
                        else:
                            st.balloons()
                            st.success("انتهيت!")
                    else:
                        st.error("يرجى تعبئة الحقول المهمة")

            with c2:
                st.form_submit_button("إلغاء", use_container_width=True, on_click=lambda: st.rerun())

    # أزرار التنقل
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        if i > 0:
            st.button("السابق", on_click=go_prev, args=(i,), use_container_width=True, type="secondary")
    with col3:
        if (i < total - 1 and st.session_state.get("show_next_in_review", False) 
            and i < st.session_state.malq_max_reached_idx):
            st.button("التالي", on_click=go_next, args=(i,), use_container_width=True, type="primary")

    if (st.session_state.get("malq_source_choice") or st.session_state.get("malq_manual_entry")) and not is_saved:
        st.warning("يجب الحفظ قبل المتابعة")

    # تحميل الملف
    with st.expander("تحميل البيانات المحدثة"):
        if os.path.exists(MISSING_FILE):
            with open(MISSING_FILE, "rb") as f:
                st.download_button(
                    label=f"تحميل {MISSING_FILE}",
                    data=f,
                    file_name=MISSING_FILE,
                    mime="application/vnd.openpyxlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            st.success(f"تم حفظ {sum(st.session_state.malq_saved_records.values())} من {total} سجل")
        else:
            st.info("لم يتم حفظ أي تعديلات بعد")

def render_wizard_steps(current_index: int, total_records: int):
    """عرض خطوات الويزارد"""
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
                label_color = '#48bb78'
                label_text = 'مكتمل'
            elif actual_index == current_index:
                circle_color = '#f97316'
                icon = '▶'
                label_color = '#f97316'
                label_text = 'الحالي'
            else:
                circle_color = '#e2e8f0'
                icon = str(actual_index + 1)
                label_color = '#718096'
                label_text = 'قادم'
            
            animation_style = "animation: pulse 2s infinite;" if actual_index == current_index else ""
            
            st.markdown(f"""
                <div style="text-align: center; margin-bottom: 1rem;">
                    <div style="width: 60px; height: 60px; border-radius: 50%; background: {circle_color}; 
                                color: white; display: flex; align-items: center; justify-content: center; 
                                margin: 0 auto 0.5rem auto; font-weight: bold; font-size: 1.3em; 
                                box-shadow: 0 4px 10px rgba(0,0,0,0.2); {animation_style}">
                        {icon}
                    </div>
                    <div style="color: {label_color}; font-size: 0.9em; font-weight: 600;">
                        {label_text}
                    </div>
                </div>
            """, unsafe_allow_html=True)


# ==================== عرض المقارنة ====================
def render_law_comparison(qistas_df: pd.DataFrame, diwan_df: pd.DataFrame, current_index: int, total_records: int):
    """عرض مقارنة سجل محدد كجدول (اسم الحقل | قسطاس | الديوان) - يدعم جميع أنواع التشريعات تلقائيًا"""
    qistas_data = get_legislation_data(current_index, qistas_df)
    diwan_data = get_legislation_data(current_index, diwan_df)

    st.markdown("<h3 style='color: #667eea !important; text-align: center;'>المقارنة التفصيلية</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # === خريطة ذكية للأعمدة حسب نوع التشريع (الحل النهائي والأخير) ===
    FIELD_MAPPING = {
        "نظام": {
            "name_qis": "LegName",           "name_diw": "ByLawName",
            "num_qis":  "LegNumber",          "num_diw":  "ByLawNumber",
        },
        "قانون": {
            "name_qis": "LegName",           "name_diw": "Law_Name",
            "num_qis":  "LegNumber",         "num_diw":  "Law_Number",
        },
        "تعليمات": {
            "name_qis": "LegName",   "name_diw": "Instruction_Name",
            "num_qis":  "LegNumber", "num_diw":  "Instruction_Number",
        },
        "اتفاقيات": {
            "name_qis": "LegName",     "name_diw": "Agreement_Name",
            "num_qis":  "LegNumber",   "num_diw":  "Agreement_Number",
        }
    }

    # نأخذ الخريطة الصحيحة حسب النوع المختار (مع fallback آمن)
    mapping = FIELD_MAPPING.get(option, FIELD_MAPPING["نظام"])

    # الأعمدة الأساسية اللي تظهر دائمًا
    DISPLAY_FIELDS = [
        ("اسم التشريع",       mapping["name_qis"], mapping["name_diw"]),
        ("رقم التشريع",       mapping["num_qis"],  mapping["num_diw"]),
        ("السنة",              "Year",             "Year"),
        ("يحل محل",           "Replaced For",     "Replaced_For"),
        ("تاريخ الجريدة",     "Magazine_Date",    "Magazine_Date"),
        ("تاريخ السريان",     "ActiveDate",       "Active_Date"),
        ("الحالة",            "Status",           "Status"),
    ]

    # الحقول اللي تظهر فقط إذا كان Status = 2 (غير ساري)
    CONDITIONAL_FIELDS = [
        ("ألغي بواسطة",       "Canceled By",      "Canceled_By"),
        ("تاريخ الانتهاء",    "EndDate",          "EndDate"),
        ("تم استبداله بواسطة", "Replaced By",      "Replaced_By"),
    ]

    # تحليل حالة قسطاس لتحديد إظهار الحقول المشروطة
    status_q_int = parse_status(qistas_data.get('Status'))

    rows = []

    # === إضافة الحقول الأساسية ===
    for label, q_key, d_key in DISPLAY_FIELDS:
        qv = qistas_data.get(q_key, '')
        dv = diwan_data.get(d_key, '')

        q_str = '—' if pd.isna(qv) or str(qv).strip() == '' else str(qv)
        d_str = '—' if pd.isna(dv) or str(dv).strip() == '' else str(dv)

        diff_class = 'cmp-diff' if q_str != '—' and d_str != '—' and q_str != d_str else ''
        rows.append((label, q_str, d_str, diff_class))

    # === إضافة الحقول المشروطة فقط إذا كان "غير ساري" ===
    if status_q_int == 2:
        for label, q_key, d_key in CONDITIONAL_FIELDS:
            qv = qistas_data.get(q_key, '')
            dv = diwan_data.get(d_key, '') if d_key else qistas_data.get(q_key, '')

            q_str = '—' if pd.isna(qv) or str(qv).strip() == '' else str(qv)
            d_str = '—' if pd.isna(dv) or str(dv).strip() == '' else str(dv)

            # لا نعرض السطر إذا كلاهما فارغان
            if q_str == '—' and d_str == '—':
                continue

            diff_class = 'cmp-diff' if q_str != '—' and d_str != '—' and q_str != d_str else ''
            rows.append((label, q_str, d_str, diff_class))

    # === رسم الجدول النهائي ===
    if rows:
        html = ["<div class='cmp-wrapper'><table class='cmp-table'>"]
        html.append("<thead><tr><th>اسم الحقل</th><th>قسطاس</th><th>الديوان</th></tr></thead><tbody>")
        for label, qv, dv, cls in rows:
            q_td = f"<td class='{cls}'>{qv}</td>"
            d_td = f"<td class='{cls}'>{dv}</td>"
            html.append(f"<tr><td>{label}</td>{q_td}{d_td}</tr>")
        html.append("</tbody></table></div>")
        st.markdown("\n".join(html), unsafe_allow_html=True)
    else:
        st.info("لا توجد بيانات للمقارنة في هذا السجل.")

    # استدعاء الأزرار التحكم (اختيار المصدر + التنقل)
    render_selection_buttons(qistas_data, diwan_data, current_index, total_records)
    render_navigation_buttons(current_index, total_records)


def render_selection_buttons(qistas_data: dict, diwan_data: dict, current_index: int, total_records: int):
    """عرض أزرار اختيار المصدر"""
    st.markdown("---")
    st.markdown("<h3 style='color: white !important; text-align: center; margin-top: 2rem;'>❓ أيهما أكثر دقة؟</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ قسطاس صحيح", use_container_width=True, key=f"qistas_{current_index}"):
            save_comparison_record(qistas_data, 'قسطاس')
            st.success("✅ تم حفظ النتيجة من قسطاس!")
            move_to_next_record(total_records, current_index)
    
    with col2:
        if st.button("✅ الديوان صحيح", use_container_width=True, key=f"diwan_{current_index}"):
            save_comparison_record(diwan_data, 'الديوان')
            st.success("✅ تم حفظ النتيجة من الديوان!")
            move_to_next_record(total_records, current_index)
    
    with col3:
        form_key = SessionManager.get_unique_key('show_custom_form')

        if st.button("⚠️ لا أحد منهم", use_container_width=True, key=f"none_{current_index}_{option}"):
            st.session_state[form_key] = True
            st.rerun()

    
    # نموذج الإدخال المخصص
    if st.session_state.get(form_key, False):

        render_custom_form(qistas_data, current_index, total_records)


def render_custom_form(reference_data: dict, current_index: int, total_records: int):
    """عرض نموذج الإدخال المخصص"""
    st.markdown("---")
    st.markdown("<h3 style='color: white !important; text-align: center;'>✍️ أدخل البيانات الصحيحة</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.form("custom_data_form", clear_on_submit=False):
        custom_data = {}
        
        # إنشاء حقول إدخال لكل عمود
        num_cols = 3
        columns = list(reference_data.keys())
        
        for i in range(0, len(columns), num_cols):
            cols = st.columns(num_cols)
            for j, col in enumerate(cols):
                if i + j < len(columns):
                    field_name = columns[i + j]
                    default_value = reference_data[field_name]
                    custom_data[field_name] = col.text_input(
                        field_name, 
                        value=str(default_value) if default_value else ""
                    )
        
        col1, col2 = st.columns(2)
        with col1:
            submit_custom = st.form_submit_button("💾 حفظ والانتقال للتالي", use_container_width=True)
        with col2:
            cancel_custom = st.form_submit_button("❌ إلغاء", use_container_width=True)
        
        form_key = SessionManager.get_unique_key('show_custom_form')

        if submit_custom:
            save_comparison_record(custom_data, 'مصدر آخر')
            st.session_state[form_key] = False
            st.success("✅ تم حفظ البيانات المخصصة!")
            move_to_next_record(total_records, current_index)

        if cancel_custom:
            st.session_state[form_key] = False
            st.rerun()


def render_navigation_buttons(current_index: int, total_records: int):
    """عرض أزرار التنقل"""
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    idx_key = SessionManager.get_unique_key('current_index')
    form_key = SessionManager.get_unique_key('show_custom_form')
    next_key = SessionManager.get_unique_key('show_next_in_review')
    max_key = SessionManager.get_unique_key('max_reached_idx')
    
    with col1:
        if current_index > 0:
            if st.button("⏮️ السابق", use_container_width=True):
                st.session_state[idx_key] -= 1
                st.session_state[form_key] = False
                
                # 🔥 عند الرجوع للخلف: نسمح بزر "التالي" (وضع المراجعة)
                st.session_state[next_key] = True
                
                save_persistent_data()
                st.rerun()
    
    # 🔥 زر التالي الجديد
    with col3:
        max_reached = st.session_state.get(max_key, 0)
        show_next = st.session_state.get(next_key, False)
        
        # نعرض الزر فقط إذا:
        # 1. في صفحات بعدنا
        # 2. وضع المراجعة مفعّل
        # 3. الصفحة الحالية أقل من آخر صفحة وصلنا لها
        if current_index < total_records - 1 and show_next and current_index < max_reached:
            if st.button("⏭️ التالي", use_container_width=True, type="primary"):
                new_idx = current_index + 1
                st.session_state[idx_key] = new_idx
                
                # 🔥 إذا وصلنا لآخر صفحة كنا فيها: نخفي زر "التالي"
                if new_idx >= max_reached:
                    st.session_state[next_key] = False
                
                save_persistent_data()
                st.rerun()
    


def render_comparison_tab(qistas_df: pd.DataFrame, diwan_df: pd.DataFrame):
    """عرض تبويب المقارنة التفصيلية"""
    st.markdown("<div class='comparison-card'>", unsafe_allow_html=True)

    # 🔥 إخفاء زر "التالي" إذا كان فورم الإدخال المخصص مفتوح
    form_key = SessionManager.get_unique_key('show_custom_form')
    next_key = SessionManager.get_unique_key('show_next_in_review')
    
    if st.session_state.get(form_key, False):
        st.session_state[next_key] = False
    
    total_records = min(len(qistas_df), len(diwan_df))
    idx_key = SessionManager.get_unique_key('current_index')
    current_index = st.session_state[idx_key]

    
    # شريط التقدم
    progress_percentage = int(((current_index + 1) / total_records) * 100) if total_records > 0 else 0
    st.markdown(f"""
        <div class='wizard-container'>
            <h3 style='color: #667eea; text-align: center; margin-bottom: 0.5rem;'>مقارنة التشريعات</h3>
            <p style='color: #718096; text-align: center; font-size: 1.1em; margin-bottom: 2rem;'>
                {current_index + 1} من {total_records} ({progress_percentage}%)
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # عرض الخطوات
    if total_records > 0:
        render_wizard_steps(current_index, total_records)
    
    # شريط التقدم
    st.markdown(f"""
        <div style="background: #e2e8f0; height: 15px; border-radius: 10px; overflow: hidden; margin: 1.5rem 0 2rem 0;">
            <div style="height: 100%; background: linear-gradient(90deg, #667eea 0%, #48bb78 100%); 
                        width: {progress_percentage}%; transition: width 0.5s ease; border-radius: 10px;">
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    
    if current_index < total_records:
        render_law_comparison(qistas_df, diwan_df, current_index, total_records)
    else:
        st.success(f"🎉 تم الانتهاء من مراجعة جميع السجلات!")
        if st.button("🔄 البدء من جديد", use_container_width=True, key=f"restart_{option}"):
            st.session_state[idx_key] = 0
            st.session_state[SessionManager.get_unique_key('show_custom_form')] = False
            save_persistent_data()
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)


def render_saved_data_tab():
    """عرض تبويب البيانات المحفوظة - ملفات منفصلة لكل نوع + حذف نهائي"""
    st.markdown("<div class='comparison-card'>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='color: #667eea !important; text-align: center;'>البيانات المحفوظة - {option}</h2>", unsafe_allow_html=True)
    st.markdown("---")

    # ==================== نتائج المقارنة التفصيلية (كما هي) ====================
    comp_key = SessionManager.get_unique_key('comparison_data')
    
    st.markdown("### نتائج المقارنة التفصيلية")
    
    if st.session_state.get(comp_key):
        df_comp = pd.DataFrame(st.session_state[comp_key])
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_comp.to_excel(writer, sheet_name='المقارنة', index=False)

        c1, c2 = st.columns([3, 1])
        with c1:
            st.download_button(
                label=f"تحميل مقارنة {option} ({len(df_comp)} سجل)",
                data=buffer.getvalue(),
                file_name=COMPARISON_FILE,
                mime="application/vnd.openpyxlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with c2:
            confirm_key = f"confirm_delete_comp_{option}"
            if st.button("مسح نتائج المقارنة نهائيًا", type="secondary", use_container_width=True):
                if st.session_state.get(confirm_key, False):
                    for f in [DATA_FILE, PROGRESS_FILE]:
                        if os.path.exists(f): os.remove(f)
                    st.session_state[comp_key] = []
                    st.session_state[SessionManager.get_unique_key('current_index')] = 0
                    st.session_state[confirm_key] = False
                    st.success("تم حذف نتائج المقارنة نهائيًا")
                    st.rerun()
                else:
                    st.session_state[confirm_key] = True
                    st.warning("هل أنت متأكد؟ اضغط مرة أخرى للحذف النهائي")
    else:
        st.info(f"لا توجد بيانات محفوظة للمقارنة في {option} بعد")

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    # ==================================================================
    # القيم المفقودة المُصححة – الحل النهائي والمضمون
    # ==================================================================
    st.markdown("### القيم المفقودة المُصححة")

    malq_saved_key = f'malq_completed_records_{option.replace(" ", "_")}'

    # الحل السحري: كل ما نفتح التبويب ده، نقرأ من الاكسل لو موجود
    if os.path.exists(MISSING_FILE):
        try:
            df_loaded = pd.read_excel(MISSING_FILE)
            # نحدث الذاكرة فورًا من الملف
            st.session_state[malq_saved_key] = df_loaded.to_dict('records')
            st.success(f"تم تحميل {len(df_loaded)} سجل مصحح من الملف")
        except Exception as e:
            st.error(f"خطأ في قراءة الملف: {e}")
            if malq_saved_key not in st.session_state:
                st.session_state[malq_saved_key] = []
    else:
        # لو الملف مش موجود، نتأكد إن المفتاح موجود وفاضي
        if malq_saved_key not in st.session_state:
            st.session_state[malq_saved_key] = []

    # نجيب البيانات من الذاكرة (اللي تم تحديثها فوق)
    saved_records = st.session_state.get(malq_saved_key, [])

    if saved_records:
        df_missing = pd.DataFrame(saved_records)
        st.dataframe(df_missing, use_container_width=True, hide_index=True)

        col1, col2 = st.columns([3, 1])
        with col1:
            with open(MISSING_FILE, "rb") as f:
                st.download_button(
                    label=f"تحميل {option} المُصححة ({len(saved_records)} سجل)",
                    data=f.read(),
                    file_name=MISSING_FILE,
                    mime="application/vnd.openpyxlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        with col2:
            confirm_miss_key = f"confirm_delete_missing_{option}"
            if st.button("مسح القيم المفقودة نهائيًا", type="secondary", use_container_width=True):
                if st.session_state.get(confirm_miss_key, False):
                    if os.path.exists(MISSING_FILE):
                        os.remove(MISSING_FILE)
                    progress_file = f'malq_progress_{option.replace(" ", "_")}.json'
                    if os.path.exists(progress_file):
                        os.remove(progress_file)
                    st.session_state[malq_saved_key] = []
                    # نمسح كل مفاتيح malq_ عشان نرجع زي الأول
                    for k in list(st.session_state.keys()):
                        if k.startswith('malq_'):
                            del st.session_state[k]
                    st.session_state[confirm_miss_key] = False
                    st.success("تم حذف ملف القيم المفقودة نهائيًا")
                    st.rerun()
                else:
                    st.session_state[confirm_miss_key] = True
                    st.warning("تحذير: اضغط مرة أخرى للحذف النهائي")
    else:
        st.info(f"لا توجد قيم مفقودة مُصححة لـ {option} بعد")

    st.markdown("</div>", unsafe_allow_html=True)
def generate_side_card(data: dict, shown_cols: list, title: str, layout: str = 'grid', hide_on_status2: bool = False) -> str:
    """إنشاء HTML لكارت مصدر (قسطاس/الديوان)
    يدعم layout = 'grid' أو 'scroll' (قائمة عمودية قابلة للتمرير)
    """
    status = data.get('Status') if isinstance(data.get('Status'), (int, float)) else None

    # كلاس القاعدة
    card_classes = "source-card"
    inner_html = ""

    if layout == 'scroll':
        # اختيار كلاس مخصص اعتماداً على العنوان (قسطاس vs الديوان)
        if 'قسطاس' in title:
            card_classes += " qistas-card"
            scroll_class = "qistas-scroll"
        else:
            card_classes += " diwan-card"
            scroll_class = "diwan-scroll"

        inner_html += f"<div class='{scroll_class}'>"
        # عرض كل الحقول كصفوف عمودية واضحة (compact)
        for key in shown_cols:
            if key not in data:
                continue
            if hide_on_status2 and status == 2 and key in ('Replaced By', 'EndDate', 'Canceled By'):
                continue
            value = '' if data.get(key) is None else data.get(key)
            safe_value = str(value)
            inner_html += (
                "<div class='info-card' style='display:block;'>"
                f"<div class='field-name'>{key}</div>"
                f"<div class='field-value'>{safe_value}</div>"
                "</div>"
            )
        inner_html += "</div>"

    else:
        # الوضع الشبكي الافتراضي: بطاقات صغيرة موزعة
        inner_html += "<div class='info-grid'>"
        for key in shown_cols:
            if key not in data:
                continue
            if hide_on_status2 and status == 2 and key in ('Replaced By', 'EndDate', 'Canceled By'):
                continue
            value = '' if data.get(key) is None else data.get(key)
            safe_value = str(value)
            inner_html += (
                "<div class='info-card'>"
                f"<div class='field-name'>{key}</div>"
                f"<div class='field-value'>{safe_value}</div>"
                "</div>"
            )
        inner_html += "</div>"

    html = f"<div class='{card_classes}'><h4>{title}</h4>{inner_html}</div>"
    return html


# ==================== البرنامج الرئيسي ====================
def main():
    """الدالة الرئيسية للبرنامج"""
    # تطبيق التنسيقات
    apply_styles()
    
    # العنوان الرئيسي
    st.markdown("""
        <div class="title-container">
            <h1 style='color: #667eea; margin: 0;'>⚖️ نظام التحقق من التشريعات القانونية</h1>
            <p style='color: #718096; margin-top: 0.5rem; font-size: 18px;'>
                مقارنة شاملة بين بيانات قسطاس والديوان التشريعي
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # تهيئة البيانات
    initialize_session_state()
    
    # تحميل البيانات من CSV بحسب اختيار المستخدم
    qistas_df, diwan_df = load_csv_data(option)
    
    if isinstance(qistas_df, pd.DataFrame) and 'GroupKey' in qistas_df.columns:
        qistas_df = qistas_df.sort_values(by='GroupKey').reset_index(drop=True)
    if isinstance(diwan_df, pd.DataFrame) and 'GroupKey' in diwan_df.columns:
        diwan_df = diwan_df.sort_values(by='GroupKey').reset_index(drop=True)
    
    if qistas_df is None or diwan_df is None:
        st.error("⚠️ فشل تحميل ملفات CSV للنوع المحدد. تأكد من وجود الملفات أو تعديل مرشحات المسارات في الكود.")
        # عرض أمثلة المسارات الممكنة للمساعدة
        st.info("مسارات محتملة:\n- extData/Bylaws/... (النظام)\n- extData/Laws/... (القوانين)\n- extData/Instructions/... (التعليمات)")
        return
    

    st.sidebar.markdown("---")
    
    # التبويبات
    tab1, tab2, tab3 = st.tabs([
        "🔍 مقارنة تفصيلية",      
        "📁 البيانات المحفوظة",   
        "⚠️ قيم مفقودة"            
    ])
    
    # ========== التبويب الأول: المقارنة التفصيلية ==========
    with tab1:
        render_comparison_tab(qistas_df, diwan_df)
    
    # ========== التبويب الثاني: البيانات المحفوظة ==========
    with tab2:
        render_saved_data_tab()
    with tab3:
        render_missing_malq_tab()
    
    # التذييل
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: white; padding: 1rem;'>
            <p>نظام التحقق من التشريعات القانونية © 2025</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

