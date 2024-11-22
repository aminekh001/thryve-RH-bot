from transformers import pipeline

# Load your model via the Hugging Face API
model_name = "suno/bark"  # replace with your model
api_token = "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"

# Create the TTS pipeline
tts = pipeline("text-to-speech", model=model_name, use_auth_token=api_token)

# Generate audio from text
audio = tts("Hello, this is a test of the Bark TTS model.")

# Save or play the audio
with open("output.wav", "wb") as f:
    f.write(audio["audio"])