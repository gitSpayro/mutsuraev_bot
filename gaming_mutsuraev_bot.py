import requests
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# 🔑 API-ключ OpenRouter
API_KEY = "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"

# 🔑 API-ключ Telegram бота
TELEGRAM_BOT_TOKEN = "7965923857:AAE81U_myTerQMTxlnNJjM1-2j7xOISLu0c"

# 📌 Используемая языковая модель DeepSeek R1 Free
MODEL = "deepseek/deepseek-r1:free"

# 📌 Оптимизированные параметры для скорости и точности
GENERATION_PARAMS = {
    "temperature": 0.5,          # Баланс точности и вариативности
    "top_p": 0.9,                # Ограничение случайности
    "top_k": 1,                  # Минимальный выбор токенов → высокая точность
    "repetition_penalty": 1.1,   # Снижение повторов
    "frequency_penalty": 0.5,    # Уменьшение повторяемости слов
    "presence_penalty": 0.2,     # Минимальное поощрение новизны
    "max_tokens": 512            # Ограничение длины ответа
}

# 📌 Словарь для хранения истории сообщений (контекста) по чатам
chat_histories = {}

def chat_request(chat_id, user_message):
    """Отправляет запрос в OpenRouter AI с учетом истории сообщений."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Берем историю чата или создаем новую
    chat_histories.setdefault(chat_id, [])
    
    # Добавляем новое сообщение пользователя в историю
    chat_histories[chat_id].append({"role": "user", "content": user_message})

    # Ограничиваем историю до 6 последних сообщений (баланс между памятью и скоростью)
    chat_histories[chat_id] = chat_histories[chat_id][-6:]

    # Создаем запрос с текущей историей
    data = {
        "model": MODEL,
        "messages": chat_histories[chat_id],  # Передаем всю историю диалога
        **GENERATION_PARAMS
    }

    print(f"\n[LOG] Отправка запроса к OpenRouter: {json.dumps(data, indent=2)}")

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        
        print(f"[LOG] Ответ API (статус {response.status_code}): {response.text[:200]}...")  # Ограничиваем вывод

        if response.status_code != 200:
            return f"Ошибка API: {response.status_code} {response.text}"

        response_json = response.json()
        
        if "choices" in response_json and response_json["choices"]:
            content = response_json["choices"][0]["message"].get("content", "").strip()
            
            # Добавляем ответ бота в историю
            chat_histories[chat_id].append({"role": "assistant", "content": content})
            chat_histories[chat_id] = chat_histories[chat_id][-6:]  # Ограничиваем до 6 сообщений

            return content if content else "Ошибка: пустой ответ от модели."
        else:
            return "Ошибка: API вернул неожиданный формат данных."

    except requests.RequestException as e:
        print(f"[ERROR] Ошибка соединения с API: {e}")
        return f"Ошибка соединения с API: {str(e)}"

async def start(update: Update, context: CallbackContext):
    """Отправляет приветственное сообщение при старте и очищает историю."""
    chat_id = update.message.chat_id
    chat_histories[chat_id] = []  # Очищаем историю при новом старте
    print(f"[LOG] Пользователь {chat_id} отправил /start (история сброшена)")
    await update.message.reply_text("Привет! Я бот на DeepSeek R1. Напиши мне в ЛС или тегни в группе (@меня), либо ответь на мое сообщение кнопкой 'Ответить'!")

async def handle_message(update: Update, context: CallbackContext):
    """Обрабатывает сообщения в ЛС и группах (если бот тегнули или на него ответили)."""
    user_text = update.message.text
    chat_type = update.message.chat.type
    chat_id = update.message.chat_id
    bot_username = context.bot.username

    print(f"[LOG] Новое сообщение в {chat_type} от {chat_id}: {user_text}")

    # Проверяем, ответили ли на сообщение бота (reply_to_message)
    is_reply_to_bot = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id if update.message.reply_to_message else False

    # Проверяем, в каком чате бот получил сообщение
    if chat_type == "private":
        print(f"[LOG] Сообщение из ЛС, бот отвечает.")
        response = chat_request(chat_id, user_text)
        await update.message.reply_text(response)
    
    elif chat_type in ["group", "supergroup"]:
        if f"@{bot_username}" in user_text or is_reply_to_bot:
            print(f"[LOG] Бота упомянули или ответили на его сообщение в группе, бот отвечает.")
            clean_text = user_text.replace(f"@{bot_username}", "").strip()  # Убираем упоминание
            response = chat_request(chat_id, clean_text)
            await update.message.reply_text(response)
        else:
            print(f"[LOG] Сообщение в группе без упоминания или ответа боту, бот игнорирует.")

async def error_handler(update: Update, context: CallbackContext):
    """Логирует ошибки."""
    print(f"[ERROR] Ошибка: {context.error}")

def main():
    """Запуск бота."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))  
    app.add_error_handler(error_handler)

    print("[LOG] Бот запущен! Работает в ЛС, в группах при упоминании и при ответе на его сообщение.")
    app.run_polling()

if __name__ == "__main__":
    main()
