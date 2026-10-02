# Complete Updated pipeline.py

```python
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
from datetime import datetime

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
    # Strip edition tags like "Ed. #123", "Edition 222", "Ed 99" safely
    clean = re.sub(r'\b(?:Ed|Edition)\.?\s*#?\s*\d+\b', '', str(text), flags=re.IGNORECASE)
    clean = re.sub(r'[^\x00-\x7F]+', '', clean).strip()
    clean = re.sub(r'\s+', ' ', clean)
    return clean

def clean_str(val):
    return str(val or "").strip("<> \"'\t\r\n")

# ==========================================
# STEP 0: Real-Time AI News & Educational Topic Ingestion
# ==========================================
def get_trending_news_and_learning_topic():
    print("📰 Step 0: Scraping real-time AI news and selecting AI Learning topic...")
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
            if feedparser:
                feed = feedparser.parse(url)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")[:300]
                    full_text = f"{title} {summary}".lower()
                    
                    if any(kw in full_text for kw in ai_keywords):
                        clean_title = sanitize_text(title.replace('"', "'").replace("\n", " "))
                        clean_summary = sanitize_text(summary.replace('"', "'").replace("\n", " "))
                        news_items.append({"title": clean_title, "summary": clean_summary})
        except Exception as e:
            print(f"   ⚠️ RSS Feed error ({url}): {e}")

    if not news_items:
        news_items = [{
            "title": "OpenAI Advances Autonomous AI Coding Agents for Enterprise Workflows",
            "summary": "Next-generation neural models automate end-to-end software engineering workflows with extreme reasoning efficiency."
        }]

    selected_item = random.choice(news_items)

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

    print(f"   ✅ Selected News: {selected_item['title'][:70]}...")
    print(f"   🎓 Selected AI Learning Topic: {selected_learning}")
    return selected_item, selected_learning

# ==========================================
# STEP 1: Multi-Provider AI Script Generation Engine
# ==========================================
def generate_triple_scripts():
    print("🧠 Step 1: Generating Short, Long News, and Separate 3-Min AI Learning Masterclass Packages...")
    gemini_key = clean_str(os.environ.get("GEMINI_API_KEY"))
    groq_key = clean_str(os.environ.get("GROQ_API_KEY"))
    openrouter_key = clean_str(os.environ.get("OPENROUTER_API_KEY"))
    news_item, learning_topic = get_trending_news_and_learning_topic()
    news_context = f"Headline: {news_item['title']} | Summary: {news_item['summary']}"
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    prompt = f"""You are an elite YouTube AI content creator specializing in viral AI news and engaging educational AI lessons.
Randomization Seed: {current_time}
News Story: {news_context}
Learning Topic: {learning_topic}

CRITICAL DIRECTIVES:
Generate THREE distinct video content packages:
1. "short": Vertical 9:16 Short DERIVED DIRECTLY from the main AI news story (5 slides, ~45-50s spoken audio, total 100-130 words).
2. "long": Widescreen 16:9 Main AI News Video explaining the latest news in detail (8 slides, ~1.5-2 mins spoken audio, total 250-320 words).
3. "learning": SEPARATE Widescreen 16:9 Educational AI Masterclass Lesson explaining '{learning_topic}' in full depth (12 slides, EXACTLY 3 minutes total spoken audio, each slide containing 3-4 detailed educational sentences, total 480-550 words focusing exclusively on this single topic).

VISUAL PROMPT RULES:
Every slide's "prompt" MUST describe vibrant, animated 3D character visuals and people actively using AI, such as: "3D Pixar-style female software developer interacting with a floating 3D holographic neural network interface, futuristic lab, 8k render". Always include people or 3D animated character scientists using AI in visual prompts!

IMPORTANT:
- Do NOT include any static on-screen subscribe banners, subscribe calls-to-action, or subscribe text in the slide text or narration scripts!
- Every slide's "text" field MUST contain the exact educational narrative to be spoken by TTS voiceover and shown as subtitles on screen.
- Do NOT include edition numbers, run IDs, or 'Ed. #' tags in titles or descriptions!

Return ONLY a valid JSON object with this exact structure:
{{
  "short": {{
    "title": "{news_item['title'][:60]} | #Shorts",
    "description": "Quick breakdown of latest AI news. #Shorts #AINews #Tech",
    "thumb_prompt": "3D animated male tech presenter pointing at glowing holographic AI brain dark technical studio 8k",
    "tags": ["AI News", "Shorts", "Tech", "Artificial Intelligence"],
    "slides": [
      {{"text": "Breaking artificial intelligence developments today: {news_item['title'][:60]}.", "prompt": "3D animated male engineer amazed by glowing cyan neural network 8k", "badge": "BREAKING AI"}},
      {{"text": "Here are the key details from researchers: {news_item['summary'][:150]}.", "prompt": "3D animated character working on holographic terminal floating code", "badge": "NEWS BREAKDOWN"}},
      {{"text": "Tech industry analysts report this breakthrough will significantly accelerate enterprise software automation.", "prompt": "3D female scientist pointing at quantum supercomputer data streams", "badge": "INDUSTRY IMPACT"}},
      {{"text": "As deployment expands globally, researchers highlight key safety benchmarks and performance optimizations.", "prompt": "3D animated developer interacting with floating cybernetic shield", "badge": "SAFETY & CONTROL"}},
      {{"text": "This milestone represents a major leap forward for autonomous artificial intelligence systems worldwide.", "prompt": "3D character standing in front of futuristic neon skyline at night 8k", "badge": "SUMMARY"}}
    ]
  }},
  "long": {{
    "title": "{news_item['title'][:80]} | FutureTech Pulse",
    "description": "Comprehensive deep dive into recent artificial intelligence developments: {news_item['summary']}",
    "thumb_prompt": "3D animated female scientist presenting glowing cyan AI core in high tech lab 8k",
    "tags": ["AI Breakthrough", "Artificial Intelligence", "Tech News", "FutureTech"],
    "slides": [
      {{"text": "Welcome to FutureTech Pulse. Today we are exploring milestone AI developments regarding {news_item['title'][:60]}.", "prompt": "3D animated tech presenter introducing artificial intelligence news in futuristic lab", "badge": "AI DEEP DIVE"}},
      {{"text": "To understand this news story, let us look at the core research summary: {news_item['summary'][:200]}.", "prompt": "3D female scientist analyzing glowing holographic neural nodes network", "badge": "NEWS ANALYSIS"}},
      {{"text": "Leading research laboratories demonstrate that this new architecture dramatically improves execution speed and efficiency.", "prompt": "3D male engineer working with floating digital code matrix in high tech facility", "badge": "SOFTWARE INNOVATION"}},
      {{"text": "In rigorous benchmark evaluations, the neural system surpassed existing industry standards in logical reasoning.", "prompt": "3D animated character examining performance benchmark graphs on holographic display", "badge": "BENCHMARKS"}},
      {{"text": "Major cloud infrastructure providers are already preparing to integrate these models into enterprise workflows.", "prompt": "3D developers collaborating around glowing digital globe floating data streams", "badge": "ENTERPRISE INTEGRATION"}},
      {{"text": "At the same time, security researchers are introducing novel alignment frameworks to ensure reliable operations.", "prompt": "3D cyber security specialist setting up glowing neon shield alignment protocols", "badge": "SAFETY & ALIGNMENT"}},
      {{"text": "Industry experts project that these neural systems will become the primary engine for software within the decade.", "prompt": "3D animated team looking at futuristic smart city skyline at night 8k", "badge": "FUTURE HORIZON"}},
      {{"text": "As neural models continue evolving, autonomous agents will redefine the entire landscape of modern technology.", "prompt": "3D animated presenter looking ahead into glowing cyan digital portal 8k", "badge": "FINAL THOUGHTS"}}
    ]
  }},
  "learning": {{
    "title": "AI EXPLAINED: {learning_topic} (3-Min Masterclass) | FutureTech Pulse",
    "description": "Master {learning_topic} step-by-step in this comprehensive 3-minute educational AI slideshow lesson.",
    "thumb_prompt": "3D animated female professor holding glowing holographic neural diagram masterclass 8k",
    "tags": ["AI Learning", "AI Explained", "Machine Learning", "Tech Tutorial", "FutureTech"],
    "slides": [
      {{"text": "Welcome to FutureTech AI Academy. In this 3-minute masterclass, we are breaking down {learning_topic} step-by-step so you can understand its core architecture.", "prompt": "3D animated female instructor presenting in futuristic holographic classroom 8k", "badge": "LESSON OVERVIEW"}},
      {{"text": "To master this concept, we must first examine how traditional static data processing differs from modern multi-dimensional neural network representations.", "prompt": "3D male software developer comparing traditional code vs glowing neural matrix", "badge": "CORE FOUNDATION"}},
      {{"text": "At the heart of this system lies an encoder mechanism that transforms raw input tokens into mathematical vector embeddings across thousands of dimensions.", "prompt": "3D animated character floating inside 3D vector space surrounded by glowing data nodes", "badge": "VECTOR EMBEDDINGS"}},
      {{"text": "These mathematical vector representations allow the artificial intelligence model to capture complex semantic relationships and contextual meaning instantaneously.", "prompt": "3D female researcher adjusting glowing synaptic connections on holographic board", "badge": "SEMANTIC MATRIX"}},
      {{"text": "Next, multi-head self-attention mechanisms calculate contextual importance weights for every token relative to every other token in the sequence.", "prompt": "3D animated engineer operating multi head attention mechanism with glowing light beams", "badge": "ATTENTION LAYERS"}},
      {{"text": "By computing these attention scores in parallel across dedicated hardware tensor cores, modern neural models scale across hundreds of billions of parameters.", "prompt": "3D character supervising massive supercomputer server cluster with neon light trails", "badge": "PARALLEL COMPUTATION"}},
      {{"text": "During the initial training phase, mathematical loss functions continuously evaluate predictions and guide gradient descent optimization.", "prompt": "3D scientist studying 3D mathematical loss surface graph on holographic table", "badge": "GRADIENT DESCENT"}},
      {{"text": "Backpropagation algorithms then calculate partial derivatives across all layers, adjusting synaptic weights to minimize error iteratively.", "prompt": "3D animated character tracking backpropagation signal rerouting glowing neural nodes", "badge": "WEIGHT UPDATES"}},
      {{"text": "When deployed into production environments, this enables autonomous software agents to reason, plan, and execute multi-step workflows independently.", "prompt": "3D software engineer collaborating alongside autonomous AI hologram agent on workstation", "badge": "REAL WORLD AGENTS"}},
      {{"text": "Understanding these fundamental architectural mechanisms gives you a crucial competitive advantage as generative AI reshapes global industries.", "prompt": "3D animated tech leader holding glowing tablet showing artificial intelligence roadmap", "badge": "STRATEGIC IMPACT"}},
      {{"text": "As neural architectures become increasingly powerful, mastering these concepts will empower you to build the next generation of intelligent software.", "prompt": "3D animated team looking at futuristic digital horizon illuminated by cyan energy 8k", "badge": "MASTERCLASS SUMMARY"}},
      {{"text": "Thank you for joining this FutureTech masterclass. Keep exploring, building, and innovating with the power of artificial intelligence.", "prompt": "3D animated instructor waving goodbye in high tech laboratory background 8k", "badge": "CONCLUSION"}}
    ]
  }}
}}"""

    # --- PROVIDER 1: Gemini API ---
    if gemini_key and genai:
        try:
            client = genai.Client(api_key=gemini_key)
            gemini_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest"]
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
    if groq_key and Groq:
        try:
            print("   [Provider 2] Switching to Groq API...")
            groq_client = Groq(api_key=groq_key)
            groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

            for model in groq_models:
                try:
                    print(f"   Trying Groq model: '{model}'...")
                    completion = groq_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"},
                        max_tokens=3500
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
            openrouter_models = ["google/gemini-2.0-flash-exp:free", "meta-llama/llama-3.3-70b-instruct:free", "deepseek/deepseek-r1:free"]
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

    # --- PROVIDER 4: Dynamic Scraped Procedural Script Generator ---
    print("   ⚠️ Remote AI APIs busy. Generating Dynamic Scraped News Script Package...")
    t_head = news_item['title']
    t_sum = news_item['summary']

    return {
        "short": {
            "title": f"BREAKING: {t_head[:55]} | #Shorts",
            "description": f"Latest AI news update: {t_sum[:200]} #Shorts #AINews #Tech",
            "thumb_prompt": "3D animated tech presenter pointing at glowing holographic AI brain dark technical studio 8k",
            "tags": ["AI News", "Shorts", "Tech", "Artificial Intelligence"],
            "slides": [
                {"text": f"Breaking artificial intelligence developments today: {t_head}.", "prompt": "3D animated male engineer amazed by glowing cyan neural network 8k", "badge": "BREAKING AI"},
                {"text": f"Here are the key details from researchers: {t_sum[:150]}.", "prompt": "3D animated character working on holographic terminal floating code", "badge": "NEWS BREAKDOWN"},
                {"text": "Tech industry analysts report this breakthrough will significantly accelerate enterprise software automation.", "prompt": "3D female scientist pointing at quantum supercomputer data streams", "badge": "INDUSTRY IMPACT"},
                {"text": "As deployment expands globally, researchers highlight key safety benchmarks and performance optimizations.", "prompt": "3D animated developer interacting with floating cybernetic shield", "badge": "SAFETY & CONTROL"},
                {"text": "This milestone represents a major leap forward for autonomous artificial intelligence systems worldwide.", "prompt": "3D character standing in front of futuristic neon skyline at night 8k", "badge": "SUMMARY"}
            ]
        },
        "long": {
            "title": f"INSANE: {t_head[:75]} | FutureTech Pulse",
            "description": f"Comprehensive deep dive into recent artificial intelligence developments: {t_sum}",
            "thumb_prompt": "3D animated female scientist presenting glowing cyan AI core in high tech lab 8k",
            "tags": ["AI Breakthrough", "Artificial Intelligence", "Tech News", "FutureTech"],
            "slides": [
                {"text": f"Welcome to FutureTech Pulse. Today we are exploring milestone AI developments regarding {t_head}.", "prompt": "3D animated tech presenter introducing artificial intelligence news in futuristic lab", "badge": "AI DEEP DIVE"},
                {"text": f"To understand this news story, let us look at the core summary: {t_sum}.", "prompt": "3D female scientist analyzing glowing holographic neural nodes network", "badge": "NEWS ANALYSIS"},
                {"text": "Leading research laboratories demonstrate that this new architecture dramatically improves execution speed and efficiency.", "prompt": "3D male engineer working with floating digital code matrix in high tech facility", "badge": "SOFTWARE INNOVATION"},
                {"text": "In rigorous benchmark evaluations, the neural system surpassed existing industry standards in logical reasoning.", "prompt": "3D animated character examining performance benchmark graphs on holographic display", "badge": "BENCHMARKS"},
                {"text": "Major cloud infrastructure providers are already preparing to integrate these models into enterprise workflows.", "prompt": "3D developers collaborating around glowing digital globe floating data streams", "badge": "ENTERPRISE INTEGRATION"},
                {"text": "At the same time, security researchers are introducing novel alignment frameworks to ensure reliable operations.", "prompt": "3D cyber security specialist setting up glowing neon shield alignment protocols", "badge": "SAFETY & ALIGNMENT"},
                {"text": "Industry experts project that these neural systems will become the primary engine for software within the decade.", "prompt": "3D animated team looking at futuristic smart city skyline at night 8k", "badge": "FUTURE HORIZON"},
                {"text": "As neural models continue evolving, autonomous agents will redefine the entire landscape of modern technology.", "prompt": "3D animated presenter looking ahead into glowing cyan digital portal 8k", "badge": "FINAL THOUGHTS"}
            ]
        },
        "learning": {
            "title": f"AI EXPLAINED: {learning_topic} (3-Min Masterclass) | FutureTech Pulse",
            "description": f"Master the mechanics of {learning_topic} in this comprehensive 3-minute educational AI slideshow lesson.",
            "thumb_prompt": "3D animated female professor holding glowing holographic neural diagram masterclass 8k",
            "tags": ["AI Learning", "AI Explained", "Machine Learning", "Tech Tutorial", "FutureTech"],
            "slides": [
                {"text": f"Welcome to FutureTech AI Academy. In this 3-minute lesson, we are breaking down {learning_topic} step-by-step so you can understand its core architecture.", "prompt": "3D animated female instructor presenting in futuristic holographic classroom 8k", "badge": "LESSON OVERVIEW"},
                {"text": "To master this concept, we must first examine how traditional static data processing differs from modern multi-dimensional neural network representations.", "prompt": "3D male software developer comparing traditional code vs glowing neural matrix", "badge": "CORE FOUNDATION"},
                {"text": "At the heart of this system lies an encoder mechanism that transforms raw input tokens into mathematical vector embeddings across thousands of dimensions.", "prompt": "3D animated character floating inside 3D vector space surrounded by glowing data nodes", "badge": "VECTOR EMBEDDINGS"},
                {"text": "These mathematical vector representations allow the artificial intelligence model to capture complex semantic relationships and contextual meaning instantaneously.", "prompt": "3D female researcher adjusting glowing synaptic connections on holographic board", "badge": "SEMANTIC MATRIX"},
                {"text": "Next, multi-head self-attention mechanisms calculate contextual importance weights for every token relative to every other token in the sequence.", "prompt": "3D animated engineer operating multi head attention mechanism with glowing light beams", "badge": "ATTENTION LAYERS"},
                {"text": "By computing these attention scores in parallel across dedicated hardware tensor cores, modern neural models scale across hundreds of billions of parameters.", "prompt": "3D character supervising massive supercomputer server cluster with neon light trails", "badge": "PARALLEL COMPUTATION"},
                {"text": "During the initial training phase, mathematical loss functions continuously evaluate predictions and guide gradient descent optimization.", "prompt": "3D scientist studying 3D mathematical loss surface graph on holographic table", "badge": "GRADIENT DESCENT"},
                {"text": "Backpropagation algorithms then calculate partial derivatives across all layers, adjusting synaptic weights to minimize error iteratively.", "prompt": "3D animated character tracking backpropagation signal rerouting glowing neural nodes", "badge": "WEIGHT UPDATES"},
                {"text": "When deployed into production environments, this enables autonomous software agents to reason, plan, and execute multi-step workflows independently.", "prompt": "3D software engineer collaborating alongside autonomous AI hologram agent on workstation", "badge": "REAL WORLD AGENTS"},
                {"text": "Understanding these fundamental architectural mechanisms gives you a crucial competitive advantage as generative AI reshapes global industries.", "prompt": "3D animated tech leader holding glowing tablet showing artificial intelligence roadmap", "badge": "STRATEGIC IMPACT"},
                {"text": "As neural architectures become increasingly powerful, mastering these concepts will empower you to build the next generation of intelligent software.", "prompt": "3D animated team looking at futuristic digital horizon illuminated by cyan energy 8k", "badge": "MASTERCLASS SUMMARY"},
                {"text": "Thank you for joining this FutureTech masterclass. Keep exploring, building, and innovating with the power of artificial intelligence.", "prompt": "3D animated instructor waving goodbye in high tech laboratory background 8k", "badge": "CONCLUSION"}
            ]
        }
    }

# ==========================================
# STEP 2: Voiceover Audio Generator
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
        print(f"   ⚠️ Music download note: {e}")
    return None

# Procedural Cyberpunk Dynamic Background Generator
def generate_procedural_background(width, height, prompt="cybertech"):
    img = PIL.Image.new("RGBA", (width, height), (10, 15, 30, 255))
    draw = PIL.ImageDraw.Draw(img)
    colors = [(236, 72, 153, 110), (56, 189, 248, 110), (168, 85, 247, 110), (250, 204, 21, 110)]
    for i in range(16):
        x0 = random.randint(0, width)
        y0 = random.randint(0, height)
        draw.ellipse([x0-250, y0-250, x0+250, y0+250], fill=colors[i % len(colors)])
    img = img.filter(PIL.ImageFilter.GaussianBlur(25))
    draw_grid = PIL.ImageDraw.Draw(img)
    for y in range(0, height, 45):
        draw_grid.line([(0, y), (width, y)], fill=(255, 255, 255, 14))
    for x in range(0, width, 45):
        draw_grid.line([(x, 0), (x, height)], fill=(255, 255, 255, 14))
    return img.convert("RGB")

# ==========================================
# STEP 3: Copyright-Safe Multi-Source High-CTR Catchy Thumbnail Generator
# ==========================================
def generate_thumbnail(title_text, badge_text, visual_prompt, is_short=False, output_file="thumbnail.png"):
    width, height = (1080, 1920) if is_short else (1280, 720)
    print(f"🎨 Generating High-CTR Catchy Thumbnail ({width}x{height}) -> {output_file}...")
    
    clean_visual = sanitize_text(visual_prompt) or "3D animated tech presenter glowing AI brain cyan neon dark 8k"
    seed = random.randint(10000, 999999)

    base_img = None

    # Source 1: Pollinations AI Generation (100% Royalty Free, 3D Character Prompt)
    encoded_prompt = urllib.parse.quote(f"{clean_visual}, 3D Pixar style character animation, vibrant cyberpunk lighting 3d render cinematic quality 8k")
    img_url_pollinations = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}"
    try:
        res = requests.get(img_url_pollinations, timeout=8)
        if res.status_code == 200 and len(res.content) > 5000:
            with open("thumb_bg_temp.png", "wb") as f:
                f.write(res.content)
            base_img = PIL.Image.open("thumb_bg_temp.png").convert("RGBA").resize((width, height))
    except Exception as e:
        print(f"   ⚠️ Pollinations thumbnail note: {e}")

    # Source 2: Unsplash Tech Photo Fallback (License Free)
    if base_img is None:
        try:
            unsplash_url = f"https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w={width}&h={height}&q=80"
            res = requests.get(unsplash_url, timeout=8)
            if res.status_code == 200 and len(res.content) > 5000:
                with open("thumb_bg_temp.png", "wb") as f:
                    f.write(res.content)
                base_img = PIL.Image.open("thumb_bg_temp.png").convert("RGBA").resize((width, height))
        except Exception:
            pass

    # Source 3: Procedural High-Contrast Radial Canvas
    if base_img is None:
        base_img = generate_procedural_background(width, height, clean_visual).convert("RGBA")

    # Apply Translucent Overlay for High Readability
    gradient = PIL.Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = PIL.ImageDraw.Draw(gradient)
    if is_short:
        g_draw.rectangle([(0, 0), (width, 360)], fill=(10, 15, 30, 180))
        g_draw.rectangle([(0, 1050), (width, height)], fill=(10, 15, 30, 190))
    else:
        g_draw.rectangle([(0, 0), (width, 180)], fill=(10, 15, 30, 190))
        g_draw.rectangle([(0, 160), (width, height)], fill=(10, 15, 30, 150))

    base_img = PIL.Image.alpha_composite(base_img, gradient)
    draw = PIL.ImageDraw.Draw(base_img)

    # Outer Neon Glowing Frame
    border_color = (250, 204, 21) if "LESSON" in badge_text.upper() or "MASTERCLASS" in badge_text.upper() else (56, 189, 248)
    draw.rectangle([(16, 16), (width-16, height-16)], outline=border_color, width=10)

    # Crisp System TTF Fonts
    badge_font = get_font(38 if is_short else 44)
    title_font = get_font(56 if is_short else 68)
    cta_font = get_font(34 if is_short else 40)

    clean_badge = sanitize_text(badge_text).upper()
    clean_title = sanitize_text(title_text)

    if is_short:
        # Vertical 9:16 Thumbnail Design
        draw.rectangle([(50, 140), (1030, 260)], fill=(244, 63, 94, 245), outline=(255, 255, 255), width=4)
        draw.text((90, 172), f"HOT: {clean_badge}", fill=(255, 255, 255), font=badge_font)

        # Translucent Glass Box
        draw.rectangle([(50, 1100), (1030, 1740)], fill=(10, 15, 30, 140), outline=border_color, width=6)
        
        words = clean_title.split()
        lines, current_line = [], []
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > 16:
                lines.append(" ".join(current_line[:-1]))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))

        y_off = 1140
        for idx, line in enumerate(lines[:6]):
            safe_line = sanitize_text(line)
            for dx, dy in [(-3,-3), (3,-3), (-3,3), (3,3), (0,4), (0,-4), (4,0), (-4,0)]:
                draw.text((90+dx, y_off+dy), safe_line, fill=(0, 0, 0), font=title_font)
            text_color = (250, 204, 21) if idx % 2 == 0 else (56, 189, 248)
            draw.text((90, y_off), safe_line, fill=text_color, font=title_font)
            y_off += 90

        # Bottom Call to Action Sticker
        draw.rectangle([(50, 1760), (1030, 1860)], fill=(16, 185, 129, 245))
        draw.text((120, 1790), "WATCH NOW | 100% EXPLAINED", fill=(255, 255, 255), font=cta_font)

    else:
        # Widescreen 16:9 Thumbnail Design
        draw.rectangle([(60, 50), (680, 150)], fill=(244, 63, 94, 245), outline=(255, 255, 255), width=4)
        draw.text((90, 75), f"HOT: {clean_badge}", fill=(255, 255, 255), font=badge_font)

        right_badge_text = "3-MIN MASTERCLASS" if "MASTERCLASS" in clean_badge or "LESSON" in clean_badge else "BREAKING REPORT"
        draw.rectangle([(720, 50), (1220, 150)], fill=(147, 51, 234, 245), outline=(255, 255, 255), width=3)
        draw.text((750, 75), right_badge_text, fill=(255, 255, 255), font=badge_font)

        # Translucent Glass Box
        draw.rectangle([(60, 180), (1220, 660)], fill=(10, 15, 30, 130), outline=border_color, width=6)

        words = clean_title.split()
        lines, current_line = [], []
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > 20:
                lines.append(" ".join(current_line[:-1]))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))

        y_off = 210
        for idx, line in enumerate(lines[:5]):
            safe_line = sanitize_text(line)
            for dx, dy in [(-3,-3), (3,-3), (-3,3), (3,3), (0,4), (0,-4), (4,0), (-4,0)]:
                draw.text((90+dx, y_off+dy), safe_line, fill=(0, 0, 0), font=title_font)
            text_color = (250, 204, 21) if idx % 2 == 0 else (255, 255, 255)
            draw.text((90, y_off), safe_line, fill=text_color, font=title_font)
            y_off += 90

    base_img = base_img.convert("RGB")
    base_img.save(output_file)
    print(f"   ✅ High-CTR Catchy Thumbnail created: {output_file}")
    return output_file

# ==========================================
# STEP 4: Motion-Animated Video Engine (Word-by-Word Highlight Captions + Ken Burns Zoom)
# ==========================================
def render_multislide_video(title_text, slides, is_short=True, output_file="video.mp4"):
    width, height = (1080, 1920) if is_short else (1920, 1080)
    prefix = os.path.basename(output_file).replace(".mp4", "")
    print(f"🎬 Rendering Motion-Animated Multi-Slide Video ({width}x{height}) with {len(slides)} scenes -> {output_file}...")

    bg_music_file = get_background_music()
    slide_clips = []
    font_caption = get_font(42 if is_short else 46)
    font_badge = get_font(32 if is_short else 36)

    for idx, slide in enumerate(slides):
        slide_text = sanitize_text(slide.get("text", ""))
        slide_prompt = sanitize_text(slide.get("prompt", "3D animated female software engineer glowing AI laboratory dark"))
        slide_badge = sanitize_text(slide.get("badge", "FUTURETECH AI"))

        # 1. Synthesize voiceover audio for this slide
        audio_path = f"voice_{prefix}_slide_{idx}.mp3"
        asyncio.run(synthesize_slide_audio(slide_text, audio_path))
        
        slide_audio = AudioFileClip(audio_path)
        slide_dur = max(slide_audio.duration, 2.2)
        print(f"   Slide {idx+1}/{len(slides)}: Duration = {slide_dur:.2f}s | Badge = '{slide_badge}'")

        # 2. Copyright-Safe 3D Animated Image Fetcher (Pollinations AI / Procedural)
        seed = random.randint(10000, 999999)
        encoded_prompt = urllib.parse.quote(f"{slide_prompt}, 3D Pixar style character animation, people using AI, vibrant cyberpunk lighting 3d render cinematic quality 8k")
        img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}"
        img_path = f"slide_{prefix}_{idx}.png"

        base_img = None
        try:
            res = requests.get(img_url, timeout=8)
            if res.status_code == 200 and len(res.content) > 5000:
                with open(img_path, "wb") as f:
                    f.write(res.content)
                base_img = PIL.Image.open(img_path).convert("RGB").resize((width, height))
        except Exception:
            pass

        if base_img is None:
            base_img = generate_procedural_background(width, height, slide_prompt)

        base_img.save(img_path)

        # 3. Dynamic Motion Frame Generator with Word-by-Word Highlight Captions (No Static Subscribe Banners)
        words = slide_text.split()
        max_chars_per_line = 22 if is_short else 45
        lines = []
        curr_line = []
        for word in words:
            curr_line.append(word)
            if len(" ".join(curr_line)) > max_chars_per_line:
                lines.append(curr_line[:-1])
                curr_line = [word]
        if curr_line:
            lines.append(curr_line)

        def make_animated_frame(t, base_pil=base_img, dur=slide_dur, w=width, h=height, badge=slide_badge):
            progress = min(t / max(dur, 0.1), 1.0)
            
            # Ken Burns Continuous Motion Zoom & Pan
            scale = 1.0 + 0.18 * progress
            w_scaled, h_scaled = int(w * scale), int(h * scale)
            resized = base_pil.resize((w_scaled, h_scaled), PIL.Image.LANCZOS)
            
            crop_x = int(((w_scaled - w) // 2) + (30 * progress))
            crop_y = int(((h_scaled - h) // 2) + (20 * progress))
            cropped = resized.crop((crop_x, crop_y, crop_x + w, crop_y + h)).convert("RGBA")

            # Draw Overlays
            overlay = PIL.Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = PIL.ImageDraw.Draw(overlay)

            # Animated HUD Laser Scanline
            scan_y = int((t * 220) % h)
            draw.line([(0, scan_y), (w, scan_y)], fill=(56, 189, 248, 90), width=3)

            if is_short:
                # Top Badge
                draw.rectangle([(80, 140), (1000, 230)], fill=(30, 41, 59, 235), outline=(56, 189, 248), width=3)
                draw.text((120, 168), badge[:30].upper(), fill=(56, 189, 248), font=font_badge)

                # AI Content Disclaimer Badge
                draw.rectangle([(620, 60), (1000, 120)], fill=(15, 23, 42, 220), outline=(244, 63, 94), width=2)
                draw.text((640, 80), "[AI-GENERATED MEDIA]", fill=(244, 63, 94), font=get_font(24))

                # Subtitle Container for Spoken Text
                draw.rectangle([(60, 1240), (1020, 1780)], fill=(10, 15, 30, 220), outline=(56, 189, 248), width=3)

                # Word-by-Word Subtitle Highlight Animation
                total_words = max(len(words), 1)
                active_word_idx = int(progress * total_words)

                y_start = 1270
                word_counter = 0
                for line_words in lines[:8]:
                    x = 90
                    for w_text in line_words:
                        text_color = (250, 204, 21) if word_counter <= active_word_idx else (200, 215, 235)
                        draw.text((x, y_start), w_text + " ", fill=text_color, font=font_caption)
                        x += get_text_width(font_caption, w_text + " ")
                        word_counter += 1
                    y_start += 58

            else: # Widescreen 16:9
                # Top Badge
                draw.rectangle([(100, 50), (750, 120)], fill=(30, 41, 59, 235), outline=(56, 189, 248), width=2)
                draw.text((130, 72), f"FUTURETECH AI | {badge[:25].upper()}", fill=(56, 189, 248), font=font_badge)

                # AI Content Disclaimer Badge
                draw.rectangle([(1400, 50), (1820, 110)], fill=(15, 23, 42, 220), outline=(244, 63, 94), width=2)
                draw.text((1430, 70), "[AI-GENERATED CONTENT]", fill=(244, 63, 94), font=get_font(26))

                # Subtitle Container for Spoken Text
                draw.rectangle([(100, 720), (1820, 1020)], fill=(10, 15, 30, 220), outline=(56, 189, 248), width=3)

                # Word-by-Word Subtitle Highlight Animation
                total_words = max(len(words), 1)
                active_word_idx = int(progress * total_words)

                y_start = 745
                word_counter = 0
                for line_words in lines[:5]:
                    x = 130
                    for w_text in line_words:
                        text_color = (250, 204, 21) if word_counter <= active_word_idx else (220, 230, 245)
                        draw.text((x, y_start), w_text + " ", fill=text_color, font=font_caption)
                        x += get_text_width(font_caption, w_text + " ")
                        word_counter += 1
                    y_start += 52

            # Bottom Moving Progress Bar
            bar_y = h - 20 if is_short else h - 14
            draw.rectangle([(0, bar_y), (int(w * progress), bar_y + 14)], fill=(56, 189, 248))

            final_frame = PIL.Image.alpha_composite(cropped, overlay).convert("RGB")
            return np.array(final_frame)

        scene_clip = VideoClip(make_animated_frame, duration=slide_dur)
        scene_clip = scene_clip.set_audio(slide_audio)
        slide_clips.append(scene_clip)

    # 4. Concatenate all synchronized motion slide clips
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
    print(f"   ✅ Motion-Animated Video rendered: {output_file}")
    return output_file

# ==========================================
# STEP 5: YouTube API Uploader
# ==========================================
def upload_to_youtube(video_file, title, description, tags, thumbnail_file=None):
    clean_title = sanitize_text(title)
    clean_desc = sanitize_text(description)
    print(f"🚀 Uploading {video_file} to YouTube | Title: '{clean_title}'...")
    
    client_id = clean_str(os.environ.get("YOUTUBE_CLIENT_ID"))
    client_secret = clean_str(os.environ.get("YOUTUBE_CLIENT_SECRET"))
    refresh_token = clean_str(os.environ.get("YOUTUBE_REFRESH_TOKEN"))
    token_uri = clean_str("https://oauth2.googleapis.com/token")
    
    if not all([client_id, client_secret, refresh_token]):
        print("⚠️ YouTube OAuth credentials not fully set in environment. Skipping live upload step.")
        return None

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret
    )
    creds.refresh(Request())
    
    youtube = build("youtube", "v3", credentials=creds)
    
    full_description = f"{clean_desc[:4500]}\n\n🤖 AI CONTENT DISCLAIMER: This video features AI-synthesized narration, script analysis, and visual graphics generated for automated tech news reporting and education."

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
    
    try:
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"   Upload Progress: {int(status.progress() * 100)}%")
                
        video_id = response.get("id")
        print(f"🎉 SUCCESS! Published live to YouTube: https://youtu.be/{video_id}")

        if thumbnail_file and os.path.exists(thumbnail_file):
            try:
                print(f"🖼️ Setting custom thumbnail for Video ID {video_id}...")
                youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_file)).execute()
                print("   ✅ Custom thumbnail published successfully!")
            except Exception as e:
                print(f"   ⚠️ Could not set thumbnail ({e}). Ensure channel is phone-verified.")

        return video_id

    except HttpError as e:
        if "uploadLimitExceeded" in str(e):
            print("⚠️ YOUTUBE DAILY UPLOAD LIMIT REACHED: Uploads paused for 24 hours.")
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
    
    # 1. Render & Upload Short Video (9:16 Vertical, derived from Main News)
    print("\n--- 1. GENERATING YOUTUBE SHORT VIDEO (9:16 VERTICAL) ---")
    short_data = pkg["short"]
    short_slides = short_data.get("slides", [])
    
    thumb_short = generate_thumbnail(
        short_data["title"], 
        "BREAKING SHORTS", 
        short_data.get("thumb_prompt", "3D animated tech presenter glowing AI brain cyan neon dark 8k"), 
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
    
    # 2. Render & Upload Main AI News Video (16:9 Widescreen)
    print("\n--- 2. GENERATING MAIN AI NEWS VIDEO (16:9 WIDESCREEN) ---")
    long_data = pkg["long"]
    long_slides = long_data.get("slides", [])
    
    thumb_long = generate_thumbnail(
        long_data["title"], 
        "AI BREAKTHROUGH", 
        long_data.get("thumb_prompt", "3D animated female scientist presenting glowing cyan AI core in high tech lab 8k"), 
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

    # 3. Render & Upload Separate AI Learning Masterclass Video (16:9 Widescreen, 3 Mins)
    print("\n--- 3. GENERATING SEPARATE AI LEARNING MASTERCLASS (16:9 WIDESCREEN, 3 MINS) ---")
    learning_data = pkg["learning"]
    learning_slides = learning_data.get("slides", [])
    
    thumb_learning = generate_thumbnail(
        learning_data["title"], 
        "AI MASTERCLASS", 
        learning_data.get("thumb_prompt", "3D animated female professor holding glowing holographic neural diagram masterclass 8k"), 
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
```

