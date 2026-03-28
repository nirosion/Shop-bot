import os
import json
import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# הגדרות
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

logging.basicConfig(level=logging.INFO)

# שמירת רשימה בקובץ
LIST_FILE = "shopping_list.json"

def load_list():
    if os.path.exists(LIST_FILE):
        with open(LIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_list(data):
    with open(LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def format_list(data):
    if not data:
        return "הרשימה ריקה 🛒"
    text = "🛒 *רשימת הקניות:*\n\n"
    for category, items in data.items():
        text += f"*{category}*\n"
        for item in items:
            text += f"  • {item}\n"
        text += "\n"
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "שלום! אני בוט רשימת הקניות 🛒\n\n"
        "פשוט כתבו לי מה לקנות ואני אוסיף לרשימה!\n\n"
        "פקודות:\n"
        "/list — הצג את הרשימה\n"
        "/clear — נקה את הרשימה\n"
        "/remove [מוצר] — הסר מוצר"
    )

async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_list()
    await update.message.reply_text(format_list(data), parse_mode="Markdown")

async def clear_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_list({})
    await update.message.reply_text("הרשימה נוקתה! ✨ מתחילים מחדש.")

async def remove_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("כתוב: /remove [שם המוצר]")
        return
    
    item_to_remove = " ".join(context.args).strip()
    data = load_list()
    removed = False
    
    for category in list(data.keys()):
        if item_to_remove in data[category]:
            data[category].remove(item_to_remove)
            removed = True
            if not data[category]:
                del data[category]
    
    if removed:
        save_list(data)
        await update.message.reply_text(f"✅ הוסרה: {item_to_remove}")
    else:
        await update.message.reply_text(f"לא מצאתי את \"{item_to_remove}\" ברשימה.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    sender = update.message.from_user.first_name or "מישהו"
    
    current_list = load_list()
    
    prompt = f"""אתה עוזר רשימת קניות. המשתמש {sender} אמר: "{user_text}"

הרשימה הנוכחית:
{json.dumps(current_list, ensure_ascii=False)}

המשימה שלך:
1. זהה את כל המוצרים שצוינו
2. שייך כל מוצר לקטגוריה מתאימה בעברית (פירות וירקות, מוצרי חלב, בשר ודגים, לחם ומאפים, שימורים ויבשים, משקאות, חטיפים וממתקים, ניקיון ובית, טיפוח, קפואים, תבלינים, אחר)
3. אם מוצר כבר קיים ברשימה — אל תוסיף שוב
4. החזר JSON בלבד, ללא שום טקסט אחר:
{{
  "updated_list": {{"קטגוריה": ["מוצר1", "מוצר2"]}},
  "added": ["רשימת המוצרים שנוספו"],
  "reply": "תגובה קצרה ונחמדה בעברית"
}}"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        # נקה backticks אם יש
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        
        save_list(parsed["updated_list"])
        
        added = parsed.get("added", [])
        reply = parsed.get("reply", "נוסף לרשימה!")
        
        if added:
            items_text = "، ".join(added)
            await update.message.reply_text(f"{reply}\n\nנוסף: {items_text} ✅")
        else:
            await update.message.reply_text(reply)
            
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("אופס, משהו השתבש. נסה שוב 🙏")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", show_list))
    app.add_handler(CommandHandler("clear", clear_list))
    app.add_handler(CommandHandler("remove", remove_item))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("הבוט פועל! 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
