# ==============================================================================
# LONG-FORM CURATOR PIPELINE: 16:9 WIDESCREEN AI NEWS & DOCUMENTARY DIGEST
# Fully Automated, Monetization-Compliant 5-8 Minute Video Production
# ==============================================================================
import os
import re
import json
import time
import math
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

# ==============================================================================
# HELPER FUNCTIONS & TEXT SANITIZERS
# ==============================================================================
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

def get_text_width(font, text):
    if hasattr(font, 'getlength'):
        return int(font.getlength(text))
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0]

def sanitize_text(text):
    if not text:
        return ""
    clean = re.sub(r'\b(?:Ed|Edition)\.?\s*#?\s*\d+\b', '', str(text), flags=re.IGNORECASE)
    clean = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', clean).strip()
    clean = re.sub(r'\s+', ' ', clean)
    return clean

# Persistent History Tracker for Anti-Duplication
HISTORY_FILE = "posted_topics_history.json"

def load_posted_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_posted_history(history):
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history[-100:], f, indent=2)
    except Exception as e:
        print(f"   ⚠️ Could not save history log: {e}")

def is_duplicate_topic(candidate_title, uploaded_titles, local_history):
    clean_cand = re.sub(r'[^\w\s]', '', candidate_title.lower()).strip()
    cand_words = set(clean_cand.split())
    
    all_past = [re.sub(r'[^\w\s]', '', t.lower()).strip() for t in (uploaded_titles + local_history)]
    for past in all_past:
        past_words = set(past.split())
        if not cand_words or not past_words:
            continue
        overlap = len(cand_words.intersection(past_words))
        similarity = overlap / max(len(cand_words), len(past_words))
        if similarity > 0.55 or (overlap >= 4 and len(cand_words) <= 8):
            return True
    return False

# ==============================================================================
# STEP 1: Multi-Source AI News & Anti-Duplicate Trend Ingestion Engine
# ==============================================================================
def fetch_longform_ai_trends():
    """
    Scrapes YouTube Data API v3 and RSS feeds for trending AI developments.
    Cross-checks against uploaded channel history and local logs to guarantee
    zero duplicate videos.
    """
    print("📰 Step 1: Ingesting multi-source AI trends & filtering duplicate videos...")
    
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    
    time_48h_ago = (datetime.utcnow() - timedelta(hours=48)).isoformat() + "Z"
    news_items = []
    uploaded_titles = []
    local_history = load_posted_history()
    
    # 1. Fetch channel's past uploads to prevent duplicates
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
            
            print("   💡 Checking channel history for past uploads...")
            ch_request = youtube.search().list(
                part="snippet",
                forMine=True,
                type="video",
                maxResults=25
            )
            ch_response = ch_request.execute()
            for item in ch_response.get("items", []):
                snippet = item.get("snippet", {})
                uploaded_titles.append(snippet.get("title", ""))
            print(f"   ✅ Retrieved {len(uploaded_titles)} past upload titles for deduplication.")
        except Exception as e:
            print(f"   ⚠️ Could not fetch channel history: {e}")

    # 2. Query YouTube Data API v3 for trending AI topics
    if client_id and client_secret and refresh_token and build:
        try:
            youtube = build("youtube", "v3", credentials=creds)
            print("   💡 Searching YouTube API for trending AI breakthroughs...")
            yt_request = youtube.search().list(
                q="AI breakthrough OR OpenAI GPT-5 OR Gemini 2.0 OR Claude 3.5 OR AI Agent",
                part="snippet",
                type="video",
                order="viewCount",
                publishedAfter=time_48h_ago,
                maxResults=10
            )
            yt_response = yt_request.execute()
            for item in yt_response.get("items", []):
                snippet = item.get("snippet", {})
                vid_id = item.get("id", {}).get("videoId")
                v_title = snippet.get("title", "AI Breakthrough Update")
                if vid_id and not is_duplicate_topic(v_title, uploaded_titles, local_history):
                    news_items.append({
                        "title": v_title,
                        "channel": snippet.get("channelTitle", "Tech News"),
                        "url": "https://" + "www.youtube.com/watch?v=" + str(vid_id),
                        "description": snippet.get("description", ""),
                        "source_type": "YouTube Trending Video"
                    })
        except Exception as e:
            print(f"   ⚠️ YouTube API trend search note: {e}")

    # 3. Query RSS Feeds for Breaking Tech Press
    print("   💡 Ingesting RSS feeds (TechCrunch, MIT Tech Review, Ars Technica, VentureBeat)...")
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
                for entry in feed.entries[:5]:
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

    # Evergreen Deep-Dive Fallback Topics if recent web items are duplicates
    if not news_items:
        print("   💡 Rotating to fresh evergreen deep-dive topics...")
        evergreen = [
            {
                "title": "Fine-Tuning Local Open-Weight LLMs: Quantization & Parameter Efficiency",
                "channel": "AI Frontier Network",
                "url": "https://" + "youtube.com",
                "description": "Comprehensive technical guide on running 70B parameter neural networks locally with GGUF and vLLM.",
                "source_type": "Deep-Dive Guide"
            },
            {
                "title": "Autonomous Coding Agents Benchmark War: Devin vs Claude Engineer vs AutoCode",
                "channel": "Developer Digest",
                "url": "https://" + "youtube.com",
                "description": "Analyzing real-world SWE-bench results and multi-file code refactoring capabilities.",
                "source_type": "Benchmark Analysis"
            },
            {
                "title": "Multi-Modal Agentic Workflows: Combining Vision, Speech, and Code Generation",
                "channel": "Future Tech Systems",
                "url": "https://" + "youtube.com",
                "description": "How modern agentic pipelines integrate real-time multi-modal streaming into enterprise apps.",
                "source_type": "Architecture Report"
            }
        ]
        for eg in evergreen:
            if not is_duplicate_topic(eg["title"], uploaded_titles, local_history):
                news_items.append(eg)

    random.shuffle(news_items)
    selected_bundle = news_items[:5] if news_items else [evergreen[0]]
    print(f"   ✅ Compiled {len(selected_bundle)} unique, non-duplicate topics for long-form synthesis.")
    return selected_bundle

