import os
import io
import csv
import json
import pandas as pd
import numpy as np
import holidays
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from api.models import Dataset, Prediction, StoreProfile

# ==========================================
# 1. AUTHENTICATION & ONBOARDING VIEWS
# ==========================================

def landing_page_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    context = {
        'highlights': ['Predictive Sales Analytics', 'Hybrid ML (Prophet + RF)', 'Automated Restock Alerts', 'Nigerian Holiday Integration'],
        'workflow_steps': [
            {'title': 'Upload Data', 'description': 'Drop your supermarket CSV or Excel file into our smart analyzer.'},
            {'title': 'AI Processing', 'description': 'Our Hybrid engine calculates growth trends and seasonal patterns.'},
            {'title': 'Gain Insights', 'description': 'Download PDF reports and view AI-powered restocking advice.'}
        ]
    }
    return render(request, 'prediction/landing.html', context)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        u_name = request.POST.get('username')
        p_word = request.POST.get('password')
        user = authenticate(request, username=u_name, password=p_word)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
            return redirect('login')

    return render(request, 'prediction/auth.html', {'mode': 'login'})

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password1')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('register')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        # Create an empty profile immediately
        StoreProfile.objects.create(user=user)

        messages.success(request, "Account created! You can now sign in.")
        return redirect('login')

    return render(request, 'prediction/auth.html', {'mode': 'register'})

def logout_view(request):
    logout(request)
    return redirect('home')

# ==========================================
# 2. DASHBOARD & PROFILE VIEWS
# ==========================================

@login_required(login_url='/login/')
def dashboard_view(request):
    user_datasets = Dataset.objects.filter(owner=request.user)
    user_predictions = Prediction.objects.filter(dataset__owner=request.user).order_by('-created_at')

    total_datasets = user_datasets.count()
    total_predictions = user_predictions.count()
    last_prediction = user_predictions.first()
    
    overall_trend = last_prediction.trend_direction if last_prediction else "—"

    context = {
        'total_datasets': total_datasets,
        'total_predictions': total_predictions,
        'overall_trend': overall_trend,
        'last_prediction': last_prediction,
        'recent_predictions': user_predictions[:5],
        'datasets': user_datasets.order_by('-upload_date')[:6],
    }
    return render(request, 'prediction/dashboard.html', context)

