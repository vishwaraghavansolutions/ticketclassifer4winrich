import os
import io
import json
import pandas as pd
import streamlit as st
import altair as alt
import openai

# -------- CONFIG --------
DEFAULT_MODEL = "gpt-4.1-mini"
SLA_FILE = "data.json"   # CRUD JSON file created earlier

SYSTEM_PROMPT = """You are an analyst assessing customer satisfaction in support tickets.
Given the full conversation (messages from customer and admin), decide:
- satisfaction: yes/no
- rationale: concise explanation citing message cues
- sentiment: positive/neutral/negative
Return JSON with keys: satisfaction, sentiment, rationale."""

USER_PROMPT_TEMPLATE = """Ticket ID: {ticket_id}
Customer: {customer_name}
Product: {product_name}
Status: {status}

Conversation (chronological):
{conversation}

Task:
1) satisfaction: yes/no
2) sentiment: positive/neutral/negative
3) rationale: one short paragraph
Return JSON with keys: satisfaction, sentiment, rationale."""


# -------- SLA CONFIG --------
def load_sla_config():
    if os.path.exists(SLA_FILE):
        with open(SLA_FILE, "r") as f:
            return json.load(f)
    return []

def get_sla_for_ticket(product_name, query_text, sla_config, default_days=2):
    # Match SLA by Category (product) and optionally query substring
    for entry in sla_config:
        if entry.get("Category") == product_name and entry.get("Query") and entry.get("Query") in str(query_text):
            try:
                return int(entry.get("SLA", default_days))
            except Exception:
                pass
    for entry in sla_config:
        if entry.get("Category") == product_name:
            try:
                return int(entry.get("SLA", default_days))
            except Exception:
                pass
    return default_days


# -------- UTILS --------
def group_conversation(df):
    tickets = {}
    for _, row in df.iterrows():
        tid = str(row.get("ticket_id", "")).strip()
        if not tid:
            continue
        if tid not in tickets:
            tickets[tid] = {
                "ticket_id": tid,
                "customer_id": row.get("customer_id"),
                "customer_name": row.get("customer_name"),
                "product_name": row.get("product_name"),
                "status": row.get("status"),
                "posted_date": row.get("posted_date"),
                "closed_date": row.get("closed_date"),
                "messages": [],
            }
        tickets[tid]["messages"].append({
            "from": row.get("message_from"),
            "content": row.get("msg_content"),
            "msg_datetime": row.get("msg_datetime")
        })

    # Stitch raw text
    for tid, info in tickets.items():
        msgs = info["messages"]
        stitched = []
        for m in msgs:
            stitched.append(f"{str(m['from']).upper()}: {m['content']} ({m['msg_datetime']})")
        info["raw_text"] = "\n".join(stitched)
    return tickets


def compute_sla(posted_date, closed_date, sla_days):
    dt_posted = pd.to_datetime(posted_date, utc=True, errors="coerce")
    dt_closed = pd.to_datetime(closed_date, utc=True, errors="coerce")
    if pd.isna(dt_posted) or pd.isna(dt_closed):
        return {"sla_met": None, "resolution_hours": None}
    delta = dt_closed - dt_posted
    hours = delta.total_seconds() / 3600.0
    return {"sla_met": hours <= sla_days * 24, "resolution_hours": round(hours, 2)}


def call_openai_for_satisfaction(client, ticket, model=DEFAULT_MODEL):
    user_prompt = USER_PROMPT_TEMPLATE.format(
        ticket_id=ticket.get("ticket_id"),
        customer_name=ticket.get("customer_name"),
        product_name=ticket.get("product_name"),
        status=ticket.get("status"),
        conversation=ticket.get("raw_text", "")
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )
    content = response.choices[0].message.content
    try:
        parsed = json.loads(content)
        return {
            "satisfaction": parsed.get("satisfaction"),
            "sentiment": parsed.get("sentiment"),
            "rationale": parsed.get("rationale"),
        }
    except Exception:
        return {"satisfaction": None, "sentiment": None, "rationale": content}


def build_report(tickets, results, sla_config):
    rows = []
    for tid, t in tickets.items():
        # Use conversation text as "query_text" to match SLA by substring
        query_text = t.get("raw_text", "")
        sla_days = get_sla_for_ticket(t.get("product_name"), query_text, sla_config)
        owner = "Unknown"
        for entry in sla_config:
            if entry.get("Product") == t.get("product_name"):
                owner = entry.get("Owner", "Unknown")
                break

        sla = compute_sla(t.get("posted_date"), t.get("closed_date"), sla_days)
        ai = results.get(tid, {})
        rows.append({
            "ticket_id": tid,
            "customer_id": t.get("customer_id"),
            "customer_name": t.get("customer_name"),
            "product_name": t.get("product_name"),
            "status": t.get("status"),
            "posted_date": t.get("posted_date"),
            "closed_date": t.get("closed_date"),
            "resolution_hours": sla.get("resolution_hours"),
            "sla_days": sla_days,
            "sla_met": sla.get("sla_met"),
            "owner": owner,
            "ai_satisfaction": ai.get("satisfaction"),
            "ai_sentiment": ai.get("sentiment"),
            "ai_rationale": ai.get("rationale"),
        })
    df = pd.DataFrame(rows)

    def verdict(row):
        sat = str(row["ai_satisfaction"]).lower()
        if row["sla_met"] is True and sat == "yes":
            return "Resolved within SLA to customer satisfaction"
        if row["sla_met"] is False and sat == "yes":
            return "Resolved to satisfaction (SLA breached)"
        if row["sla_met"] is True and sat == "no":
            return "Within SLA but not satisfactory"
        if row["sla_met"] is False and sat == "no":
            return "Not within SLA and not satisfactory"
        return "Insufficient data"

    df["final_verdict"] = df.apply(verdict, axis=1)
    return df


