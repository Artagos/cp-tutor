# Load a local .env (gitignored) if present, so GEMINI_API_KEY and friends can
# live in a file instead of being exported by hand. No-op if python-dotenv
# isn't installed or there's no .env.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass
