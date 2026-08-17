# streamlit_app.py
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

st.set_page_config(page_title="InsightIQ Dashboard", layout="wide")

st.title("InsightIQ Dashboard")
st.markdown("Upload your sales file (CSV), click 'Preprocess', and get an interactive dashboard automatically!")

uploaded_file = st.file_uploader("Upload your file (CSV or Excel)", type=['csv', 'xlsx'])

if 'processed_df' not in st.session_state:
    st.session_state.processed_df = None

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], format="%d-%m-%Y", errors='coerce').dt.date
        df.dropna(subset=['Date'], inplace=True)

    st.subheader("Raw File Preview")
    st.dataframe(df.head())

    if st.button("Preprocess"):
        if 'Direct Sales' in df.columns and 'Indirect Sales' in df.columns:
            df['Total Sales'] = df['Direct Sales'] + df['Indirect Sales']
            st.session_state.processed_df = df
            st.success("Preprocessing Complete. 'Total Sales' column added.")
        else:
            st.error("'Direct Sales' and 'Indirect Sales' columns are missing in the uploaded file.")

if st.session_state.processed_df is not None:
    df = st.session_state.processed_df

    st.subheader("Processed Data Preview")
    st.dataframe(df.head())

    with st.sidebar:
        st.header("Filter Options")

        min_date = min(df['Date'])
        max_date = max(df['Date'])

        date_filter_option = st.selectbox(
            "Select Date Filter",
            options=["Today", "Yesterday", "Last 7 Days", "Last 30 Days", "Custom Range"]
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
            start_date, end_date = st.date_input(
                "Select Custom Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )

        campaign_names = df['Campaign Name'].dropna().unique().tolist()
        selected_campaign = st.selectbox("Select Campaign Name", options=["All"] + campaign_names, key="campaign")

        targeting_types = df['Targeting Type'].dropna().unique().tolist()
        selected_type = st.selectbox("Select Targeting Type", options=["All"] + targeting_types, key="type")

        targeting_values = df['Targeting Value'].dropna().unique().tolist()
        selected_value = st.selectbox("Select Targeting Value", options=["All"] + targeting_values, key="value")

    filtered_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

    if selected_campaign != "All":
        filtered_df = filtered_df[filtered_df['Campaign Name'] == selected_campaign]

    if selected_type != "All":
        filtered_df = filtered_df[filtered_df['Targeting Type'] == selected_type]

    if selected_value != "All":
        filtered_df = filtered_df[filtered_df['Targeting Value'] == selected_value]

    # New Insight Section
    if not filtered_df.empty:
        total_campaigns = filtered_df['Campaign Name'].nunique()
        total_budget_spend = filtered_df['Estimated Budget Consumed'].sum()
        total_sales = filtered_df['Total Sales'].sum()
        avg_sales_per_campaign = total_sales / total_campaigns if total_campaigns else 0

        roas_df = filtered_df.groupby('Campaign Name').agg({
            'Total Sales': 'sum',
            'Estimated Budget Consumed': 'sum'
        }).reset_index()
        roas_df = roas_df[roas_df['Estimated Budget Consumed'] > 0]
        roas_df['ROAS'] = roas_df['Total Sales'] / roas_df['Estimated Budget Consumed']
        avg_total_roas = roas_df['ROAS'].mean() if not roas_df.empty else 0

        st.subheader("Campaign Insights Summary")
        col4, col5, col6, col7 = st.columns(4)
        col4.metric("Total Campaigns", total_campaigns)
        col5.metric("Total Budget Spend", f"{total_budget_spend:,.2f}")
        col6.metric("Avg Sales per Campaign", f"{avg_sales_per_campaign:,.2f}")
        col7.metric("Avg ROAS Across Campaigns", f"{avg_total_roas:.2f}")

        # START: Strategic Recommendations Section
        st.subheader("Strategic Recommendations")

        # Focus on High Impressions (by Targeting Type)
        if 'Impressions' in filtered_df.columns:
            impressions_by_type = filtered_df.groupby('Targeting Type')['Impressions'].sum().reset_index()
            top_impression_type = impressions_by_type.sort_values(by='Impressions', ascending=False).iloc[0]
            st.markdown(f"**Focus on Targeting Type:** `{top_impression_type['Targeting Type']}` for **High Impressions** (Total: {top_impression_type['Impressions']:,})")
        else:
            st.info("No 'Impressions' data available for recommendation.")

        # Focus on High Total Sales (by Targeting Value)
        sales_by_value = filtered_df.groupby('Targeting Value')['Total Sales'].sum().reset_index()
        top_sales_value = sales_by_value.sort_values(by='Total Sales', ascending=False).iloc[0]
        st.markdown(f"**Focus on Targeting Value:** `{top_sales_value['Targeting Value']}` for **High Total Sales** (Total: {top_sales_value['Total Sales']:,.2f})")

        # Focus on High ROAS (by Campaign Name)
        roas_by_campaign = filtered_df.groupby('Campaign Name').agg({
            'Total Sales': 'sum',
            'Estimated Budget Consumed': 'sum'
        }).reset_index()
        roas_by_campaign = roas_by_campaign[roas_by_campaign['Estimated Budget Consumed'] > 0]
        roas_by_campaign['ROAS'] = roas_by_campaign['Total Sales'] / roas_by_campaign['Estimated Budget Consumed']

        if not roas_by_campaign.empty:
            top_roas_campaign = roas_by_campaign.sort_values(by='ROAS', ascending=False).iloc[0]
            st.markdown(f"**Focus on Campaign:** `{top_roas_campaign['Campaign Name']}` for **High ROAS** ({top_roas_campaign['ROAS']:.2f})")
        else:
            st.info("No budget consumed data available for ROAS recommendations.")

        # What to Minimize: Campaigns with ROAS < 2 and high spend
        risky_campaigns = roas_by_campaign[(roas_by_campaign['ROAS'] < 2) & (roas_by_campaign['Estimated Budget Consumed'] > 1000)]
        if not risky_campaigns.empty:
            st.markdown("**Minimize or Review Campaigns with Low ROAS (<2) and High Spend:**")
            for _, row in risky_campaigns.iterrows():
                st.markdown(f"- `{row['Campaign Name']}` with ROAS: {row['ROAS']:.2f} and Budget Spent: {row['Estimated Budget Consumed']:,.2f}")
        else:
            st.markdown("No campaigns identified as risky based on current filters.")

        # What to Minimize: Targeting Types with ROAS < 2  and high spend
        risky_targeting = filtered_df.groupby('Targeting Type').agg({
            'Total Sales': 'sum',
            'Estimated Budget Consumed': 'sum'
        }).reset_index()
        risky_targeting['ROAS'] = risky_targeting.apply(
            lambda x: x['Total Sales'] / x['Estimated Budget Consumed'] if x['Estimated Budget Consumed'] > 0 else 0,
            axis=1
        )
        risky_targeting = risky_targeting[(risky_targeting['ROAS'] < 2) & (risky_targeting['Estimated Budget Consumed'] > 1000)]
        if not risky_targeting.empty:
            st.markdown("**Minimize Targeting Types with Low ROAS (<2) and High Spend:**")
            for _, row in risky_targeting.iterrows():
                st.markdown(f"- `{row['Targeting Type']}` with ROAS: {row['ROAS']:.2f} and Budget Spent: {row['Estimated Budget Consumed']:,.2f}")
        else:
            st.markdown("No targeting types identified as risky based on current filters.")
        # END: Strategic Recommendations Section 

    else:
        st.warning("Filtered data is empty. No insights to display.")

    # KPI Metrics
    st.write("")
    if not filtered_df.empty:
        total_budget_consumed = filtered_df['Estimated Budget Consumed'].sum()
        total_sales_sum = filtered_df['Total Sales'].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric(label="Total Estimated Budget Consumed", value=f"{total_budget_consumed:,.2f}")
        col2.metric(label="Total Sales", value=f"{total_sales_sum:,.2f}")

        if total_budget_consumed > 0:
            roi = total_sales_sum / total_budget_consumed
            col3.metric(label="ROI (Return on Investment)", value=f"{roi:.2f}")
        else:
            col3.warning("Budget Consumed is 0, cannot calculate ROI.")
    else:
        st.warning("Filtered data is empty or missing required columns for ROI calculation.")

    # Total Sales Over Time
    time_df = df.groupby('Date')['Total Sales'].sum().reset_index()
    fig_area = px.area(time_df, x='Date', y='Total Sales', title='Total Sales Trend Over Time', template='plotly_white')
    st.plotly_chart(fig_area, use_container_width=True)

    # Sales by Campaign Name
    campaign_df = filtered_df.groupby('Campaign Name')['Total Sales'].sum().reset_index().sort_values(by='Total Sales', ascending=False)
    if not campaign_df.empty:
        fig_campaign = px.bar(campaign_df, x='Campaign Name', y='Total Sales',
                            title='Sales by Campaign',
                            labels={'Total Sales': 'Total Sales Amount'},
                            color='Total Sales')
        st.plotly_chart(fig_campaign, use_container_width=True)
    else:
        st.info("No campaign data available for the selected filters.")

    # Estimated Budget Consumed by Campaign
    if not filtered_df.empty:
        budget_campaign_df = filtered_df.groupby('Campaign Name').agg({
            'Estimated Budget Consumed': 'sum'
        }).reset_index()
        budget_campaign_df = budget_campaign_df.sort_values(by='Estimated Budget Consumed', ascending=False)

        fig_budget = px.bar(budget_campaign_df,
                            x='Campaign Name',
                            y='Estimated Budget Consumed',
                            title='Estimated Budget Consumed per Campaign',
                            color='Estimated Budget Consumed',
                            labels={'Estimated Budget Consumed': 'Estimated Budget Consumed'},
                            color_continuous_scale='Blues')
        st.plotly_chart(fig_budget, use_container_width=True)

    # ROI by Targeting Type
    roi_df = filtered_df.groupby('Targeting Type').agg({
        'Estimated Budget Consumed': 'sum',
        'Total Sales': 'sum'
    }).reset_index()
    roi_df = roi_df[roi_df['Estimated Budget Consumed'] > 0]
    if not roi_df.empty:
        roi_df['ROI'] = roi_df['Total Sales'] / roi_df['Estimated Budget Consumed']
        fig_roi = px.bar(roi_df, x='Targeting Type', y='ROI',
                        title='ROI by Targeting Type',
                        color='ROI')
        st.plotly_chart(fig_roi, use_container_width=True)
    else:
        st.info("ROI data not available for the selected filters.")
        
    # Sales by Targeting Type Pie Chart
    sales_by_targeting = filtered_df.groupby('Targeting Type')['Total Sales'].sum().reset_index()
    if not sales_by_targeting.empty:
        fig_pie_targeting = px.pie(
            sales_by_targeting,
            names='Targeting Type',
            values='Total Sales',
            title='Sales Share by Targeting Type',
            template='plotly_white'
        )
        st.plotly_chart(fig_pie_targeting, use_container_width=True)
    else:
        st.info("No data available to show Sales by Targeting Type pie chart.")

    # Hide unwanted columns
    columns_to_hide = [
        'Most Viewed Position',
        'Pacing Type',
        'Direct Quantities Sold',
        'Indirect Quantities Sold',
        'Direct ATC',
        'Indirect ATC'
    ]
    display_df = filtered_df.drop(columns=[col for col in columns_to_hide if col in filtered_df.columns])

    st.subheader("Filtered Data Table")
    st.dataframe(display_df)

    # Sales by Budget Range Table with Selected Columns
    if not filtered_df.empty:
        filtered_df_copy = filtered_df.copy()

        # Assign Budget Range based on Targeting Type
        def classify_budget(row):
            if row['Targeting Type'] == 'Category':
                if row['Estimated Budget Consumed'] > 15000:
                    return 'High'
                elif row['Estimated Budget Consumed'] >= 8000:
                    return 'Medium'
                else:
                    return 'Low'
            elif row['Targeting Type'] == 'Keyword':
                if row['Estimated Budget Consumed'] > 10000:
                    return 'High'
                elif row['Estimated Budget Consumed'] >= 5000:
                    return 'Medium'
                else:
                    return 'Low'
            else:
                return 'Other'

        filtered_df_copy['Budget Range'] = filtered_df_copy.apply(classify_budget, axis=1)

        # Compute Total ROAS per row 
        filtered_df_copy['Total ROAS'] = filtered_df_copy.apply(
            lambda row: row['Total Sales'] / row['Estimated Budget Consumed']
            if row['Estimated Budget Consumed'] > 0 else 0,
            axis=1
        )

        # Select and display the necessary columns
        display_budget_df = filtered_df_copy[[
            'Date', 'Budget Range', 'Campaign Name',
            'Targeting Type', 'Targeting Value',
            'Total ROAS', 'Total Sales'
        ]]

        st.subheader("Sales by Budget Range Table")
        st.dataframe(display_budget_df.sort_values(by='Budget Range'))

        # Aggregate sales by Budget Range for plotting
        sales_by_budget_df = display_budget_df.groupby('Budget Range')['Total Sales'].sum().reset_index()

        # Plot Sales by Budget Range Bar Chart
        if not sales_by_budget_df.empty:
            fig_sales_budget = px.bar(
                sales_by_budget_df,
                x='Budget Range',
                y='Total Sales',
                title='Total Sales by Budget Range',
                color='Budget Range',
                labels={'Total Sales': 'Total Sales Amount', 'Budget Range': 'Budget Range'},
                template='plotly_white'
            )
            st.plotly_chart(fig_sales_budget, use_container_width=True)
    else:
        st.info("No data available for Sales by Budget Range table.")

    # Top 5 Campaigns by Total Sales
    if not filtered_df.empty:
        top_campaigns_df = (
            filtered_df.groupby('Campaign Name')['Total Sales']
            .sum()
            .reset_index()
            .sort_values(by='Total Sales', ascending=False)
            .head(5)
        )

        st.subheader("Top 5 Campaigns by Total Sales")
        st.dataframe(top_campaigns_df)
    else:
        st.info("No data available to show Top 5 Campaigns.")

    # Top 5 Campaigns by ROAS
    if not filtered_df.empty:
        roas_campaign_df = (
            filtered_df.groupby('Campaign Name').agg({
                'Total Sales': 'sum',
                'Estimated Budget Consumed': 'sum'
            }).reset_index()
        )
        roas_campaign_df = roas_campaign_df[roas_campaign_df['Estimated Budget Consumed'] > 0]
        roas_campaign_df['ROAS'] = roas_campaign_df['Total Sales'] / roas_campaign_df['Estimated Budget Consumed']

        top_roas_campaigns = roas_campaign_df.sort_values(by='ROAS', ascending=False).head(5)

        st.subheader("Top 5 Campaigns by ROAS")
        st.dataframe(top_roas_campaigns[['Campaign Name', 'ROAS']])
    else:
        st.info("No data available to show Top 5 Campaigns by ROAS.")
        
    # Campaigns with ROAS less than 2
    if not filtered_df.empty:
        roas_campaign_df = (
        filtered_df.groupby('Campaign Name').agg({
            'Total Sales': 'sum',
            'Estimated Budget Consumed': 'sum'
        }).reset_index()
    )
        roas_campaign_df = roas_campaign_df[roas_campaign_df['Estimated Budget Consumed'] > 0]
        roas_campaign_df['ROAS'] = roas_campaign_df['Total Sales'] / roas_campaign_df['Estimated Budget Consumed']

        low_roas_campaigns = roas_campaign_df[roas_campaign_df['ROAS'] < 2].sort_values(by='ROAS')

        if not low_roas_campaigns.empty:
            st.subheader("Campaigns with ROAS less than 2")
            st.dataframe(low_roas_campaigns[['Campaign Name', 'ROAS', 'Estimated Budget Consumed']])
        else:
            st.info("No campaigns with ROAS less than 2 found.")
    else:
        st.info("No data available to evaluate ROAS.")

        

        



