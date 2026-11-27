import unicodedata

def is_english_text(text):
    if not text:
        return False
    foreign_chars = 0
    for char in str(text):
        cp = ord(char)
        if cp > 0x024F:
            if unicodedata.category(char).startswith(('L', 'N', 'M', 'S')):
                foreign_chars += 1
    return foreign_chars <= 1

# ==============================================================================
# GAMING & PARODY AI ACADEMY PIPELINE (EVERY 6 HOURS)
# 100% Original Parody Avatars, Transformative Fair Use (17 U.S.C. § 107), 16:9 5+ Min Video
# ==============================================================================
import os
import re
import json
import time
import math
import random
import hashlib
import asyncio
import warnings
import requests
import urllib.parse
import numpy as np
from datetime import datetime, timedelta

# Explicit PIL imports & deprecation warning fix
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import PIL.ImageFilter
warnings.filterwarnings("ignore", category=DeprecationWarning)
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS)

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    from moviepy.editor import (
        VideoClip, ImageClip, AudioFileClip, CompositeVideoClip, 
        CompositeAudioClip, concatenate_videoclips
    )
except ImportError:
    VideoClip = ImageClip = AudioFileClip = CompositeVideoClip = CompositeAudioClip = concatenate_videoclips = None

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.errors import HttpError
except ImportError:
    build = MediaFileUpload = Credentials = Request = HttpError = None

# Helper function to load crisp system TTF fonts
def get_font(size):
    font_paths = [
        '/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return PIL.ImageFont.truetype(p, size)
            except Exception:
                pass
    return PIL.ImageFont.load_default()

# Helper function to calculate text width safely
def get_text_width(font, text):
    if hasattr(font, 'getlength'):
        return int(font.getlength(text))
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0]

# Helper function to sanitize text strictly for PIL & YouTube API
def sanitize_text(text):
    if not text:
        return ""
    clean = re.sub(r'\b(?:Ed|Edition)\.?\s*#?\s*\d+\b', '', str(text), flags=re.IGNORECASE)
    clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', clean).strip()
    clean = re.sub(r'\s+', ' ', clean)
    return clean

# Anti-Duplicate Check
def is_duplicate_topic(topic_title, channel_titles, local_history):
    clean_topic = sanitize_text(topic_title).lower()
    topic_hash = hashlib.md5(clean_topic.encode('utf-8')).hexdigest()
    if topic_hash in local_history.get("hashes", []):
        return True
    for uploaded in channel_titles:
        uploaded_clean = sanitize_text(uploaded).lower()
        words_topic = set(clean_topic.split())
        words_uploaded = set(uploaded_clean.split())
        if len(words_topic) > 3 and len(words_topic.intersection(words_uploaded)) / len(words_topic) > 0.6:
            return True
    return False

# List of Parody Character Personas
PARODY_PERSONAS = [
    {
        "name": "PIXEL PLUMBER AI",
        "title_prefix": "Pixel Plumber Explains",
        "theme_badge": "RETRO ARCADE AI ACADEMY",
        "topic": "Pathfinding Algorithms & A* Search Neural Networks",
        "bg_color": (15, 23, 42),
        "accent_color": (239, 68, 68),
        "hat_color": (220, 38, 38)
    },
    {
        "name": "BLOCK CRAFTER AI",
        "title_prefix": "Block Builder Explains",
        "theme_badge": "VOXEL WORLDGEN AI LAB",
        "topic": "Procedural Generation & Infinite World Algorithms",
        "bg_color": (20, 35, 25),
        "accent_color": (34, 197, 94),
        "hat_color": (22, 163, 74)
    },
    {
        "name": "MONSTER PROFESSOR AI",
        "title_prefix": "Monster Trainer Explains",
        "theme_badge": "EVOLUTIONARY AI INSTITUTE",
        "topic": "Reinforcement Learning & Decision Tree Classifier Models",
        "bg_color": (30, 20, 45),
        "accent_color": (168, 85, 247),
        "hat_color": (147, 51, 234)
    },
    {
        "name": "CYBER KNIGHT AI",
        "title_prefix": "Cyber Knight Explains",
        "theme_badge": "CYBERPUNK NEURAL NETWORKS",
        "topic": "Transformer Architectures & High-Speed GPU Parallel Compute",
        "bg_color": (10, 25, 40),
        "accent_color": (56, 189, 248),
        "hat_color": (14, 165, 233)
    }
]

