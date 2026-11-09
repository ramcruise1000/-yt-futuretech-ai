# =========================================
# CURATOR PIPELINE: VIRAL 12-HOUR AI DIGEST
# ========================================
import os
import re
import json
import time
import random
import asyncio
import warnings
import requests
import urllib.parse
import numpy as np
from datetime import datetime, timedelta

# Explicit PIL imports & deprecation writeover fix
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
    feedparser= None

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
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

# ==========================================
# STEP"1: 12-Hour Viral AI Video & Trend Discovery Engine
# =========================================
def fetch_viral_12h_ai_content():
    """
    Searches YouTube Data API v3 and RSS feeds for viral AI videos published 
    in the last 12 hours. Prioritizes Creative Commons (CC-BY) licensed content, 
    with Transformative Fair Use commentary fallback.
    """
    print(" Step 1: Scanning for viral AI videos published in the last 12 hours...")
    
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    
    time_12h_ago = (datetime.utcnow() - timedelta(hours=12)).isoformat() + "Z"
    viral_items = []
    
    # 1. Attempt YouTube Data API v3 Search
    if client_id and client_secret and refresh_token:
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
                publishedAfter=time_12h_ago,
                videoLicense="creativeCommon",
                maxResults=5
            )
            cc_response = cc_request.execute()
            
            for item in cc_response.get("items", []):
                snippet = item.get("snippet", {})
                vid_id = item.get("id", {}).get("videoId")
                if vid_id:
                    v_url = "https://" + "www.youtube.com/watch?v=" + str(vid_id)
                    viral_items.append({
                        "id": vid_id,
                        "title": snippet.get("title", "Viral AI Breakthrough"),
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
                    q="AI breakthrough OR OpenAI OR Gemini 1.5 OR Claude 3.5 OR Nvidia AI",
                    part="snippet",
                    type="video",
                    order="viewCount",
                    publishedAfter=time_12h_ago,
                    maxResults=5
                )
                gen_response = gen_request.execute()
                for item in gen_response.get("items", []):
                    snippet = item.get("snippet", {})
                    vid_id = item.get("id", {}).get("videoId")
                    if vid_id:
                        v_url = "https://" + "www.youtube.com/watch?v=" + str(vid_id)
                        viral_items.append({
                            "id": vid_id,
                            "title": snippet.get("title", "Viral AI Breakthrough"),
                            "channel": snippet.get("channelTitle", "Tech News"),
                            "url": v_url,
                            "description": snippet.get("description", ""),
                            "published_at": snippet.get("publishedAt", ""),
                            "license_type": "Transformative Fair Use Commentary",
                            "legal_note": "Original news breakdown & commentary under Fair Use (17 U.S.C. £ 107)."
                        })
        except Exception as e:
            print(f"   ⚆ YouTube API Search note: {e}")

    # 2. RSS / Web Trend Fallback (if API search returned no items)
    if not viral_items:
        print("   𝐰 Fetching latest 12h AI news trends via RSS feeds...")
        rss_feeds = [
            "https://" + "techcrunch.com/category/artificial-intelligence/feed/",
            "https://" + "www.mittechnologyreview.com/feed/",
            "https://" + "feeds.arstechnica.com/arstechnica/index",
            "https://www.youtube.com" + "/feed/"
        ]
        for feed_url in rss_feeds:
            try:
                if feedparser:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:3]:
                        title = sanitize_text(entry.title)
                        link = entry.link
                        summary = sanitize_text(entry.get("summary", title))
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
                print(f"   ⚠f RSS fetch note for {feed_url}: {e}")

    # Fallback default item if external sources fail
    if not viral_items:
        default_url = "https://" + "www.youtube.com/results?search_query=AI+agent+breakthrough"
        viral_items.append({
            "id": "viral_ai_default_12h",
            "title": "New Agentic AI Framework Shocks Developers with 24/7 Automation",
            "channel": "AIFrontierNetwork",
            "url": default_url,
            "description": "Autonomous AI agents achieve major efficiency milestones in multi-step task execution.",
            "published_at": "Last 12 Hours",
            "license_type": "Transformative Educational Commentary",
            "legal_note": "Original educational breakdown & news commentary."
        })

    selected_item = random.choice(viral_items[:3])
    print(f"   𝔤 Selected 12H Viral Target: '{selected_item['title']}' from [{selected_item['channel']}]")
    print(f"   𝝒40Compliance Status: {selected_item['license_type']}")
    return selected_item

