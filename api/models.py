from django.db import models
from django.contrib.auth.models import User

class StoreProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # Store Settings
    store_name = models.CharField(max_length=100, default="My Supermarket")
    location = models.CharField(max_length=100, default="Lagos, Nigeria")
    country_code = models.CharField(max_length=5, default="NG")
    region = models.CharField(max_length=20, default="tropical")
    currency = models.CharField(max_length=10, default="NGN")
    industry = models.CharField(max_length=50, default="Retail")
    
    def __str__(self):
        return f"{self.user.username} - {self.store_name}"
    
class UserProfile(models.Model):  # Fixed: removed .fields
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    store_location = models.CharField(max_length=255, blank=True, null=True)
    dark_mode_preference = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

class Dataset(models.Model):  # Fixed: removed .fields
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    dataset_name = models.CharField(max_length=255)
    file_path = models.FileField(upload_to='user_datasets/')
    row_count = models.IntegerField(null=True, blank=True)
    file_size_kb = models.FloatField(null=True, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='datasets/', null=True, blank=True)
    # YOU MUST HAVE THIS LINE FOR THE COUNT TO SAVE:
    row_count = models.IntegerField(null=True, blank=True) 
    # ... your other fields ...

    def __str__(self):
        return f"{self.dataset_name} uploaded by {self.owner.username}"

class Forecast(models.Model):  # Fixed: removed .fields
    dataset_used = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    forecast_period = models.CharField(max_length=50) 
    results_data = models.JSONField() 
    overall_trend = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Forecast for {self.dataset_used.dataset_name}"
    
class Prediction(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    period_label = models.CharField(max_length=50)
    
    # Trend Analysis
    trend_direction = models.CharField(max_length=20)
    trend_percentage = models.FloatField(null=True, blank=True)
    best_product = models.CharField(max_length=100, null=True, blank=True)
    best_category = models.CharField(max_length=100, null=True, blank=True)
    
    # Model Accuracy Metrics
    mae = models.FloatField(null=True, blank=True)
    mse = models.FloatField(null=True, blank=True)
    r2 = models.FloatField(null=True, blank=True)
    
    # Massive JSON arrays for the UI Charts
    chart_labels = models.TextField() 
    chart_data = models.TextField()
    forecast_data = models.TextField(null=True, blank=True)
    product_breakdown = models.TextField(null=True, blank=True)
    category_breakdown = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    historical_data = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Forecast for {self.dataset.name} ({self.period_label})"    
# Create your models here.