@login_required(login_url='/login/')
def profile_view(request):
    profile, created = StoreProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form_name = request.POST.get('form_name')

        if form_name == 'account':
            request.user.first_name = request.POST.get('first_name', '')
            request.user.last_name = request.POST.get('last_name', '')
            request.user.email = request.POST.get('email', '')
            request.user.save()

            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']
                profile.save()
            messages.success(request, "Account details updated successfully!")

        elif form_name == 'password':
            current_password = request.POST.get('current_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            if not request.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
            elif new_password1 != new_password2:
                messages.error(request, "New passwords do not match.")
            elif len(new_password1) < 8:
                messages.error(request, "Password must be at least 8 characters.")
            else:
                request.user.set_password(new_password1)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password securely updated!")

        elif form_name == 'store':
            profile.store_name = request.POST.get('store_name', 'My Supermarket')
            profile.location = request.POST.get('location', 'Lagos, Nigeria')
            profile.country_code = request.POST.get('country_code', 'NG')
            profile.region = request.POST.get('region', 'tropical')
            profile.currency = request.POST.get('currency', 'NGN')
            profile.industry = request.POST.get('industry', 'Retail')
            profile.save()
            messages.success(request, "Store settings locked in!")

        return redirect('profile')

    context = {
        'profile': profile,
        'features': ["Regional Weather Patterns", "Local Public Holidays", "Currency Formatting", "Industry-specific AI Advice"],
        'steps': [
            {"title": "Set your location", "desc": "We use this to pull the correct weather data."},
            {"title": "Choose your region", "desc": "Tells the AI if you have 4 seasons or dry/rainy seasons."},
            {"title": "Run a forecast", "desc": "The ML engine will automatically inject these variables."}
        ],
        'profile_picture_url': profile.profile_picture.url if profile.profile_picture else None
    }
    return render(request, 'prediction/profile.html', context)

# ==========================================
# 3. DATASET MANAGEMENT VIEWS
# ==========================================

@login_required(login_url='/login/')
def all_datasets_view(request):
    user_datasets = Dataset.objects.filter(owner=request.user).order_by('-id')
    return render(request, 'prediction/all_datasets.html', {'datasets': user_datasets})

@login_required(login_url='/login/')
def upload_dataset_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        file = request.FILES.get('file')
        new_dataset = Dataset.objects.create(owner=request.user, name=name, file=file)
        messages.success(request, f"'{name}' uploaded successfully! Ready for forecasting.")
        return redirect('run_prediction', pk=new_dataset.pk)
        
    return render(request, 'prediction/upload.html')

@login_required(login_url='/login/')
def view_dataset_view(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk, owner=request.user)
    
    columns, preview_data = [], []
    column_mapping = {}

    try:
        if dataset.file and hasattr(dataset.file, 'path'):
            file_path = dataset.file.path
            dataset.formatted_size = f"{os.path.getsize(file_path) / (1024 * 1024):.2f} MB"
            
            df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
            columns = df.columns.tolist()
            preview_data = df.fillna("").head(10).values.tolist()
            
            row_count = len(df)
            dataset.column_count = len(columns)
            
            if row_count >= 5000:
                dataset.quality_status, dataset.quality_label = 'excellent', 'Excellent'
            elif row_count >= 1000:
                dataset.quality_status, dataset.quality_label = 'good', 'Good'
            elif row_count >= 180:
                dataset.quality_status, dataset.quality_label = 'fair', 'Fair'
            else:
                dataset.quality_status, dataset.quality_label = 'poor', 'Needs More Data'

            lower_cols = [c.lower() for c in columns]
            def find_column(keywords):
                for idx, col in enumerate(lower_cols):
                    if any(keyword in col for keyword in keywords):
                        return columns[idx]
                return "Not Found"

            column_mapping = {
                'Date': find_column(['date', 'time', 'day']),
                'Sales': find_column(['sale', 'revenue', 'amount', 'total']),
                'Product': find_column(['product', 'item', 'name', 'sku']),
                'Category': find_column(['category', 'type', 'dept']),
                'Quantity': find_column(['qty', 'quantity', 'count'])
            }

    except Exception as e:
        print(f"Could not read dataset: {e}")

    dataset.columns = columns
    dataset.preview_data = preview_data
    dataset.mapping = column_mapping

    return render(request, 'prediction/view_dataset.html', {'dataset': dataset})

@login_required(login_url='/login/')
def delete_dataset_view(request, pk):
    if request.method == 'POST':
        dataset = get_object_or_404(Dataset, pk=pk, owner=request.user)
        dataset_name = dataset.name
        dataset.delete()
        messages.success(request, f"Dataset '{dataset_name}' was successfully deleted.")
    return redirect('all_datasets')

def download_csv_template_view(request):
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="supermarket_sales_template.csv"'},
    )
    writer = csv.writer(response)
    writer.writerow(['order_date', 'product_name', 'category', 'sales_amount', 'quantity'])
    writer.writerow(['15/4/2026', 'Loaf Bread', 'Groceries', '1200.00', '2'])
    writer.writerow(['16/4/2026', 'Bottled Water', 'Beverages', '300.00', '5'])
    return response

# ==========================================
# 4. PREDICTION & ML ENGINE VIEWS
# ==========================================

@login_required(login_url='/login/')
def all_predictions_view(request):
    predictions = Prediction.objects.filter(dataset__owner=request.user).order_by('-created_at')
    return render(request, 'prediction/all_predictions.html', {'predictions': predictions})

