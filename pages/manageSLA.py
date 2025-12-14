import streamlit as st
import json
import os
import pandas as pd

# File to store data
DATA_FILE = "data.json"

# Load existing data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

# Save data to file
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Initialize session state
if "data" not in st.session_state:
    st.session_state.data = load_data()

st.title("CRUD App with Tabs & Table View")

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Create", "Read", "Update", "Delete", "All Records"])

# --- CREATE ---
with tab1:
    st.header("Add New Record")
    with st.form("create_form"):
        Product = st.text_input("Product")
        query = st.text_input("Query")
        owner = st.text_input("Owner")
        sla = st.text_input("SLA")
        submitted = st.form_submit_button("Add Record")
        if submitted:
            new_record = {"Product": Product, "Query": query, "Owner": owner, "SLA": sla}
            st.session_state.data.append(new_record)
            save_data(st.session_state.data)
            st.success("Record added successfully!")

# --- READ ---
with tab2:
    st.header("View Records")
    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No records found.")

# --- UPDATE ---
with tab3:
    st.header("Update Record")
    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)

        record_index = st.number_input("Select record index", min_value=0, max_value=len(st.session_state.data)-1, step=1)
        record = st.session_state.data[record_index]

        with st.form("update_form"):
            Product = st.text_input("Product", value=record["Product"])
            query = st.text_input("Query", value=record["Query"])
            owner = st.text_input("Owner", value=record["Owner"])
            sla = st.text_input("SLA", value=record["SLA"])
            update = st.form_submit_button("Update Record")

            if update:
                st.session_state.data[record_index] = {"Product": Product, "Query": query, "Owner": owner, "SLA": sla}
                save_data(st.session_state.data)
                st.success("Record updated successfully!")
    else:
        st.info("No records to update.")

# --- DELETE ---
with tab4:
    st.header("Delete Record")
    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)

        record_index = st.number_input("Select record index to delete", min_value=0, max_value=len(st.session_state.data)-1, step=1)
        delete = st.button("Delete Record")

        if delete:
            st.session_state.data.pop(record_index)
            save_data(st.session_state.data)
            st.warning("Record deleted successfully!")
    else:
        st.info("No records to delete.")

# --- ALL RECORDS ---
with tab5:
    st.header("All Records (Table View)")
    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No records found.")