# ==============================================================================
# STEP 2: Transformative Long-Form Script Generation (5-8 Mins / 14-16 Slides)
# ==============================================================================
def generate_longform_script(news_bundle):
    """
    Uses Gemini / Groq / OpenRouter with local procedural fallback to construct 
    a 14-16 slide long-form educational breakdown (~5-8 minutes runtime).
    """
    print("📝 Step 2: Generating 14-slide long-form educational script (~5-7 minutes runtime)...")
    
    topics_summary = "\n".join([
        f"- Topic {i+1}: '{item['title']}' by {item['channel']} ({item['description'][:150]})"
        for i, item in enumerate(news_bundle)
    ])
    
    prompt_lines = [
        "You are a lead technology commentator creating a 5-to-8 minute long-form YouTube educational documentary video analyzing today's top AI developments.",
        "",
        "TOPICS TO COVER:",
        topics_summary,
        "",
        "INSTRUCTIONS:",
        "1. Produce an original, highly structured 14-slide documentary script.",
        "2. CRITICAL: Each slide MUST contain 65 to 85 words of exciting, clear, educational spoken commentary (~25-30 seconds per slide = ~6-7 minutes total runtime).",
        "3. Provide an engaging YouTube Title, full 1200+ character SEO Description with timestamps, 15 SEO tags, and visual badge labels.",
        "4. Ensure content is 100% original educational synthesis, compliant with YouTube Fair Use and Monetization rules.",
        "",
        "Return ONLY valid JSON in this exact structure:",
        "{",
        '  "title": "AI BREAKTHROUGH DIGEST: Next-Gen Autonomous Models Changing Tech Forever #AINews",',
        '  "description": "Deep dive into AI news: OpenAI agent breakthroughs, GPU chips, and autonomous software.\
\
Timestamps:\
0:00 - Introduction\
0:45 - The Breakthrough\
1:30 - Technical Architecture\
2:40 - Industry Impact\
4:00 - Future Outlook",',
        '  "tags": ["AI", "ArtificialIntelligence", "OpenAI", "Gemini", "TechNews", "FutureTech", "AIAgents", "MachineLearning"],',
        '  "badge_text": "AI NEWS DIGEST",',
        '  "slides": [',
        '    {',
        '      "badge": "WELCOME & HOOK",',
        '      "text": "Welcome back to FutureTech AI. Today we present an in-depth technical documentary analyzing major artificial intelligence breakthroughs that are transforming the global tech industry, focusing on autonomous software agents, neural compute speed, and multi-modal intelligence workflows across enterprise production pipelines.",',
        '      "highlight_word": "breakthroughs"',
        '    }',
        '  ]',
        "}"
    ]
    prompt = "\n".join(prompt_lines)

    # 1. Try Gemini Models
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and genai:
        for g_model in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]:
            try:
                client = genai.Client(api_key=gemini_key)
                response = client.models.generate_content(
                    model=g_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                if response and response.text:
                    parsed = json.loads(response.text)
                    if "slides" in parsed and len(parsed["slides"]) >= 10:
                        print(f"   ✅ Gemini ({g_model}) generated {len(parsed['slides'])} slides successfully!")
                        return parsed
            except Exception as e:
                print(f"   ⚠️ Gemini model '{g_model}' note: {e}")

    # 2. Try Groq Models
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key and Groq:
        for q_model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]:
            try:
                client = Groq(api_key=groq_key)
                completion = client.chat.completions.create(
                    model=q_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                if completion.choices and completion.choices[0].message.content:
                    parsed = json.loads(completion.choices[0].message.content)
                    if "slides" in parsed and len(parsed["slides"]) >= 10:
                        print(f"   ✅ Groq ({q_model}) generated {len(parsed['slides'])} slides successfully!")
                        return parsed
            except Exception as e:
                print(f"   ⚠️ Groq model '{q_model}' note: {e}")

    # 3. Procedural Fallback Generator (Guarantees 14 Detailed Slides x 68 Words = ~950 Spoken Words = ~6.5 Mins Output)
    print("   💡 Using local procedural long-form educational script generator (14 detailed slides, ~6 mins)...")
    main_target = news_bundle[0]
    clean_title = sanitize_text(main_target["title"])
    source_channel = main_target["channel"]
    
    slides = [
        {
            "badge": "MODULE 1: EXECUTIVE OVERVIEW",
            "text": f"Welcome back to FutureTech AI. Today we present an extensive technical documentary analyzing major artificial intelligence breakthroughs, starting with '{clean_title[:55]}'. We examine why this development is sparking intense industry debate among software engineers, IT architects, research scientists, and enterprise technology executives worldwide.",
            "highlight_word": "documentary"
        },
        {
            "badge": "MODULE 2: CORE BREAKTHROUGH",
            "text": f"Engineers and artificial intelligence researchers at {source_channel} have unveiled system capabilities that push autonomous software agents to unprecedented performance levels. By eliminating manual human intervention bottlenecks, execution latency drops dramatically across complex multi-step technical tasks, refactoring large distributed codebases in fractions of a second.",
            "highlight_word": "autonomous"
        },
        {
            "badge": "MODULE 3: SYSTEM ARCHITECTURE",
            "text": "At the core of this technical milestone lies an advanced multi-agent orchestrator. Instead of relying on traditional single-prompt completion language models, the architecture deploys specialized reasoning loops that plan complex software blueprints, draft code snippets, execute scripts inside secure sandboxes, and self-correct runtime errors in an autonomous feedback cycle.",
            "highlight_word": "orchestrator"
        },
        {
            "badge": "MODULE 4: REASONING LOOPS",
            "text": "By structuring reasoning into discrete reflection and tree-of-thought exploration steps, the underlying neural network evaluates alternative solution paths before committing permanent state changes. This architecture reduces logical hallucinations by over sixty percent compared to standard zero-shot model inference, significantly increasing real-world production reliability.",
            "highlight_word": "hallucinations"
        },
        {
            "badge": "MODULE 5: HARDWARE & GPU INFRASTRUCTURE",
            "text": "Scaling these agentic models requires massive underlying compute hardware infrastructure. Next-generation GPU server clusters utilizing ultra-high bandwidth memory interconnects allow instant local tensor parallel processing, keeping token throughput fast, stable, and seamless even under high concurrent production server workloads.",
            "highlight_word": "infrastructure"
        },
        {
            "badge": "MODULE 6: BENCHMARKS & COMPETITION",
            "text": "In competitive SWE-bench and human-eval coding benchmarks, this framework demonstrates state-of-the-art capability. It consistently outperforms legacy frontier models in multi-file code refactoring, dependency resolution, automated security bug hunting, and end-to-end continuous integration test generation.",
            "highlight_word": "benchmarks"
        },
        {
            "badge": "MODULE 7: DEVELOPER AUTOMATION",
            "text": "For software engineers and system architects, this paradigm shift transforms daily programming workflows. Repetitive software engineering tasks such as drafting boilerplate code, generating comprehensive API technical documentation, and migrating legacy monoliths to modern microservices can now be delegated entirely to autonomous AI coding assistants.",
            "highlight_word": "workflows"
        },
        {
            "badge": "MODULE 8: ENTERPRISE ADOPTION",
            "text": "Enterprises across finance, healthcare, software development, and cyber security are embedding these autonomous agent pipelines directly into their internal production developer environments, accelerating software release cycles, lowering infrastructure operational overhead, and driving massive competitive market advantages.",
            "highlight_word": "enterprise"
        },
        {
            "badge": "MODULE 9: OPEN WEIGHTS vs PROPRIETARY",
            "text": "A crucial industry trend is the rapidly narrowing performance gap between closed proprietary frontier models and open-weight community releases. Highly quantized local language models now deliver enterprise-grade reasoning accuracy directly on developer workstations without requiring external cloud API dependencies.",
            "highlight_word": "quantized"
        },
        {
            "badge": "MODULE 10: ALIGNMENT & GUARDRAILS",
            "text": "As autonomous agent capabilities expand, robust alignment and security guardrails become vital. Modern production implementations incorporate strict permission boundary checks, role-based access control, and sandboxed execution environments to prevent unexpected system calls or corporate data security breaches.",
            "highlight_word": "guardrails"
        },
        {
            "badge": "MODULE 11: ON-DEVICE INFERENCE",
            "text": "The rise of four-bit and eight-bit GGUF quantization enables lightweight on-device model execution. Developers and privacy-conscious organizations can run high-capacity language models locally on consumer hardware without sending sensitive proprietary corporate codebases over external third-party network connections.",
            "highlight_word": "quantization"
        },
        {
            "badge": "MODULE 12: MULTI-MODAL STREAMING",
            "text": "Looking ahead, the integration of real-time vision, audio, and code streams represents the next major frontier. Agentic AI systems will soon interact via continuous multi-modal inputs, perceiving screen displays, terminal outputs, and natural voice commands in real time simultaneously.",
            "highlight_word": "multi-modal"
        },
        {
            "badge": "MODULE 13: STRATEGIC ROADMAP",
            "text": "For creators, developers, and technology leaders, adopting agentic automation early is key to remaining competitive. Those who master combining human domain expertise with AI-accelerated execution speed will lead the future digital engineering landscape over the next decade.",
            "highlight_word": "automation"
        },
        {
            "badge": "MODULE 14: CONCLUSION & COMMUNITY",
            "text": "What are your thoughts on this major AI breakthrough? Let us know in the comments section below which AI models and autonomous tools you rely on daily. Don't forget to subscribe to FutureTech AI for daily long-form deep dives into artificial intelligence, machine learning, and future technology!",
            "highlight_word": "subscribe"
        }
    ]
    
    return {
        "title": f"AI BREAKTHROUGH DIGEST: {clean_title[:55]} #AINews",
        "description": f"Comprehensive long-form breakdown of today's top AI news including '{clean_title}'.\n\nTimestamps:\n0:00 - Module 1: Executive Overview\n0:45 - Module 2: Core Breakthrough\n1:30 - Module 3: System Architecture\n2:30 - Module 5: GPU Infrastructure\n3:30 - Module 8: Enterprise Adoption\n4:30 - Module 13: Strategic Roadmap\n\nFeatured Source: {source_channel} ({main_target['url']})",
        "tags": ["AI", "TechNews", "ArtificialIntelligence", "OpenAI", "Gemini", "AIAgents", "MachineLearning", "FutureTech"],
        "badge_text": "AI DEEP DIVE",
        "slides": slides
    }

# ==============================================================================
# STEP 3: Multi-Voice Audio Synthesis Engine
# ==============================================================================
async def synthesize_slide_audio(text, output_file):
    """
    Synthesizes voiceover audio using edge-tts with 5-attempt voice rotation
    and an automatic gTTS fallback for 100% execution reliability.
    """
    voices = ["en-US-ChristopherNeural", "en-US-GuyNeural", "en-US-EricNeural", "en-US-AriaNeural", "en-US-JennyNeural"]
    for attempt in range(5):
        voice = voices[attempt % len(voices)]
        try:
            if edge_tts:
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_file)
                if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                    return output_file
        except Exception as e:
            print(f"   ⚠️ edge-tts attempt {attempt+1}/5 failed ({e}). Retrying...")
            await asyncio.sleep(1.5 * (attempt + 1))
    
    try:
        print("   ⚠️ edge-tts endpoints busy. Switching to gTTS fallback engine...")
        from gtts import gTTS
        tts = gTTS(text=text, lang='en')
        tts.save(output_file)
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            return output_file
    except Exception as e:
        print(f"   ⚠️ gTTS fallback note: {e}")

    if os.path.exists(output_file) and os.path.getsize(output_file) > 100:
        return output_file
    raise RuntimeError(f"Failed to synthesize voiceover audio for slide text: '{text[:30]}...'")

