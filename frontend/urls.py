from django.urls import path
from . import views

urlpatterns = [
    # HOME & AUTH
    path('', views.landing_page_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # DASHBOARD
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    
    # DATA MANAGEMENT
    path('datasets/', views.all_datasets_view, name='all_datasets'),
    path('datasets/upload/', views.upload_dataset_view, name='upload_dataset'),
    path('datasets/<int:pk>/', views.view_dataset_view, name='view_dataset'),
    path('datasets/<int:pk>/delete/', views.delete_dataset_view, name='delete_dataset'),
    path('template/download/', views.download_csv_template_view, name='download_csv_template'),

    # PREDICTIONS
    path('forecasts/', views.all_predictions_view, name='all_predictions'),
    path('datasets/<int:pk>/run/', views.run_prediction_view, name='run_prediction'),
    path('forecasts/<int:pk>/results/', views.results_view, name='results'),
    path('forecasts/<int:pk>/delete/', views.delete_prediction, name='delete_prediction'),
    # EXPORTS
    path('forecasts/<int:pk>/pdf/', views.download_pdf_view, name='download_pdf'),
    path('forecasts/<int:pk>/excel/', views.download_excel_view, name='download_excel'),
    # This stops the crash by giving 'password_reset' a destination
    path('password-reset/', views.login_view, name='password_reset'),
]