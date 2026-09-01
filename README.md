# AI Assistant

A Python-based Personal AI Assistant built using **Flask, Python, JavaScript, and the Groq API**.

The application provides a web-based chat interface where users can communicate with an AI model. It also maintains conversation history by saving chats as JSON files, allowing the AI to use previous messages from the same conversation.

> **Current Status:** Working Flask AI Assistant with conversation memory and persistent JSON-based conversation storage.

---

## Features

The current version supports:

* Web-based chat interface
* AI responses using the Groq API
* LLM integration
* Conversation memory
* Persistent conversation storage
* Unique conversation IDs
* JSON-based conversation files
* Flask backend
* Separate Flask route modules
* JavaScript frontend
* CSS-based interface
* System prompt support
* Configurable AI model settings
* Console-based AI assistant
* Basic error handling for invalid chat requests
* Application logging structure
* **Retrieval-Augmented Generation (RAG):** upload a PDF or DOCX and ask
  questions answered only from that document
* Document chunking with configurable chunk size/overlap
* Local vector database (Chroma) for semantic chunk retrieval
* Live token-usage bar showing prompt size vs. the model's context window
* Drag-and-drop / click-to-upload document panel with remove button

---

## Project Structure

```text
ai_assistant/
│
├── app.py
├── chat.py
├── config.py
├── console_app.py
├── conversation_manager.py
├── document_store.py
├── logger.py
├── system_prompt.py
├── utils.py
│
├── rag/
│   ├── __init__.py
│   ├── chunking.py
│   ├── vector_store.py
│   └── token_utils.py
│
├── routes/
│   ├── __init__.py
│   ├── chat_routes.py
│   └── page_routes.py
│
├── templates/
│   └── index.html
│
├── static/
│   ├── script.js
│   └── style.css
│
├── conversations/
│   └── *.json
│
├── logs/
│   └── chatbot.log
│
├── requirements.txt
└── README.md
```

---

# How the Application Works

The application has two main parts:

1. **Frontend**
2. **Backend**

The frontend is responsible for the user interface.

The backend is responsible for handling requests, managing conversations, and communicating with the AI model.

The basic flow is:

```text
User
  ↓
Web Browser
  ↓
JavaScript
  ↓
Flask Route
  ↓
Conversation Manager
  ↓
Chat Module
  ↓
Groq API
  ↓
LLM
  ↓
AI Response
  ↓
Flask
  ↓
JavaScript
  ↓
User
```

---

# Backend

## Flask

Flask is used to create the web application and API routes.

The Flask application receives requests from the browser and sends responses back.

For example:

```text
GET / 
```

is used to load the main page.

And:

```text
POST /chat
```

is used to send a chat message to the AI.

---

# `app.py`

`app.py` is the main Flask application file.

Its main responsibilities are:

* Create the Flask application
* Register the route blueprints
* Start the Flask development server

The application is divided into different modules instead of putting all the code inside `app.py`.

This makes the project easier to understand and maintain.

---

# Routes

The Flask routes are stored inside the `routes/` folder.

```text
routes/
├── __init__.py
├── chat_routes.py
└── page_routes.py
```

## `page_routes.py`

This file handles routes related to web pages.

The main page is:

```text
GET /
```

It returns the HTML page used by the AI Assistant.

---

## `chat_routes.py`

This file handles the chat API.

The main endpoint is:

```text
POST /chat
```

The browser sends a request similar to:

```json
{
    "message": "Hello",
    "conversation_id": "chat_2026-08-09_15-30-20"
}
```

The route then:

1. Gets the message
2. Gets the conversation ID
3. Creates a conversation if necessary
4. Loads the previous conversation
5. Adds the new user message
6. Sends the conversation to the AI
7. Gets the AI response
8. Adds the AI response to the conversation
9. Saves the updated conversation
10. Returns the response to the browser

The response looks similar to:

```json
{
    "conversation_id": "chat_2026-08-09_15-30-20",
    "response": "Hello! How can I help you?"
}
```

---

# AI / LLM Integration

## `chat.py`

`chat.py` is responsible for communicating with the Groq API.

The application uses the Groq Python client to send messages to the LLM.

