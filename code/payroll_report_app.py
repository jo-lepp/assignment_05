"""Salt City Coffee quarterly payroll report."""

import streamlit as st
import pandas as pd

import payroll


def _filtered_history(history: pd.DataFrame, department: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    out = history.copy()
    if department != "All":
        out = out[out["department"] == department]
    out = out[(out["pay_date"] >= start) & (out["pay_date"] <= end)]
    return out


st.title("Salt City Coffee — Quarterly Payroll Report")
st.caption("Upload payroll exports to preview the quarter by department and date.")

roster = payroll.load_employees()
uploads = st.file_uploader("Quarterly payroll exports", type=["csv"], accept_multiple_files=True, key="exports")

if uploads:
    history = payroll.build_history([payroll.load_export(upload) for upload in uploads], roster)

    unmatched = sorted(history.loc[history["department"].isna(), "employee_id"].drop_duplicates())
    if unmatched:
        st.warning(f"Unmatched employee IDs were left out of the report: {', '.join(unmatched)}")

    filtered = history.dropna(subset=["department"]).copy()
    departments = ["All"] + sorted(filtered["department"].dropna().unique())
    department = st.selectbox("Department", departments, index=0, key="department")

    first = filtered["pay_date"].min()
    last = filtered["pay_date"].max()
    start_date = first.date()
    end_date = last.date()
    dates = st.date_input("Pay dates", value=(start_date, end_date), min_value=start_date, max_value=end_date, key="dates")
    if isinstance(dates, tuple):
        start, end = dates if len(dates) == 2 else (dates[0], dates[0])
    else:
        start = end = dates

    selected = _filtered_history(filtered, department, pd.Timestamp(start), pd.Timestamp(end))
    if selected.empty:
        st.info("No rows match the current department and date range.")
    else:
        weeks = selected["week_ending"].nunique()
        employees = selected["employee_id"].nunique()
        total_hours = selected["hours_worked"].sum()
        total_pay = selected["gross_pay"].sum()

        cols = st.columns(4)
        cols[0].metric("Weeks", str(weeks))
        cols[1].metric("Employees", str(employees))
        cols[2].metric("Total hours", f"{total_hours:,.2f}")
        cols[3].metric("Total gross pay", f"${total_pay:,.2f}")

        monthly = payroll.pay_by_month(selected)
        st.bar_chart(monthly, x="month")
        st.dataframe(payroll.summarize_employees(selected))
        st.dataframe(payroll.hours_grid(selected))
        st.dataframe(payroll.missed_weeks(payroll.hours_grid(selected)))
        st.download_button(
            "Download CSV",
            data=monthly.to_csv(index=False),
            file_name="payroll_by_month.csv",
            key="download",
        )
