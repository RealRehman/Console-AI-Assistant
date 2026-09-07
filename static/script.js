// ============================================
// AI Assistant Chat — script.js
// ============================================

const chat = document.getElementById('chat');
const header = document.getElementById('header');
const headerSubtitle = document.getElementById('headerSubtitle');
const input = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const typingRow = document.getElementById('typingRow');

// ---------- Document / RAG panel ----------
const documentInput = document.getElementById('documentInput');
const uploadBtn = document.getElementById('uploadBtn');
const docDropzone = document.getElementById('docDropzone');
const docCard = document.getElementById('docCard');
const docName = document.getElementById('docName');
const docMeta = document.getElementById('docMeta');
const removeDocBtn = document.getElementById('removeDocBtn');

// ---------- Token usage bar ----------
const tokenLabel = document.getElementById('tokenLabel');
const tokenPercent = document.getElementById('tokenPercent');
const tokenBarFill = document.getElementById('tokenBarFill');

let contextWindow = 0;

// ---------- Boot: load current document + model limits ----------
(async function init() {
  try {
    const limitsRes = await fetch('/limits');
    const limits = await limitsRes.json();
    contextWindow = limits.context_window || 0;
    updateTokenBar(0, contextWindow);
  } catch (e) {
    console.error('Could not load model limits', e);
  }

  try {
    const statusRes = await fetch('/document/status');
    const status = await statusRes.json();
    renderDocumentStatus(status);
  } catch (e) {
    console.error('Could not load document status', e);
  }
})();

function renderDocumentStatus(status) {
  if (status && status.loaded) {
    docDropzone.hidden = true;
    docCard.hidden = false;
    docName.textContent = status.filename;
    docMeta.textContent =
      `${status.chunk_count} chunks · ~${status.total_tokens.toLocaleString()} tokens indexed`;
    headerSubtitle.textContent = `Chatting with ${status.filename}`;
  } else {
    docDropzone.hidden = false;
    docCard.hidden = true;
    headerSubtitle.textContent = 'Powered by LLM';
  }
}

function updateTokenBar(promptTokens, windowSize) {
  const total = windowSize || contextWindow || 1;
  const percent = Math.min(100, (promptTokens / total) * 100);

  tokenLabel.textContent =
    `${promptTokens.toLocaleString()} / ${total.toLocaleString()} tokens`;
  tokenPercent.textContent = `${percent.toFixed(1)}%`;
  tokenBarFill.style.width = `${percent}%`;

  tokenBarFill.classList.remove('warn', 'danger');
  if (percent >= 90) {
    tokenBarFill.classList.add('danger');
  } else if (percent >= 70) {
    tokenBarFill.classList.add('warn');
  }
}

// ---------- Upload ----------
uploadBtn.addEventListener('click', () => documentInput.click());
documentInput.addEventListener('change', () => {
  if (documentInput.files[0]) uploadDocument(documentInput.files[0]);
});

// Drag & drop support
['dragenter', 'dragover'].forEach((evt) => {
  docDropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    docDropzone.classList.add('drag-over');
  });
});

['dragleave', 'drop'].forEach((evt) => {
  docDropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    docDropzone.classList.remove('drag-over');
  });
});

docDropzone.addEventListener('drop', (e) => {
  const file = e.dataTransfer.files[0];
  if (file) uploadDocument(file);
});

async function uploadDocument(file) {

  const fileName = file.name.toLowerCase();

  if (!fileName.endsWith('.docx') && !fileName.endsWith('.pdf')) {
    alert('Only .docx and .pdf files are supported.');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Uploading...';

    const response = await fetch('/upload', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Upload failed.');
    }

    renderDocumentStatus(data.document);

  } catch (error) {
    console.error(error);
    alert(error.message || 'Unable to upload the document.');

  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = 'Upload Document';
    documentInput.value = '';
  }
}

removeDocBtn.addEventListener('click', async () => {
  try {
    removeDocBtn.disabled = true;
    const response = await fetch('/document', { method: 'DELETE' });
    const data = await response.json();
    renderDocumentStatus(data.document);
  } catch (error) {
    console.error(error);
    alert('Unable to remove the document.');
  } finally {
    removeDocBtn.disabled = false;
  }
});


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

// ---------- Show which document chunks a reply was grounded in ----------
function createSourcesRow(sources) {
  const row = document.createElement('div');
  row.className = 'sources-row';

  sources.forEach((source) => {
    const pill = document.createElement('span');
    pill.className = 'source-pill';
    pill.textContent = `Chunk ${source.chunk_index} · ${Math.round(source.score * 100)}% match`;
    row.appendChild(pill);
  });

  return row;
}