The current model configuration is controlled through `config.py`.

The important idea is that `chat.py` receives the conversation history instead of only receiving the latest user message.

For example:

```python
[
    {
        "role": "user",
        "content": "My name is Mark."
    },
    {
        "role": "assistant",
        "content": "Nice to meet you!"
    },
    {
        "role": "user",
        "content": "What is my name?"
    }
]
```

The system prompt is added before these messages.

The complete request sent to the LLM is therefore conceptually:

```text
System Prompt
      ↓
Previous User Message
      ↓
Previous AI Response
      ↓
Current User Message
```

This is how our application provides conversation memory to the LLM.

---

# Important: How Conversation Memory Works

The LLM itself does not automatically remember previous API requests.

Our application creates the memory.

The process is:

```text
User Message
     ↓
Store message
     ↓
Save conversation
     ↓
Next request
     ↓
Load conversation
     ↓
Send previous messages + new message to LLM
     ↓
Receive response
     ↓
Save updated conversation
```

For example:

### First message

```text
User:
My name is Mark.
```

The conversation is saved.

### Second message

```text
User:
What is my name?
```

The application loads the previous messages and sends them together to the LLM.

The AI can therefore answer:

```text
Your name is Mark.
```

---

# `conversation_manager.py`

This module manages saved conversations.

It currently provides functions for:

### Creating a conversation

```python
create_conversation()
```

This generates a unique conversation ID based on the current timestamp.

Example:

```text
chat_2026-08-09_15-30-20
```

---

### Saving a conversation

```python
save_conversation(conversation_id, messages)
```

The conversation is stored as a JSON file.

For example:

```text
conversations/
└── chat_2026-08-09_15-30-20.json
```

---

### Loading a conversation

```python
load_conversation(conversation_id)
```

This loads the saved messages from the corresponding JSON file.

---

### Listing conversations

```python
list_conversations()
```

This returns the saved JSON conversation files.

---

# Conversation File Format

A conversation is stored as JSON.

Example:

```json
[
    {
        "role": "user",
        "content": "My name is Mark."
    },
    {
        "role": "assistant",
        "content": "Nice to meet you!"
    },
    {
        "role": "user",
        "content": "What is my name?"
    },
    {
        "role": "assistant",
        "content": "Your name is Mark."
    }
]
```

Each message contains:

```text
role
content
```

Possible roles currently used are:

```text
user
assistant
```

The system prompt is added when the conversation is sent to the LLM.

---

# Frontend

The frontend is located in:

```text
templates/
└── index.html

static/
├── script.js
└── style.css
```

---

# `index.html`

The HTML file provides the structure of the AI Assistant interface.

It contains elements such as:

* Chat area
* Message input
* Send button
* Typing indicator
* Header

The page is served by Flask.

---

# `style.css`

This file controls the appearance of the application.

It is responsible for things such as:

* Layout
* Chat bubbles
* User messages
* AI messages
* Header
* Input area
* Buttons
* Animations
* Responsive styling

---

# `script.js`

The JavaScript file connects the frontend to the Flask backend.

It handles:

* Reading the user's message
* Sending messages to `/chat`
* Receiving the AI response
* Displaying messages
* Typing indicator
* Auto-resizing the input
* Enter-to-send
* Smooth scrolling
* Conversation ID

The browser stores the current conversation ID in:

```javascript
let conversationId = null;
```

When the first message is sent, the server creates a conversation ID.

The server sends it back:

```json
{
    "conversation_id": "chat_2026-08-09_15-30-20"
}
```

JavaScript stores this ID and sends it with future messages.

This allows multiple messages to belong to the same conversation.

---

# Configuration

## `config.py`

Configuration values are kept separately from the main application code.

The project currently uses configuration values such as:

```text
GROQ_API_KEY
MODEL
TEMPERATURE
MAX_COMPLETION_TOKENS
```

This allows the AI configuration to be changed without modifying the main chat logic.

---

# System Prompt

## `system_prompt.py`

The system prompt contains the instructions given to the AI before the conversation.

The purpose of the system prompt is to define how the assistant should behave.

The application sends the system prompt along with the conversation history.