@login_required(login_url='/login/')
def run_prediction_view(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk, owner=request.user)

    if request.method == 'POST':
        period_type = request.POST.get('period_type', 'months')
        period_value = int(request.POST.get('period_value', 3))
        days_to_predict = period_value * 30 if period_type == 'months' else period_value * 7
        period_label = f"{period_value} {period_type.capitalize()}"

        try:
            file_path = dataset.file.path
            df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
            
            # Lowercase columns for easier targeting
            df.columns = [c.lower() for c in df.columns]
            
            # ==========================================
            # 1. BULLETPROOF DATA VALIDATION
            # ==========================================
            date_col = next((c for c in df.columns if any(k in c for k in ['date', 'time', 'day'])), None)
            if not date_col:
                messages.error(request, "Data Error: No 'Date' column found. Forecasting requires a calendar date column.")
                return redirect('run_prediction', pk=dataset.pk)
            
            try:
                df[date_col] = pd.to_datetime(df[date_col])
            except Exception:
                messages.error(request, f"Data Error: Column '{date_col}' contains text/IDs (like 'DRA12') instead of calendar dates.")
                return redirect('run_prediction', pk=dataset.pk)
                
            sales_col = next((c for c in df.columns if any(k in c for k in ['sale', 'amount', 'revenue', 'total'])), None)
            if not sales_col:
                messages.error(request, "Data Error: No 'Sales' or 'Amount' column found.")
                return redirect('run_prediction', pk=dataset.pk)

            product_col = next((c for c in df.columns if any(k in c for k in ['product', 'item'])), None)
            category_col = next((c for c in df.columns if any(k in c for k in ['category', 'type'])), None)
            # ==========================================

            daily_sales = df.groupby(date_col)[sales_col].sum().reset_index().sort_values(date_col)
            
            daily_sales['time_index'] = (daily_sales[date_col] - daily_sales[date_col].min()).dt.days
            daily_sales['dayofyear'] = daily_sales[date_col].dt.dayofyear
            daily_sales['dayofweek'] = daily_sales[date_col].dt.dayofweek
            daily_sales['month'] = daily_sales[date_col].dt.month

            # Nigerian Holidays Setup
            years = daily_sales[date_col].dt.year.unique().tolist()
            years.append(years[-1] + 1)
            ng_holidays = holidays.Nigeria(years=years)

            daily_sales['is_holiday'] = daily_sales[date_col].dt.date.apply(lambda x: 1 if x in ng_holidays else 0)
            daily_sales['is_rainy_season'] = daily_sales['month'].apply(lambda m: 1 if 4 <= m <= 10 else 0)

            X_trend = daily_sales[['time_index']]
            X_season = daily_sales[['dayofyear', 'dayofweek', 'month', 'is_holiday', 'is_rainy_season']]
            y = daily_sales[sales_col]
            
            # HYBRID ML PIPELINE
            trend_model = LinearRegression()
            trend_model.fit(X_trend, y)
            historical_trend = trend_model.predict(X_trend)
            
            residuals = y - historical_trend
            
            rf_model = RandomForestRegressor(n_estimators=150, max_depth=12, random_state=42)
            rf_model.fit(X_season, residuals)
            historical_seasonality = rf_model.predict(X_season)

            raw_predictions = historical_trend + historical_seasonality
            mae = mean_absolute_error(y, raw_predictions)
            mse = mean_squared_error(y, raw_predictions)
            r2 = r2_score(y, raw_predictions)

            # FORECASTING THE FUTURE
            last_date = daily_sales[date_col].max()
            future_dates = [last_date + timedelta(days=i) for i in range(1, days_to_predict + 1)]
            future_df = pd.DataFrame({date_col: future_dates})
            
            future_df['time_index'] = (future_df[date_col] - daily_sales[date_col].min()).dt.days
            future_df['dayofyear'] = future_df[date_col].dt.dayofyear
            future_df['dayofweek'] = future_df[date_col].dt.dayofweek
            future_df['month'] = future_df[date_col].dt.month
            
            future_df['is_holiday'] = future_df[date_col].dt.date.apply(lambda x: 1 if x in ng_holidays else 0)
            future_df['is_rainy_season'] = future_df['month'].apply(lambda m: 1 if 4 <= m <= 10 else 0)
            
            future_trend = trend_model.predict(future_df[['time_index']])
            future_season = rf_model.predict(future_df[['dayofyear', 'dayofweek', 'month', 'is_holiday', 'is_rainy_season']])
            
            future_sales = np.maximum(future_trend + future_season, 0)

            # DATA FOR CHARTS
            recent_history = daily_sales.tail(60)
            recent_preds = raw_predictions[-60:]
            
            historical_table = [
                {'ds': d.strftime('%Y-%m-%d'), 'y': round(actual, 2), 'yhat': round(pred, 2)} 
                for d, actual, pred in zip(recent_history[date_col], recent_history[sales_col], recent_preds)
            ]

            past_avg = y.tail(30).mean() if len(y) >= 30 else y.mean()
            future_avg = np.mean(future_sales)
            trend_pct = ((future_avg - past_avg) / past_avg) * 100 if past_avg > 0 else 0
            trend_dir = 'growing' if trend_pct > 0 else 'declining'

            top_products = df.groupby(product_col)[sales_col].sum().nlargest(5).to_dict() if product_col else {}
            top_categories = df.groupby(category_col)[sales_col].sum().nlargest(5).to_dict() if category_col else {}
            best_product = list(top_products.keys())[0] if top_products else "N/A"
            best_category = list(top_categories.keys())[0] if top_categories else "N/A"

            forecast_table = [
                {'ds': d.strftime('%Y-%m-%d'), 'yhat': round(s, 2), 'yhat_lower': round(s * 0.92, 2), 'yhat_upper': round(s * 1.08, 2)} 
                for d, s in zip(future_dates, future_sales)
            ]

            prediction = Prediction.objects.create(
                dataset=dataset,
                period_label=period_label,
                trend_direction=trend_dir,
                trend_percentage=trend_pct,
                best_product=best_product,
                best_category=best_category,
                mae=mae,
                mse=mse,
                r2=r2,
                chart_labels=json.dumps([d.strftime('%Y-%m-%d') for d in future_dates]),
                chart_data=json.dumps(future_sales.tolist()),
                forecast_data=json.dumps(forecast_table),
                historical_data=json.dumps(historical_table),
                product_breakdown=json.dumps(top_products),
                category_breakdown=json.dumps(top_categories)
            )

            messages.success(request, f"Successfully mapped Hybrid ML forecast for {period_label}!")
            return redirect('results', pk=prediction.pk)

        except Exception as e:
            messages.error(request, f"Forecast calculation failed: {str(e)}")
            return redirect('run_prediction', pk=dataset.pk)

    context = {
        'dataset': dataset,
        'period_choices': [('weeks', 'Weeks'), ('months', 'Months')],
        'engine_layers': ['Linear Trend Analysis', 'Random Forest Residuals', 'Nigerian Holiday Detection', 'Weather Impact']
    }
    return render(request, 'prediction/run_prediction.html', context)
