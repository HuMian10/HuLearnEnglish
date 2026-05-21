import requests
from datetime import datetime
from bs4 import BeautifulSoup
import re

# 获取首条文章的链接
def extract_snumber_from_url(base_url):
    try:
        response = requests.get(base_url)
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')
        index = str(soup).find('initialArticles')
        text = str(soup)[index: index + 50]
        print(text)
        pattern = r'\\"Id\\":(\d+)'
        match = re.search(pattern, text)

        if match:
            id_value = match.group(1)
            print(f"找到 ID: {id_value}")
            return id_value  # 找到后返回 ID
        else:
            print("未在页面中找到匹配的 ID。")
            return None
    except Exception as e:
        print(f"error: {e}")
    return None
print(extract_snumber_from_url('https://www.aibase.com/zh/news/'))

def extract_news(snumber):
    url = 'https://mcpapi.aibase.cn/api/aiInfo/detail'
    params = {
        't': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'langType': 'en',
        'id': snumber,
        'type': 'news',
    }
    response = requests.get(url, params=params)
    result = response.json()
    title = result['data']['title']
    photo_url = result['data']['thumb']
    content = result['data']['summary']
    create_time = result['data']['createTime']
    return {
        'title': title,
        'content': content,
        'photo_url': photo_url,
        'create_time': create_time
    }

def extract_last_news(snumber):
    results = []
    for id in range(snumber - 20, snumber):
        try:
            result = extract_news(id)
            results.append(result)
        except Exception as e:
            print(e)
    return results