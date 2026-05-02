from django.contrib import admin
from .models import UserProfile, Dataset, Forecast

# This tells the Admin panel to display these tables
admin.site.register(UserProfile)
admin.site.register(Dataset)
admin.site.register(Forecast)