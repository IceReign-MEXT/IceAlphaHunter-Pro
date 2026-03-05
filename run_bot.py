import os
import asyncio
import multiprocessing
from dotenv import load_dotenv

load_dotenv()

def run_telegram_bot():
    """Run the Telegram bot in separate process"""
    os.system("python main.py")

def run_web_server():
    """Run web server for UptimeRobot"""
    os.system("python web_server.py")

if __name__ == "__main__":
    print("🚀 Starting IceAlphaHunter Pro...")
    print("🤖 Telegram Bot: Starting...")
    print("🌐 Web Server: Starting...")
    
    # Run both in parallel
    p1 = multiprocessing.Process(target=run_telegram_bot)
    p2 = multiprocessing.Process(target=run_web_server)
    
    p1.start()
    p2.start()
    
    p1.join()
    p2.join()