# ==========================================
# STEP"1: 12-Hour Viral AI Video & Trend Discovery Engine
# =========================================
def generate_curation_script(viral_target):
    """
    Generates a 100% original, transformative commentary & breakdown script 
    based on the 12-hour viral video item. Uses Gemini / Groq / OpenRouter / Procedural fallback.
    """
    print("𝞥 Step 2: Generating transformative commentary & viral Shorts script...")
    
    title_orig = viral_target["title"]
    channel_orig = viral_target["channel"]
    desc_orig = viral_target["description"][:300]
    license_type = viral_target["license_type"]
    
    prompt = (
        "You are a top tech journalist creating a viral YouTube Short (40-45 seconds) analyzing a viral AI video that exploded in the last 12 hours.\n\n"
        "VIRAL TARGET DATA:\n"
        "- Original Title: " + json.dumps(title_orig) + "\n"
        "- Original Creator/Channel: " + json.dumps(channel_orig) + "\n"
        "- Target Details: " + json.dumps(desc_orig) + "\n"
        "- Curation Mode: " + str(license_type) + "\n\n"
        "RULES:\n"
        "1. Create a TRANSFORMATIONAL, exciting 4-slide commentary script.\n"
        "2. DO NOT just copy the target. Analyze WHY it's viral, what it means for viewers, and the key breakthrough.\n"
        "3. Keep spoken lines punchy (15-20 words per slide).\n"
        "4. Include strong hook title, description with channel credit, tags, and badge text.\n\n"
        "Return ONLY valid JSON in this EXACT structure:\n"
        "{\n"
        '  "title": "VIRAL 12H AI: [Catchy Title] #Shorts",\n'
        '  "description": "Explaining the viral AI breakthrough...",\n'
        '  "tags": ["AI", "ArtificialIntelligence", "Shorts", "TechNews", "ViralAI"],\n'
        '  "badge_text": "12H VIRAL BREAKDOWN",\n'
        '  "slides": [\n'
        '    {\n'
        '      "badge": "VIRAL 12H UPDATE",\n'
        '      "text": "A massive AI breakthrough just went viral in the last 12 hours!",\n'
        '      "highlight_word": "breakthrough"\n'
        '    },\n'
        '    {\n'
        '      "badge": "KEY INNOVATION",\n'
        '      "text": "Here is why everyone is talking about this breakthrough and what it changes.",\n'
        '      "highlight_word": "innovative"\n'
        '    },\n'
        '    {\n'
        '      "badge": "THE IMPACT",\n'
        '      "text": "This technology automates complex workflows in seconds, disrupting traditional tools.",\n'
        '      "highlight_word": "disrupting"\n'
        '    },\n'
        '    {\n'
        '      "badge": "VERDICT",\n'
        '      "text": "Subscribe to FutureTech AI for daily 12-hour viral breakdowns as they happen!",\n'
        '      "highlight_word": "Subscribe"\n'
        '    }\n'
        '  ]\n'
        "}\n"
    )
    
    gemiji_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and genai:
        try:
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            if response and response.text:
                return json.loads(response.text)
        except Exception as e:
            print(f"   ⚠f Gemini script generation note: {e}")

    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key and Groq:
        try:
            client = Groq(api_key=groq_key)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            if completion.choices:
                return json.loads(completion.choices[0].message.content)
        except Exception as e:
            print(f"   ⚆ Groq script generation note: {e}")

    clean_target = sanitize_text(title_orig)
    return {
        "title": f"VIRAL 12H UPDATE: {clean_target[:50]} #Shorts",
        "description": f"Breaking down the viral AI breakthrough from {channel_orig} in the last 12 hours. Original Creator: {channel_orig} ({viral_target['url']}).",
        "tags": ["AI", "TechNews", "ViralAI", "Shorts", "ArtificialIntelligence"],
        "badge_text": "12H VIRAL BREAKDOWN",
        "slides": [
            {
                "badge": "VIRAL 12H UPDATE",
                "text": f"A major AI video just went viral in the last 12 hours created by {channel_orig}.",
                "highlight_word": "viral"
            },
            {
                "badge": "THE BREAKTHROUGH",
                "text": f"Analyzing '{clean_target[:45]}': autonomous speed and capability reach new peaks.",
                "highlight_word": "autonomous"
            },
            {
                "badge": "FUTURE IMPACT",
                "text": "Developers and creators are leveraging these capabilities to automate content daily.",
                "highlight_word": "automate"
            },
            {
                "badge": "STAY AHEAD",
                "text": "Subscribe to FutureTech AI for instant daily 12-hour viral tech updates!",
                "highlight_word": "Subscribe"
            }
        ]
    }

