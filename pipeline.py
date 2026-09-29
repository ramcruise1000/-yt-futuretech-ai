import os
import re
import json
import time
import random
import asyncio
import warnings
import requests
import feedparser
import urllib.parse
from datetime import datetime

# Explicit PIL imports & deprecation warning fix
import PIL.Image
import PIL.ImageDraw
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

# Helper function to sanitize text for PIL font rendering
def sanitize_text(text):
    if not text:
        return ""
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()

# ==========================================
# STEP 0: Strictly AI & Tech News Ingestion
# ==========================================
def get_trending_news():
    print("📰 Step 0: Scraping STRICT AI & Tech news via RSS...")
    rss_feeds = [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.mittechnologyreview.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index"
    ]
    ai_keywords = ["ai", "artificial intelligence", "nvidia", "openai", "google", "chip", "robot", "quantum", "llm", "software", "agent", "model", "tech"]
    news_items = []

    for url in rss_feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")[:250]
                full_text = f"{title} {summary}".lower()
                
                # Enforce strict AI & Tech relevance filter
                if any(kw in full_text for kw in ai_keywords):
                    clean_title = sanitize_text(title.replace('"', "'").replace("\n", " "))
                    clean_summary = sanitize_text(summary.replace('"', "'").replace("\n", " "))
                    news_items.append(f"Headline: {clean_title} | Summary: {clean_summary}")
        except Exception as e:
            print(f"   ⚠️ RSS Feed error ({url}): {e}")

    if news_items:
        selected_news = random.choice(news_items)
        print(f"   ✅ Selected AI & Tech Context: {selected_news[:90]}...")
        return selected_news
    
    fallback_topics = [
        "Headline: OpenAI Releases Autonomous Coding Agents | Summary: New AI system automates software engineering.",
        "Headline: NVIDIA Unveils Next-Gen AI Supercomputing Chips | Summary: Breakthrough architecture accelerates LLM training.",
        "Headline: Humanoid AI Robots Achieve Precision Assembly | Summary: Neural network control allows real-time adaptive robotics."
    ]
    return random.choice(fallback_topics)

