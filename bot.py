from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, run_async
import requests
import emojis
import logging
import sys
import os
import threading
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# in next file
link = "https://z1.fm/mp3/search?keywords="

# Enabling logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Getting mode, so we could define run function for local and Heroku setup
mode = os.getenv("MODE")
TOKEN = os.getenv("TOKEN")
if mode == "dev":
    def run(updater):
        updater.start_polling()
elif mode == "prod":
    def run(updater):
        PORT = int(os.environ.get("PORT", "8443"))
        HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TOKEN)
        updater.bot.set_webhook("https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, TOKEN))
else:
    logger.error("No MODE specified!")
    sys.exit(1)


def send_audio(chat_id, url, bot):
    bot.send_audio(chat_id=chat_id, audio=url)


# in next file
def get_url(tag):
    head = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "cookie": "ZvcurrentVolume=100; __cfduid=de713507fd3f1d7c79fbe9024f6782b511565594675; PHPSESSID=3s6b64bf32jdaoms7dhis9b4f4; zvAuth=1; zvLang=0; ZvcurrentVolume=100; _zvBoobs_=%2F%2F_-%29if-modified-since: Mon, 12 Aug 2019 11:20:00 GMT",
        "referer": link + str(tag.encode('UTF-8')),
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36",
        "x-pjax": "true",
        "x-requested-with": "XMLHttpRequest"
    }
    # head["refer"] = link + str(tag.encode('UTF-8'))
    # head["refer"] = link + tag
    soup_link = requests.get(link + tag, headers=head).text
    soup = BeautifulSoup(soup_link, "html.parser")
    content = soup.find_all("div", {"class": "song song-xl"})
    data = {}
    index = 0
    for song in content:
        try:
            index = index + 1
            if index == 11:
                index = 1
            url = song.find('span', {'data-tool': 'tooltip'})['data-url']
            name = song.find('span', {'class': 'song-play btn4 play'})['data-title']
            duration = song.find('span', {'class': 'song-time'}).text

            data.update({str(index) + '. ' + name + duration: 'https://z1.fm' + url})

        except Exception:
            continue
    return data


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


@run_async
def button(bot, update):
    # print(tag)
    # bot.send_chat_action(chat_id=update.effective_user.id, action=telegram.ChatAction.TYPING)
    query = update.callback_query
    # print(query.data)
    # print([u.message.text for u in update
    # print(query.message.message_id)
    if query.data == '0':
        bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    elif 'https' in query.data:
        bot.send_audio(chat_id=query.message.chat_id, audio=query.data)
    elif query.data.split(',')[1] in [str(x) for x in range(1, 6)]:
        callback = query.data.split(',')
        tag = callback[0]
        page_number = callback[1]
        right = tag + ',' + str(int(page_number) + 1)
        left = tag + ',' + str(int(page_number) - 1)
        if page_number == '1':

            footer_buttons = [InlineKeyboardButton(emojis.encode(':arrow_left:'), callback_data=1),
                              InlineKeyboardButton(emojis.encode(':x:'), callback_data=0),
                              InlineKeyboardButton(emojis.encode(':arrow_right:'), callback_data=right)]
        elif page_number == '5':

            footer_buttons = [InlineKeyboardButton(emojis.encode(':arrow_left:'), callback_data=left),
                              InlineKeyboardButton(emojis.encode(':x:'), callback_data=0),
                              InlineKeyboardButton(emojis.encode(':arrow_right:'), callback_data=5)]
        elif page_number == '2' or page_number == '3' or page_number == '4':
            footer_buttons = [InlineKeyboardButton(emojis.encode(':arrow_left:'), callback_data=left),
                              InlineKeyboardButton(emojis.encode(':x:'), callback_data=0),
                              InlineKeyboardButton(emojis.encode(':arrow_right:'), callback_data=right)]
        data = get_url(tag)
        url = list(data.values())
        song = list(data.keys())
        button_list = [InlineKeyboardButton(str(index + 1), callback_data=x) for index, x in
                       enumerate(url[10 * (int(page_number) - 1): 10 * (int(page_number))])]
        names = '\n'.join(song[10 * (int(page_number) - 1): 10 * (int(page_number))])

        reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=5, footer_buttons=footer_buttons))

        bot.edit_message_text(text=names, chat_id=query.message.chat_id, message_id=query.message.message_id,
                              reply_markup=reply_markup)
    else:
        threading.Thread(target=send_audio, args=(query.message.chat_id, query.data, bot,)).start()


def start(bot, update):
    logger.info("User {} started bot".format(update.effective_user["id"]))
    update.message.reply_text(
        "I'm a bot, Nice to meet you!\nJust send me an artist and/or a song name and I will find music for you!")


def stop(bot, update):
    update.message.reply_text("I'm a bot, Why you bully me?")


def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="Unknown command: " + update.message.text + ". Call /help for a list of available commands.")


def help_me(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text="Commands\nJust send me an artist and/or a song name and I will find music for you!\n/start — bot hello\n/stop - bot bye\n/about — information about author")


def about(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="GitHub: https://github.com/kihaev \nContact: @yuranusss")


@run_async
def send_text(bot, update):
    # bot.send_chat_action(chat_id=update.effective_user.id, action=telegram.ChatAction.TYPING)

    tag = update.message.text
    # Data
    data = get_url(tag)
    if data == {}:
        bot.send_message(chat_id=update.message.chat_id, text="Sorry, nothing was found")
    url = list(data.values())
    song = list(data.keys())
    names = '\n'.join(song[:10])
    # change to data {}
    button_list = [InlineKeyboardButton(str(index + 1), callback_data=x) for index, x in enumerate(url[:10])]

    footer_buttons = [InlineKeyboardButton(emojis.encode(':arrow_left:'), callback_data=1),
                      InlineKeyboardButton(emojis.encode(':x:'), callback_data=0),
                      InlineKeyboardButton(emojis.encode(':arrow_right:'), callback_data=tag + ',2')]

    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=5, footer_buttons=footer_buttons))

    bot.send_message(chat_id=update.message.chat_id, text=names, reply_markup=reply_markup)


def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('stop', stop))
    dp.add_handler(CommandHandler('help', help_me))
    dp.add_handler(CommandHandler('about', about))
    dp.add_handler(MessageHandler(Filters.text, send_text))
    dp.add_handler(MessageHandler(Filters.command, unknown))
    dp.add_handler(CallbackQueryHandler(button))
    run(updater)
    updater.idle()


if __name__ == '__main__':
    main()
