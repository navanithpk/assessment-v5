#!/usr/bin/env python3
"""
Test Script for LMStudio AI Tagging
Tests prompts and validates responses from LMStudio
"""

import requests
import json
import re
from datetime import datetime


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}")
    print(f"{text}")
    print(f"{'='*80}{Colors.ENDC}\n")


def print_section(text):
    print(f"{Colors.CYAN}{Colors.BOLD}--- {text} ---{Colors.ENDC}")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def test_lmstudio_connection(url):
    """Test if LMStudio is running and accessible"""
    print_section("Testing LMStudio Connection")

    try:
        response = requests.post(
            url,
            json={
                "model": "local-model",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            },
            timeout=5
        )

        if response.status_code == 200:
            print_success(f"LMStudio is running at {url}")
            return True
        else:
            print_error(f"LMStudio returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to LMStudio at {url}")
        print_warning("Make sure LMStudio is running and listening on the correct port")
        return False
    except Exception as e:
        print_error(f"Connection error: {str(e)}")
        return False


def test_topic_selection(url):
    """Test topic selection with sample question"""
    print_section("Testing Topic Selection")

    # Sample data
    question_text = """
    What is the process by which plants make their own food using sunlight, water, and carbon dioxide?

    A) Respiration
    B) Photosynthesis
    C) Transpiration
    D) Germination
    """

    topics = [
        "Cell Structure and Function",
        "Photosynthesis and Respiration",
        "Human Digestive System",
        "Reproduction in Plants",
        "Genetics and Evolution"
    ]

    topic_list = '\n'.join([f"{i+1}. {t}" for i, t in enumerate(topics)])

    prompt = f"""You are an expert educational content analyzer specializing in Biology for Grade 9.

**TASK**: Analyze the following question and select the MOST appropriate topic from the provided list.

**QUESTION**:
{question_text}

**AVAILABLE TOPICS** for Biology - Grade 9:
{topic_list}

**INSTRUCTIONS**:
- Read the question carefully
- Consider the subject (Biology) and grade level (Grade 9)
- Select the topic that BEST matches the question's content
- Respond with ONLY the topic number (e.g., "3")
- Do NOT include explanations, just the number

**RESPONSE** (number only):"""

    print(f"{Colors.BLUE}Prompt:{Colors.ENDC}")
    print("-" * 80)
    print(prompt)
    print("-" * 80)

    try:
        response = requests.post(
            url,
            json={
                "model": "local-model",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert educational content analyzer. Always respond with ONLY the requested numbers."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 100
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            response_text = data['choices'][0]['message']['content'].strip()

            print(f"\n{Colors.BLUE}Response:{Colors.ENDC}")
            print(f"{response_text}")

            # Validate response
            match = re.search(r'\d+', response_text)
            if match:
                topic_num = int(match.group())
                if 1 <= topic_num <= len(topics):
                    selected_topic = topics[topic_num - 1]
                    print_success(f"Valid response: Topic {topic_num} - {selected_topic}")

                    if topic_num == 2:  # Photosynthesis
                        print_success("CORRECT! The model selected 'Photosynthesis and Respiration'")
                        return True
                    else:
                        print_warning(f"Model selected '{selected_topic}' (expected 'Photosynthesis and Respiration')")
                        return False
                else:
                    print_error(f"Topic number {topic_num} is out of range (1-{len(topics)})")
                    return False
            else:
                print_error(f"No number found in response: {response_text}")
                return False
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False


def test_lo_selection(url):
    """Test learning objective selection with sample question"""
    print_section("Testing Learning Objective Selection")

    question_text = """
    Describe the process of mitosis and explain its importance in multicellular organisms.
    Include the stages of mitosis in your answer.
    """

    los = [
        {"code": "B.3.1", "description": "Describe the structure of DNA and its role in inheritance"},
        {"code": "B.3.2", "description": "Explain the process of mitosis and its significance"},
        {"code": "B.3.3", "description": "Describe meiosis and its role in sexual reproduction"},
        {"code": "B.3.4", "description": "Understand genetic variation and mutation"}
    ]

    lo_list = '\n'.join([f"{i+1}. [{lo['code']}] {lo['description']}" for i, lo in enumerate(los)])

    prompt = f"""You are an expert educational content analyzer specializing in Biology for Grade 9.

**TASK**: Analyze the following question and select the MOST relevant learning objective(s) from the provided list.

**CONTEXT**:
- Subject: Biology
- Grade: Grade 9
- Topic: Cell Division

**QUESTION**:
{question_text}

**AVAILABLE LEARNING OBJECTIVES**:
{lo_list}

**INSTRUCTIONS**:
- Read the question carefully
- You may select MULTIPLE learning objectives if the question covers multiple concepts
- Select objectives that the question is specifically assessing
- Respond with ONLY the numbers separated by commas (e.g., "1,3,5")
- Do NOT include explanations, just the numbers

**RESPONSE** (numbers only):"""

    print(f"{Colors.BLUE}Prompt:{Colors.ENDC}")
    print("-" * 80)
    print(prompt)
    print("-" * 80)

    try:
        response = requests.post(
            url,
            json={
                "model": "local-model",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert educational content analyzer. Always respond with ONLY the requested numbers."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 100
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            response_text = data['choices'][0]['message']['content'].strip()

            print(f"\n{Colors.BLUE}Response:{Colors.ENDC}")
            print(f"{response_text}")

            # Validate response
            lo_numbers = [int(n.strip()) for n in re.findall(r'\d+', response_text)]

            if lo_numbers:
                valid_numbers = [n for n in lo_numbers if 1 <= n <= len(los)]

                if valid_numbers:
                    selected_los = [f"{los[n-1]['code']} - {los[n-1]['description']}" for n in valid_numbers]
                    print_success(f"Valid response: Selected {len(valid_numbers)} LO(s)")
                    for lo_desc in selected_los:
                        print(f"  • {lo_desc}")

                    if 2 in valid_numbers:  # Mitosis LO
                        print_success("CORRECT! The model selected 'Explain the process of mitosis'")
                        return True
                    else:
                        print_warning("Model did not select the mitosis LO (expected)")
                        return False
                else:
                    print_error("All numbers are out of range")
                    return False
            else:
                print_error(f"No numbers found in response: {response_text}")
                return False
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False


def test_response_format(url):
    """Test if LMStudio returns clean number-only responses"""
    print_section("Testing Response Format Compliance")

    test_cases = [
        {
            "prompt": "Select the number 3 from this list: 1, 2, 3, 4, 5. Respond with ONLY the number.",
            "expected": "3",
            "description": "Simple number selection"
        },
        {
            "prompt": "Which numbers represent prime numbers from this list: 1, 2, 3, 4, 5, 6, 7? Respond with ONLY the numbers separated by commas.",
            "expected_pattern": r"2.*3.*5.*7",
            "description": "Multiple number selection"
        }
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n{Colors.BLUE}Test Case {i}: {test['description']}{Colors.ENDC}")

        try:
            response = requests.post(
                url,
                json={
                    "model": "local-model",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a precise assistant. Always respond with ONLY the requested numbers."
                        },
                        {
                            "role": "user",
                            "content": test['prompt']
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 50
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                response_text = data['choices'][0]['message']['content'].strip()

                print(f"Response: {response_text}")

                # Check if response is clean (no extra text)
                if 'expected' in test:
                    if response_text == test['expected']:
                        print_success("Perfect response format")
                        results.append(True)
                    elif test['expected'] in response_text:
                        print_warning(f"Correct number but extra text: '{response_text}'")
                        results.append(False)
                    else:
                        print_error(f"Incorrect response: '{response_text}'")
                        results.append(False)
                elif 'expected_pattern' in test:
                    if re.search(test['expected_pattern'], response_text):
                        print_success("Response matches expected pattern")
                        results.append(True)
                    else:
                        print_error(f"Response doesn't match pattern: '{response_text}'")
                        results.append(False)
            else:
                print_error(f"HTTP {response.status_code}")
                results.append(False)

        except Exception as e:
            print_error(f"Error: {str(e)}")
            results.append(False)

    return all(results)


def main():
    print_header("LMStudio AI Tagging Test Suite")

    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Configuration
    LMSTUDIO_URL = input("Enter LMStudio URL (default: http://localhost:1234/v1/chat/completions): ").strip()
    if not LMSTUDIO_URL:
        LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"

    print(f"\nUsing LMStudio at: {LMSTUDIO_URL}\n")

    # Run tests
    results = {}

    results['connection'] = test_lmstudio_connection(LMSTUDIO_URL)

    if results['connection']:
        results['topic'] = test_topic_selection(LMSTUDIO_URL)
        results['lo'] = test_lo_selection(LMSTUDIO_URL)
        results['format'] = test_response_format(LMSTUDIO_URL)
    else:
        print_error("\nSkipping remaining tests due to connection failure")
        return

    # Summary
    print_header("Test Summary")

    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)

    print(f"Connection Test:        {Colors.GREEN}PASS{Colors.ENDC}" if results['connection'] else f"Connection Test:        {Colors.FAIL}FAIL{Colors.ENDC}")
    print(f"Topic Selection Test:   {Colors.GREEN}PASS{Colors.ENDC}" if results.get('topic') else f"Topic Selection Test:   {Colors.FAIL}FAIL{Colors.ENDC}")
    print(f"LO Selection Test:      {Colors.GREEN}PASS{Colors.ENDC}" if results.get('lo') else f"LO Selection Test:      {Colors.FAIL}FAIL{Colors.ENDC}")
    print(f"Response Format Test:   {Colors.GREEN}PASS{Colors.ENDC}" if results.get('format') else f"Response Format Test:   {Colors.FAIL}FAIL{Colors.ENDC}")

    print(f"\n{Colors.BOLD}Overall: {passed_tests}/{total_tests} tests passed{Colors.ENDC}")

    if passed_tests == total_tests:
        print_success("\n✓ All tests passed! LMStudio is ready for AI tagging.")
    else:
        print_warning(f"\n⚠ {total_tests - passed_tests} test(s) failed. Review the output above.")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
