import streamlit as st
import pandas as pd
import plotly.express as px
from prophet import Prophet
from prophet.plot import plot_plotly
from db import get_db
from auth import create_token, verify_token

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Small Business Sales & Profit Analyzer",
    page_icon="💰",
    layout="wide"
)

# ---------------- DATABASE ----------------
db = get_db()
cursor = db.cursor()

# -------- CREATE EXTRA TABLES (IMPORTANT) ----------
cursor.execute("""
CREATE TABLE IF NOT EXISTS businesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    business_name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    business_id INTEGER,
    type TEXT,
    amount REAL,
    category TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER,
    product_name TEXT,
    quantity INTEGER,
    cost_price REAL,
    selling_price REAL
)
""")

db.commit()

# ---------------- SESSION ----------------
if "token" not in st.session_state:
    st.session_state.token = None

# ==========================================================
# ================= LOGIN / REGISTER =======================
# ==========================================================
if not st.session_state.token:

    st.title("🔐 Small Business Sales & Profit Analyzer")

    page = st.sidebar.radio("Navigation", ["Login", "Register"])

    # REGISTER
    if page == "Register":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Register"):
            cursor.execute("SELECT * FROM users WHERE username=?", (username,))
            if cursor.fetchone():
                st.error("Username already exists")
            else:
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (?,?)",
                    (username, password)
                )
                db.commit()
                st.success("Registered successfully! Please login.")

    # LOGIN
    if page == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            cursor.execute(
                "SELECT id FROM users WHERE username=? AND password=?",
                (username, password)
            )
            user = cursor.fetchone()

            if user:
                st.session_state.token = create_token(user[0])
                st.rerun()
            else:
                st.error("Invalid credentials")

# ==========================================================
# ================= AFTER LOGIN ============================
# ==========================================================
else:

    user_id = verify_token(st.session_state.token)

    if not user_id:
        st.session_state.token = None
        st.rerun()

    cursor.execute("SELECT username FROM users WHERE id=?", (user_id,))
    username = cursor.fetchone()[0].capitalize()

    st.sidebar.markdown(f"## 👋 Hello {username}")
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Inventory", "Upload Excel", "Reports", "Admin", "Logout"]
    )

# ==========================================================
# ================= DASHBOARD ==============================
# ==========================================================
    if page == "Dashboard":

        st.header("Dashboard")

        business_name = st.text_input("Business Name")

        if st.button("Create Business"):
            cursor.execute(
                "INSERT INTO businesses (user_id, business_name) VALUES (?,?)",
                (user_id, business_name)
            )
            db.commit()
            st.success("Business created")

        cursor.execute("SELECT id, business_name FROM businesses WHERE user_id=?", (user_id,))
        businesses = cursor.fetchall()

        if businesses:
            business_choice = st.selectbox(
                "Select Business",
                businesses,
                format_func=lambda x: x[1]
            )
            business_id = business_choice[0]

            st.subheader("Add Sale / Expense")

            t_type = st.radio("Type", ["Sale", "Expense"])
            amount = st.number_input("Amount", min_value=0.0)
            category = st.text_input("Category")

            if st.button("Add Transaction"):
                cursor.execute("""
                    INSERT INTO transactions
                    (user_id, business_id, type, amount, category)
                    VALUES (?,?,?,?,?)
                """, (user_id, business_id, t_type, amount, category))
                db.commit()
                st.success("Transaction added")

# ==========================================================
# ================= INVENTORY ==============================
# ==========================================================
    if page == "Inventory":

        st.header("Inventory Management")

        cursor.execute("SELECT id, business_name FROM businesses WHERE user_id=?", (user_id,))
        businesses = cursor.fetchall()

        if businesses:
            business_choice = st.selectbox(
                "Select Business",
                businesses,
                format_func=lambda x: x[1]
            )
            business_id = business_choice[0]

            product_name = st.text_input("Product Name")
            quantity = st.number_input("Quantity", min_value=0)
            cost_price = st.number_input("Cost Price", min_value=0.0)
            selling_price = st.number_input("Selling Price", min_value=0.0)

            if st.button("Add Product"):
                cursor.execute("""
                    INSERT INTO inventory
                    (business_id, product_name, quantity, cost_price, selling_price)
                    VALUES (?,?,?,?,?)
                """, (business_id, product_name, quantity, cost_price, selling_price))
                db.commit()
                st.success("Product added")

# ==========================================================
# ================= UPLOAD EXCEL ===========================
# ==========================================================
    if page == "Upload Excel":

        st.header("📊 Advanced Analytics")

        uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

        if uploaded_file:

            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith("xlsx") else pd.read_csv(uploaded_file)

            df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

            required_cols = ["date", "product", "quantity", "selling_price", "cost_price"]

            if not all(col in df.columns for col in required_cols):
                st.error("Required columns: Date, Product, Quantity, Selling Price, Cost Price")
                st.stop()

            df["date"] = pd.to_datetime(df["date"])
            df["sales"] = df["quantity"] * df["selling_price"]
            df["expenses"] = df["quantity"] * df["cost_price"]
            df["profit"] = df["sales"] - df["expenses"]

            st.dataframe(df)

            daily = df.groupby("date")[["sales"]].sum().reset_index()
            forecast_df = daily.rename(columns={"date": "ds", "sales": "y"})

            model = Prophet()
            model.fit(forecast_df)

            future = model.make_future_dataframe(periods=7)
            forecast = model.predict(future)

            fig = plot_plotly(model, forecast)
            st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# ================= REPORTS ================================
# ==========================================================
    if page == "Reports":

        st.header("Business Report")

        cursor.execute("SELECT id, business_name FROM businesses WHERE user_id=?", (user_id,))
        businesses = cursor.fetchall()

        if businesses:
            business_choice = st.selectbox(
                "Select Business",
                businesses,
                format_func=lambda x: x[1]
            )
            business_id = business_choice[0]

            cursor.execute("""
                SELECT type, amount, category
                FROM transactions
                WHERE business_id=?
            """, (business_id,))

            data = cursor.fetchall()

            if data:
                df = pd.DataFrame(data, columns=["type","amount","category"])

                total_sales = df[df["type"]=="Sale"]["amount"].sum()
                total_expense = df[df["type"]=="Expense"]["amount"].sum()
                profit = total_sales - total_expense

                st.success(f"Total Sales: ₹{total_sales}")
                st.error(f"Total Expense: ₹{total_expense}")
                st.info(f"Net Profit: ₹{profit}")

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("Download Report", csv, "business_report.csv")

# ==========================================================
# ================= ADMIN ==================================
# ==========================================================
    if page == "Admin":

        st.header("Admin Dashboard")

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM businesses")
        total_business = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transactions")
        total_transactions = cursor.fetchone()[0]

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Users", total_users)
        col2.metric("Total Businesses", total_business)
        col3.metric("Total Transactions", total_transactions)

# ==========================================================
# ================= LOGOUT =================================
# ==========================================================
    if page == "Logout":
        st.session_state.token = None
        st.rerun()


