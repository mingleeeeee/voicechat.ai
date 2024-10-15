# Chatbot Application with TTS (Text-to-Speech) and Voice Interaction

This project is a **Flask** web application that allows users to communicate with a chatbot via text or voice input. It supports two options for generating Text-to-Speech (TTS) responses: **OpenAI TTS** and **Amazon Polly TTS**. Users can select which TTS system they prefer by navigating to dedicated pages for each system.

## Features

### 1. Chatbot Interaction
- Communicate with the chatbot using either text or voice input.

### 2. Text-to-Speech (TTS) Systems
- **OpenAI TTS**: Generates natural-sounding speech using OpenAI's models.
- **Amazon Polly TTS**: Uses Amazon Polly to convert text into speech with a variety of voices, including support for different languages.

### 3. Speech-to-Text (STT)
- Converts voice input from users into text using **OpenAI's Whisper model**, allowing voice-based interaction with the chatbot.

### 4. Audio Playback
- Responses from the chatbot are played as audio, making conversations more interactive.

### 5. Dedicated Pages for TTS Selection
- Users can navigate to:
  - **/openai-tts** for the OpenAI-based TTS.
  - **/polly-tts** for Amazon Polly TTS.