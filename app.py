import streamlit as st
import pandas as pd
import plotly.express as px
from prophet import Prophet
from prophet.plot import plot_plotly
import sqlite3
from fpdf import FPDF
import os
from datetime import datetime
# ------------------ CONFIG ------------------

st.set_page_config(
    page_title="Small Business Analyzer",
    layout="wide"
)

# ------------------ PROFESSIONAL UI STYLE ------------------


st.markdown("""
<style>
/* App Background */
[data-testid="stAppViewContainer"]{
    background-color:#f4f6fb;
}
/* Sidebar */
[data-testid="stSidebar"]{
    background-color:#1f2b3e;
}
[data-testid="stSidebar"] *{
    color:black;
}
/* Main container */
.block-container{
    background:white;
    padding:25px;
    border-radius:12px;
    box-shadow:0 4px 20px rgba(0,0,0,0.08);
}
/* Titles */
h1{
    color:#1f4e79;
    font-weight:700;
}
h2,h3{
    color:#2c3e50;
}
/* Buttons */
.stButton>button{
    background:#1f77b4;
    color:white;
    border-radius:8px;
    border:none;
    padding:10px;
    font-weight:500;
}
.stButton>button:hover{
    background:#155a8a;
}
/* Metric cards */
[data-testid="metric-container"]{
    background:white;
    border-radius:12px;
    padding:15px;
    box-shadow:0 2px 10px rgba(0,0,0,0.05);
}
/* Input boxes */
.stTextInput input{
    border-radius:8px;
}
.stNumberInput input{
    border-radius:8px;
}
</style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "admin123"
# ------------------ DATABASE ------------------

conn = sqlite3.connect("business.db", check_same_thread=False)
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE transactions ADD COLUMN receipt TEXT")
    conn.commit()
except:
    pass 

# Add date column if not exists
try:
    cursor.execute("ALTER TABLE transactions ADD COLUMN date TEXT")
    conn.commit()
except:
    pass
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT,
password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS businesses(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
business_id INTEGER,
type TEXT,
amount REAL,
category TEXT,
receipt TEXT,
date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory(
id INTEGER PRIMARY KEY AUTOINCREMENT,
business_id INTEGER,
product TEXT,
quantity INTEGER,
cost REAL,
price REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_sessions(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
login_time TEXT,
logout_time TEXT
)
""")


conn.commit()

# ---------------- PDF REPORT FUNCTION ----------------

def generate_pdf_report(business_name, sales, expense, profit, df):

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"Business Performance Report",ln=True,align="C")

    pdf.ln(5)

    pdf.set_font("Arial","",12)
    pdf.cell(0,10,f"Business Name: {business_name}",ln=True)

    pdf.ln(5)

    pdf.set_font("Arial","B",12)
    pdf.cell(0,10,"Financial Summary",ln=True)

    pdf.set_font("Arial","",11)
    pdf.cell(0,8,f"Total Sales: Rs {sales}",ln=True)
    pdf.cell(0,8,f"Total Expense: Rs {expense}",ln=True)
    pdf.cell(0,8,f"Net Profit: Rs {profit}",ln=True)

    pdf.ln(5)

    pdf.set_font("Arial","B",12)
    pdf.cell(0,10,"Transactions",ln=True)

    pdf.set_font("Arial","",10)

    for index,row in df.iterrows():
        pdf.cell(0,7,f"{row['type']} | {row['category']} | Rs {row['amount']}",ln=True)

    filename="business_report.pdf"
    pdf.output(filename)

    return filename

# ------------------ SESSION ------------------

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

if "admin_access" not in st.session_state:
    st.session_state.admin_access = False

# =====================================================
# LOGIN / REGISTER
# =====================================================

