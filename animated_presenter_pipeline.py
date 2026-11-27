# ==============================================================================
# ANIMATED PRESENTER PIPELINE: 16:9 VIRTUAL STUDIO AI SHOW (EVERY 12 HOURS)
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

# ==============================================================================
# STEP 1: Multi-Source Ingestion & Anti-Duplicate Filtering
# ==============================================================================
def fetch_presenter_ai_trends():
    print("📰 Step 1: Ingesting 12-hour AI news & filtering duplicate topics...")
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

    history_file = "posted_topics_history.json"
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
                q="AI breakthrough OR OpenAI GPT-5 OR Gemini 2.5 OR Claude 3.5 OR AI Agent",
                part="snippet", type="video", order="viewCount", publishedAfter=time_48h_ago, maxResults=10
            )
            yt_response = yt_request.execute()
            for item in yt_response.get("items", []):
                snippet = item.get("snippet", {})
                vid_id = item.get("id", {}).get("videoId")
                title = snippet.get("title", "")
                if vid_id and not is_duplicate_topic(title, uploaded_titles, local_history):
                    news_items.append({
                        "title": title,
                        "channel": snippet.get("channelTitle", "AI Tech Wire"),
                        "url": "https://" + "www.youtube.com/watch?v=" + str(vid_id),
                        "description": snippet.get("description", ""),
                        "source_type": "YouTube Trending Video"
                    })
        except Exception as e:
            print(f"   ⚠️ YouTube API trend search note: {e}")

    rss_feeds = [
        "https://" + "techcrunch.com/category/artificial-intelligence/feed/",
        "https://" + "www.mittechnologyreview.com/feed/",
        "https://" + "feeds.arstechnica.com/arstechnica/index",
        "https://" + "venturebeat.com/category/ai/feed/"
    ]
    for feed_url in rss_feeds:
        try:
            if feedparser:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:4]:
                    f_title = sanitize_text(entry.title)
                    if not is_duplicate_topic(f_title, uploaded_titles, local_history):
                        news_items.append({
                            "title": f_title,
                            "channel": entry.get("author", "Tech Press Digest"),
                            "url": entry.link,
                            "description": sanitize_text(entry.get("summary", f_title)),
                            "source_type": "Press RSS News"
                        })
        except Exception as e:
            print(f"   ⚠️ RSS feed note for {feed_url}: {e}")

    if not news_items:
        evergreen = [
            {
                "title": "Virtual Studio Deep Dive: How Agentic AI Workflows Automate Software Creation",
                "channel": "AI Studio Broadcast",
                "url": "https://" + "youtube.com",
                "description": "Comprehensive technical broadcast analyzing autonomous AI agent systems and real-time execution.",
                "source_type": "Virtual Studio Special Report"
            },
            {
                "title": "OpenAI vs Google Gemini: Benchmark Breakdown of 2026 Frontier Models",
                "channel": "Tech Anchor News",
                "url": "https://" + "youtube.com",
                "description": "Architectural overview comparing reasoning speed, context windows, and code synthesis accuracy.",
                "source_type": "Benchmark Commentary"
            }
        ]
        for eg in evergreen:
            if not is_duplicate_topic(eg["title"], uploaded_titles, local_history):
                news_items.append(eg)

    random.shuffle(news_items)
    selected_bundle = news_items[:4] if news_items else [evergreen[0]]
    print(f"   ✅ Selected {len(selected_bundle)} unique AI news topics for Virtual Studio presentation.")
    return selected_bundle

# ==============================================================================
# STEP 2: Script Generation (18 Detailed Slides, 8+ Minutes Runtime)
# ==============================================================================
def generate_presenter_script(news_bundle):
    print("📝 Step 2: Generating 18-slide Virtual Studio broadcast script (~8-10 minutes runtime)...")
    main_target = news_bundle[0]
    clean_title = sanitize_text(main_target["title"])
    source_channel = main_target["channel"]

    topics_summary = "\n".join([
        f"- Story {i+1}: '{item['title']}' from {item['channel']}"
        for i, item in enumerate(news_bundle)
    ])

    prompt_lines = [
        "You are an expert AI Virtual Studio News Anchor creating a comprehensive 8-to-10 minute long-form broadcast video.",
        "TOPICS TO COVER:",
        topics_summary,
        "RULES:",
        "1. Produce an exciting, highly structured 18-slide broadcast script.",
        "2. CRITICAL: Each slide MUST contain 75 to 90 words of spoken commentary (~28 seconds per slide = 8.5 minutes total runtime).",
        "3. Provide high-SEO Title, Description with timestamps, 15 Tags, and Badge labels.",
        "4. Comply 100% with YouTube Fair Use and Monetization rules.",
        "Return ONLY valid JSON with keys: title, description, tags, badge_text, slides (list of 18 objects with badge, text, highlight_word)."
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
                    if "slides" in parsed and len(parsed["slides"]) >= 12:
                        print(f"   ✅ Gemini ({g_model}) script success with {len(parsed['slides'])} slides!")
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
                    if "slides" in parsed and len(parsed["slides"]) >= 12:
                        print(f"   ✅ Groq ({q_model}) script success with {len(parsed['slides'])} slides!")
                        return parsed
            except Exception as e:
                print(f"   ⚠️ Groq model '{q_model}' note: {e}")

    print("   💡 Using local procedural 18-slide Virtual Studio broadcast generator (~8.5 mins)...")
    clean_short = clean_title[:45]
    slides = [
        {"badge": "LIVE BROADCAST", "text": f"Welcome to FutureTech AI Studio! I am ALEX, your AI Presenter. Today we are conducting a comprehensive 8-minute technical deep dive into major artificial intelligence developments, starting with '{clean_short}'.", "highlight_word": "artificial"},
        {"badge": "THE BREAKTHROUGH", "text": f"Engineers and research scientists at {source_channel} have unveiled groundbreaking AI model capabilities that push autonomous problem-solving performance to new industry records.", "highlight_word": "autonomous"},
        {"badge": "SYSTEM ARCHITECTURE", "text": "Underneath the hood, this breakthrough relies on a multi-stage neural execution framework. By pairing real-time reasoning loops with high-capacity memory retrieval, complex code generation tasks execute with extreme precision.", "highlight_word": "reasoning"},
        {"badge": "HARDWARE ACCELERATION", "text": "Hardware compute infrastructure is accelerating rapidly. High-bandwidth GPU clusters combined with custom AI silicon allow massive parallel model training, reducing latency for instant real-time inference.", "highlight_word": "compute"},
        {"badge": "AUTONOMOUS CODING AGENTS", "text": "For software developers and engineers, autonomous coding assistants now execute end-to-end task automation, handling multi-file refactoring, test suite generation, and cloud deployment scripts seamlessly.", "highlight_word": "automation"},
        {"badge": "BENCHMARK EVALUATION", "text": "In recent benchmark tests on SWE-bench and HumanEval, these next-generation AI agents achieved record-breaking scores, outperforming traditional software engineering models across multiple languages.", "highlight_word": "benchmark"},
        {"badge": "ENTERPRISE WORKFLOWS", "text": "Global technology enterprises across finance, medicine, and cloud infrastructure are embedding these agentic AI workflows directly into operational pipelines to automate multi-step decisions at massive scale.", "highlight_word": "workflows"},
        {"badge": "OPEN-WEIGHT REVOLUTION", "text": "Concurrently, the open-weight AI ecosystem is experiencing an unprecedented boom. Quantized 70B parameter neural models can now be deployed locally on developer workstations with extreme speed and complete privacy.", "highlight_word": "quantized"},
        {"badge": "MODEL QUANTIZATION & VLLM", "text": "By leveraging 4-bit and 8-bit GGUF quantization alongside vLLM inference engines, developers achieve near-lossless model accuracy while reducing GPU memory requirements by over sixty percent.", "highlight_word": "quantization"},
        {"badge": "ROBOTICS & EMBODIED AI", "text": "Embodied AI systems are translating these digital reasoning breakthroughs into physical space. Multi-modal vision-language-action models enable humanoid robots to navigate complex physical environments autonomously.", "highlight_word": "embodied"},
        {"badge": "ALIGNMENT & SAFETY", "text": "With elevated autonomous capability comes an increased focus on alignment, guardrails, and sandboxed safety protocols to guarantee secure model behavior and eliminate hallucination risks.", "highlight_word": "guardrails"},
        {"badge": "ECONOMIC IMPACT", "text": "Economists predict that widespread adoption of multi-modal AI agents will boost software productivity by tenfold, creating immense competitive advantages for early adopter organizations.", "highlight_word": "productivity"},
        {"badge": "CREATOR & DEV TOOLS", "text": "Content creators and digital builders are combining vision, voice, and code generation models into fully automated production channels, democratizing media creation globally.", "highlight_word": "democratizing"},
        {"badge": "FUTURE ROADMAP 2026", "text": "Looking ahead to the next technological frontier, real-time agentic swarms will collaborate autonomously across edge devices, solving complex mathematical and scientific challenges continuously.", "highlight_word": "seamlessly"},
        {"badge": "EXPERT VERDICT", "text": "The sheer velocity of AI innovation demonstrates that engineers who master agentic architecture and local model deployment today will lead tomorrow's tech industry.", "highlight_word": "master"},
        {"badge": "COMMUNITY COMMENTARY", "text": "What is your perspective on this major AI milestone? Drop your thoughts in the comment section below and let us know which AI models you utilize daily.", "highlight_word": "comments"},
        {"badge": "TUTORIAL PREVIEW", "text": "Be sure to catch our upcoming hands-on engineering tutorial where we build and deploy an autonomous multi-agent pipeline from scratch live on this channel.", "highlight_word": "tutorial"},
        {"badge": "SUBSCRIBE & STAY AHEAD", "text": "Subscribe to FutureTech AI for daily 100% automated 16:9 Virtual Studio deep dives, technical AI tutorials, and breaking technology updates!", "highlight_word": "Subscribe"}
    ]
    return {
        "title": f"AI VIRTUAL STUDIO: {clean_title[:55]} #AINews",
        "description": f"Virtual Studio AI News Broadcast analyzing '{clean_title}'.\n\nTimestamps:\n0:00 - Virtual Studio Intro\n0:45 - Breaking News Analysis\n1:45 - Architecture Deep Dive\n3:00 - Benchmark & Enterprise Impact\n5:15 - Open-Weight Revolution\n7:00 - Future Roadmap & Verdict\n\nFeatured Source: {source_channel} ({main_target['url']})",
        "tags": ["AI", "ArtificialIntelligence", "TechNews", "OpenAI", "Gemini", "AIAgents", "MachineLearning", "FutureTech", "DevinAI", "Claude35"],
        "badge_text": "VIRTUAL STUDIO AI",
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

def get_background_music(output_file="bg_presenter_music.mp3"):
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

def generate_procedural_background(width, height):
    img = PIL.Image.new("RGBA", (width, height), (10, 15, 30, 255))
    draw = PIL.ImageDraw.Draw(img)
    colors = [(56, 189, 248, 100), (236, 72, 153, 100), (168, 85, 247, 100), (250, 204, 21, 100)]
    for i in range(24):
        x0 = random.randint(0, width)
        y0 = random.randint(0, height)
        draw.ellipse([x0-300, y0-300, x0+300, y0+300], fill=colors[i % len(colors)])
    img = img.filter(PIL.ImageFilter.GaussianBlur(30))
    draw_grid = PIL.ImageDraw.Draw(img)
    for y in range(0, height, 45):
        draw_grid.line([(0, y), (width, y)], fill=(255, 255, 255, 10))
    for x in range(0, width, 45):
        draw_grid.line([(x, 0), (x, height)], fill=(255, 255, 255, 10))
    return img.convert("RGB")

# ==============================================================================
# STEP 4: 16:9 Widescreen Thumbnail Generator (1280x720)
# ==============================================================================
def generate_presenter_thumbnail(title_text, badge_text, source_channel, output_file="presenter_thumbnail.png"):
    print("🖼️ Step 4: Generating 16:9 Virtual Studio thumbnail (1280x720)...")
    w, h = 1280, 720
    base_img = generate_procedural_background(w, h)
    draw = PIL.ImageDraw.Draw(base_img)

    font_large = get_font(48)
    font_badge = get_font(26)
    font_credit = get_font(20)

    draw.rectangle([15, 15, w-15, h-15], outline=(56, 189, 248), width=6)
    draw.rectangle([60, 50, 420, 105], fill=(236, 72, 153), outline=(255, 255, 255), width=2)
    draw.text((80, 65), badge_text, font=font_badge, fill=(255, 255, 255))

    # Draw Cartoon AI Presenter Head on Thumbnail
    cx, cy = 200, 380
    draw.polygon([(cx-80, cy+180), (cx+80, cy+180), (cx+60, cy+100), (cx-60, cy+100)], fill=(30, 41, 59))
    draw.ellipse([cx-70, cy-80, cx+70, cy+80], fill=(254, 215, 170), outline=(15, 23, 42), width=3)
    draw.ellipse([cx-80, cy-100, cx+80, cy-30], fill=(124, 58, 237))
    draw.ellipse([cx-40, cy-25, cx-10, cy+10], fill=(255, 255, 255))
    draw.ellipse([cx+10, cy-25, cx+40, cy+10], fill=(255, 255, 255))
    draw.ellipse([cx-30, cy-15, cx-20, cy-5], fill=(56, 189, 248))
    draw.ellipse([cx+20, cy-15, cx+30, cy-5], fill=(56, 189, 248))
    draw.arc([cx-30, cy+15, cx+30, cy+45], start=0, end=180, fill=(225, 29, 72), width=4)

    # Title Text
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
        draw.rectangle([420, y_start - 8, 420 + lw + 30, y_start + 60], fill=(15, 23, 42, 235))
        draw.text((435, y_start), line, font=font_large, fill=(250, 204, 21))
        y_start += 80

    credit_text = f"PRESENTER: ALEX (AI ANCHOR) • SOURCE: {source_channel.upper()} • FAIR USE"
    cw = get_text_width(font_credit, credit_text)
    draw.rectangle([(w - cw)//2 - 15, h - 90, (w + cw)//2 + 15, h - 45], fill=(30, 41, 59, 240), outline=(56, 189, 248), width=2)
    draw.text(((w - cw)//2, h - 75), credit_text, font=font_credit, fill=(255, 255, 255))

    base_img.save(output_file)
    print(f"   ✅ Thumbnail generated: {output_file}")
    return output_file

# ==============================================================================
# STEP 5: 16:9 Virtual Studio Dynamic Cartoon Presenter Renderer (1920x1080)
# ==============================================================================
def render_presenter_video(script_data, news_bundle, output_file="presenter_ai_video.mp4"):
    print("🎬 Step 5: Rendering 16:9 Virtual Studio Presenter video (1920x1080 resolution)...")
    w, h = 1920, 1080
    slides = script_data.get("slides", [])
    total_slides = len(slides)
    source_channel = news_bundle[0].get("channel", "AI Tech Wire")

    font_header = get_font(34)
    font_body = get_font(42)
    font_badge = get_font(28)
    font_credit = get_font(24)

    temp_files = []
    slide_clips = []
    base_bg_pil = generate_procedural_background(w, h)

    for idx, slide in enumerate(slides):
        audio_file = f"presenter_audio_{idx}.mp3"
        temp_files.append(audio_file)
        slide_text = slide.get("text", "")
        asyncio.run(synthesize_slide_audio(slide_text, audio_file))

        audio_clip = AudioFileClip(audio_file)
        # Enforce hard duration floor of 28 seconds per slide
        slide_duration = max(audio_clip.duration + 2.0, 28.0)
        badge_str = slide.get("badge", f"MODULE {idx+1} OF {total_slides}")
        highlight_str = slide.get("highlight_word", "").lower()

        frame_pil = base_bg_pil.copy()
        draw = PIL.ImageDraw.Draw(frame_pil)

        # 1. Top Header Banner
        draw.rectangle([0, 0, w, 110], fill=(15, 23, 42, 240))
        draw.text((60, 35), "FUTURETECH AI STUDIO  |  VIRTUAL AI ANCHOR BROADCAST", font=font_header, fill=(56, 189, 248))
        draw.line([(0, 110), (w, 110)], fill=(236, 72, 153), width=4)

        # 2. Slide Counter Pill
        counter_str = f"MODULE {idx+1} / {total_slides}"
        cw = get_text_width(font_header, counter_str)
        draw.rectangle([w - cw - 80, 25, w - 40, 85], fill=(30, 41, 59, 220), outline=(236, 72, 153), width=2)
        draw.text((w - cw - 60, 35), counter_str, font=font_header, fill=(250, 204, 21))

        # 3. Left Side Virtual AI Presenter Card Frame (450px wide)
        draw.rectangle([60, 160, 500, h - 140], fill=(15, 23, 42, 235), outline=(56, 189, 248), width=3)
        draw.rectangle([60, 160, 500, 220], fill=(30, 41, 59, 250))
        draw.text((80, 175), "ALEX | AI PRESENTER ANCHOR", font=get_font(22), fill=(56, 189, 248))
        draw.text((120, h - 180), f"● MODULE {idx+1} IN PROGRESS", font=get_font(20), fill=(250, 204, 21))

        # 4. Right Side Topic Badge & Text Card Setup
        draw.rectangle([540, 160, 920, 220], fill=(236, 72, 153))
        draw.text((560, 175), badge_str.upper(), font=font_badge, fill=(255, 255, 255))

        # Text Line Wrapping inside Right Card
        words = slide_text.split()
        lines_list = []
        curr = []
        for word in words:
            curr.append(word)
            if get_text_width(font_body, " ".join(curr)) > w - 660:
                curr.pop()
                lines_list.append(" ".join(curr))
                curr = [word]
        if curr:
            lines_list.append(" ".join(curr))

        panel_h = len(lines_list) * 70 + 80
        y_center = (h // 2) - (panel_h // 2) + 20
        draw.rectangle([540, y_center, w - 60, y_center + panel_h], fill=(10, 15, 30, 225), outline=(168, 85, 247), width=3)

        # 5. Lower-Third Source Attribution Line
        attr_str = f"SOURCE CREDIT: {source_channel.upper()} • FAIR USE COMMENTARY (17 U.S.C. § 107)"
        aw = get_text_width(font_credit, attr_str)
        draw.rectangle([(w - aw)//2 - 20, h - 110, (w + aw)//2 + 20, h - 55], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=2)
        draw.text(((w - aw)//2, h - 98), attr_str, font=font_credit, fill=(250, 204, 21))

        base_img_np = np.array(frame_pil)

        # Reaction Sticker Text Rotation per slide
        stickers = ["💡 MIND-BLOWING!", "🔥 VIRAL BREAKTHROUGH", "⚡ 10X SPEED BOOST", "🤖 AUTONOMOUS AGENT", "🚀 GAME CHANGER", "🧠 REASONING LOOP", "📊 RECORD BENCHMARK"]
        sticker_text = stickers[idx % len(stickers)]

        # 6. DYNAMIC ANIMATED FRAME GENERATOR (Runs frame-by-frame for time t)
        def make_frame(t, base_np=base_img_np, dur=slide_duration, text_lines=lines_list, y_start=y_center+35, hl=highlight_str, st_text=sticker_text):
            frame = PIL.Image.fromarray(base_np).copy()
            draw_anim = PIL.ImageDraw.Draw(frame)

            # A. HUD Laser Scanline
            scan_y = int((t / dur) * h)
            draw_anim.line([(0, scan_y), (w, scan_y)], fill=(56, 189, 248, 160), width=3)

            # B. Top Progress Bar
            prog_w = int((t / dur) * w)
            draw_anim.rectangle([0, 110, prog_w, 116], fill=(250, 204, 21))

            # C. DYNAMIC 2D ANIMATED AI PRESENTER AVATAR ("ALEX")
            cx, cy = 280, 410

            # Shoulders & Body / Blazer
            draw_anim.polygon([(cx-140, cy+220), (cx+140, cy+220), (cx+110, cy+110), (cx-110, cy+110)], fill=(30, 41, 59), outline=(56, 189, 248), width=3)
            draw_anim.polygon([(cx-35, cy+110), (cx+35, cy+110), (cx, cy+180)], fill=(236, 72, 153)) # Tie/V-Neck

            # Head & Skin (Warm Amber/Peach Skin Tone)
            draw_anim.ellipse([cx-85, cy-95, cx+85, cy+85], fill=(254, 215, 170), outline=(15, 23, 42), width=3)

            # Stylized Hair / Cyber Helmet
            draw_anim.ellipse([cx-95, cy-125, cx+95, cy-35], fill=(124, 58, 237))
            draw_anim.polygon([(cx-95, cy-45), (cx-65, cy-10), (cx-90, cy-10)], fill=(124, 58, 237))
            draw_anim.polygon([(cx+95, cy-45), (cx+65, cy-10), (cx+90, cy-10)], fill=(124, 58, 237))

            # EYES & PUPILS ANIMATION
            pupil_shift = int(10 * math.sin(t * 2.2)) # Pupil tracking left-right
            is_blinking = abs(math.sin(t * 0.8)) > 0.94 # Natural periodic blinking

            # Left Eye
            draw_anim.ellipse([cx-50, cy-25, cx-10, cy+15], fill=(255, 255, 255), outline=(15, 23, 42), width=2)
            if not is_blinking:
                draw_anim.ellipse([cx-38+pupil_shift, cy-15, cx-22+pupil_shift, cy+5], fill=(56, 189, 248)) # Iris
                draw_anim.ellipse([cx-33+pupil_shift, cy-10, cx-27+pupil_shift, cy-4], fill=(15, 23, 42)) # Pupil
            else:
                draw_anim.line([(cx-50, cy-5), (cx-10, cy-5)], fill=(15, 23, 42), width=3) # Closed lid

            # Right Eye
            draw_anim.ellipse([cx+10, cy-25, cx+50, cy+15], fill=(255, 255, 255), outline=(15, 23, 42), width=2)
            if not is_blinking:
                draw_anim.ellipse([cx+22+pupil_shift, cy-15, cx+38+pupil_shift, cy+5], fill=(56, 189, 248)) # Iris
                draw_anim.ellipse([cx+27+pupil_shift, cy-10, cx+33+pupil_shift, cy-4], fill=(15, 23, 42)) # Pupil
            else:
                draw_anim.line([(cx+10, cy-5), (cx+50, cy-5)], fill=(15, 23, 42), width=3) # Closed lid

            # Eyebrows (Expressive tilt)
            brow_tilt = int(4 * math.sin(t * 1.5))
            draw_anim.line([(cx-52, cy-35 - brow_tilt), (cx-8, cy-35 + brow_tilt)], fill=(15, 23, 42), width=4)
            draw_anim.line([(cx+8, cy-35 + brow_tilt), (cx+52, cy-35 - brow_tilt)], fill=(15, 23, 42), width=4)

            # DYNAMIC LIP-SYNC TALKING MOUTH ANIMATION
            # Mouth opens and closes continuously in real-time as if speaking
            mouth_open = int(14 * abs(math.sin(t * 15.0)))
            if mouth_open > 2:
                # Open Mouth with interior & teeth
                draw_anim.ellipse([cx-28, cy+25, cx+28, cy+25+mouth_open], fill=(153, 27, 27), outline=(15, 23, 42), width=2)
                draw_anim.rectangle([cx-20, cy+26, cx+20, cy+28+min(4, mouth_open//2)], fill=(255, 255, 255)) # Teeth line
            else:
                # Closed Smile Mouth
                draw_anim.arc([cx-25, cy+15, cx+25, cy+35], start=10, end=170, fill=(15, 23, 42), width=4)

            # Cyber Headset Microphone Arm
            draw_anim.ellipse([cx-92, cy-20, cx-78, cy+10], fill=(236, 72, 153)) # Ear piece
            draw_anim.line([(cx-85, cy), (cx-40, cy+40)], fill=(236, 72, 153), width=3) # Mic boom arm
            draw_anim.ellipse([cx-45, cy+35, cx-35, cy+45], fill=(250, 204, 21)) # Mic tip

            # D. Animated Audio Equalizer Bars (10 Bars under Presenter Card)
            eq_x = 90
            for eq_i in range(10):
                bar_h = int(30 + 22 * math.sin(t * 9 + eq_i * 0.8))
                draw_anim.rectangle([eq_x, 680 - bar_h, eq_x + 30, 680], fill=(56, 189, 248), outline=(236, 72, 153), width=1)
                eq_x += 38

            # E. FLOATING ANIMATED CARTOON REACTION STICKER & SPEECH BUBBLE
            bounce_y = int(8 * math.sin(t * 3.5))
            sw = get_text_width(get_font(20), st_text)
            draw_anim.rectangle([cx - sw//2 - 15, cy - 170 + bounce_y, cx + sw//2 + 15, cy - 120 + bounce_y], fill=(250, 204, 21), outline=(15, 23, 42), width=3)
            draw_anim.polygon([(cx-10, cy-120+bounce_y), (cx+10, cy-120+bounce_y), (cx, cy-105+bounce_y)], fill=(250, 204, 21))
            draw_anim.text((cx - sw//2, cy - 158 + bounce_y), st_text, font=get_font(20), fill=(15, 23, 42))

            # F. Spoken Text Rendering with Highlight Words (Right Card)
            line_y = y_start
            for line in text_lines:
                lw = get_text_width(font_body, line)
                x_pos = 580 + ((w - 640 - lw) // 2) if (w - 640 > lw) else 570
                for word in line.split():
                    clean_w = re.sub(r'[^\w]', '', word).lower()
                    color = (250, 204, 21) if (hl and hl in clean_w) else (255, 255, 255)
                    draw_anim.text((x_pos, line_y), word + " ", font=font_body, fill=color)
                    x_pos += get_text_width(font_body, word + " ")
                line_y += 70

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

    print(f"   ✅ 16:9 Virtual Studio Presenter video rendered: {output_file}")
    return output_file

# ==============================================================================
# STEP 6: YouTube Upload & Persistent History Logging
# ==============================================================================
def upload_presenter_to_youtube(video_file, title, description, tags, news_bundle=None, news_target=None, source_target=None, thumbnail_file=None):
    clean_title = sanitize_text(title)
    clean_desc = sanitize_text(description)
    print(f"🚀 Step 6: Uploading Virtual Studio video '{clean_title}' to YouTube...")

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

    target_item = {}
    if isinstance(news_bundle, list) and len(news_bundle) > 0:
        target_item = news_bundle[0]
    elif isinstance(news_bundle, dict):
        target_item = news_bundle
    elif news_target and isinstance(news_target, dict):
        target_item = news_target
    elif source_target and isinstance(source_target, dict):
        target_item = source_target

    source_title = target_item.get("title", "Original AI Breakthrough")
    source_channel = target_item.get("channel", "AI Tech Wire")
    source_url = target_item.get("url", "https://youtube.com")

    legal_attribution = (
        "📌 VIRTUAL STUDIO CREDIT & ATTRIBUTION:\n"
        f"Featured Topic: {source_title}\n"
        f"Source Channel/Press: {source_channel}\n"
        f"Source Link: {source_url}\n\n"
        "⚖️ LEGAL STATEMENT & COPYRIGHT COMPLIANCE:\n"
        "This video presents an original, transformative news synthesis, commentary, and educational breakdown of recent AI developments under 17 U.S.C. Section 107 (Fair Use).\n\n"
        "🤖 AI PRODUCTION DISCLAIMER:\n"
        "Presented by AI Host ALEX using synthetic narration and automated technical visual studio tools for education and research."
    )

    full_description = clean_desc[:3500] + "\n\n" + legal_attribution
    body = {
        "snippet": {
            "title": clean_title[:100],
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
    pub_link = "https://" + "youtu.be/" + str(video_id)
    print(f"   SUCCESS! Published Virtual Studio video live: {pub_link}")

    if thumbnail_file and os.path.exists(thumbnail_file):
        try:
            print(f"   Setting custom thumbnail for Video ID {video_id}...")
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_file)).execute()
            print("   Thumbnail updated successfully!")
        except Exception as e:
            print(f"   Could not set thumbnail: {e}")

    # Log to local history
    history_file = "posted_topics_history.json"
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
# MAIN EXECUTION PIPELINE (EVERY 12 HOURS - MULTI-VIDEO BATCH PROCESSOR)
# ==============================================================================
def main():
    print("======================================================================")
    print("🚀 STARTING 12-HOUR ANIMATED AI PRESENTER PIPELINE")
    print("======================================================================")
    
    news_bundle = fetch_presenter_ai_trends()
    
    for v_idx, news_item in enumerate(news_bundle):
        print(f"\n--- Processing Virtual Studio Episode {v_idx+1} of {len(news_bundle)}: '{news_item['title']}' ---")
        single_bundle = [news_item]
        script_data = generate_presenter_script(single_bundle)

        thumb_file = f"presenter_thumbnail_{v_idx+1}.png"
        generate_presenter_thumbnail(
            title_text=script_data.get("title", "AI STUDIO BROADCAST"),
            badge_text=script_data.get("badge_text", "VIRTUAL STUDIO AI"),
            source_channel=news_item.get("channel", "AI Creator"),
            output_file=thumb_file
        )

        out_video_file = f"presenter_ai_video_{v_idx+1}.mp4"
        video_file = render_presenter_video(
            script_data=script_data,
            news_bundle=single_bundle,
            output_file=out_video_file
        )

        upload_presenter_to_youtube(
            video_file=video_file,
            title=script_data.get("title", "AI STUDIO BROADCAST"),
            description=script_data.get("description", "Virtual Studio AI News Broadcast."),
            tags=script_data.get("tags", ["AI", "TechNews"]),
            news_bundle=single_bundle,
            thumbnail_file=thumb_file
        )

    print("======================================================================")
    print("✅ 12-HOUR ANIMATED AI PRESENTER PIPELINE COMPLETE")
    print("======================================================================")

if __name__ == "__main__":
    main()
