import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from datetime import timedelta

def train_and_forecast(df_clean, ml_features, ml_target, forecast_days=30):
    """
    Trains the Random Forest model on historical data and predicts future sales.
    """
    
    # 1. THE BRAIN: Initialize the Random Forest
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    
    # 2. LEARN: Train the model on the historical data
    model.fit(ml_features, ml_target)
    
    # 3. TIME TRAVEL: Figure out the last day in our dataset, then create dates for the future
    last_date = df_clean['order_date'].max()
    future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
    
    # 4. PREPARE THE FUTURE: Break the future dates into numbers just like we did the past
    future_df = pd.DataFrame({'order_date': future_dates})
    future_df['year'] = future_df['order_date'].dt.year
    future_df['month'] = future_df['order_date'].dt.month
    future_df['day'] = future_df['order_date'].dt.day
    future_df['day_of_week'] = future_df['order_date'].dt.dayofweek
    
    future_features = future_df[['year', 'month', 'day', 'day_of_week']]
    
    # 5. PREDICT: Ask the trained algorithm to forecast sales for those future dates
    predictions = model.predict(future_features)
    
    future_df['predicted_sales'] = predictions
    
    # 6. CONFIDENCE BOUNDS: Create an upper and lower margin (10%) for the UI charts
    margin_of_error = predictions * 0.10
    future_df['upper_bound'] = predictions + margin_of_error
    future_df['lower_bound'] = predictions - margin_of_error
    
    # 7. OVERALL TREND: Check if the last day is higher than the first day
    if predictions[-1] > predictions[0]:
        trend = "Upward"
    else:
        trend = "Downward"
        
    return future_df, trend