if not st.session_state.user_id:

    st.title("📊 Small Business Sales & Profit Analyzer")
    st.caption("Smart analytics platform to track sales, expenses, inventory and business growth.")

    st.sidebar.title("📊 Business Analyzer")

    menu = st.sidebar.radio("Menu", ["Login", "Register"])

    if menu == "Register":

        st.subheader("Create Account")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Register"):

            cursor.execute(
                "INSERT INTO users(username,password) VALUES(?,?)",
                (username, password)
            )
            conn.commit()

            st.success("✅ Registered successfully")

    if menu == "Login":

        st.subheader("Login to your account")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):

            cursor.execute(
                "SELECT id FROM users WHERE username=? AND password=?",
                (username, password)
            )

            user = cursor.fetchone()

            if user:
                st.session_state.user_id = user[0]
                st.session_state.username = username

    # Store login time
                login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute("""
                INSERT INTO user_sessions(user_id, login_time)
                VALUES(?,?)
                """, (user[0], login_time))

                conn.commit()

    # Save session ID
                st.session_state.session_id = cursor.lastrowid

                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

# =====================================================
# AFTER LOGIN
# =====================================================

else:

    st.sidebar.title(f"👋 Hello {st.session_state.username}")

    page = st.sidebar.radio(
        "Navigation",
        ["📊 Dashboard", "📦 Inventory", "📁 Upload Excel","📈 Forecast (AI)", "📑 Reports", "🧑‍💼 Admin", "🚪 Logout"]
    )
    if page != "🧑‍💼 Admin":
      st.session_state.admin_access = False
# =====================================================
# DASHBOARD
# =====================================================

    if page == "📊 Dashboard":

        st.header("Business Dashboard")

        business_name = st.text_input("Business Name")

        if st.button("Create Business"):

            cursor.execute(
                "INSERT INTO businesses(user_id,name) VALUES(?,?)",
                (st.session_state.user_id, business_name)
            )

            conn.commit()
            st.success("✅ Business Created")

        cursor.execute(
            "SELECT id,name FROM businesses WHERE user_id=?",
            (st.session_state.user_id,)
        )

        businesses = cursor.fetchall()

        if businesses:

            business = st.selectbox(
                "Select Business",
                businesses,
                format_func=lambda x: x[1]
            )

            business_id = business[0]

            st.markdown("### ➕ Add Transaction")

            t_type = st.radio("Type", ["Sale", "Expense"])

            cursor.execute(
               "SELECT product, quantity, cost, price FROM inventory WHERE business_id=?",
                (business_id,)
            )
            products = cursor.fetchall()

            product_names = [p[0] for p in products]

            selected_product = st.selectbox("Select Product", product_names)

            qty = st.number_input("Quantity Sold", min_value=1)

            category = st.text_input("Category")
            receipt = st.file_uploader("Upload Receipt / Invoice", type=["png","jpg","jpeg","pdf"])
            # ------------------ MANUAL DATE INPUT ------------------
            transaction_date = st.date_input("Transaction Date", value=datetime.today())
            transaction_date_str = transaction_date.strftime("%Y-%m-%d")  # Convert to string for DB
            if st.button("Add Transaction"):

                receipt_path = None

                if receipt is not None:
                    os.makedirs("receipts", exist_ok=True)
                    file_path = os.path.join("receipts", receipt.name)

                    with open(file_path, "wb") as f:
                       f.write(receipt.getbuffer())

                    receipt_path = file_path

    # Get product details
                cursor.execute("""
                    SELECT quantity, cost, price
                    FROM inventory
                    WHERE product=? AND business_id=?
                """, (selected_product, business_id))

                product_data = cursor.fetchone()

                if product_data:

                    stock, cost_price, selling_price = product_data

                    if t_type == "Sale":

                       if qty > stock:
                          st.error("❌ Not enough stock available")
                       else:

                # Calculate values
                          sales_amount = qty * selling_price
                          expense_amount = qty * cost_price
                          profit = sales_amount - expense_amount

                # Insert sale
                          cursor.execute("""
                             INSERT INTO transactions
                             (user_id, business_id, type, amount, category, receipt, date)
                              VALUES (?,?,?,?,?,?,?)
                          """, (
                               st.session_state.user_id,
                               business_id,
                               "Sale",
                               sales_amount,
                               category,
                               receipt_path,
                               transaction_date_str
                           ))

                # Insert cost as expense (COGS)
                          cursor.execute("""
                              INSERT INTO transactions
                              (user_id, business_id, type, amount, category, date)
                              VALUES (?,?,?,?,?,?)
                          """, (
                               st.session_state.user_id,
                               business_id,
                               "Expense",
                               expense_amount,
                               "COGS",
                               transaction_date_str
                               ))

                # Reduce stock
                          cursor.execute("""
                                 UPDATE inventory
                                 SET quantity = quantity - ?
                                 WHERE product=? AND business_id=?
                                 """, (qty, selected_product, business_id))

                          conn.commit()

                          st.success(f"✅ Sale recorded! Profit: ₹{profit}")

                else:
            # Normal expense
                    cursor.execute("""
                        INSERT INTO transactions
                        (user_id, business_id, type, amount, category, receipt, date)
                         VALUES (?,?,?,?,?,?,?)
                         """, (
                            st.session_state.user_id,
                            business_id,
                            "Expense",
                             amount,
                             category,
                             receipt_path,
                             transaction_date_str
                         ))

                    conn.commit()
                    st.success("Expense added")
            cursor.execute(
                "SELECT id,type,amount,category,receipt,date FROM transactions WHERE business_id=?",
                (business_id,)
            )

            rows = cursor.fetchall()

            if rows:

                df = pd.DataFrame(rows, columns=["id","type","amount","category","receipt","date"])
                df["date"] = pd.to_datetime(df["date"])
                # ---------------- DATE FILTER ----------------
                st.subheader("📅 Filter by Date")
                col1, col2 = st.columns(2)
                start_date = col1.date_input("Start Date", value=df["date"].min())
                end_date = col2.date_input("End Date", value=df["date"].max())
