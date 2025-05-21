import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pandas as pd
import os

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
EXCEL_FILE = 'daftar_file_drive.xlsx'

@st.cache_data(show_spinner=False)
def get_drive_service():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('drive', 'v3', credentials=creds)
    return service

@st.cache_data(show_spinner=True)
def get_files_data():
    service = get_drive_service()

    # Ambil semua folder dulu
    folder_results = service.files().list(
        q="mimeType='application/vnd.google-apps.folder'",
        fields="files(id, name)",
        pageSize=1000
    ).execute()
    folder_items = folder_results.get('files', [])
    folder_dict = {folder['id']: folder['name'] for folder in folder_items}

    # Ambil file
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
            file_data = {
                'Nama File': item['name'],
                'Tipe': item['mimeType'],
                'Folder Induk': parent_name,
                'Pemilik': item.get('owners', [{}])[0].get('emailAddress', 'Tidak Diketahui'),
                'Ukuran': item.get('size', 'Tidak Diketahui'),
                'Waktu Dibuat': item['createdTime'],
                'Terakhir Dimodifikasi': item['modifiedTime'],
                'Link': item['webViewLink']
            }
            files_data.append(file_data)
        
        page_token = results.get('nextPageToken')
        if not page_token:
            break

    return pd.DataFrame(files_data)

# ========== STREAMLIT UI ==========
st.title("Daftar File Google Drive + Nama Folder Induk")

if st.button("Ambil Data dari Google Drive"):
    with st.spinner("Mengambil data..."):
        df = get_files_data()
        st.success(f"Ditemukan {len(df)} file")
        st.dataframe(df)

        # Simpan ke Excel
        df.to_excel(EXCEL_FILE, index=False)
        with open(EXCEL_FILE, "rb") as f:
            st.download_button(
                label="Download sebagai Excel",
                data=f,
                file_name=EXCEL_FILE,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
else:
    st.info("Klik tombol di atas untuk mengambil data dari Google Drive.")
