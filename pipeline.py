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
import PIL.ImageFilter
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
from googleapiclient.errors import HttpError

# Helper function to sanitize text strictly for PIL font rendering (ASCII only, no emojis)
def sanitize_text(text):
    if not text:
        return ""
    clean = re.sub(r'[^\x00-\x7F]+', '', str(text)).strip()
    return clean

# ==========================================
# STEP 0: Strictly AI & Tech News & Learning Topics Ingestion
# ==========================================
def get_trending_news_and_learning_topic():
    print("📰 Step 0: Scraping AI news and selecting AI Learning topic...")
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

    selected_news = random.choice(news_items) if news_items else "Headline: OpenAI Advances Autonomous AI Coding Agents | Summary: Next-generation neural models automate end-to-end software engineering workflows."

    learning_topics = [
        "How Transformer Neural Networks Work (Self-Attention & Tokens)",
        "Understanding Agentic AI & Autonomous Decision Loops",
        "Large Language Models (LLMs) Explained Simply: Training to Inference",
        "Retrieval-Augmented Generation (RAG) Architecture Masterclass",
        "Diffusion Models & Generative AI Image Synthesis Step-by-Step",
        "Neural Network Backpropagation & Weights Optimization Simplified",
        "AI Vector Databases & Embeddings Concept Guide"
    ]
    selected_learning = random.choice(learning_topics)

    print(f"   ✅ Selected News Context: {selected_news[:80]}...")
    print(f"   🎓 Selected AI Learning Topic: {selected_learning}")
    return selected_news, selected_learning

