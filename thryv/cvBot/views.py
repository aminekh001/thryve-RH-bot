import unicodedata
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.contrib.auth.models import User
from .models import Resume
from .serializers import ResumeSerializer
import fitz  # PyMuPDF for text extraction
import json
import os
from groq import Groq
import re
import logging

# Configure logging
logger = logging.getLogger(__name__)


class ResumeUploadView(APIView):
    """API View to handle resume upload and evaluation."""

    def extract_text_from_pdf(self, file):
        """
        Extract text from a PDF file using PyMuPDF.

        Args:
            file (InMemoryUploadedFile): The uploaded PDF file.

        Returns:
            str: Extracted text from the PDF.
        """
        try:
            # Open the PDF file and extract text from all pages
            pdf_document = fitz.open(stream=file.read(), filetype="pdf")
            text = ""
            for page in pdf_document:
                text += page.get_text()
            pdf_document.close()
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise ValueError(f"Error extracting text from PDF: {str(e)}")

    def sanitize_text(self, text):
        """
        Sanitize the text by removing unwanted characters and normalizing.

        Args:
            text (str): The text to sanitize.

        Returns:
            str: Sanitized text.
        """
        try:
            # Ensure input is a string
            text = str(text)

            # Remove control characters (non-printable, special characters)
            sanitized_text = re.sub(r'[\x00-\x1F\x7F]', ' ', text)

            # Normalize accented characters to ASCII
            sanitized_text = unicodedata.normalize('NFKD', sanitized_text).encode('ASCII', 'ignore').decode('ASCII')

            # Replace multiple spaces with a single space
            sanitized_text = re.sub(r'\s+', ' ', sanitized_text)

            # Replace non-breaking spaces with regular spaces
            sanitized_text = sanitized_text.replace('\u00A0', ' ')

            # Remove any non-ASCII characters (characters outside 0-127)
            sanitized_text = re.sub(r'[^\x20-\x7E]', ' ', sanitized_text)

            # Strip leading and trailing spaces
            sanitized_text = sanitized_text.strip()

            return sanitized_text
        except Exception as e:
            logger.error(f"Error sanitizing text: {str(e)}")
            raise ValueError(f"Error sanitizing text: {str(e)}")

    def evaluate_resume(self, text, job_description):
        """
        Evaluate the resume using the Groq API.

        Args:
            text (str): Extracted resume text.
            job_description (str): Job description for evaluation.

        Returns:
            tuple: ATS score, best practices score, and suggestions.
        """
        try:
            # Sanitize inputs: resume text and job description
            sanitized_text = self.sanitize_text(text)
            sanitized_job_description = self.sanitize_text(job_description)

            # Ensure the API key is set for Groq
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise EnvironmentError("GROQ_API_KEY is not set in the environment.")

            # Create the Groq client with the API key
            client = Groq(api_key=api_key)

            # Construct the LLM prompt for resume evaluation
            prompt = f"""
            You are an expert in evaluating resumes for Applicant Tracking Systems (ATS) and HR best practices. Your task is to assess the following resume against the job description provided.

            Strictly respond with a valid JSON object and do not include any additional text or explanation.

            For the evaluation, provide:
            1. An ATS compatibility score (a precise numeric value between 0 and 100).
            2. A best practices score (a precise numeric value between 0 and 100).
            3. Concise and actionable improvement suggestions for enhancing the resume's alignment with ATS and HR best practices.
            4. The improvement suggestions should be written in the same language as the resume text.

            The response should be in this exact format:

            {{
                "ats_score": <numeric_score>,
                "best_practices_score": <numeric_score>,
                "suggestions": "<actionable_suggestions>"
            }}

            Important instructions:
            - The suggestions should be tailored to improve the resume for ATS systems (e.g., by including relevant keywords) and to meet HR best practices (e.g., formatting, clarity).
            - Ensure the language of the suggestions matches the language of the resume text. Do not switch languages.
            - Focus on providing clear, specific, and actionable suggestions to improve the resume.

            Resume Text:
            {sanitized_text}

            Job Description:
            {sanitized_job_description}
            """

            # Send the prompt to the Groq API and get the response
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-70b-versatile",
                response_format={"type": "json_object"}
            )

            # Extract and parse the response
            chat_response_content = response.choices[0].message.content

            # Robust JSON parsing with multiple fallback strategies
            try:
                # First attempt: standard parsing
                parsed_response = json.loads(chat_response_content)
            except json.JSONDecodeError:
                try:
                    # Second attempt: remove control characters and whitespace
                    cleaned_response = re.sub(r'[\x00-\x1F\x7F]', '', chat_response_content).strip()
                    parsed_response = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    # Last resort: manual extraction
                    default_response = {
                        "ats_score": 50.0,
                        "best_practices_score": 50.0,
                        "suggestions": "Unable to fully evaluate resume. Please review manually."
                    }
                    logger.warning(f"Failed to parse Groq response: {chat_response_content}")
                    parsed_response = default_response

            # Extract and validate scores
            ats_score = min(max(parsed_response.get("ats_score", 0), 0), 100)
            best_practices_score = min(max(parsed_response.get("best_practices_score", 0), 0), 100)
            suggestions = parsed_response.get("suggestions", "No specific suggestions available.")

            return ats_score, best_practices_score, suggestions

        except Exception as e:
            logger.error(f"Error evaluating resume with Groq API: {str(e)}")
            raise ValueError(f"Error evaluating resume with Groq API: {str(e)}")

    def post(self, request, *args, **kwargs):
        """
        Handle POST request for resume upload and evaluation.

        Returns:
            Response: Serialized resume data or error message.
        """
        try:
            # Parse incoming JSON data
            user_id = request.data.get('user_id')
            job_description = request.data.get('job_description')
            name = request.data.get('name')
            file = request.FILES.get('file')

            # Validate required fields: user_id, job_description, and file
            if not user_id or not job_description or not file:
                return Response(
                    {'error': 'user_id, job_description, and file are required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate the provided user ID
            user = User.objects.filter(id=user_id).first()
            if not user:
                return Response(
                    {'error': 'Invalid user_id provided.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Extract text from the uploaded PDF
            extracted_text = self.extract_text_from_pdf(file)

            # Evaluate the resume using the Groq API
            ats_score, best_practices_score, suggestions = self.evaluate_resume(
                extracted_text, job_description
            )

            # Save the resume in the database
            resume = Resume.objects.create(
                user=user,
                name=name,
                file=file,
                extracted_text=extracted_text,
                ats_score=ats_score,
                best_practices_score=best_practices_score,
                suggestions=suggestions,
                job_description=job_description,
            )

            # Serialize and return the response
            serializer = ResumeSerializer(resume)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Log the error for debugging
            logger.error(f"Unexpected error in resume upload: {str(e)}")

            # Handle unexpected errors and return a 500 internal server error
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )