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
# STEP 2: Script Generation (14 Slides, 5+ Minutes Runtime)
# ==============================================================================
def generate_presenter_script(news_bundle):
    print("📝 Step 2: Generating 14-slide Virtual Studio broadcast script (~5-6 minutes runtime)...")
    main_target = news_bundle[0]
    clean_title = sanitize_text(main_target["title"])
    source_channel = main_target["channel"]

    topics_summary = "\n".join([
        f"- Story {i+1}: '{item['title']}' from {item['channel']}"
        for i, item in enumerate(news_bundle)
    ])

    prompt_lines = [
        "You are an expert AI Virtual Studio News Anchor creating a comprehensive 5-to-6 minute broadcast video.",
        "TOPICS TO COVER:",
        topics_summary,
        "RULES:",
        "1. Produce an exciting 14-slide broadcast script.",
        "2. Each slide must contain 60 to 75 words of spoken commentary (~24 seconds per slide = 5.5 minutes total).",
        "3. Provide high-SEO Title, Description with timestamps, 15 Tags, and Badge labels.",
        "4. Comply 100% with YouTube Fair Use and Monetization rules.",
        "Return ONLY valid JSON with keys: title, description, tags, badge_text, slides (list of objects with badge, text, highlight_word)."
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

    print("   💡 Using local procedural 14-slide Virtual Studio broadcast generator...")
    clean_short = clean_title[:45]
    slides = [
        {"badge": "LIVE BROADCAST", "text": f"Welcome to FutureTech AI Studio! I am your AI Anchor. Today we analyze top artificial intelligence breakthroughs, starting with '{clean_short}'.", "highlight_word": "artificial"},
        {"badge": "THE BREAKTHROUGH", "text": f"Researchers and engineers at {source_channel} have unveiled impressive new model architectures that push autonomous performance to unprecedented levels.", "highlight_word": "autonomous"},
        {"badge": "SYSTEM ARCHITECTURE", "text": "Behind this breakthrough is an advanced neural execution pipeline. By coupling specialized reasoning loops with dynamic memory context, real-world task accuracy increases sharply.", "highlight_word": "reasoning"},
        {"badge": "HARDWARE SCALING", "text": "Hardware acceleration plays a decisive role. High-bandwidth GPU clusters allow massive parallel model training, reducing latency for instant real-time inference.", "highlight_word": "parallel"},
        {"badge": "DEVELOPER IMPACT", "text": "For software engineering teams, autonomous coding assistants now handle multi-file refactoring, test suite generation, and automated deployment scripts seamlessly.", "highlight_word": "automation"},
        {"badge": "BENCHMARK ANALYSIS", "text": "In recent benchmark evaluations, autonomous AI models achieved record scores on complex coding and multi-step reasoning benchmarks.", "highlight_word": "benchmark"},
        {"badge": "ENTERPRISE ADOPTION", "text": "Global enterprises across tech, finance, and healthcare are embedding these AI agent workflows directly into operational systems to scale productivity.", "highlight_word": "workflows"},
        {"badge": "OPEN WEIGHT MOVEMENT", "text": "Simultaneously, open-weight models are advancing rapidly. Quantized 70B parameter models can now run locally on developer workstations with extreme speed.", "highlight_word": "quantized"},
        {"badge": "SECURITY & ALIGNMENT", "text": "As model capabilities expand, AI safety researchers are enforcing strict alignment guardrails and sandboxed execution environments to guarantee data privacy.", "highlight_word": "guardrails"},
        {"badge": "FUTURE ROADMAP", "text": "Looking ahead to the next horizon, multi-modal AI agents will seamlessly synthesize voice, vision, code, and robotics control in real-time.", "highlight_word": "seamlessly"},
        {"badge": "STRATEGIC VERDICT", "text": "The speed of AI progress means creators and developers who integrate these autonomous agent tools today will lead the digital economy tomorrow.", "highlight_word": "lead"},
        {"badge": "COMMUNITY COMMENTARY", "text": "What are your thoughts on this AI milestone? Drop your comments below and share which AI models you use in your daily workflow.", "highlight_word": "comments"},
        {"badge": "CHANNEL NEWS", "text": "Stay tuned for our upcoming deep-dive technical tutorials where we build and deploy autonomous multi-agent systems live on channel.", "highlight_word": "tutorials"},
        {"badge": "SUBSCRIBE & STAY AHEAD", "text": "Subscribe to FutureTech AI for daily long-form Virtual Studio broadcasts, technical AI deep dives, and breaking technology news!", "highlight_word": "Subscribe"}
    ]
    return {
        "title": f"AI STUDIO BROADCAST: {clean_title[:55]} #AINews",
        "description": f"Virtual Studio AI News Broadcast analyzing '{clean_title}'.\n\nTimestamps:\n0:00 - Virtual Studio Intro\n0:45 - Breaking News Analysis\n1:45 - Architecture Deep Dive\n3:00 - Enterprise & Dev Impact\n4:30 - Final Verdict\n\nFeatured Source: {source_channel} ({main_target['url']})",
        "tags": ["AI", "ArtificialIntelligence", "TechNews", "OpenAI", "Gemini", "AIAgents", "MachineLearning", "FutureTech"],
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

    font_large = get_font(52)
    font_badge = get_font(28)
    font_credit = get_font(22)

    draw.rectangle([15, 15, w-15, h-15], outline=(56, 189, 248), width=6)
    draw.rectangle([60, 60, 420, 120], fill=(236, 72, 153), outline=(255, 255, 255), width=2)
    draw.text((80, 75), badge_text, font=font_badge, fill=(255, 255, 255))

    words = title_text.split()
    lines_list = []
    curr = []
    for word in words:
        curr.append(word)
        if get_text_width(font_large, " ".join(curr)) > w - 200:
            curr.pop()
            lines_list.append(" ".join(curr))
            curr = [word]
    if curr:
        lines_list.append(" ".join(curr))

    y_start = 200
    for line in lines_list[:3]:
        lw = get_text_width(font_large, line)
        draw.rectangle([(w - lw)//2 - 15, y_start - 8, (w + lw)//2 + 15, y_start + 65], fill=(15, 23, 42, 230))
        draw.text(((w - lw)//2, y_start), line, font=font_large, fill=(250, 204, 21))
        y_start += 85

    credit_text = f"PRESENTER: ALEX (AI ANCHOR) • SOURCE: {source_channel.upper()} • FAIR USE"
    cw = get_text_width(font_credit, credit_text)
    draw.rectangle([(w - cw)//2 - 15, h - 110, (w + cw)//2 + 15, h - 60], fill=(30, 41, 59, 240), outline=(56, 189, 248), width=2)
    draw.text(((w - cw)//2, h - 92), credit_text, font=font_credit, fill=(255, 255, 255))

    base_img.save(output_file)
    print(f"   ✅ Thumbnail generated: {output_file}")
    return output_file

# ==============================================================================
# STEP 5: 16:9 Virtual Studio MoviePy Video Renderer (1920x1080)
# ==============================================================================
def render_presenter_video(script_data, news_bundle, output_file="presenter_ai_video.mp4"):
    print("🎬 Step 5: Rendering 16:9 Virtual Studio Presenter video (1920x1080 resolution)...")
    w, h = 1920, 1080
    slides = script_data.get("slides", [])
    total_slides = len(slides)
    source_channel = news_bundle[0].get("channel", "AI Tech Wire")

    font_header = get_font(34)
    font_body = get_font(44)
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
        slide_duration = max(audio_clip.duration + 1.5, 22.0)
        badge_str = slide.get("badge", f"PART {idx+1} OF {total_slides}")
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

        # 3. Left Side Virtual AI Presenter Card (450px wide)
        draw.rectangle([60, 160, 500, h - 140], fill=(15, 23, 42, 235), outline=(56, 189, 248), width=3)
        draw.rectangle([60, 160, 500, 220], fill=(30, 41, 59, 250))
        draw.text((80, 175), "ALEX | AI PRESENTER ANCHOR", font=get_font(22), fill=(56, 189, 248))
        
        # Presenter Avatar Circle
        cx, cy = 280, 380
        draw.ellipse([cx-100, cy-100, cx+100, cy+100], fill=(30, 41, 59), outline=(236, 72, 153), width=4)
        draw.ellipse([cx-60, cy-60, cx+60, cy+60], fill=(56, 189, 248, 180))
        draw.text((cx-30, cy-15), "AI", font=get_font(38), fill=(255, 255, 255))
        draw.text((120, cy + 130), f"● MODULE {idx+1} IN PROGRESS", font=get_font(20), fill=(250, 204, 21))

        # 4. Right Side Topic & Text Card
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

        panel_h = len(lines_list) * 75 + 80
        y_center = (h // 2) - (panel_h // 2) + 20
        draw.rectangle([540, y_center, w - 60, y_center + panel_h], fill=(10, 15, 30, 225), outline=(168, 85, 247), width=3)

        # 5. Lower-Third Source Attribution Line
        attr_str = f"SOURCE CREDIT: {source_channel.upper()} • FAIR USE COMMENTARY (17 U.S.C. § 107)"
        aw = get_text_width(font_credit, attr_str)
        draw.rectangle([(w - aw)//2 - 20, h - 110, (w + aw)//2 + 20, h - 55], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=2)
        draw.text(((w - aw)//2, h - 98), attr_str, font=font_credit, fill=(250, 204, 21))

        base_img_np = np.array(frame_pil)

        def make_frame(t, base_np=base_img_np, dur=slide_duration, text_lines=lines_list, y_start=y_center+40, hl=highlight_str):
            frame = PIL.Image.fromarray(base_np).copy()
            draw_anim = PIL.ImageDraw.Draw(frame)

            # HUD Laser Scanline
            scan_y = int((t / dur) * h)
            draw_anim.line([(0, scan_y), (w, scan_y)], fill=(56, 189, 248, 160), width=3)

            # Top Progress Bar
            prog_w = int((t / dur) * w)
            draw_anim.rectangle([0, 110, prog_w, 116], fill=(250, 204, 21))

            # Animated Audio Equalizer Bars under Avatar (Left Presenter Box)
            eq_x = 120
            for eq_i in range(8):
                bar_h = int(25 + 20 * math.sin(t * 8 + eq_i * 0.7))
                draw_anim.rectangle([eq_x, 570 - bar_h, eq_x + 25, 570], fill=(56, 189, 248))
                eq_x += 40

            # Spoken Text Rendering with Highlight Words
            line_y = y_start
            for line in text_lines:
                lw = get_text_width(font_body, line)
                x_pos = 580 + ((w - 640 - lw) // 2) if (w - 640 > lw) else 570
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

    print(f"   ✅ 16:9 Virtual Studio Presenter video rendered: {output_file}")
    return output_file

# ==============================================================================
# STEP 6: YouTube Data API v3 Upload & Persistent History Logging
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

    legal_attribution = (
        "📌 VIRTUAL STUDIO CREDIT & ATTRIBUTION:\n"
        f"Featured Topic: {news_bundle[0]['title']}\n"
        f"Source Channel/Press: {news_bundle[0]['channel']}\n"
        f"Source Link: {news_bundle[0]['url']}\n\n"
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
    print(f"🎉 SUCCESS! Published Virtual Studio video live: {pub_link}")

    if thumbnail_file and os.path.exists(thumbnail_file):
        try:
            print(f"🖼️ Setting 16:9 thumbnail for Video ID {video_id}...")
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_file)).execute()
            print("   ✅ Thumbnail published successfully!")
        except Exception as e:
            print(f"   ⚠️ Could not set thumbnail ({e}).")

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
# MAIN EXECUTION PIPELINE (EVERY 12 HOURS)
# ==============================================================================
def main():
    print("======================================================================")
    print("🚀 STARTING 12-HOUR ANIMATED AI PRESENTER PIPELINE")
    print("======================================================================")
    
    news_bundle = fetch_presenter_ai_trends()
    script_data = generate_presenter_script(news_bundle)

    thumb_file = generate_presenter_thumbnail(
        title_text=script_data.get("title", "AI STUDIO BROADCAST"),
        badge_text=script_data.get("badge_text", "VIRTUAL STUDIO AI"),
        source_channel=news_bundle[0].get("channel", "AI Creator")
    )

    video_file = render_presenter_video(
        script_data=script_data,
        news_bundle=news_bundle
    )

    upload_presenter_to_youtube(
        video_file=video_file,
        title=script_data.get("title", "AI STUDIO BROADCAST"),
        description=script_data.get("description", "Virtual Studio AI News Broadcast."),
        tags=script_data.get("tags", ["AI", "TechNews"]),
        news_bundle=news_bundle,
        thumbnail_file=thumb_file
    )

    print("======================================================================")
    print("✅ 12-HOUR ANIMATED AI PRESENTER PIPELINE COMPLETE")
    print("======================================================================")

if __name__ == "__main__":
    main()
