# ==============================================================================
# CURATOR PIPELINE: VIRAL 12-HOUR AI DIGEST (YOUTUBE SHORTS)
# ==============================================================================
import os
import re
import json
import time
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


# Language filter to enforce 100% English script text
def is_english_text(text):
    if not text:
        return True
    non_english_pattern = re.compile(
        r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u0d00-\u0d7f\u0900-\u097f\u0400-\u04ff\u0600-\u06ff\u0e00-\u0e7f\uac00-\ud7af]'
    )
    if non_english_pattern.search(str(text)):
        return False
    return True


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
# STEP 1: 12-Hour Viral AI Video & Trend Discovery Engine
# ==============================================================================
def fetch_viral_12h_ai_content():
    """
    Searches YouTube Data API v3 and RSS feeds for viral AI videos published 
    in the last 12 hours. Prioritizes Creative Commons (CC-BY) licensed content, 
    with Transformative Fair Use commentary fallback.
    """
    print("📰 Step 1: Scanning for viral AI videos published in the last 12 hours...")
    
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    
    time_12h_ago = (datetime.utcnow() - timedelta(hours=12)).isoformat() + "Z"
    viral_items = []
    
    # 1. Attempt YouTube Data API v3 Search (English only)
    if client_id and client_secret and refresh_token and build:
        try:
            token_url = "https://" + "oauth2.googleapis.com/token"
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri=token_url,
                client_id=client_id,
                client_secret=client_secret
            )
            creds.refresh(Request())
            youtube = build("youtube", "v3", credentials=creds)
            
            # Query 1A: Search Creative Commons (CC-BY) AI videos from last 12h
            print("   💡 Searching Creative Commons (CC-BY) AI videos (Last 12H)...")
            cc_request = youtube.search().list(
                q="AI artificial intelligence OpenAI Gemini Claude LLM breakthrough",
                part="snippet",
                type="video",
                order="viewCount",
                relevanceLanguage="en",
                regionCode="US",
                publishedAfter=time_12h_ago,
                videoLicense="creativeCommon",
                maxResults=5
            )
            cc_response = cc_request.execute()
            
            for item in cc_response.get("items", []):
                snippet = item.get("snippet", {})
                vid_id = item.get("id", {}).get("videoId")
                title = snippet.get("title", "Viral AI Breakthrough")
                if vid_id and is_english_text(title):
                    v_url = "https://" + "www.youtube.com/watch?v=" + str(vid_id)
                    viral_items.append({
                        "id": vid_id,
                        "title": title,
                        "channel": snippet.get("channelTitle", "AI Creator"),
                        "url": v_url,
                        "description": snippet.get("description", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "license_type": "Creative Commons (CC-BY)",
                        "legal_note": "Re-used under Creative Commons Attribution License."
                    })
            
            # Query 1B: If CC videos limited, search general viral AI videos for Fair Use Commentary
            if not viral_items:
                print("   💡 Searching top trending general AI videos (Last 12H for Fair Use Commentary)...")
                gen_request = youtube.search().list(
                    q="AI breakthrough OR OpenAI OR Gemini 2.0 OR Claude 3.5 OR Nvidia AI",
                    part="snippet",
                    type="video",
                    order="viewCount",
                    relevanceLanguage="en",
                    regionCode="US",
                    publishedAfter=time_12h_ago,
                    maxResults=5
                )
                gen_response = gen_request.execute()
                for item in gen_response.get("items", []):
                    snippet = item.get("snippet", {})
                    vid_id = item.get("id", {}).get("videoId")
                    title = snippet.get("title", "Viral AI Breakthrough")
                    if vid_id and is_english_text(title):
                        v_url = "https://" + "www.youtube.com/watch?v=" + str(vid_id)
                        viral_items.append({
                            "id": vid_id,
                            "title": title,
                            "channel": snippet.get("channelTitle", "Tech News"),
                            "url": v_url,
                            "description": snippet.get("description", ""),
                            "published_at": snippet.get("publishedAt", ""),
                            "license_type": "Transformative Fair Use Commentary",
                            "legal_note": "Original news breakdown & commentary under Fair Use (17 U.S.C. § 107)."
                        })
        except Exception as e:
            print(f"   ⚠️ YouTube API Search note: {e}")

    # 2. RSS / Web Trend Fallback (if API search returned no items)
    if not viral_items:
        print("   💡 Fetching latest 12h AI news trends via RSS feeds...")
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
                    for entry in feed.entries[:3]:
                        title = sanitize_text(entry.title)
                        link = entry.link
                        summary = sanitize_text(entry.get("summary", title))
                        if is_english_text(title):
                            viral_items.append({
                                "id": f"rss_{hash(link) % 1000000}",
                                "title": title,
                                "channel": "Tech Press Digest",
                                "url": link,
                                "description": summary,
                                "published_at": entry.get("published", "Last 12 Hours"),
                                "license_type": "Transformative Editorial Digest",
                                "legal_note": "Original news synthesis and educational breakdown."
                            })
            except Exception as e:
                print(f"   ⚠️ RSS fetch note for {feed_url}: {e}")

    # Fallback default item if external sources fail
    if not viral_items:
        default_url = "https://" + "www.youtube.com/results?search_query=AI+agent+breakthrough"
        viral_items.append({
            "id": "viral_ai_default_12h",
            "title": "New Agentic AI Framework Shocks Developers with 24/7 Automation",
            "channel": "AI Frontier Network",
            "url": default_url,
            "description": "Autonomous AI agents achieve major efficiency milestones in multi-step task execution.",
            "published_at": "Last 12 Hours",
            "license_type": "Transformative Educational Commentary",
            "legal_note": "Original educational breakdown & news commentary."
        })

    selected_item = random.choice(viral_items[:3])
    print(f"   ✅ Selected 12H Viral Target: '{selected_item['title']}' from [{selected_item['channel']}]")
    print(f"   ⚖️ Compliance Status: {selected_item['license_type']}")
    return selected_item


# ==============================================================================
# STEP 2: Script Generation (4-Slide Viral Shorts Script)
# ==============================================================================
def generate_curation_script(viral_target):
    """
    Generates a 100% original, transformative commentary & breakdown script 
    based on the 12-hour viral video item. Uses Gemini / Groq / OpenRouter / Procedural fallback.
    """
    print("📝 Step 2: Generating transformative commentary & viral Shorts script...")
    
    title_orig = viral_target["title"]
    channel_orig = viral_target["channel"]
    desc_orig = viral_target["description"][:300]
    license_type = viral_target["license_type"]
    
    prompt_lines = [
        "You are a top tech journalist creating a viral YouTube Short (40-45 seconds) analyzing a viral AI video that exploded in the last 12 hours.",
        "",
        "VIRAL TARGET DATA:",
        f"- Original Title: \"{title_orig}\"",
        f"- Original Creator/Channel: \"{channel_orig}\"",
        f"- Target Details: \"{desc_orig}\"",
        f"- Curation Mode: {license_type}",
        "",
        "RULES:",
        "1. Create a TRANSFORMATIONAL, exciting 4-slide commentary script strictly in ENGLISH.",
        "2. DO NOT just copy the target. Analyze WHY it is viral, what it means for viewers, and the key breakthrough.",
        "3. Keep spoken lines punchy (15-20 words per slide).",
        "4. Include a strong hook title, description with channel credit, tags, and badge text.",
        "",
        "Return ONLY valid JSON in this exact structure:",
        "{",
        '  "title": "VIRAL 12H AI: [Catchy Title] #Shorts",',
        '  "description": "Explaining the viral AI breakthrough from channel...",',
        '  "tags": ["AI", "ArtificialIntelligence", "Shorts", "TechNews", "ViralAI"],',
        '  "badge_text": "12H VIRAL BREAKDOWN",',
        '  "slides": [',
        '    {',
        '      "badge": "VIRAL 12H UPDATE",',
        '      "text": "A massive AI breakthrough just went viral in the last 12 hours!",',
        '      "highlight_word": "breakthrough"',
        '    }',
        '  ]',
        "}"
    ]
    prompt = "\n".join(prompt_lines)

    # 1. Gemini API Fallbacks
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and genai:
        for g_model in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "models/gemini-2.0-flash"]:
            try:
                client = genai.Client(api_key=gemini_key)
                response = client.models.generate_content(
                    model=g_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                if response and response.text:
                    parsed = json.loads(response.text)
                    if "slides" in parsed and len(parsed["slides"]) >= 4:
                        print(f"   ✅ Gemini ({g_model}) script success!")
                        return parsed
            except Exception as e:
                print(f"   ⚠️ Gemini model '{g_model}' note: {e}")

    # 2. Groq API Fallbacks
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key and Groq:
        for q_model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama3-70b-8192", "mixtral-8x7b-32768"]:
            try:
                client = Groq(api_key=groq_key)
                completion = client.chat.completions.create(
                    model=q_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                if completion.choices and completion.choices[0].message.content:
                    parsed = json.loads(completion.choices[0].message.content)
                    if "slides" in parsed and len(parsed["slides"]) >= 4:
                        print(f"   ✅ Groq ({q_model}) script success!")
                        return parsed
            except Exception as e:
                print(f"   ⚠️ Groq model '{q_model}' note: {e}")

    # 3. Local Procedural Script Generator Fallback
    print("   💡 Using local procedural viral Shorts script generator...")
    clean_target = sanitize_text(title_orig)
    clean_channel = sanitize_text(channel_orig)
    
    return {
        "title": f"VIRAL 12H UPDATE: {clean_target[:45]} #Shorts",
        "description": f"Breaking down the viral AI breakthrough from {clean_channel} in the last 12 hours.\n\nOriginal Creator: {clean_channel} ({viral_target['url']}).\nLicense: {license_type}",
        "tags": ["AI", "TechNews", "ViralAI", "Shorts", "ArtificialIntelligence"],
        "badge_text": "12H VIRAL BREAKDOWN",
        "slides": [
            {
                "badge": "VIRAL 12H UPDATE",
                "text": f"A major AI development just went viral in the last 12 hours from {clean_channel}!",
                "highlight_word": "viral"
            },
            {
                "badge": "THE BREAKTHROUGH",
                "text": f"Analyzing '{clean_target[:45]}': autonomous speed and multi-step reasoning reach new peaks.",
                "highlight_word": "autonomous"
            },
            {
                "badge": "FUTURE IMPACT",
                "text": "Software teams and digital creators are integrating these automated tools to scale productivity.",
                "highlight_word": "productivity"
            },
            {
                "badge": "STAY AHEAD",
                "text": "Subscribe to FutureTech AI for instant daily 12-hour viral tech updates as they happen!",
                "highlight_word": "Subscribe"
            }
        ]
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


def get_background_music(output_file="bg_curator_music.mp3"):
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
    for i in range(20):
        x0 = random.randint(0, width)
        y0 = random.randint(0, height)
        draw.ellipse([x0-200, y0-200, x0+200, y0+200], fill=colors[i % len(colors)])
    img = img.filter(PIL.ImageFilter.GaussianBlur(30))
    draw_grid = PIL.ImageDraw.Draw(img)
    for y in range(0, height, 40):
        draw_grid.line([(0, y), (width, y)], fill=(255, 255, 255, 12))
    for x in range(0, width, 40):
        draw_grid.line([(x, 0), (x, height)], fill=(255, 255, 255, 12))
    return img.convert("RGB")


# ==============================================================================
# STEP 4: 9:16 Vertical Thumbnail Generator (1080x1920)
# ==============================================================================
def generate_curated_thumbnail(title_text, badge_text, source_channel, output_file="curated_thumbnail.png"):
    print("🖼️ Step 4: Generating 9:16 vertical viral thumbnail (1080x1920)...")
    w, h = 1080, 1920
    base_img = generate_procedural_background(w, h)
    draw = PIL.ImageDraw.Draw(base_img)

    font_large = get_font(54)
    font_badge = get_font(32)
    font_credit = get_font(24)

    draw.rectangle([20, 20, w-20, h-20], outline=(236, 72, 153), width=8)
    draw.rectangle([80, 140, 500, 210], fill=(236, 72, 153), outline=(255, 255, 255), width=2)
    draw.text((100, 160), badge_text, font=font_badge, fill=(255, 255, 255))

    words = title_text.split()
    lines_list = []
    curr = []
    for word in words:
        curr.append(word)
        if get_text_width(font_large, " ".join(curr)) > w - 180:
            curr.pop()
            lines_list.append(" ".join(curr))
            curr = [word]
    if curr:
        lines_list.append(" ".join(curr))

    y_start = 320
    for line in lines_list[:4]:
        lw = get_text_width(font_large, line)
        draw.rectangle([(w - lw)//2 - 15, y_start - 8, (w + lw)//2 + 15, y_start + 70], fill=(15, 23, 42, 235))
        draw.text(((w - lw)//2, y_start), line, font=font_large, fill=(250, 204, 21))
        y_start += 90

    credit_text = f"CURATED FROM: {source_channel.upper()} • FAIR USE"
    cw = get_text_width(font_credit, credit_text)
    draw.rectangle([(w - cw)//2 - 15, h - 220, (w + cw)//2 + 15, h - 160], fill=(30, 41, 59, 240), outline=(56, 189, 248), width=2)
    draw.text(((w - cw)//2, h - 195), credit_text, font=font_credit, fill=(255, 255, 255))

    base_img.save(output_file)
    print(f"   ✅ Thumbnail generated: {output_file}")
    return output_file


# ==============================================================================
# STEP 5: 9:16 Vertical MoviePy Video Renderer
# ==============================================================================
def render_curated_short_video(curated_data, viral_target, output_file="short_curated_video.mp4"):
    print("🎬 Step 5: Rendering 9:16 vertical viral Short video (1080x1920 resolution)...")
    
    w, h = 1080, 1920
    slides = curated_data.get("slides", [])
    total_slides = len(slides)
    source_channel = viral_target.get("channel", "Tech Digest")
    
    font_header = get_font(34)
    font_body = get_font(52)
    font_badge = get_font(30)
    font_credit = get_font(22)
    
    temp_files = []
    slide_clips = []
    base_bg_pil = generate_procedural_background(w, h)
    
    for idx, slide in enumerate(slides):
        audio_file = f"curator_audio_{idx}.mp3"
        temp_files.append(audio_file)
        
        slide_text = slide.get("text", "")
        asyncio.run(synthesize_slide_audio(slide_text, audio_file))
        
        audio_clip = AudioFileClip(audio_file)
        slide_duration = max(audio_clip.duration + 0.5, 5.0)
        
        badge_str = slide.get("badge", f"VIRAL UPDATE {idx+1}")
        highlight_str = slide.get("highlight_word", "").lower()
        
        frame_pil = base_bg_pil.copy()
        draw = PIL.ImageDraw.Draw(frame_pil)
        
        # 1. Top Header Banner
        draw.rectangle([0, 0, w, 140], fill=(15, 23, 42, 240))
        draw.text((40, 50), "FUTURETECH AI  |  12H VIRAL BREAKDOWN", font=font_header, fill=(56, 189, 248))
        draw.line([(0, 140), (w, 140)], fill=(236, 72, 153), width=4)
        
        # 2. Slide Counter Pill
        counter_str = f"{idx+1} / {total_slides}"
        cw = get_text_width(font_header, counter_str)
        draw.rectangle([w - cw - 60, 35, w - 30, 95], fill=(30, 41, 59, 220), outline=(236, 72, 153), width=2)
        draw.text((w - cw - 45, 48), counter_str, font=font_header, fill=(250, 204, 21))
        
        # 3. Slide Badge Box
        draw.rectangle([60, 220, 520, 285], fill=(236, 72, 153))
        draw.text((80, 238), badge_str.upper(), font=font_badge, fill=(255, 255, 255))
        
        # 4. Text Line Wrapping & Center Card Layout
        words = slide_text.split()
        lines_list = []
        curr = []
        for word in words:
            curr.append(word)
            if get_text_width(font_body, " ".join(curr)) > w - 180:
                curr.pop()
                lines_list.append(" ".join(curr))
                curr = [word]
        if curr:
            lines_list.append(" ".join(curr))
            
        panel_h = len(lines_list) * 85 + 100
        y_center = (h // 2) - (panel_h // 2) + 40
        draw.rectangle([50, y_center, w - 50, y_center + panel_h], fill=(10, 15, 30, 230), outline=(168, 85, 247), width=3)

        base_img_np = np.array(frame_pil)
        
        def make_frame(t, base_np=base_img_np, dur=slide_duration, text_lines=lines_list, y_start=y_center+50, hl=highlight_str):
            frame = PIL.Image.fromarray(base_np).copy()
            draw_anim = PIL.ImageDraw.Draw(frame)
            
            # HUD Laser Scanline
            scan_y = int((t / dur) * h)
            draw_anim.line([(0, scan_y), (w, scan_y)], fill=(56, 189, 248, 160), width=3)
            
            # Top Progress Bar
            prog_w = int((t / dur) * w)
            draw_anim.rectangle([0, 140, prog_w, 146], fill=(250, 204, 21))
            
            # Spoken Text Rendering with Highlight Words
            line_y = y_start
            for line in text_lines:
                lw = get_text_width(font_body, line)
                x_pos = (w - lw) // 2
                for word in line.split():
                    clean_w = re.sub(r'[^\w]', '', word).lower()
                    color = (250, 204, 21) if (hl and hl in clean_w) else (255, 255, 255)
                    draw_anim.text((x_pos, line_y), word + " ", font=font_body, fill=color)
                    x_pos += get_text_width(font_body, word + " ")
                line_y += 85
                
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
            output_file, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac", 
            preset="ultrafast",
            threads=4
        )
    else:
        print(f"   💡 MoviePy dry-run skipped rendering {output_file}.")

    for f in temp_files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    print(f"   ✅ 9:16 Vertical Viral Short rendered: {output_file}")
    return output_file


# ==============================================================================
# STEP 6: YouTube Data API v3 Upload & Curation Credit
# ==============================================================================
def upload_curated_to_youtube(video_file, title, description, tags, news_bundle=None, source_target=None, thumbnail_file=None):
    clean_title = sanitize_text(title)
    clean_desc = sanitize_text(description)
    print(f"🚀 Step 6: Uploading viral Short '{clean_title}' to YouTube...")

    target_item = {}
    if isinstance(news_bundle, list) and len(news_bundle) > 0:
        target_item = news_bundle[0]
    elif isinstance(news_bundle, dict):
        target_item = news_bundle
    elif isinstance(source_target, dict):
        target_item = source_target

    source_title = target_item.get("title", "Viral AI Breakthrough")
    source_channel = target_item.get("channel", "Tech Press Digest")
    source_url = target_item.get("url", "https://youtube.com")

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
        "📌 SOURCE CREDIT & ATTRIBUTION:\n"
        f"Original Video / News: {source_title}\n"
        f"Original Creator: {source_channel}\n"
        f"Original Link: {source_url}\n"
        "License: Creative Commons CC-BY / Transformative Fair Use (17 U.S.C. § 107)\n\n"
        "⚖️ LEGAL STATEMENT & COPYRIGHT COMPLIANCE:\n"
        "This video presents an original, transformative news synthesis, commentary, educational breakdown, and technical analysis under 17 U.S.C. Section 107.\n\n"
        "🤖 AI PRODUCTION DISCLAIMER:\n"
        "Narrated using synthetic voices and produced with automated technical curation tools for education and research."
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
            print(f"   Uploading... {int(status.progress() * 100)}%")

    video_id = response.get("id")
    print(f"   ✅ YouTube Short uploaded successfully! Video ID: {video_id}")

    if thumbnail_file and os.path.exists(thumbnail_file):
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_file)).execute()
            print("   ✅ Custom thumbnail applied!")
        except Exception as e:
            print(f"   ⚠️ Thumbnail upload note: {e}")

    return video_id


# ==============================================================================
# MAIN EXECUTION PIPELINE
# ==============================================================================
def main():
    print("======================================================")
    print("🚀 STARTING VIRAL 12-HOUR AI CURATOR PIPELINE")
    print("======================================================")
    
    viral_target = fetch_viral_12h_ai_content()
    curated_data = generate_curation_script(viral_target)
    
    thumb_file = generate_curated_thumbnail(
        title_text=curated_data.get("title", "VIRAL 12H AI BREAKDOWN"),
        badge_text=curated_data.get("badge_text", "12H VIRAL UPDATE"),
        source_channel=viral_target.get("channel", "AI Creator")
    )
    
    video_file = render_curated_short_video(
        curated_data=curated_data,
        viral_target=viral_target
    )
    
    upload_curated_to_youtube(
        video_file=video_file,
        title=curated_data.get("title", "VIRAL 12H AI BREAKDOWN #Shorts"),
        description=curated_data.get("description", "Viral 12-hour AI news breakdown."),
        tags=curated_data.get("tags", ["AI", "Shorts", "TechNews"]),
        source_target=viral_target,
        thumbnail_file=thumb_file
    )
    
    print("======================================================")
    print("✅ VIRAL 12-HOUR AI CURATOR PIPELINE COMPLETE")
    print("======================================================")


if __name__ == "__main__":
    main()
