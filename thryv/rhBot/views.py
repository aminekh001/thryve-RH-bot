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
from thryv import settings
from .models import Interview

# Load environment variables
env = environ.Env()
environ.Env.read_env()

# Initialize the TTS client with your service account JSON
tts_client = texttospeech.TextToSpeechClient.from_service_account_json('C:/Users/amine/PycharmProjects/thryv/thryv/thryve-437811-b7386ccb7409 - Copy.json')

# Ensure the audio_files directory exists
audio_directory = os.path.join(settings.MEDIA_ROOT, 'audio_files')
os.makedirs(audio_directory, exist_ok=True)  # Creates the directory if it doesn't exist

# Dictionary to temporarily store ongoing interviews
ongoing_interviews = {}

class StartInterviewAPIView(APIView):
    def post(self, request):
        api_key = env("GROQ_API_KEY")
        if not api_key:
            return Response({"error": "GROQ_API_KEY is not set."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        job_description = request.data.get("job_description", "")
        user_id = request.data.get("user_id", "")
        if not job_description or not user_id:
            return Response({"error": "Job description and user ID are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Generate interview questions
            client = Groq(api_key=api_key)
            question_prompt = f"""
                you are a human resource specialist. Generate a  series of interview questions based on this job description: {job_description}.
                Include a mix of technical and soft skills questions, and make the flow conversational as if led by a human.
            """
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": question_prompt}],
                model="llama-3.1-70b-versatile"
            )
            generated_questions = chat_completion.choices[0].message.content.split("\n")
            questions = [q.strip() for q in generated_questions if q.strip() and q.strip().endswith("?")]

            if not questions:
                return Response({"error": "No questions generated from the job description."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            interview_id = str(uuid.uuid4())
            ongoing_interviews[interview_id] = {
                'user': user_id,
                'job_description': job_description,
                'questions': questions,
                'conversation_history': [{"role": "assistant", "content": questions[0]}],
                'current_question_index': 0,
                'status': "waiting_for_response"
            }

            # TTS integration: Convert the first question to audio
            synthesis_input = texttospeech.SynthesisInput(text=questions[0])
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Wavenet-H",
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
            tts_response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

            # Ensure audio directory exists
            os.makedirs(audio_directory, exist_ok=True)

            # Save audio file in MEDIA_ROOT and generate accessible URL
            audio_filename = f"{interview_id}_first_question.mp3"
            audio_path = os.path.join(audio_directory, audio_filename)
            with open(audio_path, "wb") as out:
                out.write(tts_response.audio_content)

            # Create a URL for the frontend to access the audio file
            audio_url_path = posixpath.join(settings.MEDIA_URL, 'audio_files', audio_filename)
            audio_url = request.build_absolute_uri(audio_url_path)

            response_data = {
                "interview_id": interview_id,
                "job_description": job_description,
                "current_question": questions[0],
                "current_question_index": 0,
                "conversation_history": ongoing_interviews[interview_id]['conversation_history'],
                "status": ongoing_interviews[interview_id]['status'],
                "audio_url": audio_url  # URL that the frontend can access
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ContinueInterviewAPIView(APIView):
    def post(self, request):
        api_key = env("GROQ_API_KEY")
        interview_id = request.data.get("interview_id")
        user_response = request.data.get("user_response", "")

        if not api_key:
            return Response({"error": "GROQ_API_KEY is not set."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if interview_id not in ongoing_interviews:
            return Response({"error": "Invalid or missing interview ID."}, status=status.HTTP_404_NOT_FOUND)

        interview_data = ongoing_interviews[interview_id]
        current_question_index = interview_data['current_question_index']
        questions = interview_data['questions']
        current_question = questions[current_question_index]

        try:
            client = Groq(api_key=api_key)
            evaluation_prompt = f"""
                Question: {current_question}
                Candidate's Answer: {user_response}
                Evaluate the candidate's response thoughtfully, considering both technical accuracy and their approach to explaining their answer.
                Respond in JSON format:
                {{
                    "correct": true/false,
                    "feedback": "Your feedback here",
                    "correct_answer": "Provide if incorrect, else leave empty",
                    "follow_up_question": "Next question here"
                }}
            """
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": evaluation_prompt}],
                model="llama-3.1-70b-versatile"
            )
            evaluation_result = chat_completion.choices[0].message.content

            # Clean the response by removing extra newlines or spaces
            cleaned_result = evaluation_result.strip().lstrip('`').rstrip('`').strip()

            # Try to load the cleaned result as JSON
            try:
                eval_data = json.loads(cleaned_result)
            except json.JSONDecodeError:
                return Response(
                    {
                        "error": "Failed to parse evaluation response as JSON.",
                        "raw_response": cleaned_result
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            feedback = eval_data.get('feedback', "No feedback provided.")
            interview_data['conversation_history'].append({"role": "user", "content": user_response})
            interview_data['conversation_history'].append({"role": "assistant", "content": feedback})

            current_question_index += 1
            interview_data['current_question_index'] = current_question_index

            if current_question_index >= len(questions):
                interview_data['status'] = "completed"
                response_data = {
                    "interview_id": interview_id,
                    "message": "You've completed the interview!",
                    "conversation_history": interview_data['conversation_history'],
                    "status": interview_data['status']
                }
            else:
                next_question = questions[current_question_index]
                interview_data['conversation_history'].append({"role": "assistant", "content": next_question})

                # TTS integration: Convert the next question to audio
                synthesis_input = texttospeech.SynthesisInput(text=next_question)
                voice = texttospeech.VoiceSelectionParams(
                    language_code="en-US",
                    name="en-US-Wavenet-H",
                    ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
                )
                audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
                tts_response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

                audio_filename = f"{interview_id}_question_{current_question_index}.mp3"
                audio_path = os.path.join(audio_directory, audio_filename)
                with open(audio_path, "wb") as out:
                    out.write(tts_response.audio_content)

                # Generate accessible URL for the audio file
                audio_url_path = posixpath.join(settings.MEDIA_URL, 'audio_files', audio_filename)
                audio_url = request.build_absolute_uri(audio_url_path)

                response_data = {
                    "interview_id": interview_id,
                    "current_question": next_question,
                    "current_question_index": current_question_index,
                    "conversation_history": interview_data['conversation_history'],
                    "status": interview_data['status'],
                    "feedback": feedback,
                    "audio_url": audio_url
                }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EndInterviewAPIView(APIView):
    def post(self, request):
        interview_id = request.data.get("interview_id")

        # Check if the interview ID is valid
        if interview_id not in ongoing_interviews:
            return Response({"error": "Invalid or missing interview ID."}, status=status.HTTP_404_NOT_FOUND)

        # Access the interview data
        interview_data = ongoing_interviews[interview_id]

        # Set interview status to 'completed'
        interview_data['status'] = 'completed'

        # Create or update the Interview record in the database
        try:
            interview, created = Interview.objects.update_or_create(
                interview_id=interview_id,
                defaults={
                    'user_id': interview_data['user'],  # Assuming 'user' stores user_id
                    'job_description': interview_data['job_description'],
                    'questions': interview_data['questions'],
                    'conversation_history': interview_data['conversation_history'],
                    'status': interview_data['status']
                }
            )

            # Respond to the user that the interview is complete and saved
            response_data = {
                "interview_id": interview_id,
                "user": interview.user.username,  # Assuming the user model has a 'username' field
                "message": "The interview has been successfully completed and saved to the database.",
                "status": interview.status,
                "conversation_history": interview.conversation_history,
            }

            # Optionally, delete from temporary storage if no longer needed
            ongoing_interviews.pop(interview_id, None)

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)