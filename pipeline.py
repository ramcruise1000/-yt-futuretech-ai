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
# STEP 0: Strictly AI & Tech News Ingestion with Randomization
# ==========================================
def get_trending_news():
    print("📰 Step 0: Scraping STRICT AI & Tech news via RSS...")
    rss_feeds = [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.mittechnologyreview.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://venturebeat.com/category/ai/feed/"
    ]
    ai_keywords = ["ai", "artificial intelligence", "nvidia", "openai", "chip", "robot", "quantum", "llm", "software agent", "neural", "deep learning", "machine learning", "anthropic", "gemini", "gpt", "model", "algorithm", "supercomputer"]
    news_items = []

    random.seed(int(time.time() * 1000))

    for url in rss_feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
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
        random.shuffle(news_items)
        selected_news = news_items[0]
        print(f"   ✅ Selected AI & Tech Context: {selected_news[:90]}...")
        return selected_news
    
    dynamic_fallbacks = [
        "Headline: OpenAI Advances Autonomous AI Coding Agents | Summary: Next-generation neural models automate end-to-end software engineering workflows with self-correcting reasoning.",
        "Headline: NVIDIA Unveils Next-Gen Blackwell Supercomputing Architecture | Summary: Massive GPU clusters accelerate multi-trillion parameter LLM training and real-time world simulation.",
        "Headline: Humanoid AI Robotics Breakthrough in Autonomous Industrial Dexterity | Summary: Neural network control enables vision-guided precision manipulation in manufacturing.",
        "Headline: Quantum AI Synergy Achieves Million-Qubit Benchmark | Summary: Hybrid quantum-classical algorithms solve complex protein folding and materials discovery in seconds."
    ]
    selected_fallback = random.choice(dynamic_fallbacks)
    print(f"   ✅ Selected Fallback AI Topic: {selected_fallback[:90]}...")
    return selected_fallback

