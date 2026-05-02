import pandas as pd
import numpy as np

def clean_and_prepare_data(file_path):
    """
    Reads a raw sales dataset, cleans it, and engineers numerical features
    so the Random Forest algorithm can process it.
    """
    
    # 1. Read the file based on its extension
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format. Please use .csv or .xlsx")

    # 2. Standardize column names (lowercase, replace spaces with underscores)
    df.columns = df.columns.str.lower().str.replace(' ', '_').str.replace('-', '_')

    # 3. Verify essential columns exist (Superstore dataset usually has order_date and sales)
    if 'order_date' not in df.columns or 'sales' not in df.columns:
        raise ValueError("Dataset must contain 'Order Date' and 'Sales' columns.")

    # 4. Convert the date column to actual Python datetime objects
    df['order_date'] = pd.to_datetime(df['order_date'], format='mixed', dayfirst=True)

    # 5. Handle missing values in Sales by filling them with 0
    df['sales'] = df['sales'].fillna(0)

    # 6. Aggregate: Group all transactions by day to get the total daily sales
    daily_sales = df.groupby('order_date')['sales'].sum().reset_index()

    # 7. FEATURE ENGINEERING: Break the date into numbers for the Random Forest
    daily_sales['year'] = daily_sales['order_date'].dt.year
    daily_sales['month'] = daily_sales['order_date'].dt.month
    daily_sales['day'] = daily_sales['order_date'].dt.day
    daily_sales['day_of_week'] = daily_sales['order_date'].dt.dayofweek

    # 8. Sort chronologically just to be safe, then drop the original text date column
    daily_sales = daily_sales.sort_values('order_date').reset_index(drop=True)
    
    # Keep the date for our charts later, but separate out the features for the model
    ml_features = daily_sales[['year', 'month', 'day', 'day_of_week']]
    ml_target = daily_sales['sales']

    return daily_sales, ml_features, ml_target