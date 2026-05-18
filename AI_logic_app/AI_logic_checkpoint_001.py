import speech_recognition as sr
import pyttsx3
import psutil
import time
import os
from difflib import SequenceMatcher
import pyjokes
import datetime
from difflib import SequenceMatcher
import pywhatkit
import pyautogui as py
import json
import random
import sys
import wikipedia
import pygetwindow as gw
import subprocess
from googlesearch import search
import itertools
import requests
from bs4 import BeautifulSoup
from newspaper import Article
from django.conf import settings
from .models import save_data_in_db

inp_lang = 'en-in'


def speak(rec_input, rate = 125):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for voice in voices :
        if voice.name == 'Microsoft Zira Desktop - English (United States)':
            engine.setProperty('voice', voice.id)
    engine.setProperty("rate",rate)
    engine.setProperty("volume", 1.0)
    engine.say(rec_input)
    engine.runAndWait()

def takecommandexceptional(a):
    r = sr.Recognizer()

    with sr.Microphone() as source:
        print ("listening...")
        audio = r.listen(source,  phrase_time_limit=  a)

    try:
        print("recognizing ...")
        query = r.recognize_google(audio, language = 'en-in')
        query = query.lower()
        
        mistaken = ['qb', 'cubi', 'cubie', 'kibi', 'kooby', 'cooby', 'koobie', 'cubye', 'cuban', 'kirban', 'hey google', 'killbe', 'killby', 'cubic','cubyc']

        for i in mistaken:
            if i in query:
                query = query.replace(i,'hey cuby')
        print(query)

    except Exception as e:
        print(e)
        return ""
    return query

def startup():
    while True:
        command = takecommandexceptional(5)
        if 'hey' in command:
            speak('hai, welcome back')
            hour =  datetime.datetime.now().hour
            if hour >=6 and hour <12 :
                speak('good morning!')
            elif hour >=12 and hour <15:
                speak("good afternoon!")
            elif hour >= 15 and hour <19:
                speak("good evening !")
            else :
                speak("good night!")
            main()
        elif 'turn off' in command:
            shut_down()
        else:
            continue

def shut_down():
    speak("i am, available at any time to assist you; please feel free to call me if you require any help!. thankyou ")
    sys.exit()

def chatbot(query):
    file_path = os.path.join(settings.BASE_DIR, 'AI_logic_app', 'data', 'cuby.json')

    with open(file_path) as file:        
        intents = json.load(file)["intents"]
    matched_intents = []
    for intent in intents:
        if query in intent["patterns"]:
            matched_intents.append(intent)

    if matched_intents:
        selected_intent = random.choice(matched_intents)
        response = random.choice(selected_intent["responses"])
        speak(response)
        return response
    else:
        ""

def cur_time():
    Time =  datetime.datetime.now().strftime("%H:%M:%S")
    speak("the current time is")
    speak(Time)

def date():
    speak("the current date is")
    year = int(datetime.datetime.now().year)
    month = int(datetime.datetime.now().month)
    date = int(datetime.datetime.now().day)
    speak(date), speak(month), speak(year)

def long_define(query):
    try:
        wikipedia.set_lang("en")
        page_title = wikipedia.search(query)[0]     
        page_summary = wikipedia.summary(page_title)
        open_notepad()
        py.write(page_summary)
    except Exception as e:
        print(e)
        len_type = len(str(e).splitlines())
        speak(f"There are {len_type} types of {query}.")
        speak("Given information is not enough. please provide some more information to proceed")
def short_define(query):
    try:
        query = pywhatkit.info(query, 5, True)
        open_notepad()
        py.write(query)
    except Exception as e:
        print(e)
        len_type = len(str(e).splitlines())
        speak(f"There are {len_type} types of {query}.")
        speak("Given information is not enough. please provide some more information to proceed")

def speech_define(query):
    try:
        quest = pywhatkit.info(query, 2, True)
        speak(quest)
    except Exception as e:
        print(e)
        len_type = len(str(e).splitlines())
        speak(f"There are {len_type} types of {query}.")
        speak("Given information is not enough. please provide some more information to proceed")

def open_notepad():
    subprocess.run(['start', '',"C:/ProgramData/Microsoft/Windows/Start Menu/Programs/Accessories/Notepad.lnk"], shell = True)
    time.sleep(2)
    windows = gw.getWindowsWithTitle("Notepad")[0]
    windows.restore()
    notepad = gw.getWindowsWithTitle("Notepad")[0]
    notepad.maximize()

