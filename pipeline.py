import os
import json
import time
import random
import asyncio
import warnings
import requests
import feedparser
import urllib.parse
from datetime import datetime

# Clean Pillow compatibility fix without deprecation warnings
import PIL.Image
warnings.filterwarnings("ignore", category=DeprecationWarning)
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS)

from google import genai
from google.genai import types
from groq import Groq
import edge_tts
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip, 
    CompositeAudioClip, concatenate_videoclips
)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# ==========================================
# STEP 0: Live Breaking News Ingestion
# ==========================================
def get_trending_news():
    print("📰 Step 0: Scrape live AI & tech news via RSS...")
    rss_feeds = [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.mittechnologyreview.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index"
    ]
    news_items = []
    for url in rss_feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")[:250]
                if title:
                    news_items.append(f"Headline: {title} | Context: {summary}")
        except Exception as e:
            print(f"   ⚠️ RSS Feed error ({url}): {e}")

    if news_items:
        selected_news = random.choice(news_items)
        print(f"   ✅ Selected News Context: {selected_news[:90]}...")
        return selected_news
    
    fallback_topics = [
        "Humanoid Robotics & AI Automation Breakthroughs",
        "Autonomous AI Coding Agents Revolutionizing Software",
        "Quantum AI Synergy & Supercomputing Breakthroughs"
    ]
    return f"Topic: {random.choice(fallback_topics)}"

# ==========================================
# STEP 1: Dual AI Script Generation (Short + 1-2 Min Long)
# ==========================================
def generate_dual_scripts():
    print("🧠 Step 1: Requesting Dual Scripts (Short + 2-Min Video) from AI...")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")
    news_context = get_trending_news()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    prompt = f"""You are an expert AI & Tech news content creator for YouTube.
Timestamp Seed: {current_time}
Live News Anchor Context: {news_context}

Generate TWO distinct content packages in JSON format:
1. "short": A punchy 40-second vertical video script (#Shorts).
2. "long": An expanded 90-120 second in-depth horizontal video script.

Return ONLY a JSON object with this exact structure:
{{
  "short": {{
    "title": "Short Catchy Headline | AI News #Shorts",
    "description": "Quick breakdown of latest AI news. #Shorts #AINews #Tech",
    "tags": ["AI News", "Shorts", "Tech"],
    "prompts": [
      "futuristic glowing cybernetic AI brain, dark cyber neon lighting",
      "humanoid robot working at high tech holographic workstation"
    ],
    "script": "Spoken script for 40-second Short..."
  }},
  "long": {{
    "title": "In-Depth: Major AI Breakthrough Explored | FutureTech Pulse",
    "description": "Comprehensive 2-minute deep dive into recent AI breakthroughs. Subscribe for daily tech analysis!",
    "tags": ["AI Breakthrough", "Artificial Intelligence", "Tech News", "FutureTech"],
    "prompts": [
      "futuristic glowing cybernetic AI brain, dark cyber neon lighting",
      "humanoid robot working at high tech holographic workstation",
      "advanced quantum computing server room glowing with data streams",
      "futuristic city skyline at night with floating data networks"
    ],
    "script": "Full in-depth 90-120 second spoken narration script providing background, implications, and future outlook..."
  }}
}}"""

    # Primary Provider: Gemini API
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            print("   Attempting Gemini API (gemini-3.8-flash)...")
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            content = json.loads(response.text.strip())
            if isinstance(content, dict) and "short" in content and "long" in content:
                print("   ✅ Gemini success for Dual Scripts!")
                return content
        except Exception as e:
            print(f"   ⚠️ Gemini primary attempt failed ({e}). Switching to Groq fallback...")

    # Backup Provider: Groq API (Strict Chat LLM Filtering)
    if groq_key:
        try:
            print("   Attempting Backup Provider: Groq API...")
            groq_client = Groq(api_key=groq_key)
            models_data = groq_client.models.list().data
            
            # Filter out guard, whisper, embed, and non-chat models
            active_chat_models = [
                m.id for m in models_data 
                if not any(bad in m.id.lower() for bad in ["whisper", "safetensors", "guard", "embed"])
            ]

            for model in active_chat_models:
                try:
                    print(f"   Trying Groq model: '{model}'...")
                    completion = groq_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"}
                    )
                    raw_text = completion.choices[0].message.content.strip()
                    if "```json" in raw_text:
                        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in raw_text:
                        raw_text = raw_text.split("```")[1].split("```")[0].strip()
                        
                    content = json.loads(raw_text)
                    if isinstance(content, dict) and "short" in content and "long" in content:
                        print(f"   ✅ Groq ({model}) success for Dual Scripts!")
                        return content
                except Exception as err:
                    print(f"   ⚠️ Groq model '{model}' skipped: {err}")
        except Exception as e:
            print(f"   ⚠️ Groq API error: {e}")

    raise RuntimeError("❌ Both Gemini and Groq AI attempts failed.")

