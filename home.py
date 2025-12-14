import streamlit as st

# Initialize session state for navigation      ddd
if "page" not in st.session_state:
    st.session_state.page = "home"

def go_to(page_name):
    st.session_state.page = page_name

# --- Page Routing ---
if st.session_state.page == "home":
    st.title("Welcome to SLA Analysis App")

    st.write("Choose what you want to do:")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("AI Report"):
            st.switch_page("pages/AIReport.py")

    with col2:
        if st.button("Manage SLA"):
            st.switch_page("pages/manageSLA.py")