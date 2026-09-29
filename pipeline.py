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
import numpy as np
from datetime import datetime

# Explicit PIL imports & deprecation warning fix
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
warnings.filterwarnings("ignore", category=DeprecationWarning)
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS)

from google import genai
from google.genai import types
from groq import Groq
import edge_tts
from moviepy.editor import (
    VideoClip, ImageClip, AudioFileClip, CompositeVideoClip, 
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
# STEP 0: Strictly AI & Emerging Tech News Ingestion
# ==========================================
def get_trending_news():
    print("📰 Step 0: Scraping STRICT AI & Tech news via RSS...")
    rss_feeds = [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.mittechnologyreview.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index"
    ]
    ai_keywords = ["ai", "artificial intelligence", "nvidia", "openai", "chip", "robot", "quantum", "llm", "software agent", "neural", "deep learning", "machine learning", "anthropic", "gemini"]
    news_items = []

    for url in rss_feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")[:300]
                full_text = f"{title} {summary}".lower()
                
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
        "Headline: OpenAI Advances Autonomous AI Coding Agents | Summary: Next-generation neural models automate end-to-end software engineering workflows with self-correcting logic.",
        "Headline: NVIDIA Unveils Next-Gen AI Supercomputing Architecture | Summary: Massive GPU clusters accelerate multi-trillion parameter LLM training and real-time world simulation.",
        "Headline: Humanoid AI Robotics Breakthrough in Autonomous Assembly | Summary: Neural network control enables vision-guided precision dexterity in industrial automation."
    ]
    selected_fallback = random.choice(fallback_topics)
    print(f"   ✅ Selected Fallback AI Topic: {selected_fallback[:90]}...")
    return selected_fallback