# ==========================================
# STEP 2: Speech Synthesis & Audio Mixer
# ==========================================
async def create_voiceover(text, output_file):
    print(f"🎙️ Synthesizing speech -> {output_file}...")
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)
    print("   Speech synthesized successfully.")

def get_background_music(output_file="bg_music.mp3"):
    if os.path.exists(output_file):
        return output_file
    print("🎵 Fetching background music track...")
    url = "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3?filename=cyberpunk-tech-110391.mp3"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(res.content)
            return output_file
    except Exception as e:
        print(f"   ⚠️ Music download error: {e}")
    return None

# ==========================================
# STEP 3: Animated Background Engine (Pan & Zoom Animation)
# ==========================================
def download_animated_backgrounds(prompts, total_duration, width=1080, height=1920):
    print(f"🖼️ Generating Animated Backgrounds ({width}x{height}) with Motion...")
    image_paths = []
    per_image_dur = total_duration / len(prompts)

    for idx, raw_prompt in enumerate(prompts):
        encoded_prompt = urllib.parse.quote(f"{raw_prompt}, dark cyber aesthetic, futuristic tech 8k")
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
        file_path = f"bg_{width}x{height}_{idx}.png"
        try:
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(res.content)
                image_paths.append((file_path, per_image_dur))
        except Exception as e:
            print(f"   ⚠️ AI Image error: {e}")

    if not image_paths:
        file_path = f"fallback_{width}x{height}.png"
        img = PIL.Image.new('RGB', (width, height), color=(15, 23, 42))
        img.save(file_path)
        image_paths.append((file_path, total_duration))

    clips = []
    for path, dur in image_paths:
        img_clip = ImageClip(path).set_duration(dur)
        animated_clip = img_clip.resize(lambda t: 1.0 + 0.02 * t)
        clips.append(animated_clip)

    return concatenate_videoclips(clips, method="compose")

# ==========================================
# STEP 4: Video Builders (Short 9:16 & Long 16:9)
# ==========================================
def create_video_short(title_text, script_text, prompts, audio_file, output_file="short_video.mp4"):
    print("🎬 Rendering 9:16 Vertical Short with Motion Animation...")
    voice_audio = AudioFileClip(audio_file)
    duration = voice_audio.duration
    
    bg_music_file = get_background_music()
    if bg_music_file:
        try:
            bg_music = AudioFileClip(bg_music_file).volumex(0.08).set_duration(duration)
            final_audio = CompositeAudioClip([voice_audio, bg_music])
        except Exception:
            final_audio = voice_audio
    else:
        final_audio = voice_audio

    bg_video = download_animated_backgrounds(prompts, duration, width=1080, height=1920)

    overlay_img = PIL.Image.new('RGBA', (1080, 1920), color=(0, 0, 0, 0))
    draw = PIL.ImageDraw.Draw(overlay_img)
    
    draw.rectangle([(80, 140), (1000, 240)], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=3)
    draw.text((120, 175), "FUTURETECH AI PULSE", fill=(56, 189, 248))
    
    draw.rectangle([(80, 280), (1000, 540)], fill=(15, 23, 42, 230))
    draw.text((100, 340), title_text[:70], fill=(255, 255, 255))
    
    draw.rectangle([(80, 580), (1000, 1600)], fill=(15, 23, 42, 220))
    draw.text((120, 620), "TODAY'S AI BREAKTHROUGH:", fill=(244, 63, 94))
    
    words = script_text.split()
    lines, current_line = [], []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 28:
            lines.append(" ".join(current_line[:-1]))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    y_offset = 700
    for line in lines[:16]:
        draw.text((120, y_offset), line, fill=(226, 232, 240))
        y_offset += 52
        
    draw.rectangle([(80, 1650), (1000, 1780)], fill=(56, 189, 248, 240))
    draw.text((180, 1700), "SUBSCRIBE FOR DAILY AI NEWS", fill=(15, 23, 42))
    
    overlay_path = "overlay_short.png"
    overlay_img.save(overlay_path)
    overlay_clip = ImageClip(overlay_path).set_duration(duration)

    final_video = CompositeVideoClip([bg_video, overlay_clip])
    final_video = final_video.set_audio(final_audio)
    final_video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")
    print(f"   ✅ Short rendered: {output_file}")
    return output_file

