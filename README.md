# Telegram Bot Example

A minimal Telegram bot using `python-telegram-bot` and environment variables.

## Setup

1. Install dependencies:
    ```
    pip install -r requirements.txt
    ```

2. Create a `.env` file based on `.env.example` and fill in your secrets:
    ```
    cp .env.example .env
    # Edit .env and add your Telegram token and chat ID
    ```

3. Run the bot:
    ```
    python bot.py
    ```

## Deployment

You can deploy this bot on Railway, Oracle Cloud, or any VPS.
- **For Railway:** Set environment variables in the dashboard (`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`).
- **For other platforms:** Use the `.env` file or set environment variables as appropriate.

## Security Note

**Never commit your actual `.env` file or any real secrets to a public repository.**