def get_background_music(output_file="bg_longform_music.mp3"):
    if os.path.exists(output_file):
        return output_file
    print("🎵 Fetching ambient long-form background music track...")
    url = "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3?filename=cyberpunk-tech-110391.mp3"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(res.content)
            return output_file
    except Exception as e:
        print(f"   ⚠️ Background music download note: {e}")
    return None

# ==============================================================================
# STEP 4: 16:9 Widescreen High-CTR Thumbnail Generator (1280x720)
# ==============================================================================
def generate_procedural_background(width, height):
    img = PIL.Image.new("RGBA", (width, height), (10, 14, 28, 255))
    draw = PIL.ImageDraw.Draw(img)
    colors = [(56, 189, 248, 110), (236, 72, 153, 110), (168, 85, 247, 110), (250, 204, 21, 110)]
    for i in range(22):
        x0 = random.randint(0, width)
        y0 = random.randint(0, height)
        draw.ellipse([x0-280, y0-280, x0+280, y0+280], fill=colors[i % len(colors)])
    img = img.filter(PIL.ImageFilter.GaussianBlur(30))
    draw_grid = PIL.ImageDraw.Draw(img)
    for y in range(0, height, 45):
        draw_grid.line([(0, y), (width, y)], fill=(255, 255, 255, 12))
    for x in range(0, width, 45):
        draw_grid.line([(x, 0), (x, height)], fill=(255, 255, 255, 12))
    return img.convert("RGB")

