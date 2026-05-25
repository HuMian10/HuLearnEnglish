import sqlite3
conn = sqlite3.connect('english_lesson.db')
cursor = conn.cursor()

import pymysql
import pandas as pd
from pymysql.cursors import DictCursor
# 连接 MySQL 数据库
conn_prod = pymysql.connect(
    host='pxc-hzssyaotpmq5wt-pub.polarx.rds.aliyuncs.com',       # 主机地址
    port=3306,
    user='humian',   # 用户名
    password='XSbVZKGndT&+<M5$;9^S',  # 密码
    database='bfst',     # 数据库名
    cursorclass=DictCursor
)

# conn = pymysql.connect(
#     host='rm-wz910e8b286009p2wzo.mysql.rds.aliyuncs.com',       # 主机地址
#     port=3306,
#     user='root',   # 用户名
#     password='A123456a',  # 密码
#     database='bfst',     # 数据库名
#     ssl={}
# )
cursor_prod = conn_prod.cursor()

sql = 'select * from english_explain_dict where deleted=0'
df_words = pd.read_sql(sql, conn_prod)

import pandas as pd
import json
from tqdm import tqdm  # 显示进度条

def fast_insert_words(df_words, cursor, conn, batch_size=500):
    """
    优化版本 - 适合10万条数据
    预计耗时：从几分钟降到几秒钟
    """

    # 1. 一次性获取所有已存在的词（避免逐条查询）
    words_list = df_words['words'].tolist()
    placeholders = ','.join(['?'] * len(words_list))

    cursor.execute(f'SELECT word FROM words WHERE word IN ({placeholders})', words_list)
    existing_words = {row[0] for row in cursor.fetchall()}

    # 2. 过滤出需要插入的数据（pandas 向量化过滤）
    mask = ~df_words['words'].isin(existing_words)
    df_new = df_words[mask].copy()

    print(f"总数据: {len(df_words)}, 已存在: {len(existing_words)}, 需插入: {len(df_new)}")

    if len(df_new) == 0:
        print("没有新数据需要插入")
        return 0

    # 3. 向量化处理 meanings（避免循环）
    def process_meanings_fast(meanings_json):
        try:
            word_mean = json.loads(meanings_json)
            meanings = []
            for meaning in word_mean:
                pos = meaning.get('part', '')
                meaning_cn = ';'.join(meaning['means'])
                meanings.append({'pos': pos, 'meaning_cn': meaning_cn})
            return json.dumps(meanings, ensure_ascii=False)
        except:
            return json.dumps([])

    # 使用 apply 比 iterrows 快很多
    df_new['meanings_processed'] = df_new['words_mean'].apply(process_meanings_fast)

    # 4. 准备批量插入的数据
    data_to_insert = []
    columns = ['pronunciation', 'b_pronunciation', 'sentence', 'sentence_translation',
               'meanings_processed', 'word_plural', 'past_tense', 'past_participle',
               'comparative', 'superlative', 'third_person_singular', 'words']

    # 使用 to_numpy() 转换为数组，比 iterrows 快100倍
    values = df_new[columns].to_numpy()

    # 5. 分批插入
    total_inserted = 0
    for i in tqdm(range(0, len(values), batch_size), desc="插入数据"):
        batch = values[i:i+batch_size].tolist()
        cursor.executemany('''
            INSERT INTO words (
                phonetic_us, phonetic_uk, example_en, example_cn,
                meanings, plural, past_tense, past_participle,
                comparative, superlative, third_person, word
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', batch)
        conn.commit()
        total_inserted += len(batch)

    return total_inserted

# 使用
inserted = fast_insert_words(df_words, cursor, conn, 50)
print(f"成功插入 {inserted} 条数据")