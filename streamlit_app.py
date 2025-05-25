import streamlit as st
import pandas as pd
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os

# === Konfigurasi ===
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
EXCEL_FILE = 'daftar_file_drive.xlsx'

# === Fungsi Autentikasi OAuth ===
def get_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": st.secrets["google_oauth"]["client_id"],
                "client_secret": st.secrets["google_oauth"]["client_secret"],
                "redirect_uris": [st.secrets["google_oauth"]["redirect_uri"]],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES,
        redirect_uri=st.secrets["google_oauth"]["redirect_uri"]
    )

def authenticate():
    query_params = st.query_params  # ✅ Ini versi baru (Streamlit >= 1.30)
    if "code" in query_params:
        flow = get_flow()
        flow.fetch_token(code=query_params["code"][0])
        st.session_state.credentials = flow.credentials
    elif "credentials" not in st.session_state:
        flow = get_flow()
        auth_url, _ = flow.authorization_url(prompt='consent')
        st.markdown(f"[Login dengan Google]({auth_url})")
        st.stop()

def get_drive_service():
    creds = st.session_state.credentials
    return build('drive', 'v3', credentials=creds)

@st.cache_data(show_spinner="Mengambil data file dari Google Drive...")
def get_files_data(service):
    folder_results = service.files().list(
        q="mimeType='application/vnd.google-apps.folder'",
        fields="files(id, name)",
        pageSize=1000
    ).execute()
    folder_items = folder_results.get('files', [])
    folder_dict = {folder['id']: folder['name'] for folder in folder_items}

    files_data = []
    page_token = None
    while True:
        results = service.files().list(
            pageSize=100,
            fields="nextPageToken, files(id, name, webViewLink, mimeType, createdTime, modifiedTime, owners, size, parents)",
            pageToken=page_token
        ).execute()

        items = results.get('files', [])
        for item in items:
            parent_id = item.get('parents', [None])[0]
            parent_name = folder_dict.get(parent_id, 'ROOT' if parent_id is None else 'Tidak Diketahui')
            files_data.append({
                'Nama File': item['name'],
                'Tipe': item['mimeType'],
                'Folder Induk': parent_name,
                'Pemilik': item.get('owners', [{}])[0].get('emailAddress', 'Tidak Diketahui'),
                'Ukuran': item.get('size', 'Tidak Diketahui'),
                'Waktu Dibuat': item['createdTime'],
                'Terakhir Dimodifikasi': item['modifiedTime'],
                'Link': item['webViewLink']
            })

        page_token = results.get('nextPageToken')
        if not page_token:
            break

    return pd.DataFrame(files_data)

# === UI Streamlit ===
st.set_page_config(page_title="Drive File Viewer", layout="wide")
st.title("📂 Daftar File Google Drive")

# Autentikasi OAuth
authenticate()

# Ambil service dan data
service = get_drive_service()
if st.button("🔄 Ambil Data File"):
    df = get_files_data(service)
    st.success(f"✅ {len(df)} file ditemukan.")
    st.dataframe(df)

    # Tombol unduh
    df.to_excel(EXCEL_FILE, index=False)
    with open(EXCEL_FILE, "rb") as f:
        st.download_button(
            "⬇️ Download Excel",
            f,
            file_name=EXCEL_FILE,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Klik tombol di atas untuk mengambil daftar file dari Google Drive.")