Conceptually:

```text
System Prompt
      +
Conversation History
      ↓
      LLM
      ↓
AI Response
```

---

# Console Application

## `console_app.py`

Before building the Flask application, we created a console version of the AI assistant.

It allows the user to interact with the AI through the terminal.

Example:

```text
============================================================
          Console AI Assistant
============================================================
Type 'exit' to quit.

You: Hello
AI: Hello! How can I help you?

You: What is Python?
AI: Python is a programming language...
```

The console application helped us understand the basic AI/API flow before moving to Flask.

---

# Utilities

## `utils.py`

`utils.py` contains helper functions that can be reused by different parts of the application.

Keeping helper functions in a separate file prevents the same code from being repeated throughout the project.

This file will become more useful as the application grows.

---

# Logging

## `logger.py`

The project contains a logging module.

Logs are stored in:

```text
logs/
└── chatbot.log
```

Logging allows the application to record information about what is happening.

For example:

```text
Application started
Chat request received
Conversation loaded
AI response generated
Error occurred
```

Logging is different from displaying information to the user.

The user should receive a simple message, while the log can contain technical information useful for debugging.

---

# Requirements

The Python packages required by the project are stored in:

```text
requirements.txt
```

To install them:

```bash
pip install -r requirements.txt
```

---

# Environment Setup

It is recommended to use a Python virtual environment.

Create one:

```bash
python -m venv venv
```

Activate it on Linux:

```bash
source venv/bin/activate
```

Then install the requirements:

```bash
pip install -r requirements.txt
```

---

# API Key

The application requires a Groq API key.

The key should **not** be hard-coded into the source code or committed to GitHub.

Use an environment variable or the configuration method already used by the project.

For example:

```text
GROQ_API_KEY
```

Make sure your API key is kept private.

---

# Running the Application

Activate the virtual environment:

```bash
source venv/bin/activate
```

Start Flask:

```bash
python app.py
```

The Flask development server should start on:

```text
http://127.0.0.1:5000
```

Open that address in your browser.

---

# Testing the Current Application

## Test 1 — Open the Web Application

Open:

```text
http://127.0.0.1:5000
```

The AI Assistant interface should appear.

---

## Test 2 — Send a Message

Enter:

```text
Hello
```

The application should return an AI response.

---

## Test 3 — Test Conversation Memory

Send:

```text
My name is Mark.
```

Then send:

```text
What is my name?
```

The AI should remember the previous message and answer correctly.

---

## Test 4 — Check Saved Conversation

Open:

```text
conversations/
```

A JSON file should have been created.

Example:

```text
chat_2026-08-09_15-30-20.json
```

The file should contain the conversation messages.

---

# Current API

## `GET /`

Loads the main AI Assistant web page.

### Response

HTML page.

---

## `POST /upload`

Uploads a `.pdf` or `.docx` file, extracts its text, splits it into
chunks, and indexes those chunks in the vector store so `/chat` can
retrieve them.

### Request

`multipart/form-data` with a `file` field.

### Response

```json
{
    "message": "Document uploaded and indexed successfully",
    "document": {
        "loaded": true,
        "filename": "notes.pdf",
        "chunk_count": 33,
        "total_tokens": 9228,
        "char_count": 28322,
        "chunk_size": 180,
        "chunk_overlap": 40,
        "top_k": 4
    }
}
```

---

## `GET /document/status`

Returns the same `document` object shown above for whatever is
currently loaded (or `"loaded": false` if nothing has been uploaded
yet). Used by the frontend to restore the document panel on page load.

---

## `DELETE /document`

Clears the currently loaded document and its vector index.

---

## `GET /limits`

Returns the model's context window, used by the frontend to draw the
token-usage bar before any message has been sent.

```json
{ "context_window": 131072 }
```

---

## `POST /chat`

Sends a message to the AI. If a document is loaded, the most
relevant chunks are retrieved and the assistant answers only from
them; otherwise it falls back to the general-purpose system prompt.

### Request

```json
{ "message": "Hello" }
```

### Response