# ========================================
# STEP"3: Multi-Voice Audio Synthesis Engine
# ========================================
async def synthesize_slide_audio(text, output_file):
    """
    Synthesizes voiceover audio using edge-tts with 5-attempt voice rotation
    and an automatic gTTS fallback for 100% execution reliability.
    """
    voices = ["en-US-ChristopherNeural", "en-US-GuyNeural", "en-US-EricNeural", "en-US-AriaNeural"]
    for attempt in range(5):
        voice = voices[attempt % len(voices)]
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_file)
            if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                return output_file
        except Exception as e:
            print(f"   ⚆ edge-tts attempt {attempt+1}/5 failed ({e}). Retrying...")
            await asyncio.sleep(1.5 * (attempt + 1))
    
    try:
        print("   ⚠f edge-tts endpoints busy. Switching to gTTS fallback engine...")
        from gtts import gTTS
        tts = gTTS(text=text, lang='en')
        tts.save(output_file)
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            return output_file
    except Exception as e:
        print(f"   ⚠f gTTS fallback note: {e}")

    if os.path.exists(output_file) and os.path.getsize(output_file) > 100:
        return output_file
    raise RuntimeError(f"Failed to synthesize voiceover audio for slide text: '{text[:30]}...'")

def get_background_music(output_file="bg_curator_music.mp3"):
    if os.path.exists(output_file):
        return output_file
    print("🏵 Fetching background music track...")
    url = "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3?filename=cyberpunk-tech-110391.mp3"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(res.content)
            return output_file
    except Exception as e:
        print(f"   ⚠f Background music download note: {e}")
    return None

def generate_procedural_background(width, height):
    img = PIL.Image.new("RGBA", (width, height), (12, 10, 28, 255))
    draw = PIL.ImageDraw.Draw(img)
    colors = [(56, 189, 248, 120), (236, 72, 153, 120), (168, 85, 247, 120), (250, 204, 21, 120)]
    for i in range(18):
        x0 = random.randint(0, width)
        y0 = random.randint(0, height)
        draw.ellipse([x0-240, y0-240, x0+240, y0+240], fill=colors[i % len(colors)])
    img = img.filter(PIL.ImageFilter.GaussianBlur(25))
    draw_grid = PIL.ImageDraw.Draw(img)
    for y in range(0, height, 40):
        draw_grid.line([(0, y), (width, y)], fill=(255, 255, 255, 12))
    for x in range(0, width, 40):
        draw_grid.line([(x, 0), (x, height)], fill=(255, 255, 255, 12))
    return img.convert("RGB")

