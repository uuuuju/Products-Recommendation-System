# app.py

import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
import anthropic

# -----------------------
# PAGE CONFIG
# -----------------------
st.set_page_config(
    page_title="CurateCogit AI",
    page_icon="🛒",
    layout="wide"
)

# -----------------------
# SESSION STATE
# -----------------------
if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "rec_output" not in st.session_state:
    st.session_state.rec_output = None

if "copy_output" not in st.session_state:
    st.session_state.copy_output = None

if "plan_ready" not in st.session_state:
    st.session_state.plan_ready = False

# -----------------------
# LOAD CSS
# -----------------------
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# -----------------------
# ENV
# -----------------------
load_dotenv()

client = anthropic.Anthropic(
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
)

# -----------------------
# LOAD DATA
# -----------------------
products = pd.read_csv("products.csv")
orders = pd.read_csv("orders.csv")
order_items = pd.read_csv("order_items.csv")
customers = pd.read_csv("customers.csv")

# -----------------------
# HELPERS
# -----------------------
def get_recommendations(cart_items):
    if not cart_items:
        return []

    matching_orders = order_items[
        order_items["product_name"].isin(cart_items)
    ]["order_id"].unique()

    related = order_items[
        (order_items["order_id"].isin(matching_orders)) &
        (~order_items["product_name"].isin(cart_items))
    ]

    return related["product_name"].value_counts().head(5).index.tolist()


def get_cart_total(cart_items):
    rows = products[products["product_name"].isin(cart_items)]
    return rows["price"].sum()


def projected_aov(cart_total, rec_count):
    return round(cart_total + (rec_count * 120), 2)


# -----------------------
# AI AGENTS
# -----------------------
@st.cache_data(ttl=300)
def analyst_agent(cart_items):
    prompt = f"""
Analyze ecommerce customer intent from this cart:
{cart_items}

Keep response under 80 words.
"""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=250,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


@st.cache_data(ttl=300)
def recommendation_agent(cart_items):
    prompt = f"""
Suggest 3 upsell/cross-sell products for:
{cart_items}

Bullet points only.
"""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=250,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


@st.cache_data(ttl=300)
def copywriter_agent(cart_items):
    prompt = f"""
Write one WhatsApp marketing message to increase cart value for:
{cart_items}
"""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=250,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


# -----------------------
# TOP KPI BAR
# -----------------------
k1, k2, k3 = st.columns(3)

with k1:
    st.metric("Revenue Today", "₹86,940", "+12%")

with k2:
    st.metric("AOV", "₹1,449", "+8%")

with k3:
    st.metric("Repeat Rate", "38%", "+5%")


# -----------------------
# SIDEBAR
# -----------------------
st.sidebar.markdown("## Build Customer Cart")

goal = st.sidebar.selectbox(
    "Growth Goal",
    ["Increase AOV", "Reduce Churn", "Launch Campaign"]
)

cart_items = st.sidebar.multiselect(
    "Select products",
    products["product_name"].tolist()
)

generate = st.sidebar.button(
    "Optimize Cart",
    use_container_width=True,
    disabled=len(cart_items) == 0
)

# -----------------------
# HEADER
# -----------------------
st.markdown("""
<div class='hero'>
    <div>
        <h1>CurateCogit AI</h1>
        <p>Multi-Agent Revenue Copilot for E-commerce Brands</p>
    </div>
    <div class='pill'>Live Demo</div>
</div>
""", unsafe_allow_html=True)

# -----------------------
# RUN AI
# -----------------------
if generate and cart_items:
    with st.spinner("Optimizing cart..."):
        st.session_state.analysis = analyst_agent(cart_items)
        st.session_state.rec_output = recommendation_agent(cart_items)
        st.session_state.copy_output = copywriter_agent(cart_items)
        st.session_state.plan_ready = True

# -----------------------
# MAIN LAYOUT
# -----------------------
col1, col2 = st.columns([1.1, 1.4])

# -----------------------
# COLUMN 1 - CUSTOMER CART
# -----------------------
with col1:
    with st.container(border=True):
        st.subheader("Customer Cart")
        st.caption("Live customer basket")

        if cart_items:
            for item in cart_items:
                row = products[
                    products["product_name"] == item
                ].iloc[0]

                st.markdown(f"""
                <div class='product-row'>
                    <img src="https://picsum.photos/seed/{row['product_id']}/70">
                    <div class='grow'>
                        <div class='pname'>{row['product_name']}</div>
                        <div class='pcat'>{row['category']}</div>
                    </div>
                    <div class='price'>₹{row['price']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("Select products to begin")

        st.metric("Cart Value", f"₹{get_cart_total(cart_items)}")


# -----------------------
# COLUMN 2 - OPPORTUNITIES
# -----------------------
with col2:
    with st.container(border=True):
        st.subheader("Upsell Opportunities")
        st.caption("Recommended from basket affinity")

        recs = get_recommendations(cart_items)

        if recs:
            for r in recs[:5]:
                st.write("•", r)
        else:
            st.caption("Recommendations appear after selection")

        if cart_items:
            st.markdown("---")
            st.subheader("Revenue Forecast")

            cart_total = get_cart_total(cart_items)
            new_aov = projected_aov(cart_total, len(recs))
            uplift = new_aov - cart_total

            st.metric(
                "Projected Order Value",
                f"₹{new_aov}",
                f"+₹{round(uplift)}"
            )

# -----------------------
# ACTIVATION PLAN
# -----------------------
if st.session_state.plan_ready:
    with st.container(border=True):
        st.markdown("## Activation Plan")

        tab1, tab2, tab3 = st.tabs(
            ["Insights", "Recommendations", "Copy Message"]
        )

        with tab1:
            st.write(st.session_state.analysis)

        with tab2:
            st.write(st.session_state.rec_output)

        with tab3:
            st.write(st.session_state.copy_output)

        left, right = st.columns([4, 1])

        with right:
            if st.button(
                "Launch Campaign",
                use_container_width=True
            ):
                st.success(
                    "Campaign launched to 312 customers"
                )

# -----------------------
# FOOTER
# -----------------------
st.caption("CurateCogit AI • Built for CogitX")