# ==========================================
# STEP 1: Multi-Provider AI Engine
# ==========================================
def generate_dual_scripts():
    print("🧠 Step 1: Generating Animated Multi-Slide AI & Tech News Package...")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    news_context = get_trending_news()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    prompt = f"""You are an elite YouTube AI content creator specializing in viral, high-CTR AI & Tech news.
Randomization Seed: {current_time}
Context: {news_context}

CRITICAL DIRECTIVES:
1. Every run MUST produce UNIQUE, fresh content based on the news context.
2. Titles MUST be viral, high-CTR hooks (e.g. "INSANE AI Breakthrough", "JUST UNVEILED", "THIS CHANGES EVERYTHING").
3. Prompts for thumbnails and slides MUST describe vivid, dynamic visual scenes tailored specifically to the story topic.
4. Content structure:
   - "short": 5 distinct slide scenes, total 90-120 words (~45 seconds spoken audio).
   - "long": 8-10 distinct slide scenes, total 280-350 words (~1.5-2 minutes spoken audio).

Return ONLY a valid JSON object with this exact structure:
{{
  "short": {{
    "title": "Viral Headline | AI News #Shorts",
    "description": "Quick breakdown of latest AI news. #Shorts #AINews #Tech",
    "thumb_prompt": "Specific high impact 8k visual prompt matching this news story",
    "tags": ["AI News", "Shorts", "Tech", "Artificial Intelligence"],
    "slides": [
      {{"text": "Slide 1 sentence...", "prompt": "specific topic visual prompt 1", "badge": "BREAKING AI"}},
      {{"text": "Slide 2 sentence...", "prompt": "specific topic visual prompt 2", "badge": "NEURAL AGENTS"}},
      {{"text": "Slide 3 sentence...", "prompt": "specific topic visual prompt 3", "badge": "INDUSTRY IMPACT"}},
      {{"text": "Slide 4 sentence...", "prompt": "specific topic visual prompt 4", "badge": "FUTURE OUTLOOK"}},
      {{"text": "Subscribe to FutureTech Pulse right now for daily breaking AI news!", "prompt": "futuristic neon subscribe button circuit background", "badge": "SUBSCRIBE NOW"}}
    ]
  }},
  "long": {{
    "title": "Viral High-CTR Widescreen Title | FutureTech Pulse",
    "description": "Comprehensive deep dive into recent artificial intelligence breakthroughs.",
    "thumb_prompt": "Specific high impact 8k widescreen visual prompt matching this deep dive",
    "tags": ["AI Breakthrough", "Artificial Intelligence", "Tech News", "FutureTech"],
    "slides": [
      {{"text": "Slide 1 sentence...", "prompt": "specific topic visual prompt 1", "badge": "AI DEEP DIVE"}},
      {{"text": "Slide 2 sentence...", "prompt": "specific topic visual prompt 2", "badge": "NEURAL TECH"}},
      {{"text": "Slide 3 sentence...", "prompt": "specific topic visual prompt 3", "badge": "INNOVATION"}},
      {{"text": "Slide 4 sentence...", "prompt": "specific topic visual prompt 4", "badge": "BENCHMARKS"}},
      {{"text": "Slide 5 sentence...", "prompt": "specific topic visual prompt 5", "badge": "INTEGRATION"}},
      {{"text": "Slide 6 sentence...", "prompt": "specific topic visual prompt 6", "badge": "ALIGNMENT"}},
      {{"text": "Slide 7 sentence...", "prompt": "specific topic visual prompt 7", "badge": "FUTURE HORIZON"}},
      {{"text": "Make sure to subscribe to FutureTech Pulse for daily comprehensive AI coverage!", "prompt": "futuristic neon subscribe banner cyan dark", "badge": "SUBSCRIBE FOR MORE"}}
    ]
  }}
}}"""

    # --- PROVIDER 1: Gemini API ---
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            gemini_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
            for g_model in gemini_models:
                try:
                    print(f"   [Provider 1] Gemini API trying model '{g_model}'...")
                    response = client.models.generate_content(
                        model=g_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    content = json.loads(response.text.strip())
                    if isinstance(content, dict) and "short" in content and "long" in content:
                        print(f"   ✅ Gemini ({g_model}) success!")
                        return content
                except Exception as e:
                    print(f"   ⚠️ Gemini model '{g_model}' note: {e}")
                    time.sleep(2)
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
            print(f"   ⚠️ Groq API error: {e}")

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

    # --- PROVIDER 4: Dynamic Procedural Template Generator ---
    print("   ⚠️ All remote AI providers busy. Generating Dynamic Procedural Script Package...")
    run_id = int(time.time()) % 1000
    
    return {
        "short": {
            "title": f"JUST UNVEILED: Autonomous AI Models Take Over Coding! | #Shorts (Ed. #{run_id})",
            "description": "Quick breakdown of latest AI news regarding autonomous software agents. #Shorts #AINews #Tech",
            "thumb_prompt": "humanoid robot engineer glowing holographic cybernetics dark neon tech",
            "tags": ["AI News", "Shorts", "Tech", "Artificial Intelligence"],
            "slides": [
                {"text": "Breaking news in artificial intelligence as researchers unveil a massive breakthrough in autonomous neural networks.", "prompt": "glowing cybernetic AI brain dark cyan neon 8k", "badge": "BREAKING AI"},
                {"text": "This new architecture allows AI models to solve complex software engineering problems ten times faster.", "prompt": "humanoid robot working at holographic terminal", "badge": "NEURAL AGENTS"},
                {"text": "Tech leaders report that this innovation will accelerate enterprise automation across industries.", "prompt": "quantum computing server room glowing blue data streams", "badge": "INDUSTRY IMPACT"},
                {"text": "As deployment expands globally, computer scientists highlight key security and alignment benchmarks.", "prompt": "cybersecurity shield glowing neon circuit background", "badge": "SAFETY & CONTROL"},
                {"text": "Subscribe to FutureTech Pulse right now for daily breaking AI news!", "prompt": "futuristic neon subscribe button circuit background", "badge": "SUBSCRIBE NOW"}
            ]
        },
        "long": {
            "title": f"INSANE: Next-Gen AI Models Pass Critical Human Benchmarks | FutureTech Pulse (Ed. #{run_id})",
            "description": "Comprehensive deep dive into recent artificial intelligence breakthroughs.",
            "thumb_prompt": "quantum supercomputing server matrix glowing neon cybernetic AI brain 8k render",
            "tags": ["AI Breakthrough", "Artificial Intelligence", "Tech News", "FutureTech"],
            "slides": [
                {"text": "Welcome to FutureTech Pulse. Today we are conducting an in-depth exploration into milestone AI developments.", "prompt": "futuristic glowing cybernetic AI brain 8k", "badge": "AI DEEP DIVE"},
                {"text": "Leading research laboratories have officially demonstrated a novel architecture engineered for extreme reasoning.", "prompt": "high tech robotics laboratory dark aesthetic", "badge": "NEURAL ARCHITECTURE"},
                {"text": "Unlike standard transformer architectures, this breakthrough significantly decreases computational latency.", "prompt": "floating holographic code matrix glowing cyan", "badge": "SOFTWARE INNOVATION"},
                {"text": "In benchmark evaluations, the system surpassed existing industry standards in autonomous execution.", "prompt": "supercomputer server room glowing neon circuit trails", "badge": "BENCHMARK PERFORMANCE"},
                {"text": "Major cloud infrastructure providers are preparing to deploy these advanced models to power AI agents.", "prompt": "futuristic digital globe with connected data streams", "badge": "ENTERPRISE INTEGRATION"},
                {"text": "At the same time, security researchers are introducing novel alignment frameworks to ensure reliable operations.", "prompt": "cybersecurity shield visual glowing neon lock code", "badge": "SAFETY & ALIGNMENT"},
                {"text": "Industry experts project that these neural models will become the primary operating engine for tech within the decade.", "prompt": "futuristic city skyline at night floating glowing network", "badge": "FUTURE HORIZON"},
                {"text": "Make sure to subscribe to FutureTech Pulse for daily comprehensive coverage of artificial intelligence!", "prompt": "futuristic neon subscribe banner cyan dark", "badge": "SUBSCRIBE FOR MORE"}
            ]
        }
    }

# ==========================================
# STEP 2: Per-Slide Voiceover Generator
# ==========================================
async def synthesize_slide_audio(text, output_file):
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)
    return output_file

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
# STEP 3: High-CTR Custom Dynamic Thumbnail Generator
# ==========================================
def generate_thumbnail(title_text, badge_text, visual_prompt, is_short=False, output_file="thumbnail.png"):
    width, height = (1080, 1920) if is_short else (1280, 720)
    print(f"🎨 Generating Unique High-CTR Thumbnail ({width}x{height}) -> {output_file}...")
    
    # Use topic-specific prompt with cache-busting seed
    clean_visual = sanitize_text(visual_prompt) if visual_prompt else "futuristic AI brain cybernetic neon dark 8k"
    seed = random.randint(10000, 999999)
    encoded_prompt = urllib.parse.quote(f"{clean_visual}, high contrast dark cyber aesthetic 8k quality render")
    img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}"
    
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
        # Vertical 9:16 Thumbnail
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
            draw.text((90, y_off), line, fill=(250, 204, 21)) # High-CTR Yellow Text
            y_off += 65
    else:
        # Widescreen 16:9 Thumbnail
        draw.rectangle([(80, 80), (650, 160)], fill=(244, 63, 94, 240))
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
            draw.text((110, y_off), line, fill=(250, 204, 21)) # High-CTR Yellow Text
            y_off += 70

    base_img = base_img.convert("RGB")
    base_img.save(output_file)
    print(f"   ✅ Unique Thumbnail created: {output_file}")
    return output_file

