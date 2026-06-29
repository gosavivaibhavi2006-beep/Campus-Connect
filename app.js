document.addEventListener('DOMContentLoaded', () => {
    // 1. Ticker System Status Simulator
    const tickerEl = document.getElementById('system-status-ticker');
    if (tickerEl) {
        const statuses = [
            "🟢 System Active | All APIs responding in under 35ms",
            "🟢 System Active | Database sync completed successfully",
            "🟢 System Active | Server load 12% | CPU Temp 41°C",
            "🟢 System Active | Latency: 18ms | 0 errors in past 24h"
        ];
        let statusIdx = 0;
        setInterval(() => {
            statusIdx = (statusIdx + 1) % statuses.length;
            tickerEl.style.opacity = 0;
            setTimeout(() => {
                tickerEl.textContent = statuses[statusIdx];
                tickerEl.style.opacity = 1;
            }, 300);
        }, 8000);
    }

    // 2. Chatbot Dialog Control
    const chatToggle = document.getElementById('chat-toggle');
    const chatWindow = document.getElementById('chat-window');
    const closeChat = document.getElementById('close-chat');
    const chatInput = document.getElementById('chat-input');
    const sendChatBtn = document.getElementById('send-chat');
    const chatMessages = document.getElementById('chat-messages');
    const voiceBtn = document.getElementById('voice-assistant-btn');
    const speakResponseToggle = document.getElementById('speak-response-toggle');

    if (chatToggle && chatWindow) {
        chatToggle.addEventListener('click', () => {
            chatWindow.classList.toggle('active');
            if (chatWindow.classList.contains('active')) {
                chatInput.focus();
            }
        });
    }

    if (closeChat && chatWindow) {
        closeChat.addEventListener('click', () => {
            chatWindow.classList.remove('active');
        });
    }

    // Send chat logic
    async function handleSend() {
        const text = chatInput.value.trim();
        if (!text) return;

        appendMessage(text, 'user');
        chatInput.value = '';

        // Add loading state
        const loadingId = appendMessage('Thinking...', 'bot');

        try {
            const res = await fetch('/chatbot/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();
            
            // Remove loading bubble
            const loadingBubble = document.getElementById(loadingId);
            if (loadingBubble) loadingBubble.remove();

            appendMessage(data.reply, 'bot');
            
            // Speech Synthesis if enabled
            if (speakResponseToggle && speakResponseToggle.checked) {
                speakText(data.reply);
            }
        } catch (err) {
            console.error(err);
            const loadingBubble = document.getElementById(loadingId);
            if (loadingBubble) loadingBubble.remove();
            appendMessage("Error communicating with AI assistant. Please try again.", 'bot');
        }
    }

    if (sendChatBtn) {
        sendChatBtn.addEventListener('click', handleSend);
    }

    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleSend();
            }
        });
    }

    function appendMessage(text, sender) {
        const bubble = document.createElement('div');
        const uniqueId = 'bubble-' + Date.now();
        bubble.id = uniqueId;
        bubble.classList.add('chat-bubble', sender);
        
        // Render basic markdown-like formatting (bold and italic)
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
            
        bubble.innerHTML = formatted;
        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return uniqueId;
    }

    // 3. Voice Assistance (Speech-to-Text / Speech Recognition)
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    let isListening = false;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
            isListening = true;
            if (voiceBtn) {
                voiceBtn.classList.add('animate-pulse');
                voiceBtn.classList.remove('bg-gray-800');
                voiceBtn.classList.add('bg-red-600');
                const icon = voiceBtn.querySelector('svg, i');
                if (icon) {
                    icon.style.color = '#fff';
                }
            }
            if (chatInput) {
                chatInput.placeholder = "Listening to voice...";
            }
        };

        recognition.onend = () => {
            isListening = false;
            if (voiceBtn) {
                voiceBtn.classList.remove('animate-pulse');
                voiceBtn.classList.add('bg-gray-800');
                voiceBtn.classList.remove('bg-red-600');
                const icon = voiceBtn.querySelector('svg, i');
                if (icon) {
                    icon.style.color = '';
                }
            }
            if (chatInput) {
                chatInput.placeholder = "Ask question...";
            }
        };

        recognition.onerror = (event) => {
            console.error("Speech Recognition Error: ", event.error);
            appendMessage(`[Voice Error: ${event.error}]`, 'bot');
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            chatInput.value = transcript;
            handleSend();
        };
    } else {
        if (voiceBtn) {
            voiceBtn.title = "Voice recognition not supported in this browser";
            voiceBtn.disabled = true;
            voiceBtn.style.opacity = '0.5';
        }
    }

    if (voiceBtn && recognition) {
        voiceBtn.addEventListener('click', () => {
            if (isListening) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });
    }

    // 4. Speech Synthesis (Text-to-Speech)
    function speakText(text) {
        if (!window.speechSynthesis) return;

        // Cancel current utterance if speaking
        window.speechSynthesis.cancel();

        // Strip HTML tags for speaking
        const cleanedText = text.replace(/<[^>]*>/g, '').replace(/\*/g, '');
        const utterance = new SpeechSynthesisUtterance(cleanedText);
        utterance.lang = 'en-US';
        utterance.rate = 1.0;
        
        // Try to pick a premium natural sounding voice if available
        const voices = window.speechSynthesis.getVoices();
        const englishVoice = voices.find(v => v.lang.startsWith('en') && v.name.includes('Google'));
        if (englishVoice) {
            utterance.voice = englishVoice;
        }

        window.speechSynthesis.speak(utterance);
    }
});
