from telegram.ext import Updater
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
    bot = telegram.Bot(token=telegram_token)
    bot.sendMessage(chat_id=identify_player(db, player)["telegram_id"],
            text=f"{mode} time!")
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

    updater = Updater(telegram_token, use_context=True)
    dispatcher = updater.dispatcher
    
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("username", username))
    dispatcher.add_handler(MessageHandler(filters.TEXT, unknown))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))
    
    updater.start_polling()
    updater.idle()

    return

if __name__ == "__main__":
    main()