def playsongs(query):
    def matchings(a,b):
        return SequenceMatcher(None , a,b).ratio()
    song_path = os.path.join(settings.BASE_DIR, 'AI_logic_app', 'data','songs')
    song = query

    matching_song = None
    song_count = 0

    songs = os.listdir(song_path)
    for file in songs:
        bestest = matchings(song,file)
        if bestest> song_count:
            matching_song = file
            song_count = bestest
    path = os.path.join(song_path,matching_song)
    os.startfile(path)

def cpu():
    usage = str(psutil.cpu_percent())
    speak("CPU is "+usage)
    battery = psutil.sensors_battery()
    speak("battery is ")
    speak((battery.percent, "percentage"))

def screenshot():
    img = py.screenshot()
    Time =  datetime.datetime.now().strftime("%H.%M.%S")
    path = os.path.join(settings.BASE_DIR, 'AI_logic_app', 'data','screenshots')
    img_path = (f'ss {Time}.png')
    full_path = os.path.join(path, img_path)
    img.save(full_path)

def minimizer():
    try:
        all_windows = gw.getAllWindows()
        all_windows[1].minimize()
    except Exception as e:
        speak("could not minimize the window")

def writter():
    while True:
        speak('say...')
        command = takecommandexceptional(10)
        if 'exit writer' in command:
            speak('leaving writer mode...')
            main()
        elif ' press space' in command:
            py.press('spacebar')
        elif 'colon' in command:
            py.press(':')
        elif 'semicolon' in command:
            py.press(';')
        elif 'open parenthesis' in command:
            py.press("(")
        elif 'close parenthesis' in command:
            py.press(")")
        elif 'parenthesis' in command:
            py.press("(")
            py.press(")")
        elif 'single quotes' in command:
            py.press("'")
        elif 'double quotes' in command:
            py.press('"')
        elif 'triple quotes' in command:
            py.write("'''")
        elif 'press enter' in command:
            py.press('enter')
        elif 'caps lock' in command:
            py.press('capslock')
        elif 'tab' in command:
            py.press('Tab')
        else:
            py.write(command)
def controlpannel():
    subprocess.run(['start', '',"C:/Users/lenovo/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/System Tools/Control Panel.lnk"], shell = True)
    time.sleep(3)
    windows = gw.getWindowsWithTitle("Control Panel")[0]
    windows.restore()
    c_panel = gw.getWindowsWithTitle("Control Panel")[0]
    c_panel.maximize()
    while True:
        search = takecommandexceptional(5)
        if 'exit con' in search:
            speak('leaving contol pannel')
            py.click(1350, 20)
            main()
        elif 'search' in search:
            time.sleep(3)
            py.click(1300, 40)
            search= search.lower()
            search = search.replace('search','')
            py.write(search)
            time.sleep(2)
            py.click(200, 85)
            time.sleep(5)
        elif 'go back' in search:
            py.click(10, 50)
        elif 'go front' in search:
            py.click(40, 50)

def thispc():
    py.click(370, 800)
    windows = gw.getWindowsWithTitle("This PC")[0]
    windows.restore()
    panel = gw.getWindowsWithTitle("This PC")[0]
    panel.maximize()
    while True:
        command = takecommandexceptional(4)
        command = command.lower()
        if 'exit this pc' in command:
            py.click(1400, 20)
            main()
        elif 'minimize' in command:
            py.click(1300,20)
            main()
        elif 'search' in command:
            py.click(1300, 70)
            time.sleep(3)
            while True:
                command = takecommandexceptional(5)
                if 'exit search' in command:
                    thispc()
                else:
                    py.write(command)
                    time.sleep(3)
                    py.press('enter')
                    thispc()
        elif 'quick access' in command:
            py.click(80, 120)
        elif 'this pc' in command:
            py.click(80, 270)
        elif '3d objects' in command:
            py.click(80, 290)
        elif 'desktop' in command:
            py.click(80, 310)
        elif 'documents' in command:
            py.click(80, 330)
        elif 'downloads' in command:
            py.click(80, 360)
        elif 'music' in command:
            py.click(80, 385)
        elif 'pictures' in command:
            py.click(80, 410)
        elif 'videos' in command:
            py.click(80, 435)
        elif 'disc c' in command:
            py.click(80, 460)
        elif 'disc e'in command:
            py.click(80, 485)
        elif 'disc f' in command:
            py.click(80, 510)
        elif 'vengatesh' in command:
            py.click(80, 460)
        elif 'media' in command:
            py.click(80, 485)
        elif 'studies' in command:
            py.click(80, 510)
        elif 'network' in command:
            py.click(80, 535)
        elif 'press' in command:
            py.click(500,600)
            query = command.replace('press ','')
            query = list(query)
            for letter in query:
                py.press(query)
        elif 'enter'  in command:
            py.press('enter')
        elif 'go back' in command:
            py.click(10, 60)
        elif 'go front' in command:
            py.click(50, 60)

