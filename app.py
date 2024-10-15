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
    # Comprehensive system message in Japanese
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

    # Chat completion request
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_input}
        ]
    )
    return response.choices[0].message.content.strip()

# Function to convert text to speech using OpenAI TTS
def text_to_speech_openai(text):
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        response.stream_to_file(temp_file.name)
        return temp_file.name
    except Exception as e:
        print(f"Error generating speech with OpenAI: {e}")
        return None

# Function to convert text to speech using Amazon Polly
def text_to_speech_polly(text):
    try:
        response = polly_client.synthesize_speech(
            Text=text,
            VoiceId="Mizuki",  # Use the 'Mizuki' voice for Japanese
            OutputFormat="mp3"
        )
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        with open(temp_file.name, "wb") as audio_file:
            audio_file.write(response['AudioStream'].read())
        return temp_file.name
    except Exception as e:
        print(f"Error generating speech with Polly: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

# @app.route('/openai')
# def openai_tts_page():
#     return render_template('openai.html')

@app.route('/polly')
def polly_tts_page():
    return render_template('polly.html')

@socketio.on('message')
def handle_message(msg):
    # Get chatbot response
    bot_message = get_chatbot_response(msg)

    # Convert response to speech
    audio_path = text_to_speech_openai(bot_message)

    if audio_path:  # Check if the audio path is valid before proceeding
        with open(audio_path, 'rb') as audio_file:
            audio_data = audio_file.read()

        # Emit both the message and audio data to the frontend
        emit('response_with_audio', {'message': bot_message, 'audio': audio_data})
    else:
        emit('response_with_audio', {'message': bot_message, 'error': 'Failed to generate audio.'})

# # Handle OpenAI TTS
# @socketio.on('message_openai')
# def handle_message_openai(msg):
#     bot_message = get_chatbot_response(msg)
#     audio_path = text_to_speech_openai(bot_message)
#     if audio_path:
#         with open(audio_path, 'rb') as audio_file:
#             audio_data = audio_file.read()
#         emit('response_with_audio', {'message': bot_message, 'audio': audio_data})
#     else:
#         emit('response_with_audio', {'message': bot_message, 'error': 'Failed to generate audio.'})

# Handle Amazon Polly TTS
@socketio.on('message_polly')
def handle_message_polly(msg):
    bot_message = get_chatbot_response(msg)
    audio_path = text_to_speech_polly(bot_message)
    if audio_path:
        with open(audio_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        emit('response_with_audio', {'message': bot_message, 'audio': audio_data})
    else:
        emit('response_with_audio', {'message': bot_message, 'error': 'Failed to generate audio.'})

if __name__ == '__main__':
    socketio.run(app, debug=True)
