document.addEventListener("DOMContentLoaded", () => {
    const socket = io.connect();
    const startTalkingButton = document.getElementById("start-talking-button");  // Microphone button
    const keyboardButton = document.getElementById("keyboard-button");  // Keyboard button
    const sendButton = document.getElementById("send-button");  // Send button
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

    // Handle incoming message and audio data from the server
    socket.on("response_with_audio", data => {
        // Remove loading indicator when the response is received
        removeLoadingIndicator();

        // Display the bot message
        appendMessage("bot", data.message);

        // Handle audio playback if audio data is provided
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

    // Handle incoming text converted from speech
    socket.on("stt_response", data => {
        removeLoadingIndicator();  // Remove the loading indicator

        if (data.text) {
            // If transcribed text is available, append it and send it as a message
            appendMessage("user", data.text);  // Display the transcribed text as a user message
            socket.emit("message", data.text);  // Send the transcribed text to the backend
        } else {
            // If no transcribed text is available, show error message
            appendMessage("user", "Unable to detect human voice.");  // Show error message
            console.error('Failed to convert speech to text:', data.error);
        }
    });

    // Toggle visibility of the input box and send button when keyboard icon is clicked
    keyboardButton.addEventListener("click", () => {
        const isVisible = hiddenInputContainer.style.display === 'flex';
        hiddenInputContainer.style.display = isVisible ? 'none' : 'flex';  // Toggle visibility

        // Ensure the container's layout is consistent when visible
        hiddenInputContainer.style.flexDirection = 'row';

        if (!isVisible) {
            userInput.focus();  // Focus on the input field when shown
        }
    });

    // Handle start/stop recording when the "Start talking" button is clicked
    startTalkingButton.addEventListener("click", () => {
        if (mediaRecorder && mediaRecorder.state === "recording") {
            // Stop recording
            mediaRecorder.stop();
            startTalkingButton.classList.remove("recording");  // Remove recording class
            startTalkingButton.textContent = "🎤";  // Reset icon to normal state
        } else {
            // Start recording
            startRecording();
            startTalkingButton.classList.add("recording");  // Add recording class
            startTalkingButton.textContent = "🎤";  // Icon remains same
        }
    });

    // Function to start recording audio
    function startRecording() {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.start();
                
                // Clear previous audio chunks
                audioChunks = [];

                // Store audio data chunks
                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };

                // When recording is stopped, send the audio to the backend
                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
                    const reader = new FileReader();
                    
                    reader.onload = () => {
                        const arrayBuffer = reader.result;
                        const audioData = new Uint8Array(arrayBuffer);
                        socket.emit("speech_to_text", { audio: audioData });
                    };

                    reader.readAsArrayBuffer(audioBlob);  // Convert the Blob to ArrayBuffer

                    // Show loading indicator after the user clicks "Stop talking and send"
                    showLoadingIndicator(true);  // Pass true to align the indicator to the right
                };
            })
            .catch(error => {
                console.error("Error accessing microphone:", error);
            });
    }

    // Function to append message to the chat box
    function appendMessage(sender, message) {
        const messageElement = document.createElement("div");
        messageElement.classList.add("message", sender.toLowerCase());
        // Style the "Unable to detect human voice" message like a user message
        if (message === "Unable to detect human voice." && sender === "user") {
            messageElement.style.backgroundColor = "#DCF8C6";  // Same green background
            messageElement.style.color = "#333";  // Same text color
            messageElement.style.alignSelf = "flex-end";  // Align to the right like user messages
        }
        messageElement.textContent = message;  // Only display the message content
        messagesDiv.appendChild(messageElement);
        messagesDiv.scrollTop = messagesDiv.scrollHeight; // Scroll to bottom
    }

    // Function to show loading indicator with animation in the chat box
    function showLoadingIndicator() {
        loadingMessageElement = document.createElement("div");
        loadingMessageElement.classList.add("message", "loading");
        loadingMessageElement.textContent = ".";  // Initial content is a single dot

        // Apply styles to center the loading animation in the chat box
        loadingMessageElement.style.textAlign = 'center';  // Center the text
        loadingMessageElement.style.alignSelf = 'center';  // Center the element

        messagesDiv.appendChild(loadingMessageElement);
        messagesDiv.scrollTop = messagesDiv.scrollHeight; // Scroll to bottom

        let dots = 1;
        loadingInterval = setInterval(() => {
            dots = (dots % 3) + 1;  // Cycle between 1, 2, and 3 dots
            loadingMessageElement.textContent = ".".repeat(dots);  // Update content
        }, 500);  // Change every 500ms for smooth animation
    }

    // Function to remove loading indicator
    function removeLoadingIndicator() {
        if (loadingMessageElement) {
            messagesDiv.removeChild(loadingMessageElement);
            loadingMessageElement = null;
        }
        if (loadingInterval) {
            clearInterval(loadingInterval);  // Clear the animation interval
            loadingInterval = null;
        }
    }
});
