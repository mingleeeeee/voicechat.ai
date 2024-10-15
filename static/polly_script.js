document.addEventListener("DOMContentLoaded", () => {
    const socket = io.connect();
    const startTalkingButton = document.getElementById("start-talking-button");  // Microphone button
    const keyboardButton = document.getElementById("keyboard-button");  // Keyboard button
    const sendButton = document.getElementById("send-button");  // Send button
    const stopAudioButton = document.getElementById("stop-audio-button");  // Stop Audio button
    const userInput = document.getElementById("chat-input");  // Input field for typing text
    const messagesDiv = document.getElementById("chat-messages");
    const hiddenInputContainer = document.getElementById("hidden-input-container");  // Container for input box and send button
    const audioPlayer = new Audio();  // Create a new audio player element
    let loadingMessageElement = null;  // Reference to the loading indicator element
    let loadingInterval = null;  // Reference to interval for loading animation

    let mediaRecorder;  // MediaRecorder instance for recording
    let audioChunks = [];  // Array to store audio data chunks

    // Hide the text input and send button container by default
    hiddenInputContainer.style.display = 'none';

    // Handle incoming message and audio data from the server (for Polly)
    socket.on("response_with_audio", data => {
        removeLoadingIndicator();

        appendMessage("bot", data.message);

        if (data.audio) {
            const audioBlob = new Blob([data.audio], { type: 'audio/mp3' });
            const audioUrl = URL.createObjectURL(audioBlob);
            audioPlayer.src = audioUrl;
            audioPlayer.onloadedmetadata = () => {
                audioPlayer.play();
            };
        } else {
            console.error('Failed to generate audio:', data.error);
        }
    });

    socket.on("stt_response", data => {
        removeLoadingIndicator();

        if (data.text) {
            appendMessage("user", data.text);
            showLoadingIndicator();
            socket.emit("message_polly", data.text);  // Use Polly-specific message route
        } else {
            appendMessage("user", "Unable to detect human voice.");
            console.error('Failed to convert speech to text:', data.error);
        }
    });

    stopAudioButton.addEventListener("click", () => {
        audioPlayer.pause();
        audioPlayer.currentTime = 0;
        console.log("Audio playback stopped.");
    });

    keyboardButton.addEventListener("click", () => {
        const isVisible = hiddenInputContainer.style.display === 'flex';
        hiddenInputContainer.style.display = isVisible ? 'none' : 'flex';
        hiddenInputContainer.style.flexDirection = 'row';

        if (!isVisible) {
            userInput.focus();
        }
    });

    sendButton.addEventListener("click", () => {
        const message = userInput.value.trim();
        if (message) {
            appendMessage("user", message);
            socket.emit("message_polly", message);  // Emit message via Polly-specific route
            userInput.value = "";  // Clear the input field after sending
            showLoadingIndicator();
        }
    });

    userInput.addEventListener("keyup", (event) => {
        if (event.key === "Enter" || event.keyCode === 13) {
            sendButton.click();  // Trigger send button click on 'Enter' press
        }
    });

    startTalkingButton.addEventListener("click", () => {
        if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop();
            startTalkingButton.classList.remove("recording");
            startTalkingButton.textContent = "🎤";
        } else {
            startRecording();
            startTalkingButton.classList.add("recording");
            startTalkingButton.textContent = "🎤";
        }
    });

    function startRecording() {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.start();

                audioChunks = [];

                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };

                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
                    const reader = new FileReader();

                    reader.onload = () => {
                        const arrayBuffer = reader.result;
                        const audioData = new Uint8Array(arrayBuffer);
                        socket.emit("speech_to_text", { audio: audioData });
                    };

                    reader.readAsArrayBuffer(audioBlob);
                    showLoadingIndicator(true);
                };
            })
            .catch(error => {
                console.error("Error accessing microphone:", error);
            });
    }

    function appendMessage(sender, message) {
        const messageElement = document.createElement("div");
        messageElement.classList.add("message", sender.toLowerCase());
    
        // Use innerHTML to render HTML tags like <strong> for bold text
        messageElement.innerHTML = message;
    
        // Special formatting for the "Unable to detect human voice." message
        if (message === "Unable to detect human voice." && sender === "user") {
            messageElement.style.backgroundColor = "#DCF8C6";
            messageElement.style.color = "#333";
            messageElement.style.alignSelf = "flex-end";
        }
    
        messagesDiv.appendChild(messageElement);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;  // Scroll to bottom
    }

    function showLoadingIndicator() {
        if (!loadingMessageElement) {
            loadingMessageElement = document.createElement("div");
            loadingMessageElement.classList.add("message", "loading");
            loadingMessageElement.textContent = ".";

            loadingMessageElement.style.textAlign = 'center';
            loadingMessageElement.style.alignSelf = 'center';

            messagesDiv.appendChild(loadingMessageElement);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;

            let dots = 1;
            loadingInterval = setInterval(() => {
                dots = (dots % 3) + 1;
                loadingMessageElement.textContent = ".".repeat(dots);
            }, 500);
        }
    }

    function removeLoadingIndicator() {
        if (loadingMessageElement) {
            messagesDiv.removeChild(loadingMessageElement);
            loadingMessageElement = null;
        }
        if (loadingInterval) {
            clearInterval(loadingInterval);
            loadingInterval = null;
        }
    }
});