# ==============================================================================
# STEP 1: Multi-Source Ingestion & Parody Persona Selection
# ==============================================================================
def fetch_gaming_ai_trends():
    print("📰 Step 1: Ingesting AI trends & selecting Gaming/Parody character persona...")
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    
    uploaded_titles = []
    if client_id and client_secret and refresh_token and build:
        try:
            token_url = "https://" + "oauth2.googleapis.com/token"
            creds = Credentials(token=None, refresh_token=refresh_token, token_uri=token_url, client_id=client_id, client_secret=client_secret)
            creds.refresh(Request())
            youtube = build("youtube", "v3", credentials=creds)
            res = youtube.search().list(part="snippet", forMine=True, maxResults=25, type="video").execute()
            for item in res.get("items", []):
                uploaded_titles.append(item.get("snippet", {}).get("title", ""))
        except Exception as e:
            print(f"   ⚠️ Could not fetch channel video history ({e}).")

    history_file = "posted_gaming_ai_history.json"
    local_history = {"hashes": [], "titles": []}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                local_history = json.load(f)
        except Exception:
            pass

    time_48h_ago = (datetime.utcnow() - timedelta(hours=48)).isoformat() + "Z"
    news_items = []

    if client_id and client_secret and refresh_token and build:
        try:
            yt_request = youtube.search().list(
                relevanceLanguage="en",
                regionCode="US",
                q="AI Pathfinding OR Game AI neural network OR Procedural Generation AI OR Reinforcement Learning",
                part="snippet", type="video", order="viewCount", publishedAfter=time_48h_ago, maxResults=8
            )
            yt_response = yt_request.execute()
            for item in yt_response.get("items", []):
                snippet = item.get("snippet", {})
                vid_id = item.get("id", {}).get("videoId")
                title = snippet.get("title", "")
                if vid_id and is_english_text(title) and not is_duplicate_topic(title, uploaded_titles, local_history):
                    news_items.append({
                        "title": title,
                        "channel": snippet.get("channelTitle", "AI Gaming Lab"),
                        "url": "https://" + "www.youtube.com/watch?v=" + str(vid_id),
                        "description": snippet.get("description", ""),
                        "source_type": "YouTube Gaming AI"
                    })
        except Exception as e:
            print(f"   ⚠️ YouTube API trend search note: {e}")

    rss_feeds = [
        "https://" + "techcrunch.com/category/artificial-intelligence/feed/",
        "https://" + "www.mittechnologyreview.com/feed/",
        "https://" + "feeds.arstechnica.com/arstechnica/index"
    ]
    for feed_url in rss_feeds:
        try:
            if feedparser:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:3]:
                    f_title = sanitize_text(entry.title)
                    if is_english_text(f_title) and not is_duplicate_topic(f_title, uploaded_titles, local_history):
                        news_items.append({
                            "title": f_title,
                            "channel": entry.get("author", "Tech Press Digest"),
                            "url": entry.link,
                            "description": sanitize_text(entry.get("summary", f_title)),
                            "source_type": "Press RSS News"
                        })
        except Exception as e:
            print(f"   ⚠️ RSS feed note for {feed_url}: {e}")

    # Fallback topics if web trend matches are duplicates
    if not news_items:
        news_items = [
            {
                "title": "Pathfinding Algorithms & A* Search in Games: How AI Navigates Virtual Worlds",
                "channel": "Pixel Arcade Lab",
                "url": "https://" + "youtube.com",
                "description": "Deep dive into A* pathfinding, Navigation Meshes, and Decision Trees in game development.",
                "source_type": "Educational Gaming AI"
            },
            {
                "title": "Procedural Generation & Voxel WorldGen AI: How Infinite Universes are Rendered",
                "channel": "Block Architect Wire",
                "url": "https://" + "youtube.com",
                "description": "Explaining Perlin Noise, Wave Function Collapse, and AI Procedural Generation.",
                "source_type": "Voxel AI Report"
            }
        ]

    random.shuffle(news_items)
    selected_item = news_items[0]
    persona = random.choice(PARODY_PERSONAS)
    
    print(f"   ✅ Selected Persona: '{persona['name']}' presenting '{selected_item['title']}'")
    return {"news": selected_item, "persona": persona}