```json
{
    "response": "Hello! How can I help you?",
    "used_rag": false,
    "sources": [],
    "token_usage": {
        "prompt_tokens": 42,
        "context_window": 131072,
        "percent_used": 0.03
    }
}
```

When a document is loaded and the question is answered from it,
`used_rag` is `true` and `sources` lists the chunk index and
similarity score of each retrieved chunk, e.g.
`{"chunk_index": 12, "score": 0.83}`.

> **Note:** the request/response shapes above describe what the code
> actually does today. Conversation IDs and multi-turn memory are
> described elsewhere in this document as a design goal, but are not
> yet wired into `/chat` — see **Current Limitations** below.

---

# Retrieval-Augmented Generation (RAG)

This is how a document goes from an uploaded file to an answer:

```text
Upload (.pdf / .docx)
        ↓
Extract raw text  (pypdf / python-docx)
        ↓
Chunk the text     (rag/chunking.py)
        ↓
Embed each chunk   (TF-IDF, scikit-learn)
        ↓
Store in vector DB (Chroma, rag/vector_store.py)
        ↓
User asks a question
        ↓
Embed the question with the same TF-IDF vectorizer
        ↓
Retrieve the top-K most similar chunks
        ↓
Insert those chunks into the system prompt
        ↓
Ask the LLM to answer using ONLY those chunks
```

### Why TF-IDF instead of a neural embedding model?

Neural embedding models (e.g. `sentence-transformers`) need to
download model weights from the internet the first time they run,
which makes the app fragile on machines with restricted networks.
TF-IDF vectors are computed 100% locally with `scikit-learn`, need no
downloads, and work well for finding the chunks that share vocabulary
with a question — which is exactly what a single-document assistant
like this needs.

Chroma still does the real "vector database" work: storing the
vectors and running the similarity search. It's just handed
pre-computed TF-IDF vectors instead of generating its own embeddings.

### Only one document at a time

Uploading a new file replaces whatever was indexed before, same as
the original version of this project. The vector index lives in
memory for the lifetime of the Flask process — it is not persisted
to disk, so it resets when the server restarts.

### Configuration

All of this is tunable in `config.py`:

```text
RAG_CHUNK_SIZE      # target words per chunk (default: 180)
RAG_CHUNK_OVERLAP   # words repeated between chunks (default: 40)
RAG_TOP_K           # chunks retrieved per question (default: 4)
MODEL_CONTEXT_WINDOW  # used for the token-usage bar (131,072 for
                       # openai/gpt-oss-120b on Groq)
```

### Token usage in the UI

Since the exact tokenizer used by the hosted model isn't available
offline, `rag/token_utils.py` estimates tokens using the common
~4-characters-per-token rule of thumb. It's an approximation, not an
exact count, but it's accurate enough to give a real sense of how
much of the model's context window a request is using — the bar in
the document panel updates after every reply.

---

# Current Architecture

The current application can be understood as several layers.

```text
┌──────────────────────────────┐
│          Frontend            │
│                              │
│  HTML + CSS + JavaScript     │
└──────────────┬───────────────┘
               │
               │ HTTP
               ↓
┌──────────────────────────────┐
│           Flask              │
│                              │
│       page_routes.py         │
│       chat_routes.py         │
└──────────────┬───────────────┘
               │
               ↓
┌──────────────────────────────┐
│     Conversation Manager     │
│                              │
│  Create / Load / Save        │
└──────────────┬───────────────┘
               │
               ↓
┌──────────────────────────────┐
│          chat.py             │
│                              │
│      Groq API Client         │
└──────────────┬───────────────┘
               │
               ↓
┌──────────────────────────────┐
│            Groq              │
│                              │
│             LLM              │
└──────────────────────────────┘
```

---

# What We Have Learned

During the development of this application, we have worked with several important concepts:

### Python

* Functions
* Modules
* Imports
* JSON
* File handling
* Exception handling
* Environment/configuration
* Working with external APIs

### APIs

* API requests
* Request data
* Response data
* HTTP methods
* JSON request/response format

### Flask

* Flask application
* Routes
* Blueprints
* GET requests
* POST requests
* `request`
* `jsonify`
* Templates
* Static files

### AI / LLM

