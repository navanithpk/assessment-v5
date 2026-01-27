#!/usr/bin/env python
"""
Quick diagnostic script to test AI services connectivity
"""
import os
import requests

def test_lmstudio():
    """Test if LMStudio is running"""
    print("\n" + "="*60)
    print("Testing LMStudio Connection")
    print("="*60)

    url = os.environ.get('LMSTUDIO_URL', 'http://localhost:1234/v1/chat/completions')
    print(f"URL: {url}")

    try:
        response = requests.post(
            url,
            json={
                "model": "local-model",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 10
            },
            timeout=5
        )

        if response.status_code == 200:
            print("✅ LMStudio is RUNNING and responding")
            data = response.json()
            print(f"   Response: {data.get('choices', [{}])[0].get('message', {}).get('content', 'N/A')}")
            return True
        else:
            print(f"❌ LMStudio returned HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ LMStudio is NOT RUNNING (Connection refused)")
        print("   Solution: Start LMStudio and enable local server")
        return False
    except requests.exceptions.Timeout:
        print("❌ LMStudio request TIMED OUT")
        print("   Solution: LMStudio may be overloaded or frozen")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_google_gemini():
    """Test if Google Gemini API is working"""
    print("\n" + "="*60)
    print("Testing Google Gemini API")
    print("="*60)

    api_key = os.environ.get('GOOGLE_API_KEY', 'AIzaSyCzbW72vCJ3YfxBEkQNb8HZkBTXD3iL6QE')

    if not api_key or api_key == 'AIzaSyCzbW72vCJ3YfxBEkQNb8HZkBTXD3iL6QE':
        print("⚠️  Using default/fallback API key")
    else:
        print("✅ Custom API key configured")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"

    try:
        response = requests.post(
            url,
            json={
                "contents": [{
                    "parts": [{
                        "text": "Say hello in one word"
                    }]
                }]
            },
            timeout=10
        )

        if response.status_code == 200:
            print("✅ Google Gemini API is WORKING")
            data = response.json()
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'N/A')
            print(f"   Response: {text[:100]}")
            return True
        elif response.status_code == 429:
            print("❌ Google Gemini RATE LIMITED")
            print("   Solution: Wait or use a different API key")
            return False
        elif response.status_code == 400:
            print("❌ Google Gemini BAD REQUEST")
            try:
                error_msg = response.json().get('error', {}).get('message', '')
                print(f"   Error: {error_msg[:200]}")
            except:
                print(f"   Response: {response.text[:200]}")
            print("   Solution: Check API key validity")
            return False
        else:
            print(f"❌ Google Gemini returned HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_anthropic():
    """Test if Anthropic API is configured"""
    print("\n" + "="*60)
    print("Testing Anthropic API")
    print("="*60)

    api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        print("⚠️  No ANTHROPIC_API_KEY configured")
        print("   This is optional - LMStudio and Gemini are sufficient")
        return None
    else:
        print("✅ ANTHROPIC_API_KEY is configured")
        print("   (Not testing actual API call to save credits)")
        return True


def test_pytesseract():
    """Test if pytesseract is installed"""
    print("\n" + "="*60)
    print("Testing OCR (pytesseract)")
    print("="*60)

    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"✅ pytesseract is installed (Tesseract {version})")
        return True
    except ImportError:
        print("❌ pytesseract is NOT installed")
        print("   Solution: pip install pytesseract")
        print("   Also install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    except Exception as e:
        print(f"⚠️  pytesseract installed but Tesseract binary not found")
        print(f"   Error: {str(e)}")
        print("   Solution: Install Tesseract OCR binary")
        return False


def main():
    print("\n" + "="*80)
    print("AI SERVICES DIAGNOSTIC TOOL")
    print("="*80)
    print("\nThis script tests connectivity to all AI services used for tagging.")

    results = {
        'lmstudio': test_lmstudio(),
        'gemini': test_google_gemini(),
        'anthropic': test_anthropic(),
        'pytesseract': test_pytesseract()
    }

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    working_services = []
    if results['lmstudio']:
        working_services.append('LMStudio (local, free)')
    if results['gemini']:
        working_services.append('Google Gemini (cloud, free tier)')
    if results['anthropic']:
        working_services.append('Anthropic (cloud, paid)')

    if working_services:
        print(f"\n✅ Working AI services ({len(working_services)}):")
        for service in working_services:
            print(f"   - {service}")
    else:
        print("\n❌ NO AI services are working!")
        print("   You need at least ONE working service to use AI tagging.")

    if results['pytesseract']:
        print("\n✅ OCR is available - can extract text from images")
    else:
        print("\n⚠️  OCR not available - image questions will use only visible text")

    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    if not results['lmstudio']:
        print("\n🔧 LMStudio (RECOMMENDED - free and unlimited):")
        print("   1. Download from: https://lmstudio.ai/")
        print("   2. Load a model (e.g., Llama 3.1 8B)")
        print("   3. Start local server (default: http://localhost:1234)")

    if not results['pytesseract']:
        print("\n🔧 Pytesseract (for image text extraction):")
        print("   1. pip install pytesseract pillow")
        print("   2. Install Tesseract OCR:")
        print("      Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        print("      macOS: brew install tesseract")
        print("      Linux: sudo apt-get install tesseract-ocr")

    if not any([results['lmstudio'], results['gemini'], results['anthropic']]):
        print("\n⚠️  CRITICAL: No working AI services!")
        print("   AI tagging will NOT work until you configure at least one service.")

    print("\n" + "="*80)


if __name__ == '__main__':
    main()
