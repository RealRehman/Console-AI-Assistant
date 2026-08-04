from chat import get_ai_response
from config import SYSTEM_PROMPT
from logger import logger
from utils import print_banner, get_user_input
from conversation_manager import save_conversation


# Store conversation history
messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    }
]


def main():

    print_banner()

    while True:

        user_input = get_user_input()

        if user_input.lower() == "exit":

            filename = save_conversation(messages)

            print(f"\nConversation saved to:\n{filename}")

            logger.info(f"Conversation saved: {filename}")

            print("\nGoodbye! 👋")

            break

        logger.info(f"USER: {user_input}")

        messages.append(
            {
                "role": "user",
                "content": user_input
            }
        )

        try:

            ai_reply = get_ai_response(messages)

            print(f"\nAI: {ai_reply}\n")

            logger.info(f"AI: {ai_reply}")

            messages.append(
                {
                    "role": "assistant",
                    "content": ai_reply
                }
            )

        except Exception as e:

            logger.error(str(e))

            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()