# ==========================================
# STEP 1: Multi-Provider AI Engine (Gemini -> Groq -> OpenRouter -> Fallback)
# ==========================================
def generate_dual_scripts():
    print("🧠 Step 1: Generating Animated Multi-Slide AI & Tech News Package...")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    news_context = get_trending_news()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    prompt = f"""You are an expert AI & Tech news content creator for YouTube.
Timestamp Seed: {current_time}
Live News Context: {news_context}

Generate TWO distinct content packages ("short" and "long") structured into animated slide scenes.

Return ONLY a JSON object with this exact structure:
{{
  "short": {{
    "title": "Short Catchy Headline | AI News #Shorts",
    "description": "Quick breakdown of latest AI news. #Shorts #AINews #Tech",
    "tags": ["AI News", "Shorts", "Tech"],
    "slides": [
      {{"text": "Headline breakdown sentence 1.", "prompt": "glowing cybernetic AI brain, dark cyan neon 8k", "badge": "BREAKING AI NEWS"}},
      {{"text": "Key implication or detail sentence 2.", "prompt": "humanoid robot working at holographic terminal", "badge": "TECH BREAKTHROUGH"}},
      {{"text": "Future impact sentence 3.", "prompt": "quantum computing server room glowing blue data streams", "badge": "INDUSTRY IMPACT"}},
      {{"text": "Subscribe to FutureTech Pulse for daily AI news!", "prompt": "futuristic neon subscribe button with circuit background", "badge": "SUBSCRIBE NOW"}}
    ]
  }},
  "long": {{
    "title": "In-Depth: Major AI Breakthrough Explored | FutureTech Pulse",
    "description": "Comprehensive deep dive into recent AI breakthroughs.",
    "tags": ["AI Breakthrough", "Artificial Intelligence", "Tech News"],
    "slides": [
      {{"text": "Welcome to FutureTech Pulse with today's top AI story.", "prompt": "futuristic glowing cybernetic AI brain 8k", "badge": "AI DEEP DIVE"}},
      {{"text": "Engineers have unveiled a major breakthrough in autonomous systems.", "prompt": "high tech robotics laboratory dark aesthetic", "badge": "AUTONOMOUS AI"}},
      {{"text": "This technology enables software to self-correct and execute complex code.", "prompt": "floating holographic code matrix glowing cyan", "badge": "SOFTWARE INNOVATION"}},
      {{"text": "Industry analysts predict this could transform software production globally.", "prompt": "futuristic city skyline with glowing data network", "badge": "GLOBAL IMPACT"}},
      {{"text": "Subscribe for daily in-depth artificial intelligence coverage!", "prompt": "futuristic neon subscribe banner cyan dark", "badge": "SUBSCRIBE FOR MORE"}}
    ]
  }}
}}"""

    # --- PROVIDER 1: Gemini API ---
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            for attempt in range(1, 4):
                try:
                    print(f"   [Provider 1] Gemini API attempt {attempt}/3...")
                    response = client.models.generate_content(
                        model="gemini-3.8-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    content = json.loads(response.text.strip())
                    if isinstance(content, dict) and "short" in content and "long" in content:
                        print("   ✅ Gemini success!")
                        return content
                except Exception as e:
                    print(f"   ⚠️ Gemini attempt {attempt} failed ({e}).")
                    time.sleep(3)
        except Exception as e:
            print(f"   ⚠️ Gemini client error: {e}")

    # --- PROVIDER 2: Groq API ---
    if groq_key:
        try:
            print("   [Provider 2] Switching to Groq API...")
            groq_client = Groq(api_key=groq_key)
            models_data = groq_client.models.list().data
            active_chat_models = [m.id for m in models_data if not any(b in m.id.lower() for b in ["whisper", "safetensors", "guard", "embed", "canopylabs", "orpheus"])]

            for model in active_chat_models:
                try:
                    print(f"   Trying Groq model: '{model}'...")
                    completion = groq_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"},
                        max_tokens=1000
                    )
                    raw_text = completion.choices.message.content.strip()
                    content = json.loads(raw_text)
                    if isinstance(content, dict) and "short" in content and "long" in content:
                        print(f"   ✅ Groq ({model}) success!")
                        return content
                except Exception:
                    pass
        except Exception as e:
            print(f"   ⚠️ Groq API error: {e}")

    # --- PROVIDER 3: OpenRouter API (Free Tier Models) ---
    if openrouter_key:
        try:
            print("   [Provider 3] Switching to OpenRouter Free API...")
            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json"
            }
            openrouter_models = [
                "google/gemma-2-9b-it:free",
                "meta-llama/llama-3.2-11b-vision-instruct:free",
                "qwen/qwen-2.5-coder-32b-instruct:free"
            ]
            for model in openrouter_models:
                try:
                    print(f"   Trying OpenRouter model: '{model}'...")
                    payload = {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"}
                    }
                    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=20)
                    if res.status_code == 200:
                        raw_text = res.json()["choices"][0]["message"]["content"]
                        content = json.loads(raw_text)
                        if isinstance(content, dict) and "short" in content and "long" in content:
                            print(f"   ✅ OpenRouter ({model}) success!")
                            return content
                except Exception as e:
                    print(f"   ⚠️ OpenRouter model '{model}' skipped: {e}")
        except Exception as e:
            print(f"   ⚠️ OpenRouter API error: {e}")

    # --- PROVIDER 4: Fail-Safe Built-in Template Engine ---
    print("   ⚠️ All remote AI providers busy. Using Fail-Safe Template Engine...")
    return {
        "short": {
            "title": "Breaking AI & Tech News Update | #Shorts",
            "description": "Latest breaking developments in artificial intelligence and tech.",
            "tags": ["AI News", "Shorts", "Tech"],
            "slides": [
                {"text": "Breaking news in artificial intelligence and autonomous systems.", "prompt": "glowing cybernetic AI brain neon blue 8k", "badge": "BREAKING AI NEWS"},
                {"text": "Next generation AI models achieve unprecedented performance leaps.", "prompt": "humanoid robot coding at holographic computer terminal", "badge": "TECH BREAKTHROUGH"},
                {"text": "Subscribe to FutureTech Pulse for daily breaking tech news!", "prompt": "futuristic neon subscribe button circuit background", "badge": "SUBSCRIBE NOW"}
            ]
        },
        "long": {
            "title": "In-Depth: Major Artificial Intelligence Breakthrough | FutureTech Pulse",
            "description": "Comprehensive analysis of today's top AI and tech developments.",
            "tags": ["AI Breakthrough", "Tech News", "FutureTech"],
            "slides": [
                {"text": "Welcome to FutureTech Pulse with today's deep dive into AI developments.", "prompt": "futuristic glowing cybernetic AI brain 8k", "badge": "AI DEEP DIVE"},
                {"text": "Recent advancements in neural networks are transforming autonomous tools.", "prompt": "high tech robotics laboratory dark aesthetic", "badge": "AUTONOMOUS AI"},
                {"text": "Subscribe for daily in-depth artificial intelligence coverage!", "prompt": "futuristic neon subscribe banner cyan dark", "badge": "SUBSCRIBE FOR MORE"}
            ]
        }
    }

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
# STEP 3: Multi-Slide Animated Video Engine
# ==========================================
def render_multislide_video(title_text, slides, audio_file, is_short=True, output_file="video.mp4"):
    width, height = (1080, 1920) if is_short else (1920, 1080)
    print(f"🎬 Rendering Animated Multi-Slide Video ({width}x{height}) with {len(slides)} scenes...")

    voice_audio = AudioFileClip(audio_file)
    total_duration = voice_audio.duration
    slide_dur = total_duration / len(slides)

    bg_music_file = get_background_music()
    if bg_music_file:
        try:
            bg_music = AudioFileClip(bg_music_file).volumex(0.08).set_duration(total_duration)
            final_audio = CompositeAudioClip([voice_audio, bg_music])
        except Exception:
            final_audio = voice_audio
    else:
        final_audio = voice_audio

    slide_clips = []

    for idx, slide in enumerate(slides):
        slide_text = sanitize_text(slide.get("text", ""))
        slide_prompt = sanitize_text(slide.get("prompt", "futuristic AI technology dark"))
        slide_badge = sanitize_text(slide.get("badge", "FUTURETECH AI"))

        # 1. Download unique image for this specific slide
        encoded_prompt = urllib.parse.quote(f"{slide_prompt}, dark cyber aesthetic 8k")
        img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
        file_path = f"slide_{'short' if is_short else 'long'}_{idx}.png"

        try:
            res = requests.get(img_url, timeout=12)
            if res.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(res.content)
            else:
                raise ValueError("Image download non-200")
        except Exception:
            img = PIL.Image.new('RGB', (width, height), color=(15, 23, 42))
            img.save(file_path)

        # 2. Animated Motion Background (Ken Burns Zoom)
        img_clip = ImageClip(file_path).set_duration(slide_dur)
        animated_bg = img_clip.resize(lambda t: 1.0 + 0.03 * t)

        # 3. Create sleek, dynamic lower-third caption card for this slide ONLY
        overlay_img = PIL.Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(overlay_img)

        if is_short:
            # Top Badge
            draw.rectangle([(80, 140), (1000, 230)], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=3)
            draw.text((120, 168), slide_badge[:30], fill=(56, 189, 248))

            # Sleek Lower-Third Caption Card (doesn't block the screen!)
            draw.rectangle([(80, 1280), (1000, 1680)], fill=(15, 23, 42, 220), outline=(56, 189, 248), width=2)
            
            words = slide_text.split()
            lines, current_line = [], []
            for word in words:
                current_line.append(word)
                if len(" ".join(current_line)) > 26:
                    lines.append(" ".join(current_line[:-1]))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))

            y_offset = 1320
            for line in lines[:6]:
                draw.text((110, y_offset), line, fill=(255, 255, 255))
                y_offset += 52

            # Subscribe CTA
            draw.rectangle([(80, 1720), (1000, 1820)], fill=(56, 189, 248, 240))
            draw.text((180, 1750), "SUBSCRIBE FOR DAILY AI NEWS", fill=(15, 23, 42))

        else: # Widescreen 16:9
            # Top Left Badge
            draw.rectangle([(100, 60), (700, 130)], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=2)
            draw.text((130, 82), f"FUTURETECH AI | {slide_badge[:25]}", fill=(56, 189, 248))

            # Bottom Caption Bar
            draw.rectangle([(100, 720), (1820, 960)], fill=(15, 23, 42, 220), outline=(56, 189, 248), width=2)

            words = slide_text.split()
            lines, current_line = [], []
            for word in words:
                current_line.append(word)
                if len(" ".join(current_line)) > 55:
                    lines.append(" ".join(current_line[:-1]))
                    current_line = [word]
            if current_line:
                lines.append(" ".join(current_line))

            y_offset = 750
            for line in lines[:4]:
                draw.text((140, y_offset), line, fill=(255, 255, 255))
                y_offset += 48

            # Bottom CTA
            draw.rectangle([(100, 980), (1820, 1040)], fill=(56, 189, 248, 230))
            draw.text((650, 995), "SUBSCRIBE FOR DAILY IN-DEPTH AI COVERAGE", fill=(15, 23, 42))

        overlay_path = f"overlay_{'short' if is_short else 'long'}_{idx}.png"
        overlay_img.save(overlay_path)
        overlay_clip = ImageClip(overlay_path).set_duration(slide_dur)

        scene_clip = CompositeVideoClip([animated_bg, overlay_clip])
        slide_clips.append(scene_clip)

    final_video = concatenate_videoclips(slide_clips, method="compose")
    final_video = final_video.set_audio(final_audio)
    final_video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")
    print(f"   ✅ Video rendered successfully: {output_file}")
    return output_file

