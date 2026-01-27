# Manual AI Tagging Improvements

## Summary

The manual AI tagging feature (used when adding/editing individual questions) has been upgraded to use the same powerful infrastructure as bulk tagging.

---

## ✅ What Changed

### Before (Old System)
- ❌ Generic prompts without subject/grade context
- ❌ **Rejected image-based questions** with error: "Image-based questions require Anthropic API"
- ❌ No OCR text extraction from images
- ❌ Anthropic → Google Gemini → LMStudio priority (expensive first)
- ❌ Simple topic/LO list without context

### After (New System)
- ✅ **Context-aware prompting** with subject, grade, topic names
- ✅ **OCR text extraction** from images (uses Tesseract)
- ✅ **LMStudio prioritization** → Google Gemini → Anthropic (free first!)
- ✅ **Works with image questions** via OCR (no Anthropic required)
- ✅ Returns which service was used + OCR info

---

## 🎯 Key Improvements

### 1. OCR Text Extraction

**Problem**: Questions with embedded images were rejected unless you had Anthropic API.

**Solution**: Now uses OCR to extract text from images, then feeds the extracted text to LMStudio/Gemini.

```
Question with image → OCR extracts text → Appends to prompt → Works with all AI services
```

### 2. Context-Aware Prompting

**Old Prompt**:
```
Analyze this question and select the most appropriate topic from the list below.

Question: [question text]

Available topics:
1. Topic A
2. Topic B
```

**New Prompt**:
```
You are an expert educational content analyzer specializing in Biology for Grade 10.

TASK: Analyze the following question and select the MOST appropriate topic...

QUESTION:
[question text]
[Image Content from OCR]: [extracted text from image]

AVAILABLE TOPICS for Biology - Grade 10:
1. Topic A
2. Topic B

INSTRUCTIONS:
- Consider the subject (Biology) and grade level (Grade 10)
- Select the topic that BEST matches the question's content
- Respond with ONLY the topic number
```

### 3. Service Priority Reordering

**Old Order**: Anthropic (paid) → Google Gemini → LMStudio
**New Order**: **LMStudio (free, local)** → Google Gemini → Anthropic

This means:
- Faster responses (local processing)
- No API costs for most requests
- Only uses cloud APIs as fallback

### 4. Image Handling

**Before**:
- Image questions → Show error "Image-based questions require Anthropic API"
- User must have Anthropic API key
- Costs money per request

**After**:
- Image questions → Extract text via OCR
- Send text to LMStudio (free, local)
- Falls back to Gemini/Anthropic if needed
- Works WITHOUT any API keys (if LMStudio is running)

---

## 📋 Affected Features

### 1. Topic Auto-Suggestion
**URL**: `/ajax/ai-suggest-topic/`
**Usage**: When clicking "Auto-tag Topic" in question editor

**Improvements**:
- Now includes subject and grade context
- Extracts OCR text from images
- Tries LMStudio first
- Returns service used: `{"success": true, "topic_id": 5, "service": "LMStudio", "ocr_extracted": "Extracted 156 characters from image"}`

### 2. Learning Objective Auto-Suggestion
**URL**: `/ajax/ai-suggest-los/`
**Usage**: When clicking "Auto-tag LO" in question editor

**Improvements**:
- Now includes subject, grade, and topic context
- Extracts OCR text from images
- Tries LMStudio first
- Can suggest multiple LOs
- Returns service used

---

## 🧪 Testing

### Test Case 1: Text-Only Question
1. Add/edit a question without images
2. Click "Auto-tag Topic"
3. **Expected**: LMStudio processes it (if running), otherwise falls back to Gemini

### Test Case 2: Image Question (NEW - Now Works!)
1. Add/edit a question with an embedded image (e.g., diagram, graph)
2. Click "Auto-tag Topic"
3. **Expected**:
   - OCR extracts text from image
   - LMStudio processes question + OCR text
   - Returns topic suggestion
   - **No "Image-based questions require Anthropic" error**

### Test Case 3: Fallback Behavior
1. Stop LMStudio
2. Click "Auto-tag Topic"
3. **Expected**: Falls back to Google Gemini, then Anthropic

---

## 🔍 Response Format

### Success Response
```json
{
  "success": true,
  "topic_id": 5,
  "topic_name": "Photosynthesis and Respiration",
  "service": "LMStudio",
  "ocr_extracted": "Extracted 156 characters from image"
}
```

