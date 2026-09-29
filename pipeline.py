import os
import json
import time
import asyncio
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
# STEP 1: AI Script Generation (Gemini + Groq Active Models)
# ==========================================
def generate_script():
    print("🧠 Step 1: Requesting educational script from AI...")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")

    prompt = """You are an expert AI & Tech news content creator for YouTube Shorts.
Generate an educational, highly engaging 40-second video script about a major recent breakthrough in AI (e.g., OpenAI, Gemini, Robotics, or Autonomous Agents).

Return ONLY a JSON object with this exact structure:
{
  "title": "Did OpenAI Just Change Coding Forever? | AI News #Shorts",
  "description": "Exploring the latest AI breakthrough in software engineering. Subscribe to FutureTech Pulse for daily AI news! #Shorts #AINews #FutureTech",
  "tags": ["AI News", "OpenAI", "Machine Learning", "Future Tech", "Tech Breakthroughs"],
  "script": "OpenAI just unveiled a massive update that might change software development forever. Here is what you need to know in 40 seconds..."
}"""

    # --- PRIMARY PROVIDER: Gemini API with Retries ---
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
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
                    print(f"   ✅ Gemini success! Title: {content['title']}")
                    return content
                except Exception as e:
                    print(f"   ⚠️ Gemini API attempt {attempt} failed: {e}")
                    if attempt < 3:
                        wait_time = attempt * 15
                        print(f"   Pausing {wait_time} seconds for server capacity to clear...")
                        time.sleep(wait_time)
        except Exception as e:
            print(f"   ⚠️ Gemini client initialization error: {e}")

    # --- BACKUP PROVIDER: Groq API with Active Production Models ---
    if groq_key:
        groq_models = [
            "llama-3.1-8b-instant",
            "llama-3.3-70b-specdec",
            "deepseek-r1-distill-llama-70b",
            "qwen-2.5-32b"
        ]
        groq_client = Groq(api_key=groq_key)
        for model in groq_models:
            try:
                print(f"   Attempting Backup Provider: Groq API ({model})...")
                completion = groq_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )
                raw_json = completion.choices.message.content
                content = json.loads(raw_json.strip())
                print(f"   ✅ Groq ({model}) success! Title: {content['title']}")
                return content
            except Exception as e:
                print(f"   ⚠️ Groq model '{model}' failed: {e}")
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
