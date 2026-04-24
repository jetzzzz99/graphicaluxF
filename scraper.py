import requests
from bs4 import BeautifulSoup
import jdatetime
import pytz
from datetime import datetime, timedelta
import time
import os

# تنظیمات زمان
tehran_tz = pytz.timezone('Asia/Tehran')

def get_media_tag(msg_div):
    # تشخیص انواع رسانه
    has_photo = msg_div.select_one('.tgme_widget_message_photo_wrap') is not None
    has_video = msg_div.select_one('.tgme_widget_message_video') is not None
    has_poll = msg_div.select_one('.tgme_widget_message_poll') is not None
    has_doc = msg_div.select_one('.tgme_widget_message_document') is not None
    has_gif = msg_div.select_one('.videogif') is not None

    if has_photo and has_video: return "[عکس و ویدئو]"
    if has_gif: return "[گیف]"
    if has_photo: return "[عکس]"
    if has_video: return "[ویدئو]"
    if has_poll: return "[نظرسنجی]"
    if has_doc: return "[فایل]"
    return ""

def format_text(text):
    if not text: return ""
    rlm = "\u200F" # کاراکتر برای درست کردن چیدمان راست‌به‌چپ
    lines = text.strip().split('\n')
    return "\n".join([f"{rlm}{line}" for line in lines])

def main():
    if not os.path.exists('channels.txt'):
        print("فایل channels.txt پیدا نشد.")
        return

    with open('channels.txt', 'r', encoding='utf-8') as f:
        channels = [line.strip().replace('@', '') for line in f if line.strip()]

    all_posts = []
    now_utc = datetime.now(pytz.utc)
    cutoff_time = now_utc - timedelta(hours=24) # فیلتر ۲۴ ساعت

    for channel in channels:
        print(f"در حال استخراج: {channel}...")
        url = f"https://t.me/s/{channel}"
        try:
            res = requests.get(url, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            messages = soup.select('.tgme_widget_message')
            
            for msg in messages:
                # ۱. استخراج زمان و چک کردن فیلتر ۲۴ ساعت
                time_tag = msg.select_one('time')
                if not time_tag or not time_tag.has_attr('datetime'):
                    continue
                
                post_dt_utc = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                
                if post_dt_utc < cutoff_time:
                    continue # اگر قدیمی‌تر از ۲۴ ساعت بود نادیده بگیر

                # ۲. استخراج متن
                text_div = msg.select_one('.tgme_widget_message_text')
                if text_div:
                    for br in text_div.find_all("br"): br.replace_with("\n")
                    post_text = text_div.get_text()
                else:
                    post_text = ""

                # ۳. استخراج تگ رسانه
                media_tag = get_media_tag(msg)

                # ۴. ذخیره در لیست (حتی اگر متن نداشته باشد ولی رسانه داشته باشد)
                if post_text or media_tag:
                    # تبدیل به زمان تهران برای نمایش
                    dt_tehran = post_dt_utc.astimezone(tehran_tz)
                    shamsi_date = jdatetime.datetime.fromgregorian(datetime=dt_tehran)
                    
                    all_posts.append({
                        'timestamp': post_dt_utc, # برای مرتب‌سازی
                        'channel': channel,
                        'media': media_tag,
                        'text': post_text,
                        'time_str': dt_tehran.strftime('%H:%M'),
                        'date_str': shamsi_date.strftime('%Y/%m/%d')
                    })

        except Exception as e:
            print(f"خطا در کانال {channel}: {e}")
        
        time.sleep(1.5)

    # مرتب‌سازی کل پست‌ها بر اساس زمان (جدیدترین در ابتدا)
    all_posts.sort(key=lambda x: x['timestamp'], reverse=True)

    # ساخت فایل خروجی
    output_content = ""
    for post in all_posts:
        entry = f"src :@{post['channel']}\n"
        if post['media']:
            entry += f"{post['media']}\n"
        if post['text']:
            entry += f"{format_text(post['text'])}\n"
        
        entry += f"{post['time_str']}\n"
        entry += f"{post['date_str']}\n"
        
        output_content += entry + "\n\n\n\n" # فاصله ۳ خطی

    with open('output.txt', 'w', encoding='utf-8') as f:
        f.write(output_content.strip())
    
    print(f"عملیات موفقیت‌آمیز بود. {len(all_posts)} پست استخراج شد.")

if __name__ == "__main__":
    main()