// ---------- Show which tools were called for a reply (function calling) ----------
function createToolsRow(toolCalls) {
  const row = document.createElement('div');
  row.className = 'tools-row';

  toolCalls.forEach((call) => {
    const pill = document.createElement('span');
    pill.className = 'tool-pill';
    pill.textContent = `🔧 ${call.name}`;
    pill.title = JSON.stringify(call.arguments) + ' → ' + JSON.stringify(call.result);
    row.appendChild(pill);
  });

  return row;
}

// ---------- Show sentiment / priority / category for a user message (structured output) ----------
function createAnalysisRow(analysis) {
  const row = document.createElement('div');
  row.className = 'analysis-row';

  const sentimentPill = document.createElement('span');
  sentimentPill.className = `analysis-pill sentiment-${analysis.sentiment}`;
  sentimentPill.textContent = analysis.sentiment;
  row.appendChild(sentimentPill);

  const priorityPill = document.createElement('span');
  priorityPill.className = `analysis-pill priority-${analysis.priority}`;
  priorityPill.textContent = `${analysis.priority} priority`;
  row.appendChild(priorityPill);

  const categoryPill = document.createElement('span');
  categoryPill.className = 'analysis-pill';
  categoryPill.textContent = analysis.category;
  row.appendChild(categoryPill);

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

document.querySelectorAll('.row').forEach((row) => observeRow(row));


// ---------- Structured-output demo: tag the user's own message ----------
async function analyzeMessage(userRow, text) {
  try {
    const response = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });

    if (!response.ok) return; // best-effort only; never blocks the chat

    const analysis = await response.json();
    const analysisRow = createAnalysisRow(analysis);
    userRow.after(analysisRow);
  } catch (error) {
    console.error('Analysis unavailable:', error);
  }
}


// ---------- Send a message (streamed) ----------
async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  const userRow = createRow(text, 'user');
  chat.appendChild(userRow);
  observeRow(userRow);

  // Fire-and-forget structured-output classification of the user's message.
  analyzeMessage(userRow, text);

  input.value = '';
  autoResize();
  scrollToBottom();

  showTyping();

  const aiRow = createRow('', 'ai');
  const bubble = aiRow.querySelector('.bubble');
  let toolsUsed = [];
  let hasStartedStreaming = false;

  try {
    const response = await fetch('/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });

    if (!response.ok || !response.body) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || 'Something went wrong.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line ("\n\n").
      const frames = buffer.split('\n\n');
      buffer = frames.pop(); // last (possibly incomplete) frame stays buffered

      for (const frame of frames) {
        const line = frame.split('\n').find((l) => l.startsWith('data:'));
        if (!line) continue;

        const jsonStr = line.slice(5).trim();
        if (!jsonStr) continue;

        let event;
        try {
          event = JSON.parse(jsonStr);
        } catch (e) {
          continue;
        }

        if (event.type === 'token') {
          if (!hasStartedStreaming) {
            hideTyping();
            chat.appendChild(aiRow);
            observeRow(aiRow);
            bubble.classList.add('streaming');
            hasStartedStreaming = true;
          }
          bubble.textContent += event.content;
          scrollToBottom();

        } else if (event.type === 'tool_call') {
          toolsUsed.push(event);

        } else if (event.type === 'meta') {
          if (event.used_rag && event.sources && event.sources.length) {
            aiRow.dataset.sources = JSON.stringify(event.sources);
          }

        } else if (event.type === 'done') {
          if (!hasStartedStreaming) {
            hideTyping();
            chat.appendChild(aiRow);
            observeRow(aiRow);
          }
          bubble.classList.remove('streaming');

          if (toolsUsed.length) {
            const toolsRow = createToolsRow(toolsUsed);
            aiRow.after(toolsRow);
          }

          if (aiRow.dataset.sources) {
            const sourcesRow = createSourcesRow(JSON.parse(aiRow.dataset.sources));
            aiRow.after(sourcesRow);
          }

          if (event.token_usage) {
            updateTokenBar(event.token_usage.cumulative_total_tokens, event.token_usage.context_window);
          }

          scrollToBottom();

        } else if (event.type === 'error') {
          throw new Error(event.message || 'Something went wrong.');
        }
      }
    }

  } catch (error) {
    hideTyping();

    if (!hasStartedStreaming) {
      bubble.textContent = error.message || 'Unable to connect to the server.';
      chat.appendChild(aiRow);
      observeRow(aiRow);
    } else {
      bubble.textContent += `\n\n⚠️ ${error.message || 'Connection lost.'}`;
    }

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