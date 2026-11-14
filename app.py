import streamlit as st
import pandas as pd
from datetime import date
import os
import json
import gspread
from google.oauth2.service_account import Credentials

def append_to_gsheet(df):
    scope = ["https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive"]
    # ✅ Ambil isi credentials dari Streamlit Secrets
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    
    # Ganti URL ini dengan URL Google Sheet client kamu
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/118j0HX6EfbjJ67PAZ8O6-BaKOzkR9VQTS74QwSbCYVU/edit?usp=sharing")
    worksheet = sheet.sheet1  # atau .worksheet("NamaSheet")
    
    # Append baris satu per satu (aman di semua versi)
    for row in df.values.tolist():
        worksheet.append_row(row)
# Nama file data siswa
STUDENT_FILE = "daftar_siswa_ix.csv"

# Load data siswa
@st.cache_data
def load_students(file):
    df = pd.read_csv(file)
    # pastikan kolomnya ada
    if not all(col in df.columns for col in ["kelas", "nama_siswa"]):
        st.error("CSV harus punya kolom: 'kelas' dan 'nama_siswa'")
        st.stop()
    return df

students_df = load_students(STUDENT_FILE)
st.title("📘 Presensi Digital TAJAM")

st.markdown(
    "Silahkan input nama siswa yang **TIDAK HADIR** "
    "pada kegiatan tambahan jam pembelajaran."
)
st.markdown("Jika siswa hadir semua, maka tidak perlu mengisi.")

# Input tanggal
tanggal = st.date_input("📅 Pilih Tanggal", date.today())

# Membuat dictionary nama siswa dan kelas
student_options = {
    f"{row['nama_siswa']} - {row['kelas']}":
    (row['nama_siswa'], row['kelas'])
    for _, row in students_df.iterrows()
}

# Searchable dropdown
selected_students = st.multiselect(
    "🔍 Cari Nama Siswa",
    options=list(student_options.keys()),
    placeholder="Ketik nama siswa...",
)

# Inisialisasi session state
if "absensi" not in st.session_state:
    st.session_state.absensi = {}

# Menampilkan siswa yang dipilih
if selected_students:

    st.markdown("---")
    st.markdown("#### Daftar Siswa Tidak Hadir")

    for i, selected in enumerate(selected_students, start=1):

        nama, kelas = student_options[selected]

        col_no, col_nama, col_alpha, col_sakit, col_izin, col_delete = st.columns(
            [0.3, 2.5, 1, 1, 1, 0.6]
        )

        with col_no:
            st.markdown(f"**{i}.**")

        with col_nama:
            st.markdown(f"**{nama}**")
            st.caption(f"Kelas {kelas}")

        if nama not in st.session_state.absensi:
            st.session_state.absensi[nama] = None

        with col_alpha:
            if st.button("Alpha", key=f"{kelas}_{nama}_alpha"):
                st.session_state.absensi[nama] = "Alpha"

        with col_sakit:
            if st.button("Sakit", key=f"{kelas}_{nama}_sakit"):
                st.session_state.absensi[nama] = "Sakit"

        with col_izin:
            if st.button("Izin", key=f"{kelas}_{nama}_izin"):
                st.session_state.absensi[nama] = "Izin"

        with col_delete:
            if st.button("🗑️", key=f"{kelas}_{nama}_delete"):
                st.session_state.absensi.pop(nama, None)
                st.rerun()

        if st.session_state.absensi.get(nama):
            st.markdown(
                f"<div style='color:green; font-size:13px; "
                f"margin-left:60px;'>"
                f"✔️ {st.session_state.absensi[nama]} dipilih"
                f"</div>",
                unsafe_allow_html=True
            )

    st.markdown("---")

    col_reset, col_save = st.columns(2)

    if col_reset.button("🔄 Reset Semua"):
        st.session_state.absensi = {}
        st.rerun()

    if col_save.button("💾 Simpan Absensi"):

        records = []

        for selected in selected_students:
            nama, kelas = student_options[selected]
            status = st.session_state.absensi.get(nama)

            if status:
                records.append({
                    "Tanggal": tanggal.strftime("%Y-%m-%d"),
                    "Kelas": kelas,
                    "Nama Siswa": nama,
                    "Keterangan": status
                })

        if records:
            df = pd.DataFrame(records)
            append_to_gsheet(df)

            st.session_state.absensi = {}
            st.session_state.show_toast = True
            st.rerun()

        else:
            st.warning(
                "⚠️ Belum ada keterangan ketidakhadiran yang dipilih."
            )

if st.session_state.get("show_toast", False):
    st.toast("Absensi berhasil disimpan!", icon="✅")
    st.session_state.show_toast = False
