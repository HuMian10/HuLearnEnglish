import os
import json
import time
import requests
import feedparser
import schedule

from newspaper import Article
from jinja2 import Template
from datetime import datetime

RSS_FEEDS = [
    "https://feeds.reuters.com/reuters/topNews",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
]

OUTPUT_DIR = "news_site"
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
ARTICLE_DIR = os.path.join(OUTPUT_DIR, "articles")

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(ARTICLE_DIR, exist_ok=True)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>

    <style>
        body {
            background: #111;
            color: #eee;
            font-family: Arial;
            max-width: 900px;
            margin: auto;
            padding: 30px;
            line-height: 1.8;
        }

        img {
            width: 100%;
            border-radius: 10px;
        }

        h1 {
            font-size: 42px;
        }

        .meta {
            color: #aaa;
            margin-bottom: 20px;
        }

        a {
            color: #6ab0ff;
        }
    </style>
</head>

<body>
    <a href="../index.html">← Back</a>

    <h1>{{ title }}</h1>

    <div class="meta">
        {{ publish_date }}
    </div>

    {% if image %}
    <img src="../images/{{ image }}">
    {% endif %}

    <div>
        {{ content }}
    </div>
</body>
</html>
"""

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Daily News</title>

    <style>
        body {
            background: #111;
            color: #eee;
            font-family: Arial;
            max-width: 1000px;
            margin: auto;
            padding: 30px;
        }

        .card {
            background: #1c1c1c;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 12px;
        }

        .card img {
            width: 100%;
            border-radius: 10px;
        }

        a {
            color: white;
            text-decoration: none;
        }

        h2 {
            margin-top: 10px;
        }
    </style>
</head>

<body>
    <h1>Daily English News</h1>

    {% for item in items %}
    <div class="card">

        {% if item.image %}
        <img src="images/{{ item.image }}">
        {% endif %}

        <h2>
            <a href="articles/{{ item.file }}">
                {{ item.title }}
            </a>
        </h2>

        <p>{{ item.summary }}</p>

    </div>
    {% endfor %}
</body>
</html>
"""


def download_image(url, filename):
    try:
        r = requests.get(url, timeout=10)

        path = os.path.join(IMAGE_DIR, filename)

        with open(path, "wb") as f:
            f.write(r.content)

        return filename

    except:
        return None


def process_article(url):

    article = Article(url)

    article.download()
    article.parse()

    title = article.title
    text = article.text
    top_image = article.top_image

    filename = str(int(time.time())) + ".html"

    image_name = None

    if top_image:
        image_name = filename.replace(".html", ".jpg")
        download_image(top_image, image_name)

    html_content = text.replace("\n", "<br><br>")

    html = Template(HTML_TEMPLATE).render(
        title=title,
        publish_date=str(datetime.now()),
        image=image_name,
        content=html_content
    )

    with open(os.path.join(ARTICLE_DIR, filename), "w", encoding="utf-8") as f:
        f.write(html)

    return {
        "title": title,
        "summary": text[:180] + "...",
        "file": filename,
        "image": image_name
    }


def build_news():

    items = []

    MAX_NEWS = 20

    count = 0

    for rss in RSS_FEEDS:

        feed = feedparser.parse(rss)

        for entry in feed.entries:

            if count >= MAX_NEWS:
                break

            try:
                print("Processing:", entry.link)

                item = process_article(entry.link)

                items.append(item)

                count += 1

            except Exception as e:
                print(e)

        if count >= MAX_NEWS:
            break

    html = Template(INDEX_TEMPLATE).render(items=items)

    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    print("DONE")


def job():
    build_news()


schedule.every().day.at("08:00").do(job)

job()

while True:
    schedule.run_pending()
    time.sleep(60)