# ==========================================
# STEP 1: Multi-Provider AI Engine (Strict AI Topic & Length)
# ==========================================
def generate_dual_scripts():
    print("🧠 Step 1: Generating Animated Multi-Slide AI & Tech News Package...")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    news_context = get_trending_news()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    prompt = f"""You are a professional AI & Technology news anchor for YouTube.
Timestamp Seed: {current_time}
Context: {news_context}

CRITICAL MANDATE:
- Topic MUST be strictly about Artificial Intelligence, LLMs, Robotics, Microchips, or Emerging Tech.
- Generate TWO distinct content packages:
  1. "short": 5 slides, total 90-120 words (~40-50 seconds spoken audio).
  2. "long": 8-10 slides, total 280-350 words (~90-120 seconds spoken audio).

Return ONLY a valid JSON object with this exact structure:
{{
  "short": {{
    "title": "Short Catchy Headline | AI News #Shorts",
    "description": "Quick breakdown of latest AI news. #Shorts #AINews #Tech",
    "tags": ["AI News", "Shorts", "Tech"],
    "slides": [
      {{"text": "Breaking news in artificial intelligence as researchers announce a massive breakthrough in autonomous models.", "prompt": "glowing cybernetic AI brain, dark cyan neon 8k", "badge": "BREAKING AI NEWS"}},
      {{"text": "This new architecture allows AI systems to process complex reasoning tasks up to ten times faster than previous generations.", "prompt": "humanoid robot working at holographic terminal", "badge": "NEURAL BREAKTHROUGH"}},
      {{"text": "Major tech leaders report that this innovation will accelerate enterprise automation across software and biotech industries.", "prompt": "quantum computing server room glowing blue data streams", "badge": "INDUSTRY IMPACT"}},
      {{"text": "As deployment expands globally, experts predict a fundamental shift in how human engineers collaborate with artificial intelligence.", "prompt": "futuristic city skyline at night floating glowing network", "badge": "FUTURE OUTLOOK"}},
      {{"text": "Subscribe to FutureTech Pulse for daily breaking artificial intelligence updates!", "prompt": "futuristic neon subscribe button circuit background", "badge": "SUBSCRIBE NOW"}}
    ]
  }},
  "long": {{
    "title": "In-Depth Analysis: The Next Era of Artificial Intelligence | FutureTech Pulse",
    "description": "Comprehensive 2-minute deep dive into recent artificial intelligence breakthroughs and industry implications.",
    "tags": ["AI Breakthrough", "Artificial Intelligence", "Tech News", "FutureTech"],
    "slides": [
      {{"text": "Welcome to FutureTech Pulse. Today we are exploring a milestone development in artificial intelligence.", "prompt": "futuristic glowing cybernetic AI brain 8k", "badge": "AI DEEP DIVE"}},
      {{"text": "Engineers and computer scientists have officially unveiled a novel neural network architecture built for extreme scalability.", "prompt": "high tech robotics laboratory dark aesthetic", "badge": "NEURAL ARCHITECTURE"}},
      {{"text": "Unlike traditional transformer models, this new framework reduces computational overhead while dramatically boosting reasoning accuracy.", "prompt": "floating holographic code matrix glowing cyan", "badge": "SOFTWARE INNOVATION"}},
      {{"text": "In benchmark evaluations, the model demonstrated unprecedented capability in autonomous software development and scientific research.", "prompt": "supercomputer server room glowing neon circuit trails", "badge": "BENCHMARK PERFORMANCE"}},
      {{"text": "Key industry partners are already integrating this system into cloud infrastructure to power next generation AI agents.", "prompt": "futuristic digital globe with connected data streams", "badge": "ENTERPRISE INTEGRATION"}},
      {{"text": "However, security researchers emphasize the crucial need for robust alignment safeguards as autonomous capabilities expand.", "prompt": "cybersecurity shield visual glowing neon lock code", "badge": "SAFETY & ALIGNMENT"}},
      {{"text": "Looking ahead, this breakthrough sets the foundation for highly adaptable AI systems capable of continuous real time learning.", "prompt": "futuristic tech laboratory with glowing hologram displays", "badge": "FUTURE HORIZON"}},
      {{"text": "Make sure to subscribe to FutureTech Pulse for daily, comprehensive coverage of artificial intelligence and emerging technology!", "prompt": "futuristic neon subscribe banner cyan dark", "badge": "SUBSCRIBE FOR MORE"}}
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
                        max_tokens=1500
                    )
                    raw_text = completion.choices.message.content.strip()
                    content = json.loads(raw_text)
                    if isinstance(content, dict) and "short" in content and "long" in content:
                        print(f"   ✅ Groq ({model}) success!")
                        return content
                except Exception as err:
                    print(f"   ⚠️ Groq model '{model}' skipped: {err}")
        except Exception as e:
            print(f"   ⚠️️ Groq API error: {e}")

    # --- PROVIDER 3: OpenRouter API ---
    if openrouter_key:
        try:
            print("   [Provider 3] Switching to OpenRouter Free API...")
            headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
            openrouter_models = ["google/gemma-2-9b-it:free", "meta-llama/llama-3.2-11b-vision-instruct:free"]
            for model in openrouter_models:
                try:
                    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}, timeout=20)
                    if res.status_code == 200:
                        content = json.loads(res.json()["choices"]["message"]["content"])
                        if isinstance(content, dict) and "short" in content and "long" in content:
                            print(f"   ✅ OpenRouter ({model}) success!")
                            return content
                except Exception:
                    pass
        except Exception as e:
            print(f"   ⚠️ OpenRouter API error: {e}")

    # --- PROVIDER 4: Fail-Safe AI Template Engine ---
    print("   ⚠️ All remote AI providers busy. Using Fail-Safe AI Template Engine...")
    return {
        "short": {
            "title": "Next-Gen Autonomous AI Models Unveiled | #Shorts",
            "description": "Quick breakdown of major developments in artificial intelligence and autonomous systems. #Shorts #AINews #Tech",
            "tags": ["AI News", "Shorts", "Tech", "Artificial Intelligence"],
            "slides": [
                {"text": "Major breakthrough in artificial intelligence as researchers announce next-generation autonomous models.", "prompt": "glowing cybernetic AI brain neon blue 8k", "badge": "BREAKING AI NEWS"},
                {"text": "This new architecture allows neural networks to execute multi-step logic and self-correct software code in real time.", "prompt": "humanoid robot coding at holographic computer terminal", "badge": "NEURAL BREAKTHROUGH"},
                {"text": "Enterprise tech leaders report that automated agents will streamline complex software development globally.", "prompt": "quantum computing server room glowing blue data streams", "badge": "INDUSTRY IMPACT"},
                {"text": "As autonomous AI expands across cloud networks, computer scientists emphasize the need for rigorous security benchmarks.", "prompt": "cybersecurity shield glowing neon circuit background", "badge": "SAFETY & CONTROL"},
                {"text": "Subscribe to FutureTech Pulse for daily breaking artificial intelligence and technology news!", "prompt": "futuristic neon subscribe button circuit background", "badge": "SUBSCRIBE NOW"}
            ]
        },
        "long": {
            "title": "In-Depth Analysis: How Next-Gen AI Models Are Revolutionizing Tech | FutureTech Pulse",
            "description": "Comprehensive deep dive into recent artificial intelligence breakthroughs, neural architectures, and enterprise impact.",
            "tags": ["AI Breakthrough", "Artificial Intelligence", "Tech News", "FutureTech"],
            "slides": [
                {"text": "Welcome to FutureTech Pulse. Today we are conducting an in-depth exploration into the latest milestones in artificial intelligence.", "prompt": "futuristic glowing cybernetic AI brain 8k", "badge": "AI DEEP DIVE"},
                {"text": "Leading AI research labs have officially demonstrated a new neural network architecture designed for high speed complex reasoning.", "prompt": "high tech robotics laboratory dark aesthetic", "badge": "NEURAL ARCHITECTURE"},
                {"text": "Unlike standard transformer architectures, this breakthrough dramatically decreases latency while scaling contextual memory capacity.", "prompt": "floating holographic code matrix glowing cyan", "badge": "SOFTWARE INNOVATION"},
                {"text": "In rigorous benchmark evaluations, the model surpassed existing standards in autonomous software engineering and mathematical problem solving.", "prompt": "supercomputer server room glowing neon circuit trails", "badge": "BENCHMARK PERFORMANCE"},
                {"text": "Major cloud infrastructure providers are preparing to roll out these advanced models to power enterprise autonomous AI agents globally.", "prompt": "futuristic digital globe with connected data streams", "badge": "ENTERPRISE INTEGRATION"},
                {"text": "At the same time, safety researchers are introducing novel guardrail frameworks to ensure reliable, policy compliant AI operations.", "prompt": "cybersecurity shield visual glowing neon lock code", "badge": "SAFETY & ALIGNMENT"},
                {"text": "Industry experts project that adaptive neural models will become the primary operating engine for software development within the decade.", "prompt": "futuristic city skyline at night floating glowing network", "badge": "FUTURE HORIZON"},
                {"text": "Make sure to subscribe to FutureTech Pulse for daily, comprehensive coverage of artificial intelligence and emerging technology!", "prompt": "futuristic neon subscribe banner cyan dark", "badge": "SUBSCRIBE FOR MORE"}
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
# STEP 3: High-CTR Custom Thumbnail Generators
# ==========================================
def generate_thumbnail(title_text, badge_text, is_short=False, output_file="thumbnail.png"):
    width, height = (1080, 1920) if is_short else (1280, 720)
    print(f"🎨 Generating High-CTR Thumbnail ({width}x{height}) -> {output_file}...")
    
    encoded_prompt = urllib.parse.quote("futuristic AI brain glowing cybernetic neon dark 8k high quality render")
    img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
    
    try:
        res = requests.get(img_url, timeout=12)
        if res.status_code == 200:
            with open("thumb_bg.png", "wb") as f:
                f.write(res.content)
            base_img = PIL.Image.open("thumb_bg.png").convert("RGBA")
        else:
            base_img = PIL.Image.new("RGBA", (width, height), (15, 23, 42, 255))
    except Exception:
        base_img = PIL.Image.new("RGBA", (width, height), (15, 23, 42, 255))

    draw = PIL.ImageDraw.Draw(base_img)
    
    # Outer Neon Border
    draw.rectangle([(20, 20), (width-20, height-20)], outline=(56, 189, 248), width=6)
    
    clean_badge = sanitize_text(badge_text).upper()
    clean_title = sanitize_text(title_text)

    if is_short:
        # Vertical 9:16 Thumbnail Overlay
        draw.rectangle([(60, 160), (1020, 280)], fill=(244, 63, 94, 240))
        draw.text((100, 200), clean_badge, fill=(255, 255, 255))
        
        draw.rectangle([(60, 1200), (1020, 1680)], fill=(15, 23, 42, 235), outline=(250, 204, 21), width=4)
        words = clean_title.split()
        lines, current_line = [], []
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > 20:
                lines.append(" ".join(current_line[:-1]))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
            
        y_off = 1240
        for line in lines[:5]:
            draw.text((90, y_off), line, fill=(250, 204, 21))
            y_off += 65
    else:
        # Widescreen 16:9 Thumbnail Overlay
        draw.rectangle([(80, 80), (600, 160)], fill=(244, 63, 94, 240))
        draw.text((110, 105), f"HOT: {clean_badge}", fill=(255, 255, 255))
        
        draw.rectangle([(80, 220), (1200, 580)], fill=(15, 23, 42, 230), outline=(56, 189, 248), width=4)
        words = clean_title.split()
        lines, current_line = [], []
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > 32:
                lines.append(" ".join(current_line[:-1]))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
            
        y_off = 250
        for line in lines[:4]:
            draw.text((110, y_off), line, fill=(250, 204, 21))
            y_off += 70

    base_img = base_img.convert("RGB")
    base_img.save(output_file)
    print(f"   ✅ Thumbnail created: {output_file}")
    return output_file

# ==========================================
# STEP 4: True Frame-by-Frame Motion Zoom Video Engine
# ==========================================
def render_multislide_video(title_text, slides, audio_file, is_short=True, output_file="video.mp4"):
    width, height = (1080, 1920) if is_short else (1920, 1080)
    print(f"🎬 Rendering Animated Multi-Slide Video ({width}x{height}) with {len(slides)} scenes...")

    voice_audio = AudioFileClip(audio_file)
    total_duration = voice_audio.duration
    slide_dur = total_duration / len(slides)
    print(f"   Total Audio Duration: {total_duration:.1f}s | Slide Duration: {slide_dur:.1f}s across {len(slides)} slides.")

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

        overlay_img = PIL.Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(overlay_img)

        if is_short:
            draw.rectangle([(80, 140), (1000, 230)], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=3)
            draw.text((120, 168), slide_badge[:30], fill=(56, 189, 248))

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

            draw.rectangle([(80, 1720), (1000, 1820)], fill=(56, 189, 248, 240))
            draw.text((180, 1750), "SUBSCRIBE FOR DAILY AI NEWS", fill=(15, 23, 42))

        else: # Widescreen 16:9
            draw.rectangle([(100, 60), (700, 130)], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=2)
            draw.text((130, 82), f"FUTURETECH AI | {slide_badge[:25]}", fill=(56, 189, 248))

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

            draw.rectangle([(100, 980), (1820, 1040)], fill=(56, 189, 248, 230))
            draw.text((650, 995), "SUBSCRIBE FOR DAILY IN-DEPTH AI COVERAGE", fill=(15, 23, 42))

        base_pil = PIL.Image.open(file_path).convert("RGBA").resize((width, height))
        composed_pil = PIL.Image.alpha_composite(base_pil, overlay_img).convert("RGB")

        def make_animated_frame(t, pil_img=composed_pil, dur=slide_dur, w=width, h=height):
            scale = 1.0 + 0.12 * (t / max(dur, 0.1))
            w_scaled, h_scaled = int(w * scale), int(h * scale)
            resized = pil_img.resize((w_scaled, h_scaled), PIL.Image.LANCZOS)
            
            crop_x = (w_scaled - w) // 2
            crop_y = (h_scaled - h) // 2
            cropped = resized.crop((crop_x, crop_y, crop_x + w, crop_y + h))
            
            frame_draw = PIL.ImageDraw.Draw(cropped)
            progress_ratio = min(t / max(dur, 0.1), 1.0)
            bar_y = h - 25 if is_short else h - 15
            frame_draw.rectangle([(0, bar_y), (int(w * progress_ratio), bar_y + 15)], fill=(56, 189, 248))
            
            return np.array(cropped)

        scene_clip = VideoClip(make_animated_frame, duration=slide_dur)
        slide_clips.append(scene_clip)

    final_video = concatenate_videoclips(slide_clips, method="compose")
    final_video = final_video.set_audio(final_audio)
    final_video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")
    print(f"   ✅ Motion Animated Video rendered: {output_file}")
    return output_file

# ==========================================
# STEP 5: YouTube API Uploader with Custom Thumbnail Support
# ==========================================
def upload_to_youtube(video_file, title, description, tags, thumbnail_file=None):
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
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   Upload Progress: {int(status.progress() * 100)}%")
            
    video_id = response.get("id")
    print(f"🎉 SUCCESS! Published live to YouTube: https://youtu.be/{video_id}")

    # Set Custom Thumbnail via API
    if thumbnail_file and os.path.exists(thumbnail_file):
        try:
            print(f"🖼️ Setting custom thumbnail for Video ID {video_id}...")
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_file)).execute()
            print("   ✅ Custom thumbnail published successfully!")
        except Exception as e:
            print(f"   ⚠️ Could not set thumbnail ({e}). (Ensure YouTube channel is phone verified for custom thumbnails).")

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
    
    thumb_short = generate_thumbnail(short_data["title"], "BREAKING AI", is_short=True, output_file="thumb_short.png")
    
    short_file = render_multislide_video(
        short_data["title"], 
        short_slides, 
        "voice_short.mp3", 
        is_short=True, 
        output_file="short_video.mp4"
    )
    upload_to_youtube(short_file, short_data["title"], short_data["description"], short_data["tags"], thumbnail_file=thumb_short)
    
    # 2. Render & Upload Long Video (16:9 Widescreen)
    long_data = pkg["long"]
    long_slides = long_data.get("slides", [])
    long_full_script = " ".join([s.get("text", "") for s in long_slides])
    asyncio.run(create_voiceover(long_full_script, "voice_long.mp3"))
    
    thumb_long = generate_thumbnail(long_data["title"], "AI BREAKTHROUGH", is_short=False, output_file="thumb_long.png")
    
    long_file = render_multislide_video(
        long_data["title"], 
        long_slides, 
        "voice_long.mp3", 
        is_short=False, 
        output_file="long_video.mp4"
    )
    upload_to_youtube(long_file, long_data["title"], long_data["description"], long_data["tags"], thumbnail_file=thumb_long)
