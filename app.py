# app.py

from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from openai import OpenAI
from datetime import datetime
import os
import numpy as np
import librosa  # Import librosa for audio analysis
import json
from python_speech_features import mfcc
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit
import tempfile  # Import tempfile for temporary file storage
from pathlib import Path  # Import Path for handling file paths

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app and SocketIO
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Enable CORS for all routes of the Flask app
socketio = SocketIO(app)  # Initialize Flask-SocketIO before using it

# Retrieve the API key from the environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

client = OpenAI(api_key=api_key)


# Function to get chatbot response using OpenAI API
def get_chatbot_response(user_input):
    personality = "You are a helpful and humorous assistant. User will directly talk with you (by microphone), and your reponse will come out by Text-To-Speech, so expect that it should be oral-like chat, not too formal or too long sentences."
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": personality},
            {"role": "user", "content": user_input}
        ]
    )
    return response.choices[0].message.content.strip()


# Function to convert text to speech using OpenAI's TTS API
def text_to_speech(text):
    try:
        # Use OpenAI TTS API to generate speech
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text
        )

        # Create a temporary file to store the audio data
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        # Save the generated speech to the specified file path
        response.stream_to_file(Path(temp_file.name))

        return temp_file.name  # Return the path to the audio file

    except Exception as e:
        print(f"Error generating speech: {e}")
        return None


# Function to analyze audio and check if it contains human voice
def analyze_audio(audio_path):
    try:
        # Load the audio file with librosa
        y, sr = librosa.load(audio_path, sr=22050)

        # Calculate the zero crossing rate (ZCR) of the audio signal
        zcr = librosa.feature.zero_crossing_rate(y)[0]

        # Calculate the mean and threshold for ZCR
        zcr_mean = np.mean(zcr)

        # If the mean ZCR is above a certain threshold, we assume human voice is present
        # (Adjust this threshold value as needed)
        if zcr_mean > 0:
            print(f"Detected human voice with ZCR mean: {zcr_mean}")
            return True
        else:
            print(f"No human voice detected. ZCR mean: {zcr_mean}")
            return False

    except Exception as e:
        print(f"Error analyzing audio: {e}")
        return False


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    """Send a greeting message when the user first connects to the chat."""
    initial_message = "Hi there! Need help or just a friendly chat?"
    
    # Convert the initial greeting to speech
    audio_path = text_to_speech(initial_message)

    if audio_path:
        with open(audio_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        # Emit the initial message and audio to the frontend
        emit('response_with_audio', {'message': initial_message, 'audio': audio_data})
    else:
        emit('response_with_audio', {'message': initial_message, 'error': 'Failed to generate initial audio.'})


@socketio.on('message')
def handle_message(msg):
    # Get chatbot response
    bot_message = get_chatbot_response(msg)

    # Convert response to speech
    audio_path = text_to_speech(bot_message)

    if audio_path:  # Check if the audio path is valid before proceeding
        with open(audio_path, 'rb') as audio_file:
            audio_data = audio_file.read()

        # Emit both the message and audio data to the frontend
        emit('response_with_audio', {'message': bot_message, 'audio': audio_data})
    else:
        emit('response_with_audio', {'message': bot_message, 'error': 'Failed to generate audio.'})


@socketio.on('speech_to_text')
def handle_speech_to_text(data):
    try:
        # Create a temporary file to save the incoming audio data
        temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_audio_file.write(data['audio'])
        temp_audio_file.close()

        # Analyze the audio to detect if it contains human voice
        contains_human_voice = analyze_audio(temp_audio_file.name)

        if contains_human_voice:
            # Call OpenAI API for transcription if human voice is detected
            with open(temp_audio_file.name, 'rb') as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            emit('stt_response', {'text': transcription.text})
        else:
            emit('stt_response', {'text': None, 'error': 'No human voice detected.'})

    except Exception as e:
        print(f"Error transcribing speech: {e}")
        emit('stt_response', {'text': None, 'error': str(e)})


if __name__ == '__main__':
    socketio.run(app, debug=True)
