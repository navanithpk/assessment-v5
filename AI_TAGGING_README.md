# AI Tagging System - Setup and Usage Guide

## 🎯 Overview

The improved AI tagging system includes:
- **OCR Text Extraction** from question images
- **Context-Aware Prompting** with subject, grade, and topic information
- **Comprehensive Logging** for debugging
- **LMStudio Priority** with Google Gemini and Anthropic fallbacks
- **Logs Viewer** for monitoring tagging operations

## 📦 Installation

### 1. Install Python Dependencies

```bash
pip install pytesseract pillow
```

### 2. Install Tesseract OCR

#### Windows:
1. Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default location: `C:\Program Files\Tesseract-OCR`
3. Add to system PATH: `C:\Program Files\Tesseract-OCR`

#### macOS:
```bash
brew install tesseract
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

### 3. Verify Installation

```bash
tesseract --version
```

Should output something like: `tesseract 5.x.x`

## 🔧 Configuration

### API Keys (Environment Variables)

Add these to your environment or `.env` file:

```bash
# Optional - Anthropic Claude API
export ANTHROPIC_API_KEY="your-key-here"

# Optional - Google Gemini API (fallback included in code)
export GOOGLE_API_KEY="your-key-here"

# LMStudio URL (default: http://localhost:1234/v1/chat/completions)
export LMSTUDIO_URL="http://localhost:1234/v1/chat/completions"
```

### LMStudio Setup

1. Download and install LMStudio from: https://lmstudio.ai/
2. Load a capable model (recommended: Llama 3.1 8B or better)
3. Start the local server:
   - In LMStudio, go to "Local Server" tab
   - Click "Start Server"
   - Verify it's running on `http://localhost:1234`

## 🧪 Testing

### Test LMStudio Connection and Prompts

Run the test script:

```bash
python test_lmstudio_prompt.py
```

This will:
- ✅ Test connection to LMStudio
- ✅ Test topic selection with sample question
- ✅ Test learning objective selection
- ✅ Test response format compliance

**Sample Output:**
```
================================================================================
LMStudio AI Tagging Test Suite
================================================================================

Using LMStudio at: http://localhost:1234/v1/chat/completions

--- Testing LMStudio Connection ---
✓ LMStudio is running at http://localhost:1234/v1/chat/completions

--- Testing Topic Selection ---
Prompt:
--------------------------------------------------------------------------------
You are an expert educational content analyzer specializing in Biology...
--------------------------------------------------------------------------------

Response:
2

✓ Valid response: Topic 2 - Photosynthesis and Respiration
✓ CORRECT! The model selected 'Photosynthesis and Respiration'

================================================================================
Test Summary
================================================================================
Connection Test:        PASS
Topic Selection Test:   PASS
LO Selection Test:      PASS
Response Format Test:   PASS

Overall: 4/4 tests passed

✓ All tests passed! LMStudio is ready for AI tagging.
```

## 🚀 Usage

### 1. Access the Feature

1. Login as teacher/admin
2. Go to Teacher Dashboard
3. You'll see an "Untagged Questions" card if there are questions without topics/LOs
4. Click "🤖 AI Tag All Questions"

### 2. Monitor Progress

- Real-time progress bar shows tagging progress
- Each question is processed sequentially
- Progress indicator shows: "Tagged X of Y questions..."

### 3. View Logs

After tagging completes:

1. Navigate to `/teacher/ai-logs/`
2. Select a log file from the sidebar
3. View detailed logs with:
   - **Filters**: All, Info, Warnings, Errors, Debug
   - **Search**: Search through log content
   - **Color-coded**: Different colors for log levels

### Log File Structure

Logs include:
- ✅ Question processing start/end
- ✅ OCR text extraction results
- ✅ Prompts sent to AI services
- ✅ Responses received
- ✅ Topics and LOs tagged
- ✅ Errors and warnings
- ✅ Statistics summary

## 📊 Log Viewer Features

### Filters
- **All**: Show all log entries
- **Info**: General information
- **Warning**: Warnings (non-critical issues)
- **Error**: Errors that occurred
- **Debug**: Detailed debug information

### Search
Type in the search box to filter logs by content

### Statistics
Each log session shows:
- Total questions processed
- Topics tagged
- Learning objectives tagged
- Skipped questions
- Errors
- API calls made (Anthropic, Gemini, LMStudio)
- OCR extractions performed

## 🔍 How It Works

### 1. Context-Aware Prompting

**Old System:**
```
Analyze this question and select a topic: [question text]
Topics: 1. Topic A, 2. Topic B...
```