# ==========================================
# STEP 4: Per-Slide Synchronized Motion Video Engine with AI Disclaimer
# ==========================================
def render_multislide_video(title_text, slides, is_short=True, output_file="video.mp4"):
    width, height = (1080, 1920) if is_short else (1920, 1080)
    prefix = "short" if is_short else "long"
    print(f"🎬 Rendering Synchronized Multi-Slide Video ({width}x{height}) with {len(slides)} scenes...")

    bg_music_file = get_background_music()
    slide_clips = []

    for idx, slide in enumerate(slides):
        slide_text = sanitize_text(slide.get("text", ""))
        slide_prompt = sanitize_text(slide.get("prompt", "futuristic AI technology dark"))
        slide_badge = sanitize_text(slide.get("badge", "FUTURETECH AI"))

        # 1. Synthesize exact voiceover audio for THIS specific slide
        audio_path = f"voice_{prefix}_slide_{idx}.mp3"
        asyncio.run(synthesize_slide_audio(slide_text, audio_path))
        
        slide_audio = AudioFileClip(audio_path)
        slide_dur = max(slide_audio.duration, 2.0)
        print(f"   Slide {idx+1}/{len(slides)}: Spoken Duration = {slide_dur:.2f}s | Badge = '{slide_badge}'")

        # 2. Fetch unique background image for this slide with cache-busting seed
        seed = random.randint(10000, 999999)
        encoded_prompt = urllib.parse.quote(f"{slide_prompt}, dark cyber aesthetic 8k high quality")
        img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}"
        img_path = f"slide_{prefix}_{idx}.png"

        try:
            res = requests.get(img_url, timeout=12)
            if res.status_code == 200:
                with open(img_path, "wb") as f:
                    f.write(res.content)
            else:
                raise ValueError("Download non-200")
        except Exception:
            img = PIL.Image.new('RGB', (width, height), color=(15, 23, 42))
            img.save(img_path)

        # 3. Create Lower-Third Caption Overlay + AI Content Disclaimer Badge
        overlay_img = PIL.Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(overlay_img)

        if is_short:
            # Top Badge
            draw.rectangle([(80, 140), (1000, 230)], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=3)
            draw.text((120, 168), slide_badge[:30].upper(), fill=(56, 189, 248))

            # AI Content Disclaimer Badge (Top Right Corner)
            draw.rectangle([(620, 60), (1000, 120)], fill=(15, 23, 42, 220), outline=(244, 63, 94), width=2)
            draw.text((640, 80), "[AI-GENERATED MEDIA]", fill=(244, 63, 94))

            # Caption Box
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
            # Top Badge
            draw.rectangle([(100, 60), (750, 130)], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=2)
            draw.text((130, 82), f"FUTURETECH AI | {slide_badge[:25].upper()}", fill=(56, 189, 248))

            # AI Content Disclaimer Badge (Top Right)
            draw.rectangle([(1400, 60), (1820, 120)], fill=(15, 23, 42, 220), outline=(244, 63, 94), width=2)
            draw.text((1430, 80), "[AI-GENERATED CONTENT]", fill=(244, 63, 94))

            # Caption Box
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

        # 4. Compose Base Image + Overlay
        base_pil = PIL.Image.open(img_path).convert("RGBA").resize((width, height))
        composed_pil = PIL.Image.alpha_composite(base_pil, overlay_img).convert("RGB")

        # 5. Continuous Smooth Ken Burns Motion Zoom Frame Generator
        def make_animated_frame(t, pil_img=composed_pil, dur=slide_dur, w=width, h=height):
            progress = min(t / max(dur, 0.1), 1.0)
            scale = 1.0 + 0.15 * progress
            w_scaled, h_scaled = int(w * scale), int(h * scale)
            resized = pil_img.resize((w_scaled, h_scaled), PIL.Image.LANCZOS)
            
            crop_x = (w_scaled - w) // 2
            crop_y = (h_scaled - h) // 2
            cropped = resized.crop((crop_x, crop_y, crop_x + w, crop_y + h))
            
            # Animated progress bar
            frame_draw = PIL.ImageDraw.Draw(cropped)
            bar_y = h - 25 if is_short else h - 15
            frame_draw.rectangle([(0, bar_y), (int(w * progress), bar_y + 15)], fill=(56, 189, 248))
            
            return np.array(cropped)

        scene_clip = VideoClip(make_animated_frame, duration=slide_dur)
        scene_clip = scene_clip.set_audio(slide_audio)
        slide_clips.append(scene_clip)

    # 6. Concatenate all perfectly synced slide clips
    full_video = concatenate_videoclips(slide_clips, method="compose")

    if bg_music_file:
        try:
            total_dur = full_video.duration
            bg_music = AudioFileClip(bg_music_file).volumex(0.07).set_duration(total_dur)
            final_audio = CompositeAudioClip([full_video.audio, bg_music])
            full_video = full_video.set_audio(final_audio)
        except Exception as e:
            print(f"   ⚠️ Music overlay note: {e}")

    full_video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")
    print(f"   ✅ Synchronized Motion Video rendered: {output_file}")
    return output_file

