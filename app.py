from groq import Groq
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create Groq client
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# Conversation history
messages = [
    {
        "role": "system",
        "content": "You are a helpful AI assistant."
    }
]

print("=" * 50)
print("      Welcome to AI Chatbot")
print("Type 'exit' to quit.")
print("=" * 50)

while True:

    user_input = input("\nYou: ").strip()

    if user_input.lower() == "exit":
        print("\nGoodbye! ")
        break

    # Save user message
    messages.append({
        "role": "user",
        "content": user_input
    })

    try:

        # Send entire conversation to Groq
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_completion_tokens=500
        )

        # Extract AI response
        ai_reply = response.choices[0].message.content

        # Print AI response
        print(f"\nAI: {ai_reply}")

        # Save AI response
        messages.append({
            "role": "assistant",
            "content": ai_reply
        })

    except Exception as e:
        print(f"\nError: {e}")