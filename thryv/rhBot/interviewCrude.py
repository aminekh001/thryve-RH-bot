from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Interview
from .serializers import InterviewSerializer
from django.contrib.auth.models import User

class InterviewByUserAPIView(APIView):
    def get(self, request, user_id):
        """
        Retrieve interviews for a specific user ID.
        """
        try:
            user = User.objects.get(id=user_id)  # Fetch the user by ID
            interviews = Interview.objects.filter(user=user)  # Filter interviews by user
            serializer = InterviewSerializer(interviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)




    def delete(self, request, interview_id):
        """
        Delete an interview by its ID.
        """
        try:
            interview = Interview.objects.get(id=interview_id)
            interview.delete()
            return Response({"message": "Interview deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Interview.DoesNotExist:
            return Response({"error": "Interview not found"}, status=status.HTTP_404_NOT_FOUND)