@login_required(login_url='/login/')
def results_view(request, pk):
    prediction = get_object_or_404(Prediction, pk=pk, dataset__owner=request.user)
    
    forecast_json = prediction.forecast_data or "[]"
    historical_json = prediction.historical_data or "[]"
    product_json = prediction.product_breakdown or "{}"
    category_json = prediction.category_breakdown or "{}"
    
    prediction.forecast_data = json.loads(prediction.forecast_data) if prediction.forecast_data else []
    prediction.product_breakdown = json.loads(prediction.product_breakdown) if prediction.product_breakdown else {}
    prediction.category_breakdown = json.loads(prediction.category_breakdown) if prediction.category_breakdown else {}

    context = {
        'prediction': prediction,
        'dataset': prediction.dataset,
        'forecast_json': forecast_json,
        'historical_json': historical_json,
        'product_json': product_json,
        'category_json': category_json,
    }
    return render(request, 'prediction/results.html', context)

@login_required(login_url='/login/')
def delete_prediction(request, pk):
    prediction = get_object_or_404(Prediction, pk=pk)
    if prediction.dataset.owner == request.user: # FIXED: user -> owner
        prediction.delete()
        messages.success(request, "Forecast deleted successfully.")
    else:
        messages.error(request, "You do not have permission to delete this.")
    return redirect('all_predictions')

# ==========================================
# 5. EXPORT & DOWNLOAD VIEWS
# ==========================================

@login_required(login_url='/login/')
def download_excel_view(request, pk):
    prediction = get_object_or_404(Prediction, pk=pk, dataset__owner=request.user)
    
    forecast_data = json.loads(prediction.forecast_data) if prediction.forecast_data else []
    historical_data = json.loads(prediction.historical_data) if prediction.historical_data else []
    product_data = json.loads(prediction.product_breakdown) if prediction.product_breakdown else {}
    category_data = json.loads(prediction.category_breakdown) if prediction.category_breakdown else {}
    
    df_forecast = pd.DataFrame(forecast_data)
    if not df_forecast.empty:
        df_forecast = df_forecast.rename(columns={'ds': 'Date', 'yhat': 'Predicted Sales', 'yhat_lower': 'Lower Bound', 'yhat_upper': 'Upper Bound'})
        
    df_history = pd.DataFrame(historical_data)
    if not df_history.empty:
        df_history = df_history.rename(columns={'ds': 'Date', 'y': 'Actual Sales', 'yhat': 'Model Fit'})

    df_products = pd.DataFrame(list(product_data.items()), columns=['Product', 'Revenue'])
    df_categories = pd.DataFrame(list(category_data.items()), columns=['Category', 'Revenue'])

    df_summary = pd.DataFrame({
        'Metric': ['Trend Direction', 'R-Squared (Accuracy)', 'Mean Absolute Error', 'Mean Squared Error'],
        'Value': [prediction.trend_direction.capitalize(), prediction.r2, prediction.mae, prediction.mse]
    })

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name='1. Executive Summary', index=False)
        df_forecast.to_excel(writer, sheet_name='2. Future Forecast', index=False)
        df_history.to_excel(writer, sheet_name='3. Historical Accuracy', index=False)
        df_products.to_excel(writer, sheet_name='4. Top Products', index=False)
        df_categories.to_excel(writer, sheet_name='5. Top Categories', index=False)
    
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="ForecastIQ_{prediction.dataset.name}_Report.xlsx"'
    return response

@login_required(login_url='/login/')
def download_pdf_view(request, pk):
    messages.success(request, "Press Ctrl+P (or Cmd+P) and select 'Save as PDF' to export this beautiful dashboard!")
    return redirect('results', pk=pk)

def dummy_download_view(request, pk):
    messages.info(request, "Export feature coming soon!")
    return redirect('results', pk=pk)