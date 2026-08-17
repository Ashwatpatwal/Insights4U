# streamlit_app.py
import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Insight4U Dashboard", layout="wide")

st.title("Insight4U Dashboard")
st.markdown(
    "Upload your sales file (CSV or Excel), click 'Preprocess', and get an interactive dashboard automatically!"
)

uploaded_file = st.file_uploader(
    "Upload your file (CSV or Excel)", type=["csv", "xlsx"]
)

if "processed_df" not in st.session_state:
  st.session_state.processed_df = None


def normalize_columns(dataframe):
  """Maps alternative common column names to standard dashboard columns."""
  column_mapping = {
      "Campaign ID": "Campaign Name",
      "Campaign": "Campaign Name",
      "Ad Spend ($)": "Estimated Budget Consumed",
      "Ad Spend": "Estimated Budget Consumed",
      "Budget Spent": "Estimated Budget Consumed",
      "Spend": "Estimated Budget Consumed",
      "Campaign Type": "Targeting Type",
      "Product": "Targeting Value",
      "Brand": "Targeting Value",
      "Direct Sales ($)": "Direct Sales",
      "Indirect Sales ($)": "Indirect Sales",
      "GMV ($)": "Total Sales",
      "GMV": "Total Sales",
  }
  for old_col, new_col in column_mapping.items():
    if old_col in dataframe.columns and new_col not in dataframe.columns:
      dataframe[new_col] = dataframe[old_col]
  return dataframe


if uploaded_file:
  if uploaded_file.name.endswith(".csv"):
    df = pd.read_csv(uploaded_file)
  else:
    df = pd.read_excel(uploaded_file)

  # Auto-map alternative column names
  df = normalize_columns(df)

  # Flexible date conversion
  if "Date" in df.columns:
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df.dropna(subset=["Date"], inplace=True)

  st.subheader("Raw File Preview")
  st.dataframe(df.head())

  if st.button("Preprocess"):
    # Check for direct/indirect or total sales directly
    if "Direct Sales" in df.columns and "Indirect Sales" in df.columns:
      df["Total Sales"] = df["Direct Sales"] + df["Indirect Sales"]
      st.session_state.processed_df = df
      st.success("Preprocessing Complete. 'Total Sales' column calculated.")
    elif "Total Sales" in df.columns:
      st.session_state.processed_df = df
      st.success("Preprocessing Complete. 'Total Sales' column detected.")
    else:
      st.error(
          "Missing required sales columns. Please provide 'Direct Sales' and"
          " 'Indirect Sales' or 'Total Sales'."
      )