def numberselecting():
    while True:
        py.click(385, 120)
        py.click(385, 120)
        speak("tell me the person's name that you want to chat...")
        command = takecommandexceptional(7)
        command = command.lower()
        if 'exit whatsapp' in command:
            speak('leaving whatsapp')
            py.click(1230, 20)
            main()
        elif 'status' in command:
            py.click(10, 150)
            time.sleep(3)
            status()
        else:
            py.write(command)
            time.sleep(5)
            py.click(200,200)
            chat()

def chat():
    while True:
        speak("waiting for you'r message")
        command = takecommandexceptional(8)
        command = command.lower()
        if 'exit whatsapp' in command:
            speak('leaving whatsapp')
            py.click(1230, 20)
            main()
        elif 'status' in command:
            py.click(10, 150)
            time.sleep(3)
            status()
        elif 'change number' in command:
            numberselecting()
        else:
            py.write(command)
            time.sleep(3)
            py.press('enter')

def whatsapp():
    speak('you are within the whatsapp..')
    while True:
        command = takecommandexceptional(5)
        if 'status' in command:
            py.click(10, 150)
            time.sleep(3)
            status()
        elif 'chat' in command:
            numberselecting()
        elif 'exit whatsapp' in command:
            speak('leaving whatsapp')
            py.click(1230,20)
            main()

def status():
    while True:
        status = takecommandexceptional(4)
        if 'exit whatsapp' in status:
            speak('leaving whatsapp...')
            py.click(1230, 20)
            main()
        elif 'chat' in status:
            py.click(10, 80)
            numberselecting()
        elif 'play' in status:
            py.click(200, 230)
            time.sleep(5)
            while True:
                status = takecommandexceptional(4)
                if 'stop' in status:
                    py.click(10, 50)
                    time.sleep(2)
                    break
        elif 'close status' in status:
            py.click(10, 80)

class GenAI:
    def google_search(self,query):
        urls = []
        search_results = list(itertools.islice(search(query), 5))

        for i, url in enumerate(search_results):
            if "https://www.programiz.com" in url:
                urls.append(url)
                urls[0] = url
            elif "https://en.wikipedia." in url:
                urls.append(url)
                urls[0] = url
            elif "https://www.geeksforgeeks" in url:
                continue
            else:
                urls.append(url)
        GenAI.get_main_content(urls,query)


    def get_main_content(urls, query):
        url = urls[0]
        try:
            article = Article(url)
            article.download()
            article.parse()
            main_content = article.text
            main_url = url
            GenAI.extract_code(main_url, main_content, query)
        except Exception as e:
            print("Forbidden Request Error: ")
            speak("Forbidden Request Noticed!")
            main()

    def extract_code(main_url, main_content, query):
        response = requests.get(main_url)
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            code_blocks = soup.find_all('code')
            GenAI.print_results(main_content, query, code_blocks, main_url)
        else:
            pass

    def print_results(main_content, query, code_blocks, main_url):
        main_content = main_content.splitlines()
        global main_content_answer 
        global code_snippet
        global main_content_words
        main_content_answer =  main_content[:5]
        #main_content_words = main_content_for_speak[:30]
        if code_blocks:
            code_snippet = code_blocks

        if 'write'and'long' in query:
            open_notepad()
            for line in main_content[:15]:
                py.write(line)
                py.press('enter')
            py.write("Reference Link : ")
            py.write(main_url)
        elif 'write'and 'short' in query:
            open_notepad()
            for line in main_content[:5]:
                py.write(line)
                py.press('enter')
            py.write("Reference Link : ")
            py.write(main_url)
        elif 'write' and 'program' and 'explain' in query:
            main_content = '\n'.join(main_content)
            open_notepad()
        # Iterate through code blocks to find the relevant code
            for index, code_block in enumerate(code_blocks, start=1):
                code_content = code_block.get_text()
                py.write("Code Snippet ")
                py.write(": ")
                py.press('enter')
                py.write(code_content)
                py.press('enter')
            py.write(main_content)
            py.press('enter')
            py.write("Reference Link :")
            py.write( main_url)
        
        elif 'define' in query:
            speak(main_content[:3], 150)
        elif 'what' in query:
            speak(main_content[:3])
        elif 'tell me about' in query:
            speak(main_content[:3])  
        elif 'write' in query:
            open_notepad()
            for line in main_content[:5]:
                py.write(line)
                py.press('enter')
            py.write("Reference Link : ")
            py.write(main_url)
        elif code_blocks:
            open_notepad()
        # Iterate through code blocks to find the relevant code
            for index, code_block in enumerate(code_blocks, start=1):
                code_content = code_block.get_text()
                py.write("Code Snippet ")
                py.write(": ")
                py.press('enter')
                py.write(code_content)
                py.press('enter')
                ## write function need to be invoked
            py.write("Reference Link :")
            py.write( main_url)
        #elif main_content:
        #   open_notepad()
        #    for line in main_content[:5]:
        #        py.write(line)
        #        py.press('enter')
        #    py.write("Reference Link : ")
        #    py.write(main_url)
        else:
            speak(main_content[:4])
        return main_content_answer
    
