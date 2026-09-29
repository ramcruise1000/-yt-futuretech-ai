import os
import json
import time
import asyncio
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError
from PIL import Image, ImageDraw
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# ==========================================
# STEP 1: Gemini API Script Generation (with Auto-Retry)
# ==========================================
def generate_script():
    print("🧠 Step 1: Requesting educational script from Gemini API...")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("❌ GEMINI_API_KEY secret is missing or empty! Verify GitHub Repository Secrets.")

    client = genai.Client(api_key=api_key)
    
    prompt = """You are an expert AI & Tech news content creator for YouTube Shorts.
Generate an educational, highly engaging 40-second video script about a major recent breakthrough in AI (e.g., OpenAI, Gemini, Robotics, or Autonomous Agents).

Return a JSON object with this exact structure:
{
  "title": "Did OpenAI Just Change Coding Forever? | AI News #Shorts",
  "description": "Exploring the latest AI breakthrough in software engineering. Subscribe to FutureTech Pulse for daily AI news! #Shorts #AINews #FutureTech",
  "tags": ["AI News", "OpenAI", "Machine Learning", "Future Tech", "Tech Breakthroughs"],
  "script": "OpenAI just unveiled a massive update that might change software development forever. Here is what you need to know in 40 seconds..."
}"""

    # List of models to try if high-demand spikes occur
    models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]
    max_retries = 3

    for model in models_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                print(f"   Attempting model '{model}' (Try {attempt}/{max_retries})...")
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
                content = json.loads(response.text.strip())
                print(f"   ✅ Successfully generated script with model '{model}'!")
                print(f"   Generated Title: {content['title']}")
                return content
            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str:
                    print(f"   ⚠️ Model '{model}' hit a temporary 503 load spike. Pausing 10 seconds before retrying...")
                    time.sleep(10)
                else:
                    print(f"   ⚠️ Error with '{model}': {e}. Trying fallback model...")
                    break
                    
    raise RuntimeError("❌ All Gemini API attempts failed due to persistent server load. Please trigger workflow again in 2 minutes.")

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
