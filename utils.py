from dotenv import load_dotenv
import os

load_dotenv()

DEBUG = os.getenv("DEBUG")


def debug_print(msg):
    if DEBUG:
        print(f"DEBUG: {msg}")
