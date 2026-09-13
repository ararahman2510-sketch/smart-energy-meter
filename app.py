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
    st.caption("• Architecture: Decoupled Microservices")
    st.caption("• Anomaly Model: Isolation Forest")

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

def fetch_smart_bill(base_url: str):
    try:
        res = requests.get(f"{base_url}/api/v1/analytics/bill", timeout=4)
        return res.json() if res.status_code == 200 else None
    except Exception:
        return None

st.title("⚡ AI Cloud Smart Meter & Energy Analytics")
st.caption("Continuous Telemetry Profiling • Anomaly Surge Isolation • Phantom Load Auditing")

telemetry_data = fetch_recent_telemetry(api_base_url)
bill_data = fetch_smart_bill(api_base_url)

if not telemetry_data:
    st.warning("⚠️ No incoming telemetry detected. Ensure main.py and simulator.py are running.")
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
m_col2.metric("Grid Voltage", f"{latest['voltage']} V", delta=f"{round(latest['voltage'] - 230.0, 1)} V nominal")
m_col3.metric("Load Current", f"{latest['current']} A")
m_col4.metric("Power Factor", f"{latest['power_factor']}")

if latest["is_anomaly"]:
    st.error(f"🚨 **Grid Surge Detected at {latest['formatted_time']}!** Active power spiked to **{latest['active_power_watts']} W** ({latest['current']} A). Isolation Forest flagged this pattern.")

st.markdown("---")
chart_col, anomaly_col = st.columns([2, 1])

with chart_col:
    st.subheader("📈 Live Power Profile (Last 60 Points)")
    chart_df = df[["formatted_time", "active_power_watts"]].set_index("formatted_time")
    st.line_chart(chart_df, use_container_width=True)

with anomaly_col:
    st.subheader("⚠️ Detected Anomalies")
    anomalies_df = df[df["is_anomaly"] == True]
    if not anomalies_df.empty:
        st.dataframe(anomalies_df[["formatted_time", "active_power_watts", "voltage", "current"]].iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("No anomalies in buffer.")

st.markdown("---")
st.subheader("💡 AI Energy Audit & Smart Billing")

if bill_data and "bill_details" in bill_data:
    bill = bill_data["bill_details"]
    phantom = bill_data["phantom_analysis"]
    
    b_col1, b_col2, b_col3 = st.columns(3)
    b_col1.metric("Projected Units", f"{bill['units_consumed_kwh']} kWh")
    b_col2.metric("Estimated Bill", f"₹{bill['total_bill_inr']}")
    
    phantom_label = f"₹{bill['phantom_waste_inr']}/mo" if phantom["is_phantom_detected"] else "₹0.00"
    b_col3.metric("Phantom Drain Cost", phantom_label, delta="Vampire Drain" if phantom["is_phantom_detected"] else "Optimal", delta_color="inverse")

    st.markdown("#### 🤖 Prescriptive Recommendations")
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
