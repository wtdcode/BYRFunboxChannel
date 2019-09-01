import requests
import json
import pyquery
import telegram
import tempfile
import time

with open("./config.json") as f:
    config = json.load(f)

with open("./db.json") as f:
    db = json.load(f)

website_url = "https://bt.byr.cn"
funbox_url = f"{website_url}/log.php?action=funbox"

bot = telegram.Bot(token=config['bot']['token'])

def download_tmp_image(url, fp:tempfile.TemporaryFile):
    resp = requests.get(url, headers=config['headers'])
    fp.write(resp.content)

def get_funbox_metadata(page = 0):
    full_url = f"{funbox_url}&page={page}"
    result = []
    resp = requests.get(full_url, headers=config['headers'])
    d = pyquery.PyQuery(resp.text)
    tables = d("#outer > table")
    for table in tables:
        children = table.getchildren()
        if len(children) != 3:
            continue
        title_tr = children[0]
        datetime_tr = children[1]
        content_tr = children[2]
        title = title_tr.getchildren()[1].text_content()
        datetime = datetime_tr.getchildren()[1].getchildren()[0].attrib['title']
        contents = []
        for e in content_tr.getchildren()[1].getchildren():
            if e.tag == "img":
                alt = e.attrib['alt']
                src = f"{website_url}/{e.attrib['src']}"
                if src.endswith(".thumb.jpg"):
                    src = src.replace(".thumb.jpg", "")
                contents.append({
                    "alt": alt,
                    "src": src
                })
        result.append({
            "title" : title,
            "datetime": datetime,
            "contents": contents
        })
    return result
                
r = get_funbox_metadata()
for box in r[::-1]:
    if box['datetime'] in db and db[box['datetime']]['status'] == 0:
        db[box['datetime']] = {
            "status" : 0,
            "index" : 0,
            "box": box
        }
        continue
    try:
        bot.send_message(chat_id=config['telegram']['chat_id'], text=f"time:{box['datetime']}\ntitle:{box['title']}")
        for index, content in enumerate(box['contents']):
            with tempfile.TemporaryFile() as f:
                download_tmp_image(content['src'], f)
                f.seek(0)
                if content['src'].endswith("gif"):
                    bot.send_document(chat_id=config['telegram']['chat_id'], document=f, filename="1.gif")
                else:
                    bot.send_photo(chat_id=config['telegram']['chat_id'], photo=f) # omit alt intentionally.
                time.sleep(3)
        db[box['datetime']] = box
    except telegram.error.TelegramError:
        db[box['datetime']] = {
            'status': -1,
            'index': 0,
            "box": box
        }
        continue

with open("./db.json", "w+") as f:
    json.dump(db, f, indent=4)
    
