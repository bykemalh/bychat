var userId = document.getElementById("userId").textContent;
var isRequestInProgress = false;

function getToken() {
    return document.getElementById("serverToken").value;
}

async function sendMessage() {
    const chatContainer = document.getElementById("chat-container");
    const merhabaDiv = document.getElementById("merhaba");
    const userMessage = document.getElementById("user-input").value;
    const sendButton = document.getElementById("send-btn");  // Butonu al
    const token = document.getElementById("serverToken").value;

    if (userMessage.length < 2) {
        alert("Please enter at least 2 characters.");
        return;
    }

    // Eğer zaten bir istek devam ediyorsa fonksiyondan çık
    if (isRequestInProgress) {
        return;
    }

    // İstek başlıyor, buton disable ve isRequestInProgress true yapılır
    isRequestInProgress = true;
    sendButton.disabled = true;

    merhabaDiv.style.display = "none";
    document.getElementById("user-input").value = "";

    // Kullanıcı mesajı ekle
    const userMessageHTML = document.createElement('div');
    userMessageHTML.id = 'user-msg';

    const userIcon = document.createElement('span');
    userIcon.className = 'material-symbols-outlined';
    userIcon.innerHTML = 'account_circle';

    const userMessageText = document.createElement('div');
    userMessageText.innerText = userMessage;

    userMessageHTML.appendChild(userIcon);
    userMessageHTML.appendChild(userMessageText);
    chatContainer.appendChild(userMessageHTML);

    chatContainer.scrollTop = chatContainer.scrollHeight;

    // Bot mesajı için boş bir alan oluştur
    const botMessageHTML = document.createElement('div');
    botMessageHTML.id = 'bot-msg';

    const botIcon = document.createElement('span');
    botIcon.className = 'material-symbols-outlined';
    botIcon.id = "robot-span";
    botIcon.innerHTML = 'smart_toy';

    const preElement = document.createElement('div');
    preElement.className = "bot-message-text markdown-body";
    preElement.id = "botMsg-pre";

    // Bot cevabı gelene kadar animasyon göster
    preElement.innerHTML = '<div class="loading">...</div>';

    botMessageHTML.appendChild(botIcon);
    botMessageHTML.appendChild(preElement);
    chatContainer.appendChild(botMessageHTML);

    chatContainer.scrollTop = chatContainer.scrollHeight;

    try {
        const result = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                "prompt": userMessage,
                "token": token
            })
        });

        if (!result.ok) {
            throw new Error(`HTTP error! status: ${result.status}`);
        }

        const reader = result.body.getReader();
        const decoder = new TextDecoder();

        // Yükleniyor animasyonunu kaldır
        preElement.innerHTML = '';

        let fullText = '';
        let displayedText = '';
        let isWriting = false;

        async function typeWriter() {
            if (displayedText.length < fullText.length) {
                if (!isWriting) {
                    isWriting = true;
                    const nextChar = fullText[displayedText.length];
                    displayedText += nextChar;

                    // Markdown'ı HTML'e dönüştür ve göster
                    preElement.innerHTML = marked.parse(displayedText);

                    chatContainer.scrollTop = chatContainer.scrollHeight;

                    isWriting = false;
                }
                setTimeout(typeWriter, 10); // Yazma hızını ayarlayabilirsiniz
            }
        }

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.trim() !== '') {
                    try {
                        const jsonChunk = JSON.parse(line);
                        fullText += jsonChunk.chunk;
                        if (!isWriting) {
                            typeWriter();
                        }
                    } catch (e) {
                        console.error('Error parsing JSON:', e);
                    }
                }
            }
        }
        preElement.classList.add('fadeInText');
        void preElement.offsetWidth;

    } catch (error) {
        // Hata durumunda kullanıcıya mesaj gönder
        preElement.className = "error-message";
        preElement.innerText = "Hata oluştu!";
        preElement.classList.add('fadeInText');
        console.error('Error:', error);
    } finally {
        // İstek tamamlandığında butonu tekrar aktif yap ve isRequestInProgress'i false yap
        sendButton.disabled = false;
        isRequestInProgress = false;
    }

    chatContainer.scrollTop = chatContainer.scrollHeight;

}