if st.session_state.processed_df is not None:
  df = st.session_state.processed_df

  st.subheader("Processed Data Preview")
  st.dataframe(df.head())

  with st.sidebar:
    st.header("Filter Options")

    # Safe min/max date extraction
    if "Date" in df.columns and not df["Date"].empty:
      min_date = df["Date"].min()
      max_date = df["Date"].max()
    else:
      min_date = datetime.date.today()
      max_date = datetime.date.today()

    date_filter_option = st.selectbox(
        "Select Date Filter",
        options=[
            "Today",
            "Yesterday",
            "Last 7 Days",
            "Last 30 Days",
            "Custom Range",
        ],
    )
    if date_filter_option == "Today":
      start_date = end_date = max_date
    elif date_filter_option == "Yesterday":
      yesterday = max_date - datetime.timedelta(days=1)
      start_date = end_date = yesterday
    elif date_filter_option == "Last 7 Days":
      start_date = max_date - datetime.timedelta(days=6)
      end_date = max_date
    elif date_filter_option == "Last 30 Days":
      start_date = max_date - datetime.timedelta(days=29)
      end_date = max_date
    else:
      date_range = st.date_input(
          "Select Custom Date Range",
          value=(min_date, max_date),
          min_value=min_date,
          max_value=max_date,
      )
      if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
      elif isinstance(date_range, tuple) and len(date_range) == 1:
        start_date = end_date = date_range[0]
      else:
        start_date = end_date = min_date

    # Populate dropdown filters safely
    campaign_names = (
        df["Campaign Name"].dropna().unique().tolist()
        if "Campaign Name" in df.columns
        else []
    )
    selected_campaign = st.selectbox(
        "Select Campaign Name",
        options=["All"] + campaign_names,
        key="campaign",
    )

    targeting_types = (
        df["Targeting Type"].dropna().unique().tolist()
        if "Targeting Type" in df.columns
        else []
    )
    selected_type = st.selectbox(
        "Select Targeting Type", options=["All"] + targeting_types, key="type"
    )

    targeting_values = (
        df["Targeting Value"].dropna().unique().tolist()
        if "Targeting Value" in df.columns
        else []
    )
    selected_value = st.selectbox(
        "Select Targeting Value",
        options=["All"] + targeting_values,
        key="value",
    )

  # Apply Filters
  filtered_df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

  if selected_campaign != "All" and "Campaign Name" in filtered_df.columns:
    filtered_df = filtered_df[
        filtered_df["Campaign Name"] == selected_campaign
    ]

  if selected_type != "All" and "Targeting Type" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["Targeting Type"] == selected_type]

  if selected_value != "All" and "Targeting Value" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["Targeting Value"] == selected_value]

  # Strategic Insights Section
  if not filtered_df.empty:
    total_campaigns = (
        filtered_df["Campaign Name"].nunique()
        if "Campaign Name" in filtered_df.columns
        else 0
    )
    total_budget_spend = (
        filtered_df["Estimated Budget Consumed"].sum()
        if "Estimated Budget Consumed" in filtered_df.columns
        else 0
    )
    total_sales = (
        filtered_df["Total Sales"].sum()
        if "Total Sales" in filtered_df.columns
        else 0
    )
    avg_sales_per_campaign = (
        total_sales / total_campaigns if total_campaigns > 0 else 0
    )

    avg_total_roas = 0
    if (
        "Campaign Name" in filtered_df.columns
        and "Estimated Budget Consumed" in filtered_df.columns
    ):
      roas_df = (
          filtered_df.groupby("Campaign Name")
          .agg(
              {
                  "Total Sales": "sum",
                  "Estimated Budget Consumed": "sum",
              }
          )
          .reset_index()
      )
      roas_df = roas_df[roas_df["Estimated Budget Consumed"] > 0]
      roas_df["ROAS"] = (
          roas_df["Total Sales"] / roas_df["Estimated Budget Consumed"]
      )
      avg_total_roas = roas_df["ROAS"].mean() if not roas_df.empty else 0

    st.subheader("Campaign Insights Summary")
    col4, col5, col6, col7 = st.columns(4)
    col4.metric("Total Campaigns", total_campaigns)
    col5.metric("Total Budget Spend", f"${total_budget_spend:,.2f}")
    col6.metric("Avg Sales per Campaign", f"${avg_sales_per_campaign:,.2f}")
    col7.metric("Avg ROAS Across Campaigns", f"{avg_total_roas:.2f}x")

    # Recommendations
    st.subheader("Strategic Recommendations")

    # High Impressions Focus
    if (
        "Impressions" in filtered_df.columns
        and "Targeting Type" in filtered_df.columns
    ):
      impressions_by_type = (
          filtered_df.groupby("Targeting Type")["Impressions"]
          .sum()
          .reset_index()
      )
      if not impressions_by_type.empty:
        top_impression_type = impressions_by_type.sort_values(
            by="Impressions", ascending=False
        ).iloc[0]
        st.markdown(
            f"**Focus on Targeting Type:** `{top_impression_type['Targeting Type']}`"
            " for **High Impressions** (Total:"
            f" {top_impression_type['Impressions']:,})"
        )
    else:
      st.info("No 'Impressions' data available for recommendation.")

    # High Total Sales Focus
    if "Targeting Value" in filtered_df.columns:
      sales_by_value = (
          filtered_df.groupby("Targeting Value")["Total Sales"]
          .sum()
          .reset_index()
      )
      if not sales_by_value.empty:
        top_sales_value = sales_by_value.sort_values(
            by="Total Sales", ascending=False
        ).iloc[0]
        st.markdown(
            f"**Focus on Targeting Value:** `{top_sales_value['Targeting Value']}`"
            " for **High Total Sales** (Total:"
            f" ${top_sales_value['Total Sales']:,.2f})"
        )

    # High ROAS Focus
    if (
        "Campaign Name" in filtered_df.columns
        and "Estimated Budget Consumed" in filtered_df.columns
    ):
      roas_by_campaign = (
          filtered_df.groupby("Campaign Name")
          .agg({
              "Total Sales": "sum",
              "Estimated Budget Consumed": "sum",
          })
          .reset_index()
      )
      roas_by_campaign = roas_by_campaign[
          roas_by_campaign["Estimated Budget Consumed"] > 0
      ]
      roas_by_campaign["ROAS"] = (
          roas_by_campaign["Total Sales"]
          / roas_by_campaign["Estimated Budget Consumed"]
      )

      if not roas_by_campaign.empty:
        top_roas_campaign = roas_by_campaign.sort_values(
            by="ROAS", ascending=False
        ).iloc[0]
        st.markdown(
            f"**Focus on Campaign:** `{top_roas_campaign['Campaign Name']}` for"
            f" **High ROAS** ({top_roas_campaign['ROAS']:.2f}x)"
        )

        risky_campaigns = roas_by_campaign[
            (roas_by_campaign["ROAS"] < 2)
            & (roas_by_campaign["Estimated Budget Consumed"] > 1000)
        ]
        if not risky_campaigns.empty:
          st.markdown(
              "**Minimize or Review Campaigns with Low ROAS (<2) and High"
              " Spend:**"
          )
          for _, row in risky_campaigns.iterrows():
            st.markdown(
                f"- `{row['Campaign Name']}` with ROAS: {row['ROAS']:.2f}x and"
                f" Budget Spent: ${row['Estimated Budget Consumed']:,.2f}"
            )
        else:
          st.markdown(
              "No campaigns identified as risky based on current filters."
          )
  else:
    st.warning("Filtered data is empty. No insights to display.")

  # KPI Metrics
  st.write("")
  if not filtered_df.empty and "Estimated Budget Consumed" in filtered_df.columns:
    total_budget_consumed = filtered_df["Estimated Budget Consumed"].sum()
    total_sales_sum = filtered_df["Total Sales"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric(
        label="Total Estimated Budget Consumed",
        value=f"${total_budget_consumed:,.2f}",
    )
    col2.metric(label="Total Sales", value=f"${total_sales_sum:,.2f}")

    if total_budget_consumed > 0:
      roi = total_sales_sum / total_budget_consumed
      col3.metric(label="ROI (Return on Investment)", value=f"{roi:.2f}x")
    else:
      col3.warning("Budget Consumed is 0, cannot calculate ROI.")

  # Visualizations
  if not filtered_df.empty and "Date" in filtered_df.columns:
    time_df = filtered_df.groupby("Date")["Total Sales"].sum().reset_index()
    fig_area = px.area(
        time_df,
        x="Date",
        y="Total Sales",
        title="Total Sales Trend Over Time",
        template="plotly_white",
    )
    st.plotly_chart(fig_area, use_container_width=True)

  if not filtered_df.empty and "Campaign Name" in filtered_df.columns:
    campaign_df = (
        filtered_df.groupby("Campaign Name")["Total Sales"]
        .sum()
        .reset_index()
        .sort_values(by="Total Sales", ascending=False)
    )
    if not campaign_df.empty:
      fig_campaign = px.bar(
          campaign_df,
          x="Campaign Name",
          y="Total Sales",
          title="Sales by Campaign",
          labels={"Total Sales": "Total Sales Amount"},
          color="Total Sales",
      )
      st.plotly_chart(fig_campaign, use_container_width=True)

  # Data Table View
  columns_to_hide = [
      "Most Viewed Position",
      "Pacing Type",
      "Direct Quantities Sold",
      "Indirect Quantities Sold",
      "Direct ATC",
      "Indirect ATC",
  ]
  display_df = filtered_df.drop(
      columns=[col for col in columns_to_hide if col in filtered_df.columns]
  )

  st.subheader("Filtered Data Table")
  st.dataframe(display_df)