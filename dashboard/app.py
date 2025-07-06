# dashboard/app.py
import os, re, requests
from io import BytesIO
from PIL import Image

import pandas as pd
import streamlit as st
import altair as alt

# ── Load data ────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "ebay_cleaned.csv")
df = pd.read_csv(DATA_PATH)

# ── Brand extraction ──────────────────────────────────
KNOWN_BRANDS = ["nike", "adidas", "puma", "reebok", "asics", "converse", "skechers", "vans", "new", "balance"]

def extract_brand(title):
    if pd.isna(title): return None
    first = title.strip().split()[0].lower()
    return first if first in KNOWN_BRANDS else None

df["brand"] = df["title"].apply(extract_brand)

# ── Shipping fields ────────────────────────────────
df["free_shipping"] = df["shipping"].str.lower().str.contains("free", na=False)
df["shipping_cost"] = df["shipping"].apply(
    lambda s: 0 if pd.isna(s) or "free" in str(s).lower()
    else float(re.search(r"\d+\.?\d*", s).group()) if re.search(r"\d+\.?\d*", str(s)) else None
)

# ── Page setup ────────────────────────────────
st.set_page_config("eBay Retail Dashboard", layout="wide")
st.title("Retail Price Tracker — eBay Shoes")
st.caption("Explore eBay shoe listings: filter by brand, price, shipping, and discounts.")

# ── Sidebar filters ───────────────────────────────
brands_list = sorted([b for b in df["brand"].dropna().unique() if b in KNOWN_BRANDS])
brands_list.insert(0, "All")

# Setup session state defaults and reset logic
if "reset_triggered" not in st.session_state:
    st.session_state.reset_triggered = False
if "brands_select" not in st.session_state:
    st.session_state["brands_select"] = ["All"]
if "price_range" not in st.session_state:
    st.session_state["price_range"] = (float(df["price"].min()), float(df["price"].max()))
if "free_only" not in st.session_state:
    st.session_state["free_only"] = False
if "search_kw" not in st.session_state:
    st.session_state["search_kw"] = ""

if st.sidebar.button("Reset filters"):
    st.session_state.reset_triggered = True

if st.session_state.reset_triggered:
    st.session_state["brands_select"] = ["All"]
    st.session_state["price_range"] = (float(df["price"].min()), float(df["price"].max()))
    st.session_state["free_only"] = False
    st.session_state["search_kw"] = ""
    st.session_state.reset_triggered = False
    st.rerun()

selected_brands = st.sidebar.multiselect("Brands", brands_list, default=st.session_state["brands_select"], key="brands_select")
price_low, price_high = st.sidebar.slider("Price Range ($)", float(df["price"].min()), float(df["price"].max()), st.session_state["price_range"], key="price_range")
free_only = st.sidebar.checkbox("Free Shipping Only", value=st.session_state["free_only"], key="free_only")
search_kw = st.sidebar.text_input("Keyword in title", value=st.session_state["search_kw"], key="search_kw")

# ── Filter data ────────────────────────────────
flt = df.copy()
if "All" not in selected_brands:
    flt = flt[flt["brand"].isin(selected_brands)]
flt = flt[flt["price"].between(price_low, price_high)]
if free_only:
    flt = flt[flt["free_shipping"]]
if search_kw:
    pat = rf"\b{re.escape(search_kw)}\b"
    flt = flt[flt["title"].str.contains(pat, case=False, na=False)]

# ── KPI cards ───────────────────────────────
k1, k2, k3 = st.columns(3)
k1.metric("Total Listings", f"{len(flt):,}")
k2.metric("Median Price", f"${flt['price'].median():.2f}")
k3.metric("Free Shipping %", f"{flt['free_shipping'].mean()*100:.1f}%")

# ── Tabs: Charts ──────────────────────────────
tab1, tab2, tab3 = st.tabs(["📈 Price vs Discount", "🏷 Avg Discount by Brand", "🚚 Shipping Costs"])

with tab1:
    st.altair_chart(
        alt.Chart(flt)
        .mark_circle(size=60)
        .encode(x="discount_pct", y="price", color="brand", tooltip=["title", "price", "discount_pct"])
        .interactive(),
        use_container_width=True
    )

with tab2:
    top10_brands = flt["brand"].value_counts().head(10).index
    avg_discount = (
        flt[flt["brand"].isin(top10_brands)]
        .groupby("brand")["discount_pct"]
        .mean()
        .reset_index()
        .sort_values("discount_pct", ascending=False)
    )
    st.altair_chart(
        alt.Chart(avg_discount).mark_bar().encode(
            x=alt.X("brand", sort="-y"),
            y="discount_pct",
            tooltip=["discount_pct"]
        ),
        use_container_width=True
    )

with tab3:
    st.altair_chart(
        alt.Chart(flt.dropna(subset=["shipping_cost"]))
        .mark_bar()
        .encode(
            x=alt.X("shipping_cost", bin=True, title="Shipping Cost ($)"),
            y="count()", tooltip=["count()"]
        ),
        use_container_width=True
    )

# ── Top deals ────────────────────────────────
st.subheader("🔥 Top Deals (≥ 40% discount)")
deals = flt[flt["discount_pct"] >= 40].sort_values(["discount_pct", "price"], ascending=[False, True]).head(12)

if deals.empty:
    st.info("No deals found for selected filters.")
else:
    for _, r in deals.iterrows():
        with st.container():
            img_col, txt_col = st.columns([1, 4])
            with img_col:
                if pd.notna(r["image_url"]):
                    try:
                        img = requests.get(r["image_url"], timeout=5).content
                        st.image(Image.open(BytesIO(img)), width=100)
                    except:
                        st.write("🖼")
                else:
                    st.write("🖼")
            with txt_col:
                if pd.notna(r.get("product_url")):
                    st.markdown(f"<a href='{r['product_url']}' target='_blank'><strong>{r['title']}</strong></a>", unsafe_allow_html=True)
                else:
                    st.markdown(f"**{r['title']}**")

                st.write(f"💰 **${r['price']}**   🏷 **{r['discount_pct']}% off**")
                rating = f"{r['rating_num']:.1f}" if pd.notna(r['rating_num']) else "N/A"
                st.write(f"⭐ Rating: {rating}   🚚 {r['shipping']}")
        st.markdown("---", unsafe_allow_html=True)
