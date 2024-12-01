import os
import posixpath
import json
import uuid
import environ
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from groq import Groq
from google.cloud import texttospeech
from django.contrib.auth.models import User
from django.conf import settings
from .models import Interview
from .serializers import InterviewSerializer

# Load environment variables
env = environ.Env()
environ.Env.read_env()

# Initialize TTS client
tts_client = texttospeech.TextToSpeechClient.from_service_account_json(
    'C:/Users/amine/PycharmProjects/thryv/thryv/thryve-437811-b7386ccb7409 - Copy.json'
)

# Directory for audio files
audio_directory = os.path.join(settings.MEDIA_ROOT, 'audio_files')
os.makedirs(audio_directory, exist_ok=True)  # Ensure directory exists
api_key = env("GROQ_API_KEY")

class StartInterviewAPIView(APIView):
    def post(self, request):
        """Starts an interview session."""
        api_key = env("GROQ_API_KEY")
        if not api_key:
            return Response({"error": "GROQ_API_KEY is not set."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        job_description = request.data.get("job_description", "").strip()
        user_id = request.data.get("user_id", "")

        if not job_description or not user_id:
            return Response(
                {"error": "Job description and user ID are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Generate interview questions using Groq API
            client = Groq(api_key=api_key)
            prompt = f"""
                As an experienced HR specialist, create a welcoming interview script for this {job_description} position. 
                    
                    Begin with a warm welcome greeting, then follow with conversational interview questions that naturally flow from one topic to another. Craft questions that reveal both technical capabilities and personality traits while maintaining a comfortable atmosphere.
                    
                    The questions should:
                    - Start with an ice-breaker
                    - Blend naturally without numbering or bullet points
                    - Progress from general to more specific topics
                    - Include behavioral and situational scenarios
                    - Cover required technical skills
                    - Assess cultural fit and soft skills
                    
                    Please write the questions as a flowing conversation rather than a numbered list."""
            chat_response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-70b-versatile"
            )
            raw_questions = chat_response.choices[0].message.content.split("\n")
            questions = [q.strip() for q in raw_questions if q.strip().endswith("?")]

            if not questions:
                return Response(
                    {"error": "Failed to generate valid questions."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Save interview data
            interview_id = str(uuid.uuid4())
            conversation_history = json.dumps([{"role": "assistant", "content": questions[0]}])  # Initialize as JSON string

            interview = Interview.objects.create(
                interview_id=interview_id,
                user=user,
                job_description=job_description,
                questions=questions,
                conversation_history=conversation_history,
                status="ongoing"
            )

            # TTS Integration: Convert first question to audio
            audio_filename = f"{interview_id}_first_question.mp3"
            audio_path = os.path.join(audio_directory, audio_filename)
            _generate_audio(questions[0], audio_path)

            audio_url = request.build_absolute_uri(
                posixpath.join(settings.MEDIA_URL, 'audio_files', audio_filename)
            )

            return Response({
                "interview_id": interview_id,
                "current_question": questions[0],
                "conversation_history": json.loads(conversation_history),  # Convert back to JSON for response
                "audio_url": audio_url,
                "status": "ongoing"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ContinueInterviewAPIView(APIView):
    def post(self, request):
        """Handles ongoing interview responses."""
        interview_id = request.data.get("interview_id")
        user_response = request.data.get("user_response", "").strip()


        if not interview_id or not user_response:
            return Response({"error": "Interview ID and user response are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            interview = Interview.objects.get(interview_id=interview_id)



            # Load and update conversation history
            conversation_history = json.loads(interview.conversation_history)
            conversation_history.append({"role": "user", "content": user_response})

            # Evaluate user response and generate next question
            current_index = len(conversation_history) // 2  # Alternates user/assistant pairs
            questions = interview.questions
            current_question = questions[current_index-1]
            client = Groq(api_key=api_key)
            prompt = f""" You are an HR specialist evaluating a candidate's response to an interview question. 
                        Question: {current_question} 
                        Candidate's Answer: {user_response}
                        Based on this answer, evaluate whether it is correct, and offer constructive feedback.
                        - If the answer is correct, provide positive feedback like 'Great job!' and offer to move on to the next question.
                        - If the answer is incorrect, provide a polite explanation, guide them with constructive feedback, and provide the correct answer.
                                                     
                         """
            chat_response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-70b-versatile"
            )
            print(chat_response)
            response_content = chat_response.choices[0].message.content

            # Append the feedback to the conversation history
            conversation_history.append({"role": "assistant", "content": response_content})

            # Check if interview is completed

            if current_index >= len(questions):
                interview.status = "completed"
                interview.conversation_history = json.dumps(conversation_history)
                interview.save()
                return Response({
                    "message": "Interview completed.",
                    "conversation_history": conversation_history
                }, status=status.HTTP_200_OK)

            next_question = questions[current_index]
            conversation_history.append({"role": "assistant", "content": next_question})

            # TTS Integration: Generate audio for the next question
            audio_filename = f"{interview_id}_question_{current_index}.mp3"
            audio_path = os.path.join(audio_directory, audio_filename)
            _generate_audio(next_question, audio_path)

            audio_url = request.build_absolute_uri(
                posixpath.join(settings.MEDIA_URL, 'audio_files', audio_filename)
            )

            # Save updated interview
            interview.conversation_history = json.dumps(conversation_history)
            interview.save()

            return Response({
                "current_question": next_question,
                "audio_url": audio_url,
                "conversation_history": conversation_history
            }, status=status.HTTP_200_OK)

        except Interview.DoesNotExist:
            return Response({"error": "Invalid interview ID."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Utility Functions
def _generate_audio(text, path):
    """Generate an audio file from text."""
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Wavenet-H",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

    with open(path, "wb") as audio_file:
        audio_file.write(response.audio_content)

class InterviewDetailView(APIView):
    def get(self, request, interview_id):
        try:
            interview = Interview.objects.get(interview_id=interview_id)
            serializer = InterviewSerializer(interview)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Interview.DoesNotExist:
            return Response(
                {"error": f"Interview with ID {interview_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )