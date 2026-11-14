import streamlit as st
import pandas as pd
from datetime import date
import json
import gspread
from google.oauth2.service_account import Credentials


# ==========================================
# GOOGLE SHEETS CONNECTION
# ==========================================

def append_to_gsheet(df):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(
        creds_dict, scopes=scope
    )

    client = gspread.authorize(creds)

    sheet = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/19Mt4ir9Ag0XAyb6Pcc0eDWnpjn9iee7vgV6FE0PB6mA/edit?usp=sharing"
    )

    worksheet = sheet.sheet1

    for row in df.values.tolist():
        worksheet.append_row(row)


# ==========================================
# LOAD STUDENT DATA
# ==========================================

STUDENT_FILE = "daftar_siswa_ix.csv"


@st.cache_data
def load_students(file):
    df = pd.read_csv(file)

    if not all(col in df.columns for col in ["kelas", "nama_siswa"]):
        st.error("CSV harus punya kolom: 'kelas' dan 'nama_siswa'")
        st.stop()

    return df.reset_index(drop=True)


students_df = load_students(STUDENT_FILE)


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.title("📘 Presensi Digital TAJAM")

st.markdown(
    "Silahkan input nama siswa yang **TIDAK HADIR** "
    "pada kegiatan tambahan jam pembelajaran."
)

st.markdown(
    "Jika siswa hadir semua, maka tidak perlu mengisi."
)


# ==========================================
# SESSION STATE
# ==========================================

if "absensi" not in st.session_state:
    st.session_state.absensi = {}

if "selected_students" not in st.session_state:
    st.session_state.selected_students = []

if "clear_selection" not in st.session_state:
    st.session_state.clear_selection = False


# Reset dropdown sebelum widget dibuat
if st.session_state.clear_selection:
    st.session_state.selected_students = []
    st.session_state.clear_selection = False


# ==========================================
# DATE INPUT
# ==========================================

tanggal = st.date_input(
    "📅 Pilih Tanggal",
    date.today()
)


# ==========================================
# SEARCHABLE STUDENT DROPDOWN
# ==========================================

st.markdown("### 🔍 Cari Nama Siswa")

# Menggunakan indeks sebagai identitas unik siswa
student_options = students_df.index.tolist()

selected_students = st.multiselect(
    "Ketik nama siswa yang tidak hadir",
    options=student_options,
    format_func=lambda idx: str(
        students_df.loc[idx, "nama_siswa"]
    ),
    placeholder="Ketik nama siswa...",
    key="selected_students"
)


# ==========================================
# DISPLAY SELECTED STUDENTS
# ==========================================

if selected_students:

    st.markdown("---")
    st.markdown("### Daftar Siswa Tidak Hadir")

    for i, student_id in enumerate(selected_students, start=1):

        nama = students_df.loc[student_id, "nama_siswa"]
        kelas = students_df.loc[student_id, "kelas"]

        # Identitas unik siswa
        key_absen = str(student_id)

        if key_absen not in st.session_state.absensi:
            st.session_state.absensi[key_absen] = None

        col_no, col_nama, col_alpha, col_sakit, col_izin, col_delete = st.columns(
            [0.3, 2.5, 1, 1, 1, 0.6]
        )

        with col_no:
            st.markdown(f"**{i}.**")

        with col_nama:
            st.markdown(f"**{nama}**")
            st.caption(f"Kelas {kelas}")

        with col_alpha:
            if st.button("Alpha", key=f"{key_absen}_alpha"):
                st.session_state.absensi[key_absen] = "Alpha"

        with col_sakit:
            if st.button("Sakit", key=f"{key_absen}_sakit"):
                st.session_state.absensi[key_absen] = "Sakit"

        with col_izin:
            if st.button("Izin", key=f"{key_absen}_izin"):
                st.session_state.absensi[key_absen] = "Izin"

        with col_delete:
            if st.button("🗑️", key=f"{key_absen}_delete"):
                st.session_state.selected_students.remove(student_id)
                st.session_state.absensi.pop(key_absen, None)
                st.rerun()

        # Highlight selected status
        status = st.session_state.absensi[key_absen]

        if status:
            st.markdown(
                f"<div style='color:green; font-size:13px; "
                f"margin-left:60px;'>"
                f"✔️ {status} dipilih</div>",
                unsafe_allow_html=True
            )


# ==========================================
# RESET AND SAVE BUTTONS
# ==========================================

st.markdown("---")

col_reset, col_save = st.columns(2)


with col_reset:
    if st.button("🔄 Reset Semua", use_container_width=True):
        st.session_state.absensi = {}
        st.session_state.clear_selection = True
        st.rerun()


with col_save:
    if st.button("💾 Simpan Absensi", use_container_width=True):

        records = []

        for student_id in selected_students:

            nama = students_df.loc[student_id, "nama_siswa"]
            kelas = students_df.loc[student_id, "kelas"]

            key_absen = str(student_id)
            status = st.session_state.absensi.get(key_absen)

            if status:
                records.append({
                    "Tanggal": tanggal.strftime("%Y-%m-%d"),
                    "Kelas": kelas,
                    "Nama Siswa": nama,
                    "Keterangan": status
                })

        if records:

            df = pd.DataFrame(records)

            try:
                append_to_gsheet(df)

                st.session_state.absensi = {}
                st.session_state.clear_selection = True
                st.session_state.show_toast = True

                st.rerun()

            except Exception as e:
                st.error(f"Gagal menyimpan absensi: {e}")

        else:
            st.warning(
                "⚠️ Belum ada siswa yang dipilih "
                "atau keterangan absensi belum diisi."
            )


# ==========================================
# SUCCESS NOTIFICATION
# ==========================================

if st.session_state.get("show_toast", False):

    st.toast(
        "Absensi berhasil disimpan!",
        icon="✅"
    )

    st.session_state.show_toast = False
