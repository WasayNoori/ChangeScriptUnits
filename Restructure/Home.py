import streamlit as st

st.set_page_config(page_title="Script Tools", layout="wide")

st.title("Script Tools")
st.markdown("""
Use the sidebar to navigate between tools.

| Page | Purpose |
|------|---------|
| **Critique Viewer** | Drop a JSON critique report to inspect metadata, blocks, and issues |
| **Analyze Script** | Drop a raw `.txt` script file and generate a critique report using AI |
""")
