# backup_app.py

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
import webrtcvad
import boto3  # Import boto3 for Amazon Polly

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app and SocketIO
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Enable CORS for all routes of the Flask app
socketio = SocketIO(app)  # Initialize Flask-SocketIO before using it
# AWS Polly setup
polly_client = boto3.client('polly', region_name=os.getenv("AWS_REGION"))

# Retrieve the API key from the environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

client = OpenAI(api_key=api_key)

def get_chatbot_response(user_input):
    # Comprehensive system message in Japanese with essential details, ensuring all important parts are included
    system_content = """
    あなたは、TOKYO BEASTプロジェクトに関する知識豊富なアシスタントです。このプロジェクトは、2024年にリリース予定のWeb3エンターテインメントで、2124年の未来の東京を舞台にしています。回答は実際のアシスタントのように、短い文で分かりやすく伝えてください。長すぎないようにしましょう。

    主な概要:
    - **TOKYO BEAST**は、サイバーパンク風の未来の東京を舞台にしたゲームです。
    - 2023年9月発表、2024年リリース予定。**gumi**が開発し、**Turingum**が技術・財務アドバイザリーを担当。
    - ゲーム内では、プレイヤーは**BEAST NFT**と**$TBZトークン**を使って相互作用します。

    ゲームの特徴と機能:
    - **$TBZトークン**: ゲーム内通貨で、**BASE**モジュールでの投資に使用。
    - **BEAST NFT**: プレイヤーが所有、育成、訓練するデジタルアセット。**FARM**モジュールで育成可能。
    - **TRIALS**: BEASTのコピーを使用してアリーナでバトルし、トッププレイヤーはチャンピオンシップへ進出。
    - **BETTING**: 暗号資産を使ったベッティング機能。チャンピオンシップの勝敗予想が可能。

    コミュニティと法的対応:
    - 暗号通貨を使ったギャンブル機能があり、法的レビューを受けて開発中。
    - 世界配信される試合とグローバルなベッティングが予定されています。

    拡張モジュール:
    - **CLASH**: 日々のベッティング機会。
    - **FUSION**: 人気NFTやゲームとのコラボレーション。
    - **ITEMIZE**: フィジカルグッズやアパレル販売。
    - **ANIMATION**: ゲームの世界観を拡張するアニメーション展開。

    早期参加キャンペーン:
    - 2023年10月31日まで**Early Entry Campaign**が実施され、NFTや$TBZトークンが報酬として提供される可能性があります。
    """

    # Create a completion request with system context and user input
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_content},  # System message with full content in Japanese
            {"role": "user", "content": user_input}  # User's input or question
        ]
    )
    return response.choices[0].message.content.strip()

# # Function to convert text to speech using OpenAI's TTS API
# def text_to_speech(text):
#     try:
#         # Use OpenAI TTS API to generate speech
#         response = client.audio.speech.create(
#             model="tts-1",
#             voice="alloy",
#             input=text
#         )

#         # Create a temporary file to store the audio data
#         temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
#         # Save the generated speech to the specified file path
#         response.stream_to_file(Path(temp_file.name))

#         return temp_file.name  # Return the path to the audio file

#     except Exception as e:
#         print(f"Error generating speech: {e}")
#         return None

# Function to convert text to speech using Amazon Polly
def text_to_speech(text):
    try:
        # Request speech synthesis from Amazon Polly
        response = polly_client.synthesize_speech(
            Text=text,
            VoiceId="Mizuki",  # Use the 'Mizuki' voice for Japanese, you can change this if needed
            OutputFormat="mp3"
        )

        # Create a temporary file to store the audio data
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        with open(temp_file.name, "wb") as audio_file:
            audio_file.write(response['AudioStream'].read())

        return temp_file.name  # Return the path to the temporary audio file

    except Exception as e:
        print(f"Error generating speech with Polly: {e}")
        return None

def analyze_audio(audio_path, aggressiveness=0, voiced_threshold=0.3):
    """
    Analyze audio using WebRTC VAD to determine if it contains human voice.

    Args:
        audio_path (str): Path to the audio file to be analyzed.
        aggressiveness (int): Aggressiveness level of VAD (0-3). Lower values are less aggressive.
        voiced_threshold (float): Proportion of voiced chunks required to consider human voice.

    Returns:
        bool: True if human voice is detected, otherwise False.
    """
    try:
        # Initialize the VAD object with the specified aggressiveness level
        vad = webrtcvad.Vad(aggressiveness)  # 0: Least aggressive, 3: Most aggressive

        # Load audio using librosa, ensuring it's at 16kHz (recommended sample rate for VAD)
        y, sr = librosa.load(audio_path, sr=16000)

        # Check if the loaded audio has any content
        if len(y) == 0:
            print("Error: Loaded audio has no content.")
            return False

        # Convert the audio signal to 16-bit PCM format as required by VAD
        # Normalize the float samples to -32768 to 32767 (int16 range)
        samples = (y * 32768).astype(np.int16).tobytes()

        # Define parameters for chunking the audio
        sample_width = 2  # Each sample is 2 bytes (16-bit)
        frame_duration = 30  # Frame duration of 30ms
        frame_size = int(sr * (frame_duration / 1000.0))  # Calculate number of samples per frame

        # Split the audio into 30ms frames (webrtcvad accepts 10ms, 20ms, or 30ms frames)
        frames = [samples[i:i + frame_size * sample_width] for i in range(0, len(samples), frame_size * sample_width)]

        # Check if any frames were created
        if len(frames) == 0:
            print("Error: No frames created for analysis.")
            return False

        # Filter out invalid frames (frames must have consistent length for webrtcvad)
        valid_frames = [frame for frame in frames if len(frame) == frame_size * sample_width]

        # Check if there are any valid frames to process
        if len(valid_frames) == 0:
            print("Error: No valid frames found for analysis.")
            return False

        # Count the number of voiced frames using webrtcvad
        num_voiced_frames = sum([1 for frame in valid_frames if vad.is_speech(frame, sr)])

        # Avoid division by zero by checking if the total number of valid frames is zero
        if len(valid_frames) == 0:
            print("Error: Division by zero - no valid frames for VAD processing.")
            return False

        # Calculate the proportion of voiced frames
        voiced_proportion = num_voiced_frames / len(valid_frames)

        # Consider it human voice if the proportion of voiced frames is greater than the threshold
        if voiced_proportion > voiced_threshold:
            print(f"Detected human voice. Voiced proportion: {voiced_proportion:.2f}")
            return True
        else:
            print(f"No human voice detected. Voiced proportion: {voiced_proportion:.2f}")
            return False

    except Exception as e:
        print(f"Error analyzing audio with VAD: {e}")
        return False



@app.route('/')
def index():
    return render_template('index.html')


# @socketio.on('connect')
# def handle_connect():
#     """Send a greeting message when the user first connects to the chat."""
#     initial_message = "Hi there! Need help or just a friendly chat?"
    
#     # Convert the initial greeting to speech
#     audio_path = text_to_speech(initial_message)

#     if audio_path:
#         with open(audio_path, 'rb') as audio_file:
#             audio_data = audio_file.read()
#         # Emit the initial message and audio to the frontend
#         emit('response_with_audio', {'message': initial_message, 'audio': audio_data})
#     else:
#         emit('response_with_audio', {'message': initial_message, 'error': 'Failed to generate initial audio.'})


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
