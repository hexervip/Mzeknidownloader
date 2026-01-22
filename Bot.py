import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp

TOKEN = '8261784470:AAF6tpvgOKihxMefRlSqqzTEsWDynR6v5Ug'

# Global cache for results
user_data_cache = {}

YDL_OPTIONS = {
    'format': 'm4a/bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
}

SEARCH_OPTIONS = {
    'quiet': True,
    'extract_flat': True,
    'force_generic_extractor': True,
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 **MZEKNI PRO DOWNLOADER**\nSearch a singer or paste a Link!")

async def download_and_send(message, url, title):
    try:
        def _sync_download():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        file_path = await asyncio.to_thread(_sync_download)
        
        # Ensure file exists before opening
        if os.path.exists(file_path):
            with open(file_path, 'rb') as audio:
                await message.reply_audio(audio, title=title)
            os.remove(file_path)
    except Exception as e:
        print(f"Download Error: {e}")

async def handle_mass_link(update, url, status_msg):
    await status_msg.edit_text("📦 Extracting Playlist info...")
    try:
        def _get_info():
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                return ydl.extract_info(url, download=False)
                
        info = await asyncio.to_thread(_get_info)
        entries = list(info.get('entries', []))
        await status_msg.edit_text(f"✅ Found {len(entries)} songs. Downloading...")
        
        for entry in entries:
            song_url = entry.get('url') or entry.get('webpage_url')
            if song_url:
                asyncio.create_task(download_and_send(update.message, song_url, entry.get('title', 'Unknown')))
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    user_id = update.effective_user.id
    status = await update.message.reply_text(f"🔍 Searching for '{query}'...")

    if any(x in query for x in ["youtube.com/", "youtu.be/", "list="]):
        return await handle_mass_link(update, query, status)

    try:
        def _sync_search():
            with yt_dlp.YoutubeDL(SEARCH_OPTIONS) as ydl:
                return ydl.extract_info(f"ytsearch100:{query}", download=False)['entries']

        results = await asyncio.to_thread(_sync_search)
        # Store using user_id as key
        user_data_cache[user_id] = {'results': results, 'query': query}
        await status.delete()
        await show_page(update, user_id, page=0)
    except Exception as e:
        await status.edit_text(f"❌ Search Error: {e}")

async def show_page(update, user_id, page=0):
    data = user_data_cache.get(user_id)
    if not data:
        # If cache is missing, notify user instead of crashing
        msg = "❌ Session expired. Please search again."
        if update.callback_query:
            await update.callback_query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return
    
    entries = data['results']
    start_idx, end_idx = page * 10, (page + 1) * 10
    current_batch = entries[start_idx:end_idx]

    text = f"🎵 **Results for:** {data['query']}\nPage {page + 1}\n\n"
    keyboard = []
    
    row = []
    for i, entry in enumerate(current_batch, 1):
        actual_num = start_idx + i
        # Truncate title for buttons to avoid errors
        clean_title = entry.get('title', 'Unknown')[:50]
        text += f"{actual_num}. {clean_title}...\n"
        row.append(InlineKeyboardButton(f"{actual_num}", callback_data=f"dl_{actual_num-1}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)

    nav_row = []
    if page > 0: nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{page-1}"))
    if end_idx < len(entries): nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
    
    keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("📥 DOWNLOAD THIS PAGE", callback_data=f"masspage_{page}")])
    
    markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()
    
    # 1. Check if user still has data in cache
    if user_id not in user_data_cache:
        await query.edit_message_text("⚠️ Result expired. Please search again.")
        return

    data = query.data
    if data.startswith("page_"):
        await show_page(update, user_id, page=int(data.split("_")[1]))
    
    elif data.startswith("dl_"):
        idx = int(data.split("_")[1])
        song = user_data_cache[user_id]['results'][idx]
        asyncio.create_task(download_and_send(query.message, song['url'], song['title']))
    
    elif data.startswith("masspage_"):
        page = int(data.split("_")[1])
        start_idx, end_idx = page * 10, (page + 1) * 10
        batch = user_data_cache[user_id]['results'][start_idx:end_idx]
        
        await query.message.reply_text(f"📦 Queuing {len(batch)} songs...")
        for song in batch:
            asyncio.create_task(download_and_send(query.message, song['url'], song['title']))

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🚀 PRO Bot (REPAIRED & FAST) Running!")
    app.run_polling()

if __name__ == '__main__':
    main()
    
