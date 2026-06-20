import os
import time
import requests
import subprocess
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Render Environment Variables
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

CHANNELS = {}
index_data = []

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("👋 Hello! Main ek Course Uploader Bot hoon.\n\n1. Pehle `/add_channel <Channel_ID> <Name>` karke channel add karein.\n2. Phir mujhe apni .txt file bhejein.")

@app.on_message(filters.command("add_channel"))
async def add_channel(client, message):
    try:
        _, ch_id, ch_name = message.text.split(" ", 2)
        CHANNELS[ch_name] = int(ch_id)
        await message.reply_text(f"✅ Channel '{ch_name}' successfully add ho gaya!")
    except:
        await message.reply_text("❌ Galat format. Aise likhein:\n`/add_channel -1001234567890 MyChannelName`")

@app.on_message(filters.document & filters.private)
async def handle_txt_file(client, message):
    if not message.document.file_name.endswith(".txt"):
        return await message.reply_text("⚠️ Kripya sirf .txt file bhejein.")
    
    if not CHANNELS:
        return await message.reply_text("❌ Pehle `/add_channel` command se koi channel add karein.")

    file_path = await message.download()
    
    buttons = []
    for name, ch_id in CHANNELS.items():
        buttons.append([InlineKeyboardButton(name, callback_data=f"upload_{ch_id}_{file_path}")])
    
    await message.reply_text(
        "📂 Aap is file ka course kis channel me upload karna chahte hain?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex(r"^upload_"))
async def process_file(client, callback_query):
    data = callback_query.data.split("_", 2)
    target_channel = int(data[1])
    file_path = data[2]
    
    await callback_query.message.edit_text("⏳ Uploading shuru ho rahi hai... Kripya wait karein.")
    
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    global index_data
    index_data = []

    for line in lines:
        line = line.strip()
        if not line: continue
        
        try:
            # File name aur link ko alag karna (Peeche se pehla space)
            name, link = line.rsplit(" ", 1)
        except:
            continue

        success = False
        # Retry System: 3 baar try karega
        for attempt in range(3):
            try:
                msg = await callback_query.message.reply_text(f"📥 Downloading:\n**{name}**\n*(Attempt: {attempt + 1}/3)*")
                
                if link.endswith(".pdf"):
                    pdf_path = f"{name}.pdf".replace("/", "_")
                    response = requests.get(link)
                    with open(pdf_path, "wb") as pdf_file:
                        pdf_file.write(response.content)
                    
                    sent_msg = await client.send_document(target_channel, document=pdf_path, caption=name)
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                    
                else:
                    video_path = f"{name}.mp4".replace("/", "_")
                    # m3u8 ya mp4 ko yt-dlp aur ffmpeg se download karna
                    command = f'yt-dlp -o "{video_path}" "{link}"'
                    subprocess.run(command, shell=True, check=True)
                    
                    sent_msg = await client.send_video(target_channel, video=video_path, caption=name)
                    if os.path.exists(video_path):
                        os.remove(video_path)

                # Indexing ke liye ID save karna
                index_data.append({"name": name, "msg_id": sent_msg.id, "channel": target_channel})
                await msg.delete()
                success = True
                time.sleep(5) # Telegram spams se bachne ke liye thoda delay
                break
                
            except Exception as e:
                await msg.edit_text(f"❌ Error in {name}: {e}\nRetrying in 3 seconds...")
                time.sleep(3)
                
        if not success:
            await client.send_message(callback_query.message.chat.id, f"⚠️ FAILED (3 tries): {name}\nLink: {link}")

    # Pura upload hone ke baad Index message bhejna
    if index_data:
        index_text = "📚 **Course Index**\n\n"
        chan_id_str = str(target_channel).replace("-100", "") 
        for item in index_data:
            index_text += f"▪️ [{item['name']}](https://t.me/c/{chan_id_str}/{item['msg_id']})\n"
        
        await client.send_message(target_channel, index_text, disable_web_page_preview=True)
        await callback_query.message.reply_text("✅ Course successfully upload ho gaya aur Index ban gaya!")


# ==========================================
# --- RENDER KE LIYE DUMMY WEB SERVER ---
# ==========================================
web_server = Flask(__name__)

@web_server.route('/')
def home():
    return "Bot is Alive and Running on Render!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_server.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Web server ko background thread me chalana
    threading.Thread(target=run_web, daemon=True).start()
    # Telegram Bot ko start karna
    print("Bot is starting...")
    app.run()
