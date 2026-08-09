// ============================================
// AI Assistant Chat — script.js
// ============================================

const chat = document.getElementById('chat');
const header = document.getElementById('header');
const input = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const typingRow = document.getElementById('typingRow');
let conversationId = null;

// ---------- Auto-resize the textarea as you type ----------
function autoResize() {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 140) + 'px';
}
input.addEventListener('input', autoResize);

// ---------- Enter to send, Shift+Enter for a new line ----------
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener('click', sendMessage);

// ---------- Create a message bubble ----------
function createRow(text, sender) {
  const row = document.createElement('div');
  row.className = `row ${sender}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = sender === 'user' ? '👤' : '🤖';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;

  row.appendChild(avatar);
  row.appendChild(bubble);
  return row;
}

// ---------- Scroll reveal (IntersectionObserver) ----------
const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        revealObserver.unobserve(entry.target);
      }
    });
  },
  { root: chat, threshold: 0.15 }
);

function observeRow(row) {
  revealObserver.observe(row);
}

// Reveal any messages already in the DOM on load
document.querySelectorAll('.row').forEach((row) => observeRow(row));

// ---------- Send a message ----------
async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  const userRow = createRow(text, 'user');
  chat.appendChild(userRow);
  observeRow(userRow);

  input.value = '';
  autoResize();
  scrollToBottom();

  showTyping();

  try {

    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message: text, 
        conversation_id: conversationId
      })
    });

    const data = await response.json();
    conversationId = data.conversation_id;

    hideTyping();

    const aiRow = createRow(data.response, "ai");

    chat.appendChild(aiRow);

    observeRow(aiRow);

    scrollToBottom();

  } catch (error) {

    hideTyping();

    const aiRow = createRow(
      "Unable to connect to the server.",
      "ai"
    );

    chat.appendChild(aiRow);

    observeRow(aiRow);

    scrollToBottom();

    console.error(error);

  }

  // ---------- Typing indicator ----------
  function showTyping() {
    typingRow.hidden = false;
  }
  function hideTyping() {
    typingRow.hidden = true;
  }

  // ---------- Smooth scroll to the latest message ----------
  function scrollToBottom() {
    chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' });
  }

  // ---------- Header shadow on scroll ----------
  chat.addEventListener('scroll', () => {
    if (chat.scrollTop > 4) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
  });

  // ---------- Initial scroll position ----------
  scrollToBottom();
}