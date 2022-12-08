import asyncio
import logging
import os

import telegram.constants as constants
from asyncChatGPT.asyncChatGPT import Chatbot as ChatGPT3Bot
from telegram import Update, Chat
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()

users_file = open('./users.txt', 'r+')
groups_file  = open('./groups.txt', 'r+')
whitelist_mode = (os.getenv('WHITELIST_MODE') != None) & (len(os.getenv('WHITELIST_MODE')) != 0)
bot_owner_id = int(os.getenv('OWNER_ID'))
bot_owner_username = os.getenv('OWNER_USERNAME')

class ChatGPT3TelegramBot:
    """
    Class representing a Chat-GPT3 Telegram Bot.
    """
    def __init__(self, config: dict, gpt3_bot: ChatGPT3Bot):
        """
        Initializes the bot with the given configuration and GPT-3 bot object.
        :param config: A dictionary containing the bot configuration
        :param gpt3_bot: The GPT-3 bot object
        """
        self.config = config
        self.gpt3_bot = gpt3_bot
        self.disallowed_message = f'Sorry, you are not allowed to use this bot, please contact @{bot_owner_username} to request permissons.\n\n You can check out the source code at ' \
                                   'https://github.com/n3d1117/chatgpt-telegram-bot'

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Shows the help menu.
        """
        await update.message.reply_text("/start - Start the bot\n"
                                        "/reset - Reset conversation\n"
                                        "/allow - Add a user or group to whitelist\n"
                                        "/help - Help menu\n\n"
                                        "Open source at https://github.com/n3d1117/chatgpt-telegram-bot",
                                        disable_web_page_preview=True)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handles the /start command.
        """
        if not self.is_allowed(update):
            logging.info(f'User {update.message.from_user.name} is not allowed to start the bot')
            await self.send_disallowed_message(update)
            return

        logging.info('Bot started')
        await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a Chat-GPT3 Bot, please talk to me!")

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Resets the conversation.
        """
        if not self.is_allowed(update):
            logging.info(f'User {update.message.from_user.name} is not allowed to reset the bot')
            await self.send_disallowed_message(update)
            return

        logging.info('Resetting the conversation...')
        self.gpt3_bot.reset_chat()
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Done!")

    async def allow(self, update: Update):
        """
        Add user to whitelist
        """
        if not whitelist_mode:
            await update.message.reply_text('Whitelist mode is off.')
            return
        if update.message.from_user.id != bot_owner_id:
            await update.message.reply_text('You are not allowed to use this commmand.')
            return
        if update.message.reply_to_message != None:
            users_file.writelines(list(str(update.message.reply_to_message.from_user.id) + '\n'))
        elif len(update.message.text.split(' ')) > 1:
            param = update.message.text.split(' ')[1]
            if param == 'group':
                if update.message.chat.type == Chat.GROUP or update.message.chat.type == Chat.SUPERGROUP:
                    groups_file.writelines(list(str(update.message.chat.id) + '\n'))
                    await update.message.reply_text('Added this group to whiselist.')
                else:
                    await update.message.reply_text('Current chat is not a group.')
                return
            else:
                users_file.writelines(list(update.message.text.split(' ')[1] + '\n'))
        else:
            await update.message.reply_text('Please specify a user or group first.')
            return
        await update.message.reply_text('Added the user to whitelist.')
        return

    async def send_typing_periodically(self, update: Update, context: ContextTypes.DEFAULT_TYPE, every_seconds):
        """
        Sends the typing action periodically to the chat
        """
        while True:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
            await asyncio.sleep(every_seconds)

    async def prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        React to incoming messages and respond accordingly.
        """
        if not self.is_allowed(update):
            logging.info(f'User {update.message.from_user.name} is not allowed to use the bot')
            await self.send_disallowed_message(update)
            return

        logging.info(f'New message received from user {update.message.from_user.name}')

        # Send "Typing..." action periodically every 4 seconds until the response is received
        typing_task = asyncio.get_event_loop().create_task(
            self.send_typing_periodically(update, context, every_seconds=4)
        )
        response = await self.get_chatgpt_response(update.message.text)
        typing_task.cancel()

        await update.message.reply_text(
            text=response['message'],
            parse_mode=constants.ParseMode.MARKDOWN
        )

    async def get_chatgpt_response(self, message) -> dict:
        """
        Gets the response from the ChatGPT APIs.
        """
        try:
            response = await self.gpt3_bot.get_chat_response(message)
            return response
        except Exception as e:
            logging.info(f'Error while getting the response: {str(e)}')
            return {"message": "I'm having some trouble talking to you, please try again later."}

    async def send_disallowed_message(self, update: Update):
        """
        Sends the disallowed message to the user.
        """
        await update.message.reply_text(
            text=self.disallowed_message,
            disable_web_page_preview=True
        )

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handles errors in the telegram-python-bot library.
        """
        logging.debug(f'Exception while handling an update: {context.error}')
        report=f"""
        Error occured when handling update:

        <pre>
        {context.error}
        </pre>
        """
        await context.bot.send_message(
            chat_id=bot_owner_id,
            text=report,
            parse_mode=constants.ParseMode.HTML
        )

    def is_allowed(self, update: Update) -> bool:
        """
        Checks if the user is allowed to use the bot.
        """
        if not whitelist_mode:
            return True
        users_file.seek(0)
        users = users_file.read().split('\n')
        groups_file.seek(0)
        groups = groups_file.read().split('\n')
        if str(update.message.from_user.id) in users or str(update.message.chat.id) in groups:
            return True
        return False

    def run(self):
        """
        Runs the bot indefinitely until the user presses Ctrl+C
        """
        application = ApplicationBuilder().token(self.config['token']).build()

        application.add_handler(CommandHandler('start', self.start))
        application.add_handler(CommandHandler('reset', self.reset))
        application.add_handler(CommandHandler('allow', self.allow))
        application.add_handler(CommandHandler('help', self.help))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.prompt))

        application.add_error_handler(self.error_handler)

        application.run_polling()