# ==========================================
# STEP 4: YouTube API Uploader
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
            "title": sanitize_text(title)[:100],
            "description": sanitize_text(description)[:5000],
            "tags": [sanitize_text(t) for t in tags],
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
    
    # 1. Render & Upload Short Video (9:16 Vertical)
    short_data = pkg["short"]
    short_slides = short_data.get("slides", [])
    short_full_script = " ".join([s.get("text", "") for s in short_slides])
    asyncio.run(create_voiceover(short_full_script, "voice_short.mp3"))
    
    short_file = render_multislide_video(
        short_data["title"], 
        short_slides, 
        "voice_short.mp3", 
        is_short=True, 
        output_file="short_video.mp4"
    )
    upload_to_youtube(short_file, short_data["title"], short_data["description"], short_data["tags"])
    
    # 2. Render & Upload Long Video (16:9 Widescreen)
    long_data = pkg["long"]
    long_slides = long_data.get("slides", [])
    long_full_script = " ".join([s.get("text", "") for s in long_slides])
    asyncio.run(create_voiceover(long_full_script, "voice_long.mp3"))
    
    long_file = render_multislide_video(
        long_data["title"], 
        long_slides, 
        "voice_long.mp3", 
        is_short=False, 
        output_file="long_video.mp4"
    )
    upload_to_youtube(long_file, long_data["title"], long_data["description"], long_data["tags"])
