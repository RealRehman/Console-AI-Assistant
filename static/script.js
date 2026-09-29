// ============================================
// AI Assistant Chat — script.js (Week 7: multi-document RAG + citations)
// ============================================

const chat = document.getElementById('chat');
const header = document.getElementById('header');
const headerSubtitle = document.getElementById('headerSubtitle');
const input = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const typingRow = document.getElementById('typingRow');

// ---------- Document library panel ----------
const documentInput = document.getElementById('documentInput');
const uploadBtn = document.getElementById('uploadBtn');
const docDropzone = document.getElementById('docDropzone');
const docList = document.getElementById('docList');

// ---------- Token usage bar ----------
const tokenLabel = document.getElementById('tokenLabel');
const tokenPercent = document.getElementById('tokenPercent');
const tokenBarFill = document.getElementById('tokenBarFill');

let contextWindow = 0;

// ---------- Boot: load current library + model limits ----------
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
    renderDocumentLibrary(status);
  } catch (e) {
    console.error('Could not load document status', e);
  }
})();

function renderDocumentLibrary(status) {
  docList.innerHTML = '';

  if (!status || !status.loaded) {
    headerSubtitle.textContent = 'Powered by LLM';
    return;
  }

  headerSubtitle.textContent =
    `Chatting with ${status.document_count} document${status.document_count === 1 ? '' : 's'}`;

  status.documents.forEach((doc) => {
    const card = document.createElement('div');
    card.className = 'doc-card';
    card.dataset.docId = doc.doc_id;

    const icon = document.createElement('div');
    icon.className = 'doc-card-icon';
    icon.textContent = '📄';

    const info = document.createElement('div');
    info.className = 'doc-card-info';

    const name = document.createElement('strong');
    name.textContent = doc.filename;

    const metaRow = document.createElement('div');
    metaRow.className = 'doc-card-meta-row';

    const meta = document.createElement('span');
    meta.textContent = `${doc.chunk_count} chunks · ~${doc.total_tokens.toLocaleString()} tokens`;
    metaRow.appendChild(meta);

    if (doc.duplicate_of) {
      const badge = document.createElement('span');
      badge.className = 'doc-duplicate-badge';
      badge.title = 'Identical content to an already-loaded document';
      badge.textContent = 'Duplicate content';
      metaRow.appendChild(badge);
    }

    info.appendChild(name);
    info.appendChild(metaRow);

    const removeBtn = document.createElement('button');
    removeBtn.className = 'doc-btn doc-btn-ghost';
    removeBtn.type = 'button';
    removeBtn.title = 'Remove this document';
    removeBtn.textContent = 'Remove';
    removeBtn.addEventListener('click', () => removeDocument(doc.doc_id));

    card.appendChild(icon);
    card.appendChild(info);
    card.appendChild(removeBtn);
    docList.appendChild(card);
  });
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

// ---------- Upload (one or more files) ----------
uploadBtn.addEventListener('click', () => documentInput.click());
documentInput.addEventListener('change', () => {
  if (documentInput.files.length) uploadDocuments(Array.from(documentInput.files));
});

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
  const files = Array.from(e.dataTransfer.files || []);
  if (files.length) uploadDocuments(files);
});

async function uploadDocuments(files) {
  const allowed = /\.(docx|pdf|txt|md|markdown)$/i;
  const valid = files.filter((f) => allowed.test(f.name));

  if (!valid.length) {
    alert('Only PDF, DOCX, TXT, and Markdown files are supported.');
    return;
  }

  uploadBtn.disabled = true;
  const originalLabel = uploadBtn.textContent;

  try {
    for (let i = 0; i < valid.length; i++) {
      uploadBtn.textContent = `Uploading ${i + 1}/${valid.length}...`;
      await uploadOneDocument(valid[i]);
    }
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = originalLabel;
    documentInput.value = '';
  }
}

async function uploadOneDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch('/upload', { method: 'POST', body: formData });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || `Upload failed for ${file.name}.`);
    }

    renderDocumentLibrary(data.library);
  } catch (error) {
    console.error(error);
    alert(error.message || `Unable to upload ${file.name}.`);
  }
}

async function removeDocument(docId) {
  try {
    const response = await fetch(`/document/${docId}`, { method: 'DELETE' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not remove document.');
    renderDocumentLibrary(data.library);
  } catch (error) {
    console.error(error);
    alert(error.message || 'Unable to remove the document.');
  }
}


// ---------- Auto-resize the textarea as you type ----------
function autoResize() {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 140) + 'px';
}

input.addEventListener('input', autoResize);

input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener('click', sendMessage);


// ---------- Message bubble helpers ----------
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

// Citations: each source is {source, page, section, score, label}
function createSourcesRow(sources) {
  const row = document.createElement('div');
  row.className = 'sources-row';

  sources.forEach((source) => {
    const pill = document.createElement('span');
    pill.className = 'source-pill citation-pill';
    pill.textContent = `${source.label} · ${Math.round(source.score * 100)}%`;
    row.appendChild(pill);
  });

  return row;
}

function createNoContextNote() {
  const note = document.createElement('div');
  note.className = 'no-context-note';
  note.textContent = 'No excerpt in the loaded document(s) scored as relevant to this question.';
  return note;
}

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


// ---------- Scroll reveal ----------
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
    if (!response.ok) return;
    const analysis = await response.json();
    userRow.after(createAnalysisRow(analysis));
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

  analyzeMessage(userRow, text);

  input.value = '';
  autoResize();
  scrollToBottom();

  showTyping();

  const aiRow = createRow('', 'ai');
  const bubble = aiRow.querySelector('.bubble');
  let toolsUsed = [];
  let usedRag = false;
  let sources = [];
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
      const frames = buffer.split('\n\n');
      buffer = frames.pop();

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
          usedRag = event.used_rag;
          sources = event.sources || [];

        } else if (event.type === 'done') {
          if (!hasStartedStreaming) {
            hideTyping();
            chat.appendChild(aiRow);
            observeRow(aiRow);
          }
          bubble.classList.remove('streaming');

          if (toolsUsed.length) {
            aiRow.after(createToolsRow(toolsUsed));
          }

          if (usedRag) {
            if (sources.length) {
              aiRow.after(createSourcesRow(sources));
            } else {
              aiRow.after(createNoContextNote());
            }
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
function showTyping() { typingRow.hidden = false; }
function hideTyping() { typingRow.hidden = true; }

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

scrollToBottom();