import pandas as pd
import numpy as np

# ダミーデータの作成
data = {
    'Name': ['Taro', 'Jiro', 'Saburo', 'Shiro', 'Goro'],
    'Age': [28, 34, 29, 31, 24],
    'City': ['Tokyo', 'Osaka', 'Nagoya', 'Sapporo', 'Fukuoka']
}

# データフレームの作成
df = pd.DataFrame(data)

# データフレームをJSON形式に変換
df_json = df.to_json(orient='records')

with open('data.json', 'w') as file:
    file.write(df_json)