# -------- STREAMLIT UI --------
st.title("Ticket Interaction Analysis")

st.sidebar.markdown("## Configuration")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")
model_name = st.sidebar.text_input("Model", value=DEFAULT_MODEL)

uploaded = st.file_uploader("Upload ticket Excel", type=["xlsx"])
run_btn = st.button("Run Analysis")

if run_btn:
    if not api_key:
        st.error("Please provide your OpenAI API key.")
        st.stop()
    if not uploaded:
        st.error("Please upload the Excel file.")
        st.stop()

    # Read Excel
    df = pd.read_excel(uploaded)
    df.columns = [c.strip() for c in df.columns]

    required_cols = [
        "ticket_id", "customer_id", "customer_name", "product_name",
        "message_from", "msg_content", "msg_datetime", "status",
        "posted_date", "closed_date"
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {missing}")
        st.stop()

    # Prepare data and SLA config
    tickets = group_conversation(df)
    sla_config = load_sla_config()

    # OpenAI client
    client = openai.OpenAI(api_key=api_key)

    # Analyze
    ai_results = {}
    progress = st.progress(0)
    for i, (tid, t) in enumerate(tickets.items(), start=1):
        ai_results[tid] = call_openai_for_satisfaction(client, t, model=model_name)
        progress.progress(i / len(tickets))

    # Report
    report_df = build_report(tickets, ai_results, sla_config)

    st.subheader("Final Report")
    st.dataframe(report_df, use_container_width=True)

    # --- Charts ---
    st.subheader("Charts")

    chart1 = alt.Chart(report_df).mark_bar().encode(
        x=alt.X("product_name:N", title="Product"),
        y=alt.Y("count():Q", title="Cases"),
        color="sla_met:N"
    ).properties(title="SLA Compliance by Product")
    st.altair_chart(chart1, use_container_width=True)

    chart2 = alt.Chart(report_df).mark_bar().encode(
        x=alt.X("ai_satisfaction:N", title="Satisfaction"),
        y=alt.Y("count():Q", title="Cases"),
        color="ai_satisfaction:N"
    ).properties(title="Cases by Customer Satisfaction")
    st.altair_chart(chart2, use_container_width=True)

    chart3 = alt.Chart(report_df).mark_bar().encode(
        x=alt.X("final_verdict:N", title="Verdict"),
        y=alt.Y("count():Q", title="Cases"),
        color="final_verdict:N"
    ).properties(title="Cases by Final Verdict")
    st.altair_chart(chart3, use_container_width=True)

     # --- NEW: Unresolved Issues Chart ---
    unresolved_df = report_df[report_df["final_verdict"] != "Resolved within SLA to customer satisfaction"]
    if not unresolved_df.empty:
        chart_unresolved = alt.Chart(unresolved_df).mark_bar().encode(
            x=alt.X("product_name:N", title="Product"),
            y=alt.Y("count():Q", title="Unresolved Cases"),
            color="final_verdict:N"
        ).properties(title="Unresolved Issues by Product")
        st.altair_chart(chart_unresolved, use_container_width=True)
    else:
        st.info("All issues resolved within SLA to customer satisfaction 🎉")

    # --- Chart by Owner ---
    st.subheader("Cases by Person Responsible for Resolution")
    if "owner" in report_df.columns and not report_df["owner"].isna().all():
        chart_owner = alt.Chart(report_df).mark_bar().encode(
            x=alt.X("owner:N", title="Owner"),
            y=alt.Y("count():Q", title="Cases"),
            color="owner:N"
        ).properties(title="Cases by Responsible Owner")
        st.altair_chart(chart_owner, use_container_width=True)
    else:
        st.info("No owner information available in SLA config.")


    # --- Downloads ---
    csv_buf = io.StringIO()
    report_df.to_csv(csv_buf, index=False)
    st.download_button("Download CSV", data=csv_buf.getvalue(), file_name="ticket_report.csv", mime="text/csv")

    json_buf = io.StringIO()
    json_buf.write(report_df.to_json(orient="records", indent=2))
    st.download_button("Download JSON", data=json_buf.getvalue(), file_name="ticket_report.json", mime="application/json")