def main():
    speak("how can i assist you today?")
    while True:
        query = takecommandexceptional(20)
        query =query.lower()
        chatbot(query) 
        query_1 = query
        search_obj = GenAI()
                
        if 'turn off' in query:
            shut_down()
        elif 'activate offline' in query:
            speak('Please feel free to call me if you require any help!')
            startup()
        elif 'time' in query:
            cur_time(), date()
        elif 'date' in query:
            date(), cur_time()

        elif 'make a search' in query:
            search = query.replace('make a search','')
            pywhatkit.search(search)
        elif 'log out my pc' in query:
            speak('warning! it will lock your system. please confirm the command, say yes to continue')
            lock = takecommandexceptional(5)
            if 'yes' in lock:
                os.system('C:\\Windows\\System32\\rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
            else:
                continue
        elif 'shut down my pc' in query:
            speak('warning! it will shutdown your system. please confirm the command, say yes to continue')
            lock = takecommandexceptional(5)
            if 'yes' in lock:
                os.system('C:\\Windows\\System32\\shutdown.exe /s /t 0')
            else:
                continue
        elif 'restart my pc' in query:
            speak('warning! it will restart your system. please confirm the command, say yes to continue')
            lock = takecommandexceptional(5)
            if 'yes' in lock:
                os.system('C:\\Windows\\System32\\shutdown.exe /r /t 0')
            else:
                continue
        elif 'play offline songs' in query :
            file_path = os.path.join(settings.BASE_DIR, 'AI_logic_app', 'data','songs')
            songs_dir = file_path
            songs = os.listdir(songs_dir)
            os.startfile(os.path.join(songs_dir,songs[0]))
        elif 'play' in query:
            query = query.lower()
            query = query.replace('play','')
            playsongs(query)
        elif 'remember that' in query:
            query = query.replace('remember that','')
            speak("you said me to remember"+query)
            file_path = os.path.join(settings.BASE_DIR, 'AI_logic_app', 'data','remember','data.txt')
            remember = open(file_path,'w')
            remember.write(query)
            remember.close()
        elif 'anything to remember' in query:
            file_path = os.path.join(settings.BASE_DIR, 'AI_logic_app', 'data','remember','data.txt')
            remember = open(file_path,'r')
            speak("you said me to remember that" +remember.read())
        elif 'technical joke' in query:
            speak(pyjokes.get_joke(category='all'))
        elif 'cpu' in query:
            cpu()
        elif 'battery' in query:
            cpu()
        elif 'screenshot' in query:
            screenshot()  
            speak("done!")
        elif 'minimise' in query:
            minimizer()
        elif 'maximize' in query:
            py.hotkey("win","up")
        elif 'youtube' in query:
            try:
                query = query.replace('youtube','')
                pywhatkit.playonyt(query)
            except Exception as e:
                speak("could not play the video on Youtube")
        elif 'settings' in query:
            controlpannel()
        elif 'this pc' in query:
            thispc()
        elif 'select all' in query:
            py.hotkey('ctrl', 'a')
        elif 'save with custom name' in query:
            py.hotkey('ctrl', 's')
        elif 'save' in query:
            py.hotkey('ctrl', 's')
            time.sleep(2)
            py.write(query_1)
            time.sleep(2)
            py.press("enter")
        elif 'press' in query:
            query = query.lower()
            query = query.replace('press ','')
            if 'enter' in query:
                py.press('enter')
            query = list(query)
            for letter in query:
                py.press(letter)
        elif 'activate write' in query:
            writter()
        elif 'go to' in query:
            py.click(200,800)
            time.sleep(6)
            query = query.replace('go to','')
            py.write(query)
            time.sleep(3)
            py.press('enter')
        elif 'pause' in query:
            py.press('space')
        elif 'whatsapp' in query:
            command = query
            py.click(200, 950)
            time.sleep(3)
            py.write('whatsapp')
            time.sleep(4)
            py.press('enter')
            time.sleep(3)
            whatsapp()
        elif "close it" in query:
            py.hotkey("alt", "f4")
        elif query:
            search_obj.google_search(query)
            save_data_in_db(query, main_content_answer)
            #print(main_content_words)
