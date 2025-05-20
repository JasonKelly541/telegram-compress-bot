import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from PIL import Image
import zipfile

# Pakai variabel environment
TOKEN = os.getenv("BOT_TOKEN")

WAIT_IMAGES, WAIT_ZIPNAME = range(2)
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Kirim hingga 10 gambar.\nJika sudah selesai, ketik /done."
    )
    user_sessions[update.effective_user.id] = []
    return WAIT_IMAGES

async def collect_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions.setdefault(user_id, [])

    if len(user_sessions[user_id]) >= 10:
        await update.message.reply_text("Sudah 10 gambar. Ketik /done.")
        return WAIT_IMAGES

    photo = update.message.photo[-1]
    file = await photo.get_file()
    raw = f"{photo.file_unique_id}_raw.jpg"
    comp = f"compressed_{photo.file_unique_id}.jpg"

    await file.download_to_drive(raw)
    with Image.open(raw) as img:
        img.save(comp, "JPEG", quality=30)
    os.remove(raw)
    user_sessions[user_id].append(comp)

    await update.message.reply_text(f"✅ Gambar disimpan ({len(user_sessions[user_id])}/10).")
    return WAIT_IMAGES

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ketik nama file ZIP (tanpa .zip):")
    return WAIT_ZIPNAME

async def make_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    zip_name = update.message.text.strip() + ".zip"
    images = user_sessions.get(user_id, [])

    if not images:
        await update.message.reply_text("Tidak ada gambar.")
        return ConversationHandler.END

    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for img in images:
            zipf.write(img, arcname=os.path.basename(img))

    with open(zip_name, 'rb') as f:
        await update.message.reply_document(f, filename=zip_name)

    for img in images:
        os.remove(img)
    os.remove(zip_name)
    user_sessions.pop(user_id, None)
    await update.message.reply_text("ZIP selesai dikirim 🎉")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_sessions.pop(update.effective_user.id, None)
    await update.message.reply_text("❌ Dibatalkan.")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAIT_IMAGES: [
                MessageHandler(filters.PHOTO, collect_images),
                CommandHandler("done", done)
            ],
            WAIT_ZIPNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, make_zip)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    app.run_polling()