# ==========================================
# STEP 1: Multi-Provider AI Engine (Short, Long News, AI Learning)
# ==========================================
def generate_triple_scripts():
    print("🧠 Step 1: Generating Short, Long News, and 2-3 Min AI Learning Video Packages...")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    news_context, learning_topic = get_trending_news_and_learning_topic()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    prompt = f"""You are an elite YouTube AI content creator specializing in viral AI news and engaging educational AI lessons.
Randomization Seed: {current_time}
News Context: {news_context}
Learning Topic: {learning_topic}

CRITICAL DIRECTIVES:
Generate THREE distinct video content packages:
1. "short": Vertical 9:16 Short (5 slides, ~45s spoken audio, total 90-120 words).
2. "long": Widescreen 16:9 News Video (8 slides, ~1.5-2 mins spoken audio, total 250-300 words).
3. "learning": Widescreen 16:9 Educational AI Slideshow (10-12 slides, ~2.5-3 mins spoken audio, total 350-450 words explaining the concept step-by-step).

Return ONLY a valid JSON object with this exact structure:
{{
  "short": {{
    "title": "INSANE AI Breakthrough Unveiled! | #Shorts",
    "description": "Quick breakdown of latest AI news. #Shorts #AINews #Tech",
    "thumb_prompt": "cybernetic humanoid robot head glowing cyan neon dark technical background 8k",
    "tags": ["AI News", "Shorts", "Tech", "Artificial Intelligence"],
    "slides": [
      {{"text": "Slide 1 sentence...", "prompt": "visual prompt 1", "badge": "BREAKING AI"}},
      {{"text": "Slide 2 sentence...", "prompt": "visual prompt 2", "badge": "NEURAL AGENTS"}},
      {{"text": "Slide 3 sentence...", "prompt": "visual prompt 3", "badge": "INDUSTRY IMPACT"}},
      {{"text": "Slide 4 sentence...", "prompt": "visual prompt 4", "badge": "FUTURE OUTLOOK"}},
      {{"text": "Subscribe to FutureTech Pulse right now for daily breaking AI news!", "prompt": "futuristic neon subscribe button circuit background", "badge": "SUBSCRIBE NOW"}}
    ]
  }},
  "long": {{
    "title": "MUST SEE: Next-Gen AI Architecture Shocks Tech Industry | FutureTech Pulse",
    "description": "Comprehensive deep dive into recent artificial intelligence developments.",
    "thumb_prompt": "supercomputer matrix glowing blue circuits cybernetic AI core 8k render",
    "tags": ["AI Breakthrough", "Artificial Intelligence", "Tech News", "FutureTech"],
    "slides": [
      {{"text": "Slide 1 sentence...", "prompt": "visual prompt 1", "badge": "AI DEEP DIVE"}},
      {{"text": "Slide 2 sentence...", "prompt": "visual prompt 2", "badge": "NEURAL TECH"}},
      {{"text": "Slide 3 sentence...", "prompt": "visual prompt 3", "badge": "INNOVATION"}},
      {{"text": "Slide 4 sentence...", "prompt": "visual prompt 4", "badge": "BENCHMARKS"}},
      {{"text": "Slide 5 sentence...", "prompt": "visual prompt 5", "badge": "INTEGRATION"}},
      {{"text": "Slide 6 sentence...", "prompt": "visual prompt 6", "badge": "ALIGNMENT"}},
      {{"text": "Slide 7 sentence...", "prompt": "visual prompt 7", "badge": "FUTURE HORIZON"}},
      {{"text": "Make sure to subscribe to FutureTech Pulse for daily comprehensive AI coverage!", "prompt": "futuristic neon subscribe banner cyan dark", "badge": "SUBSCRIBE FOR MORE"}}
    ]
  }},
  "learning": {{
    "title": "AI EXPLAINED: {learning_topic} (2-Minute Masterclass) | FutureTech Pulse",
    "description": "Learn {learning_topic} step-by-step in this 2-3 minute educational AI slideshow lesson.",
    "thumb_prompt": "glowing holographic neural network diagram learning class technical 8k render",
    "tags": ["AI Learning", "AI Explained", "Machine Learning", "Tech Tutorial", "FutureTech"],
    "slides": [
      {{"text": "Welcome to FutureTech AI Academy. Today we are breaking down {learning_topic} step-by-step.", "prompt": "futuristic holographic academy classroom glowing neural diagram 8k", "badge": "LESSON OVERVIEW"}},
      {{"text": "To understand this concept, we first look at how traditional data processing differs from modern neural representations.", "prompt": "data flow matrix comparison traditional vs neural networks cyan", "badge": "CORE CONCEPT"}},
      {{"text": "At the core of this system lies an architecture designed to transform raw input tokens into mathematical vector embeddings.", "prompt": "vector embeddings space 3d spatial data nodes glowing blue", "badge": "VECTOR EMBEDDINGS"}},
      {{"text": "These mathematical vectors allow the neural model to capture contextual relationships and semantic meaning instantaneously.", "prompt": "synaptic neural connections firing glowing nodes network", "badge": "CONTEXTUAL LOGIC"}},
      {{"text": "Next, multi-head attention mechanisms weigh the importance of every token relative to every other token in the sequence.", "prompt": "multi head attention mechanism visualization glowing beams", "badge": "ATTENTION LAYERS"}},
      {{"text": "This parallel computation allows the model to scale efficiently across billions of parameters without losing context.", "prompt": "supercomputer parallel processing GPU cluster neon trails", "badge": "PARALLEL SCALING"}},
      {{"text": "During the training phase, backpropagation continually adjusts synaptic weights to minimize loss and optimize predictions.", "prompt": "gradient descent mathematical surface optimization 3d graph", "badge": "WEIGHT OPTIMIZATION"}},
      {{"text": "In practical applications, this enables autonomous AI agents to reason, plan, and execute complex workflows seamlessly.", "prompt": "autonomous AI software agent working on holographic dashboard", "badge": "REAL WORLD AGENTS"}},
      {{"text": "Understanding these core principles gives you a massive advantage as generative AI transforms software engineering globally.", "prompt": "futuristic software developer collaborating with AI hologram", "badge": "STRATEGIC IMPACT"}},
      {{"text": "Subscribe to FutureTech Pulse for daily 2-minute AI learning lessons and breaking technology masterclasses!", "prompt": "futuristic neon academy subscribe button glowing circuit", "badge": "SUBSCRIBE FOR LESSONS"}}
    ]
  }}
}}"""

    # --- PROVIDER 1: Gemini API ---
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            gemini_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
            for g_model in gemini_models:
                try:
                    print(f"   [Provider 1] Gemini API trying model '{g_model}'...")
                    response = client.models.generate_content(
                        model=g_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    content = json.loads(response.text.strip())
                    if isinstance(content, dict) and "short" in content and "long" in content and "learning" in content:
                        print(f"   ✅ Gemini ({g_model}) success!")
                        return content
                except Exception as e:
                    print(f"   ⚠️ Gemini model '{g_model}' note: {e}")
                    time.sleep(1)
        except Exception as e:
            print(f"   ⚠️ Gemini client error: {e}")

    # --- PROVIDER 2: Groq API ---
    if groq_key:
        try:
            print("   [Provider 2] Switching to Groq API...")
            groq_client = Groq(api_key=groq_key)
            groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]

            for model in groq_models:
                try:
                    print(f"   Trying Groq model: '{model}'...")
                    completion = groq_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"},
                        max_tokens=2500
                    )
                    raw_text = completion.choices.message.content.strip()
                    content = json.loads(raw_text)
                    if isinstance(content, dict) and "short" in content and "long" in content and "learning" in content:
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
                        if isinstance(content, dict) and "short" in content and "long" in content and "learning" in content:
                            print(f"   ✅ OpenRouter ({model}) success!")
                            return content
                except Exception:
                    pass
        except Exception as e:
            print(f"   ⚠️ OpenRouter API error: {e}")

    # --- PROVIDER 4: Procedural Fallback Engine ---
    print("   ⚠️ All remote AI providers busy. Generating Procedural Triple Script Package...")
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
            "thumb_prompt": "quantum supercomputing server matrix glowing cyan AI brain 8k render",
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
        },
        "learning": {
            "title": f"AI EXPLAINED: How Autonomous Agentic Neural Loops Work | FutureTech Pulse (Ed. #{run_id})",
            "description": f"Master the mechanics of Agentic AI and Neural Decision Loops in this 2-3 minute educational slideshow lesson.",
            "thumb_prompt": "glowing holographic AI agent brain learning diagram masterclass cyan neon 8k",
            "tags": ["AI Learning", "AI Explained", "Machine Learning", "Tech Tutorial", "FutureTech"],
            "slides": [
                {"text": "Welcome to FutureTech AI Academy. Today we are exploring the architecture behind autonomous agentic neural loops.", "prompt": "futuristic holographic academy classroom glowing neural diagram 8k", "badge": "LESSON OVERVIEW"},
                {"text": "Unlike static models that answer prompts passively, agentic systems operate in continuous perception and action cycles.", "prompt": "continuous decision loop flowchart glowing neon cyan data streams", "badge": "AGENTIC LOOPS"},
                {"text": "The cycle begins when an incoming goal is decomposed into discrete, executable sub-tasks by a planning model.", "prompt": "sub task decomposition tree diagram glowing nodes network", "badge": "GOAL PLANNING"},
                {"text": "Next, the agent queries memory stores, retrieving relevant context through vector semantic embeddings.", "prompt": "vector embeddings space 3d spatial data nodes glowing blue", "badge": "VECTOR MEMORY"},
                {"text": "Tool calling frameworks then allow the AI to interact directly with software environments and APIs.", "prompt": "digital API interaction nodes connecting software applications", "badge": "TOOL INTEGRATION"},
                {"text": "After executing an action, the system evaluates environmental feedback to assess task completion accuracy.", "prompt": "real time feedback control loop glowing green indicator lines", "badge": "EVALUATION LOOP"},
                {"text": "If errors occur, self-reflection mechanisms prompt the model to modify its approach and attempt self-correction.", "prompt": "self correcting neural network node rerouting data streams", "badge": "SELF CORRECTION"},
                {"text": "This continuous feedback loop allows autonomous agents to complete complex software engineering tasks independently.", "prompt": "autonomous AI software agent working on holographic dashboard", "badge": "AUTONOMOUS WORKFLOWS"},
                {"text": "Understanding these architectural foundations gives you a crucial strategic edge in modern AI development.", "prompt": "futuristic software engineer collaborating with AI hologram", "badge": "STRATEGIC IMPACT"},
                {"text": "Subscribe to FutureTech Pulse for daily 2-minute AI learning slideshows and technology masterclasses!", "prompt": "futuristic neon academy subscribe button glowing circuit", "badge": "SUBSCRIBE FOR LESSONS"}
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
# STEP 3: Multi-Source High-CTR Catchy Thumbnail Generator
# ==========================================
def generate_thumbnail(title_text, badge_text, visual_prompt, is_short=False, output_file="thumbnail.png"):
    width, height = (1080, 1920) if is_short else (1280, 720)
    print(f"🎨 Generating High-CTR Catchy Thumbnail ({width}x{height}) -> {output_file}...")
    
    clean_visual = sanitize_text(visual_prompt) if visual_prompt else "futuristic AI brain cybernetic neon dark 8k"
    seed = random.randint(10000, 999999)

    base_img = None

    # Source 1: Pollinations AI Generation
    encoded_prompt = urllib.parse.quote(f"{clean_visual}, vibrant cyberpunk lighting high contrast 8k render")
    img_url_pollinations = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}"
    try:
        res = requests.get(img_url_pollinations, timeout=8)
        if res.status_code == 200 and len(res.content) > 5000:
            with open("thumb_bg_temp.png", "wb") as f:
                f.write(res.content)
            base_img = PIL.Image.open("thumb_bg_temp.png").convert("RGBA").resize((width, height))
    except Exception as e:
        print(f"   ⚠️ Pollinations thumbnail note: {e}")

    # Source 2: Unsplash High-Res Tech Photography Fallback
    if base_img is None:
        try:
            unsplash_url = f"https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w={width}&h={height}&q=80"
            res = requests.get(unsplash_url, timeout=8)
            if res.status_code == 200:
                with open("thumb_bg_temp.png", "wb") as f:
                    f.write(res.content)
                base_img = PIL.Image.open("thumb_bg_temp.png").convert("RGBA").resize((width, height))
        except Exception:
            pass

    # Source 3: Procedural High-Contrast Radial Cyber-Grid Canvas (Guaranteed Non-Static)
    if base_img is None:
        base_img = PIL.Image.new("RGBA", (width, height), (10, 15, 30, 255))
        draw_proc = PIL.ImageDraw.Draw(base_img)
        center_x, center_y = width // 2, height // 2
        colors = [(236, 72, 153, 90), (56, 189, 248, 90), (168, 85, 247, 90), (250, 204, 21, 90)]
        for i in range(16):
            angle = (i / 16) * 2 * np.pi
            end_x = int(center_x + width * np.cos(angle))
            end_y = int(center_y + height * np.sin(angle))
            draw_proc.line([(center_x, center_y), (end_x, end_y)], fill=colors[i % len(colors)], width=45)

    # Apply Dark Vignette Gradient Overlay for readability
    gradient = PIL.Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = PIL.ImageDraw.Draw(gradient)
    if is_short:
        g_draw.rectangle([(0, 0), (width, 360)], fill=(15, 23, 42, 215))
        g_draw.rectangle([(0, 1100), (width, height)], fill=(15, 23, 42, 235))
    else:
        g_draw.rectangle([(0, 0), (width, 210)], fill=(15, 23, 42, 225))
        g_draw.rectangle([(0, 180), (width, height)], fill=(15, 23, 42, 210))

    base_img = PIL.Image.alpha_composite(base_img, gradient)
    draw = PIL.ImageDraw.Draw(base_img)

    # Outer Neon Glowing Frame
    border_color = (250, 204, 21) if "LEARN" in badge_text.upper() or "EXPLAINED" in title_text.upper() else (56, 189, 248)
    draw.rectangle([(16, 16), (width-16, height-16)], outline=border_color, width=8)

    clean_badge = sanitize_text(badge_text).upper()
    clean_title = sanitize_text(title_text)

    if is_short:
        # Vertical 9:16 Thumbnail Design
        # 1. Top High-CTR Badge Sticker
        draw.rectangle([(50, 140), (1030, 260)], fill=(244, 63, 94, 245), outline=(255, 255, 255), width=3)
        draw.text((90, 175), f"HOT: {clean_badge}", fill=(255, 255, 255))

        # 2. Lower Main Title Box with High-Contrast Yellow/Cyan Text
        draw.rectangle([(50, 1150), (1030, 1750)], fill=(15, 23, 42, 240), outline=border_color, width=5)
        
        words = clean_title.split()
        lines, current_line = [], []
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > 18:
                lines.append(" ".join(current_line[:-1]))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))

        y_off = 1190
        for idx, line in enumerate(lines[:6]):
            safe_line = sanitize_text(line)
            draw.text((93, y_off+3), safe_line, fill=(0, 0, 0)) # Drop shadow
            text_color = (250, 204, 21) if idx % 2 == 0 else (56, 189, 248)
            draw.text((90, y_off), safe_line, fill=text_color)
            y_off += 70

        # Bottom Call to Action Sticker
        draw.rectangle([(50, 1770), (1030, 1860)], fill=(16, 185, 129, 245))
        draw.text((140, 1795), "WATCH NOW | 100% EXPLAINED", fill=(255, 255, 255))

    else:
        # Widescreen 16:9 Thumbnail Design
        # 1. Top Left Badge Sticker
        badge_bg = (244, 63, 94, 245) if "HOT" in clean_badge or "BREAKTHROUGH" in clean_badge else (147, 51, 234, 245)
        draw.rectangle([(60, 60), (700, 150)], fill=badge_bg, outline=(255, 255, 255), width=3)
        draw.text((90, 85), f"HOT: {clean_badge}", fill=(255, 255, 255))

        # 2. Large Main Headline Box
        draw.rectangle([(60, 180), (1220, 620)], fill=(15, 23, 42, 235), outline=border_color, width=5)

        words = clean_title.split()
        lines, current_line = [], []
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > 28:
                lines.append(" ".join(current_line[:-1]))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))

        y_off = 210
        for idx, line in enumerate(lines[:5]):
            safe_line = sanitize_text(line)
            draw.text((94, y_off+4), safe_line, fill=(0, 0, 0)) # Drop shadow
            text_color = (250, 204, 21) if idx % 2 == 0 else (255, 255, 255)
            draw.text((90, y_off), safe_line, fill=text_color)
            y_off += 75

        # Bottom Right Floating Sticker
        draw.rectangle([(750, 60), (1220, 150)], fill=(16, 185, 129, 245), outline=(255, 255, 255), width=2)
        draw.text((780, 85), "NEW 2026 LESSON", fill=(255, 255, 255))

    base_img = base_img.convert("RGB")
    base_img.save(output_file)
    print(f"   ✅ High-CTR Catchy Thumbnail created: {output_file}")
    return output_file

