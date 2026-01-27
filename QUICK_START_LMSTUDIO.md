# Quick Start: LMStudio for AI Tagging

## Current Status

✅ **OCR Working** - Tesseract 5.3 installed and configured
✅ **LMStudio Running** - Server is active at http://localhost:1234
❌ **No Model Loaded** - Need to load a model in LMStudio
❌ **Google Gemini** - API key expired (alternative option)

---

## Solution: Load a Model in LMStudio

### Step 1: Open LMStudio
- LMStudio is already running (server detected at localhost:1234)
- Open the LMStudio application

### Step 2: Load a Model

**If you already have models downloaded:**
1. Go to the **"Developer"** or **"Chat"** tab
2. Click on the **model dropdown** at the top
3. Select any model you have (recommended: Llama 3.1 8B, Mistral 7B, or similar)
4. Wait for it to load (you'll see "Model loaded" message)

**If you need to download a model:**
1. Go to the **"Discover"** or **"Search"** tab
2. Search for: `meta-llama-3.1-8b-instruct`
3. Click **Download**
4. After download completes, go to **"Developer"** tab
5. Select the model from dropdown
6. Click **"Load Model"**

### Step 3: Verify It's Working

Run this command in your terminal:
```bash
python -c "import requests; r = requests.post('http://localhost:1234/v1/chat/completions', json={'model':'local-model','messages':[{'role':'user','content':'Hello'}],'max_tokens':10}, timeout=5); print('Status:', r.status_code); print('Working!' if r.status_code == 200 else 'Error:', r.text[:200])"
```

**Expected output:**
```
Status: 200
Working!
```

### Step 4: Test AI Tagging

1. Go to your Django application
2. Edit a question (with or without an image)
3. Click **"Auto-tag Topic"**
4. Should work now with LMStudio!

---

## Alternative: Use Google Gemini API

If you prefer using Google's cloud API instead of local LMStudio:

### Get a New Free API Key

1. Go to: https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key

### Set the API Key

**Windows (current session):**
```bash
set GOOGLE_API_KEY=your-actual-api-key-here
```

**Windows (permanent):**
```bash
setx GOOGLE_API_KEY "your-actual-api-key-here"
```

**Then restart your Django server:**
```bash
python manage.py runserver
```

---

## Recommended Models for LMStudio

Choose based on your system:

### For 8GB RAM or less:
- **Qwen 2.5 3B Instruct** (very fast, good for tagging)
- **Phi-3 Mini** (Microsoft, efficient)

### For 16GB RAM:
- **Llama 3.1 8B Instruct** (best balance, recommended)
- **Mistral 7B Instruct**
- **Gemma 2 9B**

### For 32GB+ RAM:
- **Llama 3.1 70B** (most accurate)
- **Qwen 2.5 32B**

---

## Troubleshooting

### "Model loading is slow"
- **Cause**: Large model + limited RAM
- **Solution**: Try a smaller model (3B or 7B)

### "LMStudio keeps timing out"
- **Cause**: Model is too large for your system
- **Solution**:
  1. Reduce context length in LMStudio settings
  2. Use a smaller/quantized model
  3. Increase timeout in settings

### "Still getting errors after loading model"
- **Solution**: Restart LMStudio server:
  1. In LMStudio, go to **"Developer"** tab
  2. Click **"Stop Server"**
  3. Click **"Start Server"**
  4. Reload your model

---

## What Happens Next?

Once you have LMStudio working with a loaded model:

✅ **Manual AI Tagging** - Click "Auto-tag Topic" on any question
✅ **Bulk AI Tagging** - Tag all untagged questions at once
✅ **Image Questions** - OCR extracts text, LMStudio processes it
✅ **Free & Unlimited** - No API costs, no rate limits
✅ **Fast** - Local processing, typically 2-3 seconds per question

---

## System Architecture

```
Question (text + image)
    ↓
OCR extracts image text (Tesseract)
    ↓
Build context-aware prompt (subject + grade + topics)
    ↓
Try LMStudio (local, free) ← YOU ARE HERE
    ↓ (if fails)
Try Google Gemini (cloud, free tier)
    ↓ (if fails)
Try Anthropic (cloud, paid)
    ↓
Return topic/LO suggestion
```

---

## Current System Status

| Component | Status | Notes |
|-----------|--------|-------|
| OCR (Tesseract) | ✅ Working | v5.3, configured at `C:\Program Files\Tesseract-OCR` |
| LMStudio Server | ✅ Running | http://localhost:1234 |
| LMStudio Model | ❌ **Not Loaded** | **Action Required** |
| Google Gemini | ❌ Key Expired | Optional - can get new key |
| Anthropic | ❌ Not Configured | Optional - paid service |

---

## Quick Reference

**Check if model is loaded:**
```bash
curl -X POST http://localhost:1234/v1/chat/completions -H "Content-Type: application/json" -d "{\"model\":\"local-model\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":10}"
```

**Expected when working:**
```json
{
  "choices": [{
    "message": {
      "content": "Hello! ..."
    }
  }]
}
```

**Expected when no model loaded:**
```json
{
  "error": {
    "message": "No models loaded. Please load a model..."
  }
}
```

---

**Need Help?**
- LMStudio Docs: https://lmstudio.ai/docs
- Download Models: https://huggingface.co/models
- Test Connection: Run `python test_ai_services.py` (use the simple version we created)

---

**Last Updated**: 2026-01-25
**Your Status**: Ready to load a model and start tagging! 🚀