# Convert to datetime
                start_date = pd.to_datetime(start_date)
                end_date = pd.to_datetime(end_date)
                # Apply filter
                df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
                st.dataframe(df, use_container_width=True)
                total_sales = df[df["type"] == "Sale"]["amount"].sum()
                total_expense = df[df["type"] == "Expense"]["amount"].sum()
                net_profit = total_sales - total_expense
                
                col1, col2, col3 = st.columns(3)

                col1.metric("💰 Total Sales", f"₹ {total_sales}")
                col2.metric("📉 Total Expense", f"₹ {total_expense}")
                col3.metric("📊 Net Profit", f"₹ {net_profit}")
                # ---------------- PROFIT MARGIN ----------------
                if total_sales > 0:
                    profit_margin = (total_sales - total_expense) / total_sales * 100
                else:
                    profit_margin = 0
                st.metric("📈 Profit Margin", f"{profit_margin:.2f}%")    
                # -------- WEEKLY SALES SUMMARY --------
                st.subheader("📊 Weekly Sales Summary")

                weekly = df[df["type"]=="Sale"].groupby(
                    df["date"].dt.to_period("W")
                )["amount"].sum().reset_index()

                weekly["date"] = weekly["date"].astype(str)

                fig_week = px.bar(
                    weekly,
                    x="date",
                    y="amount",
                    title="Weekly Sales Trend"
                 )

                st.plotly_chart(fig_week)

                # ---------------- MONTHLY PROFIT ----------------
                st.subheader("📈 Monthly Profit Summary")

                monthly = df.groupby(
                  df["date"].dt.to_period("M")
                ).apply(
                    lambda x: x[x["type"]=="Sale"]["amount"].sum()
                      - x[x["type"]=="Expense"]["amount"].sum()
                ).reset_index(name="profit")

                monthly["date"] = monthly["date"].astype(str)

                fig_month = px.line(
                   monthly,
                   x="date",
                   y="profit",
                   markers=True,
                   title="Monthly Profit Trend"
                )

                st.plotly_chart(fig_month)
                # ---------------- CATEGORY-WISE PROFIT ----------------
                st.subheader("📊 Category-wise Profit")

                category_profit = df.groupby("category").apply(
                    lambda x: x[x["type"]=="Sale"]["amount"].sum()
                             - x[x["type"]=="Expense"]["amount"].sum()
                ).reset_index(name="profit")

                fig_cat = px.bar(
                  category_profit,
                  x="category",
                  y="profit",
                  title="Category-wise Profit"
                )

                st.plotly_chart(fig_cat)
                # ---------------- AI BUSINESS INSIGHTS ----------------
                st.subheader("💡 Business Insights")