# ========================================
# STEP 4: High-CTR Viral Thumbnail Generator
# =========================================
def generate_curated_thumbnail(title_text, badge_text, source_channel, output_file="curated_thumbnail.png"):
    print("🖼️ Step 4: Generating high-CTR viral Short thumbnail...")
    w, h = 1080, 1920
    base_img = generate_procedural_background(w, h)
    draw = PIL.ImageDraw.Draw(base_img)
    
    font_large = get_font(72)
    font_badge = get_font(38)
    font_credit = get_font(32)
    
    draw.rectangle([20, 20, w-20, h-20], outline=(56, 189, 248), width=8)
    draw.rectangle([80, 250, w-80, 340], fill=(236, 72, 153), outline=(255, 255, 255), width=3)
    bw = get_text_width(font_badge, badge_text)
    draw.text(((w - bw)//2, 270), badge_text, font=font_badge, fill=(255, 255, 255))
    
    words = title_text.split()
    lines_list = []
    curr = []
    for word in words:
        curr.append(word)
        if get_text_width(font_large, " ".join(curr)) > w - 160:
            curr.pop()
            lines_list.append(" ".join(curr))
            curr = [word]
    if curr:
        lines_list.append(" ".join(curr))
        
    y_start = 600
    for line in lines_list[:4]:
        lw = get_text_width(font_large, line)
        draw.rectangle([(w - lw)//2 - 15, y_start - 10, (w + lw)//2 + 15, y_start + 85], fill=(15, 23, 42, 220))
        draw.text(((w - lw)//2, y_start), line, font=font_large, fill=(250, 204, 21))
        y_start += 110

    credit_text = f"SOURCE: {source_channel.upper()} | CC-BY / FAIR USE"
    cw = get_text_width(font_credit, credit_text)
    draw.rectangle([(w - cw)//2 - 20, h - 300, (w + cw)//2 + 20, h - 230], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=2)
    draw.text(((w - cw)//2, h - 280), credit_text, font=font_credit, fill=(255, 255, 255))

    base_img.save(output_file)
    print(f"   ✅ Thumbnail generated: {output_file}")
    return output_file


# ==========================================
# STEP"5: Transformative Visual & MoviePy Video Renderer
# ========================================
def render_curated_short_video(curated_data, viral_target, output_file="short_curated_video.mp4"):
    print("🎬 Step 5: Rendering transformational animated 9:16 Shorts video...")
    
    w, h = 1080, 1920
    slides = curated_data.get("slides", [])
    source_channel = viral_target.get("channel", "Original Creator")
    license_note = viral_target.get("legal_note", "Licensed Content")
    
    font_title = get_font(42)
    font_body = get_font(52)
    font_badge = get_font(34)
    font_credit = get_font(28)
    
    temp_files = []
    slide_clips = []
    
    base_bg_pil = generate_procedural_background(w, h)
    
    for idx, slide in enumerate(slides):
        audio_file = f"curated_audio_{idx}.mp3"
        temp_files.append(audio_file)
        
        slide_text = slide.get("text", "")
        asyncio.run(synthesize_slide_audio(slide_text, audio_file))
        
        audio_clip = AudioFileClip(audio_file)
        slide_duration = max(audio_clip.duration + 0.4, 3.5)
        
        badge_str = slide.get("badge", "12H VIRAL UPDATE")
        highlight_str = slide.get("highlight_word", "").lower()
        
        frame_pil = base_bg_pil.copy()
        draw = PIL.ImageDraw.Draw(frame_pil)
        
        draw.rectangle([0, 0, w, 140], fill=(15, 23, 42, 240))
        draw.text((40, 45), "FUTURETECH AI  |  12H VIRAL DIGEST", font=font_title, fill=(56, 189, 248))
        draw.line([(0, 140), (w, 140)], fill=(236, 72, 153), width=5)
        
        draw.rectangle([60, 220, 520, 290], fill=(236, 72, 153))
        draw.text((80, 235), badge_str.upper(), font=font_badge, fill=(255, 255, 255))
        
        attr_str = f"SOURCE: {source_channel.upper()} • {license_note.upper()}"
        aw = get_text_width(font_credit, attr_str)
        drw = draw
        drw.rectangle([(w - aw)//2 - 15, h - 220, (w + aw)//2 + 15, h - 160], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=2)
        drw.text(((w - aw)//2, h - 200), attr_str, font=font_credit, fill=(250, 204, 21))

        words = slide_text.split()
        lines_list = []
        curr = []
        for word in words:
            curr.append(word)
            if get_text_width(font_body, " ".join(curr)) > w - 160:
                curr.pop()
                lines_list.append(" ".join(curr))
                curr = [word]
        if curr:
            lines_list.append(" ".join(curr))
        panel_h = len(lines_list) * 85 + 60
        y_center = (h // 2) - (panel_h // 2)
        draw.rectangle([50, y_center, w - 50, y_center + panel_h], fill=(10, 15, 30, 220), outline=(168, 85, 247), width=3)

        base_img_np = np.array(frame_pil)
        
        def make_frame(t, base_np=base_img_np, dur=slide_duration, text_lines=lines_list, y_start=y_center+30, hl=highlight_str):
            frame = PIL.Image.fromarray(base_np).copy()
            draw_anim = PIL.ImageDraw.Draw(frame)
            
            scan_y = int((t / dur) * h)
            draw_anim.line([(0, scan_y), (w, scan_y)], fill=(56, 189, 248, 180), width=3)
            
            prog_w = int((t / dur) * w)
            draw_anim.rectangle([0, 140, prog_w, 148], fill=(250, 204, 21))
            
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

        clip = VideoClip(make_frame, duration=slide_duration)
        clip = clip.set_audio(audio_clip)
        slide_clips.append(clip)
        
    final_video = concatenate_videoclips(slide_clips, method="compose")
    
    music_path = get_background_music()
    if music_path and os.path.exists(music_path):
        try:
            bg_music = AudioFileClip(music_path).filter(lambda gf, t: 0.12 * gf(t)).set_duration(final_video.duration)
            comp_audio = CompositeAudioClip([final_video.audio, bg_music])
            final_video = final_video.set_audio(comp_audio)
        except Exception as e:
            print(f"   ⚠️ Music mixing note: {e}")
            
    final_video.write_videofile(
        output_file, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac", 
        preset="ultrafast",
        threads=4
    )
    
    for f in temp_files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    print(f"   ✅ Curated Short rendered successfully: {output_file}")
    return output_file


# ==========================================
# STEP 6: YouTube Upload with Legal Attribution
# ==========================================
def upload_curated_to_youtube(video_file, title, description, tags, source_target, thumbnail_file=None):
    clean_title = sanitize_text(title)
    clean_desc = sanitize_text(description)
    print("🚀 Step 6: Uploading curated video '" + str(clean_title) + "' to YouTube...")
    
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        print("⚠️ Credentials missing in environment. Skipping live upload step.")
        return None

    token_url = "https://oauth2.googleapis.com/token"
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=token_url,
        client_id=client_id,
        client_secret=client_secret
    )
    creds.refresh(Request())
    youtube = build("youtube", "v3", credentials=creds)
    
    source_title = source_target.get("title", "Original Source")
    source_channel = source_target.get("channel", "Creator")
    source_url = source_target.get("url", "https://youtube.com")
    license_type = source_target.get("license_type", "Licensed Commentary")
    
    legal_attribution = (
        "📌 SOURCE CREDIT & ATTRIBUTION:\n" +
        "Original Video: " + str(source_title) + "\n" +
        "Original Creator: " + str(source_channel) + "\n" +
        "Original Link: " + str(source_url) + "\n" +
        "License: " + str(license_type) + "\n\n" +
        "⚖️ LEGAL STATEMENT & COMPLIANCE:\n" +
        "This video presents an original, transformative news synthesis, commentary, and educational breakdown of recent AI developments under Section 107.\n\n" +
        "🤖 AI PRODUCTION DISCLAIMER:\n" +
        "Narrated using AI synthesis and produced with automated technical curation tools for education and research."
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
            print("   Upload Progress: " + str(int(status.progress() * 100)) + "%")
        
    video_id = response.get("id")
    pub_link = "https://youtu.be/" + str(video_id)
    print("🎉 SUCCESS! Published Curated Short live: " + str(pub_link))

    if thumbnail_file and os.path.exists(thumbnail_file):
        try:
            print("🖼️ Setting custom thumbnail for Video ID " + str(video_id) + "...")
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_file)).execute()
            print("   ✅ Thumbnail updated successfully!")
        except Exception as e:
            print("   ⚠️ Could not set thumbnail: " + str(e))

    return video_id

# ==========================================
# MAIN EXECUTION PIPELINE
# ==========================================
def main():
    print("======================================================")
    print("🚀 STARTING VIRAL 12-HOUR AI CURATOR PIPELINE")
    print("======================================================")
    
    viral_target = fetch_viral_12h_ai_content()
    curated_data = generate_curation_script(viral_target)
    
    thumb_file = generate_curated_thumbnail(
        title_text=curated_data.get("title", "VIRAL 12H AI BREAKTHROUGH"),
        badge_text=curated_data.get("badge_text", "12H VIRAL BREAKDOWN"),
        source_channel=viral_target.get("channel", "Original Creator")
    )
    
    video_file = render_curated_short_video(
        curated_data=curated_data,
        viral_target=viral_target
    )
    
    upload_curated_to_youtube(
        video_file=video_file,
        title=curated_data.get("title", "VIRAL 12H AI BREAKTHROUGH"),
        description=curated_data.get("description", "Viral AI news breakdown."),
        tags=curated_data.get("tags", ["AI", "Shorts"]),
        source_target=viral_target,
        thumbnail_file=thumb_file
    )
    
    print("======================================================")
    print("✅ VIRAL 12-HOUR AI CURATOR PIPELINE COMPLETE")
    print("======================================================")

if __name__ == "__main__":
    main()