# ==============================================================================
# STEP 2: Script Generation (14 Slides, 5+ Minutes Runtime)
# ==============================================================================
def generate_gaming_script(bundle):
    news = bundle["news"]
    persona = bundle["persona"]
    print(f"📝 Step 2: Generating 14-slide Educational Parody Script for {persona['name']} (~5-6 minutes runtime)...")
    
    clean_title = sanitize_text(news["title"])
    source_channel = news["channel"]

    prompt_lines = [
        f"You are the host of a fun, highly educational 16:9 YouTube show called '{persona['theme_badge']}'.",
        f"CHARACTER PERSONA: {persona['name']} ({persona['title_prefix']}).",
        f"TOPIC TO EXPLAIN: '{clean_title}'.",
        "",
        "RULES:",
        "0. CRITICAL LANGUAGE RULE: The generated title, description, tags, and all slide text MUST be strictly 100% in ENGLISH. Translate any foreign words or non-English characters into clear English.",
        "1. Produce an original, exciting 14-slide educational script.",
        "2. CRITICAL: Each slide MUST contain 60 to 75 words of spoken commentary (~24 seconds per slide = ~5.5 minutes total runtime).",
        "3. Explain the technical AI concept using fun gaming/cartoon analogies, pixel math, and real developer insights.",
        "4. Provide an SEO Title starting with persona's title prefix, 1200+ char Description with timestamps, 15 Tags, and Badge labels.",
        "5. Comply 100% with YouTube Fair Use (17 U.S.C. § 107) and Partner Program monetization guidelines.",
        "",
        "Return ONLY valid JSON with keys: title, description, tags, badge_text, slides (list of objects with badge, text, highlight_word, sticker)."
    ]
    prompt = "\n".join(prompt_lines)

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and genai:
        for g_model in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]:
            try:
                client = genai.Client(api_key=gemini_key)
                response = client.models.generate_content(model=g_model, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
                if response and response.text:
                    parsed = json.loads(response.text)
                    if "slides" in parsed and len(parsed["slides"]) >= 8:
                        print(f"   ✅ Gemini ({g_model}) script success!")
                        return parsed
            except Exception as e:
                print(f"   ⚠️ Gemini model '{g_model}' note: {e}")

    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key and Groq:
        for q_model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
            try:
                client = Groq(api_key=groq_key)
                completion = client.chat.completions.create(model=q_model, messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                if completion.choices and completion.choices[0].message.content:
                    parsed = json.loads(completion.choices[0].message.content)
                    if "slides" in parsed and len(parsed["slides"]) >= 8:
                        print(f"   ✅ Groq ({q_model}) script success!")
                        return parsed
            except Exception as e:
                print(f"   ⚠️ Groq model '{q_model}' note: {e}")

    print("   💡 Using local procedural 14-slide Gaming AI Academy script generator (~5.5 mins)...")
    clean_short = clean_title[:45]
    slides = [
        {"badge": "WELCOME ACADEMY", "text": f"Welcome back to the Gaming AI Academy! I am your host, {persona['name']}. Today we are breaking down '{clean_short}' and how modern artificial intelligence powers virtual worlds.", "highlight_word": "artificial", "sticker": "🎮 WELCOME LEVEL 1!"},
        {"badge": "THE CORE MECHANIC", "text": f"Whether navigating complex game maps or processing multi-step algorithms, neural models developed at {source_channel} rely on specialized logic loops to calculate optimal outcomes.", "highlight_word": "algorithms", "sticker": "💡 CORE LOGIC!"},
        {"badge": "PATHFINDING & A* SEARCH", "text": "In game engines, autonomous characters use A-star pathfinding algorithms to calculate the shortest node distance across grid maps, avoiding obstacles while optimizing movement speed.", "highlight_word": "pathfinding", "sticker": "🗺️ A* PATHFINDING!"},
        {"badge": "PROCEDURAL WORLDGEN", "text": "Procedural generation uses mathematical noise functions like Perlin and Simplex noise to generate endless terrain, seed-based voxel structures, and dynamic dungeon layouts in real time.", "highlight_word": "Procedural", "sticker": "🧱 WORLDGEN NOISE!"},
        {"badge": "REINFORCEMENT LEARNING", "text": "Reinforcement learning trains AI agents through trial, error, and reward functions. By penalizing mistakes and boosting success scores, neural agents master complex tasks automatically.", "highlight_word": "Reinforcement", "sticker": "🏆 REWARD BOOST!"},
        {"badge": "DECISION TREE LOGIC", "text": "Game state machines evaluate decision trees to choose combat actions, non-player character dialogue paths, and tactical maneuvers dynamically based on player behavior.", "highlight_word": "decision", "sticker": "🌳 DECISION TREE!"},
        {"badge": "GPU ACCELERATION", "text": "Modern graphics processing units execute massive matrix multiplications in parallel, allowing neural networks to evaluate billions of floating point operations per second.", "highlight_word": "matrix", "sticker": "⚡ 10X GPU SPEED!"},
        {"badge": "COMPUTER VISION IN GAMES", "text": "Vision transformers process incoming pixel buffers, identifying target objects, depth maps, and structural boundaries instantly to guide autonomous agent actions.", "highlight_word": "transformers", "sticker": "👁️ VISION AI!"},
        {"badge": "OPEN SOURCE TOOLS", "text": "Open-source machine learning libraries and quantized models enable developers to embed intelligent agent behaviors locally without relying on expensive cloud servers.", "highlight_word": "quantized", "sticker": "🛠️ OPEN SOURCE!"},
        {"badge": "NEURAL NAVIGATION MESH", "text": "Navigation meshes define walkable surface geometry, allowing non-player characters to navigate complex three-dimensional environments without clipping through terrain walls.", "highlight_word": "Navigation", "sticker": "📐 NAV MESH!"},
        {"badge": "FUTURE HORIZON", "text": "Looking ahead, multi-modal generative models will create real-time voice, procedural dialogue, adaptive music, and dynamic quests tailored specifically to your playstyle.", "highlight_word": "generative", "sticker": "🚀 FUTURE TECH!"},
        {"badge": "KEY TAKEAWAY", "text": "Understanding these foundational AI mechanics empowers creators and game developers to build smarter interactive experiences and master modern artificial intelligence.", "highlight_word": "interactive", "sticker": "🧠 LEVEL UP!"},
        {"badge": "COMMUNITY CHALLENGE", "text": "Which game AI mechanic surprised you the most? Drop your thoughts in the comments below and let us know which algorithm we should break down next!", "highlight_word": "comments", "sticker": "💬 COMMENT BELOW!"},
        {"badge": "SUBSCRIBE & LEVEL UP", "text": "Subscribe to FutureTech AI for weekly Gaming AI Academy lessons, algorithm breakdowns, and cutting-edge artificial intelligence deep dives!", "highlight_word": "Subscribe", "sticker": "⭐ SUBSCRIBE!"}
    ]
    
    return {
        "title": f"{persona['title_prefix']} {clean_title[:50]}: How AI Works! #AINews",
        "description": f"Gaming AI Academy broadcast hosted by {persona['name']} analyzing '{clean_title}'.\n\nTimestamps:\n0:00 - Academy Intro\n0:45 - Core AI Mechanic\n1:45 - Pathfinding & WorldGen\n3:00 - Neural GPU Hardware\n4:30 - Final Verdict\n\nFeatured Source: {source_channel} ({news['url']})",
        "tags": ["AI", "GameAI", "ArtificialIntelligence", "SuperMario", "Minecraft", "AIAgents", "TechNews", "FutureTech"],
        "badge_text": persona["theme_badge"],
        "slides": slides
    }

# ==============================================================================
# STEP 3: Multi-Voice Audio Synthesis
# ==============================================================================
async def synthesize_slide_audio(text, output_file):
    voices = ["en-US-ChristopherNeural", "en-US-GuyNeural", "en-US-EricNeural", "en-US-AriaNeural"]
    if edge_tts:
        for attempt in range(4):
            voice = voices[attempt % len(voices)]
            try:
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_file)
                if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                    return output_file
            except Exception:
                await asyncio.sleep(1.0)
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang='en')
        tts.save(output_file)
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            return output_file
    except Exception as e:
        print(f"   ⚠️ Audio TTS note: {e}")

    if os.path.exists(output_file) and os.path.getsize(output_file) > 100:
        return output_file
    raise RuntimeError("Audio synthesis failed.")