# Filter only sales
                sales_df = df[df["type"]=="Sale"].copy()
                sales_df['month'] = sales_df['date'].dt.to_period('M')

# Monthly sales sum
                monthly_sales = sales_df.groupby('month')['amount'].sum().reset_index()
                monthly_sales['month'] = monthly_sales['month'].astype(str)

# Calculate percentage change vs previous month
                monthly_sales['pct_change'] = monthly_sales['amount'].pct_change() * 100

# Generate insights
                insights = []

                if len(monthly_sales) > 1:
                   last_change = monthly_sales['pct_change'].iloc[-1]
    
                   if last_change < -10:  # >10% drop
                     insights.append(f"⚠️ Sales dropped by {abs(last_change):.1f}% compared to last month. Consider running a promotion!")
                   elif last_change > 10:  # >10% increase
                     insights.append(f"✅ Sales increased by {last_change:.1f}% compared to last month. Keep up the good work!")
                   else:
                     insights.append("📈 Sales are stable compared to last month.")
                else:
                  insights.append("Not enough data to generate insights.")

# Display in Streamlit
                for insight in insights:
                    st.info(insight)
                # ---------------- SMART RECOMMENDATION ----------------
                if profit_margin < 10:
                    st.warning("⚠️ Low profit margin. Try reducing costs or increasing price.")
                elif profit_margin > 30:
                    st.success("💰 Excellent profit margin!")
                else:
                    st.info("👍 Profit margin is moderate. Monitor regularly.")
                # ================= ADVANCED INSIGHTS =================

                # 🏆 Best Category
                cursor.execute("""
                SELECT category, SUM(amount)
                FROM transactions
                WHERE type='Sale' AND business_id=?
                GROUP BY category
                ORDER BY SUM(amount) DESC
                LIMIT 1
                """, (business_id,))

                top = cursor.fetchone()

                if top:
                    st.success(f"🏆 Best Category: {top[0]}")

                # 📉 Worst Category
                cursor.execute("""
                SELECT category, SUM(amount)
                FROM transactions
                WHERE type='Sale' AND business_id=?
                GROUP BY category
                ORDER BY SUM(amount) ASC
                LIMIT 1
                """, (business_id,))

                low = cursor.fetchone()

                if low:
                    st.warning(f"📉 Lowest Category: {low[0]}")    
                selected_id = st.selectbox("Select Transaction", df["id"])

                selected_row = df[df["id"] == selected_id].iloc[0]

                col1,col2 = st.columns(2)

                if col1.button("Delete Transaction"):

                    cursor.execute("DELETE FROM transactions WHERE id=?", (selected_id,))
                    conn.commit()

                    st.success("Deleted")
                    st.experimental_rerun()

                if col2.button("Edit Transaction"):

                    st.session_state.edit_mode = True
                    st.session_state.edit_id = selected_id

                if st.session_state.edit_mode:

                    new_amount = st.number_input(
                        "New Amount",
                        value=float(selected_row["amount"])
                    )

                    new_category = st.text_input(
                        "New Category",
                        value=selected_row["category"]
                    )

                    if st.button("Update Transaction"):

                        cursor.execute("""
                        UPDATE transactions
                        SET amount=?,category=?
                        WHERE id=?
                        """,(new_amount,new_category,st.session_state.edit_id))

                        conn.commit()

                        st.success("Updated Successfully")
                        st.session_state.edit_mode=False
                        st.experimental_rerun()

