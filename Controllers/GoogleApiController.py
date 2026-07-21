import os
import json
import base64
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import httpx

router = APIRouter(prefix="", tags=["google"])

def get_google_api_key():
    return os.getenv("GOOGLE_API_KEY")

def get_maps_api_key():
    # Geocoding, Maps, Directions, Places, Speech-to-Text (Google does not allow these on the same key as Gemini)
    return os.getenv("GOOGLE_MAPS_API_KEY") or get_google_api_key()

@router.get("/status")
async def status():
    key = get_google_api_key()
    configured = bool(key and key.strip())
    maps_key = get_maps_api_key()
    return {
        "configured": configured,
        "mapsConfigured": bool(maps_key and maps_key.strip()),
        "message": "Google API key is set. Gemini uses GOOGLE_API_KEY; Maps, Places, Directions, Geocoding, and Speech-to-Text use GOOGLE_MAPS_API_KEY." if configured else 'Google API key is not set. Add GOOGLE_API_KEY in Railway environment variables.'
    }

@router.get("/health")
async def health():
    return await gemini()

@router.get("/gemini")
async def gemini():
    key = get_google_api_key()
    if not key or not key.strip():
        return JSONResponse(content={"status": "not_configured", "message": "GOOGLE_API_KEY is not set.", "service": "Gemini"})
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
        body = {"contents": [{"parts": [{"text": "Reply with exactly: OK"}]}]}
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=body)
        text = r.text
        if not r.is_success:
            return JSONResponse(content={"status": "error", "message": text[:200] + ("..." if len(text) > 200 else ""), "service": "Gemini"})
        data = json.loads(text)
        message = "OK"
        if "candidates" in data and data["candidates"]:
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            if parts and "text" in parts[0]:
                message = (parts[0]["text"] or "OK").strip()
        return {"status": "ok", "message": message, "service": "Gemini"}
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e), "service": "Gemini"})

@router.get("/geocoding")
async def geocoding():
    key = get_maps_api_key()
    if not key or not key.strip():
        return JSONResponse(content={"status": "not_configured", "message": "GOOGLE_MAPS_API_KEY is not set.", "service": "Geocoding"})
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json?address=Times+Square+New+York&key=" + key
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
        text = r.text
        if not r.is_success:
            return JSONResponse(content={"status": "error", "message": text[:200] + ("..." if len(text) > 200 else ""), "service": "Geocoding"})
        data = json.loads(text)
        status_val = data.get("status", "")
        if status_val == "OK":
            return {"status": "ok", "message": "Geocoding API responded successfully.", "service": "Geocoding"}
        return JSONResponse(content={"status": "error", "message": status_val, "service": "Geocoding"})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e), "service": "Geocoding"})

@router.get("/maps")
async def maps():
    key = get_maps_api_key()
    if not key or not key.strip():
        return JSONResponse(content={"status": "not_configured", "message": "GOOGLE_MAPS_API_KEY is not set.", "service": "Maps"})
    try:
        url = f"https://maps.googleapis.com/maps/api/js?key={key}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
        text = r.text
        if not r.is_success:
            return JSONResponse(content={"status": "error", "message": text[:200] + ("..." if len(text) > 200 else ""), "service": "Maps"})
        if "ApiNotActivatedMapError" in text:
            return JSONResponse(content={"status": "error", "message": "Maps JavaScript API is not enabled for this key.", "service": "Maps"})
        if "RefererNotAllowedMapError" in text:
            return JSONResponse(content={"status": "error", "message": "Referer not allowed for this key.", "service": "Maps"})
        if "InvalidKeyMapError" in text:
            return JSONResponse(content={"status": "error", "message": "Invalid API key.", "service": "Maps"})
        return {"status": "ok", "message": "Maps JavaScript API key valid.", "service": "Maps"}
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e), "service": "Maps"})

@router.get("/directions")
async def directions():
    key = get_maps_api_key()
    if not key or not key.strip():
        return JSONResponse(content={"status": "not_configured", "message": "GOOGLE_MAPS_API_KEY is not set.", "service": "Directions"})
    try:
        import urllib.parse
        origin = urllib.parse.quote("Times Square, New York, NY")
        dest = urllib.parse.quote("Brooklyn Bridge, New York, NY")
        url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={dest}&key={key}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
        text = r.text
        if not r.is_success:
            return JSONResponse(content={"status": "error", "message": text[:200] + ("..." if len(text) > 200 else ""), "service": "Directions"})
        data = json.loads(text)
        status_val = data.get("status", "")
        if status_val == "OK":
            return {"status": "ok", "message": "Directions API responded successfully. Use it from the backend to return routes to the frontend.", "service": "Directions"}
        return JSONResponse(content={"status": "error", "message": status_val, "service": "Directions"})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e), "service": "Directions"})

@router.get("/places")
async def places():
    key = get_maps_api_key()
    if not key or not key.strip():
        return JSONResponse(content={"status": "not_configured", "message": "GOOGLE_MAPS_API_KEY is not set.", "service": "Places"})
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                "https://places.googleapis.com/v1/places:searchText",
                json={"textQuery": "coffee"},
                headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": "places.id"}
            )
        text = r.text
        if r.is_success:
            return {"status": "ok", "message": "Places API (New) responded successfully.", "service": "Places"}
        return JSONResponse(content={"status": "error", "message": text[:200] + ("..." if len(text) > 200 else ""), "service": "Places"})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e), "service": "Places"})

@router.get("/speech-to-text")
async def speech_to_text():
    key = get_maps_api_key()
    if not key or not key.strip():
        return JSONResponse(content={"status": "not_configured", "message": "GOOGLE_MAPS_API_KEY is not set.", "service": "SpeechToText"})
    try:
        silence_bytes = b'\x00' * 3200
        base64_audio = base64.b64encode(silence_bytes).decode("utf-8")
        body = {"config": {"encoding": "LINEAR16", "sampleRateHertz": 16000, "languageCode": "en-US"}, "audio": {"content": base64_audio}}
        url = f"https://speech.googleapis.com/v1/speech:recognize?key={key}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=body)
        text = r.text
        if r.is_success:
            return {"status": "ok", "message": "Speech-to-Text API accepted the request.", "service": "SpeechToText"}
        if r.status_code == 400 and "No speech" in text:
            return {"status": "ok", "message": "Speech-to-Text API responded (no speech in test audio).", "service": "SpeechToText"}
        return JSONResponse(content={"status": "error", "message": text[:200] + ("..." if len(text) > 200 else ""), "service": "SpeechToText"})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e), "service": "SpeechToText"})