**New System:**
```
You are an expert educational content analyzer specializing in [SUBJECT] for Grade [GRADE].

TASK: Analyze the following question...

QUESTION:
[question text]
[Image Content from OCR]: [extracted text]

AVAILABLE TOPICS for [SUBJECT] - Grade [GRADE]:
1. Topic A
2. Topic B
...

INSTRUCTIONS:
- Consider the subject ([SUBJECT]) and grade level ([GRADE])
- Select the topic that BEST matches the question's content
- Respond with ONLY the topic number
```

### 2. OCR Text Extraction

For questions with images:
1. Detects base64 encoded images in HTML
2. Extracts image data
3. Uses Tesseract OCR to extract text
4. Appends extracted text to question context
5. Logs extraction results

### 3. Service Priority

1. **LMStudio** (Primary) - Local, free, unlimited
2. **Google Gemini** (Fallback #1) - Free tier available
3. **Anthropic Claude** (Fallback #2) - Paid, high quality

### 4. Logging

Every operation is logged:
- Timestamp
- Log level (INFO, DEBUG, WARNING, ERROR)
- Message
- Service used
- Results

## 🐛 Troubleshooting

### "Error: Cannot connect to LMStudio"

**Solution:**
1. Ensure LMStudio is running
2. Check local server is started in LMStudio
3. Verify URL is correct: `http://localhost:1234`
4. Run test script to diagnose: `python test_lmstudio_prompt.py`

### "OCR not available"

**Solution:**
1. Install pytesseract: `pip install pytesseract`
2. Install Tesseract OCR (see Installation section)
3. Verify: `tesseract --version`

### "All AI services failed"

**Possible causes:**
1. LMStudio not running
2. Invalid API keys for Gemini/Anthropic
3. Network issues

**Solution:**
1. Check logs in `/teacher/ai-logs/`
2. Look for ERROR level entries
3. Verify API keys are set
4. Run test script to diagnose

### Questions not getting tagged

**Check:**
1. Questions must have `subject` and `grade` set
2. Topics must exist for that subject/grade combination
3. Learning Objectives must exist for topics
4. View logs to see why questions were skipped

## 📝 Example Log Entry

```
2026-01-25 14:30:22 - INFO - === Bulk AI Tagging Started - Total Questions: 85 ===
2026-01-25 14:30:22 - INFO - --- Processing Question 42 ---
2026-01-25 14:30:22 - DEBUG - Question Preview: What is photosynthesis?...
2026-01-25 14:30:23 - INFO - OCR Extracted from Question 42: 156 chars
2026-01-25 14:30:23 - DEBUG - OCR Text: The diagram shows a plant cell...
2026-01-25 14:30:23 - DEBUG - [LMStudio] PROMPT:
--------------------------------------------------------------------------------
You are an expert educational content analyzer specializing in Biology...
--------------------------------------------------------------------------------
2026-01-25 14:30:25 - DEBUG - [LMStudio] RESPONSE:
--------------------------------------------------------------------------------
2
--------------------------------------------------------------------------------
2026-01-25 14:30:25 - INFO - ✓ Question 42 tagged with Topic: Photosynthesis (via LMStudio)
2026-01-25 14:30:26 - INFO - ✓ Question 42 tagged with LOs: B.2.1, B.2.2 (via LMStudio)
```

## 🎓 Best Practices

1. **Test First**: Always run `test_lmstudio_prompt.py` before bulk tagging
2. **Monitor Logs**: Check logs after tagging to identify issues
3. **LMStudio Model**: Use models with 7B+ parameters for better accuracy
4. **Batch Size**: The system processes all questions; for very large databases (1000+), consider batching
5. **Review Results**: Spot-check tagged questions to ensure accuracy

## 🆘 Support

For issues or questions:
1. Check the logs at `/teacher/ai-logs/`
2. Run the test script: `python test_lmstudio_prompt.py`
3. Review this README
4. Check Django logs for Python exceptions

## 📈 Performance

Expected performance (with LMStudio on local machine):
- **Topic tagging**: ~2-3 seconds per question
- **LO tagging**: ~2-3 seconds per question
- **Total**: ~5-6 seconds per question
- **100 questions**: ~8-10 minutes

With rate limiting delay: Add 0.3s per question

## 🔄 Updates

### Version 2.0 (Current)
- ✅ OCR text extraction from images
- ✅ Context-aware prompting with subject/grade
- ✅ Comprehensive logging system
- ✅ Logs viewer web interface
- ✅ LMStudio prioritization
- ✅ Test script for validation

### Version 1.0 (Previous)
- Basic AI tagging
- Simple prompts
- No logging
- No OCR support