# =====================================================
# INVENTORY
# =====================================================

    if page == "📦 Inventory":

        st.header("Inventory Management")

        cursor.execute(
            "SELECT id,name FROM businesses WHERE user_id=?",
            (st.session_state.user_id,)
        )

        businesses = cursor.fetchall()

        if businesses:

            business = st.selectbox(
                "Select Business",
                businesses,
                format_func=lambda x: x[1]
            )

            business_id = business[0]

            product = st.text_input("Product")
            qty = st.number_input("Quantity", min_value=0)
            cost = st.number_input("Cost Price", min_value=0.0)
            price = st.number_input("Selling Price", min_value=0.0)

            if st.button("Add Product"):

                cursor.execute("""
                INSERT INTO inventory(business_id,product,quantity,cost,price)
                VALUES(?,?,?,?,?)
                """,(business_id,product,qty,cost,price))

                conn.commit()
                st.success("Product Added")

            st.markdown("### Low Stock Alerts")

            cursor.execute(
                "SELECT product,quantity FROM inventory WHERE business_id=?",
                (business_id,)
            )

            items = cursor.fetchall()

            for product,q in items:
                if q < 5:
                    st.warning(f"Low stock: {product} ({q})")
            # ---------------- Inventory Details Table ----------------
            st.markdown("### 🗃️ Inventory Details")

            cursor.execute(
              "SELECT product, quantity, cost, price FROM inventory WHERE business_id=?",
               (business_id,)
             )
            inventory_data = cursor.fetchall()

            if inventory_data:
              inv_df = pd.DataFrame(inventory_data, columns=["Product", "Quantity", "Cost Price", "Selling Price"])
              st.dataframe(inv_df, use_container_width=True)

    # ---------------- Charts ----------------
              st.markdown("### 📊 Inventory Charts")

    # Pie chart for product quantity distribution
              fig_pie = px.pie(inv_df, names="Product", values="Quantity", title="Product Quantity Distribution")
              st.plotly_chart(fig_pie)

    # Bar chart for quantity per product
              fig_bar = px.bar(inv_df, x="Product", y="Quantity", title="Quantity per Product", text="Quantity")
              st.plotly_chart(fig_bar)

    # Line chart for price trend
              fig_line = px.line(inv_df, x="Product", y="Selling Price", title="Selling Price Trend", markers=True)
              st.plotly_chart(fig_line)

    # Histogram for cost distribution
              fig_hist = px.histogram(inv_df, x="Cost Price", nbins=10, title="Cost Price Distribution")
              st.plotly_chart(fig_hist)
            else:
              st.info("No inventory records found for this business.")
    # =====================================================
    # FORECASTING
    # =====================================================

    if page == "📁 Upload Excel":

        st.header("Sales Forecast")

        file = st.file_uploader("Upload CSV or Excel", type=["csv","xlsx"])

        if file:

            if file.name.endswith("xlsx"):
                df = pd.read_excel(file)
            else:
                df = pd.read_csv(file)

            st.dataframe(df, use_container_width=True)

            date_col = st.selectbox("Date Column", df.columns)

            numeric = df.select_dtypes(include=["int64","float64"]).columns
            value_col = st.selectbox("Value Column", numeric)

            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

            if df[date_col].isna().all():
                st.error("❌ Selected column is not a valid date column")
                st.stop()

            df = df.dropna(subset=[date_col])

            data = df[[date_col, value_col]].rename(
                columns={date_col: "ds", value_col: "y"}
            )

            model = Prophet()
            model.fit(data)

            future = model.make_future_dataframe(periods=30)
            forecast = model.predict(future)

            fig = plot_plotly(model, forecast)

            st.plotly_chart(fig)
