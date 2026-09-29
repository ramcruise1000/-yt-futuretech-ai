import os
import json
import time
import random
import asyncio
import requests
from datetime import datetime
from google import genai
from google.genai import types
from groq import Groq
from PIL import Image, ImageDraw
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# ==========================================
# STEP 1: AI Script Generation (Unique Topic Rotation & Failover)
# ==========================================
def generate_script():
    print("🧠 Step 1: Requesting unique educational script from AI...")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")

    # Rotate through distinct sub-topics so every video is 100% unique
    niches = [
        "Humanoid Robotics & Boston Dynamics",
        "AI in Space Exploration & NASA",
        "Autonomous AI Coding Agents & Developer Tools",
        "Quantum Computing & AI Synergy",
        "AI Medical Discoveries & Drug Design",
        "Brain-Computer Interfaces & Neuralink",
        "Generative Video Models & Visual World Simulators",
        "AI Cybersecurity & Autonomous Defense Systems"
    ]
    selected_topic = random.choice(niches)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    prompt = f"""You are an expert AI & Tech news content creator for YouTube Shorts.
Timestamp Seed: {current_time}
Selected Sub-Topic: {selected_topic}

Generate a brand new, highly engaging 40-second video script specifically focused on {selected_topic}.
CRITICAL REQUIREMENT: Do NOT use generic placeholder text or repeat prior topics. Create a completely original headline, description, and script based on {selected_topic}.

Return ONLY a JSON object with this exact structure:
{{
  "title": "Catchy Specific Headline Here | AI News #Shorts",
  "description": "Engaging 2-sentence breakdown with hashtags #Shorts #AINews #FutureTech #TechBreakthroughs",
  "tags": ["AI News", "Future Tech", "{selected_topic}", "Technology"],
  "script": "Full 40-second spoken narration script goes here..."
}}"""

    # --- PRIMARY PROVIDER: Gemini API with Retries & Dynamic Fallback ---
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            
            # Try gemini-3.8-flash first
            for attempt in range(1, 4):
                try:
                    print(f"   Attempting Primary Provider: Gemini API (gemini-3.8-flash, Try {attempt}/3)...")
                    response = client.models.generate_content(
                        model="gemini-3.8-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                        ),
                    )
                    content = json.loads(response.text.strip())
                    print(f"   ✅ Gemini success! Topic: {selected_topic} | Title: {content['title']}")
                    return content
                except Exception as e:
                    print(f"   ⚠️ Gemini gemini-3.8-flash attempt {attempt} failed: {e}")
                    if attempt < 3:
                        time.sleep(5)

            # Dynamic Gemini Model Discovery Fallback
            print("   ⚠️ gemini-3.8-flash unavailable. Discovering active Gemini models...")
            for m in client.models.list():
                model_id = m.name.replace("models/", "")
                if "flash" in model_id or "pro" in model_id:
                    try:
                        print(f"   Trying Gemini model: '{model_id}'...")
                        response = client.models.generate_content(
                            model=model_id,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                            ),
                        )
                        content = json.loads(response.text.strip())
                        print(f"   ✅ Gemini ('{model_id}') success! Title: {content['title']}")
                        return content
                    except Exception as e:
                        print(f"   ⚠️ Gemini model '{model_id}' failed: {e}")

        except Exception as e:
            print(f"   ⚠️ Gemini API initialization error: {e}")

    # --- BACKUP PROVIDER: Groq API with Dynamic Active Model Discovery ---
    if groq_key:
        try:
            print("   Attempting Backup Provider: Groq API...")
            groq_client = Groq(api_key=groq_key)
            
            models_data = groq_client.models.list().data
            active_groq_models = [m.id for m in models_data if "whisper" not in m.id and "safetensors" not in m.id]
            print(f"   Discovered {len(active_groq_models)} active Groq models.")

            for model in active_groq_models:
                try:
                    print(f"   Trying Groq model: '{model}'...")
                    completion = groq_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"},
                    )
                    raw_json = completion.choices.message.content
                    content = json.loads(raw_json.strip())
                    print(f"   ✅ Groq ('{model}') success! Title: {content['title']}")
                    return content
                except Exception as e:
                    print(f"   ⚠️ Groq model '{model}' failed: {e}")
        except Exception as e:
            print(f"   ⚠️ Groq API initialization error: {e}")
    else:
        print("   ⚠️ GROQ_API_KEY environment variable is not set or empty in GitHub.")

    raise RuntimeError("❌ Both Gemini and Groq AI attempts failed. Please verify API keys.")

# ==========================================
# STEP 2: Edge-TTS Neural Voice Generation
# ==========================================
async def create_voiceover(text, output_file="voiceover.mp3"):
    print("🎙️ Step 2: Synthesizing natural neural speech via edge-tts...")
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)
    print("   Voiceover file generated successfully.")

# ==========================================
# STEP 3: Video Assembly via PIL & MoviePy
# ==========================================
def create_video(title_text, script_text, audio_file="voiceover.mp3", output_file="final_video.mp4"):
    print("🎬 Step 3: Assembling 9:16 vertical video & formatting subtitles...")
    audio = AudioFileClip(audio_file)
    duration = audio.duration
    
    # Create 9:16 vertical canvas (1080x1920)
    img = Image.new('RGB', (1080, 1920), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    # Top Header Badge
    draw.rectangle([(80, 180), (1000, 280)], fill=(30, 41, 59), outline=(56, 189, 248), width=3)
    draw.text((120, 215), "FUTURETECH AI PULSE", fill=(56, 189, 248))
    
    # Headline Box
    draw.rectangle([(80, 320), (1000, 580)], fill=(15, 23, 42))
    draw.text((100, 380), title_text[:75], fill=(255, 255, 255))
    
    # Subtitles / Script Card
    draw.rectangle([(80, 620), (1000, 1600)], fill=(30, 41, 59))
    draw.text((120, 660), "TODAY'S AI BREAKTHROUGH:", fill=(244, 63, 94))
    
    # Word Wrap Script
    words = script_text.split()
    lines, current_line = [], []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 30:
            lines.append(" ".join(current_line[:-1]))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    y_offset = 740
    for line in lines[:15]:
        draw.text((120, y_offset), line, fill=(226, 232, 240))
        y_offset += 50
        
    # Bottom Call to Action
    draw.rectangle([(80, 1650), (1000, 1780)], fill=(56, 189, 248))
    draw.text((180, 1700), "SUBSCRIBE FOR DAILY AI NEWS", fill=(15, 23, 42))
    
    frame_path = "frame.png"
    img.save(frame_path)
    
    video = ImageClip(frame_path).set_duration(duration)
    video = video.set_audio(audio)
    video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")
    print(f"   Video rendering complete: {output_file}")
    return output_file

# ==========================================
# STEP 4: YouTube API Upload (YPP Compliant)
# ==========================================
def upload_to_youtube(video_file, title, description, tags):
    print("🚀 Step 4: Uploading video to YouTube via Data API v3...")
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
            "title": title[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": "28"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }
    
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   Upload Progress: {int(status.progress() * 100)}%")
            
    video_id = response.get("id")
    print(f"🎉 SUCCESS! Video published live to YouTube: https://youtu.be/{video_id}")
    return video_id

# ==========================================
# MAIN EXECUTION ROUTINE
# ==========================================
if __name__ == "__main__":
    content = generate_script()
    asyncio.run(create_voiceover(content["script"], "voiceover.mp3"))
    video_file = create_video(content["title"], content["script"], "voiceover.mp3", "final_video.mp4")
    upload_to_youtube(video_file, content["title"], content["description"], content["tags"])
