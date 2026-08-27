// ============================================
// AI Assistant Chat — script.js
// ============================================

const chat = document.getElementById('chat');
const header = document.getElementById('header');
const input = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const typingRow = document.getElementById('typingRow');

// ---------- Document upload ----------
const documentInput = document.getElementById('documentInput');
const uploadBtn = document.getElementById('uploadBtn');

uploadBtn.addEventListener('click', uploadDocument);

async function uploadDocument() {

  const file = documentInput.files[0];

  if (!file) {
    alert("Please select a Word document first.");
    return;
  }

  const fileName = file.name.toLowerCase();

  if (
    !fileName.endsWith(".docx") &&
    !fileName.endsWith(".pdf")
  ) {
    alert("Only .docx and .pdf files are supported.");
    return;
  }

  const formData = new FormData();

  formData.append("file", file);

  try {

    uploadBtn.disabled = true;
    uploadBtn.textContent = "Uploading...";

    const response = await fetch("/upload", {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Upload failed.");
    }

    alert("Document uploaded successfully.");

    console.log(data);

  } catch (error) {

    console.error(error);

    alert(
      error.message || "Unable to upload the document."
    );

  } finally {

    uploadBtn.disabled = false;
    uploadBtn.textContent = "Upload Document";

  }
}


// ---------- Auto-resize the textarea as you type ----------
function autoResize() {

  input.style.height = 'auto';

  input.style.height =
    Math.min(input.scrollHeight, 140) + 'px';
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

  avatar.textContent =
    sender === 'user' ? '👤' : '🤖';


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

  {
    root: chat,
    threshold: 0.15
  }

);


function observeRow(row) {

  revealObserver.observe(row);

}


// Reveal existing messages on load
document
  .querySelectorAll('.row')
  .forEach((row) => observeRow(row));


// ---------- Send a message ----------
async function sendMessage() {

  const text = input.value.trim();

  if (!text) return;


  const userRow =
    createRow(text, 'user');

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
        message: text
      })

    });


    const data =
      await response.json();


    hideTyping();


    const aiRow =
      createRow(
        data.response,
        "ai"
      );


    chat.appendChild(aiRow);

    observeRow(aiRow);

    scrollToBottom();


  } catch (error) {

    hideTyping();


    const aiRow =
      createRow(
        "Unable to connect to the server.",
        "ai"
      );


    chat.appendChild(aiRow);

    observeRow(aiRow);

    scrollToBottom();


    console.error(error);

  }

}


// ---------- Typing indicator ----------
function showTyping() {

  typingRow.hidden = false;

}


function hideTyping() {

  typingRow.hidden = true;

}


// ---------- Smooth scroll ----------
function scrollToBottom() {

  chat.scrollTo({

    top: chat.scrollHeight,

    behavior: 'smooth'

  });

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