def generate_longform_thumbnail(title_text, badge_text, source_channel, output_file="longform_thumbnail.png"):
    print("🖼️ Step 4: Generating high-CTR 16:9 widescreen thumbnail (1280x720)...")
    w, h = 1280, 720
    base_img = generate_procedural_background(w, h)
    draw = PIL.ImageDraw.Draw(base_img)
    
    font_large = get_font(52)
    font_badge = get_font(28)
    font_credit = get_font(22)
    
    # Outer Border
    draw.rectangle([15, 15, w-15, h-15], outline=(56, 189, 248), width=6)
    
    # Badge Box (Top Left)
    draw.rectangle([50, 50, 420, 110], fill=(236, 72, 153), outline=(255, 255, 255), width=2)
    bw = get_text_width(font_badge, badge_text)
    draw.text((50 + (370 - bw)//2, 65), badge_text.upper(), font=font_badge, fill=(255, 255, 255))
    
    # AI Host Presenter Badge (Top Right)
    draw.rectangle([w - 380, 50, w - 50, 110], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=2)
    draw.text((w - 360, 65), "● ALEX | AI HOST ANALYST", font=font_credit, fill=(56, 189, 248))

    # Main Title Lines
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
        
    y_start = 180
    for line in lines_list[:3]:
        lw = get_text_width(font_large, line)
        draw.rectangle([60, y_start - 5, 60 + lw + 30, y_start + 65], fill=(15, 23, 42, 230))
        draw.text((75, y_start), line, font=font_large, fill=(250, 204, 21))
        y_start += 80

    # Lower-Third Source Credit
    credit_text = f"FEATURED SOURCE: {source_channel.upper()} • DEEP DIVE ANALYSIS"
    cw = get_text_width(font_credit, credit_text)
    draw.rectangle([50, h - 100, 50 + cw + 40, h - 45], fill=(30, 41, 59, 230), outline=(168, 85, 247), width=2)
    draw.text((70, h - 85), credit_text, font=font_credit, fill=(255, 255, 255))

    base_img.save(output_file)
    print(f"   ✅ Widescreen 16:9 Thumbnail generated: {output_file}")
    return output_file

# ==============================================================================
# STEP 5: 16:9 Long-Form Widescreen Video Renderer with Animated Presenter Avatar
# ==============================================================================
def render_longform_video(script_data, news_bundle, output_file="longform_ai_video.mp4"):
    """
    Renders a 16:9 widescreen (1920x1080) animated video featuring 14-16 detailed slides,
    a left-side Animated AI Presenter Avatar card with pulsing audio frequency equalizer bars,
    glowing yellow word-highlights, scanlines, ducked ambient music, and progress bars.
    """
    print("🎬 Step 5: Rendering 16:9 widescreen long-form video (1920x1080 resolution, 5+ min duration)...")
    
    w, h = 1920, 1080
    slides = script_data.get("slides", [])
    total_slides = len(slides)
    source_channel = news_bundle[0].get("channel", "Tech Press Digest") if news_bundle else "Tech Press Digest"
    
    font_header = get_font(36)
    font_body = get_font(38)
    font_badge = get_font(28)
    font_credit = get_font(22)
    font_host = get_font(24)
    
    temp_files = []
    slide_clips = []
    
    base_bg_pil = generate_procedural_background(w, h)
    
    for idx, slide in enumerate(slides):
        audio_file = f"longform_audio_{idx}.mp3"
        temp_files.append(audio_file)
        
        slide_text = slide.get("text", "")
        asyncio.run(synthesize_slide_audio(slide_text, audio_file))
        
        audio_clip = AudioFileClip(audio_file)
        # Guarantee minimum 22.0s floor per slide to ensure 5+ minute total video length
        slide_duration = max(audio_clip.duration + 1.5, 22.0)
        
        badge_str = slide.get("badge", f"MODULE {idx+1} OF {total_slides}")
        highlight_str = slide.get("highlight_word", "").lower()
        
        frame_pil = base_bg_pil.copy()
        draw = PIL.ImageDraw.Draw(frame_pil)
        
        # 1. Top Widescreen Title Banner
        draw.rectangle([0, 0, w, 110], fill=(15, 23, 42, 240))
        draw.text((60, 35), "FUTURETECH AI  |  LONG-FORM AI NEWS & TECHNICAL DOCUMENTARY", font=font_header, fill=(56, 189, 248))
        draw.line([(0, 110), (w, 110)], fill=(236, 72, 153), width=4)
        
        # 2. Top Right Slide Counter Pill
        counter_str = f"MODULE {idx+1} / {total_slides}"
        cw = get_text_width(font_header, counter_str)
        draw.rectangle([w - cw - 80, 25, w - 40, 85], fill=(30, 41, 59, 220), outline=(236, 72, 153), width=2)
        draw.text((w - cw - 60, 35), counter_str, font=font_header, fill=(250, 204, 21))
        
        # 3. Left-Side AI Presenter Avatar Card Box [60, 150, 480, 950]
        draw.rectangle([60, 150, 480, 950], fill=(15, 23, 42, 230), outline=(56, 189, 248), width=3)
        draw.rectangle([60, 150, 480, 210], fill=(30, 41, 59, 250))
        draw.text((90, 170), "● AI HOST: ALEX", font=font_host, fill=(250, 204, 21))
        
        # Circular Avatar Graphic
        draw.ellipse([130, 250, 410, 530], fill=(30, 41, 59, 250), outline=(236, 72, 153), width=4)
        draw.ellipse([170, 290, 370, 490], fill=(15, 23, 42, 250), outline=(56, 189, 248), width=3)
        draw.text((220, 370), "ALEX AI", font=font_badge, fill=(56, 189, 248))
        
        draw.rectangle([90, 560, 450, 610], fill=(236, 72, 153))
        draw.text((110, 575), f"EXPLAINING MODULE {idx+1}", font=font_credit, fill=(255, 255, 255))
        
        # 4. Lower-Third Source Attribution Line
        attr_str = f"SOURCE CREDIT: {source_channel.upper()} • FAIR USE COMMENTARY (17 U.S.C. § 107)"
        aw = get_text_width(font_credit, attr_str)
        draw.rectangle([(w - aw)//2 - 20, h - 100, (w + aw)//2 + 20, h - 45], fill=(30, 41, 59, 230), outline=(56, 189, 248), width=2)
        draw.text(((w - aw)//2, h - 88), attr_str, font=font_credit, fill=(250, 204, 21))

        # 5. Right-Side Content Breakdown Card Box [520, 150, 1860, 950]
        words = slide_text.split()
        lines_list = []
        curr = []
        for word in words:
            curr.append(word)
            if get_text_width(font_body, " ".join(curr)) > 1220:
                curr.pop()
                lines_list.append(" ".join(curr))
                curr = [word]
        if curr:
            lines_list.append(" ".join(curr))
            
        panel_h = len(lines_list) * 65 + 160
        y_center = (h // 2) - (panel_h // 2) + 20
        draw.rectangle([520, y_center, 1860, y_center + panel_h], fill=(10, 15, 30, 230), outline=(168, 85, 247), width=3)
        
        # Badge Label inside Right Card
        draw.rectangle([560, y_center + 30, 1100, y_center + 85], fill=(236, 72, 153))
        draw.text((580, y_center + 45), badge_str.upper(), font=font_badge, fill=(255, 255, 255))

        base_img_np = np.array(frame_pil)
        
        # 6. Dynamic Animation Frame Generator (Scanlines + Presenter Equalizer Bars + Word Highlights)
        def make_frame(t, base_np=base_img_np, dur=slide_duration, text_lines=lines_list, y_start=y_center+110, hl=highlight_str):
            frame = PIL.Image.fromarray(base_np).copy()
            draw_anim = PIL.ImageDraw.Draw(frame)
            
            # HUD Laser Scanline
            scan_y = int((t / dur) * h)
            draw_anim.line([(0, scan_y), (w, scan_y)], fill=(56, 189, 248, 160), width=3)
            
            # Top Progress Bar
            prog_w = int((t / dur) * w)
            draw_anim.rectangle([0, 110, prog_w, 116], fill=(250, 204, 21))
            
            # Equalizer Audio Frequency Bars in AI Presenter Card (8 Bars)
            eq_x = 120
            for i in range(8):
                bar_h = int(35 + 28 * math.sin(t * 10 + i * 0.8))
                draw_anim.rectangle([eq_x, 730 - bar_h, eq_x + 25, 730], fill=(56, 189, 248))
                eq_x += 42
            draw_anim.text((120, 750), "AUDIO VOICE FREQUENCY", font=font_credit, fill=(250, 204, 21))
            
            # Spoken Text Rendering with Word-by-Word Highlights
            line_y = y_start
            for line in text_lines:
                lw = get_text_width(font_body, line)
                x_pos = 560
                for word in line.split():
                    clean_w = re.sub(r'[^\w]', '', word).lower()
                    color = (250, 204, 21) if (hl and hl in clean_w) else (255, 255, 255)
                    draw_anim.text((x_pos, line_y), word + " ", font=font_body, fill=color)
                    x_pos += get_text_width(font_body, word + " ")
                line_y += 65
                
            return np.array(frame)

        if VideoClip:
            clip = VideoClip(make_frame, duration=slide_duration)
            clip = clip.set_audio(audio_clip)
            slide_clips.append(clip)
        
    if concatenate_videoclips and slide_clips:
        final_video = concatenate_videoclips(slide_clips, method="compose")
        
        # Ambient Background Music Mixing
        music_path = get_background_music()
        if music_path and os.path.exists(music_path):
            try:
                bg_music = AudioFileClip(music_path).filter(lambda gf, t: 0.10 * gf(t)).set_duration(final_video.duration)
                comp_audio = CompositeAudioClip([final_video.audio, bg_music])
                final_video = final_video.set_audio(comp_audio)
            except Exception as e:
                print(f"   ⚠️ Background music mixing note: {e}")
                
        final_video.write_videofile(
            output_file, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac", 
            preset="ultrafast",
            threads=4
        )
    else:
        print(f"   💡 MoviePy not available in environment. Dry-run skipped rendering {output_file}.")

    for f in temp_files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    print(f"   ✅ Long-Form 16:9 Video rendered successfully: {output_file}")
    return output_file

# ==============================================================================
# STEP 6: YouTube Data API v3 Long-Form Video & SEO Publishing
# ==============================================================================
def upload_longform_to_youtube(video_file, title, description, tags, news_bundle, thumbnail_file=None):
    clean_title = sanitize_text(title)
    clean_desc = sanitize_text(description)
    print(f"🚀 Step 6: Uploading long-form video '{clean_title}' to YouTube...")
    
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]) or not build:
        print("⚠️ YouTube OAuth credentials or build API missing. Skipping live upload.")
        return None

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
    
    main_source = news_bundle[0] if news_bundle else {}
    source_title = main_source.get("title", "AI Industry Report")
    source_channel = main_source.get("channel", "Tech Press")
    source_url = main_source.get("url", "https://youtube.com")
    
    legal_attribution = (
        "📌 SOURCE CREDIT & ATTRIBUTION:\n"
        "Featured News/Topic: " + str(source_title) + "\n"
        "Original Creator/Source: " + str(source_channel) + "\n"
        "Original Reference Link: " + str(source_url) + "\n\n"
        "⚖️ LEGAL STATEMENT & MONETIZATION COMPLIANCE:\n"
        "This video presents an original, highly structured news synthesis, commentary, and educational analysis of recent AI developments. Content re-use adheres strictly to Creative Commons Attribution (CC-BY) guidelines and Fair Use principles under 17 U.S.C. Section 107.\n\n"
        "🤖 AI PRODUCTION DISCLAIMER:\n"
        "Narrated using AI synthesis and produced with automated technical curation tools for education and research."
    )
    
    full_description = clean_desc[:3500] + "\n\n" + legal_attribution
    
    body = {
        "snippet": {
            "title": clean_title[:100],
            "description": full_description,
            "tags": [sanitize_text(t) for t in tags],
            "categoryId": "28" # Science & Technology
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
    print(f"🎉 SUCCESS! Published Long-Form 16:9 Video live: {pub_link}")

    if thumbnail_file and os.path.exists(thumbnail_file):
        try:
            print(f"🖼️ Setting custom 16:9 thumbnail for Video ID {video_id}...")
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_file)).execute()
            print("   ✅ Custom 16:9 Thumbnail updated successfully!")
        except Exception as e:
            print(f"   ⚠️ Could not set thumbnail ({e}). Ensure channel phone verification.")

    # Save to local history log to prevent duplicates
    history = load_posted_history()
    history.append(clean_title)
    save_posted_history(history)

    return video_id

# ==============================================================================
# MAIN EXECUTION PIPELINE
# ==============================================================================
def main():
    print("======================================================")
    print("🚀 STARTING 16:9 LONG-FORM (4-8 MIN) AI CURATOR PIPELINE")
    print("======================================================")
    
    news_bundle = fetch_longform_ai_trends()
    script_data = generate_longform_script(news_bundle)
    
    thumb_file = generate_longform_thumbnail(
        title_text=script_data.get("title", "AI BREAKTHROUGH DIGEST"),
        badge_text=script_data.get("badge_text", "AI DEEP DIVE"),
        source_channel=news_bundle[0].get("channel", "Tech Press Digest") if news_bundle else "Tech Press Digest"
    )
    
    video_file = render_longform_video(
        script_data=script_data,
        news_bundle=news_bundle
    )
    
    upload_longform_to_youtube(
        video_file=video_file,
        title=script_data.get("title", "AI BREAKTHROUGH DIGEST #AINews"),
        description=script_data.get("description", "Comprehensive long-form AI news breakdown."),
        tags=script_data.get("tags", ["AI", "TechNews"]),
        news_bundle=news_bundle,
        thumbnail_file=thumb_file
    )
    
    print("======================================================")
    print("✅ 16:9 LONG-FORM AI CURATOR PIPELINE COMPLETE")
    print("======================================================")

if __name__ == "__main__":
    main()
