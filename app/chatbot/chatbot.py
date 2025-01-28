import os
from dotenv import load_dotenv
from hugchat import hugchat
from hugchat.login import Login


class HuggingChatWrapper:
    def __init__(self):
        """Initialize the HuggingChatWrapper class and load environment variables."""
        # Load environment variables
        load_dotenv()

        # Fetch environment variables
        self.__email = os.getenv("HUGGINGFACE_EMAIL")
        self.__password = os.getenv("HUGGINGFACE_PASSWORD")
        self.__cookie_path_dir = os.getenv("HUGGINGFACE_COOKIE_DIR")

        if not self.__email or not self.__password:
            raise ValueError("Missing HUGGINGFACE_EMAIL or HUGGINGFACE_PASSWORD in environment variables.")

        self._chatbot_instance = None  # Singleton instance placeholder
        print("initialized NEW HuggingChatWrapper")


    def get_chatbot(self) -> hugchat.ChatBot:
        """Initialize and return a singleton instance of the ChatBot."""
        if self._chatbot_instance is None:
            try:
                # Authenticate and store the cookies
                sign = Login(self.__email, self.__password)
                cookies = sign.login()
                self._chatbot_instance = hugchat.ChatBot(
                    cookies=cookies.get_dict(),
                    default_llm="meta-llama/Llama-3.3-70B-Instruct"
                )
                print("initialized a NEW hugchat ChatBot")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize ChatBot: {e}")
        return self._chatbot_instance