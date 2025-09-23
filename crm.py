import streamlit as st
import pandas as pd
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import io, os, datetime, tempfile, re, json
import numpy as np
import smtplib
from email.message import EmailMessage

st.set_page_config(page_title="ŞEKEROĞLU İHRACAT CRM", layout="wide")

# ==== KULLANICI GİRİŞİ SİSTEMİ ====
USERS = {
    "export1": "Seker12345!",
    "admin": "Seker12345!",
    "Boss": "Seker12345!",
}
if "user" not in st.session_state:
    st.session_state.user = None

def login_screen():
    st.title("ŞEKEROĞLU CRM - Giriş Ekranı")
    username = st.text_input("Kullanıcı Adı")
    password = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        if username in USERS and password == USERS[username]:
            st.session_state.user = username
            st.success("Giriş başarılı!")
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı.")

if not st.session_state.user:
    login_screen()
    st.stop()

# Sol menüde çıkış
if st.sidebar.button("Çıkış Yap"):
    st.session_state.user = None
    st.rerun()

# --- Referans listeler ---
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

# --- Sabitler ---
LOGO_FILE_ID     = "1DCxtSsAeR7Zfk2IQU0UMGmD0uTdNO1B3"
LOGO_LOCAL_NAME  = "logo1.png"
EXCEL_FILE_ID    = "1C8OpNAIRySkWYTI9jBaboV-Rq85UbVD9"
EVRAK_KLASOR_ID  = "14FTE1oSeIeJ6Y_7C0oQyZPKC8dK8hr1J"
FIYAT_TEKLIFI_ID = "1TNjwx-xhmlxNRI3ggCJA7jaCAu9Lt_65"

