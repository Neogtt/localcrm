# crm.py
import streamlit as st
import pandas as pd
import numpy as np
import io, os, re, time, tempfile, datetime, mimetypes, json, logging
from email.message import EmailMessage
import smtplib
from typing import Tuple
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from streamlit_option_menu import option_menu

# ===========================
# ==== GENEL AYARLAR
# ===========================
st.set_page_config(page_title="ŞEKEROĞLU İHRACAT CRM", layout="wide")

# Load Bootstrap Icons for consistent menu visuals
st.markdown(
    '<link rel="stylesheet" '
    'href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">',
    unsafe_allow_html=True,
)

# Load custom sidebar styles

sidebar_css = Path(__file__).resolve().parent / "css" / "sidebar.css"
if sidebar_css.exists():
    with sidebar_css.open() as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    logging.warning("Sidebar CSS file not found at %s", sidebar_css)
    
# Sabitler (Kullanacağımız Drive klasörleri ve Sheets)

SHEET_ID = "1A_gL11UL6JFAoZrMrg92K8bAegeCn_KzwUyU8AWzE_0"
MUSTERI_SHEET_NAME = "Sayfa1"

LOGO_FILE_ID = "1DCxtSsAeR7Zfk2IQU0UMGmD0uTdNO1B3"
LOGO_LOCAL_NAME = "logo1.png"

FIYAT_TEKLIFI_ID = "1TNjwx-xhmlxNRI3ggCJA7jaCAu9Lt_65"   # Teklif PDF klasörü
EVRAK_KLASOR_ID   = "14FTE1oSeIeJ6Y_7C0oQyZPKC8dK8hr1J"   # Evrak ana klasör
PROFORMA_PDF_FOLDER_ID  = "17lPkdYcC4BdowLdCsiWxiq0H_6oVGXLs"
SIPARIS_FORMU_FOLDER_ID = "1xeTdhOE1Cc6ohJsRzPVlCMMraBIXWO9w"

# ===========================
# ==== KULLANICI GİRİŞİ
# ===========================
USERS = {"export1":"Seker12345!", "admin":"Seker12345!", "Boss":"Seker12345!"}
if "user" not in st.session_state: st.session_state.user = None

def login_screen():
    st.title("ŞEKEROĞLU CRM - Giriş Ekranı")
    u = st.text_input("Kullanıcı Adı")
    p = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        if u in USERS and p == USERS[u]:
            st.session_state.user = u
            st.success("Giriş başarılı!")
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı.")

if not st.session_state.user:
    login_screen()
    st.stop()

if st.sidebar.button("Çıkış Yap"):
    st.session_state.user = None
    st.rerun()

# ===========================
# ==== REFERANS LİSTELER
# ===========================
ulke_listesi = sorted([
    "Afganistan","Almanya","Amerika Birleşik Devletleri","Andorra","Angola","Antigua ve Barbuda","Arjantin",
    "Arnavutluk","Avustralya","Avusturya","Azerbaycan","Bahamalar","Bahreyn","Bangladeş","Barbados","Belçika",
    "Belize","Benin","Beyaz Rusya","Bhutan","Birleşik Arap Emirlikleri","Birleşik Krallık","Bolivya",
    "Bosna-Hersek","Botsvana","Brezilya","Brunei","Bulgaristan","Burkina Faso","Burundi","Butan",
    "Cezayir","Çad","Çekya","Çin","Danimarka","Doğu Timor","Dominik Cumhuriyeti","Dominika","Ekvador",
    "Ekvator Ginesi","El Salvador","Endonezya","Eritre","Ermenistan","Estonya","Etiyopya","Fas",
    "Fiji","Fildişi Sahili","Filipinler","Filistin","Finlandiya","Fransa","Gabon","Gambia",
    "Gana","Gine","Gine-Bissau","Grenada","Guatemala","Guyana","Güney Afrika","Güney Kore",
    "Güney Sudan","Gürcistan","Haiti","Hindistan","Hırvatistan","Hollanda","Honduras","Hong Kong",
    "Irak","İran","İrlanda","İspanya","İsrail","İsveç","İsviçre","İtalya","İzlanda","Jamaika",
    "Japonya","Kamboçya","Kamerun","Kanada","Karadağ","Katar","Kazakistan","Kenya","Kırgızistan",
    "Kiribati","Kolombiya","Komorlar","Kongo","Kongo Demokratik Cumhuriyeti","Kostarika","Küba",
    "Kuveyt","Kuzey Kore","Kuzey Makedonya","Laos","Lesotho","Letonya","Liberya","Libya",
    "Liechtenstein","Litvanya","Lübnan","Lüksemburg","Macaristan","Madagaskar","Malavi","Maldivler",
    "Malezya","Mali","Malta","Marshall Adaları","Meksika","Mısır","Mikronezya","Moğolistan","Moldova",
    "Monako","Morityus","Mozambik","Myanmar","Namibya","Nauru","Nepal","Nijer","Nijerya",
    "Nikaragua","Norveç","Orta Afrika Cumhuriyeti","Özbekistan","Pakistan","Palau","Panama","Papua Yeni Gine",
    "Paraguay","Peru","Polonya","Portekiz","Romanya","Ruanda","Rusya","Saint Kitts ve Nevis",
    "Saint Lucia","Saint Vincent ve Grenadinler","Samoa","San Marino","Sao Tome ve Principe","Senegal",
    "Seyşeller","Sırbistan","Sierra Leone","Singapur","Slovakya","Slovenya","Solomon Adaları","Somali",
    "Sri Lanka","Sudan","Surinam","Suriye","Suudi Arabistan","Svaziland","Şili","Tacikistan","Tanzanya",
    "Tayland","Tayvan","Togo","Tonga","Trinidad ve Tobago","Tunus","Tuvalu","Türkiye","Türkmenistan",
    "Uganda","Ukrayna","Umman","Uruguay","Ürdün","Vanuatu","Vatikan","Venezuela","Vietnam",
    "Yemen","Yeni Zelanda","Yunanistan","Zambiya","Zimbabve"
]) + ["Diğer"]

temsilci_listesi = ["KEMAL İLKER ÇELİKKALKAN", "HÜSEYİN POLAT", "EFE YILDIRIM", "FERHAT ŞEKEROĞLU"]

# ===========================
# ==== GOOGLE API SERVİSLERİ (Service Account)
# ===========================
@st.cache_resource
def build_sheets():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)

@st.cache_resource
def build_drive():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)

# Güvenlik eklemesi
try:
    sheets_svc = build_sheets()
    drive_svc  = build_drive()
except Exception as e:
    st.error(f"Google API servisleri başlatılamadı: {e}")
    st.stop()

def safe_name(text, maxlen=120):
    """Dosya ve klasör adları için güvenli bir isim üretir."""
    s = str(text or "").strip().replace(" ", "_")
    s = re.sub(r'[\\/*?:"<>|]+', "_", s)
    return s[:maxlen]

def get_or_create_child_folder(folder_name: str, parent_id: str) -> str:
    """Verilen parent klasör içinde folder_name adlı alt klasörü döndürür; yoksa oluşturur."""
    query = (
        f"'{parent_id}' in parents and "
        f"name='{folder_name}' and "
        "mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    result = drive_svc.files().list(
        q=query, spaces="drive", fields="files(id)", pageSize=1
    ).execute()
    files = result.get("files", [])
    if files:
        return files[0]["id"]
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    created = drive_svc.files().create(body=metadata, fields="id").execute()
    return created.get("id")

def upload_bytes_to_folder(folder_id: str, filename: str, data: bytes) -> str:
    """Byte verisini Drive'da belirtilen klasöre yükler ve paylaşılabilir linki döndürür."""
    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaIoBaseUpload(
        io.BytesIO(data),
        mimetype=mimetypes.guess_type(filename)[0] or "application/octet-stream",
    )
    uploaded = drive_svc.files().create(
        body=file_metadata, media_body=media, fields="id, webViewLink"
    ).execute()
    return uploaded.get("webViewLink") or uploaded.get("id")


# === Google Sheets Okuma Fonksiyonları ===

def ensure_required_columns(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    """Belirlenen zorunlu kolonları ekler, eksikleri boş değerle tamamlar."""
    required_columns = {
        "Sayfa1": {
            "Müşteri Adı": "",
            "Ülke": "",
            "Telefon": "",
            "E-posta": "",
            "Adres": "",
            "Satış Temsilcisi": "",
            "Kategori": "",
            "Durum": "",
            "Vade (Gün)": "",
            "Ödeme Şekli": "",
            "Para Birimi": "",
            "DT Seçimi": "",
        },
        "Kayıtlar": {
            "Müşteri Adı": "",
            "Tarih": "",
            "Tip": "",
            "Açıklama": "",
        },
        "Teklifler": {
            "Müşteri Adı": "",
            "Tarih": "",
            "Teklif No": "",
            "Tutar": "",
            "Ürün/Hizmet": "",
            "Açıklama": "",
            "Durum": "",
            "PDF": "",
        },
        "Proformalar": {
            "Müşteri Adı": "",
            "Tarih": "",
            "Proforma No": "",
            "Tutar": "",
            "Vade (gün)": "",
            "Açıklama": "",
            "Durum": "",
            "Sevk Durumu": "",
            "Termin Tarihi": "",
            "Sipariş Formu": "",
            "Ulaşma Tarihi": "",
        },
        "Evraklar": {
            "Müşteri Adı": "",
            "Proforma No": "",
            "Fatura No": "",
            "Fatura Tarihi": "",
            "Vade Tarihi": "",
            "Tutar": "",
            "Ödendi": False,
            "Ödeme Kanıtı": "",
        },
        "ETA": {
            "Müşteri Adı": "",
            "Proforma No": "",
            "ETA Tarihi": "",
            "Açıklama": "",
        },
        "FuarMusteri": {
            "Fuar Adı": "",
            "Müşteri Adı": "",
            "Ülke": "",
            "Telefon": "",
            "E-mail": "",
            "Satış Temsilcisi": "",
            "Açıklamalar": "",
            "Görüşme Kalitesi": "",
            "Tarih": "",
        },
    }

    required = required_columns.get(sheet_name, {})
    for col, default in required.items():
        if col not in df.columns:
            df[col] = default
    return df


def read_sheet(sheet_name: str) -> pd.DataFrame:
    """Google Sheets'ten oku, eksik kolonları tamamla"""
    try:
        sheet = sheets_svc.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range=f"{sheet_name}!A1:ZZ"
        ).execute()
        values = result.get("values", [])
        if not values:
            st.warning(f"{sheet_name} sheet'i boş görünüyor.")
            return ensure_required_columns(pd.DataFrame(), sheet_name)

        if len(values) > 1:
            header, rows = values[0], values[1:]
            df = pd.DataFrame(rows, columns=header)
        else:
            header = values[0]
            df = pd.DataFrame(columns=header)

        return ensure_required_columns(df, sheet_name)

    except Exception as e:
        st.error(f"{sheet_name} okunamadı: {e}")
        return ensure_required_columns(pd.DataFrame(), sheet_name)


def read_all_sheets() -> Tuple[pd.DataFrame, ...]:
    """Tüm sheet'leri okuyup DataFrame'leri döndür"""
    df_m = read_sheet("Sayfa1")
    df_k = read_sheet("Kayıtlar")
    df_t = read_sheet("Teklifler")
    df_p = read_sheet("Proformalar")
    df_e = read_sheet("Evraklar")
    df_eta = read_sheet("ETA")
    df_fuar = read_sheet("FuarMusteri")
    return df_m, df_k, df_t, df_p, df_e, df_eta, df_fuar


