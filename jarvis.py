import sys
import time
import io
import os
import glob
import tempfile
import winsound
import subprocess
import json
import shutil
import webbrowser
import re
from datetime import datetime

ffmpeg_path = r"C:\Users\naiti\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin"
if os.path.exists(ffmpeg_path) and ffmpeg_path not in os.environ.get('PATH', ''):
    os.environ['PATH'] = ffmpeg_path + os.pathsep + os.environ.get('PATH', '')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ORANGE = "\033[38;5;208m"
BLUE = "\033[34m"
GREEN = "\033[32m"
RESET = "\033[0m"

try:
    from pocket_tts import TTSModel
except ImportError:
    TTSModel = None

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    import scipy.io.wavfile as wav
except ImportError:
    wav = None

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except ImportError:
    SD_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

tts_model = None
voice_state = None
client = None
recognizer = None
microphone = None
whisper_model = None
conversation_history = []
input_mode = "text"
is_shutting_down = False

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "conversation_history.json")

os.makedirs(DATA_DIR, exist_ok=True)

def load_conversation_history():
    global conversation_history
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                conversation_history = json.load(f)
    except:
        conversation_history = []

def save_conversation_history():
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(conversation_history, f, indent=2, ensure_ascii=False)
    except:
        pass

def add_to_history(user_input, jarvis_response):
    conversation_history.append({
        "timestamp": datetime.now().isoformat(),
        "user": user_input,
        "jarvis": jarvis_response
    })
    save_conversation_history()

def init_voice():
    global recognizer, microphone, whisper_model
    if WHISPER_AVAILABLE and SD_AVAILABLE:
        try:
            print(f"{BLUE}  Loading Whisper model...{RESET}")
            whisper_model = whisper.load_model("base")
            print(f"{BLUE}  Whisper model loaded.{RESET}")
            sd.rec(int(1 * 16000), samplerate=16000, channels=1, dtype='int16')
            sd.stop()
            return True
        except Exception as e:
            print(f"{BLUE}  Voice init failed: {e}{RESET}")
            return False
    elif SR_AVAILABLE:
        try:
            recognizer = sr.Recognizer()
            microphone = sr.Microphone()
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
            return True
        except Exception as e:
            print(f"{BLUE}  Mic init failed: {e}{RESET}")
            return False
    return False

def listen_voice():
    if WHISPER_AVAILABLE and SD_AVAILABLE and whisper_model:
        try:
            print(f"{BLUE}  [Listening...]{RESET}")
            duration = 5
            audio = sd.rec(int(duration * 16000), samplerate=16000, channels=1, dtype='int16')
            sd.wait()
            audio_path = tempfile.mktemp(suffix='.wav')
            import scipy.io.wavfile as swav
            swav.write(audio_path, 16000, audio)
            result = whisper_model.transcribe(audio_path, language='en')
            os.remove(audio_path)
            text = result['text'].strip()
            if text:
                return text
            return None
        except Exception as e:
            print(f"{BLUE}  Whisper error: {e}{RESET}")
            return None
    elif SR_AVAILABLE and recognizer and microphone:
        try:
            with microphone as source:
                print(f"{BLUE}  [Listening...]{RESET}")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            text = recognizer.recognize_google(audio)
            return text
        except:
            return None
    return None

def init_tts():
    global tts_model, voice_state
    try:
        if not TTSModel:
            raise ImportError("pocket_tts not installed")
        print(f"{BLUE}  Initializing TTS engine...{RESET}")
        tts_model = TTSModel.load_model()
        
        if not tts_model:
            raise Exception("Failed to load TTS model")
            
        voice_files = glob.glob(os.path.join(os.path.dirname(__file__), "voice", "*.wav"))
        if voice_files:
            audio_prompt = voice_files[0]
            print(f"{BLUE}  Loading voice from: {os.path.basename(audio_prompt)}{RESET}")
            voice_state = tts_model.get_state_for_audio_prompt(audio_prompt)
        else:
            print(f"{BLUE}  Using default voice (alba){RESET}")
            voice_state = tts_model.get_state_for_audio_prompt("alba")
            
        if not voice_state:
            raise Exception("Failed to initialize voice state")
            
    except Exception as e:
        print(f"{ORANGE}  TTS initialization failed: {e}{RESET}")
        tts_model = None
        voice_state = None