# --- Google Drive bağlantısı (Service Account + Streamlit secrets) ---
@st.cache_resource
def get_drive():
    """
    Streamlit Cloud'da: .streamlit/secrets.toml içinde [gcp_service_account] olmalı.
    Lokalde: secrets yoksa otomatik LocalWebserverAuth'a düşer (tarayıcıda OAuth açar).
    """
    gauth = GoogleAuth()

    try:
        if "gcp_service_account" in st.secrets:
            # Secrets içindeki JSON'u geçici dosyaya yaz
            sa = dict(st.secrets["gcp_service_account"])
            fd, tmp_path = tempfile.mkstemp(suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(sa, f)

            # PyDrive2'yi service account ile yetkilendir
            gauth.settings.update({
                "client_config_backend": "service",
                "service_config": {"client_json_file_path": tmp_path}
            })
            gauth.ServiceAuth()
        else:
            # Lokal geliştirme için geri dönüş (OAuth flow)
            gauth.LocalWebserverAuth()
    except Exception as e:
        st.error(f"Google Drive kimlik doğrulama hatası: {e}")
        raise

    return GoogleDrive(gauth)

drive = get_drive()

# --- Logo indir (yoksa) ---
if not os.path.exists(LOGO_LOCAL_NAME):
    try:
        logo_file = drive.CreateFile({'id': LOGO_FILE_ID})
        logo_file.GetContentFile(LOGO_LOCAL_NAME)
    except Exception as e:
        st.warning(f"Logo indirilemedi: {e}")

# --- Üst başlık ---
col1, col2 = st.columns([3, 7])
with col1:
    if os.path.exists(LOGO_LOCAL_NAME):
        st.image(LOGO_LOCAL_NAME, width=300)
with col2:
    st.markdown("""
        <style>.block-container { padding-top: 0.2rem !important; }</style>
        <div style="display:flex; flex-direction:column; align-items:flex-start; width:100%; margin-bottom:10px;">
            <h1 style="color: #219A41; font-weight: bold; font-size: 2.8em; letter-spacing:2px; margin:0; margin-top:-8px;">
                ŞEKEROĞLU İHRACAT CRM
            </h1>
        </div>
    """, unsafe_allow_html=True)

# --- Excel'i Drive'dan çek ---
downloaded = drive.CreateFile({'id': EXCEL_FILE_ID})
try:
    downloaded.FetchMetadata(fetch_all=True)
    downloaded.GetContentFile("temp.xlsx")
except Exception as e:
    st.error(f"CRM dosyası indirilemedi (EXCEL_FILE_ID yanlış olabilir ya da yetki yok): {e}")

# --- DataFrame’leri yükle (aynı sütun güvenliğiyle) ---
def _read_sheet(name, cols=None):
    try:
        df = pd.read_excel("temp.xlsx", sheet_name=name) if os.path.exists("temp.xlsx") else pd.DataFrame()
        if cols:
            for c in cols:
                if c not in df.columns:
                    df[c] = ""
        return df
    except Exception:
        return pd.DataFrame({c: [] for c in (cols or [])})

df_musteri = _read_sheet(0, ["Müşteri Adı","Telefon","E-posta","Adres","Ülke","Satış Temsilcisi","Kategori","Durum","Vade (Gün)","Ödeme Şekli"])
df_kayit   = _read_sheet("Kayıtlar", ["Müşteri Adı","Tarih","Tip","Açıklama"])
df_teklif  = _read_sheet("Teklifler", ["Müşteri Adı","Tarih","Teklif No","Tutar","Ürün/Hizmet","Açıklama","Durum","PDF"])
df_proforma= _read_sheet("Proformalar", ["Müşteri Adı","Tarih","Proforma No","Tutar","Açıklama","Durum","PDF","Sipariş Formu","Vade","Sevk Durumu"])
df_evrak   = _read_sheet("Evraklar", ["Müşteri Adı","Fatura No","Fatura Tarihi","Vade Tarihi","Tutar",
                                       "Commercial Invoice","Sağlık Sertifikası","Packing List","Konşimento","İhracat Beyannamesi",
                                       "Fatura PDF","Sipariş Formu","Yük Resimleri","EK Belgeler"])
df_eta     = _read_sheet("ETA", ["Müşteri Adı","Proforma No","ETA Tarihi","Açıklama"])
df_fuar_musteri = _read_sheet("FuarMusteri", ["Fuar Adı","Müşteri Adı","Ülke","Telefon","E-mail","Açıklamalar","Tarih"])

# --- Excel'i geri Drive’a yaz (tek fonksiyon) ---
def update_excel():
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_musteri.to_excel(writer, sheet_name="Sayfa1", index=False)
        df_kayit.to_excel(writer, sheet_name="Kayıtlar", index=False)
        df_teklif.to_excel(writer, sheet_name="Teklifler", index=False)
        df_proforma.to_excel(writer, sheet_name="Proformalar", index=False)
        df_evrak.to_excel(writer, sheet_name="Evraklar", index=False)
        df_eta.to_excel(writer, sheet_name="ETA", index=False)
        df_fuar_musteri.to_excel(writer, sheet_name="FuarMusteri", index=False)
    buffer.seek(0)

    with open("temp.xlsx", "wb") as f:
        f.write(buffer.read())

    try:
        uploaded = drive.CreateFile({'id': EXCEL_FILE_ID})
        uploaded.SetContentFile("temp.xlsx")
        uploaded.Upload()  # My Drive için yeterli
    except Exception as e:
        st.error(f"CRM dosyası Drive’a yüklenemedi: {e}")


# ========= ŞIK SIDEBAR MENÜ (RADIO + ANINDA STATE) =========

# 1) Menü grupları
MENU_GROUPS = [
    ("Yönetim", ["Genel Bakış", "Satış Analitiği"]),
    ("Müşteri & Satış", ["Yeni Cari Kaydı", "Müşteri Portföyü", "Etkileşim Günlüğü", "Teklif Yönetimi"]),
    ("Operasyon", ["Proforma Yönetimi", "Sipariş Operasyonları", "ETA İzleme"]),
    ("Finans", ["İhracat Evrakları", "Tahsilat Planı"]),
    ("Arşiv", ["Fuar Kayıtları", "İçerik Arşivi"]),

# 2) Tüm kullanıcılar için aynı menüler
allowed_menus = [(group, name) for group, entries in MENU_GROUPS for name in entries]

# 3) Etiketler ve haritalar
llabels = []
name_by_label = {}
label_by_name = {}
group_by_name = {}
for group, name in allowed_menus:
    label = f"{group} · {name}"
    labels.append(label)
    name_by_label[label] = name
    label_by_name[name] = label
    group_by_name[name] = group

# 4) Varsayılan state

if "menu_state" not in st.session_state:
    st.session_state.menu_state = allowed_menus[0][1]
elif st.session_state.menu_state not in label_by_name:
    st.session_state.menu_state = allowed_menus[0][1]

# 5) CSS (kurumsal görünümlü kartlar)
st.sidebar.markdown("""
<style>
section[data-testid="stSidebar"] { padding-top: .5rem; }
.sidebar-section-title {
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    margin: 18px 0 6px;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.65);
}

div[data-testid="stSidebar"] .stRadio > div { gap: 6px !important; }
div[data-testid="stSidebar"] .stRadio label {
    border-radius: 12px;
    padding: 10px 12px;
    margin-bottom: 2px;
    border: 1px solid rgba(255,255,255,0.15);
    display: flex; align-items: center;
    background: rgba(33, 154, 65, 0.08);
    transition: background .15s ease, border .15s ease;
}

div[data-testid="stSidebar"] .stRadio label span { font-weight: 600; color: #ffffff; }
div[data-testid="stSidebar"] .stRadio label:hover { background: rgba(33, 154, 65, 0.18); }
div[data-testid="stSidebar"] .stRadio [aria-checked="true"] {
    border: 1px solid #219A41;
    background: rgba(33, 154, 65, 0.32);
}

</style>
""", unsafe_allow_html=True)

# 6) Menü seçimleri
for group, entries in MENU_GROUPS:
    st.sidebar.markdown(f"<div class='sidebar-section-title'>{group}</div>", unsafe_allow_html=True)
    group_labels = [label_by_name[name] for name in entries]
    radio_key = f"menu_radio_{re.sub(r'[^0-9a-zA-Z]+', '_', group).lower()}"
    previous_selection = st.session_state.get(radio_key)

    if st.session_state.menu_state in entries:
        current_label = label_by_name[st.session_state.menu_state]
    elif previous_selection in group_labels:
        current_label = previous_selection
    else:
        current_label = group_labels[0]

    selected_label = st.sidebar.radio(
        "Menü",
        group_labels,
        index=group_labels.index(current_label),
        label_visibility="collapsed",
        key=radio_key
    )
    
    if previous_selection is not None and selected_label != previous_selection:
        st.session_state.menu_state = name_by_label[selected_label]

# 7) Kullanım: seçili menü adı

menu = st.session_state.menu_state
# ========= /ŞIK MENÜ =========


### ===========================
### === GENEL BAKIŞ (Vade Durumu Dahil) ===
### ===========================

if menu == "Genel Bakış":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>ŞEKEROĞLU İHRACAT CRM - Genel Bakış</h2>", unsafe_allow_html=True)

    # ---------- Güvenli tutar dönüştürücü ----------
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
        if "," in s:
            try:
                return float(s.replace(".", "").replace(",", "."))
            except:
                pass
        return 0.0

    # ---------- Toplam Fatura ----------
    toplam_fatura_tutar = 0.0
    if "Tutar" in df_evrak.columns and not df_evrak.empty:
        df_evrak = df_evrak.copy()
        df_evrak["Tutar_num"] = df_evrak["Tutar"].apply(smart_to_num).fillna(0.0)
        toplam_fatura_tutar = float(df_evrak["Tutar_num"].sum())
    st.markdown(f"<div style='font-size:1.5em; color:#d35400; font-weight:bold;'>Toplam Fatura Tutarı: {toplam_fatura_tutar:,.2f} USD</div>", unsafe_allow_html=True)

    # ---------- Vade Durumu Kutucukları ----------
    for col in ["Vade Tarihi", "Ödendi"]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col == "Vade Tarihi" else False

    vade_ts = pd.to_datetime(df_evrak["Vade Tarihi"], errors="coerce")
    today_norm = pd.Timestamp.today().normalize()

    od_me = ~df_evrak["Ödendi"].astype(bool)
    vadesi_gelmemis_m = (vade_ts > today_norm) & od_me
    vadesi_bugun_m     = (vade_ts.dt.date == today_norm.date()) & od_me
    gecikmis_m         = (vade_ts < today_norm) & od_me

    tg_sum = float(df_evrak.loc[vadesi_gelmemis_m, "Tutar_num"].sum())
    tb_sum = float(df_evrak.loc[vadesi_bugun_m, "Tutar_num"].sum())
    gec_sum = float(df_evrak.loc[gecikmis_m, "Tutar_num"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Vadeleri Gelmeyen", f"{tg_sum:,.2f} USD", f"{int(vadesi_gelmemis_m.sum())} Fatura")
    c2.metric("Bugün Vadesi Dolan", f"{tb_sum:,.2f} USD", f"{int(vadesi_bugun_m.sum())} Fatura")
    c3.metric("Geciken Ödemeler", f"{gec_sum:,.2f} USD", f"{int(gecikmis_m.sum())} Fatura")

    st.markdown("---")

    # ---- Bekleyen Teklifler ----
     st.markdown("### Bekleyen Teklifler")
    bekleyen_teklifler = df_teklif[df_teklif["Durum"] == "Açık"] if "Durum" in df_teklif.columns else pd.DataFrame()
    try:
        toplam_teklif = pd.to_numeric(bekleyen_teklifler["Tutar"], errors="coerce").sum()
    except:
        toplam_teklif = 0
    st.markdown(f"<div style='font-size:1.3em; color:#11998e; font-weight:bold;'>Toplam: {toplam_teklif:,.2f} USD</div>", unsafe_allow_html=True)
    if bekleyen_teklifler.empty:
        st.info("Bekleyen teklif yok.")
    else:
        st.dataframe(bekleyen_teklifler[["Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama"]], use_container_width=True)

    # ---- Bekleyen Proformalar ----
    st.markdown("### Bekleyen Proformalar")
    bekleyen_proformalar = df_proforma[df_proforma["Durum"] == "Beklemede"] if "Durum" in df_proforma.columns else pd.DataFrame()
    try:
        toplam_proforma = pd.to_numeric(bekleyen_proformalar["Tutar"], errors="coerce").sum()
    except:
        toplam_proforma = 0
    st.markdown(f"<div style='font-size:1.3em; color:#f7971e; font-weight:bold;'>Toplam: {toplam_proforma:,.2f} USD</div>", unsafe_allow_html=True)
    if bekleyen_proformalar.empty:
        st.info("Bekleyen proforma yok.")
    else:
        st.dataframe(bekleyen_proformalar[["Müşteri Adı", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]], use_container_width=True)

    # ---- Sevk Bekleyen Siparişler ----
    st.markdown("### Sevk Bekleyen Siparişler")
    if "Sevk Durumu" not in df_proforma.columns:
        df_proforma["Sevk Durumu"] = ""
    if "Ülke" not in df_proforma.columns:
        df_proforma["Ülke"] = ""
    sevk_bekleyenler = df_proforma[(df_proforma["Durum"] == "Siparişe Dönüştü") & (~df_proforma["Sevk Durumu"].isin(["Sevkedildi", "Ulaşıldı"]))] if "Durum" in df_proforma.columns else pd.DataFrame()
    try:
        toplam_siparis = pd.to_numeric(sevk_bekleyenler["Tutar"], errors="coerce").sum()
    except:
        toplam_siparis = 0
    st.markdown(f"<div style='font-size:1.3em; color:#185a9d; font-weight:bold;'>Toplam: {toplam_siparis:,.2f} USD</div>", unsafe_allow_html=True)
    if sevk_bekleyenler.empty:
        st.info("Sevk bekleyen sipariş yok.")
    else:
        st.dataframe(sevk_bekleyenler[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]], use_container_width=True)

    # ---- Yolda Olan Siparişler ----
    st.markdown("### ETA Takibindeki Siparişler")
    eta_yolda = df_proforma[(df_proforma["Sevk Durumu"] == "Sevkedildi") & (~df_proforma["Sevk Durumu"].isin(["Ulaşıldı"]))] if "Sevk Durumu" in df_proforma.columns else pd.DataFrame()
    try:
        toplam_eta = pd.to_numeric(eta_yolda["Tutar"], errors="coerce").sum()
    except:
        toplam_eta = 0
    st.markdown(f"<div style='font-size:1.3em; color:#c471f5; font-weight:bold;'>Toplam: {toplam_eta:,.2f} USD</div>", unsafe_allow_html=True)
    if eta_yolda.empty:
        st.info("Yolda olan (sevk edilmiş) sipariş yok.")
    else:
        st.dataframe(eta_yolda[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]], use_container_width=True)

    # ---- Son Teslim Edilen Siparişler ----
    st.markdown("### Son Teslim Edilen 5 Sipariş")
    if "Sevk Durumu" in df_proforma.columns:
        teslim_edilenler = df_proforma[df_proforma["Sevk Durumu"] == "Ulaşıldı"]
        if not teslim_edilenler.empty:
            teslim_edilenler = teslim_edilenler.sort_values(by="Tarih", ascending=False).head(5)
            st.dataframe(teslim_edilenler[["Müşteri Adı", "Ülke", "Proforma No", "Tarih", "Tutar", "Vade (gün)", "Açıklama"]], use_container_width=True)
        else:
            st.info("Teslim edilmiş sipariş yok.")
    else:
        st.info("Teslim edilmiş sipariş yok.")

    # ---- Vade Takibi Tablosu (HERKES GÖRÜR) ----
    st.markdown("### Vadeli Fatura ve Tahsilat Takibi")
    for col in ["Proforma No", "Vade (gün)", "Ödendi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli"]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col != "Ödendi" else False
    df_evrak["Ödendi"] = df_evrak["Ödendi"].fillna(False).astype(bool)

    vade_df = df_evrak[df_evrak["Vade Tarihi"].notna() & (~df_evrak["Ödendi"])].copy()
    if vade_df.empty:
        st.info("Açık vade kaydı yok.")
    else:
        vade_df["Vade Tarihi"] = pd.to_datetime(vade_df["Vade Tarihi"])
        vade_df["Kalan Gün"] = (vade_df["Vade Tarihi"] - pd.to_datetime(datetime.date.today())).dt.days
        st.dataframe(vade_df[["Müşteri Adı", "Ülke", "Fatura No", "Vade Tarihi", "Tutar", "Kalan Gün"]], use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.info("Daha detaylı işlem yapmak için sol menüden ilgili bölüme geçebilirsiniz.")


### ===========================
### === CARİ EKLEME MENÜSÜ ===
### ===========================

if menu == "Yeni Cari Kaydı":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Yeni Müşteri Ekle</h2>", unsafe_allow_html=True)

    # ---- Yardımcılar: doğrulama & normalizasyon ----
    import re
    def _clean_text(s):
        return (str(s or "")).strip()

    def _valid_email(s):
        s = _clean_text(s)
        if not s:
            return True  # boşsa zorunlu değil; doluysa kontrol
        # basit ve sağlam bir desen
        return re.match(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$", s) is not None

    def _normalized_phone(s):
        # sadece rakamları al, 10–15 haneye izin ver
        digits = re.sub(r"\D+", "", str(s or ""))
        return digits

    # Mükerrer kontrol için set (ad+ülke)
    if df_musteri.empty:
        existing_pairs = set()
    else:
        existing_pairs = set(
            (str(a).strip().lower(), str(u).strip().lower())
            for a, u in zip(df_musteri.get("Müşteri Adı", []), df_musteri.get("Ülke", []))
        )

    with st.form("add_customer", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Müşteri Adı *", placeholder="Örn: ABC Dış Ticaret Ltd.")
            phone = st.text_input("Telefon", placeholder="+90 ...")
            email = st.text_input("E-posta", placeholder="ornek@firma.com")
            address = st.text_area("Adres")
            kategori = st.selectbox("Kategori", ["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"], index=3)
            aktif_pasif = st.selectbox("Durum", ["Aktif", "Pasif"], index=0)
        with c2:
            ulke = st.selectbox("Ülke *", ulke_listesi)
            temsilci = st.selectbox("Satış Temsilcisi *", temsilci_listesi)
            vade_gun = st.number_input("Vade (Gün Sayısı)", min_value=0, max_value=365, value=0, step=1)
            odeme_sekli = st.selectbox("Ödeme Şekli", ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"])
            para_birimi = st.selectbox("Para Birimi", ["USD", "EURO", "TL", "RUBLE"], index=0)
            dt_secim = st.selectbox("DT Seçin", ["DT-1", "DT-2", "DT-3", "DT-4"], index=0)

        submitted = st.form_submit_button("Kaydet")

    if submitted:
        # --- Normalizasyon ---
        name_n = _clean_text(name)
        ulke_n = _clean_text(ulke)
        email_n = _clean_text(email)
        phone_n = _normalized_phone(phone)

        # --- Zorunlu alanlar ---
        errors = []
        if not name_n:
            errors.append("Müşteri adı boş olamaz.")
        if not ulke_n:
            errors.append("Ülke seçimi zorunludur.")
        if not temsilci:
            errors.append("Satış temsilcisi seçimi zorunludur.")
        if not _valid_email(email_n):
            errors.append("E-posta formatı hatalı görünüyor.")

        # --- Mükerrer kontrol (Ad + Ülke) ---
        key = (name_n.lower(), ulke_n.lower())
        if key in existing_pairs:
            errors.append("Aynı ada ve ülkeye ait bir müşteri zaten kayıtlı görünüyor.")

        if errors:
            for e in errors:
                st.error(e)
            st.stop()

        # --- Yeni satır ---
        new_row = {
            "Müşteri Adı": name_n,
            "Telefon": phone_n,                          # normalize edilmiş
            "E-posta": email_n,
            "Adres": _clean_text(address),
            "Ülke": ulke_n,
            "Satış Temsilcisi": temsilci,
            "Kategori": kategori,
            "Durum": aktif_pasif,
            "Vade (Gün)": vade_gun,
            "Ödeme Şekli": odeme_sekli,
            "Para Birimi": para_birimi,
            "DT Seçimi": dt_secim,
            "Oluşturma Tarihi": datetime.date.today(),  # faydalı meta
        }

        # --- Kaydet ---
        df_musteri = pd.concat([df_musteri, pd.DataFrame([new_row])], ignore_index=True)
        update_excel()

        # --- Muhasebeye e-posta (sende tanımlı yardımcılar) ---
        try:
            yeni_cari_txt_olustur(new_row)
            send_email_with_txt(
                to_email=["muhasebe@sekeroglugroup.com", "h.boy@sekeroglugroup.com"],
                subject="Yeni Cari Açılışı",
                body="Muhasebe için yeni cari açılışı ekte gönderilmiştir.",
                file_path="yeni_cari.txt"
            )
            st.success("Müşteri eklendi ve e‑posta ile muhasebeye gönderildi!")
        except Exception as e:
            st.warning(f"Müşteri eklendi ancak e‑posta gönderilemedi: {e}")

        st.balloons()
        st.rerun()

                
### ===========================
### === MÜŞTERİ LİSTESİ MENÜSÜ (Cloud-Sağlam) ===
### ===========================

import uuid
import numpy as np  # Eksik bilgi mesajı için gerekli

# — Zorunlu sütunları garanti altına al —
gerekli_kolonlar = [
    "ID", "Müşteri Adı", "Telefon", "E-posta", "Adres",
    "Ülke", "Satış Temsilcisi", "Kategori", "Durum",
    "Vade (Gün)", "Ödeme Şekli", "Para Birimi", "DT Seçimi"
]
for col in gerekli_kolonlar:
    if col not in df_musteri.columns:
        if col == "ID":
            # eksikse tüm satırlar için üret
            if len(df_musteri) > 0:
                df_musteri[col] = [str(uuid.uuid4()) for _ in range(len(df_musteri))]
            else:
                df_musteri[col] = []
        elif col == "Vade (Gün)":
            df_musteri[col] = ""
        else:
            df_musteri[col] = ""

# — Eski kayıtlarda ID boşsa doldur —
mask_id_bos = df_musteri["ID"].isna() | (df_musteri["ID"].astype(str).str.strip() == "")
if mask_id_bos.any():
    df_musteri.loc[mask_id_bos, "ID"] = [str(uuid.uuid4()) for _ in range(mask_id_bos.sum())]
    update_excel()

if menu == "Müşteri Portföyü":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Müşteri Listesi</h2>", unsafe_allow_html=True)

    # ---- Üst Araçlar: Arama + Filtreler ----
    with st.container():
        c1, c2, c3, c4 = st.columns([2, 1.2, 1.2, 1.2])
        aranacak = c1.text_input("Arama (Ad / Telefon / E-posta / Adres)", value="")
        ulke_filtre = c2.multiselect("Ülke Filtresi", sorted([u for u in df_musteri["Ülke"].dropna().unique() if str(u).strip()]), default=[])
        temsilci_filtre = c3.multiselect("Temsilci Filtresi", sorted([t for t in df_musteri["Satış Temsilcisi"].dropna().unique() if str(t).strip()]), default=[])
        durum_filtre = c4.multiselect("Durum", ["Aktif", "Pasif"], default=["Aktif"])  # Varsayılan: Aktif

    # ---- Filtreleme mantığı ----
    view_df = df_musteri.copy()

    # Durum filtresi
    if len(durum_filtre) > 0:
        view_df = view_df[view_df["Durum"].isin(durum_filtre)]

    # Ülke filtresi
    if len(ulke_filtre) > 0:
        view_df = view_df[view_df["Ülke"].isin(ulke_filtre)]

    # Temsilci filtresi
    if len(temsilci_filtre) > 0:
        view_df = view_df[view_df["Satış Temsilcisi"].isin(temsilci_filtre)]

    # Arama filtresi
    if aranacak.strip():
        s = aranacak.strip().lower()
        def _match(row):
            fields = [
                row.get("Müşteri Adı", ""), row.get("Telefon", ""), row.get("E-posta", ""),
                row.get("Adres", ""), row.get("Ülke", ""), row.get("Satış Temsilcisi", "")
            ]
            return any(s in str(x).lower() for x in fields)
        view_df = view_df[view_df.apply(_match, axis=1)]

    # Görüntü tablosu (boşları sadece tabloda “—” yap)
    show_cols = ["Müşteri Adı", "Ülke", "Satış Temsilcisi", "Telefon", "E-posta", "Adres", "Kategori", "Durum", "Vade (Gün)", "Ödeme Şekli", "Para Birimi", "DT Seçimi"]
    for c in show_cols:
        if c not in view_df.columns:
            view_df[c] = ""

    table_df = view_df[show_cols].replace({np.nan: "—", "": "—"})
    table_df = table_df.sort_values("Müşteri Adı").reset_index(drop=True)

    # Özet bilgi ve dışa aktar
    top_row = st.columns([3, 1])
    with top_row[0]:
        st.markdown(f"<div style='color:#219A41; font-weight:700;'>Toplam Kayıt: {len(view_df)}</div>", unsafe_allow_html=True)
    with top_row[1]:
        st.download_button(
            "CSV indir",
            data=table_df.to_csv(index=False).encode("utf-8"),
            file_name="musteri_listesi.csv",
            mime="text/csv",
            use_container_width=True
        )

    if table_df.empty:
        st.markdown("<div style='color:#b00020; font-weight:bold; font-size:1.1em;'>Kayıt bulunamadı.</div>", unsafe_allow_html=True)
    else:
        st.dataframe(table_df, use_container_width=True)

    st.markdown("<h4 style='margin-top: 24px;'>Müşteri Düzenle / Sil</h4>", unsafe_allow_html=True)

    # Düzenleme/Silme için seçim: ID ile — güvenli
    # Önce ekranda gösterilen view_df'ten seçim yaptırıyoruz (alfabetik)
    secenek_df = view_df.sort_values("Müşteri Adı").reset_index(drop=True)
    if secenek_df.empty:
        st.info("Düzenlemek/silmek için uygun kayıt yok.")
    else:
        secim = st.selectbox(
            "Düzenlenecek Müşteriyi Seçin",
            options=secenek_df["ID"].tolist(),
            format_func=lambda _id: f"{secenek_df.loc[secenek_df['ID']==_id, 'Müşteri Adı'].values[0]} ({secenek_df.loc[secenek_df['ID']==_id, 'Kategori'].values[0]})"
        )

        # Orijinal index (ana df_musteri içinden) — ID ile eşle
        orj_mask = (df_musteri["ID"] == secim)
        if not orj_mask.any():
            st.warning("Beklenmeyen hata: Seçilen kayıt ana tabloda bulunamadı.")
        else:
            orj_idx = df_musteri.index[orj_mask][0]

            with st.form("edit_existing_customer"):
                name = st.text_input("Müşteri Adı", value=str(df_musteri.at[orj_idx, "Müşteri Adı"]))
                phone = st.text_input("Telefon", value=str(df_musteri.at[orj_idx, "Telefon"]))
                email = st.text_input("E-posta", value=str(df_musteri.at[orj_idx, "E-posta"]))
                address = st.text_area("Adres", value=str(df_musteri.at[orj_idx, "Adres"]))

                # Ülke / Temsilci seçimleri
                try:
                    ulke_def = df_musteri.at[orj_idx, "Ülke"]
                    ulke_idx = ulke_listesi.index(ulke_def) if ulke_def in ulke_listesi else 0
                except Exception:
                    ulke_idx = 0
                ulke = st.selectbox("Ülke", ulke_listesi, index=ulke_idx)

                try:
                    tem_def = df_musteri.at[orj_idx, "Satış Temsilcisi"]
                    tem_idx = temsilci_listesi.index(tem_def) if tem_def in temsilci_listesi else 0
                except Exception:
                    tem_idx = 0
                temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi, index=tem_idx)

                kategori = st.selectbox(
                    "Kategori",
                    sorted(["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"]),
                    index=sorted(["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"]).index(df_musteri.at[orj_idx, "Kategori"])
                    if df_musteri.at[orj_idx, "Kategori"] in ["Avrupa bayi", "bayi", "müşteri", "yeni müşteri"] else 0
                )
                aktif_pasif = st.selectbox(
                    "Durum", ["Aktif", "Pasif"],
                    index=(0 if str(df_musteri.at[orj_idx, "Durum"]) == "Aktif" else 1)
                )

                vade = st.text_input("Vade (Gün)", value=str(df_musteri.at[orj_idx, "Vade (Gün)"]) if "Vade (Gün)" in df_musteri.columns else "")
                odeme_sekli = st.selectbox(
                    "Ödeme Şekli",
                    ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"],
                    index=["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"].index(df_musteri.at[orj_idx, "Ödeme Şekli"])
                    if df_musteri.at[orj_idx, "Ödeme Şekli"] in ["Peşin", "Mal Mukabili", "Vesaik Mukabili", "Akreditif", "Diğer"] else 0
                )

                para_birimi = st.selectbox(
                    "Para Birimi",
                    ["EURO", "USD", "TL", "RUBLE"],
                    index=["EURO", "USD", "TL", "RUBLE"].index(df_musteri.at[orj_idx, "Para Birimi"]) if df_musteri.at[orj_idx, "Para Birimi"] in ["EURO", "USD", "TL", "RUBLE"] else 0
                )

                dt_secimi = st.selectbox(
                    "DT Seçimi",
                    ["DT-1", "DT-2", "DT-3", "DT-4"],
                    index=["DT-1", "DT-2", "DT-3", "DT-4"].index(df_musteri.at[orj_idx, "DT Seçimi"]) if df_musteri.at[orj_idx, "DT Seçimi"] in ["DT-1", "DT-2", "DT-3", "DT-4"] else 0
                )

                colu, cols = st.columns(2)
                guncelle = colu.form_submit_button("Güncelle")
                sil = cols.form_submit_button("Sil")

            if guncelle:
                df_musteri.at[orj_idx, "Müşteri Adı"] = name
                df_musteri.at[orj_idx, "Telefon"] = phone
                df_musteri.at[orj_idx, "E-posta"] = email
                df_musteri.at[orj_idx, "Adres"] = address
                df_musteri.at[orj_idx, "Ülke"] = ulke
                df_musteri.at[orj_idx, "Satış Temsilcisi"] = temsilci
                df_musteri.at[orj_idx, "Kategori"] = kategori
                df_musteri.at[orj_idx, "Durum"] = aktif_pasif
                df_musteri.at[orj_idx, "Vade (Gün)"] = vade
                df_musteri.at[orj_idx, "Ödeme Şekli"] = odeme_sekli
                df_musteri.at[orj_idx, "Para Birimi"] = para_birimi
                df_musteri.at[orj_idx, "DT Seçimi"] = dt_secimi
                update_excel()
                st.success("Müşteri bilgisi güncellendi!")
                st.rerun()

            if sil:
                df_musteri = df_musteri.drop(orj_idx).reset_index(drop=True)
                update_excel()
                st.success("Müşteri kaydı silindi!")
                st.rerun()


### ===========================
### === ETKİLEŞİM GÜNLÜĞÜ (Cloud-Sağlam) ===
### ===========================

import uuid

# Zorunlu kolonlar
gerekli = ["ID", "Müşteri Adı", "Tarih", "Tip", "Açıklama"]
for c in gerekli:
    if c not in df_kayit.columns:
        df_kayit[c] = ""

# Eski kayıtlarda ID yoksa doldur
mask_bos_id = df_kayit["ID"].isna() | (df_kayit["ID"].astype(str).str.strip() == "")
if mask_bos_id.any():
    df_kayit.loc[mask_bos_id, "ID"] = [str(uuid.uuid4()) for _ in range(mask_bos_id.sum())]
    update_excel()

if menu == "Etkileşim Günlüğü":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Etkileşim Günlüğü</h2>", unsafe_allow_html=True)
    
    st.subheader("Kayıt Ekranı")
    secim = st.radio("Lütfen işlem seçin:", ["Yeni Kayıt", "Eski Kayıt", "Tarih Aralığı ile Kayıtlar"], horizontal=False)

    # --- Ortak: müşteri listesi (boş hariç, alfabetik) ---
    musteri_options = [""] + sorted([
        m for m in df_musteri["Müşteri Adı"].dropna().unique()
        if isinstance(m, str) and m.strip() != ""
    ])

    # === YENİ KAYIT ===
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
                        "ID": str(uuid.uuid4()),
                        "Müşteri Adı": musteri_sec,
                        "Tarih": tarih,
                        "Tip": tip,
                        "Açıklama": aciklama
                    }
                    df_kayit = pd.concat([df_kayit, pd.DataFrame([new_row])], ignore_index=True)
                    update_excel()
                    st.success("Kayıt eklendi!")
                    st.rerun()

    # === ESKİ KAYIT (Listele / Ara / Düzenle / Sil) ===
    elif secim == "Eski Kayıt":
        colf1, colf2, colf3 = st.columns([2, 1, 1])
        musteri_f = colf1.selectbox("Müşteri Filtresi", ["(Hepsi)"] + sorted(df_kayit["Müşteri Adı"].dropna().unique().tolist()))
        tip_f = colf2.multiselect("Tip Filtresi", ["Arama", "Görüşme", "Ziyaret"], default=[])
        aranacak = colf3.text_input("Ara (açıklama)", value="")

        view = df_kayit.copy()
        # Filtreler
        if musteri_f and musteri_f != "(Hepsi)":
            view = view[view["Müşteri Adı"] == musteri_f]
        if tip_f:
            view = view[view["Tip"].isin(tip_f)]
        if aranacak.strip():
            s = aranacak.lower().strip()
            view = view[view["Açıklama"].astype(str).str.lower().str.contains(s, na=False)]

        # Görünüm tablosu
        if not view.empty:
            goster = view.copy()
            goster["Tarih"] = pd.to_datetime(goster["Tarih"], errors="coerce").dt.strftime("%d/%m/%Y")
            st.dataframe(goster[["Müşteri Adı", "Tarih", "Tip", "Açıklama"]].sort_values("Tarih", ascending=False), use_container_width=True)

            # Dışa aktar
            st.download_button(
                "CSV indir",
                data=goster.to_csv(index=False).encode("utf-8"),
                file_name="gorusme_kayitlari.csv",
                mime="text/csv"
            )
        else:
            st.info("Seçilen filtrelere uygun kayıt bulunamadı.")

        # Düzenleme / Silme
        st.markdown("#### Kayıt Düzenle / Sil")
        if view.empty:
            st.caption("Önce filtreleriyle bir kayıt listeleyin.")
        else:
            # Seçim ID ile (en son ekleneni üste almak için tarihe göre sıralayalım)
            view_sorted = view.sort_values("Tarih", ascending=False).reset_index(drop=True)
            sec_id = st.selectbox(
                "Kayıt Seçin",
                options=view_sorted["ID"].tolist(),
                format_func=lambda _id: f"{view_sorted.loc[view_sorted['ID']==_id, 'Müşteri Adı'].values[0]} | {view_sorted.loc[view_sorted['ID']==_id, 'Tip'].values[0]}"
            )

            # Orijinal index
            orj_mask = (df_kayit["ID"] == sec_id)
            if not orj_mask.any():
                st.warning("Beklenmeyen hata: Kayıt ana tabloda bulunamadı.")
            else:
                orj_idx = df_kayit.index[orj_mask][0]
                with st.form("edit_kayit"):
                    musteri_g = st.selectbox("Müşteri", musteri_options, index=(musteri_options.index(df_kayit.at[orj_idx, "Müşteri Adı"]) if df_kayit.at[orj_idx, "Müşteri Adı"] in musteri_options else 0))
                    try:
                        tarih_g = pd.to_datetime(df_kayit.at[orj_idx, "Tarih"]).date()
                    except Exception:
                        tarih_g = datetime.date.today()
                    tarih_g = st.date_input("Tarih", value=tarih_g, format="DD/MM/YYYY")
                    tip_g = st.selectbox("Tip", ["Arama", "Görüşme", "Ziyaret"], index=["Arama","Görüşme","Ziyaret"].index(df_kayit.at[orj_idx,"Tip"]) if df_kayit.at[orj_idx,"Tip"] in ["Arama","Görüşme","Ziyaret"] else 0)
                    aciklama_g = st.text_area("Açıklama", value=str(df_kayit.at[orj_idx, "Açıklama"]))
                    colu, cols = st.columns(2)
                    guncelle = colu.form_submit_button("Güncelle")
                    sil = cols.form_submit_button("Sil")

                if guncelle:
                    df_kayit.at[orj_idx, "Müşteri Adı"] = musteri_g
                    df_kayit.at[orj_idx, "Tarih"] = tarih_g
                    df_kayit.at[orj_idx, "Tip"] = tip_g
                    df_kayit.at[orj_idx, "Açıklama"] = aciklama_g
                    update_excel()
                    st.success("Kayıt güncellendi!")
                    st.rerun()

                if sil:
                    df_kayit = df_kayit.drop(orj_idx).reset_index(drop=True)
                    update_excel()
                    st.success("Kayıt silindi!")
                    st.rerun()

    # === TARİH ARALIĞI İLE KAYITLAR ===
    elif secim == "Tarih Aralığı ile Kayıtlar":
        col1, col2 = st.columns(2)
        with col1:
            baslangic = st.date_input("Başlangıç Tarihi", value=datetime.date.today() - datetime.timedelta(days=7), format="DD/MM/YYYY")
        with col2:
            bitis = st.date_input("Bitiş Tarihi", value=datetime.date.today(), format="DD/MM/YYYY")

        # Sağlam tarih filtrelemesi
        tser = pd.to_datetime(df_kayit["Tarih"], errors="coerce")
        start_ts = pd.to_datetime(baslangic)
        end_ts = pd.to_datetime(bitis) + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
        tarih_arasi = df_kayit[tser.between(start_ts, end_ts, inclusive="both")].copy()

        if not tarih_arasi.empty:
            goster = tarih_arasi.copy()
            goster["Tarih"] = pd.to_datetime(goster["Tarih"], errors="coerce").dt.strftime('%d/%m/%Y')
            st.dataframe(goster.sort_values("Tarih", ascending=False), use_container_width=True)
            st.download_button(
                "CSV indir",
                data=goster.to_csv(index=False).encode("utf-8"),
                file_name="gorusme_kayitlari_tarih_araligi.csv",
                mime="text/csv"
            )
        else:
            st.info("Bu tarihler arasında kayıt yok.")


### ===========================
### --- TEKLİF YÖNETİMİ (Cloud-Sağlam) ---
### ===========================

elif menu == "Teklif Yönetimi":
    import uuid, time

    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Teklif Yönetimi</h2>", unsafe_allow_html=True)

    # --- Zorunlu kolonlar + ID backfill ---
    gerekli = ["ID", "Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama", "Durum", "PDF"]
    for c in gerekli:
        if c not in df_teklif.columns:
            df_teklif[c] = ""
    mask_bos_id = df_teklif["ID"].astype(str).str.strip().isin(["", "nan"])
    if mask_bos_id.any():
        df_teklif.loc[mask_bos_id, "ID"] = [str(uuid.uuid4()) for _ in range(mask_bos_id.sum())]
        update_excel()

    # --- Akıllı sayı dönüştürücü ---
    def smart_to_num(x):
        if pd.isna(x): return 0.0
        s = str(x).strip()
        for sym in ["USD", "$", "€", "EUR", "₺", "TL", "tl", "Tl"]:
            s = s.replace(sym, "")
        s = s.replace("\u00A0", "").replace(" ", "")
        try: return float(s)                     # US format
        except: pass
        if "," in s:
            try: return float(s.replace(".", "").replace(",", "."))  # EU format
            except: pass
        return 0.0

    # --- Otomatik teklif no ---
    def otomatik_teklif_no():
        if df_teklif.empty or "Teklif No" not in df_teklif.columns:
            return "TKF-0001"
        sayilar = pd.to_numeric(
            df_teklif["Teklif No"].astype(str).str.extract(r'(\d+)$')[0], errors='coerce'
        ).dropna().astype(int)
        yeni_no = (sayilar.max() + 1) if not sayilar.empty else 1
        return f"TKF-{yeni_no:04d}"

    # --- Güvenli geçici dosya sil ---
    def güvenli_sil(dosya, tekrar=5, bekle=1):
        for _ in range(tekrar):
            try:
                os.remove(dosya)
                return True
            except PermissionError:
                time.sleep(bekle)
            except FileNotFoundError:
                return True
        return False

    # ---------- ÜST ÖZET: Açık teklifler ----------
    tkg = df_teklif.copy()
    tkg["Tarih"] = pd.to_datetime(tkg["Tarih"], errors="coerce")
    acik_teklifler = tkg[tkg["Durum"] == "Açık"].sort_values(["Müşteri Adı", "Teklif No"])
    toplam_teklif = float(acik_teklifler["Tutar"].apply(smart_to_num).sum())
    acik_teklif_sayi = len(acik_teklifler)
    st.subheader("Açık Pozisyondaki Teklifler")
    st.markdown(
        f"<div style='font-size:1.05em; color:#11998e; font-weight:bold;'>Toplam: {toplam_teklif:,.2f} USD | "
        f"Toplam Açık Teklif: {acik_teklif_sayi} adet</div>",
        unsafe_allow_html=True
    )
    if not acik_teklifler.empty:
        goster = acik_teklifler.copy()
        goster["Tarih"] = goster["Tarih"].dt.strftime("%d/%m/%Y")
        st.dataframe(goster[["Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Ürün/Hizmet", "Açıklama"]], use_container_width=True)
    else:
        st.info("Açık teklif bulunmuyor.")

    st.markdown("##### Lütfen bir işlem seçin")
    col1, col2 = st.columns(2)
    with col1:
        yeni_teklif_buton = st.button("Yeni Teklif")
    with col2:
        eski_teklif_buton = st.button("Eski Teklifler / Düzenle")

    if "teklif_view" not in st.session_state:
        st.session_state['teklif_view'] = None
    if yeni_teklif_buton:
        st.session_state['teklif_view'] = "yeni"
    if eski_teklif_buton:
        st.session_state['teklif_view'] = "eski"

    # ============== YENİ TEKLİF ==============
    if st.session_state['teklif_view'] == "yeni":
        musteri_list = [""] + sorted(df_musteri["Müşteri Adı"].dropna().unique().tolist())
        st.subheader("Yeni Teklif Ekle")
        with st.form("add_teklif"):
            musteri_sec = st.selectbox("Müşteri Seç", musteri_list, key="yeni_teklif_musteri")
            tarih = st.date_input("Tarih", value=datetime.date.today(), format="DD/MM/YYYY")
            teklif_no = st.text_input("Teklif No", value=otomatik_teklif_no())
            tutar = st.text_input("Tutar (USD)")
            urun = st.text_input("Ürün/Hizmet")
            aciklama = st.text_area("Açıklama")
            durum = st.selectbox("Durum", ["Açık", "Sonuçlandı", "Beklemede"])
            pdf_file = st.file_uploader("Teklif PDF", type="pdf")
            submitted = st.form_submit_button("Kaydet")

            pdf_link = ""
            if submitted:
                if not teklif_no.strip():
                    st.error("Teklif No boş olamaz!")
                elif not musteri_sec:
                    st.error("Lütfen müşteri seçiniz!")
                else:
                    # PDF'yi Drive'a yükle (varsa)
                    if pdf_file:
                        temiz_musteri = "".join(x if x.isalnum() else "_" for x in str(musteri_sec))
                        temiz_tarih = str(tarih).replace("-", "")
                        pdf_filename = f"{temiz_musteri}__{temiz_tarih}__{teklif_no}.pdf"
                        temp_path = os.path.join(".", pdf_filename)
                        with open(temp_path, "wb") as f:
                            f.write(pdf_file.read())
                        gfile = drive.CreateFile({'title': pdf_filename, 'parents': [{'id': FIYAT_TEKLIFI_ID}]})
                        gfile.SetContentFile(temp_path)
                        gfile.Upload()
                        pdf_link = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                        güvenli_sil(temp_path)

                    new_row = {
                        "ID": str(uuid.uuid4()),
                        "Müşteri Adı": musteri_sec,
                        "Tarih": tarih,
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

    # ============== ESKİ TEKLİFLER / DÜZENLE / SİL ==============
    if st.session_state['teklif_view'] == "eski":
        st.subheader("Eski Teklifler")

        # ---- Filtreler ----
        f1, f2, f3, f4 = st.columns([1.5, 1, 1.3, 1.2])
        musteri_f = f1.selectbox("Müşteri", ["(Hepsi)"] + sorted(df_teklif["Müşteri Adı"].dropna().unique().tolist()))
        durum_f = f2.multiselect("Durum", ["Açık", "Beklemede", "Sonuçlandı"], default=[])
        # Tarih aralığı
        tmp = pd.to_datetime(df_teklif["Tarih"], errors="coerce")
        min_dt = (tmp.min().date() if tmp.notna().any() else datetime.date.today())
        max_dt = (tmp.max().date() if tmp.notna().any() else datetime.date.today())
        d1 = f3.date_input("Başlangıç", value=min_dt)
        d2 = f4.date_input("Bitiş", value=max_dt)
        aranacak = st.text_input("Ara (ürün/açıklama/teklif no)")

        view = df_teklif.copy()
        view["Tarih"] = pd.to_datetime(view["Tarih"], errors="coerce")

        if musteri_f and musteri_f != "(Hepsi)":
            view = view[view["Müşteri Adı"] == musteri_f]
        if durum_f:
            view = view[view["Durum"].isin(durum_f)]

        start_ts = pd.to_datetime(d1)
        end_ts = pd.to_datetime(d2) + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
        view = view[view["Tarih"].between(start_ts, end_ts, inclusive="both")]

        if aranacak.strip():
            s = aranacak.lower().strip()
            view = view[
                view["Ürün/Hizmet"].astype(str).str.lower().str.contains(s, na=False) |
                view["Açıklama"].astype(str).str.lower().str.contains(s, na=False) |
                view["Teklif No"].astype(str).str.lower().str.contains(s, na=False)
            ]

        # Toplam ve tablo
        toplam_view = float(view["Tutar"].apply(smart_to_num).sum())
        st.markdown(f"<div style='margin:.25rem 0 .5rem 0; font-weight:600;'>Filtreli Toplam: {toplam_view:,.2f} USD</div>", unsafe_allow_html=True)

        if not view.empty:
            tablo = view.sort_values("Tarih", ascending=False).copy()
            tablo["Tarih"] = tablo["Tarih"].dt.strftime("%d/%m/%Y")
            st.dataframe(tablo[["Müşteri Adı", "Tarih", "Teklif No", "Tutar", "Durum", "Ürün/Hizmet", "Açıklama"]], use_container_width=True)
            st.download_button(
                "CSV indir",
                data=tablo.to_csv(index=False).encode("utf-8"),
                file_name="teklifler.csv",
                mime="text/csv"
            )
        else:
            st.info("Filtrelere göre teklif bulunamadı.")

        # ---- Düzenle / Sil ----
        st.markdown("#### Teklif Düzenle / Sil")
        if view.empty:
            st.caption("Önce filtrelerle bir kayıt listeleyin.")
        else:
            v_sorted = view.sort_values("Tarih", ascending=False).reset_index(drop=True)
            sec_id = st.selectbox(
                "Teklif Seçiniz",
                options=v_sorted["ID"].tolist(),
                format_func=lambda _id: f"{v_sorted.loc[v_sorted['ID']==_id, 'Müşteri Adı'].values[0]} | {v_sorted.loc[v_sorted['ID']==_id, 'Teklif No'].values[0]}"
            )

            orj_mask = (df_teklif["ID"] == sec_id)
            if not orj_mask.any():
                st.warning("Beklenmeyen hata: Teklif ana tabloda bulunamadı.")
            else:
                orj_idx = df_teklif.index[orj_mask][0]
                # Var olan PDF linkini göster
                mevcut_pdf = str(df_teklif.at[orj_idx, "PDF"]) if pd.notna(df_teklif.at[orj_idx, "PDF"]) else ""
                if mevcut_pdf:
                    st.markdown(f"**Mevcut PDF:** [Görüntüle]({mevcut_pdf})", unsafe_allow_html=True)

                with st.form("edit_teklif"):
                    try:
                        tarih_g = pd.to_datetime(df_teklif.at[orj_idx, "Tarih"]).date()
                    except Exception:
                        tarih_g = datetime.date.today()
                    tarih_g = st.date_input("Tarih", value=tarih_g, format="DD/MM/YYYY")
                    teklif_no_g = st.text_input("Teklif No", value=str(df_teklif.at[orj_idx, "Teklif No"]))
                    musteri_g = st.selectbox(
                        "Müşteri",
                        [""] + sorted(df_musteri["Müşteri Adı"].dropna().unique().tolist()),
                        index=([""] + sorted(df_musteri["Müşteri Adı"].dropna().unique().tolist())).index(df_teklif.at[orj_idx, "Müşteri Adı"]) if df_teklif.at[orj_idx, "Müşteri Adı"] in ([""] + sorted(df_musteri["Müşteri Adı"].dropna().unique().tolist())) else 0
                    )
                    tutar_g = st.text_input("Tutar (USD)", value=str(df_teklif.at[orj_idx, "Tutar"]))
                    urun_g = st.text_input("Ürün/Hizmet", value=str(df_teklif.at[orj_idx, "Ürün/Hizmet"]))
                    aciklama_g = st.text_area("Açıklama", value=str(df_teklif.at[orj_idx, "Açıklama"]))
                    durum_g = st.selectbox("Durum", ["Açık", "Beklemede", "Sonuçlandı"],
                                           index=["Açık", "Beklemede", "Sonuçlandı"].index(df_teklif.at[orj_idx, "Durum"]) if df_teklif.at[orj_idx, "Durum"] in ["Açık","Beklemede","Sonuçlandı"] else 0)
                    pdf_yeni = st.file_uploader("PDF Güncelle (opsiyonel)", type="pdf", key=f"pdf_guncel_{sec_id}")
                    colu, cols = st.columns(2)
                    guncelle = colu.form_submit_button("Güncelle")
                    sil = cols.form_submit_button("Sil")

                if guncelle:
                    pdf_link_final = mevcut_pdf
                    if pdf_yeni:
                        # Yeni PDF yükle
                        temiz_m = "".join(x if x.isalnum() else "_" for x in str(musteri_g or "musteri"))
                        temiz_t = str(tarih_g).replace("-", "")
                        fname = f"{temiz_m}__{temiz_t}__{teklif_no_g}.pdf"
                        tmp_path = os.path.join(".", fname)
                        with open(tmp_path, "wb") as f:
                            f.write(pdf_yeni.read())
                        gfile = drive.CreateFile({'title': fname, 'parents': [{'id': FIYAT_TEKLIFI_ID}]})
                        gfile.SetContentFile(tmp_path)
                        gfile.Upload()
                        pdf_link_final = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                        güvenli_sil(tmp_path)

                    df_teklif.at[orj_idx, "Tarih"] = tarih_g
                    df_teklif.at[orj_idx, "Teklif No"] = teklif_no_g
                    df_teklif.at[orj_idx, "Müşteri Adı"] = musteri_g
                    df_teklif.at[orj_idx, "Tutar"] = tutar_g
                    df_teklif.at[orj_idx, "Ürün/Hizmet"] = urun_g
                    df_teklif.at[orj_idx, "Açıklama"] = aciklama_g
                    df_teklif.at[orj_idx, "Durum"] = durum_g
                    df_teklif.at[orj_idx, "PDF"] = pdf_link_final
                    update_excel()
                    st.success("Teklif güncellendi!")
                    st.rerun()

                if sil:
                    df_teklif = df_teklif.drop(orj_idx).reset_index(drop=True)
                    update_excel()
                    st.success("Teklif silindi!")
                    st.rerun()




### ===========================
### --- PROFORMA TAKİBİ MENÜSÜ (Cloud-Sağlam) ---
### ===========================

elif menu == "Proforma Yönetimi":
    import uuid, tempfile, time

    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Proforma Yönetimi</h2>", unsafe_allow_html=True)

    # ---- Drive klasör ID'leri (üstten tanımlıysa onları, yoksa EVRAK_KLASOR_ID'yi kullan) ----
    PROFORMA_PDF_FOLDER_ID   = globals().get("PROFORMA_PDF_FOLDER_ID", globals().get("EVRAK_KLASOR_ID"))
    SIPARIS_FORMU_FOLDER_ID  = globals().get("SIPARIS_FORMU_FOLDER_ID", globals().get("EVRAK_KLASOR_ID"))

    # ---- Kolon güvenliği + ID backfill ----
    gerekli = ["ID","Müşteri Adı","Tarih","Proforma No","Tutar","Açıklama","Durum","PDF",
               "Vade (gün)","Sevk Durumu","Ülke","Satış Temsilcisi","Ödeme Şekli","Termin Tarihi","Ulaşma Tarihi","Sipariş Formu"]
    for c in gerekli:
        if c not in df_proforma.columns:
            df_proforma[c] = ""
    mask_bos_id = df_proforma["ID"].astype(str).str.strip().isin(["","nan"])
    if mask_bos_id.any():
        df_proforma.loc[mask_bos_id, "ID"] = [str(uuid.uuid4()) for _ in range(mask_bos_id.sum())]
        update_excel()

    # --- Akıllı sayı dönüştürücü (toplamlar için) ---
    def smart_to_num(x):
        if pd.isna(x): return 0.0
        s = str(x).strip()
        for sym in ["USD","$","€","EUR","₺","TL","tl","Tl"]: s = s.replace(sym,"")
        s = s.replace("\u00A0","").replace(" ","")
        try: return float(s)
        except: pass
        if "," in s:
            try: return float(s.replace(".","").replace(",","."))
            except: pass
        return 0.0

    # --- Güvenli silme ---
    def güvenli_sil(path, tekrar=5, bekle=1):
        for _ in range(tekrar):
            try:
                os.remove(path); return True
            except PermissionError:
                time.sleep(bekle)
            except FileNotFoundError:
                return True
        return False

    # ---------- ÜST ÖZET: Bekleyen Proformalar ----------
    pview = df_proforma.copy()
    pview["Tarih"] = pd.to_datetime(pview["Tarih"], errors="coerce")
    beklemede_kayitlar = pview[pview["Durum"] == "Beklemede"].sort_values(["Tarih","Müşteri Adı"], ascending=[False, True])
    toplam_bekleyen = float(beklemede_kayitlar["Tutar"].apply(smart_to_num).sum())

    st.subheader("Bekleyen Proformalar")
    st.markdown(f"<div style='font-weight:600;'>Toplam Bekleyen: {toplam_bekleyen:,.2f} USD</div>", unsafe_allow_html=True)
    if not beklemede_kayitlar.empty:
        g = beklemede_kayitlar.copy()
        g["Tarih"] = g["Tarih"].dt.strftime("%d/%m/%Y")
        st.dataframe(g[["Müşteri Adı","Proforma No","Tarih","Tutar","Durum","Vade (gün)","Sevk Durumu"]], use_container_width=True)
    else:
        st.info("Beklemede proforma bulunmuyor.")

    # ---------- Müşteri seçimi ----------
    musteri_list = sorted([x for x in df_musteri["Müşteri Adı"].dropna().unique() if str(x).strip()!=""]) if not df_musteri.empty else []
    musteri_sec = st.selectbox("Müşteri Seç", [""] + musteri_list)

    if musteri_sec:
        st.write("Proforma işlemi seçin:")
        islem = st.radio("", ["Yeni Kayıt","Eski Kayıt / Düzenle"], horizontal=True)

        # ============== YENİ KAYIT ==============
        if islem == "Yeni Kayıt":
            musteri_info = df_musteri[df_musteri["Müşteri Adı"] == musteri_sec]
            default_ulke      = musteri_info["Ülke"].values[0] if not musteri_info.empty else ""
            default_temsilci  = musteri_info["Satış Temsilcisi"].values[0] if not musteri_info.empty else ""
            default_odeme     = musteri_info["Ödeme Şekli"].values[0] if not musteri_info.empty else ""

            with st.form("add_proforma"):
                tarih      = st.date_input("Tarih", value=datetime.date.today())
                proforma_no= st.text_input("Proforma No")
                tutar      = st.text_input("Tutar (USD)")
                vade_gun   = st.text_input("Vade (gün)")
                ulke       = st.text_input("Ülke", value=default_ulke, disabled=True)
                temsilci   = st.text_input("Satış Temsilcisi", value=default_temsilci, disabled=True)
                odeme      = st.text_input("Ödeme Şekli", value=default_odeme, disabled=True)
                aciklama   = st.text_area("Açıklama")
                durum      = st.selectbox("Durum", ["Beklemede","İptal","Faturası Kesildi","Siparişe Dönüştü"], index=0)
                pdf_file   = st.file_uploader("Proforma PDF", type="pdf")
                submitted  = st.form_submit_button("Kaydet")

                if submitted:
                    if not proforma_no.strip() or not vade_gun.strip():
                        st.error("Proforma No ve Vade (gün) boş olamaz!")
                    else:
                        # Aynı müşteri+proforma no duplike kontrolü
                        if ((df_proforma["Müşteri Adı"]==musteri_sec) & (df_proforma["Proforma No"].astype(str)==proforma_no.strip())).any():
                            st.warning("Bu Proforma No bu müşteri için zaten kayıtlı.")
                        else:
                            pdf_link = ""
                            if pdf_file and PROFORMA_PDF_FOLDER_ID:
                                fname = f"{musteri_sec}_{tarih}_{proforma_no}.pdf"
                                tmp = os.path.join(".", fname)
                                with open(tmp,"wb") as f: f.write(pdf_file.read())
                                gfile = drive.CreateFile({'title': fname, 'parents':[{'id': PROFORMA_PDF_FOLDER_ID}]})
                                gfile.SetContentFile(tmp); gfile.Upload()
                                pdf_link = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                                güvenli_sil(tmp)

                            new_row = {
                                "ID": str(uuid.uuid4()),
                                "Müşteri Adı": musteri_sec,
                                "Tarih": tarih,
                                "Proforma No": proforma_no.strip(),
                                "Tutar": tutar,
                                "Vade (gün)": vade_gun,
                                "Ülke": default_ulke,
                                "Satış Temsilcisi": default_temsilci,
                                "Ödeme Şekli": default_odeme,
                                "Açıklama": aciklama,
                                "Durum": "Beklemede" if durum!="Siparişe Dönüştü" else "Siparişe Dönüştü",
                                "PDF": pdf_link,
                                "Sipariş Formu": "",
                                "Sevk Durumu": "",
                                "Termin Tarihi": "",
                                "Ulaşma Tarihi": ""
                            }
                            df_proforma = pd.concat([df_proforma, pd.DataFrame([new_row])], ignore_index=True)
                            update_excel()
                            st.success("Proforma eklendi!")
                            st.rerun()

        # ============== ESKİ KAYIT / DÜZENLE / SİL / SİPARİŞE DÖNÜŞTÜR ==============
        elif islem == "Eski Kayıt / Düzenle":
            # Seçilen müşterinin beklemede + diğer durumları
            kayitlar = df_proforma[df_proforma["Müşteri Adı"] == musteri_sec].copy()
            if kayitlar.empty:
                st.info("Bu müşteriye ait proforma kaydı yok.")
            else:
                kayitlar["Tarih"] = pd.to_datetime(kayitlar["Tarih"], errors="coerce")
                st.dataframe(
                    kayitlar.sort_values("Tarih", ascending=False)[
                        ["Müşteri Adı","Proforma No","Tarih","Tutar","Durum","Vade (gün)","Sevk Durumu"]
                    ],
                    use_container_width=True
                )

                sec_id = st.selectbox(
                    "Proforma Seç",
                    options=kayitlar["ID"].tolist(),
                    format_func=lambda _id: f"{kayitlar.loc[kayitlar['ID']==_id,'Proforma No'].values[0]} | {kayitlar.loc[kayitlar['ID']==_id,'Tarih'].dt.strftime('%d/%m/%Y').values[0] if pd.notna(kayitlar.loc[kayitlar['ID']==_id,'Tarih'].values[0]) else ''}"
                )

                orj_mask = (df_proforma["ID"] == sec_id)
                if not orj_mask.any():
                    st.warning("Beklenmeyen hata: Kayıt bulunamadı.")
                else:
                    idx = df_proforma.index[orj_mask][0]
                    kayit = df_proforma.loc[idx]

                    if str(kayit.get("PDF","")).strip():
                        st.markdown(f"**Proforma PDF:** [Görüntüle]({kayit['PDF']})", unsafe_allow_html=True)

                    with st.form("edit_proforma"):
                        tarih_      = st.date_input("Tarih", value=(pd.to_datetime(kayit["Tarih"], errors="coerce").date() if pd.notna(pd.to_datetime(kayit["Tarih"], errors="coerce")) else datetime.date.today()))
                        proforma_no_= st.text_input("Proforma No", value=str(kayit["Proforma No"]))
                        tutar_      = st.text_input("Tutar (USD)", value=str(kayit["Tutar"]))
                        vade_gun_   = st.text_input("Vade (gün)", value=str(kayit["Vade (gün)"]))
                        aciklama_   = st.text_area("Açıklama", value=str(kayit["Açıklama"]))
                        durum_      = st.selectbox("Durum", ["Beklemede","Siparişe Dönüştü","İptal","Faturası Kesildi"],
                                                    index=["Beklemede","Siparişe Dönüştü","İptal","Faturası Kesildi"].index(kayit["Durum"]) if kayit["Durum"] in ["Beklemede","Siparişe Dönüştü","İptal","Faturası Kesildi"] else 0)
                        termin_     = st.date_input("Termin Tarihi", value=(pd.to_datetime(kayit.get("Termin Tarihi",""), errors="coerce").date() if pd.notna(pd.to_datetime(kayit.get("Termin Tarihi",""), errors="coerce")) else datetime.date.today()), key="termin_inp")
                        pdf_yeni    = st.file_uploader("Proforma PDF (güncelle - opsiyonel)", type="pdf")
                        colu, colm, cols = st.columns(3)
                        guncelle = colu.form_submit_button("Güncelle")
                        donustur = colm.form_submit_button("Siparişe Dönüştür (+ Sipariş Formu)")
                        sil      = cols.form_submit_button("Sil")

                    # --- GÜNCELLE ---
                    if guncelle:
                        pdf_final = str(kayit.get("PDF",""))
                        if pdf_yeni and PROFORMA_PDF_FOLDER_ID:
                            fname = f"{musteri_sec}_{tarih_}_{proforma_no_}.pdf"
                            tmp = os.path.join(".", fname)
                            with open(tmp,"wb") as f: f.write(pdf_yeni.read())
                            gfile = drive.CreateFile({'title': fname, 'parents':[{'id': PROFORMA_PDF_FOLDER_ID}]})
                            gfile.SetContentFile(tmp); gfile.Upload()
                            pdf_final = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                            güvenli_sil(tmp)

                        df_proforma.at[idx, "Tarih"] = tarih_
                        df_proforma.at[idx, "Proforma No"] = proforma_no_
                        df_proforma.at[idx, "Tutar"] = tutar_
                        df_proforma.at[idx, "Vade (gün)"] = vade_gun_
                        df_proforma.at[idx, "Açıklama"] = aciklama_
                        df_proforma.at[idx, "Durum"] = durum_ if durum_ != "Siparişe Dönüştü" else df_proforma.at[idx, "Durum"]
                        df_proforma.at[idx, "Termin Tarihi"] = termin_
                        df_proforma.at[idx, "PDF"] = pdf_final
                        update_excel()
                        st.success("Proforma güncellendi!")
                        st.rerun()

                    # --- SİPARİŞE DÖNÜŞTÜR (Sipariş Formu zorunlu) ---
                    if donustur:
                        with st.form(f"siparis_formu_upload_{sec_id}"):
                            st.info("Lütfen sipariş formunu (PDF) yükleyin ve kaydedin.")
                            siparis_formu_file = st.file_uploader("Sipariş Formu PDF", type="pdf", key=f"sf_{sec_id}")
                            kaydet_sf = st.form_submit_button("Sipariş Formunu Kaydet ve Dönüştür")

                        if kaydet_sf:
                            if siparis_formu_file is None:
                                st.error("Sipariş formu yüklenmeli.")
                            else:
                                sf_name = f"{musteri_sec}_{proforma_no_}_SiparisFormu_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                                tmp = os.path.join(".", sf_name)
                                with open(tmp,"wb") as f: f.write(siparis_formu_file.read())
                                gfile = drive.CreateFile({'title': sf_name, 'parents':[{'id': SIPARIS_FORMU_FOLDER_ID}]})
                                gfile.SetContentFile(tmp); gfile.Upload()
                                sf_url = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                                güvenli_sil(tmp)

                                df_proforma.at[idx, "Sipariş Formu"] = sf_url
                                df_proforma.at[idx, "Durum"] = "Siparişe Dönüştü"
                                df_proforma.at[idx, "Sevk Durumu"] = ""   # sevk akışı diğer menülerde
                                update_excel()
                                st.success("Sipariş formu kaydedildi ve durum 'Siparişe Dönüştü' olarak güncellendi!")
                                st.rerun()

                    # --- SİL ---
                    if sil:
                        df_proforma = df_proforma.drop(idx).reset_index(drop=True)
                        update_excel()
                        st.success("Kayıt silindi!")
                        st.rerun()


### ===========================
### --- SİPARİŞ OPERASYONLARI (ID tabanlı) ---
### ===========================

elif menu == "Sipariş Operasyonları":
    import uuid

    st.header("Güncel Sipariş Durumu")

    # ---- Kolon güvenliği + ID backfill ----
    gerekli = ["ID","Sevk Durumu","Termin Tarihi","Sipariş Formu","Ülke","Satış Temsilcisi","Ödeme Şekli","PDF","Durum","Tarih","Tutar","Müşteri Adı","Proforma No","Açıklama"]
    for c in gerekli:
        if c not in df_proforma.columns:
            df_proforma[c] = ""
    bos_id = df_proforma["ID"].astype(str).str.strip().isin(["","nan"])
    if bos_id.any():
        df_proforma.loc[bos_id, "ID"] = [str(uuid.uuid4()) for _ in range(bos_id.sum())]
        update_excel()

    # ---- Filtre: Siparişe dönmüş ama sevk edilmemiş/ulaşmamış kayıtlar
    siparisler = df_proforma[
        (df_proforma["Durum"] == "Siparişe Dönüştü")
        & (~df_proforma["Sevk Durumu"].isin(["Sevkedildi","Ulaşıldı"]))
    ].copy()

    if siparisler.empty:
        st.info("Henüz sevk edilmeyi bekleyen sipariş yok.")
        st.stop()

    # ---- Sıralama: Termin Tarihi
    siparisler["Termin Tarihi Order"] = pd.to_datetime(siparisler["Termin Tarihi"], errors="coerce")
    siparisler["Tarih"] = pd.to_datetime(siparisler["Tarih"], errors="coerce")
    siparisler = siparisler.sort_values(["Termin Tarihi Order","Tarih"], ascending=[True, True])

    # ---- Görünüm için format
    g = siparisler.copy()
    g["Tarih"] = g["Tarih"].dt.strftime("%d/%m/%Y")
    g["Termin Tarihi"] = pd.to_datetime(g["Termin Tarihi"], errors="coerce").dt.strftime("%d/%m/%Y")

    st.markdown("<h4 style='color:#219A41; font-weight:bold;'>Tüm Siparişe Dönüşenler</h4>", unsafe_allow_html=True)
    st.dataframe(
        g[["Tarih","Müşteri Adı","Termin Tarihi","Ülke","Satış Temsilcisi","Ödeme Şekli","Proforma No","Tutar","Açıklama"]],
        use_container_width=True
    )

    # ================= Termin Tarihi Güncelle =================
    st.markdown("#### Termin Tarihi Güncelle")
    sec_id_termin = st.selectbox(
        "Termin Tarihi Girilecek Sipariş",
        options=siparisler["ID"].tolist(),
        format_func=lambda _id: f"{siparisler.loc[siparisler['ID']==_id, 'Müşteri Adı'].values[0]} - {siparisler.loc[siparisler['ID']==_id, 'Proforma No'].values[0]}"
    )
    mask_termin = (df_proforma["ID"] == sec_id_termin)
    mevcut_termin = pd.to_datetime(df_proforma.loc[mask_termin, "Termin Tarihi"].values[0] if mask_termin.any() else None, errors="coerce")
    default_termin = (mevcut_termin.date() if pd.notna(mevcut_termin) else datetime.date.today())
    yeni_termin = st.date_input("Termin Tarihi", value=default_termin, key="termin_input")

    if st.button("Termin Tarihini Kaydet"):
        df_proforma.loc[mask_termin, "Termin Tarihi"] = yeni_termin
        update_excel()
        st.success("Termin tarihi kaydedildi!")
        st.rerun()

    # ================= Sevk Et (ETA’ya gönder) =================
    st.markdown("#### Siparişi Sevk Et (ETA İzleme Kaydına Gönder)")
    sec_id_sevk = st.selectbox(
        "Sevk Edilecek Sipariş",
        options=siparisler["ID"].tolist(),
        format_func=lambda _id: f"{siparisler.loc[siparisler['ID']==_id, 'Müşteri Adı'].values[0]} - {siparisler.loc[siparisler['ID']==_id, 'Proforma No'].values[0]}",
        key="sevk_sec"
    )
    if st.button("Sevkedildi → ETA İzlemeye Ekle"):
        # Proforma'dan bilgiler
        row = df_proforma.loc[df_proforma["ID"] == sec_id_sevk].iloc[0]
        # ETA kolon güvenliği
        for col in ["Müşteri Adı","Proforma No","ETA Tarihi","Açıklama"]:
            if col not in df_eta.columns:
                df_eta[col] = ""
        # ETA'ya ekle (varsa güncelleme)
        filt = (df_eta["Müşteri Adı"] == row["Müşteri Adı"]) & (df_eta["Proforma No"] == row["Proforma No"])
        if filt.any():
            df_eta.loc[filt, "Açıklama"] = row.get("Açıklama","")
        else:
            df_eta = pd.concat([df_eta, pd.DataFrame([{
                "Müşteri Adı": row["Müşteri Adı"],
                "Proforma No": row["Proforma No"],
                "ETA Tarihi": "",
                "Açıklama": row.get("Açıklama","")
            }])], ignore_index=True)
        # Proforma'yı işaretle
        df_proforma.loc[df_proforma["ID"] == sec_id_sevk, "Sevk Durumu"] = "Sevkedildi"
        update_excel()
        st.success("Sipariş sevkedildi ve ETA takibine gönderildi!")
        st.rerun()

    # ================= Beklemeye Al (Geri Çağır) =================
    st.markdown("#### Siparişi Beklemeye Al (Geri Çağır)")
    sec_id_geri = st.selectbox(
        "Beklemeye Alınacak Sipariş",
        options=siparisler["ID"].tolist(),
        format_func=lambda _id: f"{siparisler.loc[siparisler['ID']==_id, 'Müşteri Adı'].values[0]} - {siparisler.loc[siparisler['ID']==_id, 'Proforma No'].values[0]}",
        key="geri_sec"
    )
    if st.button("Beklemeye Al / Geri Çağır"):
        m = (df_proforma["ID"] == sec_id_geri)
        df_proforma.loc[m, ["Durum","Sevk Durumu","Termin Tarihi"]] = ["Beklemede","",""]
        update_excel()
        st.success("Sipariş tekrar bekleyen proformalar listesine alındı!")
        st.rerun()

    # ================= Linkler + Toplam =================
    st.markdown("#### Tıklanabilir Proforma ve Sipariş Formu Linkleri")
    for _, r in siparisler.iterrows():
        links = []
        if str(r.get("PDF","")).strip():
            links.append(f"[Proforma PDF: {r['Proforma No']}]({r['PDF']})")
        if str(r.get("Sipariş Formu","")).strip():
            fname = f"{r['Müşteri Adı']}__{r['Proforma No']}__SiparisFormu"
            links.append(f"[Sipariş Formu: {fname}]({r['Sipariş Formu']})")
        if links:
            st.markdown(" - " + " | ".join(links), unsafe_allow_html=True)

    # Toplam bekleyen sevk tutarı (akıllı parse)
    def smart_to_num(x):
        if pd.isna(x): return 0.0
        s = str(x).strip()
        for sym in ["USD","$","€","EUR","₺","TL","tl","Tl"]: s = s.replace(sym,"")
        s = s.replace("\u00A0","").replace(" ","")
        try: return float(s)
        except: pass
        if "," in s:
            try: return float(s.replace(".","").replace(",","."))
            except: pass
        return 0.0

    toplam = float(siparisler["Tutar"].apply(smart_to_num).sum())
    st.markdown(f"<div style='color:#219A41; font-weight:bold;'>*Toplam Bekleyen Sevk: {toplam:,.2f} USD*</div>", unsafe_allow_html=True)

### ===========================
### --- İHRACAT EVRAKLARI MENÜSÜ ---
### ===========================

elif menu == "İhracat Evrakları":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>İhracat Evrakları</h2>", unsafe_allow_html=True)

    for col in [
        "Proforma No", "Vade (gün)", "Vade Tarihi", "Ülke", "Satış Temsilcisi", "Ödeme Şekli",
        "Commercial Invoice", "Sağlık Sertifikası", "Packing List",
        "Konşimento", "İhracat Beyannamesi", "Fatura PDF", "Sipariş Formu",
        "Yük Resimleri", "EK Belgeler", "Ödendi"
    ]:
        if col not in df_evrak.columns:
            df_evrak[col] = "" if col != "Ödendi" else False

    musteri_secenek = sorted(df_proforma["Müşteri Adı"].dropna().unique().tolist())
    secilen_musteri = st.selectbox("Müşteri Seç", [""] + musteri_secenek)
    secilen_proformalar = df_proforma[df_proforma["Müşteri Adı"] == secilen_musteri] if secilen_musteri else pd.DataFrame()
    proforma_no_sec = ""
    if not secilen_proformalar.empty:
        proforma_no_sec = st.selectbox("Proforma No Seç", [""] + secilen_proformalar["Proforma No"].astype(str).tolist())
    else:
        proforma_no_sec = st.selectbox("Proforma No Seç", [""])

    musteri_info = df_musteri[df_musteri["Müşteri Adı"] == secilen_musteri]
    ulke = musteri_info["Ülke"].values[0] if not musteri_info.empty else ""
    temsilci = musteri_info["Satış Temsilcisi"].values[0] if not musteri_info.empty else ""
    odeme = musteri_info["Ödeme Şekli"].values[0] if not musteri_info.empty else ""

    # --- 1. Önceki evrakların linklerini çek ---
    onceki_evrak = df_evrak[
        (df_evrak["Müşteri Adı"] == secilen_musteri) &
        (df_evrak["Proforma No"] == proforma_no_sec)
    ]

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
        tutar = st.text_input("Fatura Tutarı (USD)")
        vade_gun = ""
        vade_tarihi = ""
        if secilen_musteri and proforma_no_sec:
            proforma_kayit = df_proforma[(df_proforma["Müşteri Adı"] == secilen_musteri) & (df_proforma["Proforma No"] == proforma_no_sec)]
            if not proforma_kayit.empty:
                vade_gun = proforma_kayit.iloc[0].get("Vade (gün)", "")
                try:
                    vade_gun_int = int(vade_gun)
                    vade_tarihi = fatura_tarih + datetime.timedelta(days=vade_gun_int)
                except:
                    vade_tarihi = ""
        st.text_input("Vade (gün)", value=vade_gun, key="vade_gun", disabled=True)
        st.date_input("Vade Tarihi", value=vade_tarihi if vade_tarihi else fatura_tarih, key="vade_tarihi", disabled=True)
        st.text_input("Ülke", value=ulke, disabled=True)
        st.text_input("Satış Temsilcisi", value=temsilci, disabled=True)
        st.text_input("Ödeme Şekli", value=odeme, disabled=True)
        
        # --- 2. Evrak yükleme alanları ve eski dosya linkleri ---
        uploaded_files = {}
        for col, label in evrak_tipleri:
            uploaded_files[col] = st.file_uploader(label, type="pdf", key=f"{col}_upload")
            prev_url = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""
            st.markdown(file_link_html(label, prev_url), unsafe_allow_html=True)
        
        submitted = st.form_submit_button("Kaydet")

        if submitted:
            if not fatura_no.strip() or not tutar.strip():
                st.error("Fatura No ve Tutar boş olamaz!")
            else:
                # Dosya yükleme ve eski dosya kontrolü
                file_urls = {}
                for col, label in evrak_tipleri:
                    uploaded_file = uploaded_files[col]
                    # Önce yeni dosya yüklendiyse Drive'a yükle, yoksa eski dosya linkini al
                    if uploaded_file:
                        file_name = f"{col}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                        temp_path = os.path.join(".", file_name)
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.read())
                        gfile = drive.CreateFile({'title': file_name, 'parents': [{'id': "14FTE1oSeIeJ6Y_7C0oQyZPKC8dK8hr1J"}]})
                        gfile.SetContentFile(temp_path)
                        gfile.Upload()
                        file_urls[col] = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
                        try:
                            os.remove(temp_path)
                        except:
                            pass
                    else:
                        file_urls[col] = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""

                new_row = {
                    "Müşteri Adı": secilen_musteri,
                    "Proforma No": proforma_no_sec,
                    "Fatura No": fatura_no,
                    "Fatura Tarihi": fatura_tarih,
                    "Tutar": tutar,
                    "Vade (gün)": vade_gun,
                    "Vade Tarihi": vade_tarihi,
                    "Ülke": ulke,
                    "Satış Temsilcisi": temsilci,
                    "Ödeme Şekli": odeme,
                    "Commercial Invoice": file_urls.get("Commercial Invoice", ""),
                    "Sağlık Sertifikası": file_urls.get("Sağlık Sertifikası", ""),
                    "Packing List": file_urls.get("Packing List", ""),
                    "Konşimento": file_urls.get("Konşimento", ""),
                    "İhracat Beyannamesi": file_urls.get("İhracat Beyannamesi", ""),
                    "Fatura PDF": "",  # Gerekirse ekle
                    "Sipariş Formu": "",
                    "Yük Resimleri": "",
                    "EK Belgeler": "",
                    "Ödendi": False,
                }
                df_evrak = pd.concat([df_evrak, pd.DataFrame([new_row])], ignore_index=True)
                update_excel()
                st.success("Evrak eklendi!")
                st.rerun()

### ===========================
### --- İHRACAT EVRAKLARI MENÜSÜ (ID + tekilleştirme) ---
### ===========================

elif menu == "İhracat Evrakları":
    import uuid, tempfile

    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>İhracat Evrakları</h2>", unsafe_allow_html=True)

    # ---- Sütun güvenliği + benzersiz ID ----
    gerekli_kolonlar = [
        "ID","Müşteri Adı","Proforma No","Fatura No","Fatura Tarihi","Tutar",
        "Vade (gün)","Vade Tarihi","Ülke","Satış Temsilcisi","Ödeme Şekli",
        "Commercial Invoice","Sağlık Sertifikası","Packing List","Konşimento",
        "İhracat Beyannamesi","Fatura PDF","Sipariş Formu","Yük Resimleri",
        "EK Belgeler","Ödendi"
    ]
    for c in gerekli_kolonlar:
        if c not in df_evrak.columns:
            df_evrak[c] = False if c == "Ödendi" else ""

    bos_id_mask = df_evrak["ID"].astype(str).str.strip().isin(["","nan"])
    if bos_id_mask.any():
        df_evrak.loc[bos_id_mask, "ID"] = [str(uuid.uuid4()) for _ in range(bos_id_mask.sum())]
        update_excel()

    # ---- Müşteri / Proforma seçimleri ----
    musteri_secenek = sorted(df_proforma["Müşteri Adı"].dropna().astype(str).unique().tolist())
    secilen_musteri = st.selectbox("Müşteri Seç", [""] + musteri_secenek)

    if secilen_musteri:
        p_list = df_proforma.loc[df_proforma["Müşteri Adı"] == secilen_musteri, "Proforma No"].dropna().astype(str).unique().tolist()
        proforma_no_sec = st.selectbox("Proforma No Seç", [""] + sorted(p_list))
    else:
        proforma_no_sec = ""

    # ---- Müşteri varsayılanları (ülke/temsilci/ödeme) ----
    musteri_info = df_musteri[df_musteri["Müşteri Adı"] == secilen_musteri]
    ulke = musteri_info["Ülke"].values[0] if not musteri_info.empty else ""
    temsilci = musteri_info["Satış Temsilcisi"].values[0] if not musteri_info.empty else ""
    odeme = musteri_info["Ödeme Şekli"].values[0] if not musteri_info.empty else ""

    # ---- Proforma'dan Vade (gün) çek ve Vade Tarihi hesapla ----
    vade_gun = ""
    if secilen_musteri and proforma_no_sec:
        pr = df_proforma[(df_proforma["Müşteri Adı"] == secilen_musteri) & (df_proforma["Proforma No"] == proforma_no_sec)]
        if not pr.empty:
            vade_gun = pr.iloc[0].get("Vade (gün)", "")

    # ---- Eski evrak linkleri (aynı müşteri+proforma altında son satır) ----
    onceki_evrak = df_evrak[(df_evrak["Müşteri Adı"] == secilen_musteri) & (df_evrak["Proforma No"] == proforma_no_sec)].tail(1)

    def file_link_html(label, url):
        return f'<div style="margin-top:-6px;"><a href="{url}" target="_blank" style="color:#219A41;">[Daha önce yüklenmiş {label}]</a></div>' if url else \
               '<div style="margin-top:-6px; color:#b00020; font-size:0.95em;">(Daha önce yüklenmemiş)</div>'

    evrak_tipleri = [
        ("Commercial Invoice",  "Commercial Invoice PDF"),
        ("Sağlık Sertifikası",  "Sağlık Sertifikası PDF"),
        ("Packing List",        "Packing List PDF"),
        ("Konşimento",          "Konşimento PDF"),
        ("İhracat Beyannamesi", "İhracat Beyannamesi PDF"),
        ("Fatura PDF",          "Fatura PDF")  # eklendi
    ]

    # ---- Drive'a yükleme yardımcı fonksiyonu ----
    def upload_to_drive(parent_folder_id: str, filename: str, bytes_data: bytes) -> str:
        meta = {'title': filename, 'parents': [{'id': parent_folder_id}]}
        gfile = drive.CreateFile(meta)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(bytes_data)
            tmp_path = tmp.name
        gfile.SetContentFile(tmp_path)
        try:
            gfile.Upload()  # personal drive: supportsAllDrives gerekmez
            link = f"https://drive.google.com/file/d/{gfile['id']}/view?usp=sharing"
        finally:
            try: os.remove(tmp_path)
            except: pass
        return link

    # ---- Form ----
    with st.form("add_evrak"):
        fatura_no = st.text_input("Fatura No")
        fatura_tarih = st.date_input("Fatura Tarihi", value=datetime.date.today())
        tutar = st.text_input("Fatura Tutarı (USD)")
        # Vade (gün) & vade tarihi gösterimi
        st.text_input("Vade (gün)", value=str(vade_gun), key="vade_gun", disabled=True)

        try:
            vade_int = int(vade_gun)
            vade_tarihi_hesap = fatura_tarih + datetime.timedelta(days=vade_int)
        except:
            vade_tarihi_hesap = None
        st.date_input("Vade Tarihi", value=(vade_tarihi_hesap or fatura_tarih), key="vade_tarihi", disabled=True)

        st.text_input("Ülke", value=ulke, disabled=True)
        st.text_input("Satış Temsilcisi", value=temsilci, disabled=True)
        st.text_input("Ödeme Şekli", value=odeme, disabled=True)

        # Evrak yüklemeleri + eski link gösterimleri
        uploaded_files = {}
        for col, label in evrak_tipleri:
            uploaded_files[col] = st.file_uploader(label, type="pdf", key=f"{col}_upload")
            prev_url = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""
            st.markdown(file_link_html(label, prev_url), unsafe_allow_html=True)

        submitted = st.form_submit_button("Kaydet")

    if submitted:
        if not (secilen_musteri and proforma_no_sec and fatura_no.strip() and tutar.strip()):
            st.error("Müşteri, Proforma No, Fatura No ve Tutar zorunludur.")
            st.stop()

        # 1) Dosyaları Drive'a yükle (varsa). Yoksa eski linki koru.
        file_urls = {}
        for col, _label in evrak_tipleri:
            upfile = uploaded_files[col]
            if upfile:
                clean_name = re.sub(r'[\\/*?:"<>|]+', "_", f"{secilen_musteri}__{proforma_no_sec}__{col}__{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
                file_urls[col] = upload_to_drive(EVRAK_KLASOR_ID, clean_name, upfile.read())
            else:
                file_urls[col] = onceki_evrak.iloc[0][col] if not onceki_evrak.empty else ""

        # 2) Tekilleştirme: aynı (Müşteri, Proforma, Fatura No) varsa GÜNCELLE; yoksa EKLE
        key_mask = (
            (df_evrak["Müşteri Adı"] == secilen_musteri) &
            (df_evrak["Proforma No"] == proforma_no_sec) &
            (df_evrak["Fatura No"] == fatura_no)
        )

        # Vade Tarihi yazımı
        vade_tarihi_yaz = vade_tarihi_hesap if vade_tarihi_hesap else ""

        if key_mask.any():
            idx = df_evrak[key_mask].index[0]
            df_evrak.at[idx, "Fatura Tarihi"]    = fatura_tarih
            df_evrak.at[idx, "Tutar"]            = tutar
            df_evrak.at[idx, "Vade (gün)"]       = vade_gun
            df_evrak.at[idx, "Vade Tarihi"]      = vade_tarihi_yaz
            df_evrak.at[idx, "Ülke"]             = ulke
            df_evrak.at[idx, "Satış Temsilcisi"] = temsilci
            df_evrak.at[idx, "Ödeme Şekli"]      = odeme
            for col, _ in evrak_tipleri:
                df_evrak.at[idx, col] = file_urls.get(col, "")
            islem = "güncellendi"
        else:
            new_row = {
                "ID": str(uuid.uuid4()),
                "Müşteri Adı": secilen_musteri,
                "Proforma No": proforma_no_sec,
                "Fatura No": fatura_no,
                "Fatura Tarihi": fatura_tarih,
                "Tutar": tutar,
                "Vade (gün)": vade_gun,
                "Vade Tarihi": vade_tarihi_yaz,
                "Ülke": ulke,
                "Satış Temsilcisi": temsilci,
                "Ödeme Şekli": odeme,
                "Ödendi": False,
                **{col: file_urls.get(col, "") for col, _ in evrak_tipleri},
                "Sipariş Formu": "",
                "Yük Resimleri": "",
                "EK Belgeler": "",
            }
            df_evrak = pd.concat([df_evrak, pd.DataFrame([new_row])], ignore_index=True)
            islem = "eklendi"

        update_excel()
        st.success(f"Evrak {islem}!")
        st.rerun()


### ===========================
### --- TAHSİLAT PLANI MENÜSÜ ---
### ===========================

elif menu == "Tahsilat Planı":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Tahsilat Planı</h2>", unsafe_allow_html=True)

    # Gerekli kolonlar yoksa ekle
    for c in ["Müşteri Adı","Fatura No","Vade Tarihi","Tutar_num","Ülke","Satış Temsilcisi","Ödeme Şekli","Ödendi"]:
        if c not in df_evrak.columns:
            df_evrak[c] = "" if c != "Ödendi" else False

    # Sadece vadesi olan kayıtlar
    vade_df = df_evrak.copy()
    vade_df["Vade Tarihi"] = pd.to_datetime(vade_df["Vade Tarihi"], errors="coerce")
    vade_df = vade_df[vade_df["Vade Tarihi"].notna()]

    if vade_df.empty:
        st.info("Vade tarihi girilmiş kayıt bulunmuyor.")
    else:
        today = pd.Timestamp.today().normalize()
        vade_df["Kalan Gün"] = (vade_df["Vade Tarihi"] - today).dt.days

        # Ödenmemişler üzerinden özet kutucukları
        acik = vade_df[~vade_df["Ödendi"]].copy()
        vadesi_gelmemis = acik[acik["Kalan Gün"] > 0]
        bugun = acik[acik["Kalan Gün"] == 0]
        gecikmis = acik[acik["Kalan Gün"] < 0]

        c1.metric("Vadeleri Gelmeyen", f"{float(vadesi_gelmemis['Tutar_num'].sum()):,.2f} USD", f"{len(vadesi_gelmemis)} Fatura")
        c2.metric("Bugün Vadesi",   f"{float(bugun['Tutar_num'].sum()):,.2f} USD", f"{len(bugun)} Fatura")
        c3.metric("Gecikmiş Ödemeler",        f"{float(gecikmis['Tutar_num'].sum()):,.2f} USD", f"{len(gecikmis)} Fatura")

        st.markdown("---")

        # Filtreler
        f1, f2, f3 = st.columns([1.4, 1.2, 1.2])
        ulke_f = f1.multiselect("Ülke", sorted([u for u in vade_df["Ülke"].dropna().unique() if str(u).strip()]))
        tem_f  = f2.multiselect("Satış Temsilcisi", sorted([t for t in vade_df["Satış Temsilcisi"].dropna().unique() if str(t).strip()]))
        durum_f = f3.selectbox("Ödeme Durumu", ["Ödenmemiş (varsayılan)", "Hepsi", "Sadece Ödenmiş"], index=0)

        view = vade_df.copy()
        if ulke_f:
            view = view[view["Ülke"].isin(ulke_f)]
        if tem_f:
            view = view[view["Satış Temsilcisi"].isin(tem_f)]
        if durum_f == "Ödenmemiş (varsayılan)":
            view = view[~view["Ödendi"]]
        elif durum_f == "Sadece Ödenmiş":
            view = view[view["Ödendi"]]

        # Görüntü tablosu (görsel kopya)
        show = view.copy()
        show["Vade Tarihi"] = pd.to_datetime(show["Vade Tarihi"]).dt.strftime("%d/%m/%Y")
        show["Tutar"] = show["Tutar_num"].map(lambda x: f"{float(x):,.2f} USD")
        cols = ["Müşteri Adı","Ülke","Satış Temsilcisi","Fatura No","Vade Tarihi","Kalan Gün","Tutar","Ödendi"]
        cols = [c for c in cols if c in show.columns]
        st.dataframe(show[cols].sort_values(["Kalan Gün","Vade Tarihi"]), use_container_width=True)

        st.markdown("#### Ödeme Durumu Güncelle")
        if not view.empty:
            # ID yoksa güvenli seçim için bir satır anahtarı oluşturalım
            view = view.reset_index(drop=False).rename(columns={"index":"_row"})
            sec = st.selectbox(
                "Kayıt Seç",
                options=view["_row"].tolist(),
                format_func=lambda i: f"{view.loc[view['_row']==i,'Müşteri Adı'].values[0]} | {view.loc[view['_row']==i,'Fatura No'].values[0]}"
            )

            odendi_mi = st.checkbox("Ödendi olarak işaretle")
            if st.button("Kaydet / Güncelle"):
                # Ana df_evrak’taki satıra yaz
                # _row önceki index, aynı sırayı df_evrak’ta güncellemek için kullanıyoruz
                ana_index = view.loc[view["_row"] == sec, "_row"].values[0]
                df_evrak.at[ana_index, "Ödendi"] = bool(odendi_mi)
                update_excel()
                st.success("Ödeme durumu güncellendi!")
                st.rerun()

### ===========================
### --- ETA İZLEME MENÜSÜ ---
### ===========================

elif menu == "ETA İzleme":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>ETA İzleme</h2>", unsafe_allow_html=True)

    import re, tempfile

    # ---- Sabitler ----
    ROOT_EXPORT_FOLDER_ID = "14FTE1oSeIeJ6Y_7C0oQyZPKC8dK8hr1J"  # İhracat Evrakları ana klasör ID (MY DRIVE)

    # ---- Güvenlik: gerekli kolonlar ----
    for col in ["Sevk Durumu", "Proforma No", "Sevk Tarihi", "Ulaşma Tarihi"]:
        if col not in df_proforma.columns:
            df_proforma[col] = ""

    for col in ["Müşteri Adı", "Proforma No", "ETA Tarihi", "Açıklama"]:
        if col not in df_eta.columns:
            df_eta[col] = ""

    # ---- Yardımcılar ----
    def safe_name(text, maxlen=120):
        s = str(text or "").strip()
        s = re.sub(r"\s+", " ", s)            # çoklu boşluk -> tek
        s = s.replace(" ", "_")               # boşluk -> _
        s = re.sub(r'[\\/*?:"<>|]+', "_", s)  # Drive yasak karakterleri
        return s[:maxlen]

    def get_or_create_folder_by_name(name: str, parent_id: str) -> str:
        """
        Parent altında isme göre klasör bulur; yoksa oluşturur.
        (My Drive — Shared Drive kullanılmıyor)
        """
        q = (
            f"title = '{name}' and mimeType = 'application/vnd.google-apps.folder' "
            f"and '{parent_id}' in parents and trashed = false"
        )
        try:
            lst = drive.ListFile({'q': q}).GetList()
            if lst:
                return lst[0]['id']
            meta = {
                'title': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [{'id': parent_id}],
            }
            f = drive.CreateFile(meta)
            f.Upload()
            return f['id']
        except Exception as e:
            st.error(f"Klasör oluşturma/arama hatası: {e}")
            return ""

    def resolve_folder_date(musteri: str, proforma_no: str) -> datetime.date:
        """
        Klasör adı için kullanılacak tarihi belirler:
        1) Proforma 'Sevk Tarihi' varsa o,
        2) yoksa ilgili ETA kaydındaki 'ETA Tarihi',
        3) o da yoksa bugün.
        """
        # Sevk Tarihi
        pr_mask = (df_proforma["Müşteri Adı"] == musteri) & (df_proforma["Proforma No"] == proforma_no)
        sevk_ts = None
        if pr_mask.any():
            try:
                sevk_ts = pd.to_datetime(df_proforma.loc[pr_mask, "Sevk Tarihi"].values[0], errors="coerce")
            except Exception:
                sevk_ts = None
        if pd.notnull(sevk_ts):
            try:
                return sevk_ts.date()
            except Exception:
                pass

        # ETA Tarihi
        eta_mask = (df_eta["Müşteri Adı"] == musteri) & (df_eta["Proforma No"] == proforma_no)
        eta_ts = None
        if eta_mask.any():
            try:
                eta_ts = pd.to_datetime(df_eta.loc[eta_mask, "ETA Tarihi"].values[0], errors="coerce")
            except Exception:
                eta_ts = None
        if pd.notnull(eta_ts):
            try:
                return eta_ts.date()
            except Exception:
                pass

        # Default: bugün
        return datetime.date.today()

    def get_loading_photos_folder(musteri_adi: str, tarih: datetime.date) -> str:
        """
        Ana klasör altında <Müşteri_Adi>_<YYYY-MM-DD> / Yükleme Resimleri hiyerarşisini hazırlar ve döndürür.
        """
        if not ROOT_EXPORT_FOLDER_ID:
            return ""
        folder_name = f"{safe_name(musteri_adi)}_{tarih.strftime('%Y-%m-%d')}"
        parent = get_or_create_folder_by_name(folder_name, ROOT_EXPORT_FOLDER_ID)
        if not parent:
            return ""
        yukleme = get_or_create_folder_by_name("Yükleme Resimleri", parent)
        return yukleme

    # ==== SEVKEDİLENLER (Yolda) ====
    sevkedilenler = df_proforma[df_proforma["Sevk Durumu"] == "Sevkedildi"].copy()
    if sevkedilenler.empty:
        st.info("Sevkedilmiş sipariş bulunmuyor.")
    else:
        # Seçim
        secenekler = sevkedilenler[["Müşteri Adı", "Proforma No"]].drop_duplicates()
        secenekler["sec_text"] = secenekler["Müşteri Adı"] + " - " + secenekler["Proforma No"]
        selected = st.selectbox("Sevkedilen Sipariş Seç", secenekler["sec_text"])
        selected_row = secenekler[secenekler["sec_text"] == selected].iloc[0]
        sec_musteri = selected_row["Müşteri Adı"]
        sec_proforma = selected_row["Proforma No"]

        # === Klasör tarihi (Sevk/ETA/bugün) + Müşteri adı ===
        klasor_tarih = resolve_folder_date(sec_musteri, sec_proforma)

        # ========== YÜKLEME FOTOĞRAFLARI (Müşteri_Adi + Tarih → “Yükleme Resimleri”) ==========
        st.markdown("#### Yükleme Fotoğrafları (Müşteri + Tarih bazlı)")

        hedef_klasor = get_loading_photos_folder(sec_musteri, klasor_tarih)
        if not hedef_klasor:
            st.error("Klasör hiyerarşisi oluşturulamadı.")
        else:
            # 1) Klasörü yeni sekmede aç butonu
            drive_link = f"https://drive.google.com/drive/folders/{hedef_klasor}?usp=sharing"
            st.markdown(f"[Klasörü yeni sekmede aç]({drive_link})")

            # 2) Panel içinde gömülü görüntüleme – sadece gezinme
            with st.expander(f"Panelde klasörü görüntüle – {sec_musteri} / {klasor_tarih.strftime('%Y-%m-%d')}"):
                embed = f"https://drive.google.com/embeddedfolderview?id={hedef_klasor}#grid"
                st.markdown(
                    f'<iframe src="{embed}" width="100%" height="520" frameborder="0" '
                    f'style="border:1px solid #eee; border-radius:12px;"></iframe>',
                    unsafe_allow_html=True
                )

            # 3) Mevcut dosyaları say ve özetle (ilk 10 isim)
            try:
                mevcut_dosyalar = drive.ListFile({
                    'q': f"'{hedef_klasor}' in parents and trashed = false"
                }).GetList()
            except Exception as e:
                mevcut_dosyalar = []
                st.warning(f"Dosyalar listelenemedi: {e}")

            if mevcut_dosyalar:
                st.caption(f"Bu klasörde {len(mevcut_dosyalar)} dosya var.")
                names = [f"- {f['title']}" for f in mevcut_dosyalar[:10]]
                st.write("\n".join(names) if names else "")
                if len(mevcut_dosyalar) > 10:
                    st.write("…")

            # 4) (OPSİYONEL) Dosya Ekle – duplike önleme (aynı isim SKIP)
            with st.expander("Dosya Ekle (opsiyonel, duplike önleme)"):
                files = st.file_uploader(
                    "Yüklenecek dosyaları seçin",
                    type=["pdf", "jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=True,
                    key=f"yuk_resimleri_dedupe_{sec_musteri}_{klasor_tarih}"
                )

                if files:
                    var_olan_isimler = set(f["title"] for f in mevcut_dosyalar)
                    yuklenen_say = 0
                    atlanan_duplike = 0

                    for up in files:
                        suffix = os.path.splitext(up.name)[1].lower() or ""
                        base = os.path.splitext(up.name)[0]
                        fname = safe_name(base) + suffix

                        if fname in var_olan_isimler:
                            atlanan_duplike += 1
                            continue

                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
                            fp.write(up.read())
                            temp_path = fp.name

                        meta = {'title': fname, 'parents': [{'id': hedef_klasor}]}
                        gfile = drive.CreateFile(meta)
                        gfile.SetContentFile(temp_path)
                        try:
                            gfile.Upload()
                            yuklenen_say += 1
                            var_olan_isimler.add(fname)
                        except Exception as e:
                            st.error(f"{up.name} yüklenemedi: {e}")
                        finally:
                            try: os.remove(temp_path)
                            except: pass

                    if yuklenen_say:
                        update_excel()
                        st.success(f"{yuklenen_say} yeni dosya yüklendi.")
                        if atlanan_duplike:
                            st.info(f"{atlanan_duplike} dosya aynı isimle bulunduğu için atlandı.")
                        st.rerun()
                    else:
                        if atlanan_duplike and not yuklenen_say:
                            st.warning("Tüm dosyalar klasörde zaten mevcut (isimler aynı).")

        st.markdown("---")

        # ========== ETA Düzenleme ==========
        # Önceden ETA girilmiş mi?
        filtre = (df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma)
        if filtre.any():
            mevcut_eta = df_eta.loc[filtre, "ETA Tarihi"].values[0]
            mevcut_aciklama = df_eta.loc[filtre, "Açıklama"].values[0]
        else:
            mevcut_eta = ""
            mevcut_aciklama = ""

        with st.form("edit_eta"):
            try:
                varsayilan_eta = pd.to_datetime(mevcut_eta).date() if mevcut_eta and pd.notnull(mevcut_eta) and str(mevcut_eta) != "NaT" else datetime.date.today()
            except Exception:
                varsayilan_eta = datetime.date.today()
            eta_tarih = st.date_input("ETA Tarihi", value=varsayilan_eta)
            aciklama = st.text_area("Açıklama", value=mevcut_aciklama)
            guncelle = st.form_submit_button("ETA'yı Kaydet/Güncelle")
            ulasti = st.form_submit_button("Ulaştı")
            geri_al = st.form_submit_button("Sevki Geri Al")

            if guncelle:
                if filtre.any():
                    df_eta.loc[filtre, "ETA Tarihi"] = eta_tarih
                    df_eta.loc[filtre, "Açıklama"] = aciklama
                else:
                    new_row = {
                        "Müşteri Adı": sec_musteri,
                        "Proforma No": sec_proforma,
                        "ETA Tarihi": eta_tarih,
                        "Açıklama": aciklama
                    }
                    df_eta = pd.concat([df_eta, pd.DataFrame([new_row])], ignore_index=True)
                update_excel()
                st.success("ETA kaydedildi/güncellendi!")
                st.rerun()

            if ulasti:
                # Ulaşıldı: ETA listesinden çıkar, proforma'da Sevk Durumu "Ulaşıldı" ve bugünün tarihi "Ulaşma Tarihi" olarak kaydet
                df_eta = df_eta[~((df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma))]
                idx = df_proforma[(df_proforma["Müşteri Adı"] == sec_musteri) & (df_proforma["Proforma No"] == sec_proforma)].index
                if len(idx) > 0:
                    df_proforma.at[idx[0], "Sevk Durumu"] = "Ulaşıldı"
                    df_proforma.at[idx[0], "Ulaşma Tarihi"] = datetime.date.today()
                update_excel()
                st.success("Sipariş 'Ulaşıldı' olarak işaretlendi ve ETA takibinden çıkarıldı!")
                st.rerun()

            if geri_al:
                # Siparişi geri al: ETA'dan çıkar, proforma'da sevk durumunu boş yap (Sipariş Operasyonları'na döner)
                df_eta = df_eta[~((df_eta["Müşteri Adı"] == sec_musteri) & (df_eta["Proforma No"] == sec_proforma))]
                idx = df_proforma[(df_proforma["Müşteri Adı"] == sec_musteri) & (df_proforma["Proforma No"] == sec_proforma)].index
                if len(idx) > 0:
                    df_proforma.at[idx[0], "Sevk Durumu"] = ""
                update_excel()
                st.success("Sevkiyat geri alındı! Sipariş tekrar Sipariş Operasyonları'na gönderildi.")
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
        tablo = df_eta[["Müşteri Adı", "Proforma No", "ETA Tarihi", "Kalan Gün", "Açıklama"]].copy()
        tablo = tablo.sort_values(["ETA Tarihi", "Müşteri Adı", "Proforma No"], ascending=[True, True, True])
        st.dataframe(tablo, use_container_width=True)

        st.markdown("##### ETA Kaydı Sil")
        silinecekler = df_eta.index.tolist()
        sil_sec = st.selectbox("Silinecek Kaydı Seçin", options=silinecekler,
            format_func=lambda i: f"{df_eta.at[i, 'Müşteri Adı']} - {df_eta.at[i, 'Proforma No']}")
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

        # Ulaşma tarihi düzenleme
        try:
            current_ulasma = pd.to_datetime(row.get("Ulaşma Tarihi", None)).date()
            if pd.isnull(current_ulasma) or str(current_ulasma) == "NaT":
                current_ulasma = datetime.date.today()
        except Exception:
            current_ulasma = datetime.date.today()

        new_ulasma_tarih = st.date_input("Ulaşma Tarihi", value=current_ulasma, key="ulasan_guncelle")
        if st.button("Ulaşma Tarihini Kaydet"):
            idx = df_proforma[(df_proforma["Müşteri Adı"] == row["Müşteri Adı"]) & 
                              (df_proforma["Proforma No"] == row["Proforma No"])].index
            if len(idx) > 0:
                df_proforma.at[idx[0], "Ulaşma Tarihi"] = new_ulasma_tarih
                update_excel()
                st.success("Ulaşma Tarihi güncellendi!")
                st.rerun()

        st.markdown("---")
        # Ulaşanlardan YOLA GERİ AL (yeniden Sevkedildi + ETA’ya ekle/güncelle)
        with st.form("ulasan_geri_al_form"):
            st.markdown("##### 🔄 Ulaşan siparişi yeniden **Yolda Olanlar (ETA)** listesine al")
            yeni_eta = st.date_input("Yeni ETA (opsiyonel)", value=datetime.date.today() + datetime.timedelta(days=7))
            aciklama_geri = st.text_input("Açıklama (opsiyonel)", value="Geri alındı - tekrar yolda")
            onay = st.form_submit_button("Yola Geri Al")

        if onay:
            musteri = row["Müşteri Adı"]
            pno = row["Proforma No"]

            # Proforma statüsü
            idx = df_proforma[(df_proforma["Müşteri Adı"] == musteri) & (df_proforma["Proforma No"] == pno)].index
            if len(idx) > 0:
                df_proforma.at[idx[0], "Sevk Durumu"] = "Sevkedildi"
                df_proforma.at[idx[0], "Ulaşma Tarihi"] = ""

            # ETA ekle/güncelle
            filtre_eta = (df_eta["Müşteri Adı"] == musteri) & (df_eta["Proforma No"] == pno)
            eta_deger = pd.to_datetime(yeni_eta) if yeni_eta else ""
            if filtre_eta.any():
                if yeni_eta:
                    df_eta.loc[filtre_eta, "ETA Tarihi"] = eta_deger
                if aciklama_geri:
                    df_eta.loc[filtre_eta, "Açıklama"] = aciklama_geri
            else:
                yeni_satir = {
                    "Müşteri Adı": musteri,
                    "Proforma No": pno,
                    "ETA Tarihi": eta_deger if yeni_eta else "",
                    "Açıklama": aciklama_geri,
                }
                df_eta = pd.concat([df_eta, pd.DataFrame([yeni_satir])], ignore_index=True)

            update_excel()
            st.success("Sipariş, Ulaşanlar'dan geri alındı ve ETA listesine taşındı (Sevkedildi).")
            st.rerun()

        # Ulaşanlar Tablosu
        st.markdown("#### Ulaşan (Teslim Edilmiş) Siparişler")
        if "Sevk Tarihi" in ulasanlar.columns:
            ulasanlar["Sevk Tarihi"] = pd.to_datetime(ulasanlar["Sevk Tarihi"], errors="coerce")
        else:
            ulasanlar["Sevk Tarihi"] = pd.NaT
        if "Termin Tarihi" in ulasanlar.columns:
            ulasanlar["Termin Tarihi"] = pd.to_datetime(ulasanlar["Termin Tarihi"], errors="coerce")
        else:
            ulasanlar["Termin Tarihi"] = pd.NaT
        ulasanlar["Ulaşma Tarihi"] = pd.to_datetime(ulasanlar["Ulaşma Tarihi"], errors="coerce")

        ulasanlar["Gün Farkı"] = (ulasanlar["Ulaşma Tarihi"] - ulasanlar["Termin Tarihi"]).dt.days
        ulasanlar["Sevk Tarihi"] = ulasanlar["Sevk Tarihi"].dt.strftime("%d/%m/%Y")
        ulasanlar["Termin Tarihi"] = ulasanlar["Termin Tarihi"].dt.strftime("%d/%m/%Y")
        ulasanlar["Ulaşma Tarihi"] = ulasanlar["Ulaşma Tarihi"].dt.strftime("%d/%m/%Y")

        tablo = ulasanlar[["Müşteri Adı", "Proforma No", "Termin Tarihi", "Sevk Tarihi", "Ulaşma Tarihi", "Gün Farkı", "Tutar", "Açıklama"]]
        st.dataframe(tablo, use_container_width=True)
    else:
        st.info("Henüz ulaşan sipariş yok.")

 

# ==============================
# FUAR KAYITLARI MENÜSÜ
# ==============================

# Gerekli kolonlar (eksikse ekle)
FUAR_KOLONLAR = [
    "Fuar Adı", "Müşteri Adı", "Ülke", "Telefon", "E-mail",
    "Satış Temsilcisi", "Açıklamalar", "Görüşme Kalitesi", "Tarih"
]
for c in FUAR_KOLONLAR:
    if c not in df_fuar_musteri.columns:
        df_fuar_musteri[c] = "" if c not in ["Görüşme Kalitesi", "Tarih"] else np.nan

if menu == "Fuar Kayıtları":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold; text-align:center;'>Fuar Kayıtları</h2>", unsafe_allow_html=True)
    st.info("Fuarlarda müşteri görüşmelerinizi hızlıca buraya ekleyin. Yeni kayıt oluşturun, mevcutları düzenleyin.")

    # --- Fuar seçimi / oluşturma ---
    mevcut_fuarlar = sorted([f for f in df_fuar_musteri["Fuar Adı"].dropna().unique() if str(f).strip() != ""])
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        fuar_adi = st.selectbox("Fuar Seçiniz", ["— Fuar Seçiniz —"] + mevcut_fuarlar, index=0)
        fuar_adi = "" if fuar_adi == "— Fuar Seçiniz —" else fuar_adi
    with col_f2:
        yeni_fuar = st.text_input("Yeni Fuar Adı (opsiyonel)")
        if st.button("Fuar Ekle"):
            y = yeni_fuar.strip()
            if not y:
                st.warning("Fuar adı boş olamaz.")
            elif y in mevcut_fuarlar:
                st.info("Bu fuar zaten mevcut.")
                fuar_adi = y
            else:
                fuar_adi = y
                st.success(f"Fuar eklendi: {y}")

    secim = st.radio("İşlem Seçiniz:", ["Yeni Kayıt", "Eski Kayıt"], horizontal=True)

    # --- YENİ KAYIT ---
    if secim == "Yeni Kayıt":
        st.markdown("#### Yeni Fuar Müşteri Kaydı")
        with st.form("fuar_musteri_ekle"):
            musteri_adi = st.text_input("Müşteri Adı")
            ulke = st.selectbox("Ülke Seçin", ulke_listesi)  # global listeden
            tel = st.text_input("Telefon")
            email = st.text_input("E-mail")
            temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi)  # global listeden
            aciklama = st.text_area("Açıklamalar")
            gorusme_kalitesi = st.slider("Görüşme Kalitesi (1=Kötü, 5=Çok İyi)", 1, 5, 3)
            tarih = st.date_input("Tarih", value=datetime.date.today())

            kaydet = st.form_submit_button("Kaydet")
            if kaydet:
                if not fuar_adi:
                    st.warning("Lütfen bir fuar seçin veya ekleyin.")
                elif not musteri_adi.strip():
                    st.warning("Müşteri adı gerekli.")
                else:
                    yeni = {
                        "Fuar Adı": fuar_adi,
                        "Müşteri Adı": musteri_adi.strip(),
                        "Ülke": ulke,
                        "Telefon": tel.strip(),
                        "E-mail": email.strip(),
                        "Satış Temsilcisi": temsilci,
                        "Açıklamalar": aciklama.strip(),
                        "Görüşme Kalitesi": int(gorusme_kalitesi),
                        "Tarih": tarih,
                    }
                    df_fuar_musteri = pd.concat([df_fuar_musteri, pd.DataFrame([yeni])], ignore_index=True)
                    update_excel()
                    st.success("Fuar müşterisi eklendi!")
                    st.rerun()

    # --- ESKİ KAYIT: listele / filtrele / düzenle / sil ---
    elif secim == "Eski Kayıt":
        if not fuar_adi:
            st.info("Önce bir fuar seçin.")
        else:
            st.markdown(f"<h4 style='color:#4776e6;'>{fuar_adi} – Kayıtlar</h4>", unsafe_allow_html=True)

            fuar_df = df_fuar_musteri[df_fuar_musteri["Fuar Adı"] == fuar_adi].copy()

            # Hızlı filtreler
            col_fa, col_fb, col_fc = st.columns([1, 1, 1])
            with col_fa:
                min_puan = st.slider("Min. Görüşme Kalitesi", 1, 5, 1)
            with col_fb:
                tarih_bas = st.date_input("Başlangıç Tarihi", value=datetime.date.today() - datetime.timedelta(days=30))
            with col_fc:
                tarih_bit = st.date_input("Bitiş Tarihi", value=datetime.date.today())

            # Tip dönüşümleri ve filtre uygula
            fuar_df["Görüşme Kalitesi"] = pd.to_numeric(fuar_df["Görüşme Kalitesi"], errors="coerce")
            fuar_df["Tarih"] = pd.to_datetime(fuar_df["Tarih"], errors="coerce")
            mask = (
                (fuar_df["Görüşme Kalitesi"].fillna(0) >= min_puan) &
                (fuar_df["Tarih"].dt.date >= tarih_bas) &
                (fuar_df["Tarih"].dt.date <= tarih_bit)
            )
            fuar_df = fuar_df[mask].copy().sort_values("Tarih", ascending=False)

            if fuar_df.empty:
                st.info("Filtrelere uyan kayıt yok.")
            else:
                # Seçim
                secili_index = st.selectbox(
                    "Düzenlemek/Silmek istediğiniz kaydı seçin:",
                    fuar_df.index,
                    format_func=lambda i: f"{fuar_df.at[i, 'Müşteri Adı']} ({fuar_df.at[i, 'Tarih'].date() if pd.notnull(fuar_df.at[i, 'Tarih']) else ''})"
                )

                # Detay formu
                with st.form("kayit_duzenle"):
                    musteri_adi = st.text_input("Müşteri Adı", value=str(fuar_df.at[secili_index, "Müşteri Adı"]))
                    u_val = fuar_df.at[secili_index, "Ülke"]
                    ulke = st.selectbox("Ülke", ulke_listesi, index=ulke_listesi.index(u_val) if u_val in ulke_listesi else ulke_listesi.index("Diğer"))
                    t_val = fuar_df.at[secili_index, "Satış Temsilcisi"]
                    temsilci = st.selectbox("Satış Temsilcisi", temsilci_listesi, index=temsilci_listesi.index(t_val) if t_val in temsilci_listesi else 0)
                    tel = st.text_input("Telefon", value=str(fuar_df.at[secili_index, "Telefon"] or ""))
                    email = st.text_input("E-mail", value=str(fuar_df.at[secili_index, "E-mail"] or ""))
                    aciklama = st.text_area("Açıklamalar", value=str(fuar_df.at[secili_index, "Açıklamalar"] or ""))
                    gk_raw = fuar_df.at[secili_index, "Görüşme Kalitesi"]
                    gk_default = int(gk_raw) if pd.notnull(gk_raw) and str(gk_raw).isdigit() else 3
                    gorusme_kalitesi = st.slider("Görüşme Kalitesi (1-5)", 1, 5, gk_default)
                    t_raw = fuar_df.at[secili_index, "Tarih"]
                    tarih = st.date_input("Tarih", value=(pd.to_datetime(t_raw).date() if pd.notnull(t_raw) else datetime.date.today()))

                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        guncelle = st.form_submit_button("Kaydı Güncelle")
                    with col_b2:
                        sil = st.form_submit_button("Kaydı Sil")

                # Güncelle
                if guncelle:
                    for k, v in {
                        "Müşteri Adı": musteri_adi.strip(),
                        "Ülke": ulke,
                        "Telefon": tel.strip(),
                        "E-mail": email.strip(),
                        "Satış Temsilcisi": temsilci,
                        "Açıklamalar": aciklama.strip(),
                        "Görüşme Kalitesi": int(gorusme_kalitesi),
                        "Tarih": tarih,
                    }.items():
                        df_fuar_musteri.at[secili_index, k] = v
                    update_excel()
                    st.success("Kayıt güncellendi!")
                    st.rerun()

                # Sil
                if sil:
                    df_fuar_musteri = df_fuar_musteri.drop(secili_index).reset_index(drop=True)
                    update_excel()
                    st.success("Kayıt silindi!")
                    st.rerun()

                # Görsel tablo
                tablo = fuar_df.copy()
                tablo["Tarih"] = tablo["Tarih"].dt.strftime("%d/%m/%Y")
                st.dataframe(tablo[[
                    "Müşteri Adı", "Ülke", "Telefon", "E-mail",
                    "Satış Temsilcisi", "Açıklamalar", "Görüşme Kalitesi", "Tarih"
                ]], use_container_width=True)

# ===========================
# === İÇERİK ARŞİVİ MENÜSÜ ===
# ===========================

elif menu == "İçerik Arşivi":
    st.markdown("<h2 style='color:#8e54e9; font-weight:bold;'>İçerik Arşivi</h2>", unsafe_allow_html=True)
    st.info("Google Drive’daki medya, ürün görselleri ve kalite evraklarına aşağıdaki sekmelerden ulaşabilirsiniz.")

    # --- Klasör ID'leri (kolayca değiştirilebilir) ---
    DRIVE_FOLDER_IDS = {
        "Genel Medya Klasörü": "1gFAaK-6v1e3346e-W0TsizOqSq43vHLY",
        "Ürün Görselleri":      "18NNlmadm5NNFkI1Amzt_YMwB53j6AmbD",
        "Kalite Evrakları":     "1pbArzYfA4Tp50zvdyTzSPF2ThrMWrGJc",
    }

    def embed_url(folder_id: str) -> str:
        return f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"

    def open_url(folder_id: str) -> str:
        return f"https://drive.google.com/drive/folders/{folder_id}?usp=sharing"

    # --- Gömülü görünüm yüksekliği ayarı (ekranına göre) ---
    h = st.slider("Gömülü görünüm yüksekliği (px)", min_value=450, max_value=900, value=600, step=50)

    tabs = st.tabs(list(DRIVE_FOLDER_IDS.keys()))
    for tab, tab_name in zip(tabs, DRIVE_FOLDER_IDS.keys()):
        with tab:
            fid = DRIVE_FOLDER_IDS[tab_name]
            st.markdown(
                f"""
                <iframe src="{embed_url(fid)}"
                        width="100%" height="{h}" frameborder="0"
                        style="border:1px solid #eee; border-radius:12px; margin-top:10px;">
                </iframe>
                """,
                unsafe_allow_html=True
            )
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.link_button("Klasörü yeni sekmede aç", open_url(fid))
            with col_b:
                st.info("Dosya/klasörlere çift tıklayarak yeni sekmede açabilir veya indirebilirsiniz.")

    st.warning("Not: Klasörlerin paylaşımı 'Bağlantıya sahip olan herkes görüntüleyebilir' olmalı; aksi halde gömülü görünüm boş kalır.")


### ===========================
### --- SATIŞ ANALİTİĞİ MENÜSÜ ---
### ===========================

elif menu == "Satış Analitiği":
    st.markdown("<h2 style='color:#219A41; font-weight:bold;'>Satış Analitiği</h2>", unsafe_allow_html=True)

    # --- Akıllı sayı dönüştürücü ---
    def smart_to_num(x):
        if pd.isna(x): return 0.0
        s = str(x).strip()
        for sym in ["USD", "$", "€", "EUR", "₺", "TL", "tl", "Tl"]:
            s = s.replace(sym, "")
        s = s.replace("\u00A0", "").replace(" ", "")
        # 1) Doğrudan parse (US)
        try: return float(s)
        except: pass
        # 2) Avrupa formatı
        if "," in s:
            try: return float(s.replace(".", "").replace(",", "."))
            except: pass
        return 0.0

    # ---- Kolon güvenliği ----
    if "Tutar" not in df_evrak.columns:
        df_evrak["Tutar"] = 0
    date_col = "Fatura Tarihi" if "Fatura Tarihi" in df_evrak.columns else "Tarih"
    if date_col not in df_evrak.columns:
        df_evrak[date_col] = pd.NaT

    # ---- Tip dönüşümleri ----
    df_evrak = df_evrak.copy()
    df_evrak["Tutar_num"] = df_evrak["Tutar"].apply(smart_to_num).fillna(0.0)
    df_evrak[date_col] = pd.to_datetime(df_evrak[date_col], errors="coerce")
    df_evrak = df_evrak[df_evrak[date_col].notna()]  # geçersiz tarihleri at

    # ---- Toplamlar ----
    toplam_fatura = float(df_evrak["Tutar_num"].sum())
        st.markdown(f"<div style='font-size:1.3em; color:#185a9d; font-weight:bold;'>Toplam Fatura Tutarı: {toplam_fatura:,.2f} USD</div>", unsafe_allow_html=True)
    # ---- Tarih aralığı filtresi (Timestamp ile) ----
    min_ts = df_evrak[date_col].min()
    max_ts = df_evrak[date_col].max()
    d1, d2 = st.date_input("Tarih Aralığı", value=(min_ts.date(), max_ts.date()))

    start_ts = pd.to_datetime(d1)  # 00:00
    end_ts   = pd.to_datetime(d2) + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)  # gün sonu

    mask = df_evrak[date_col].between(start_ts, end_ts, inclusive="both")
    df_range = df_evrak[mask]

    aralik_toplam = float(df_range["Tutar_num"].sum())
     st.markdown(f"<div style='font-size:1.2em; color:#f7971e; font-weight:bold;'>{d1} - {d2} Arası Toplam: {aralik_toplam:,.2f} USD</div>", unsafe_allow_html=True)
    # ---- Detay tablo ----
    show_cols = ["Müşteri Adı", "Fatura No", date_col, "Tutar"]
    show_cols = [c for c in show_cols if c in df_range.columns]
    st.dataframe(df_range[show_cols].sort_values(by=date_col, ascending=False), use_container_width=True)
