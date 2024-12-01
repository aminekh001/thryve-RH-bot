from rest_framework import serializers
from .models import Interview
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model to display user-related data in InterviewSerializer.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email']  # Include only relevant fields


class InterviewSerializer(serializers.ModelSerializer):
    """
    Serializer for Interview model.
    """
    user = UserSerializer(read_only=True)  # Include nested user data in read-only mode
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='user',  # Map user_id to the 'user' foreign key field
        write_only=True  # Only allow this field during creation or update
    )

    class Meta:
        model = Interview
        fields = [
            'id', 'interview_id', 'user', 'user_id', 'job_description',
            'questions', 'conversation_history', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']  # Ensure timestamps are read-only

    def validate_status(self, value):
        """
        Custom validation for the `status` field.
        """
        allowed_statuses = ['Pending', 'In Progress', 'Completed', 'Cancelled']
        if value not in allowed_statuses:
            raise serializers.ValidationError(
                f"Invalid status: {value}. Allowed values are {', '.join(allowed_statuses)}."
            )
        return value

    def create(self, validated_data):
        """
        Custom create method if needed for additional logic.
        """
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Custom update method if needed for additional logic.
        """
        return super().update(instance, validated_data)