# ==========================================
# STEP 5: YouTube API Uploader with AI Disclosure Metadata
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
    
    # Standard AI Disclosure in description for YouTube Policy Compliance
    full_description = f"{sanitize_text(description)[:4500]}\n\n🤖 AI CONTENT DISCLAIMER: This video features AI-synthesized narration, script analysis, and visual graphics generated for automated tech news reporting."

    body = {
        "snippet": {
            "title": sanitize_text(title)[:100],
            "description": full_description,
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
            print(f"   ⚠️ Could not set thumbnail ({e}). Ensure YouTube channel is phone-verified for custom thumbnails.")

    return video_id

# ==========================================
# MAIN EXECUTION ROUTINE
# ==========================================
if __name__ == "__main__":
    pkg = generate_dual_scripts()
    
    # 1. Render & Upload Short Video (9:16 Vertical)
    short_data = pkg["short"]
    short_slides = short_data.get("slides", [])
    
    thumb_short = generate_thumbnail(
        short_data["title"], 
        "BREAKING AI", 
        short_data.get("thumb_prompt", "futuristic AI brain cybernetic neon"), 
        is_short=True, 
        output_file="thumb_short.png"
    )
    
    short_file = render_multislide_video(
        short_data["title"], 
        short_slides, 
        is_short=True, 
        output_file="short_video.mp4"
    )
    upload_to_youtube(short_file, short_data["title"], short_data["description"], short_data["tags"], thumbnail_file=thumb_short)
    
    # 2. Render & Upload Long Video (16:9 Widescreen)
    long_data = pkg["long"]
    long_slides = long_data.get("slides", [])
    
    thumb_long = generate_thumbnail(
        long_data["title"], 
        "AI BREAKTHROUGH", 
        long_data.get("thumb_prompt", "supercomputer server matrix glowing cyan AI brain"), 
        is_short=False, 
        output_file="thumb_long.png"
    )
    
    long_file = render_multislide_video(
        long_data["title"], 
        long_slides, 
        is_short=False, 
        output_file="long_video.mp4"
    )
    upload_to_youtube(long_file, long_data["title"], long_data["description"], long_data["tags"], thumbnail_file=thumb_long)
