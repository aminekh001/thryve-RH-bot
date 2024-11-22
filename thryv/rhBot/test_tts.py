from bark import generate_audio

text = "Hello, this is a test of the Bark text-to-speech model."
audio = generate_audio(text)
audio.export("output.wav", format="wav")
