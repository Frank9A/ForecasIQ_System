from rest_framework import serializers
from .models import Dataset

class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        # These are the fields we want to accept or send back to the frontend
        fields = ['id', 'owner', 'dataset_name', 'file_path', 'row_count', 'file_size_kb', 'upload_date']
        
        # 'read_only' means the frontend doesn't need to provide these when uploading; 
        # our backend will calculate and fill them in automatically later.
        read_only_fields = ['owner', 'row_count', 'file_size_kb', 'upload_date']