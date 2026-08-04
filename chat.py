from groq import Groq

from config import (
    GROQ_API_KEY,
    MODEL,
    TEMPERATURE,
    MAX_COMPLETION_TOKENS,
)

client = Groq(api_key=GROQ_API_KEY)


def get_ai_response(messages):

    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        stream=True
    )

    complete_response = ""

    print("\nAI: ", end="", flush=True)
    #in the aobe line of code the the flush function is used to force the output to be written to the console immediately, rather than being buffered. 
    
    for chunk in stream:

        content = chunk.choices[0].delta.content

        if content:

            print(content, end="", flush=True)

            complete_response += content

    print()

    return complete_response