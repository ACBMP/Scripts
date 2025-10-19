from telegram.ext import Application
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import filters
import telegram
import logging
from botconfig import *
from util import *
db = connect()

def notify_player(player, mode):
    """
    Notify a player it's game time.

    :param player: player to notify
    :param mode: mode to play
    """
    message_player(player, f"{mode} time!")
    return

async def message_player(player, message):
    bot = telegram.Bot(token=telegram_token)
    await bot.sendMessage(chat_id=identify_player(db, player)["telegram_id"], text=message)
    return


def main():
    def start(update: Update, context: CallbackContext):
        context.bot.send_message(chat_id=update.effective_chat.id,
                text="Welcome to the Assassins' Network bot. To tie your account to your AN username, type /username [YOUR USERNAME HERE].")
        return
    
    
    def unknown(update: Update, context: CallbackContext):
        context.bot.send_message(chat_id=update.effective_chat.id,
                text="Sorry, I currently only support queue notifications.")
        return
    
    
    def username(update: Update, context: CallbackContext):
        player = " ".join(context.args)
        if player:
            try:
                player = identify_player(db, player)
            except:
                context.bot.send_message(chat_id=update.effective_chat.id,
                        text=f"Could not identify player {player['name']}. Please check that it matches the username on https://assassins.network/profiles.")
                return
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,
                    text=f"No username specified. Please try again.")
            return
        # we have no way of verifying users but luckily we're small enough it doesn't matter
        if player["telegram_id"] == "":
            db.players.update_one({"name": player["name"]}, {"$set": {"telegram_id": update.message.chat_id}})
            context.bot.send_message(chat_id=update.effective_chat.id,
                    text=f"Successfully tied chat to AN account: {player['name']}.")
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,
                    text=f"Could not tie to AN account {player['name']}, as it already has a Telegram account tied to it. Please contact an administrator for help.")
        return

    application = Application.builder().token(telegram_token).build()
    
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("username", username))
    application.add_handler(MessageHandler(filters.TEXT, unknown))
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    application.run_polling()

    return

if __name__ == "__main__":
    main()