### Error Response (All Services Failed)
```json
{
  "error": "All AI services failed. Please check your API keys and LMStudio connection."
}
```

---

## 🎓 Context-Aware Prompting Details

### Topic Selection Prompt
Includes:
- Subject name (e.g., "Biology")
- Grade level (e.g., "Grade 10")
- Topic list for that exact subject/grade combination
- Question text + OCR-extracted image text
- Clear instructions

### Learning Objective Selection Prompt
Includes:
- Subject name
- Grade level
- Topic name (already selected)
- LO list with codes and descriptions
- Question text + OCR-extracted image text
- Allows multiple LO selection

---

## 💡 Benefits

### For Users
1. **No API costs** - Works with free LMStudio
2. **Image questions work** - No more "Anthropic required" errors
3. **Better accuracy** - Context-aware prompts improve AI understanding
4. **Faster responses** - Local LMStudio is faster than cloud APIs

### For System
1. **Consistent infrastructure** - Uses same code as bulk tagging
2. **Maintainable** - Single source of truth for prompts
3. **Flexible** - Easy to update prompts in one place
4. **Resilient** - Multiple fallback options

---

## 📁 Files Modified

### `core/views.py`
**Function**: `ai_suggest_topic()` (lines 2588-2700)
- Added subject/grade name retrieval
- Integrated OCR text extraction
- Reordered service priority (LMStudio first)
- Uses `ContextAwarePromptBuilder` from `ai_tagging_improved.py`

**Function**: `ai_suggest_learning_objectives()` (lines 2803-2900)
- Added subject/grade/topic context
- Integrated OCR text extraction
- Reordered service priority
- Uses `ContextAwarePromptBuilder`

---

## 🔧 Dependencies

Same as bulk tagging:

```bash
pip install pytesseract pillow requests
```

**Tesseract OCR**:
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- macOS: `brew install tesseract`
- Linux: `sudo apt-get install tesseract-ocr`

**LMStudio** (optional but recommended):
- Download from https://lmstudio.ai/
- Load a model (Llama 3.1 8B or better)
- Start server on port 1234

---

## 🐛 Troubleshooting

### "Image-based questions require Anthropic API" Error

**This error should NO LONGER appear!** If you still see it:

1. **Check OCR installation**:
   ```bash
   tesseract --version
   ```

2. **Check Python can import pytesseract**:
   ```python
   import pytesseract
   print(pytesseract.get_tesseract_version())
   ```

3. **Check Django logs** - OCR failures will be logged

### "All AI services failed" Error

**Cause**: LMStudio not running AND no API keys configured

**Solutions**:
1. Start LMStudio local server
2. OR set Google API key: `export GOOGLE_API_KEY="your-key"`
3. OR set Anthropic API key: `export ANTHROPIC_API_KEY="your-key"`

### Topic/LO Suggestions Wrong

**Cause**: AI might need better context or the topic/LO list might not match the question

**Solutions**:
1. Ensure question has correct subject and grade selected
2. Check if appropriate topics exist for that subject/grade
3. Try a different AI service manually (if LMStudio fails, Gemini might work better)

---

## 📊 Comparison: Before vs After

| Feature | Before | After |
|---------|--------|-------|
| Image questions | ❌ Rejected | ✅ Works with OCR |
| Service priority | Anthropic first | LMStudio first |
| Subject/grade context | ❌ No | ✅ Yes |
| OCR text extraction | ❌ No | ✅ Yes |
| API costs (if LMStudio running) | $ per request | Free |
| Response time (local) | Slow (cloud API) | Fast (local) |
| Prompt quality | Generic | Context-aware |
| Service transparency | ❌ Hidden | ✅ Shows which service used |

---

## 🚀 Next Steps

1. **Install OCR** (if not already):
   ```bash
   pip install pytesseract
   # Then install Tesseract OCR (see Dependencies)
   ```

2. **Setup LMStudio** (optional but recommended):
   - Download and install
   - Load model
   - Start server

3. **Test it**:
   - Edit a question with an image
   - Click "Auto-tag Topic"
   - Should work without Anthropic API!

4. **Monitor results**:
   - Check console for which service was used
   - Verify OCR extraction is working for images

---

**Last Updated**: 2026-01-25
**Version**: 2.0 (aligned with bulk tagging infrastructure)
