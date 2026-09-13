import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

st.set_page_config(
    page_title="AI Smart Energy Meter | Cloud Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

with st.sidebar:
    st.header("⚙️ Cloud Configuration")
    api_base_url = st.text_input("API Base URL", value="http://localhost:8000")
    refresh_rate = st.slider("Polling Frequency (seconds)", min_value=1, max_value=10, value=2)
    auto_refresh = st.checkbox("Live Auto-Refresh", value=True)
    
    st.markdown("---")
    st.markdown("**Novel Architectural Highlights:**")
    st.caption("• **NILM Engine**: Non-Intrusive Disaggregation")
    st.caption("• **Carbon Ledger**: Real-time CEA Grid Carbon Intensity")
    st.caption("• **Surge ML**: Isolation Forest Unsupervised Model")

    if st.button("Reset In-Memory Buffer"):
        try:
            requests.post(f"{api_base_url}/api/v1/buffer/clear", timeout=3)
            st.success("Buffer reset.")
        except Exception as e:
            st.error(f"Error: {e}")

def fetch_recent_telemetry(base_url: str):
    try:
        res = requests.get(f"{base_url}/api/v1/telemetry/recent?limit=60", timeout=4)
        return res.json() if res.status_code == 200 else []
    except Exception:
        return []

def fetch_nilm_events(base_url: str):
    try:
        res = requests.get(f"{base_url}/api/v1/nilm/events", timeout=4)
        return res.json() if res.status_code == 200 else []
    except Exception:
        return []

def fetch_smart_bill(base_url: str):
    try:
        res = requests.get(f"{base_url}/api/v1/analytics/bill", timeout=4)
        return res.json() if res.status_code == 200 else None
    except Exception:
        return None

st.title("⚡ AI Cloud Smart Meter & Carbon Analytics")
st.caption("Continuous Telemetry Profiling • Non-Intrusive Load Monitoring (NILM) • Carbon Emission Ledger")

telemetry_data = fetch_recent_telemetry(api_base_url)
nilm_events = fetch_nilm_events(api_base_url)
bill_data = fetch_smart_bill(api_base_url)

if not telemetry_data:
    st.warning("⚠️ No incoming telemetry detected. Ensure the backend and simulator are running.")
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()
    st.stop()

df = pd.DataFrame(telemetry_data)
df["formatted_time"] = df["timestamp"].apply(lambda ts: datetime.fromtimestamp(ts).strftime("%H:%M:%S"))
latest = df.iloc[-1]

m_col1, m_col2, m_col3, m_col4 = st.columns(4)
power_delta = "SURGE" if latest["is_anomaly"] else ("IDLE / PHANTOM" if latest["is_idle"] else "NORMAL")
m_col1.metric("Active Power", f"{latest['active_power_watts']} W", delta=power_delta, delta_color="inverse" if latest["is_anomaly"] else "normal")
m_col2.metric("Grid Voltage", f"{latest['voltage']} V", delta=f"{round(latest['voltage'] - 230.0, 1)} V")
m_col3.metric("Load Current", f"{latest['current']} A")
m_col4.metric("Power Factor", f"{latest['power_factor']}")

if latest["is_anomaly"]:
    st.error(f"🚨 **Grid Anomaly Surge at {latest['formatted_time']}!** Active load drew **{latest['active_power_watts']} W**.")

st.markdown("---")
chart_col, side_panel = st.columns([2, 1])

with chart_col:
    st.subheader("📈 Real-time Power Curve")
    chart_df = df[["formatted_time", "active_power_watts"]].set_index("formatted_time")
    st.line_chart(chart_df, use_container_width=True)

with side_panel:
    st.subheader("🔍 NILM Appliance Disaggregation")
    if nilm_events:
        nilm_df = pd.DataFrame(nilm_events)
        nilm_df["time"] = nilm_df["timestamp"].apply(lambda ts: datetime.fromtimestamp(ts).strftime("%H:%M:%S"))
        st.dataframe(nilm_df[["time", "appliance", "delta_watts"]].iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("Monitoring step-transitions for appliance signatures...")

st.markdown("---")
st.subheader("💡 Dynamic Slab Billing & Scope-2 Carbon Footprint")

if bill_data and "bill_details" in bill_data:
    bill = bill_data["bill_details"]
    phantom = bill_data["phantom_analysis"]
    
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    b_col1.metric("Simulated Usage", f"{bill['units_consumed_kwh']} kWh")
    b_col2.metric("Estimated Cost", f"₹{bill['total_bill_inr']}")
    b_col3.metric("CO₂ Footprint", f"{bill.get('carbon_kg', 0.0)} kg CO₂")
    phantom_label = f"₹{bill['phantom_waste_inr']}/mo" if phantom["is_phantom_detected"] else "₹0.00"
    b_col4.metric("Vampire Waste", phantom_label, delta="Standby Drain" if phantom["is_phantom_detected"] else "Optimal", delta_color="inverse")

    st.markdown("#### 🤖 Actionable Energy Prescriptions")
    for tip in bill["ai_recommendations"]:
        if "Vampire" in tip:
            st.warning(tip)
        elif "Alert" in tip:
            st.error(tip)
        else:
            st.success(tip)

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