def init_groq():
    global client
    try:
        if not Groq:
            raise ImportError("groq not installed")
        client = Groq(api_key=os.environ.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE"))
    except Exception as e:
        print(f"{BLUE}  Groq initialization info: {e}{RESET}")
        client = None

def speak(text):
    if not tts_model or not voice_state or is_shutting_down:
        return
    temp_path = None
    try:
        audio = tts_model.generate_audio(voice_state, text)
        if audio is None:
            return
        audio_np = audio.cpu().numpy() if hasattr(audio, 'numpy') else audio
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_path = temp_file.name
        temp_file.close()
        if wav:
            wav.write(temp_path, tts_model.sample_rate, audio_np)
        winsound.PlaySound(temp_path, winsound.SND_FILENAME)
    except Exception as e:
        pass
    finally:
        if temp_path:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass

def is_app_installed(app_name):
    app_paths = [
        f"C:\\Program Files\\{app_name}\\{app_name}.exe",
        f"C:\\Program Files (x86)\\{app_name}\\{app_name}.exe",
        f"C:\\Users\\{os.getenv('USERNAME')}\\AppData\\Local\\{app_name}\\{app_name}.exe",
    ]
    for path in app_paths:
        if os.path.exists(path):
            return True
    
    try:
        result = subprocess.run(["where", app_name], capture_output=True, text=True)
        if result.returncode == 0:
            return True
    except:
        pass
    return False

def open_app_or_website(command):
    command = command.lower()
    
    browser_patterns = ['chrome', 'firefox', 'edge', 'browser', 'brave', 'opera']
    websites = {
        'instagram': 'https://www.instagram.com',
        'youtube': 'https://www.youtube.com',
        'facebook': 'https://www.facebook.com',
        'twitter': 'https://twitter.com',
        'whatsapp': 'https://web.whatsapp.com',
        'gmail': 'https://mail.google.com',
        'google': 'https://www.google.com',
        'reddit': 'https://www.reddit.com',
        'linkedin': 'https://www.linkedin.com',
        'github': 'https://github.com',
        'netflix': 'https://www.netflix.com',
        'spotify': 'https://open.spotify.com',
        'telegram': 'https://web.telegram.org',
    }
    
    browser_to_use = None
    for browser in browser_patterns:
        if browser in command:
            browser_to_use = browser
            break
    
    for site, url in websites.items():
        if site in command:
            if browser_to_use:
                webbrowser.get(f'{browser_to_use} %s').open(url)
            else:
                webbrowser.open(url)
            return f"Opening {site} {'in ' + browser_to_use if browser_to_use else ''}"
    
    apps = {
        'notepad': 'notepad.exe',
        'calculator': 'calc.exe',
        'paint': 'mspaint.exe',
        'word': 'winword.exe',
        'excel': 'excel.exe',
        'powerpoint': 'powerpnt.exe',
        'vs code': 'code.exe',
        'vscode': 'code.exe',
        'sublime': 'sublime_text.exe',
        'chrome': 'chrome.exe',
        'firefox': 'firefox.exe',
        'edge': 'msedge.exe',
        'brave': 'brave.exe',
        'spotify': 'spotify.exe',
        'discord': 'discord.exe',
        'telegram': 'Telegram.exe',
        'whatsapp': 'WhatsApp.exe',
        'zoom': 'Zoom.exe',
        'teams': 'Teams.exe',
        'skype': 'Skype.exe',
        'vlc': 'vlc.exe',
        'OBS': 'obs64.exe',
        'python': 'python.exe',
        'git': 'git.exe',
        'cmd': 'cmd.exe',
        'powershell': 'powershell.exe',
        'explorer': 'explorer.exe',
    }
    
    for app_name, exe_name in apps.items():
        if app_name in command:
            if is_app_installed(exe_name.replace('.exe', '')):
                try:
                    subprocess.Popen(exe_name)
                    return f"Opening {app_name}"
                except:
                    pass
            else:
                search_url = f"https://www.google.com/search?q=download+{app_name}"
                webbrowser.open(search_url)
                return f"{app_name} not found. Opening search in browser."
    
    return None

def close_app_or_tab(command):
    command = command.lower()
    
    tab_apps = {
        'chrome': 'chrome',
        'firefox': 'firefox',
        'edge': 'msedge',
        'brave': 'brave',
        'opera': 'opera',
    }
    
    for browser, proc_name in tab_apps.items():
        if browser in command and ('tab' in command or 'close' in command or 'website' in command or 'page' in command):
            try:
                subprocess.run(['taskkill', '/F', '/IM', f'{proc_name}.exe'], capture_output=True)
                return f"Closing all {browser} windows"
            except:
                pass
    
    apps_to_kill = {
        'notepad': 'notepad.exe',
        'calculator': 'calc.exe',
        'paint': 'mspaint.exe',
        'word': 'winword.exe',
        'excel': 'excel.exe',
        'powerpoint': 'powerpnt.exe',
        'vs code': 'code.exe',
        'chrome': 'chrome.exe',
        'firefox': 'firefox.exe',
        'edge': 'msedge.exe',
        'spotify': 'spotify.exe',
        'discord': 'discord.exe',
        'telegram': 'Telegram.exe',
        'whatsapp': 'WhatsApp.exe',
        'zoom': 'Zoom.exe',
        'teams': 'Teams.exe',
    }
    
    for app_name, exe_name in apps_to_kill.items():
        if app_name in command:
            try:
                subprocess.run(['taskkill', '/F', '/IM', exe_name], capture_output=True)
                return f"Closing {app_name}"
            except:
                return f"Could not close {app_name}"
    
    return None

def create_file_folder(command):
    command = command.lower()
    
    patterns = [
        r'create\s+(?:a\s+)?(?:new\s+)?folder\s+(?:named\s+|called\s+)?["\']?(.+?)["\']?\s+(?:on|in)\s+(.+)',
        r'create\s+(?:a\s+)?(?:new\s+)?folder\s+(?:named\s+|called\s+)?["\']?(.+?)["\']?',
        r'create\s+(?:a\s+)?(?:new\s+)?file\s+(?:named\s+|called\s+)?["\']?(.+?)["\']?\s+(?:on|in)\s+(.+)',
        r'create\s+(?:a\s+)?(?:new\s+)?file\s+(?:named\s+|called\s+)?["\']?(.+?)["\']?',
        r'make\s+(?:a\s+)?folder\s+(?:named\s+|called\s+)?["\']?(.+?)["\']?\s+(?:on|in)\s+(.+)',
        r'make\s+(?:a\s+)?folder\s+(?:named\s+|called\s+)?["\']?(.+?)["\']?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                name, location = groups
            else:
                name = groups[0]
                location = None
            
            name = name.strip().strip('"').strip("'")
            
            if location:
                location = location.strip()
                if not os.path.exists(location):
                    return f"Location not found: {location}"
                full_path = os.path.join(location, name)
            else:
                if 'desktop' in command:
                    location = os.path.join(os.path.expanduser('~'), 'Desktop')
                elif 'd drive' in command or 'd:' in command:
                    location = 'D:\\'
                elif 'c drive' in command:
                    location = 'C:\\'
                else:
                    location = os.path.expanduser('~')
                full_path = os.path.join(location, name)
            
            try:
                if 'folder' in command:
                    os.makedirs(full_path, exist_ok=True)
                    return f"Created folder: {full_path}"
                else:
                    ext = ''
                    if '.' not in name:
                        if 'python' in command:
                            ext = '.py'
                        elif 'text' in command:
                            ext = '.txt'
                        elif 'excel' in command:
                            ext = '.xlsx'
                        elif 'word' in command:
                            ext = '.docx'
                        else:
                            ext = '.txt'
                        name = name + ext
                    full_path = os.path.join(os.path.dirname(full_path), name)
                    with open(full_path, 'w') as f:
                        pass
                    return f"Created file: {full_path}"
            except Exception as e:
                return f"Error creating: {str(e)}"
    
    return None

def delete_file_folder(command):
    command = command.lower()
    
    patterns = [
        r'delete\s+(?:the\s+)?(?:folder\s+|file\s+)?["\']?(.+?)["\']?',
        r'remove\s+(?:the\s+)?(?:folder\s+|file\s+)?["\']?(.+?)["\']?',
        r'delete\s+(?:the\s+)?["\']?(.+?)["\']?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            path = match.group(1).strip().strip('"').strip("'")
            
            if os.path.exists(path):
                full_path = path
            elif 'desktop' in command:
                full_path = os.path.join(os.path.expanduser('~'), 'Desktop', os.path.basename(path))
            else:
                search_paths = [
                    os.path.join(os.path.expanduser('~'), 'Desktop', path),
                    os.path.join('C:\\', path),
                    os.path.join('D:\\', path),
                ]
                full_path = None
                for sp in search_paths:
                    if os.path.exists(sp):
                        full_path = sp
                        break
            
            if full_path and os.path.exists(full_path):
                try:
                    if os.path.isdir(full_path):
                        shutil.rmtree(full_path)
                        return f"Deleted folder: {full_path}"
                    else:
                        os.remove(full_path)
                        return f"Deleted file: {full_path}"
                except Exception as e:
                    return f"Error deleting: {str(e)}"
            else:
                return f"Path not found: {path}"
    
    return None

def open_file_folder(command):
    command = command.lower()
    
    patterns = [
        r'open\s+(?:the\s+)?(?:folder\s+|file\s+)?["\']?(.+?)["\']?',
        r'read\s+(?:the\s+)?(?:folder\s+|file\s+)?["\']?(.+?)["\']?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            path = match.group(1).strip().strip('"').strip("'")
            
            if os.path.exists(path):
                full_path = path
            else:
                search_paths = [
                    os.path.join(os.path.expanduser('~'), 'Desktop', path),
                    os.path.join('C:\\', path),
                    os.path.join('D:\\', path),
                    os.path.join(os.path.expanduser('~'), 'Documents', path),
                ]
                full_path = None
                for sp in search_paths:
                    if os.path.exists(sp):
                        full_path = sp
                        break
            
            if full_path and os.path.exists(full_path):
                try:
                    if os.path.isdir(full_path):
                        os.startfile(full_path)
                        return f"Opening folder: {full_path}"
                    else:
                        os.startfile(full_path)
                        return f"Opening file: {full_path}"
                except Exception as e:
                    return f"Error opening: {str(e)}"
            else:
                return f"Path not found: {path}"
    
    return None

def read_file(command):
    command = command.lower()
    
    patterns = [
        r'read\s+(?:the\s+)?file\s+["\']?(.+?)["\']?',
        r'show\s+(?:the\s+)?content\s+(?:of\s+)?["\']?(.+?)["\']?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            path = match.group(1).strip().strip('"').strip("'")
            
            if os.path.exists(path) and os.path.isfile(path):
                full_path = path
            else:
                search_paths = [
                    os.path.join(os.path.expanduser('~'), 'Desktop', path),
                    os.path.join(os.path.expanduser('~'), 'Documents', path),
                    os.path.join('C:\\', path),
                    os.path.join('D:\\', path),
                ]
                full_path = None
                for sp in search_paths:
                    if os.path.exists(sp) and os.path.isfile(sp):
                        full_path = sp
                        break
            
            if full_path and os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(2000)
                    if len(content) > 0:
                        return f"Content of {os.path.basename(full_path)}:\n{content}"
                    else:
                        return f"File is empty: {full_path}"
                except Exception as e:
                    return f"Error reading: {str(e)}"
            else:
                return f"File not found: {path}"
    
    return None

def switch_input_mode(command):
    global input_mode
    command = command.lower()
    
    if 'voice' in command and ('mode' in command or 'input' in command or 'switch' in command or 'change' in command or 'enable' in command or 'use' in command):
        input_mode = "voice"
        return "Switched to voice input mode"
    
    if 'text' in command and ('mode' in command or 'input' in command or 'switch' in command or 'change' in command or 'enable' in command or 'use' in command):
        input_mode = "text"
        return "Switched to text input mode"
    
    if 'toggle' in command or 'switch' in command:
        input_mode = "voice" if input_mode == "text" else "text"
        return f"Switched to {input_mode} input mode"
    
    return None

def process_command(command):
    command = command.lower()
    
    if switch_input_mode(command):
        return switch_input_mode(command)
    
    if 'open' in command:
        result = open_app_or_website(command)
        if result:
            return result
    
    if 'close' in command or 'quit' in command or 'exit' in command:
        if 'close' in command and ('tab' in command or 'website' in command or 'page' in command or 'app' in command or any(b in command for b in ['chrome', 'firefox', 'edge', 'notepad', 'calculator', 'spotify', 'discord'])):
            result = close_app_or_tab(command)
            if result:
                return result
    
    if 'create' in command or 'make' in command:
        if 'folder' in command or 'file' in command:
            result = create_file_folder(command)
            if result:
                return result
    
    if 'delete' in command or 'remove' in command:
        if 'folder' in command or 'file' in command:
            result = delete_file_folder(command)
            if result:
                return result
    
    if 'open' in command and ('folder' in command or 'file' in command):
        result = open_file_folder(command)
        if result:
            return result
    
    if 'read' in command and 'file' in command:
        result = read_file(command)
        if result:
            return result
    
    if 'what is input mode' in command or 'check input mode' in command or 'input mode' in command:
        return f"Current input mode is: {input_mode}"
    
    if 'history' in command or 'past conversation' in command or 'previous chat' in command:
        if conversation_history:
            summary = f"You have {len(conversation_history)} past conversations.\n"
            for i, conv in enumerate(conversation_history[-5:]):
                summary += f"{i+1}. You: {conv['user'][:50]}... | JARVIS: {conv['jarvis'][:50]}...\n"
            return summary
        else:
            return "No conversation history found."
    
    return None

def get_jarvis_response(user_input):
    cmd_result = process_command(user_input)
    if cmd_result:
        return cmd_result
    
    if not client:
        return "I apologize, but I'm having trouble connecting to my brain. Please try again."
    
    try:
        history_text = ""
        if conversation_history:
            history_text = "Previous conversation context:\n"
            for conv in conversation_history[-5:]:
                history_text += f"User: {conv['user']}\nJARVIS: {conv['jarvis']}\n"
        
        system_prompt = f"""You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), Tony Stark's AI assistant from Marvel. 
You are helpful, witty, polite, and slightly formal. Keep responses conversational and concise, as they will be spoken aloud. 
You have access to system commands: open apps/websites, close apps/tabs, create/delete files and folders, read files, open files and folders.
You should use these capabilities when asked.
Never use markdown formatting or bullet points in your responses.
{history_text}"""
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
            max_tokens=512
        )
        
        response = chat_completion.choices[0].message.content
        add_to_history(user_input, response)
        return response
    except Exception as e:
        return f"I encountered an error. {str(e)}"

def print_art():
    art = f"""
{ORANGE}╔══════════════════════════════════════════════════════════════════════╗{RESET}
{ORANGE}║                                                                      ║{RESET}
{ORANGE}║      ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗                         ║{RESET}
{ORANGE}║      ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝                         ║{RESET}
{ORANGE}║      ██║███████║██████╔╝██║   ██║██║███████╗                         ║{RESET}
{ORANGE}║ ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║                         ║{RESET}
{ORANGE}║ ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║                         ║{RESET}
{ORANGE}║  ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝                         ║{RESET}
{ORANGE}║                                                                      ║{RESET}
{ORANGE}║                     J.A.R.V.I.S.                                     ║{RESET}
{ORANGE}║        Just A Rather Very Intelligent System                         ║{RESET}
{ORANGE}║                                                                      ║{RESET}
{ORANGE}╚══════════════════════════════════════════════════════════════════════╝{RESET}
"""
    for char in art:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.0005)
    print()

def main():
    global input_mode
    
    print_art()
    
    load_conversation_history()
    init_tts()
    init_groq()
    voice_available = init_voice()
    
    print(f"{BLUE}  Input modes: {GREEN}text{RESET} | {GREEN}voice{RESET}")
    print(f"{BLUE}  Current mode: {GREEN}{input_mode}{RESET}")
    if voice_available:
        if WHISPER_AVAILABLE and SD_AVAILABLE:
            print(f"{GREEN}  Voice input: Available (Whisper + sounddevice){RESET}")
        else:
            print(f"{GREEN}  Voice input: Available (SpeechRecognition){RESET}")
    else:
        print(f"{ORANGE}  Voice input: Not available{RESET}")
    
    response = "I am JARVIS. How may I assist you today?"
    print(f"\n{BLUE}  {response}{RESET}")
    speak(response)
    print(f"{BLUE}  Type 'exit' to quit.{RESET}\n")
    
    while True:
        try:
            if input_mode == "voice" and voice_available:
                print(f"{BLUE}  Say something... (or say 'switch to text'){RESET}")
                user_input = listen_voice()
                if user_input:
                    print(f"{GREEN}  You: {user_input}{RESET}")
                else:
                    print(f"{ORANGE}  Could not understand. Switching to text mode.{RESET}")
                    input_mode = "text"
                    continue
            else:
                user_input = input(f"{BLUE}  >> {RESET}").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'exit':
                response = "Going to standby mode. Good day, Sir."
                print(f"\n{BLUE}  JARVIS: {response}{RESET}")
                speak(response)
                break
            
            if user_input.lower() == 'mode':
                input_mode = "voice" if input_mode == "text" else "text"
                response = f"Switched to {input_mode} mode"
                print(f"{BLUE}  JARVIS: {response}{RESET}")
                speak(response)
                continue
            
            print(f"\n{BLUE}  [Processing...]{RESET}")
            response = get_jarvis_response(user_input)
            print(f"{BLUE}  JARVIS: {response}{RESET}")
            speak(response)
            print()
            
        except KeyboardInterrupt:
            is_shutting_down = True
            response = "Going to standby mode. Good day, Sir."
            print(f"\n\n{BLUE}  JARVIS: {response}{RESET}")
            break
        except EOFError:
            break

if __name__ == "__main__":
    main()