# ==========================================
# STEP 4: Per-Slide Synchronized Motion Video Engine with AI Disclaimer
# ==========================================
def render_multislide_video(title_text, slides, is_short=True, output_file="video.mp4"):
    width, height = (1080, 1920) if is_short else (1920, 1080)
    prefix = os.path.basename(output_file).replace(".mp4", "")
    print(f"🎬 Rendering Synchronized Multi-Slide Video ({width}x{height}) with {len(slides)} scenes -> {output_file}...")

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
        slide_dur = max(slide_audio.duration, 2.2)
        print(f"   Slide {idx+1}/{len(slides)}: Duration = {slide_dur:.2f}s | Badge = '{slide_badge}'")

        # 2. Fetch unique background image for this slide with cache-busting seed
        seed = random.randint(10000, 999999)
        encoded_prompt = urllib.parse.quote(f"{slide_prompt}, dark cyber aesthetic 8k high quality render")
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
# STEP 5: YouTube API Uploader with Graceful Limit Handling
# ==========================================
def upload_to_youtube(video_file, title, description, tags, thumbnail_file=None):
    print(f"🚀 Uploading {video_file} to YouTube...")
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        print("⚠️ YouTube OAuth credentials not fully set in environment. Skipping live upload step.")
        return None

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
    full_description = f"{sanitize_text(description)[:4500]}\n\n🤖 AI CONTENT DISCLAIMER: This video features AI-synthesized narration, script analysis, and visual graphics generated for automated tech news reporting and education."

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
    
    try:
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
                print(f"🖼️️ Setting custom thumbnail for Video ID {video_id}...")
                youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_file)).execute()
                print("   ✅ Custom thumbnail published successfully!")
            except Exception as e:
                print(f"   ⚠️ Could not set thumbnail ({e}). Ensure YouTube channel is phone-verified for custom thumbnails.")

        return video_id

    except HttpError as e:
        if "uploadLimitExceeded" in str(e):
            print("⚠️ YOUTUBE DAILY UPLOAD LIMIT REACHED: YouTube restricts new/automated channels to a limited number of uploads per 24 hours.")
            print("   Your video was generated and rendered successfully, but YouTube paused uploads for today.")
            print("   The daily upload limit will reset automatically in 24 hours!")
        else:
            print(f"⚠️ YouTube API Error ({e.resp.status}): {e}")
        return None
    except Exception as e:
        print(f"⚠️ Upload Exception: {e}")
        return None

# ==========================================
# MAIN EXECUTION ROUTINE
# ==========================================
if __name__ == "__main__":
    pkg = generate_triple_scripts()
    
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
    
    # 2. Render & Upload Long News Video (16:9 Widescreen)
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

    # 3. Render & Upload AI Learning Video (16:9 Widescreen, 2-3 Mins Slideshow)
    learning_data = pkg["learning"]
    learning_slides = learning_data.get("slides", [])
    
    thumb_learning = generate_thumbnail(
        learning_data["title"], 
        "AI LESSON EXPLAINED", 
        learning_data.get("thumb_prompt", "glowing holographic AI neural diagram classroom masterclass"), 
        is_short=False, 
        output_file="thumb_learning.png"
    )
    
    learning_file = render_multislide_video(
        learning_data["title"], 
        learning_slides, 
        is_short=False, 
        output_file="learning_video.mp4"
    )
    upload_to_youtube(learning_file, learning_data["title"], learning_data["description"], learning_data["tags"], thumbnail_file=thumb_learning)