* LLM API
* System prompts
* User messages
* Assistant messages
* Conversation history
* Sending previous messages to an LLM
* Token limits
* Temperature

### Frontend

* HTML
* CSS
* JavaScript
* `fetch()`
* JSON
* DOM manipulation
* Async functions
* HTTP requests

### Project Structure

We also learned why a real project should not put everything inside one Python file.

Different parts of the application have different responsibilities.

```text
app.py
    ↓
Routes
    ↓
Application Logic
    ↓
AI / Data Handling
```

---

# Current Limitations

The current version is working, but it is still an early version of the application.

Some areas still need improvement.

### 1. Error Handling

The current error handling is basic.

The application needs better handling for:

* Groq API errors
* Network errors
* Invalid requests
* Missing data
* File errors
* Invalid conversation IDs

---

### 2. Conversation Memory Is Not Wired Into `/chat` Yet

`conversation_manager.py` can create, save, and load conversation
JSON files, and the console app / earlier design docs describe using
it for multi-turn memory — but the current `/chat` route does not
call it. Each request is answered independently, with no memory of
earlier turns in the same session. Wiring `conversation_manager`
into `chat.py` (loading prior turns, saving new ones, returning a
`conversation_id`) is the natural next step.

---

### 3. RAG Index Is In-Memory Only

The vector index built from an uploaded document lives in memory for
as long as the Flask process runs. Restarting the server clears it,
and the document has to be re-uploaded. There's also only ever one
active document — uploading a new file replaces the previous one
rather than adding to a growing library.

---

### 4. Token Counts Are Approximate

`rag/token_utils.py` estimates tokens with a ~4-characters-per-token
rule of thumb rather than the model's exact tokenizer, since the
exact tokenizer isn't available without a network download. The
token-usage bar is accurate enough to reason about the context
budget, but not exact.

---

### 5. Database

The application currently uses JSON files for conversation storage.

Later, we can move to a database such as SQLite.

---

### 6. Authentication

There is currently no user authentication.

The application is currently designed as a local personal assistant.

---

### 7. Testing

Automated tests still need to be added.

---

# Planned Development

The project will be developed step by step.

The next planned improvements are:

```text
Current Working Application
          ↓
Better Error Handling
          ↓
Better Logging
          ↓
Input Validation
          ↓
Conversation Management
          ↓
API Improvements
          ↓
Automated Testing
          ↓
Database
          ↓
Knowledge / Document Features
          ↓
Personal Knowledge Assistant
```

The final goal is to turn this into a **Personal Knowledge Assistant** that can work with the user's own information and documents.

---

# Development Philosophy

This project is being built step by step rather than creating everything at once.

Each new feature should:

1. Have a clear purpose
2. Use concepts already learned where possible
3. Be tested before moving forward
4. Keep the project structure clean
5. Avoid unnecessary complexity

The goal is not only to build the application, but also to understand **why each part exists and how the parts communicate with each other**.

---

# Project Status

### Working

* [x] Python AI assistant
* [x] Groq API integration
* [x] Console application
* [x] Flask application
* [x] Web interface
* [x] Flask routes
* [x] Separate route modules
* [x] Conversation manager (saving/loading conversation files; not yet wired into `/chat` — see Current Limitations)
* [x] JSON conversation storage
* [x] System prompt
* [x] Configurable model settings
* [x] Basic logging structure
* [x] Document upload (PDF + DOCX)
* [x] Document chunking
* [x] Local vector database (Chroma + TF-IDF embeddings)
* [x] Retrieval-Augmented Generation in `/chat`
* [x] Token-usage bar in the UI
* [x] Drag-and-drop document panel with remove button

<!-- ### Next

* [ ] Wire conversation memory into /chat
* [ ] Better error handling
* [ ] Better logging integration
* [ ] Better input validation
* [ ] Automated testing
* [ ] Improved project documentation
* [ ] Database storage
* [ ] Knowledge/document features
* [ ] Personal Knowledge Assistant features -->

---

# Author

**Mudassir Rehman**

This project is being developed as part of an AI/Software Engineering internship to learn Python, APIs, Flask, LLM integration, backend development, and AI application development.