# =====================================================
# FORECAST FROM DATABASE
# =====================================================

    if page == "📈 Forecast (AI)":

       st.header("📈 AI Sales Forecast ")

       cursor.execute(
          "SELECT id,name FROM businesses WHERE user_id=?",
          (st.session_state.user_id,)
       )

       businesses = cursor.fetchall()

       if businesses:

          business = st.selectbox(
            "Select Business",
            businesses,
            format_func=lambda x: x[1]
          )

          business_id = business[0]

        # Fetch sales data
          cursor.execute("""
            SELECT date, amount 
            FROM transactions 
            WHERE business_id=? AND type='Sale'
          """, (business_id,))

          data = cursor.fetchall()

          if data:

            df = pd.DataFrame(data, columns=["date", "amount"])

            df["date"] = pd.to_datetime(df["date"])

            # Prepare for Prophet
            df = df.rename(columns={"date": "ds", "amount": "y"})

            # Group by date (important)
            df = df.groupby("ds")["y"].sum().reset_index()

            st.dataframe(df)

            # ---------------- TRAIN TEST SPLIT ----------------
            if len(df) > 10: 
                train =df[:-7]
                test = df[-7:]

                model = Prophet()
                model.fit(train)

                future = model.make_future_dataframe(periods=7)
                forecast = model.predict(future)
                # ---------------- ACCURACY ----------------
                pred = forecast[["ds", "yhat"]].tail(7)
                merged = test.merge(pred, on="ds")

                from sklearn.metrics import mean_absolute_error

                mae = mean_absolute_error(merged["y"], merged["yhat"])

                st.metric("📉 Forecast Error (MAE)", f"{mae:.2f}")
                 # ---------------- PLOT ----------------
                fig = plot_plotly(model, forecast)
                st.plotly_chart(fig)

          else:
            st.warning("Not enough data for accuracy calculation (need at least 10 records)")
# =====================================================
# REPORTS
# =====================================================

    if page == "📑 Reports":

        st.header("Reports & Analytics")

        cursor.execute(
            "SELECT id,name FROM businesses WHERE user_id=?",
            (st.session_state.user_id,)
        )

        businesses = cursor.fetchall()

        if businesses:

            business = st.selectbox(
                "Select Business",
                businesses,
                format_func=lambda x:x[1]
            )

            business_id = business[0]

            cursor.execute(
                "SELECT type,amount,category FROM transactions WHERE business_id=?",
                (business_id,)
            )

            data = cursor.fetchall()

            if data:

                df = pd.DataFrame(data, columns=["type","amount","category"])

                sales = df[df["type"]=="Sale"]["amount"].sum()
                expense = df[df["type"]=="Expense"]["amount"].sum()
                profit = sales-expense

                col1,col2,col3 = st.columns(3)

                col1.metric("💰 Total Sales",f"₹ {sales}")
                col2.metric("📉 Total Expense",f"₹ {expense}")
                col3.metric("📊 Profit",f"₹ {profit}")

                fig = px.pie(
                    df,
                    names="category",
                    values="amount",
                    hole=0.4,
                    title="Expense Distribution"
                )

                fig.update_layout(template="plotly_white")

                st.plotly_chart(fig)

                csv = df.to_csv(index=False).encode()

                st.download_button("Download CSV",csv,"report.csv")

                if st.button("Generate PDF Report"):

                    filename = generate_pdf_report(
                        business[1],
                        sales,
                        expense,
                        profit,
                        df
                    )

                    with open(filename,"rb") as f:

                        st.download_button(
                            "Download PDF Report",
                            f,
                            "business_report.pdf",
                            mime="application/pdf"
                        )