def load_frames_from_local() -> Tuple[pd.DataFrame, ...]:
    if not os.path.exists("temp.xlsx"):
        return read_all_sheets()
    else:
        with pd.ExcelFile("temp.xlsx") as xls:
            df_m = pd.read_excel(xls, "Sayfa1") if "Sayfa1" in xls.sheet_names else pd.DataFrame()
            df_k = pd.read_excel(xls, "Kayıtlar") if "Kayıtlar" in xls.sheet_names else pd.DataFrame()
            df_t = pd.read_excel(xls, "Teklifler") if "Teklifler" in xls.sheet_names else pd.DataFrame()
            df_p = pd.read_excel(xls, "Proformalar") if "Proformalar" in xls.sheet_names else pd.DataFrame()
            df_e = pd.read_excel(xls, "Evraklar") if "Evraklar" in xls.sheet_names else pd.DataFrame()
            df_eta = pd.read_excel(xls, "ETA") if "ETA" in xls.sheet_names else pd.DataFrame()
            df_fuar = pd.read_excel(xls, "FuarMusteri") if "FuarMusteri" in xls.sheet_names else pd.DataFrame()

        # ✅ Eksik kolonları tamamla
        df_m = ensure_required_columns(df_m, "Sayfa1")
        df_k = ensure_required_columns(df_k, "Kayıtlar")
        df_t = ensure_required_columns(df_t, "Teklifler")
        df_p = ensure_required_columns(df_p, "Proformalar")
        df_e = ensure_required_columns(df_e, "Evraklar")
        df_eta = ensure_required_columns(df_eta, "ETA")
        df_fuar = ensure_required_columns(df_fuar, "FuarMusteri")

        return df_m, df_k, df_t, df_p, df_e, df_eta, df_fuar
        
df_musteri, df_kayit, df_teklif, df_proforma, df_evrak, df_eta, df_fuar = load_frames_from_local()

def update_excel():
    """Persist global DataFrames to local Excel and optionally sync to Google Sheets."""
    global df_musteri, df_kayit, df_teklif, df_proforma, df_evrak, df_eta, df_fuar

    with pd.ExcelWriter("temp.xlsx", engine="openpyxl") as writer:
        df_musteri.to_excel(writer, sheet_name="Sayfa1", index=False)
        df_kayit.to_excel(writer, sheet_name="Kayıtlar", index=False)
        df_teklif.to_excel(writer, sheet_name="Teklifler", index=False)
        df_proforma.to_excel(writer, sheet_name="Proformalar", index=False)
        df_evrak.to_excel(writer, sheet_name="Evraklar", index=False)
        df_eta.to_excel(writer, sheet_name="ETA", index=False)
        df_fuar.to_excel(writer, sheet_name="FuarMusteri", index=False)

    # ✅ Optional: sync customers to Google Sheets
    try:
        write_customers_to_gsheet(df_musteri)
    except Exception as e:
        st.warning(f"Google Sheets güncellemesi başarısız: {e}")

def execute_with_retry(request, retries: int = 3, wait: float = 1.0):
    """Execute a Google API request with retry on rate limit or server errors."""
    for attempt in range(retries):
        try:
            return request.execute()
        except HttpError as err:
            status = getattr(err, "resp", None)
            status = getattr(status, "status", None)
            if status in (429,) or (status is not None and 500 <= status < 600):
                if attempt == retries - 1:
                    raise
                time.sleep(wait)
            else:
                raise


def write_customers_to_gsheet(df: pd.DataFrame):
    """Write customer DataFrame to the Google Sheet."""
    values = [df.columns.tolist()] + df.fillna("").astype(str).values.tolist()
    body = {"values": values}
    request = sheets_svc.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=f"{MUSTERI_SHEET_NAME}!A1",
        valueInputOption="RAW",
        body=body,
    )
    return execute_with_retry(request)

def push_customers_throttled(cooldown: int = 10):
    """Push customers to Google Sheets with a simple cooldown."""
    if "last_customer_push" not in st.session_state:
        st.session_state.last_customer_push = 0.0

    elapsed = time.time() - st.session_state.last_customer_push
    if elapsed < cooldown:
        remaining = int(cooldown - elapsed)
        st.info(f"Lütfen {remaining} saniye sonra tekrar deneyin.")
        return

    try:
        write_customers_to_gsheet(df_musteri)
        st.success("Müşteriler Google Sheets'e yazıldı!")
        st.session_state.last_customer_push = time.time()
    except Exception as e:
        st.error(f"Google Sheets güncellemesi başarısız: {e}")

def _sanitize_vade(value):
    numeric_value = pd.to_numeric(value, errors="coerce")
    return int(numeric_value) if pd.notna(numeric_value) else 0

# ===========================
# ==== ŞIK SIDEBAR MENÜ
# ===========================
menuler = [
    ("Özet Ekran", "bar-chart"),
    ("Cari Ekleme", "person-plus"),
    ("Müşteri Listesi", "people"),
    ("Görüşme / Arama / Ziyaret Kayıtları", "telephone"),
    ("Fiyat Teklifleri", "currency-dollar"),
    ("Proforma Takibi", "file-earmark-text"),
    ("Güncel Sipariş Durumu", "truck"),
    ("Fatura & İhracat Evrakları", "file-earmark"),
    ("Vade Takibi", "clock"),
    ("ETA Takibi", "calendar-event"),
    ("Fuar Müşteri Kayıtları", "ticket"),
    ("Medya Çekmecesi", "folder"),
    ("Satış Performansı", "graph-up"),
]

if st.session_state.user == "Boss":
    allowed_menus = [("Özet Ekran", "bar-chart")]
else:
    allowed_menus = menuler

menu_names = [n for n, _ in allowed_menus]
menu_icons = [i for _, i in allowed_menus]

if "menu_state" not in st.session_state or st.session_state.menu_state not in menu_names:
    st.session_state.menu_state = menu_names[0]

default_idx = menu_names.index(st.session_state.menu_state)

# Display company logo above the menu if available
if os.path.exists(LOGO_LOCAL_NAME):
    st.sidebar.image(LOGO_LOCAL_NAME, use_column_width=True)

with st.sidebar:
    selected = option_menu(
        menu_title=None,
        options=menu_names,
        icons=menu_icons,
        default_index=default_idx,
        key="menu_option_menu",
    )

st.session_state.menu_state = selected
menu = st.session_state.menu_state

# Sidebar: manuel senkron
with st.sidebar.expander("🔄 Sheets Senkron"):
    if st.button("Müşterileri Sheets’e Yaz"):
        push_customers_throttled()

# ===========================
# ==== E-POSTA (Cari açılış)
# ===========================
def yeni_cari_txt_olustur(cari_dict, file_path="yeni_cari.txt"):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(
            f"Müşteri Adı: {cari_dict.get('Müşteri Adı','')}\n"
            f"Telefon: {cari_dict.get('Telefon','')}\n"
            f"E-posta: {cari_dict.get('E-posta','')}\n"
            f"Adres: {cari_dict.get('Adres','')}\n"
            f"Ülke: {cari_dict.get('Ülke','')}\n"
            f"Satış Temsilcisi: {cari_dict.get('Satış Temsilcisi','')}\n"
            f"Kategori: {cari_dict.get('Kategori','')}\n"
            f"Durum: {cari_dict.get('Durum','')}\n"
            f"Vade (Gün): {cari_dict.get('Vade (Gün)','')}\n"
            f"Ödeme Şekli: {cari_dict.get('Ödeme Şekli','')}\n"
            f"Para Birimi: {cari_dict.get('Para Birimi','')}\n"
            f"DT Seçimi: {cari_dict.get('DT Seçimi','')}\n"
        )