function handleKeyPress(event) {
    // Eğer istek devam ediyorsa Enter ile yeni istek göndermeyi engelle
    if (event.key === 'Enter' && !event.shiftKey && !event.ctrlKey && !event.metaKey && !isRequestInProgress) {
        event.preventDefault();
        sendMessage();
    }
}

function scrollToBottom() {
    const chatContainer = document.getElementById("chat-container");
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

document.addEventListener('DOMContentLoaded', function () {
    const token = document.getElementById("serverToken").value;
    const loadHistory = document.getElementById("loadHistory").value === 'true';
    const urlParams = new URLSearchParams(window.location.search);
    const userInput = document.getElementById("user-input");
    const questionLinks = document.querySelectorAll('.soru');
    const questions = {
        "#option1": [
            "What can I do to determine my own values and priorities?",
            "Which strategies should I try to improve my time management skills?",
            "What can I do to be more effective in coping with stress?",
            "Which activities should I implement to increase my emotional intelligence level?",
            "What steps can I take to be more effective in goal setting and planning?",
            "What internal resources can I use to motivate myself more?",
            "What can I do to develop a habit of reading books and increase my knowledge?",
        ],
        "#option2": [
            "What steps do I need to take to advance in my career and achieve my goals?",
            "What should I do to determine and plan for my future financial goals?",
            "Which skills and talents should I develop to support my personal or professional growth?",
            "What should I consider in creating a long-term life plan?",
            "Which industries will have more job opportunities in the future, and how can I build a career in these industries?",
            "Which professions will be in higher demand with the development of digital technologies?",
            "What will be the demand for careers in green energy and sustainability in the future?",
            "What learning and development strategy should I adopt to gain a competitive advantage in future professions?",
        ],
        "#option3": [
            "What's the weather like today, will it rain or be sunny outside?",
            "What passions do you want to explore?",
            "What is a scene or quote from the last book you read or movie you watched that influenced you?",
            "Do you want to set a small goal for today and focus on it?",
            "Is there a moment in your daily activities where you want to reward yourself?",
            "What new thing do you want to learn about today?",
            "Do you have a plan that you will be proud of for something you will do today?",
            "Have you considered taking a few minutes to calm down amid your daily hustle?",
            "Is there an opportunity today to do a good deed or help others?",
            "Do you have a plan to spend quality time with your loved ones or friends today?",
        ],
        "#option4": [
            "How are you leveraging technology to enhance your daily health and well-being routine?",
            "What tech-based solutions are you exploring to improve your health and well-being?",
            "Which apps or devices can assist you in tracking and increasing your daily water intake?",
            "How can technology support you in achieving a healthier diet?",
            "What technological innovations can you incorporate into your daily exercise routine?",
            "Which digital tools or platforms can contribute to your mental health and well-being?",
            "How can technology help you establish and maintain regular sleep habits?",
            "What digital resources or apps can assist you in improving your stress coping methods?",
            "In what ways can you use technology to take breaks and relax more in your daily life?",
            "Which digital tools or apps are you considering for setting and tracking your health goals?",
        ],
    };

    questionLinks.forEach(function (link) {
        link.addEventListener('click', function (event) {
            event.preventDefault();

            const questionId = link.getAttribute('href');
            const categoryQuestions = questions[questionId];
            const randomIndex = Math.floor(Math.random() * categoryQuestions.length);
            const randomQuestion = categoryQuestions[randomIndex];

            userInput.value = randomQuestion;
        });
    });
});

var settingsVisible = false; // Başlangıçta div gizli

function toggleSettings() {
    var settingsDiv = document.getElementById("user-settings");
    settingsVisible = !settingsVisible; // Durumu tersine çevir

    if (settingsVisible) {
        settingsDiv.style.display = "flex";
    } else {
        settingsDiv.style.display = "none";
    }
}