# =====================================================
# ADMIN DASHBOARD
# =====================================================

    if page == "🧑‍💼 Admin":

        st.header("Admin Dashboard")

        if not st.session_state.admin_access:

            pwd = st.text_input("Enter Admin Password",type="password")

            if st.button("Login as Admin"):

                if pwd == ADMIN_PASSWORD:

                    st.session_state.admin_access=True
                    st.success("Access granted")
                    st.experimental_rerun()

                else:
                    st.error("Wrong password")

        else:

            cursor.execute("SELECT COUNT(*) FROM users")
            users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM businesses")
            businesses = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM transactions")
            transactions = cursor.fetchone()[0]

            col1,col2,col3 = st.columns(3)

            col1.metric("Users",users)
            col2.metric("Businesses",businesses)
            col3.metric("Transactions",transactions)

            st.subheader("Manage Users")

            cursor.execute("SELECT id,username,password FROM users")
            user_data = cursor.fetchall()

            if user_data:

                user_df = pd.DataFrame(user_data,columns=["User ID","Username","password"])
                st.dataframe(user_df,use_container_width=True)

                selected_user = st.selectbox("Select User",user_df["User ID"])

                col1,col2 = st.columns(2)

                if col1.button("Delete Selected User"):

                    cursor.execute("DELETE FROM users WHERE id=?", (selected_user,))
                    conn.commit()

                    st.success("User deleted")
                    st.experimental_rerun()

                new_password = col2.text_input("New Password for User",type="password")

                if col2.button("Update User Password"):

                    cursor.execute(
                        "UPDATE users SET password=? WHERE id=?",
                        (new_password,selected_user)
                    )

                    conn.commit()
                    st.success("Password updated successfully")
            st.subheader("🕒 User Login Activity")

            cursor.execute("""
            SELECT users.username, user_sessions.login_time, user_sessions.logout_time
            FROM user_sessions
            JOIN users ON user_sessions.user_id = users.id
            ORDER BY user_sessions.id DESC
            """)

            session_data = cursor.fetchall()

            if session_data:

               session_df = pd.DataFrame(
               session_data,
               columns=["Username", "Login Time", "Logout Time"]
               )

               st.dataframe(session_df, use_container_width=True)

            else:
               st.info("No session data available")
            st.subheader("Manage Businesses")

            cursor.execute("""
            SELECT businesses.id,businesses.name,users.username
            FROM businesses
            JOIN users ON businesses.user_id=users.id
            """)

            biz_data = cursor.fetchall()

            if biz_data:

                biz_df = pd.DataFrame(
                    biz_data,
                    columns=["Business ID","Business Name","Owner"]
                )

                st.dataframe(biz_df,use_container_width=True)

                biz_delete = st.selectbox("Delete Business",biz_df["Business ID"])

                if st.button("Delete Selected Business"):

                    cursor.execute("DELETE FROM businesses WHERE id=?", (biz_delete,))
                    conn.commit()

                    st.success("Business deleted")
                    st.experimental_rerun()

            st.subheader("System Usage Monitoring")

            cursor.execute("SELECT type,COUNT(*) FROM transactions GROUP BY type")
            usage = cursor.fetchall()

            if usage:

                usage_df = pd.DataFrame(usage,columns=["Type","Count"])

                fig = px.bar(usage_df,x="Type",y="Count",title="Transaction Usage")
                fig.update_layout(template="plotly_white")

                st.plotly_chart(fig)

            st.subheader("Data Quality Monitor")

            cursor.execute("""
            SELECT id,type,amount,category
            FROM transactions
            WHERE amount<=0 OR category=''
       """)

            bad_data = cursor.fetchall()

            if bad_data:

              bad_df = pd.DataFrame(
              bad_data,
              columns=["Transaction ID","Type","Amount","Category"]
         )

              st.warning(f"{len(bad_df)} invalid transactions found")

              st.dataframe(bad_df, use_container_width=True)

    # Optional: admin can delete bad records
              bad_id = st.selectbox(
                  "Select Invalid Transaction to Remove",
                   bad_df["Transaction ID"]
             )

              if st.button("Delete Invalid Transaction"):

                    cursor.execute(
                       "DELETE FROM transactions WHERE id=?",
                       (bad_id,)
            )

                    conn.commit()

                    st.success("Invalid transaction removed")
                    st.experimental_rerun()

            else:

                 st.success("No data issues found")

            if st.button("Logout Admin"):

                st.session_state.admin_access=False
                st.experimental_rerun()

# =====================================================
# LOGOUT
# =====================================================

    if page == "🚪 Logout":

       if "session_id" in st.session_state:

           logout_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

           cursor.execute("""
           UPDATE user_sessions
           SET logout_time=?
           WHERE id=?
           """, (logout_time, st.session_state.session_id))

           conn.commit()

       st.session_state.user_id = None
       st.experimental_rerun()