def send_email_with_txt(to_email, subject, body, file_path):
    from_email = "todo@sekeroglugroup.com"
    password   = "vbgvforwwbcpzhxf"  # senin bıraktığın gibi düz metin

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_email)
    msg.set_content(body)

    with open(file_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="text",
            subtype="plain",
            filename="yeni_cari.txt"
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(from_email, password)
        smtp.send_message(msg)

# ===========================
# ==== MENÜLER
# ===========================

# --- ÖZET EKRAN ---
if menu == "Özet Ekran":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>📊 Özet Ekran</h2>", unsafe_allow_html=True)

    def smart_to_num(x):
        if pd.isna(x): return 0.0
        s = str(x).strip()
        for sym in ["USD","$","€","EUR","₺","TL","tl","Tl"]:
            s = s.replace(sym, "")
        s = s.replace("\u00A0", "").replace(" ", "")
        try:
            return float(s)
        except:
            pass
        if "," in s:
            try:
                return float(s.replace(".", "").replace(",", "."))
            except:
                pass
        return 0.0

    # === Toplam fatura tutarı ===
    toplam_fatura_tutar = 0.0
    if not df_evrak.empty and "Tutar" in df_evrak.columns:
        _ev = df_evrak.copy()
        _ev["Tutar_num"] = _ev["Tutar"].apply(smart_to_num).fillna(0.0)
        toplam_fatura_tutar = float(_ev["Tutar_num"].sum())
    st.markdown(
        f"<div style='font-size:1.4em;color:#B22222;font-weight:bold;'>💰 Toplam Fatura Tutarı: {toplam_fatura_tutar:,.2f} USD</div>",
        unsafe_allow_html=True
    )

    st.markdown("---")

    # === Vade Analizi ===
    for col in ["Vade Tarihi", "Ödendi", "Tutar"]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col != "Ödendi" else False

    v = df_evrak.copy()
    v["Ödendi"] = v["Ödendi"].fillna(False).astype(bool)
    v["Vade Tarihi"] = pd.to_datetime(v["Vade Tarihi"], errors="coerce")
    v["Tutar_num"] = v["Tutar"].apply(smart_to_num).fillna(0.0)

    today_norm = pd.Timestamp.today().normalize()
    od_me = ~v["Ödendi"]

    m_gelmemis = (v["Vade Tarihi"] > today_norm) & od_me
    m_bugun = (v["Vade Tarihi"].dt.date == today_norm.date()) & od_me
    m_gecikmis = (v["Vade Tarihi"] < today_norm) & od_me

    c1, c2, c3 = st.columns(3)
    c1.metric("📅 Vadesi Gelmemiş", f"{v.loc[m_gelmemis, 'Tutar_num'].sum():,.2f} USD", f"{int(m_gelmemis.sum())} Fatura")
    c2.metric("⚠️ Bugün Vadesi Dolan", f"{v.loc[m_bugun, 'Tutar_num'].sum():,.2f} USD", f"{int(m_bugun.sum())} Fatura")
    c3.metric("⛔ Gecikmiş", f"{v.loc[m_gecikmis, 'Tutar_num'].sum():,.2f} USD", f"{int(m_gecikmis.sum())} Fatura")

    acik = v[v["Vade Tarihi"].notna() & (~v["Ödendi"])].copy()
    if not acik.empty:
        acik["Kalan Gün"] = (acik["Vade Tarihi"] - today_norm).dt.days
        st.markdown("#### 💸 Açık Vade Kayıtları")
        cols = ["Müşteri Adı", "Ülke", "Fatura No", "Vade Tarihi", "Tutar", "Kalan Gün"]
        cols = [c for c in cols if c in acik.columns]
        acik["Vade Tarihi"] = pd.to_datetime(acik["Vade Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")
        st.dataframe(acik[cols].sort_values("Kalan Gün"), use_container_width=True)
    else:
        st.info("Açık vade kaydı yok.")

    st.markdown("---")

    # === Bekleyen Teklifler ===
    st.markdown("#### 📄 Bekleyen Teklifler")
    if "Durum" in df_teklif.columns:
        bek_teklif = df_teklif[df_teklif["Durum"] == "Açık"].copy()
    else:
        bek_teklif = pd.DataFrame()

    toplam_teklif = pd.to_numeric(bek_teklif.get("Tutar", []), errors="coerce").sum()
    st.markdown(f"<div style='font-size:1.1em;color:#11998e;font-weight:bold;'>Toplam: {toplam_teklif:,.2f} $</div>", unsafe_allow_html=True)
    if bek_teklif.empty:
        st.info("Bekleyen teklif yok.")
    else:
        st.dataframe(bek_teklif[["Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama"]], use_container_width=True)

    # === Bekleyen Proformalar ===
    st.markdown("#### 📄 Bekleyen Proformalar")
    if "Durum" in df_proforma.columns:
        bek_prof = df_proforma[df_proforma["Durum"] == "Beklemede"].copy()
    else:
        bek_prof = pd.DataFrame()

    toplam_p = pd.to_numeric(bek_prof.get("Tutar", []), errors="coerce").sum()
    st.markdown(f"<div style='font-size:1.1em;color:#f7971e;font-weight:bold;'>Toplam: {toplam_p:,.2f} $</div>", unsafe_allow_html=True)
    if bek_prof.empty:
        st.info("Bekleyen proforma yok.")
    else:
        st.dataframe(bek_prof[["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]], use_container_width=True)

    # === Sevk Bekleyen Siparişler ===
    st.markdown("#### 🚚 Sevk Bekleyen Siparişler")
    for c in ["Sevk Durumu", "Ülke", "Termin Tarihi"]:
        if c not in df_proforma.columns:
            df_proforma[c] = ""

    sevk_bekleyen = df_proforma[
        (df_proforma.get("Durum", "") == "Siparişe Dönüştü") &
        (~df_proforma["Sevk Durumu"].isin(["Sevkedildi", "Ulaşıldı"]))
    ].copy()

    toplam_s = pd.to_numeric(sevk_bekleyen.get("Tutar", []), errors="coerce").sum()
    st.markdown(f"<div style='font-size:1.1em;color:#185a9d;font-weight:bold;'>Toplam: {toplam_s:,.2f} $</div>", unsafe_allow_html=True)
    if sevk_bekleyen.empty:
        st.info("Sevk bekleyen sipariş yok.")
    else:
        sevk_bekleyen["Tarih"] = pd.to_datetime(sevk_bekleyen["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")
        sevk_bekleyen["Termin Tarihi"] = pd.to_datetime(sevk_bekleyen["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")
        st.dataframe(sevk_bekleyen[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Termin Tarihi", "Tutar", "Vade (gün)", "Açıklama"]], use_container_width=True)

    # === ETA Takibi ===
    st.markdown("#### 🛳️ ETA Takibi")
    eta_yolda = df_proforma[df_proforma.get("Sevk Durumu", "") == "Sevkedildi"].copy()
    toplam_eta = pd.to_numeric(eta_yolda.get("Tutar", []), errors="coerce").sum()
    st.markdown(f"<div style='font-size:1.1em;color:#c471f5;font-weight:bold;'>Toplam: {toplam_eta:,.2f} $</div>", unsafe_allow_html=True)
    if eta_yolda.empty:
        st.info("Yolda olan (sevk edilmiş) sipariş yok.")
    else:
        eta_yolda["Tarih"] = pd.to_datetime(eta_yolda["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")
        st.dataframe(eta_yolda[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]], use_container_width=True)

    # === Son Teslim Edilenler ===
    st.markdown("#### ✅ Son Teslim Edilenler")
    if "Sevk Durumu" in df_proforma.columns:
        teslim = df_proforma[df_proforma["Sevk Durumu"] == "Ulaşıldı"].copy()
        if not teslim.empty:
            teslim = teslim.sort_values(by="Tarih", ascending=False).head(5)
            teslim["Tarih"] = pd.to_datetime(teslim["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")
            st.dataframe(teslim[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]], use_container_width=True)
        else:
            st.info("Teslim edilmiş sipariş yok.")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.info("Detaylar için soldaki menülerden ilgili bölümlere geçebilirsiniz.")

# --- CARİ EKLEME ---
elif menu == "Cari Ekleme":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Yeni Müşteri Ekle</h2>", unsafe_allow_html=True)

    with st.form("add_customer"):
        name = st.text_input("Müşteri Adı")
        phone = st.text_input("Telefon")
        email = st.text_input("E-posta")
        address = st.text_area("Adres")
        ulke = st.selectbox("Ülke", ulke_listesi)
        temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi)
        kategori = st.selectbox("Kategori", ["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"])
        aktif_pasif = st.selectbox("Durum", ["Aktif", "Pasif"])
        vade_gun = st.number_input("Vade (Gün Sayısı)", min_value=0, max_value=365, value=0, step=1)
        odeme_sekli = st.selectbox("Ödeme Şekli", ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"])
        para_birimi = st.selectbox("Para Birimi", ["EURO", "USD", "TL", "RUBLE"])
        dt_secim = st.selectbox("DT Seçin", ["DT-1", "DT-2", "DT-3", "DT-4"])
        submitted = st.form_submit_button("Kaydet")

    if submitted:
        if not name.strip():
            st.error("Müşteri adı boş olamaz!")
        else:
            new_row = {
                "Müşteri Adı": name,
                "Telefon": phone,
                "E-posta": email,
                "Adres": address,
                "Ülke": ulke,
                "Satış Temsilcisi": temsilci,
                "Kategori": kategori,
                "Durum": aktif_pasif,
                "Vade (Gün)": vade_gun,
                "Ödeme Şekli": odeme_sekli,
                "Para Birimi": para_birimi,
                "DT Seçimi": dt_secim,
            }
            df_musteri = pd.concat([df_musteri, pd.DataFrame([new_row])], ignore_index=True)
            update_excel()

            # === E-posta ===
            yeni_cari_txt_olustur(new_row)
            try:
                send_email_with_txt(
                    to_email=["muhasebe@sekeroglugroup.com", "h.boy@sekeroglugroup.com"],
                    subject="Yeni Cari Açılışı",
                    body="Muhasebe için yeni cari açılışı ekte gönderilmiştir.",
                    file_path="yeni_cari.txt",
                )
                st.success("Müşteri eklendi ve e-posta gönderildi!")
            except Exception as e:
                st.warning(f"Müşteri eklendi ama e-posta gönderilemedi: {e}")

            # === Google Sheets senkron ===
            push_customers_throttled()

            st.rerun()

# --- MÜŞTERİ LİSTESİ ---
elif menu == "Müşteri Listesi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Müşteri Listesi</h2>", unsafe_allow_html=True)

    st.dataframe(df_musteri, use_container_width=True)

    # --- Müşteri Silme ---
    if not df_musteri.empty:
        secili_index = st.selectbox(
            "Silmek istediğiniz müşteri kaydını seçiniz:",
            df_musteri.index,
            format_func=lambda i: f"{df_musteri.at[i, 'Müşteri Adı']} ({df_musteri.at[i, 'Ülke']})"
        )
        if st.button("Müşteriyi Sil"):
            df_musteri = df_musteri.drop(secili_index).reset_index(drop=True)
            update_excel()
            st.success("Müşteri silindi!")
            st.rerun()

    # --- Müşteri Düzenleme ---
    if not df_musteri.empty:
        secili_index_edit = st.selectbox(
            "Düzenlemek istediğiniz müşteri kaydını seçiniz:",
            df_musteri.index,
            format_func=lambda i: f"{df_musteri.at[i, 'Müşteri Adı']} ({df_musteri.at[i, 'Ülke']})"
         )
            
        with st.form("edit_customer"):
            name = st.text_input("Müşteri Adı", value=df_musteri.at[secili_index_edit, "Müşteri Adı"])
            phone = st.text_input("Telefon", value=df_musteri.at[secili_index_edit, "Telefon"])
            email = st.text_input("E-posta", value=df_musteri.at[secili_index_edit, "E-posta"])
            address = st.text_area("Adres", value=df_musteri.at[secili_index_edit, "Adres"])
            ulke = st.selectbox("Ülke", ulke_listesi,
                                index=ulke_listesi.index(df_musteri.at[secili_index_edit, "Ülke"])
                                if df_musteri.at[secili_index_edit, "Ülke"] in ulke_listesi else 0)
            temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi,
                                    index=temsilci_listesi.index(df_musteri.at[secili_index_edit, "Satış Temsilcisi"])
                                    if df_musteri.at[secili_index_edit, "Satış Temsilcisi"] in temsilci_listesi else 0)
            kategori = st.selectbox("Kategori", ["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"],
                                    index=["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"].index(df_musteri.at[secili_index_edit, "Kategori"])
                                    if df_musteri.at[secili_index_edit, "Kategori"] in ["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"] else 0)
            aktif_pasif = st.selectbox("Durum", ["Aktif", "Pasif"],
                                       index=["Aktif", "Pasif"].index(df_musteri.at[secili_index_edit, "Durum"])
                                       if df_musteri.at[secili_index_edit, "Durum"] in ["Aktif", "Pasif"] else 0)
            vade_sanitized = _sanitize_vade(df_musteri.at[secili_index_edit, "Vade (Gün)"])
            vade_gun = st.number_input("Vade (Gün Sayısı)", min_value=0, max_value=365,
                                       value=vade_sanitized)
            odeme_sekli = st.selectbox("Ödeme Şekli", ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"],
                                       index=["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"].index(df_musteri.at[secili_index_edit, "Ödeme Şekli"])
                                       if df_musteri.at[secili_index_edit, "Ödeme Şekli"] in ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"] else 0)
            para_birimi = st.selectbox("Para Birimi", ["EURO", "USD", "TL", "RUBLE"],
                                       index=["EURO", "USD", "TL", "RUBLE"].index(df_musteri.at[secili_index_edit, "Para Birimi"])
                                       if df_musteri.at[secili_index_edit, "Para Birimi"] in ["EURO", "USD", "TL", "RUBLE"] else 0)
            dt_secim = st.selectbox("DT Seçin", ["DT-1", "DT-2", "DT-3", "DT-4"],
                                    index=["DT-1", "DT-2", "DT-3", "DT-4"].index(df_musteri.at[secili_index_edit, "DT Seçimi"])
                                    if df_musteri.at[secili_index_edit, "DT Seçimi"] in ["DT-1", "DT-2", "DT-3", "DT-4"] else 0)
            guncelle = st.form_submit_button("Güncelle")

        if guncelle:
            df_musteri.at[secili_index_edit, "Müşteri Adı"] = name
            df_musteri.at[secili_index_edit, "Telefon"] = phone
            df_musteri.at[secili_index_edit, "E-posta"] = email
            df_musteri.at[secili_index_edit, "Adres"] = address
            df_musteri.at[secili_index_edit, "Ülke"] = ulke
            df_musteri.at[secili_index_edit, "Satış Temsilcisi"] = temsilci
            df_musteri.at[secili_index_edit, "Kategori"] = kategori
            df_musteri.at[secili_index_edit, "Durum"] = aktif_pasif
            df_musteri.at[secili_index_edit, "Vade (Gün)"] = vade_gun
            df_musteri.at[secili_index_edit, "Ödeme Şekli"] = odeme_sekli
            df_musteri.at[secili_index_edit, "Para Birimi"] = para_birimi
            df_musteri.at[secili_index_edit, "DT Seçimi"] = dt_secim
            update_excel()
            st.success("Müşteri bilgileri güncellendi!")
            st.rerun()
# --- GÖRÜŞME / ARAMA / ZİYARET ---
elif menu == "Görüşme / Arama / Ziyaret Kayıtları":
    # canlı okuma
    if os.path.exists("temp.xlsx"):
        try:
            df_musteri = pd.read_excel("temp.xlsx", sheet_name="Sayfa1")
        except:
            df_musteri = pd.DataFrame(columns=["Müşteri Adı"])
        try:
            df_kayit = pd.read_excel("temp.xlsx", sheet_name="Kayıtlar")
        except:
            df_kayit = pd.DataFrame(columns=["Müşteri Adı","Tarih","Tip","Açıklama"])

    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Görüşme / Arama / Ziyaret Kayıtları</h2>", unsafe_allow_html=True)
    musteri_listesi = [m for m in df_musteri["Müşteri Adı"].dropna().unique() if isinstance(m, str) and m.strip() != ""]
    musteri_options = [""] + sorted(musteri_listesi)

    st.subheader("Kayıt Ekranı")
    secim = st.radio("Lütfen işlem seçin:", ["Yeni Kayıt", "Eski Kayıt", "Tarih Aralığı ile Kayıtlar"])

    # === Yeni Kayıt ===
    if secim == "Yeni Kayıt":
        with st.form("add_kayit"):
            musteri_sec = st.selectbox("Müşteri Seç", musteri_options, index=0)
            tarih = st.date_input("Tarih", value=datetime.date.today(), format="DD/MM/YYYY")
            tip = st.selectbox("Tip", ["Arama", "Görüşme", "Ziyaret"])
            aciklama = st.text_area("Açıklama")
            submitted = st.form_submit_button("Kaydet")

            if submitted:
                if not musteri_sec:
                    st.error("Lütfen bir müşteri seçiniz.")
                else:
                    new_row = {
                        "Müşteri Adı": musteri_sec,
                        "Tarih": str(tarih),   # string olarak kaydet
                        "Tip": tip,
                        "Açıklama": aciklama,
                    }
                    df_kayit = pd.concat([df_kayit, pd.DataFrame([new_row])], ignore_index=True)
                    update_excel()  # bu fonksiyon df_kayit → "Kayıtlar" sheet'ine yazmalı
                    st.success("Kayıt eklendi!")
                    st.rerun()

    # === Eski Kayıt ===
    elif secim == "Eski Kayıt":
        musteri_sec = st.selectbox("Müşteri Seç", musteri_options, index=0, key="eski_musteri")
        if musteri_sec:
            musteri_kayitlar = df_kayit[df_kayit["Müşteri Adı"] == musteri_sec].sort_values("Tarih", ascending=False)
            if not musteri_kayitlar.empty:
                tablo_goster = musteri_kayitlar.copy()
                if "Tarih" in tablo_goster.columns:
                    tablo_goster["Tarih"] = pd.to_datetime(tablo_goster["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
                st.dataframe(tablo_goster, use_container_width=True)
            else:
                st.info("Seçili müşteri için kayıt yok.")
        else:
            st.info("Lütfen müşteri seçin.")

    # === Tarih Aralığı ile Kayıtlar ===
    elif secim == "Tarih Aralığı ile Kayıtlar":
        col1, col2 = st.columns(2)
        with col1:
            baslangic = st.date_input("Başlangıç Tarihi", value=datetime.date.today() - datetime.timedelta(days=7), format="DD/MM/YYYY")
        with col2:
            bitis = st.date_input("Bitiş Tarihi", value=datetime.date.today(), format="DD/MM/YYYY")

        tarih_arasi = df_kayit[
            (pd.to_datetime(df_kayit["Tarih"], errors="coerce") >= pd.to_datetime(baslangic)) &
            (pd.to_datetime(df_kayit["Tarih"], errors="coerce") <= pd.to_datetime(bitis))
        ]

        if not tarih_arasi.empty:
            tablo_goster = tarih_arasi.copy()
            if "Tarih" in tablo_goster.columns:
                tablo_goster["Tarih"] = pd.to_datetime(tablo_goster["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
            st.dataframe(tablo_goster.sort_values("Tarih", ascending=False), use_container_width=True)
        else:
            st.info("Bu tarihler arasında kayıt yok.")

# --- FİYAT TEKLİFLERİ ---
elif menu == "Fiyat Teklifleri":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Fiyat Teklifleri</h2>", unsafe_allow_html=True)

    def otomatik_teklif_no():
        if df_teklif.empty or "Teklif No" not in df_teklif.columns:
            return "TKF-0001"
        mevcut_nolar = pd.to_numeric(
            df_teklif["Teklif No"].astype(str).str.extract(r'(\d+)$')[0], errors='coerce'
        ).dropna().astype(int)
        if mevcut_nolar.empty:
            return "TKF-0001"
        yeni_no = max(mevcut_nolar) + 1
        return f"TKF-{yeni_no:04d}"

    # --- Açık Teklifler ---
    st.subheader("Açık Pozisyondaki Teklifler Listesi")
    teklif_goster = df_teklif.copy()
    if not teklif_goster.empty and "Tarih" in teklif_goster.columns:
        teklif_goster["Tarih"] = pd.to_datetime(teklif_goster["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
    acik_teklifler = (
        teklif_goster[teklif_goster["Durum"] == "Açık"].sort_values(by=["Müşteri Adı", "Teklif No"])
        if "Durum" in teklif_goster.columns else pd.DataFrame()
    )
    acik_teklif_sayi = len(acik_teklifler)
    try:
        toplam_teklif = pd.to_numeric(acik_teklifler["Tutar"], errors="coerce").sum()
    except Exception:
        toplam_teklif = 0
    st.markdown(
        f"<div style='font-size:1.1em; color:#11998e; font-weight:bold;'>"
        f"Toplam: {toplam_teklif:,.2f} $ | Toplam Açık Teklif: {acik_teklif_sayi} adet"
        f"</div>", unsafe_allow_html=True
    )
    if not acik_teklifler.empty:
        st.dataframe(acik_teklifler[["Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama"]],
                     use_container_width=True)

    # --- İşlem seçimi ---
    st.markdown("##### Lütfen bir işlem seçin")
    col1, col2 = st.columns(2)
    with col1: yeni_teklif_buton = st.button("Yeni Teklif")
    with col2: eski_teklif_buton = st.button("Eski Teklif")

    if "teklif_view" not in st.session_state:
        st.session_state['teklif_view'] = None
    if yeni_teklif_buton: st.session_state['teklif_view'] = "yeni"
    if eski_teklif_buton: st.session_state['teklif_view'] = "eski"

    # --- YENİ TEKLİF ---
    if st.session_state['teklif_view'] == "yeni":
        musteri_list = [""] + sorted(df_musteri["Müşteri Adı"].dropna().unique().tolist())
        st.subheader("Yeni Teklif Ekle")
        with st.form("add_teklif"):
            musteri_sec = st.selectbox("Müşteri Seç", musteri_list, key="yeni_teklif_musteri")
            tarih = st.date_input("Tarih", value=datetime.date.today(), format="DD/MM/YYYY")
            teklif_no = st.text_input("Teklif No", value=otomatik_teklif_no())
            tutar = st.text_input("Tutar ($)")
            urun = st.text_input("Ürün/Hizmet")
            aciklama = st.text_area("Açıklama")
            durum = st.selectbox("Durum", ["Açık", "Sonuçlandı", "Beklemede"])
            pdf_file = st.file_uploader("Teklif PDF", type="pdf")
            submitted = st.form_submit_button("Kaydet")

            if submitted:
                if not teklif_no.strip():
                    st.error("Teklif No boş olamaz!")
                elif not musteri_sec:
                    st.error("Lütfen müşteri seçiniz!")
                elif teklif_no in df_teklif["Teklif No"].astype(str).values:
                    st.error("Bu Teklif No zaten mevcut!")
                else:
                    pdf_link = ""
                    if pdf_file:
                        try:
                            temiz_musteri = "".join(x if x.isalnum() else "_" for x in str(musteri_sec))
                            temiz_tarih = str(tarih).replace("-", "")
                            pdf_filename = f"{temiz_musteri}__{temiz_tarih}__{teklif_no}.pdf"
                            pdf_link = upload_bytes_to_folder(FIYAT_TEKLIFI_ID, pdf_filename, pdf_file.getvalue())
                        except Exception as e:
                            st.warning(f"PDF yüklenemedi: {e}")

                    new_row = {
                        "Müşteri Adı": musteri_sec,
                        "Tarih": str(tarih),   # string olarak kaydet
                        "Teklif No": teklif_no,
                        "Tutar": tutar,
                        "Ürün/Hizmet": urun,
                        "Açıklama": aciklama,
                        "Durum": durum,
                        "PDF": pdf_link
                    }
                    df_teklif = pd.concat([df_teklif, pd.DataFrame([new_row])], ignore_index=True)
                    update_excel()
                    st.success("Teklif eklendi!")
                    st.session_state['teklif_view'] = None
                    st.rerun()

    # --- ESKİ TEKLİFLER ---
    if st.session_state['teklif_view'] == "eski":
        st.subheader("Eski Teklifler Listesi")
        eski_teklif_musteriler = [""] + sorted(df_teklif["Müşteri Adı"].dropna().unique().tolist())
        secili_musteri = st.selectbox("Müşteri Seçiniz", eski_teklif_musteriler, key="eski_teklif_musteri_sec")

        if secili_musteri:
            teklifler_bu_musteri = df_teklif[df_teklif["Müşteri Adı"] == secili_musteri].sort_values(by="Tarih", ascending=False)
            if teklifler_bu_musteri.empty:
                st.info("Bu müşteriye ait teklif kaydı yok.")
            else:
                teklif_index = st.selectbox(
                    "Teklif Seçiniz",
                    teklifler_bu_musteri.index,
                    format_func=lambda i: f"{teklifler_bu_musteri.at[i, 'Teklif No']} | "
                                          f"{pd.to_datetime(teklifler_bu_musteri.at[i, 'Tarih'], errors='coerce').date()}"
                )
                secilen_teklif = teklifler_bu_musteri.loc[teklif_index]
                if secilen_teklif.get("PDF", ""):
                    st.markdown(f"**Teklif PDF:** [{secilen_teklif['Teklif No']}]({secilen_teklif['PDF']})", unsafe_allow_html=True)
                else:
                    st.info("PDF bulunamadı.")
                st.dataframe(pd.DataFrame([secilen_teklif]), use_container_width=True)

# --- PROFORMA TAKİBİ ---
elif menu == "Proforma Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Proforma Takibi</h2>", unsafe_allow_html=True)

    for col in ["Vade (gün)", "Sipariş Formu", "Durum", "PDF", "Sevk Durumu", "Ülke", "Satış Temsilcisi", "Ödeme Şekli"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""

    # Bekleyenleri özetle
    beklemede_kayitlar = df_proforma[df_proforma["Durum"] == "Beklemede"]
    if not beklemede_kayitlar.empty:
        st.subheader("Bekleyen Proformalar")
        st.dataframe(
            beklemede_kayitlar[["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Durum", "Vade (gün)", "Sevk Durumu"]],
            use_container_width=True
        )

    musteri_list = sorted([x for x in df_musteri["Müşteri Adı"].dropna().unique() if isinstance(x,str) and x.strip()!=""]) if not df_musteri.empty else []
    musteri_sec = st.selectbox("Müşteri Seç", [""] + musteri_list)

    if musteri_sec:
        st.write("Proforma işlemi seçin:")
        islem = st.radio("", ["Yeni Kayıt", "Eski Kayıt"], horizontal=True)

        # --- YENİ KAYIT ---
        if islem == "Yeni Kayıt":
            musteri_info = df_musteri[df_musteri["Müşteri Adı"] == musteri_sec]
            default_ulke = musteri_info["Ülke"].values[0] if not musteri_info.empty else ""
            default_temsilci = musteri_info["Satış Temsilcisi"].values[0] if not musteri_info.empty else ""
            default_odeme = musteri_info["Ödeme Şekli"].values[0] if not musteri_info.empty else ""

            with st.form("add_proforma"):
                tarih = st.date_input("Tarih", value=datetime.date.today())
                proforma_no = st.text_input("Proforma No")
                tutar = st.text_input("Tutar ($)")
                vade_gun = st.text_input("Vade (gün)")
                ulke = st.text_input("Ülke", value=default_ulke, disabled=True)
                temsilci = st.text_input("Satış Temsilcisi", value=default_temsilci, disabled=True)
                odeme = st.text_input("Ödeme Şekli", value=default_odeme, disabled=True)
                aciklama = st.text_area("Açıklama")
                durum = st.selectbox("Durum", ["Beklemede", "İptal", "Faturası Kesildi", "Siparişe Dönüştü"])
                pdf_file = st.file_uploader("Proforma PDF", type="pdf")
                submitted = st.form_submit_button("Kaydet")

                if submitted:
                    if not proforma_no.strip() or not vade_gun.strip():
                        st.error("Proforma No ve Vade (gün) boş olamaz!")
                    else:
                        pdf_link = ""
                        if pdf_file:
                            try:
                                pdf_filename = f"{musteri_sec}_{tarih}_{proforma_no}.pdf"
                                pdf_link = upload_bytes_to_folder(PROFORMA_PDF_FOLDER_ID, pdf_filename, pdf_file.getvalue())
                            except Exception as e:
                                st.warning(f"PDF yüklenemedi: {e}")

                        new_row = {
                            "Müşteri Adı": musteri_sec,
                            "Tarih": str(tarih),
                            "Proforma No": proforma_no,
                            "Tutar": tutar,
                            "Vade (gün)": vade_gun,
                            "Ülke": default_ulke,
                            "Satış Temsilcisi": default_temsilci,
                            "Ödeme Şekli": default_odeme,
                            "Açıklama": aciklama,
                            "Durum": durum,
                            "PDF": pdf_link,
                            "Sipariş Formu": "",
                            "Sevk Durumu": ""
                        }
                        df_proforma = pd.concat([df_proforma, pd.DataFrame([new_row])], ignore_index=True)
                        update_excel()
                        st.success("Proforma eklendi!")
                        st.rerun()

        # --- ESKİ KAYIT ---
        elif islem == "Eski Kayıt":
            eski_kayitlar = df_proforma[df_proforma["Müşteri Adı"] == musteri_sec]
            if eski_kayitlar.empty:
                st.info("Bu müşteriye ait proforma kaydı yok.")
            else:
                st.dataframe(
                    eski_kayitlar[["Müşteri Adı","Proforma No","Tarih","Tutar","Durum","Vade (gün)","Sevk Durumu"]],
                    use_container_width=True
                )
                sec_index = st.selectbox(
                    "Proforma Seç",
                    eski_kayitlar.index,
                    format_func=lambda i: f"{eski_kayitlar.at[i, 'Proforma No']} | {pd.to_datetime(eski_kayitlar.at[i, 'Tarih'], errors='coerce').date()}"
                )

                if sec_index is not None:
                    kayit = eski_kayitlar.loc[sec_index]
                    if kayit["PDF"]:
                        st.markdown(f"**Proforma PDF:** [{kayit['Proforma No']}]({kayit['PDF']})", unsafe_allow_html=True)

                    with st.form(f"edit_proforma_{sec_index}"):
                        tarih_ = st.date_input("Tarih", value=pd.to_datetime(kayit["Tarih"], errors="coerce").date())
                        proforma_no_ = st.text_input("Proforma No", value=kayit["Proforma No"])
                        tutar_ = st.text_input("Tutar ($)", value=kayit["Tutar"])
                        vade_gun_ = st.text_input("Vade (gün)", value=str(kayit["Vade (gün)"]))
                        aciklama_ = st.text_area("Açıklama", value=kayit["Açıklama"])
                        durum_ = st.selectbox("Durum",
                            ["Beklemede", "Siparişe Dönüştü", "İptal", "Faturası Kesildi"],
                            index=["Beklemede","Siparişe Dönüştü","İptal","Faturası Kesildi"].index(kayit["Durum"]) if kayit["Durum"] in ["Beklemede","Siparişe Dönüştü","İptal","Faturası Kesildi"] else 0
                        )
                        guncelle = st.form_submit_button("Güncelle")

                    if guncelle:
                        df_proforma.at[sec_index, "Tarih"] = str(tarih_)
                        df_proforma.at[sec_index, "Proforma No"] = proforma_no_
                        df_proforma.at[sec_index, "Tutar"] = tutar_
                        df_proforma.at[sec_index, "Vade (gün)"] = vade_gun_
                        df_proforma.at[sec_index, "Açıklama"] = aciklama_
                        df_proforma.at[sec_index, "Durum"] = durum_
                        update_excel()
                        st.success("Proforma güncellendi!")
                        st.rerun()

                    if st.button("Seçili Proformayı Sil", key=f"sil_{sec_index}"):
                        df_proforma = df_proforma.drop(sec_index).reset_index(drop=True)
                        update_excel()
                        st.success("Kayıt silindi!")
                        st.rerun()

                    if durum_ == "Siparişe Dönüştü":
                        st.info("Sipariş formu yükleyin:")
                        siparis_formu_file = st.file_uploader("Sipariş Formu PDF", type="pdf", key=f"siparis_{sec_index}")
                        if st.button("Sipariş Formunu Kaydet", key=f"siparis_btn_{sec_index}"):
                            if siparis_formu_file is None:
                                st.error("Sipariş formu yüklenmedi.")
                            else:
                                try:
                                    siparis_formu_fname = f"{musteri_sec}_{proforma_no_}_SiparisFormu_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                                    siparis_formu_url = upload_bytes_to_folder(SIPARIS_FORMU_FOLDER_ID, siparis_formu_fname, siparis_formu_file.getvalue())
                                    df_proforma.at[sec_index, "Sipariş Formu"] = siparis_formu_url
                                    update_excel()
                                    st.success("Sipariş formu kaydedildi!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Form yüklenemedi: {e}")

# --- GÜNCEL SİPARİŞ DURUMU ---
elif menu == "Güncel Sipariş Durumu":
    st.header("Güncel Sipariş Durumu")

    # Gerekli kolonlar yoksa ekle
    for c in ["Sevk Durumu","Termin Tarihi"]:
        if c not in df_proforma.columns:
            df_proforma[c] = ""

    # ETA tablosu garanti olsun
    for c in ["Müşteri Adı","Proforma No","ETA Tarihi","Açıklama"]:
        if c not in df_eta.columns:
            df_eta[c] = ""

    # Sadece sevke gitmemiş siparişler
    siparisler = df_proforma[
        (df_proforma["Durum"] == "Siparişe Dönüştü") & (~df_proforma["Sevk Durumu"].isin(["Sevkedildi","Ulaşıldı"]))
    ].copy()

    for col in ["Termin Tarihi", "Sipariş Formu", "Ülke", "Satış Temsilcisi", "Ödeme Şekli", "Fatura No"]:
        if col not in siparisler.columns:
            siparisler[col] = ""

    siparisler["Termin Tarihi Order"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce")
    siparisler = siparisler.sort_values("Termin Tarihi Order", ascending=True)

    if siparisler.empty:
        st.info("Henüz sevk edilmeyi bekleyen sipariş yok.")
    else:
        # Tarih formatlarını düzelt
        siparisler["Tarih"] = pd.to_datetime(siparisler["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
        siparisler["Termin Tarihi"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")

        tablo = siparisler[["Tarih","Müşteri Adı","Termin Tarihi","Ülke","Satış Temsilcisi","Ödeme Şekli","Proforma No","Tutar","Açıklama"]]
        st.markdown("<h4 style='color:#219A41; font-weight:bold;'>Tüm Siparişe Dönüşenler</h4>", unsafe_allow_html=True)
        st.dataframe(tablo, use_container_width=True)

        # --- Termin Tarihi Güncelle ---
        st.markdown("#### Termin Tarihi Güncelle")
        sec_index = st.selectbox(
            "Termin Tarihi Girilecek Siparişi Seçin",
            options=siparisler.index,
            format_func=lambda i: f"{siparisler.at[i,'Müşteri Adı']} - {siparisler.at[i,'Proforma No']}"
        )
        mevcut_termin = df_proforma.at[sec_index, "Termin Tarihi"] if "Termin Tarihi" in df_proforma.columns else ""
        try:
            default_termin = pd.to_datetime(mevcut_termin, errors="coerce")
            default_termin = datetime.date.today() if pd.isnull(default_termin) else default_termin.date()
        except Exception:
            default_termin = datetime.date.today()

        yeni_termin = st.date_input("Termin Tarihi", value=default_termin, key="termin_input")
        if st.button("Termin Tarihini Kaydet"):
            df_proforma.at[sec_index, "Termin Tarihi"] = str(yeni_termin)
            update_excel()
            st.success("Termin tarihi kaydedildi!")
            st.rerun()

        # --- Siparişi Sevk Et ---
        st.markdown("#### Sipariş Sevk Et")
        sevk_sec_index = st.selectbox(
            "Sevk Edilecek Siparişi Seçin",
            options=siparisler.index,
            format_func=lambda i: f"{siparisler.at[i,'Müşteri Adı']} - {siparisler.at[i,'Proforma No']}",
            key="sevk_sec"
        )
        if st.button("Sipariş Sevkedildi (ETA Takibine Gönder)"):
            yeni_eta = {
                "Müşteri Adı": siparisler.at[sevk_sec_index, "Müşteri Adı"],
                "Proforma No": siparisler.at[sevk_sec_index, "Proforma No"],
                "ETA Tarihi": "",
                "Açıklama": siparisler.at[sevk_sec_index, "Açıklama"]
            }
            df_eta = pd.concat([df_eta, pd.DataFrame([yeni_eta])], ignore_index=True)
            df_proforma.at[sevk_sec_index, "Sevk Durumu"] = "Sevkedildi"
            update_excel()
            st.success("Sipariş sevkedildi ve ETA takibine gönderildi!")
            st.rerun()

        # --- Beklemeye Al ---
        st.markdown("#### Siparişi Beklemeye Al (Geri Çağır)")
        geri_index = st.selectbox(
            "Beklemeye Alınacak Siparişi Seçin",
            options=siparisler.index,
            format_func=lambda i: f"{siparisler.at[i,'Müşteri Adı']} - {siparisler.at[i,'Proforma No']}",
            key="geri_sec"
        )
        if st.button("Siparişi Beklemeye Al / Geri Çağır"):
            df_proforma.at[geri_index, "Durum"] = "Beklemede"
            df_proforma.at[geri_index, "Sevk Durumu"] = ""
            df_proforma.at[geri_index, "Termin Tarihi"] = "Beklemede"
            update_excel()
            st.success("Sipariş tekrar bekleyen proformalar listesine alındı!")
            st.rerun()

        # --- Tıklanabilir Linkler ---
        st.markdown("#### Tıklanabilir Proforma ve Sipariş Formu Linkleri")
        link_rows = []
        for i, row in siparisler.iterrows():
            links = []
            if pd.notnull(row.get("PDF","")) and row.get("PDF",""):
                links.append(f"<a href='{row['PDF']}' target='_blank'>Proforma PDF ({row['Proforma No']})</a>")
            if pd.notnull(row.get("Sipariş Formu","")) and row.get("Sipariş Formu",""):
                fname = f"{row['Müşteri Adı']}__{row['Proforma No']}__{row.get('Fatura No', '')}"
                
# --- FATURA & İHRACAT EVRAKLARI ---
elif menu == "Fatura & İhracat Evrakları":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Fatura & İhracat Evrakları</h2>", unsafe_allow_html=True)

    for col in ["Proforma No","Vade (gün)","Vade Tarihi","Ülke","Satış Temsilcisi","Ödeme Şekli",
                "Commercial Invoice","Sağlık Sertifikası","Packing List","Konşimento","İhracat Beyannamesi",
                "Fatura PDF","Sipariş Formu","Yük Resimleri","EK Belgeler","Ödendi","Ödeme Kanıtı"]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col not in ["Ödendi"] else False

    musteri_secenek = sorted(df_proforma["Müşteri Adı"].dropna().unique().tolist()) if not df_proforma.empty else []
    secilen_musteri = st.selectbox("Müşteri Seç", [""] + musteri_secenek)
    secilen_proformalar = df_proforma[df_proforma["Müşteri Adı"] == secilen_musteri] if secilen_musteri else pd.DataFrame()
    proforma_no_sec = st.selectbox("Proforma No Seç", [""] + secilen_proformalar["Proforma No"].astype(str).tolist()) if not secilen_proformalar.empty else st.selectbox("Proforma No Seç", [""])

    musteri_info = df_musteri[df_musteri["Müşteri Adı"] == secilen_musteri]
    ulke = musteri_info["Ülke"].values[0] if not musteri_info.empty else ""
    temsilci = musteri_info["Satış Temsilcisi"].values[0] if not musteri_info.empty else ""
    odeme = musteri_info["Ödeme Şekli"].values[0] if not musteri_info.empty else ""

    onceki_evrak = df_evrak[(df_evrak["Müşteri Adı"] == secilen_musteri) & (df_evrak["Proforma No"] == proforma_no_sec)]

    def file_link_html(label, url):
        if url:
            return f'<div style="margin-top:-6px;"><a href="{url}" target="_blank" style="color:#219A41;">[Daha önce yüklenmiş {label}]</a></div>'
        else:
            return f'<div style="margin-top:-6px; color:#b00020; font-size:0.95em;">(Daha önce yüklenmemiş)</div>'

    evrak_tipleri = [
        ("Commercial Invoice", "Commercial Invoice PDF"),
        ("Sağlık Sertifikası", "Sağlık Sertifikası PDF"),
        ("Packing List", "Packing List PDF"),
        ("Konşimento", "Konşimento PDF"),
        ("İhracat Beyannamesi", "İhracat Beyannamesi PDF"),
    ]

    with st.form("add_evrak"):
        fatura_no = st.text_input("Fatura No")
        fatura_tarih = st.date_input("Fatura Tarihi", value=datetime.date.today())
        tutar = st.text_input("Fatura Tutarı ($)")

        vade_gun = ""
        vade_tarihi = ""
        if secilen_musteri and proforma_no_sec:
            proforma_kayit = df_proforma[(df_proforma["Müşteri Adı"] == secilen_musteri) & (df_proforma["Proforma No"] == proforma_no_sec)]
            if not proforma_kayit.empty:
                vade_gun = proforma_kayit.iloc[0].get("Vade (gün)", "")
                try:
                    vade_gun_int = int(str(vade_gun).strip())
                    vade_tarihi = fatura_tarih + datetime.timedelta(days=vade_gun_int)
                except:
                    vade_tarihi = ""
        st.text_input("Vade (gün)", value=vade_gun, key="vade_gun", disabled=True)
        st.date_input("Vade Tarihi", value=vade_tarihi if vade_tarihi else fatura_tarih, key="vade_tarihi", disabled=True)
        st.text_input("Ülke", value=ulke, disabled=True)
        st.text_input("Satış Temsilcisi", value=temsilci, disabled=True)
        st.text_input("Ödeme Şekli", value=odeme, disabled=True)

        uploaded_files = {}
        for col, label in evrak_tipleri:
            uploaded_files[col] = st.file_uploader(label, type="pdf", key=f"{col}_upload")
            prev_url = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""
            st.markdown(file_link_html(label, prev_url), unsafe_allow_html=True)

        # Ek belgeler alanı
        yuk_resimleri = st.file_uploader("Yük Resimleri (PDF/ZIP)", type=["pdf","zip"], key="yuk_resim_upload")
        ek_belgeler = st.file_uploader("EK Belgeler (PDF/ZIP)", type=["pdf","zip"], key="ek_belge_upload")

        submitted = st.form_submit_button("Kaydet")
        if submitted:
            if not fatura_no.strip() or not tutar.strip() or not proforma_no_sec:
                st.error("Fatura No, Tutar ve Proforma No boş olamaz!")
            else:
                file_urls = {}
                for col, label in evrak_tipleri:
                    uploaded_file = uploaded_files[col]
                    if uploaded_file:
                        file_name = f"{secilen_musteri}__{proforma_no_sec}__{col}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                        file_urls[col] = upload_bytes_to_folder(EVRAK_KLASOR_ID, file_name, uploaded_file.getvalue())
                    else:
                        file_urls[col] = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""

                # Yük resimleri ve ek belgeler
                yuk_url = ""
                ek_url = ""
                if yuk_resimleri:
                    yuk_name = f"{secilen_musteri}__{proforma_no_sec}__YukResimleri_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                    yuk_url = upload_bytes_to_folder(EVRAK_KLASOR_ID, yuk_name, yuk_resimleri.getvalue())
                if ek_belgeler:
                    ek_name = f"{secilen_musteri}__{proforma_no_sec}__EkBelgeler_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                    ek_url = upload_bytes_to_folder(EVRAK_KLASOR_ID, ek_name, ek_belgeler.getvalue())

                new_row = {
                    "Müşteri Adı": secilen_musteri, "Proforma No": proforma_no_sec, "Fatura No": fatura_no,
                    "Fatura Tarihi": str(fatura_tarih), "Tutar": tutar,
                    "Vade (gün)": vade_gun, "Vade Tarihi": str(vade_tarihi) if vade_tarihi else "",
                    "Ülke": ulke, "Satış Temsilcisi": temsilci, "Ödeme Şekli": odeme,
                    "Commercial Invoice": file_urls.get("Commercial Invoice",""),
                    "Sağlık Sertifikası": file_urls.get("Sağlık Sertifikası",""),
                    "Packing List": file_urls.get("Packing List",""),
                    "Konşimento": file_urls.get("Konşimento",""),
                    "İhracat Beyannamesi": file_urls.get("İhracat Beyannamesi",""),
                    "Fatura PDF": "", "Sipariş Formu": "", 
                    "Yük Resimleri": yuk_url, "EK Belgeler": ek_url, 
                    "Ödendi": False
                }

                # Eğer aynı müşteri+proforma daha önce kaydedilmişse güncelle
                if not onceki_evrak.empty:
                    idx = onceki_evrak.index[0]
                    for k,v in new_row.items():
                        df_evrak.at[idx,k] = v
                else:
                    df_evrak = pd.concat([df_evrak, pd.DataFrame([new_row])], ignore_index=True)

                update_excel()
                st.success("Evrak kaydedildi / güncellendi!")
                st.rerun()

# --- VADE TAKİBİ ---
elif menu == "Vade Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Vade Takibi</h2>", unsafe_allow_html=True)

    ROOT_EXPORT_FOLDER_ID = EVRAK_KLASOR_ID

    def get_or_create_customer_folder(customer_name: str, parent_folder_id: str) -> str:
        return get_or_create_child_folder(safe_name(customer_name, 100), parent_folder_id)

    for col in ["Proforma No","Vade (gün)","Ödendi","Ülke","Satış Temsilcisi","Ödeme Şekli",
                "Vade Tarihi","Fatura No","Müşteri Adı","Ödeme Kanıtı"]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col != "Ödendi" else False

    df_evrak["Ödendi"] = df_evrak["Ödendi"].fillna(False).astype(bool)
    df_evrak["Vade Tarihi"] = pd.to_datetime(df_evrak["Vade Tarihi"], errors="coerce")
    today = pd.to_datetime(datetime.date.today())
    vade_df = df_evrak[df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])].reset_index()

     # Sadece ödenmemiş ve vadeli kayıtlar
    vade_df = df_evrak[df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])].reset_index()

    if vade_df.empty:
        st.info("Açık vade kaydı yok.")
    else:
        # Her satır için bilgi + ödeme kanıtı yükleme + Ödendi checkbox
        for i, row in vade_df.iterrows():
            kalan = (row["Vade Tarihi"] - today).days
            mesaj = (
                f"{row['Müşteri Adı']} | {row.get('Ülke','')} | {row.get('Satış Temsilcisi','')} "
                f"| Proforma No: {row.get('Proforma No','')} | Fatura No: {row['Fatura No']} "
                f"| Vade Tarihi: {row['Vade Tarihi'].date()} | Ödeme: {row.get('Ödeme Şekli','')}"
            )

            box = st.container(border=True)
            with box:
                if kalan == 1:
                    st.error(f"{mesaj} | **YARIN VADE DOLUYOR!**")
                elif kalan < 0:
                    st.warning(f"{mesaj} | **{abs(kalan)} gün GECİKTİ!**")
                else:
                    st.info(f"{mesaj} | {kalan} gün kaldı.")

                # Ödeme kanıtı uploader (çoklu format)
                kanit_file = st.file_uploader(
                    "Ödeme Kanıtı (PDF/JPG/PNG/JPEG/WEBP)",
                    type=["pdf", "jpg", "jpeg", "png", "webp"],
                    key=f"kanit_{i}"
                )

                # Daha önce yüklenmiş link varsa göster
                prev_link = row.get("Ödeme Kanıtı", "")
                if prev_link:
                    st.markdown(f"[Önceden yüklenmiş ödeme kanıtı]({prev_link})", unsafe_allow_html=True)

                tick = st.checkbox(
                    f"Ödendi olarak işaretle → {row['Müşteri Adı']} - Proforma No: {row.get('Proforma No','')} - Fatura No: {row['Fatura No']}",
                    key=f"odendi_{i}"
                )

                if tick:
                    # Kanıt zorunlu
                    if kanit_file is None and not prev_link:
                        st.error("Lütfen önce **Ödeme Kanıtı** dosyası yükleyin (PDF/JPG/PNG…).")
                    else:
                        # Eğer yeni dosya geldiyse Drive'a yükle
                        odeme_kaniti_url = prev_link
                        if kanit_file is not None:
                            if not ROOT_EXPORT_FOLDER_ID:
                                st.error("Ana klasör ID tanımlı değil; yükleme iptal edildi.")
                                st.stop()

                            cust_folder_id = get_or_create_customer_folder(row["Müşteri Adı"], ROOT_EXPORT_FOLDER_ID)
                            if not cust_folder_id:
                                st.error("Müşteri klasörü oluşturulamadı; yükleme iptal edildi.")
                                st.stop()

                            # Müşteri altında 'Odeme_Kanitlari' alt klasörü
                            kanit_folder_id = get_or_create_folder_by_name("Odeme_Kanitlari", cust_folder_id)
                            if not kanit_folder_id:
                                st.error("Ödeme kanıtı klasörü oluşturulamadı; yükleme iptal edildi.")
                                st.stop()

                            # Dosyayı geçici kaydet ve yükle
                            suffix = os.path.splitext(kanit_file.name)[1].lower() or ".pdf"
                            ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                            fname = safe_name(f"OdemeKaniti__{row['Müşteri Adı']}__{row.get('Proforma No','')}__{row['Fatura No']}__{ts}") + suffix

                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
                                fp.write(kanit_file.read())
                                temp_path = fp.name

                            meta = {
                                'title': fname,
                                'parents': [{'id': kanit_folder_id}],
                            }
                            gfile = drive.CreateFile(meta)
                            gfile.SetContentFile(temp_path)
                            try:
                                # supportsAllDrives => Shared Drive desteği
                                gfile.Upload(param={'supportsAllDrives': True})
                                odeme_kaniti_url = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                            except Exception as e:
                                st.error(f"Ödeme kanıtı yüklenirken hata: {e}")
                            finally:
                                try: os.remove(temp_path)
                                except: pass

                        # Kayıt güncelle: kanıt linki + Ödendi = True
                        df_evrak.at[row['index'], "Ödeme Kanıtı"] = odeme_kaniti_url
                        df_evrak.at[row['index'], "Ödendi"] = True
                        update_excel()
                        st.success("Kayıt 'Ödendi' olarak işaretlendi ve ödeme kanıtı kaydedildi.")
                        st.rerun()

        st.markdown("#### Açık Vade Kayıtları")
        st.dataframe(
            df_evrak[
                df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])
            ][["Müşteri Adı", "Ülke", "Satış Temsilcisi", "Ödeme Şekli",
               "Proforma No", "Fatura No", "Fatura Tarihi", "Vade (gün)", "Vade Tarihi", "Tutar"]],
            use_container_width=True
        )

# --- ETA TAKİBİ ---
elif menu == "ETA Takibi":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>ETA Takibi</h2>", unsafe_allow_html=True)

    # Gerekli kolonlar
    for col in ["Sevk Durumu", "Proforma No", "Sevk Tarihi", "Ulaşma Tarihi"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""
    for col in ["Müşteri Adı", "Proforma No", "ETA Tarihi", "Açıklama"]:
        if col not in df_eta.columns:
            df_eta[col] = ""

    # Proforma bazlı "Yükleme Resimleri" klasörü (EVRAK_KLASOR_ID altında)
    def get_proforma_yukleme_folder(proforma_no: str) -> str:
        if not EVRAK_KLASOR_ID:
            return ""
        proforma_folder = get_or_create_child_folder(safe_name(proforma_no, 100), EVRAK_KLASOR_ID)
        if not proforma_folder:
            return ""
        return get_or_create_child_folder("Yükleme Resimleri", proforma_folder)

    # ==== SEVKEDİLENLER (Yolda) ====
    sevkedilenler = df_proforma[df_proforma["Sevk Durumu"] == "Sevkedildi"].copy()
    if sevkedilenler.empty:
        st.info("Sevkedilmiş sipariş bulunmuyor.")
    else:
        secenekler = sevkedilenler[["Müşteri Adı", "Proforma No"]].drop_duplicates().copy()
        secenekler["sec_text"] = secenekler["Müşteri Adı"] + " - " + secenekler["Proforma No"]
        selected = st.selectbox("Sevkedilen Sipariş Seç", secenekler["sec_text"])
        selected_row = secenekler[secenekler["sec_text"] == selected].iloc[0]
        sec_musteri = selected_row["Müşteri Adı"]
        sec_proforma = selected_row["Proforma No"]

        # --- YÜKLEME FOTOĞRAFLARI ---
        st.markdown("#### 🖼️ Yükleme Fotoğrafları (Proforma bazlı)")
        hedef_klasor = get_proforma_yukleme_folder(sec_proforma)
        if not hedef_klasor:
            st.error("Proforma klasörü / 'Yükleme Resimleri' klasörü oluşturulamadı.")
        else:
            # Klasörü aç linki + gömülü görünüm
            st.markdown(f"[🔗 Klasörü yeni sekmede aç](https://drive.google.com/drive/folders/{hedef_klasor}?usp=sharing)")
            with st.expander("📂 Panelde klasörü görüntüle"):
                st.markdown(
                    f'<iframe src="https://drive.google.com/embeddedfolderview?id={hedef_klasor}#grid" '
                    f'width="100%" height="520" frameborder="0" style="border:1px solid #eee; border-radius:12px;"></iframe>',
                    unsafe_allow_html=True
                )

            # Mevcut dosya adlarını çek (duplike engelle)
            try:
                res = execute_with_retry(drive_svc.files().list(
                    q=f"'{hedef_klasor}' in parents and trashed = false",
                    fields="files(id,name)"
                ))
                mevcut_adlar = {f["name"] for f in res.get("files", [])}
            except Exception as e:
                mevcut_adlar = set()
                st.warning(f"Dosyalar listelenemedi: {e}")

            with st.expander("➕ Dosya Ekle (duplike isimleri atlar)"):
                files = st.file_uploader(
                    "Yüklenecek dosyaları seçin",
                    type=["pdf","jpg","jpeg","png","webp"],
                    accept_multiple_files=True,
                    key=f"yuk_resimleri_{sec_proforma}"
                )
                if files:
                    yuklenen, atlanan = 0, 0
                    for up in files:
                        base, ext = os.path.splitext(up.name)
                        fname = safe_name(base) + (ext if ext else "")
                        if fname in mevcut_adlar:
                            atlanan += 1
                            continue
                        try:
                            upload_bytes_to_folder(hedef_klasor, fname, up.getvalue())
                            yuklenen += 1
                            mevcut_adlar.add(fname)
                        except Exception as e:
                            st.error(f"{up.name} yüklenemedi: {e}")
                    if yuklenen:
                        st.success(f"{yuklenen} dosya yüklendi.")
                        if atlanan:
                            st.info(f"{atlanan} dosya aynı isimle bulunduğu için atlandı.")
                        st.rerun()
                    elif atlanan and not yuklenen:
                        st.warning("Tüm dosyalar klasörde zaten mevcut görünüyor (isimleri aynı).")

        st.markdown("---")

        # --- ETA Düzenleme ---
        filtre = (df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma)
        mevcut_eta = df_eta.loc[filtre, "ETA Tarihi"].values[0] if filtre.any() else ""
        mevcut_aciklama = df_eta.loc[filtre, "Açıklama"].values[0] if filtre.any() else ""
        mevcut_eta = pd.to_datetime(mevcut_eta, errors="coerce")
        varsayilan_eta = mevcut_eta.date() if not pd.isna(mevcut_eta) else datetime.date.today()

        # Form 1: Güncelle
        with st.form("edit_eta"):
            eta_tarih = st.date_input("ETA Tarihi", value=varsayilan_eta)
            aciklama = st.text_area("Açıklama", value=mevcut_aciklama)
            guncelle = st.form_submit_button("ETA'yı Kaydet/Güncelle")

        if guncelle:
            eta_value = pd.to_datetime(eta_tarih)
            if filtre.any():
                df_eta.loc[filtre, "ETA Tarihi"] = eta_value
                df_eta.loc[filtre, "Açıklama"] = aciklama
            else:
                df_eta = pd.concat([df_eta, pd.DataFrame([{
                    "Müşteri Adı": sec_musteri,
                    "Proforma No": sec_proforma,
                    "ETA Tarihi": eta_value,
                    "Açıklama": aciklama
                }])], ignore_index=True)
            update_excel()
            st.success("ETA kaydedildi/güncellendi!")
            st.rerun()

        # Form 2: Ulaştı
        with st.form("eta_ulasti"):
            ulasti = st.form_submit_button("Ulaştı")
        if ulasti:
            df_eta = df_eta[~((df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma))]
            idx = df_proforma[(df_proforma["Müşteri Adı"] == sec_musteri) & (df_proforma["Proforma No"] == sec_proforma)].index
            if len(idx) > 0:
                df_proforma.at[idx[0], "Sevk Durumu"] = "Ulaşıldı"
                df_proforma.at[idx[0], "Ulaşma Tarihi"] = pd.to_datetime(datetime.date.today())
            update_excel()
            st.success("Sipariş 'Ulaşıldı' olarak işaretlendi ve ETA takibinden çıkarıldı!")
            st.rerun()

        # Form 3: Geri Al
        with st.form("eta_geri_al"):
            geri_al = st.form_submit_button("Sevki Geri Al")
        if geri_al:
            df_eta = df_eta[~((df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma))]
            idx = df_proforma[(df_proforma["Müşteri Adı"] == sec_musteri) & (df_proforma["Proforma No"] == sec_proforma)].index
            if len(idx) > 0:
                df_proforma.at[idx[0], "Sevk Durumu"] = ""
            update_excel()
            st.success("Sevkiyat geri alındı! Sipariş tekrar Güncel Sipariş Durumu'na gönderildi.")
            st.rerun()

    # ==== ETA TAKİP LİSTESİ ====
    st.markdown("#### ETA Takip Listesi")
    for col in ["Proforma No", "ETA Tarihi"]:
        if col not in df_eta.columns:
            df_eta[col] = ""
    if not df_eta.empty:
        df_eta["ETA Tarihi"] = pd.to_datetime(df_eta["ETA Tarihi"], errors="coerce")
        today = pd.to_datetime(datetime.date.today())
        df_eta["Kalan Gün"] = (df_eta["ETA Tarihi"] - today).dt.days
        df_eta["Kalan Gün"] = df_eta["Kalan Gün"].astype("Int64")

        def highlight_days(val):
            if val == "" or pd.isna(val):
                return ''
            if val < 0:
                return 'background-color: #ffcccc;'  # kırmızı
            elif val <= 3:
                return 'background-color: #fff3cd;'  # turuncu
            else:
                return 'background-color: #d4edda;'  # yeşil
                
        df_eta["Kalan Gün"] = df_eta["Kalan Gün"].fillna("")
        tablo = df_eta[["Müşteri Adı", "Proforma No", "ETA Tarihi", "Kalan Gün", "Açıklama"]].copy()
        tablo = tablo.sort_values(["ETA Tarihi", "Müşteri Adı", "Proforma No"], ascending=[True, True, True])
        st.dataframe(tablo.style.applymap(highlight_days, subset=["Kalan Gün"]), use_container_width=True)

        st.markdown("##### ETA Kaydı Sil")
        silinecekler = df_eta.index.tolist()
        sil_sec = st.selectbox(
            "Silinecek Kaydı Seçin",
            options=silinecekler,
            format_func=lambda i: f"{df_eta.at[i, 'Müşteri Adı']} - {df_eta.at[i, 'Proforma No']}"
        )
        if st.button("KAYDI SİL"):
            df_eta = df_eta.drop(sil_sec).reset_index(drop=True)
            update_excel()
            st.success("Seçilen ETA kaydı silindi!")
            st.rerun()
    else:
        st.info("Henüz ETA kaydı yok.")

    # ==== ULAŞANLAR (TESLİM EDİLENLER) ====
    ulasanlar = df_proforma[df_proforma["Sevk Durumu"] == "Ulaşıldı"].copy()
    if not ulasanlar.empty:
        ulasanlar["sec_text"] = ulasanlar["Müşteri Adı"] + " - " + ulasanlar["Proforma No"]
        st.markdown("#### Teslim Edilen Siparişlerde İşlemler")
        selected_ulasan = st.selectbox("Sipariş Seçiniz", ulasanlar["sec_text"])
        row = ulasanlar[ulasanlar["sec_text"] == selected_ulasan].iloc[0]

        try:
            current_ulasma = pd.to_datetime(row.get("Ulaşma Tarihi", None)).date()
            if pd.isnull(current_ulasma) or str(current_ulasma) == "NaT":
                current_ulasma = datetime.date.today()
        except Exception:
            current_ulasma = datetime.date.today()

        new_ulasma_tarih = st.date_input("Ulaşma Tarihi", value=current_ulasma, key="ulasan_guncelle")
        if st.button("Ulaşma Tarihini Kaydet"):
            idx = df_proforma[
                (df_proforma["Müşteri Adı"] == row["Müşteri Adı"]) &
                (df_proforma["Proforma No"] == row["Proforma No"])
            ].index
            if len(idx) > 0:
                df_proforma.at[idx[0], "Ulaşma Tarihi"] = pd.to_datetime(new_ulasma_tarih)
                update_excel()
                st.success("Ulaşma Tarihi güncellendi!")
                st.rerun()

        st.markdown("---")
        with st.form("ulasan_geri_al_form"):
            st.markdown("##### 🔄 Ulaşan siparişi yeniden **Yolda Olanlar (ETA)** listesine al")
            yeni_eta = st.date_input("Yeni ETA (opsiyonel)", value=datetime.date.today() + datetime.timedelta(days=7))
            aciklama_geri = st.text_input("Açıklama (opsiyonel)", value="Geri alındı - tekrar yolda")
            onay = st.form_submit_button("Yola Geri Al")

        if onay:
            musteri = row["Müşteri Adı"]
            pno = row["Proforma No"]
            idx = df_proforma[(df_proforma["Müşteri Adı"] == musteri) & (df_proforma["Proforma No"] == pno)].index
            if len(idx) > 0:
                df_proforma.at[idx[0], "Sevk Durumu"] = "Sevkedildi"
                df_proforma.at[idx[0], "Ulaşma Tarihi"] = pd.NaT

            filtre_eta = (df_eta["Müşteri Adı"] == musteri) & (df_eta["Proforma No"] == pno)
            eta_deger = pd.to_datetime(yeni_eta) if yeni_eta else pd.NaT
            if filtre_eta.any():
                if yeni_eta:
                    df_eta.loc[filtre_eta, "ETA Tarihi"] = eta_deger
                if aciklama_geri:
                    df_eta.loc[filtre_eta, "Açıklama"] = aciklama_geri
            else:
                df_eta = pd.concat([df_eta, pd.DataFrame([{
                    "Müşteri Adı": musteri,
                    "Proforma No": pno,
                    "ETA Tarihi": eta_deger if yeni_eta else pd.NaT,
                    "Açıklama": aciklama_geri
                }])], ignore_index=True)

            update_excel()
            st.success("Sipariş, Ulaşanlar'dan geri alındı ve ETA listesine taşındı (Sevkedildi).")
            st.rerun()

        st.markdown("#### Ulaşan (Teslim Edilmiş) Siparişler")
        for col in ["Sevk Tarihi", "Termin Tarihi", "Ulaşma Tarihi"]:
            ulasanlar[col] = pd.to_datetime(ulasanlar[col], errors="coerce")
        ulasanlar["Gün Farkı"] = (ulasanlar["Ulaşma Tarihi"] - ulasanlar["Termin Tarihi"]).dt.days
        ulasanlar["Sevk Tarihi"] = ulasanlar["Sevk Tarihi"].dt.strftime("%d/%m/%Y")
        ulasanlar["Termin Tarihi"] = ulasanlar["Termin Tarihi"].dt.strftime("%d/%m/%Y")
        ulasanlar["Ulaşma Tarihi"] = ulasanlar["Ulaşma Tarihi"].dt.strftime("%d/%m/%Y")
        tablo = ulasanlar[["Müşteri Adı","Proforma No","Termin Tarihi","Sevk Tarihi","Ulaşma Tarihi","Gün Farkı","Tutar","Açıklama"]]
        st.dataframe(tablo, use_container_width=True)
    else:
        st.info("Henüz ulaşan sipariş yok.")


# --- FUAR MÜŞTERİ KAYITLARI ---
elif menu == "Fuar Müşteri Kayıtları":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold; text-align:center;'>🎫 FUAR MÜŞTERİ KAYITLARI</h2>", unsafe_allow_html=True)
    st.info("Fuarlarda müşteri görüşmelerinizi hızlıca buraya ekleyin. Hem yeni kayıt oluşturabilir hem de mevcut kayıtlarınızı düzenleyebilirsiniz.")

        fuar_isimleri = list(df_fuar["Fuar Adı"].dropna().unique())
    yeni_fuar = st.text_input("Yeni Fuar Adı Ekleyin (Eklemek istemiyorsanız boş bırakın):").strip()
    if yeni_fuar and yeni_fuar not in fuar_isimleri:
        fuar_isimleri.append(yeni_fuar)
        fuar_adi = yeni_fuar
    else:
        fuar_adi = st.selectbox("Fuar Seçiniz", ["- Fuar Seçiniz -"] + sorted(fuar_isimleri), index=0)
        fuar_adi = "" if fuar_adi == "- Fuar Seçiniz -" else fuar_adi

    secim = st.radio("İşlem Seçiniz:", ["Yeni Kayıt", "Eski Kayıt"])
    temsilci_listesi_local = temsilci_listesi  # yukarıdaki global liste

    # --- Yeni Kayıt ---
    if secim == "Yeni Kayıt":
        st.markdown("#### Yeni Fuar Müşteri Kaydı Ekle")
        with st.form("fuar_musteri_ekle"):
            musteri_adi = st.text_input("Müşteri Adı").strip()
            ulke = st.selectbox("Ülke Seçin", ulke_listesi)
            tel = st.text_input("Telefon").strip()
            email = st.text_input("E-mail").strip()
            temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi_local)
            aciklama = st.text_area("Açıklamalar")
            gorusme_kalitesi = st.slider("Görüşme Kalitesi (1=Kötü, 5=Çok İyi)", 1, 5, 3)
            tarih = st.date_input("Tarih", value=datetime.date.today())
            submitted = st.form_submit_button("Kaydet")

            if submitted:
                if not musteri_adi or not fuar_adi:
                    st.warning("Lütfen fuar seçin ve müşteri adı girin.")
                else:
                    new_row = {
                        "Fuar Adı": fuar_adi, "Müşteri Adı": musteri_adi, "Ülke": ulke, "Telefon": tel, "E-mail": email,
                        "Satış Temsilcisi": temsilci, "Açıklamalar": aciklama,
                        "Görüşme Kalitesi": int(gorusme_kalitesi), "Tarih": pd.to_datetime(tarih)
                    }
                    df_fuar = pd.concat([df_fuar, pd.DataFrame([new_row])], ignore_index=True)
                    update_excel()
                    st.success("Fuar müşterisi başarıyla eklendi!")
                    st.rerun()

    # --- Eski Kayıt ---
    else:
        kolonlar = ["Müşteri Adı","Ülke","Telefon","E-mail","Satış Temsilcisi","Açıklamalar","Görüşme Kalitesi","Tarih"]
         musteri_df = df_fuar[df_fuar["Fuar Adı"] == fuar_adi].copy()

        if musteri_df.empty:
            st.info("Bu fuara ait müşteri kaydı bulunamadı.")
        else:
            musteri_df["Tarih"] = pd.to_datetime(musteri_df["Tarih"], errors="coerce").dt.date
            st.markdown(f"<h4 style='color:#4776e6;'>{fuar_adi} Fuarındaki Müşteri Görüşme Kayıtları</h4>", unsafe_allow_html=True)

            secili_index = st.selectbox(
                "Düzenlemek/Silmek istediğiniz kaydı seçin:",
                musteri_df.index,
                format_func=lambda i: f"{musteri_df.at[i, 'Müşteri Adı']} ({musteri_df.at[i, 'Tarih']})"
            )

            with st.form("kayit_duzenle"):
                musteri_adi = st.text_input("Müşteri Adı", value=musteri_df.at[secili_index, "Müşteri Adı"])
                ulke = st.selectbox("Ülke", ulke_listesi,
                                    index=ulke_listesi.index(musteri_df.at[secili_index, "Ülke"]) if musteri_df.at[secili_index, "Ülke"] in ulke_listesi else 0)
                temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi_local,
                                        index=temsilci_listesi_local.index(musteri_df.at[secili_index, "Satış Temsilcisi"]) if musteri_df.at[secili_index, "Satış Temsilcisi"] in temsilci_listesi_local else 0)
                tel = st.text_input("Telefon", value=musteri_df.at[secili_index, "Telefon"])
                email = st.text_input("E-mail", value=musteri_df.at[secili_index, "E-mail"])
                aciklama = st.text_area("Açıklamalar", value=musteri_df.at[secili_index, "Açıklamalar"])

                gk_val = pd.to_numeric(musteri_df.at[secili_index, "Görüşme Kalitesi"], errors="coerce")
                gorusme_kalitesi = st.slider("Görüşme Kalitesi (1=Kötü, 5=Çok İyi)", 1, 5, int(gk_val) if not pd.isna(gk_val) else 3)

                tarih_val = musteri_df.at[secili_index, "Tarih"]
                tarih = st.date_input("Tarih", value=tarih_val if not pd.isna(tarih_val) else datetime.date.today())

                guncelle = st.form_submit_button("Kaydı Güncelle")
                sil = st.form_submit_button("Kaydı Sil")

            if guncelle:
                df_fuar.loc[secili_index, kolonlar] = [
                    musteri_adi, ulke, tel, email, temsilci, aciklama, int(gorusme_kalitesi), pd.to_datetime(tarih)
                ]
                update_excel()
                st.success("Kayıt güncellendi!")
                st.rerun()

            if sil:
                df_fuar_musteri = df_fuar_musteri.drop(secili_index).reset_index(drop=True)
                update_excel()
                st.success("Kayıt silindi!")
                st.rerun()

            st.dataframe(musteri_df[kolonlar], use_container_width=True)

# --- MEDYA ÇEKMECESİ ---
elif menu == "Medya Çekmecesi":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold;'>📂 Medya Çekmecesi</h2>", unsafe_allow_html=True)
    st.info("Google Drive’daki medya, ürün görselleri ve kalite evraklarına aşağıdaki sekmelerden ulaşabilirsiniz.")

    drive_folders = {
        "Genel Medya Klasörü": "1gFAaK-6v1e3346e-W0TsizOqSq43vHLY",
        "Ürün Görselleri": "18NNlmadm5NNFkI1Amzt_YMwB53j6AmbD",
        "Kalite Evrakları": "1pbArzYfA4Tp50zvdyTzSPF2ThrMWrGJc"
    }

    iframe_height = st.slider("📏 Görüntüleme Yüksekliği", min_value=300, max_value=1000, value=600, step=50)

    tabs = st.tabs(list(drive_folders.keys()))
    for (tab, (isim, folder_id)) in zip(tabs, drive_folders.items()):
        with tab:
            iframe_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
            st.markdown(
                f'<iframe src="{iframe_url}" width="100%" height="{iframe_height}" '
                f'frameborder="0" style="border:1px solid #eee; border-radius:12px; margin-top:10px;"></iframe>',
                unsafe_allow_html=True
            )
            st.markdown(f"[🔗 Google Drive’da Aç](https://drive.google.com/drive/folders/{folder_id}?usp=sharing)")
            st.info("Dosyaların üstüne çift tıklayarak yeni sekmede açabilir veya indirebilirsiniz.")

    st.warning("⚠️ Not: Klasörlerin paylaşım ayarlarının **'Bağlantıya sahip olan herkes görüntüleyebilir'** olduğundan emin olun.")

# --- SATIŞ PERFORMANSI ---
elif menu == "Satış Performansı":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>📈 Satış Performansı</h2>", unsafe_allow_html=True)

    # --- Akıllı sayı dönüştürücü ---
    def smart_to_num(x):
        if pd.isna(x):
            return 0.0
        s = str(x).strip()
        for sym in ["USD", "$", "€", "EUR", "₺", "TL", "tl", "Tl"]:
            s = s.replace(sym, "")
        s = s.replace("\u00A0", "").replace(" ", "")
        try:
            return float(s)
        except:
            pass
        if "," in s:  # Avrupa formatı
            try:
                return float(s.replace(".", "").replace(",", "."))
            except:
                pass
        return 0.0

    # --- Kolon güvenliği ---
    if "Tutar" not in df_evrak.columns:
        df_evrak["Tutar"] = 0
    date_col = "Fatura Tarihi" if "Fatura Tarihi" in df_evrak.columns else "Tarih"
    if date_col not in df_evrak.columns:
        df_evrak[date_col] = pd.NaT

    # --- Tip dönüşümleri ---
    df_evrak = df_evrak.copy()
    df_evrak["Tutar_num"] = df_evrak["Tutar"].apply(smart_to_num).fillna(0.0)
    df_evrak[date_col] = pd.to_datetime(df_evrak[date_col], errors="coerce")
    df_evrak = df_evrak[df_evrak[date_col].notna()]

    # --- Toplam fatura ---
    toplam_fatura = float(df_evrak["Tutar_num"].sum())
    st.markdown(f"<div style='font-size:1.3em; color:#185a9d; font-weight:bold;'>💵 Toplam Fatura Tutarı: {toplam_fatura:,.2f} USD</div>", unsafe_allow_html=True)

    # --- Tarih aralığı filtresi ---
    if not df_evrak.empty:
        min_ts = df_evrak[date_col].min()
        max_ts = df_evrak[date_col].max()
    else:
        min_ts = max_ts = pd.Timestamp.today()

    d1, d2 = st.date_input("📅 Tarih Aralığı", value=(min_ts.date(), max_ts.date()))
    start_ts = pd.to_datetime(d1)
    end_ts = pd.to_datetime(d2) + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)

    mask = df_evrak[date_col].between(start_ts, end_ts, inclusive="both")
    df_range = df_evrak[mask]

    # --- Aralık toplamı ---
    aralik_toplam = float(df_range["Tutar_num"].sum())
    st.markdown(f"<div style='font-size:1.2em; color:#f7971e; font-weight:bold;'>📊 {d1} - {d2} Arası Toplam: {aralik_toplam:,.2f} USD</div>", unsafe_allow_html=True)

    # --- Detay tablo ---
    show_cols = ["Müşteri Adı", "Fatura No", date_col, "Tutar"]
    show_cols = [c for c in show_cols if c in df_range.columns]
    if not df_range.empty:
        st.dataframe(df_range[show_cols].sort_values(by=date_col, ascending=False), use_container_width=True)
    else:
        st.info("Seçilen tarihlerde kayıt bulunamadı.")