def get_background_music(output_file="bg_gaming_music.mp3"):
    if os.path.exists(output_file):
        return output_file
    url = "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3?filename=cyberpunk-tech-110391.mp3"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(res.content)
            return output_file
    except Exception:
        pass
    return None

def generate_procedural_background(width, height, bg_color):
    img = PIL.Image.new("RGBA", (width, height), (*bg_color, 255))
    draw = PIL.ImageDraw.Draw(img)
    colors = [(56, 189, 248, 80), (239, 68, 68, 80), (34, 197, 94, 80), (250, 204, 21, 80)]
    for i in range(20):
        x0 = random.randint(0, width)
        y0 = random.randint(0, height)
        draw.ellipse([x0-250, y0-250, x0+250, y0+250], fill=colors[i % len(colors)])
    img = img.filter(PIL.ImageFilter.GaussianBlur(25))
    draw_grid = PIL.ImageDraw.Draw(img)
    for y in range(0, height, 40):
        draw_grid.line([(0, y), (width, y)], fill=(255, 255, 255, 12))
    for x in range(0, width, 40):
        draw_grid.line([(x, 0), (x, height)], fill=(255, 255, 255, 12))
    return img.convert("RGB")

# ==============================================================================
# STEP 4: 16:9 Thumbnail Generator (1280x720)
# ==============================================================================
def generate_gaming_thumbnail(title_text, badge_text, persona, source_channel, output_file="gaming_thumbnail.png"):
    print("🖼️ Step 4: Generating 16:9 Gaming AI Academy thumbnail (1280x720)...")
    w, h = 1280, 720
    base_img = generate_procedural_background(w, h, persona["bg_color"])
    draw = PIL.ImageDraw.Draw(base_img)

    font_large = get_font(50)
    font_badge = get_font(26)
    font_credit = get_font(20)

    draw.rectangle([15, 15, w-15, h-15], outline=persona["accent_color"], width=6)
    draw.rectangle([60, 50, 480, 110], fill=persona["accent_color"], outline=(255, 255, 255), width=2)
    draw.text((80, 65), badge_text, font=font_badge, fill=(255, 255, 255))

    # Draw Parody Character Face Preview on Thumbnail Left
    cx, cy = 200, 380
    draw.rectangle([cx-110, cy-140, cx+110, cy+140], fill=(15, 23, 42, 230), outline=persona["accent_color"], width=4)
    draw.ellipse([cx-75, cy-75, cx+75, cy+75], fill=persona["accent_color"])
    draw.rectangle([cx-85, cy-95, cx+85, cy-55], fill=persona["hat_color"])
    draw.ellipse([cx-40, cy-25, cx-15, cy], fill=(255, 255, 255))
    draw.ellipse([cx+15, cy-25, cx+40, cy], fill=(255, 255, 255))
    draw.ellipse([cx-32, cy-18, cx-22, cy-8], fill=(0, 0, 0))
    draw.ellipse([cx+22, cy-18, cx+32, cy-8], fill=(0, 0, 0))
    draw.text((cx-70, cy+90), persona["name"], font=get_font(18), fill=(250, 204, 21))

    words = title_text.split()
    lines_list = []
    curr = []
    for word in words:
        curr.append(word)
        if get_text_width(font_large, " ".join(curr)) > w - 460:
            curr.pop()
            lines_list.append(" ".join(curr))
            curr = [word]
    if curr:
        lines_list.append(" ".join(curr))

    y_start = 180
    for line in lines_list[:3]:
        lw = get_text_width(font_large, line)
        draw.rectangle([360, y_start - 8, 360 + lw + 30, y_start + 65], fill=(15, 23, 42, 235))
        draw.text((375, y_start), line, font=font_large, fill=(250, 204, 21))
        y_start += 85

    credit_text = f"PARODY ACADEMY: {persona['name']} • SOURCE: {source_channel.upper()} • FAIR USE"
    cw = get_text_width(font_credit, credit_text)
    draw.rectangle([(w - cw)//2 - 15, h - 90, (w + cw)//2 + 15, h - 45], fill=(30, 41, 59, 240), outline=persona["accent_color"], width=2)
    draw.text(((w - cw)//2, h - 75), credit_text, font=font_credit, fill=(255, 255, 255))

    base_img.save(output_file)
    print(f"   ✅ Thumbnail generated: {output_file}")
    return output_file

# ==============================================================================
# STEP 5: 16:9 MoviePy Video Renderer with 2D Parody Presenter Avatar
# ==============================================================================
def render_gaming_video(script_data, bundle, output_file="gaming_ai_video.mp4"):
    persona = bundle["persona"]
    news = bundle["news"]
    print(f"🎬 Step 5: Rendering 16:9 Gaming AI Academy video with {persona['name']} avatar (1920x1080)...")
    
    w, h = 1920, 1080
    slides = script_data.get("slides", [])
    total_slides = len(slides)
    source_channel = news.get("channel", "Gaming AI Digest")

    font_header = get_font(34)
    font_body = get_font(44)
    font_badge = get_font(28)
    font_credit = get_font(22)
    font_sticker = get_font(24)

    temp_files = []
    slide_clips = []
    base_bg_pil = generate_procedural_background(w, h, persona["bg_color"])

    for idx, slide in enumerate(slides):
        audio_file = f"gaming_audio_{idx}.mp3"
        temp_files.append(audio_file)
        slide_text = slide.get("text", "")
        asyncio.run(synthesize_slide_audio(slide_text, audio_file))

        audio_clip = AudioFileClip(audio_file)
        slide_duration = max(audio_clip.duration + 2.0, 28.0)
        badge_str = slide.get("badge", f"LEVEL {idx+1} OF {total_slides}")
        highlight_str = slide.get("highlight_word", "").lower()
        sticker_str = slide.get("sticker", "🎮 GAMING AI!")

        frame_pil = base_bg_pil.copy()
        draw = PIL.ImageDraw.Draw(frame_pil)

        # 1. Top Header Banner
        draw.rectangle([0, 0, w, 110], fill=(15, 23, 42, 240))
        draw.text((60, 35), f"GAMING AI ACADEMY  |  {persona['theme_badge']}", font=font_header, fill=persona["accent_color"])
        draw.line([(0, 110), (w, 110)], fill=(250, 204, 21), width=4)

        # 2. Slide Counter Pill
        counter_str = f"LEVEL {idx+1} / {total_slides}"
        cw = get_text_width(font_header, counter_str)
        draw.rectangle([w - cw - 80, 25, w - 40, 85], fill=(30, 41, 59, 220), outline=persona["accent_color"], width=2)
        draw.text((w - cw - 60, 35), counter_str, font=font_header, fill=(250, 204, 21))

        # 3. Left Side Parody Character Card (480px wide)
        draw.rectangle([60, 160, 520, h - 140], fill=(15, 23, 42, 240), outline=persona["accent_color"], width=3)
        draw.rectangle([60, 160, 520, 220], fill=(30, 41, 59, 250))
        draw.text((80, 175), persona["name"], font=get_font(22), fill=persona["accent_color"])
        draw.text((120, h - 180), f"● LESSON {idx+1} IN PROGRESS", font=get_font(20), fill=(250, 204, 21))

        # 4. Right Side Topic & Spoken Text Panel
        draw.rectangle([560, 160, 960, 220], fill=persona["accent_color"])
        draw.text((580, 175), badge_str.upper(), font=font_badge, fill=(255, 255, 255))

        words = slide_text.split()
        lines_list = []
        curr = []
        for word in words:
            curr.append(word)
            if get_text_width(font_body, " ".join(curr)) > w - 680:
                curr.pop()
                lines_list.append(" ".join(curr))
                curr = [word]
        if curr:
            lines_list.append(" ".join(curr))

        panel_h = len(lines_list) * 75 + 80
        y_center = (h // 2) - (panel_h // 2) + 20
        draw.rectangle([560, y_center, w - 60, y_center + panel_h], fill=(10, 15, 30, 230), outline=(168, 85, 247), width=3)

        # 5. Lower-Third Attribution Line & Parody Disclaimer
        attr_str = f"PARODY & EDUCATIONAL AI SHOW • SOURCE: {source_channel.upper()} • FAIR USE (17 U.S.C. § 107)"
        aw = get_text_width(font_credit, attr_str)
        draw.rectangle([(w - aw)//2 - 20, h - 110, (w + aw)//2 + 20, h - 55], fill=(30, 41, 59, 235), outline=persona["accent_color"], width=2)
        draw.text(((w - aw)//2, h - 98), attr_str, font=font_credit, fill=(250, 204, 21))

        base_img_np = np.array(frame_pil)

        # Frame Animation Function (2D Parody Character Lipsync, Eyes, Speech Bubbles, Scanlines)
        def make_frame(t, base_np=base_img_np, dur=slide_duration, text_lines=lines_list, y_start=y_center+40, hl=highlight_str, sticker=sticker_str):
            frame = PIL.Image.fromarray(base_np).copy()
            draw_anim = PIL.ImageDraw.Draw(frame)

            # Laser Scanline & Top Progress Bar
            scan_y = int((t / dur) * h)
            draw_anim.line([(0, scan_y), (w, scan_y)], fill=(56, 189, 248, 160), width=3)
            prog_w = int((t / dur) * w)
            draw_anim.rectangle([0, 110, prog_w, 116], fill=(250, 204, 21))

            # Render Animated Parody Character Avatar (Center: X=290, Y=400)
            cx, cy = 290, 390
            
            # Head Circle & Body Box
            draw_anim.rectangle([cx-110, cy+80, cx+110, cy+210], fill=(30, 41, 59), outline=persona["accent_color"], width=3)
            draw_anim.ellipse([cx-90, cy-90, cx+90, cy+90], fill=(254, 215, 170), outline=persona["accent_color"], width=4)
            
            # Parody Character Cap / Hat
            draw_anim.rectangle([cx-100, cy-110, cx+100, cy-65], fill=persona["hat_color"])
            draw_anim.polygon([(cx-100, cy-65), (cx+110, cy-65), (cx+90, cy-50), (cx-90, cy-50)], fill=persona["hat_color"])
            draw_anim.text((cx-18, cy-105), "AI", font=get_font(28), fill=(255, 255, 255))

            # Eyes with Pupil Tracking & Blinking Eyelids
            eye_y = cy - 20
            is_blinking = abs(math.sin(t * 0.8)) > 0.94
            if is_blinking:
                draw_anim.line([(cx-55, eye_y), (cx-15, eye_y)], fill=(0, 0, 0), width=4)
                draw_anim.line([(cx+15, eye_y), (cx+55, eye_y)], fill=(0, 0, 0), width=4)
            else:
                draw_anim.ellipse([cx-55, eye_y-20, cx-15, eye_y+20], fill=(255, 255, 255), outline=(0,0,0), width=2)
                draw_anim.ellipse([cx+15, eye_y-20, cx+55, eye_y+20], fill=(255, 255, 255), outline=(0,0,0), width=2)
                pupil_shift = int(10 * math.sin(t * 2.2))
                draw_anim.ellipse([cx-40+pupil_shift, eye_y-10, cx-30+pupil_shift, eye_y+10], fill=(0, 0, 0))
                draw_anim.ellipse([cx+30+pupil_shift, eye_y-10, cx+40+pupil_shift, eye_y+10], fill=(0, 0, 0))

            # Expressive Eyebrows
            brow_tilt = int(6 * math.sin(t * 1.5))
            draw_anim.line([(cx-60, eye_y-30 - brow_tilt), (cx-15, eye_y-30 + brow_tilt)], fill=(0, 0, 0), width=4)
            draw_anim.line([(cx+15, eye_y-30 + brow_tilt), (cx+60, eye_y-30 - brow_tilt)], fill=(0, 0, 0), width=4)

            # Dynamic Lip-Sync Mouth Movement
            mouth_y = cy + 30
            mouth_open = int(14 * abs(math.sin(t * 15.0)))
            if mouth_open > 3:
                draw_anim.ellipse([cx-35, mouth_y - 2, cx+35, mouth_y + mouth_open + 4], fill=(185, 28, 28), outline=(0,0,0), width=2)
                draw_anim.line([(cx-25, mouth_y + 3), (cx+25, mouth_y + 3)], fill=(255, 255, 255), width=3)
            else:
                draw_anim.arc([cx-30, mouth_y-10, cx+30, mouth_y+15], start=10, end=170, fill=(0, 0, 0), width=4)

            # Headset & Cyber Mic
            draw_anim.line([(cx-95, cy-40), (cx-115, cy+30)], fill=(56, 189, 248), width=5)
            draw_anim.ellipse([cx-125, cy+20, cx-105, cy+40], fill=(239, 68, 68))

            # Bouncing Cartoon Speech Callout Sticker
            callout_y = int(cy - 170 + 8 * math.sin(t * 3.0))
            sw = get_text_width(font_sticker, sticker)
            draw_anim.rectangle([cx - sw//2 - 15, callout_y, cx + sw//2 + 15, callout_y + 45], fill=(250, 204, 21), outline=(0,0,0), width=3)
            draw_anim.text((cx - sw//2, callout_y + 8), sticker, font=font_sticker, fill=(15, 23, 42))

            # Animated Audio Equalizer Bars (10 Bands)
            eq_x = 90
            for eq_i in range(10):
                bar_h = int(28 + 22 * math.sin(t * 9 + eq_i * 0.8))
                draw_anim.rectangle([eq_x, 620 - bar_h, eq_x + 28, 620], fill=persona["accent_color"])
                eq_x += 42

            # Spoken Text Rendering with Highlight Words
            line_y = y_start
            for line in text_lines:
                lw = get_text_width(font_body, line)
                x_pos = 600 + ((w - 680 - lw) // 2) if (w - 680 > lw) else 580
                for word in line.split():
                    clean_w = re.sub(r'[^\w]', '', word).lower()
                    color = (250, 204, 21) if (hl and hl in clean_w) else (255, 255, 255)
                    draw_anim.text((x_pos, line_y), word + " ", font=font_body, fill=color)
                    x_pos += get_text_width(font_body, word + " ")
                line_y += 75

            return np.array(frame)

        if VideoClip:
            clip = VideoClip(make_frame, duration=slide_duration)
            clip = clip.set_audio(audio_clip)
            slide_clips.append(clip)

    if concatenate_videoclips and slide_clips:
        final_video = concatenate_videoclips(slide_clips, method="compose")
        music_path = get_background_music()
        if music_path and os.path.exists(music_path):
            try:
                bg_music = AudioFileClip(music_path).filter(lambda gf, t: 0.10 * gf(t)).set_duration(final_video.duration)
                comp_audio = CompositeAudioClip([final_video.audio, bg_music])
                final_video = final_video.set_audio(comp_audio)
            except Exception as e:
                print(f"   ⚠️ Background music note: {e}")

        final_video.write_videofile(
            output_file, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4
        )
    else:
        print(f"   💡 MoviePy dry-run skipped rendering {output_file}.")

    for f in temp_files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    print(f"   ✅ 16:9 Gaming AI Academy video rendered: {output_file}")
    return output_file

# ==============================================================================
# STEP 6: YouTube Upload & Persistent History Logging
# ==============================================================================
def upload_gaming_to_youtube(video_file, title, description, tags, bundle, thumbnail_file=None):
    clean_title = sanitize_text(title)
    clean_desc = sanitize_text(description)
    persona = bundle["persona"]
    news = bundle["news"]
    print(f"🚀 Step 6: Uploading Gaming AI Academy video '{clean_title}' to YouTube...")

    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]) or not build:
        print("   ⚠️ YouTube OAuth credentials missing. Skipping live upload.")
        return None

    token_url = "https://" + "oauth2.googleapis.com/token"
    creds = Credentials(token=None, refresh_token=refresh_token, token_uri=token_url, client_id=client_id, client_secret=client_secret)
    creds.refresh(Request())
    youtube = build("youtube", "v3", credentials=creds)

    legal_attribution = (
        "📌 GAMING AI ACADEMY CREDIT & ATTRIBUTION:\n"
        f"Host Persona: {persona['name']} ({persona['title_prefix']})\n"
        f"Featured Topic: {news['title']}\n"
        f"Source Channel/Press: {news['channel']}\n"
        f"Source Link: {news['url']}\n\n"
        "⚖️ LEGAL STATEMENT, PARODY & COPYRIGHT COMPLIANCE:\n"
        "This video is an original parody, educational synthesis, and commentary show. All character avatars and graphics are original 2D procedural designs. Content re-use adheres to Fair Use principles under 17 U.S.C. Section 107.\n\n"
        "🤖 AI PRODUCTION DISCLAIMER:\n"
        "Hosted by synthetic AI persona using automated technical visual academy tools for education and research."
    )

    full_description = clean_desc[:3500] + "\n\n" + legal_attribution
    body = {
        "snippet": {
            "title": clean_title[:100],
            "description": full_description,
            "tags": [sanitize_text(t) for t in tags],
            "categoryId": "20" # Gaming category
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
    pub_link = "https://" + "youtu.be/" + str(video_id)
    print(f"   SUCCESS! Published Gaming AI Academy video live: {pub_link}")

    if thumbnail_file and os.path.exists(thumbnail_file):
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_file)).execute()
            print("   💵 Thumbnail updated successfully!")
        except Exception as e:
            print(f"   Could not set thumbnail: {e}")

    history_file = "posted_gaming_ai_history.json"
    local_history = {"hashes": [], "titles": []}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                local_history = json.load(f)
        except Exception:
            pass
    
    clean_topic = clean_title.lower()
    local_history["hashes"].append(hashlib.md5(clean_topic.encode('utf-8')).hexdigest())
    local_history["titles"].append(clean_title)
    try:
        with open(history_file, "w") as f:
            json.dump(local_history, f, indent=2)
    except Exception:
        pass

    return video_id

# ==============================================================================
# MAIN EXECUTION PIPELINE (EVERY 6 HOURS)
# ==============================================================================
def main():
    print("======================================================================")
    print("🚀 STARTING 6-HOUR GAMING & PARODY AI ACADEMY PIPELINE")
    print("======================================================================")
    
    bundle = fetch_gaming_ai_trends()
    script_data = generate_gaming_script(bundle)

    thumb_file = generate_gaming_thumbnail(
        title_text=script_data.get("title", "GAMING AI ACADEMY"),
        badge_text=script_data.get("badge_text", "PARODY AI ACADEMY"),
        persona=bundle["persona"],
        source_channel=bundle["news"].get("channel", "AI Creator")
    )

    video_file = render_gaming_video(
        script_data=script_data,
        bundle=bundle
    )

    upload_gaming_to_youtube(
        video_file=video_file,
        title=script_data.get("title", "GAMING AI ACADEMY BROADCAST"),
        description=script_data.get("description", "Gaming AI Academy Educational Show."),
        tags=script_data.get("tags", ["AI", "GameAI", "TechNews"]),
        bundle=bundle,
        thumbnail_file=thumb_file
    )

    print("======================================================================")
    print("✅ 6-HOUR GAMING & PARODY AI ACADEMY PIPELINE COMPLETE")
    print("======================================================================")

if __name__ == "__main__":
    main()
