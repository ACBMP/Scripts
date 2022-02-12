from telegram.ext.updater import Updater
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters
import logging
from botconfig import *
from util import *

updater = Updater(telegram_token, use_context=True)
dispatcher = updater.dispatcher
db = connect()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

chatids = {}

def start(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
            text="Welcome to the Assassins' Network bot. To tie your account to your AN username, type /username.")
    return

def unknown(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id,
            text="Sorry, I currently only support queue notifications.")
    return

def username(update: Update, context: CallbackContext):
    player = " ".join(context.args)
    try:
        player = identify_player(db, player)["name"]
    except:
        context.bot.send_message(chat_id=update.effective_chat.id,
                text=f"Could not identify player {player}. Please check that it matches the username on https://assassins.network/profiles.")
        return
    db.players.update_one({"name": player}, {"$set": {"telegram_id": update.message.chat_id}})
    context.bot.send_message(chat_id=update.effective_chat.id,
            text=f"Successfully tied chat to AN account: {player}.")
    return

def notify_player(player, mode):
    updater.bot.send_message(chat_id=identify_player(player)["telegram_id"],
            text=f"{mode} time!")
    return

def test_notify(update: Update, context: CallbackContext):
    notify_player("Dellpit", "Escort")
    return

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("username", username))
dispatcher.add_handler(CommandHandler("test", test_notify))
dispatcher.add_handler(MessageHandler(Filters.text, unknown))
dispatcher.add_handler(MessageHandler(Filters.command, unknown))

updater.start_polling()
updater.idle()

