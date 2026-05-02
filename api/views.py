import pandas as pd
import os
from rest_framework import generics
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .serializers import DatasetSerializer
from rest_framework.views import APIView
from .models import Dataset, Forecast
from ml_engine.data_preparation import clean_and_prepare_data
from ml_engine.random_forest_model import train_and_forecast

class DatasetUploadView(generics.GenericAPIView):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = DatasetSerializer

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file_path')
        
        if not file_obj:
            return Response({"error": "No file was attached to the request."}, status=status.HTTP_400_BAD_REQUEST)
            
        # 1. FILE TYPE VALIDATION (The Bouncer)
        if not (file_obj.name.endswith('.csv') or file_obj.name.endswith('.xlsx')):
            return Response(
                {"error": "Invalid file format. The RELTrack system only accepts .csv or .xlsx files."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DatasetSerializer(data=request.data)
        
        if serializer.is_valid():
            admin_user = User.objects.first() 
            
            # 2. Save the file so it physically exists in your media folder
            dataset_instance = serializer.save(owner=admin_user)
            
            # 3. DATA PREPARATION: Calculate size and read the data
            try:
                # Get file size in Kilobytes (KB) and round to 2 decimal places
                file_size_kb = os.path.getsize(dataset_instance.file_path.path) / 1024
                
                # Ask pandas to open the file based on its extension
                if file_obj.name.endswith('.csv'):
                    df = pd.read_csv(dataset_instance.file_path.path)
                elif file_obj.name.endswith('.xlsx'):
                    df = pd.read_excel(dataset_instance.file_path.path)
                    
                # Count how many rows of data there are
                row_count = len(df)
                
                # Update our database record with the new numbers
                dataset_instance.row_count = row_count
                dataset_instance.file_size_kb = round(file_size_kb, 2)
                dataset_instance.save()
                
                # Refresh our translator so it sends the new numbers back to the screen
                updated_serializer = DatasetSerializer(dataset_instance)
                
                return Response(
                    {"message": "File uploaded and processed successfully!", "data": updated_serializer.data}, 
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as e:
                # SAFETY NET: If pandas crashes (e.g., someone renames an image to .csv)
                dataset_instance.delete() # Delete the broken file from the system
                return Response(
                    {"error": f"Failed to read the data file. It might be corrupted. Details: {str(e)}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class RunForecastView(APIView):
    def post(self, request, *args, **kwargs):
        # 1. Grab the ID of the dataset the user wants to predict from
        dataset_id = request.data.get('dataset_id')
        
        # Default to 30 days if the user doesn't specify
        forecast_days = int(request.data.get('forecast_days', 30)) 

        if not dataset_id:
            return Response({"error": "Please provide a dataset_id."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 2. Fetch the actual file from the database
            dataset = Dataset.objects.get(id=dataset_id)

            # 3. CLEANING STATION: Run the pandas script to engineer the features
            df_clean, ml_features, ml_target = clean_and_prepare_data(dataset.file_path.path)

            # 4. PREDICTION STATION: Run the Random Forest algorithm
            future_df, trend = train_and_forecast(df_clean, ml_features, ml_target, forecast_days)

            # 5. FORMATTING: Convert the dates to text so they can be saved as JSON
            future_df['order_date'] = future_df['order_date'].dt.strftime('%Y-%m-%d')
            
            # Pack the results into a clean dictionary
            results_json = future_df[['order_date', 'predicted_sales', 'upper_bound', 'lower_bound']].to_dict(orient='records')

            # 6. SAVE TO DATABASE: Store the results in the Forecast table
            forecast = Forecast.objects.create(
                dataset_used=dataset,
                forecast_period=f"{forecast_days} days",
                results_data=results_json,
                overall_trend=trend
            )

            # 7. Send a success message back to the frontend with a sneak peek of the data!
            return Response({
                "message": "Forecast generated successfully!",
                "forecast_id": forecast.id,
                "overall_trend": trend,
                "preview_data": results_json[:5] # Show the first 5 days of predictions
            }, status=status.HTTP_201_CREATED)

        except Dataset.DoesNotExist:
            return Response({"error": "Dataset not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Forecast failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)