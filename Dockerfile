FROM python:3.10-slim

# FFmpeg install karna zaroori hai m3u8 convert karne ke liye
RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