def create_video_long(title_text, script_text, prompts, audio_file, output_file="long_video.mp4"):
    print("🎬 Rendering 16:9 Widescreen 1-2 Min Video with Motion Animation...")
    voice_audio = AudioFileClip(audio_file)
    duration = voice_audio.duration
    
    bg_music_file = get_background_music()
    if bg_music_file:
        try:
            bg_music = AudioFileClip(bg_music_file).volumex(0.08).set_duration(duration)
            final_audio = CompositeAudioClip([voice_audio, bg_music])
        except Exception:
            final_audio = voice_audio
    else:
        final_audio = voice_audio

    bg_video = download_animated_backgrounds(prompts, duration, width=1920, height=1080)

    overlay_img = PIL.Image.new('RGBA', (1920, 1080), color=(0, 0, 0, 0))
    draw = PIL.ImageDraw.Draw(overlay_img)
    
    draw.rectangle([(100, 60), (700, 130)], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=2)
    draw.text((130, 82), "FUTURETECH AI PULSE | DEEP DIVE", fill=(56, 189, 248))
    
    draw.rectangle([(100, 160), (1820, 920)], fill=(15, 23, 42, 215))
    draw.text((140, 200), title_text[:110], fill=(255, 255, 255))
    draw.rectangle([(140, 270), (1780, 272)], fill=(56, 189, 248))
    
    words = script_text.split()
    lines, current_line = [], []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 60:
            lines.append(" ".join(current_line[:-1]))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    y_offset = 300
    for line in lines[:11]:
        draw.text((140, y_offset), line, fill=(226, 232, 240))
        y_offset += 50
        
    draw.rectangle([(100, 960), (1820, 1030)], fill=(56, 189, 248, 230))
    draw.text((650, 980), "SUBSCRIBE FOR DAILY IN-DEPTH AI COVERAGE", fill=(15, 23, 42))
    
    overlay_path = "overlay_long.png"
    overlay_img.save(overlay_path)
    overlay_clip = ImageClip(overlay_path).set_duration(duration)

    final_video = CompositeVideoClip([bg_video, overlay_clip])
    final_video = final_video.set_audio(final_audio)
    final_video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")
    print(f"   ✅ Long Video rendered: {output_file}")
    return output_file

# ==========================================
# STEP 5: YouTube API Uploader
# ==========================================
def upload_to_youtube(video_file, title, description, tags):
    print(f"🚀 Uploading {video_file} to YouTube...")
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )
    creds.refresh(Request())
    
    youtube = build("youtube", "v3", credentials=creds)
    
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": "28"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }
    
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   Upload Progress: {int(status.progress() * 100)}%")
            
    video_id = response.get("id")
    print(f"🎉 SUCCESS! Published live to YouTube: https://youtu.be/{video_id}")
    return video_id

# ==========================================
# MAIN EXECUTION ROUTINE
# ==========================================
if __name__ == "__main__":
    pkg = generate_dual_scripts()
    
    # 1. Render & Upload Short Video (9:16)
    short_data = pkg["short"]
    asyncio.run(create_voiceover(short_data["script"], "voice_short.mp3"))
    short_file = create_video_short(
        short_data["title"], 
        short_data["script"], 
        short_data.get("prompts", ["cyber AI brain"]), 
        "voice_short.mp3", 
        "short_video.mp4"
    )
    upload_to_youtube(short_file, short_data["title"], short_data["description"], short_data["tags"])
    
    # 2. Render & Upload Long Video (16:9)
    long_data = pkg["long"]
    asyncio.run(create_voiceover(long_data["script"], "voice_long.mp3"))
    long_file = create_video_long(
        long_data["title"], 
        long_data["script"], 
        long_data.get("prompts", ["futuristic quantum computer"]), 
        "voice_long.mp3", 
        "long_video.mp4"
    )
    upload_to_youtube(long_file, long_data["title"], long_data["description"], long_data["tags"])
