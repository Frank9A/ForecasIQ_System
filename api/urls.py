from django.urls import path
from .views import DatasetUploadView
from .views import DatasetUploadView, RunForecastView

urlpatterns = [
    path('datasets/upload/', DatasetUploadView.as_view(), name='dataset-upload'),
    
    # This creates the new endpoint: /api/forecast/run/
    path('forecast/run/', RunForecastView.as_view(), name='run-forecast'),
]