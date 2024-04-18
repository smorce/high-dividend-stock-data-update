# --------------------------------------------------
# S&P500の銘柄をリストアップする
# --------------------------------------------------
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import requests
import json
import os

pd.set_option('display.max_columns', 200)

# --------------------------------------------------
# ヘルパー関数
# --------------------------------------------------
def extract_braces_content(text):
    """余計な出力がくる場合があるのでJSONデータだけを取り出す"""
    # 文字列から最初の '{' を探す
    start_index = text.find('{')
    # '{' 以降の文字列を抽出
    remaining_text = text[start_index:]
    # 抽出した文字列から最後の '}' の位置を探す
    end_index = remaining_text.rfind('}')
    # '{' から最後の '}' までの文字列を返す
    return remaining_text[:end_index+1]


def truncate_float_cols(df, n_decimals=2):
    """小数点第二位で切り捨て(三桁目を捨てる)"""
    float_cols = df.select_dtypes(include=['float']).columns
    df[float_cols] = np.floor(df[float_cols] * 10**n_decimals) / 10**n_decimals
    return df



# URL を指定
url = "https://stockanalysis.com/list/sp-500-stocks/"

# Web ページを取得
response = requests.get(url)

# BeautifulSoup オブジェクトを作成
soup = BeautifulSoup(response.content, 'html.parser')

# テーブルを取得
table = soup.find('table')

# テーブルのヘッダーとデータを取得
headers = [th.text for th in table.find('thead').find_all('th')]
data = [[td.text for td in row.find_all('td')] for row in table.find('tbody').find_all('tr')]

# Pandas DataFrame を作成
df_sp500 = pd.DataFrame(data, columns=headers)
# カラム名のスペースを消して半角にする
df_sp500.columns = df_sp500.columns.str.lower().str.replace(' ', '')
df_sp500 = df_sp500[["symbol","companyname","stockprice"]]
# , を消す
df_sp500["stockprice"] = df_sp500["stockprice"].str.replace(",", "")
SP500 = df_sp500.symbol.to_list()


# --------------------------------------------------
# 配当貴族(25年以上にわたって毎年増配を続けている企業)の銘柄をリストアップする
# --------------------------------------------------
# 連続増配株は取るのが難しいので、配当貴族かどうかチェックする
# 配当貴族とは、S&P500指数の構成銘柄で、25年以上にわたって毎年増配を続けている企業です。これは、すべての配当貴族のリストです。

# URL を指定
url = "https://stockanalysis.com/list/dividend-aristocrats/"

# Web ページを取得
response = requests.get(url)

# BeautifulSoup オブジェクトを作成
soup = BeautifulSoup(response.content, 'html.parser')

# テーブルを取得
table = soup.find('table')

# テーブルのヘッダーとデータを取得
headers = [th.text for th in table.find('thead').find_all('th')]
data = [[td.text for td in row.find_all('td')] for row in table.find('tbody').find_all('tr')]

# Pandas DataFrame を作成
df_aristocrat = pd.DataFrame(data, columns=headers)
df_aristocrat.columns = df_aristocrat.columns.str.lower().str.replace(' ', '')
df_aristocrat = df_aristocrat[["symbol","years"]]


# --------------------------------------------------
# データフレームをマージする
# --------------------------------------------------
df_Haiku = pd.merge(df_sp500, df_aristocrat, how='left', on='symbol')
# 配当貴族カラムを追加する
# years が連続増配年数, aristocrat_flag = 1 が配当貴族銘柄
df_Haiku['aristocrat_flag'] = df_Haiku['years'].notnull().astype(int)
# 欠損値をゼロで穴埋め
df_Haiku['years']           = df_Haiku['years'].fillna(0)
df_Haiku['aristocrat_flag'] = df_Haiku['aristocrat_flag'].fillna(0)

print(df_Haiku.aristocrat_flag.value_counts())



# --------------------------------------------------
# 各データを集計する
# 四半期のデータを取得して最新のやつだけ使う
# --------------------------------------------------
from yahooquery import Ticker
sp500 = Ticker(SP500)

df_summary = pd.DataFrame(sp500.summary_detail).T
df_summary.index.name = "symbol"

# marketCap：時価総額
# previousClose：前日終値。株価はこれで。→ なし
# dividendRate：1株当りの配当金
# dividendYield：配当利回り
# exDividendDate：次回配当金の権利確定日
# payoutRatio：配当性向（利益に対する配当金の割合）
# fiveYearAvgDividendYield：過去5年間の平均配当利回り
df_summary = df_summary[["marketCap","dividendRate","dividendYield","exDividendDate","payoutRatio","fiveYearAvgDividendYield"]]
df_summary = df_summary.reset_index()


df_income = pd.DataFrame(sp500.income_statement(frequency='q',trailing=False))  # 四半期
# TotalRevenue: 売上高
df_income = df_income[["TotalRevenue"]]
df_income = df_income.reset_index()
# 最新のレコードに絞る
df_income = df_income.drop_duplicates(subset=['symbol'], keep='last')


df_balance = pd.DataFrame(sp500.balance_sheet(frequency='q',trailing=False))
# 利益余剰金(繰延留保益): RetainedEarnings
# 株主資本(純資産, 自己資本): CapitalStock
# 総資産： TotalAssets
# 有価証券: AvailableForSaleSecurities　←　欠損が多いので怪しいため除外
# 純有利子負債: NetDebt
df_balance = df_balance[["RetainedEarnings","CapitalStock","TotalAssets","NetDebt"]]
df_balance = df_balance.reset_index()
# 最新のレコードに絞る
df_balance = df_balance.drop_duplicates(subset=['symbol'], keep='last')


df_cash_flow = pd.DataFrame(sp500.cash_flow(frequency='q',trailing=False))
# フリーキャッシュフロー  FreeCashFlow
# 営業キャッシュフロー  　OperatingCashFlow
# 財務キャッシュフロー  　FinancingCashFlow
# 投資キャッシュフロー　  InvestingCashFlow
df_cash_flow = df_cash_flow[["FreeCashFlow", "OperatingCashFlow", "FinancingCashFlow", "InvestingCashFlow"]]
df_cash_flow = df_cash_flow.reset_index()
# 最新のレコードに絞る
df_cash_flow = df_cash_flow.drop_duplicates(subset=['symbol'], keep='last')


df_financial = pd.DataFrame(sp500.financial_data).T
df_financial.index.name = "symbol"
# totalCash :現金及び現金同等物
# operatingMargins: 営業利益率
# currentRatio: 流動比率
df_financial = df_financial[["totalCash","operatingMargins","currentRatio"]]
df_financial = df_financial.reset_index()


# --------------------------------------------------
# 全て結合する
# --------------------------------------------------
df_Haiku = pd.merge(df_Haiku, df_summary, on='symbol', how='left')
df_Haiku = pd.merge(df_Haiku, df_income, on='symbol', how='left')
df_Haiku = pd.merge(df_Haiku, df_balance, on='symbol', how='left')
df_Haiku = pd.merge(df_Haiku, df_cash_flow, on='symbol', how='left')
df_Haiku = pd.merge(df_Haiku, df_financial, on='symbol', how='left')

# BRK.B はほぼデータが入っていないので削除する
df_Haiku = df_Haiku[df_Haiku["symbol"]!="BRK.B"]
# BF.B はほぼデータが入っていないので削除する
df_Haiku = df_Haiku[df_Haiku["symbol"]!="BF.B"]
# GOOG は残し GOOGL は削除する
df_Haiku = df_Haiku[df_Haiku["symbol"]!="GOOGL"]


# --------------------------------------------------
# 変数作成
# --------------------------------------------------
# 自己資本比率＝純資産 ÷ 総資産
df_Haiku["capitalRatio"] = df_Haiku["CapitalStock"] / df_Haiku["TotalAssets"]
# ネットキャッシュ=totalCash(現金及び現金同等物) + AvailableForSaleSecurities(有価証券) - NetDebt(純有利子負債)
# df_Haiku["netCash"] = df_Haiku["totalCash"] + df_Haiku["AvailableForSaleSecurities"] - df_Haiku["NetDebt"]
# 営業キャッシュフローマージン=営業キャッシュフロー ÷ 売上高
df_Haiku["operatingCashFlowMargin"] = df_Haiku["OperatingCashFlow"] / df_Haiku["TotalRevenue"]
# 発行済株式数=時価総額 ÷ 株価
df_Haiku["outstandingBalanceofIssuedStocks"] = (df_Haiku["marketCap"].astype(int) / df_Haiku["stockprice"].astype(float)).astype(int)
# 配当利回りを分かりやすくするために100倍する
df_Haiku["dividendYield"] = (df_Haiku["dividendYield"].astype(float) * 100).round(2)
# 配当利回りが 3～9％ の間にある銘柄だけに絞る（高配当優良株がコンセプトなので）
df_Haiku = df_Haiku[(df_Haiku["dividendYield"] >= 3.0) & (df_Haiku["dividendYield"] <= 9.0)]
# 配当利回りの高い順にソート
df_Haiku = df_Haiku.sort_values(by="dividendYield", ascending=False)
df_Haiku = df_Haiku.reset_index(drop=True)



# --------------------------------------------------
# Claud Haiku に投げるデータフレームを作る
# --------------------------------------------------
# 結果を入れる
df_Haiku["収益と市場優位性"]     = 0.0
df_Haiku["財務の健全性"]         = 0.0
df_Haiku["稼ぐ力と安全性"]       = 0.0
df_Haiku["配当実績と支払い能力"] = 0.0
df_Haiku["総評"]                = ""



# --------------------------------------------------
# LLM API 実行
# --------------------------------------------------
# パラメータ
url = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
}
base_user_input = """<instructions>
あなたの役割は、提供された入力データに基づいて高配当株を分析し、その結果を常にJSON形式で出力するプログラムです。高い配当利回りだけではなく、安定した財務基盤と高い収益性を持ち、将来的にもその配当利回りを維持できる企業を見つけ出すことが目的です。各変数について5点満点で評価し、その総評をコメントで提供してください。余計な出力は避け、必要な情報のみをJSONスキーマで出力してください。
</instructions>

<variables>
- 収益と市場優位性: 売上高、営業利益率、営業キャッシュフローマージン
- 財務の健全性: 現金と現金同等物、流動比率、自己資本比率
- 稼ぐ力と安全性: フリーキャッシュフロー、営業キャッシュフロー、投資キャッシュフロー、財務キャッシュフロー
  - 補足:投資キャッシュフローと財務キャッシュフローがマイナスの場合、積極的に事業投資している証拠であるため加点要素です
- 配当実績と支払い能力: 1株当りの配当金、配当利回り、過去5年間の平均配当利回り、配当性向、利益余剰金
</variables>

<analysis>
<task>
以下の入力データに基づいて、各変数を5点満点で評価し、総評をコメントで出力してください。
</task>

<input_data>
{
  "TotalRevenue": "df.TotalRevenue",
  "operatingMargins": "df.operatingMargins",
  "operatingCashFlowMargin": "df.operatingCashFlowMargin",
  "totalCash": "df.totalCash",
  "currentRatio": "df.currentRatio",
  "capitalRatio": "df.capitalRatio",
  "FreeCashFlow": "df.FreeCashFlow",
  "OperatingCashFlow": "df.OperatingCashFlow",
  "InvestingCashFlow": "df.InvestingCashFlow",
  "FinancingCashFlow": "df.FinancingCashFlow",
  "dividendRate": "df.dividendRate",
  "dividendYield": "df.dividendYield",
  "fiveYearAvgDividendYield": "df.fiveYearAvgDividendYield",
  "payoutRatio": "df.payoutRatio",
  "RetainedEarnings": "df.RetainedEarnings"
}
</input_data>
</analysis>

<output_format>
{
  "additional_information": "理由や注意事項、補足、特記事項など、どうしても書きたいことがあればここに書いてください。",
  "TotalRevenue": "評価点",
  "operatingMargins": "評価点",
  "operatingCashFlowMargin": "評価点",
  "totalCash": "評価点",
  "currentRatio": "評価点",
  "capitalRatio": "評価点",
  "FreeCashFlow": "評価点",
  "OperatingCashFlow": "評価点",
  "InvestingCashFlow": "評価点",
  "FinancingCashFlow": "評価点",
  "dividendRate": "評価点",
  "dividendYield": "評価点",
  "fiveYearAvgDividendYield": "評価点",
  "payoutRatio": "評価点",
  "RetainedEarnings": "評価点",
  "総評": "コメント"
}
</output_format>"""


################## ★デバッグ中 #####################
df_Haiku = df_Haiku[:5]
################## ★デバッグ中 #####################


for i in range(len(df_Haiku)):

    # プロンプト作成
    user_input = base_user_input.replace("df.TotalRevenue", str(df_Haiku.loc[i, 'TotalRevenue']))
    user_input = user_input.replace("df.operatingMargins", str(df_Haiku.loc[i, 'operatingMargins']))
    user_input = user_input.replace("df.operatingCashFlowMargin", str(df_Haiku.loc[i, 'operatingCashFlowMargin']))
    user_input = user_input.replace("df.totalCash", str(df_Haiku.loc[i, 'totalCash']))
    user_input = user_input.replace("df.currentRatio", str(df_Haiku.loc[i, 'currentRatio']))
    user_input = user_input.replace("df.capitalRatio", str(df_Haiku.loc[i, 'capitalRatio']))
    user_input = user_input.replace("df.FreeCashFlow", str(df_Haiku.loc[i, 'FreeCashFlow']))
    user_input = user_input.replace("df.OperatingCashFlow", str(df_Haiku.loc[i, 'OperatingCashFlow']))
    user_input = user_input.replace("df.InvestingCashFlow", str(df_Haiku.loc[i, 'InvestingCashFlow']))
    user_input = user_input.replace("df.FinancingCashFlow", str(df_Haiku.loc[i, 'FinancingCashFlow']))
    user_input = user_input.replace("df.dividendRate", str(df_Haiku.loc[i, 'dividendRate']))
    user_input = user_input.replace("df.dividendYield", str(df_Haiku.loc[i, 'dividendYield']))
    user_input = user_input.replace("df.fiveYearAvgDividendYield", str(df_Haiku.loc[i, 'fiveYearAvgDividendYield']))
    user_input = user_input.replace("df.payoutRatio", str(df_Haiku.loc[i, 'payoutRatio']))
    user_input = user_input.replace("df.RetainedEarnings", str(df_Haiku.loc[i, 'RetainedEarnings']))


    # 出力を安定化させる手法を使っている(additional_information)
    # https://zenn.dev/kinzal/articles/52d47848826227
    data = json.dumps({
        "model": "anthropic/claude-3-haiku",
        "temperature": 0.9,
        "max_tokens": 500,
        "top_p": 0.95,
        "top_k": 40,
        "repetition_penalty": 1.1,
        "stream": False,
        "messages": [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": '{\n  "additional_information": "'}
        ]
    })

    # POST
    response = requests.post(
      url=url,
      headers=headers,
      data=data
    )

    if response.status_code == 200:
        json_dict = response.json()
        json_str = json_dict["choices"][0]["message"]["content"]
        json_str_extracted = extract_braces_content(json_str)     # パース
        company_dict = json.loads(json_str_extracted)
        # print(company_dict)
    else:
        print("リクエストに失敗しました。")

    # 5点満点の平均値
    company_dict["収益と市場優位性"]     = (company_dict["TotalRevenue"] + company_dict["operatingMargins"] + company_dict["operatingCashFlowMargin"]) / 3
    company_dict["財務の健全性"]         = (company_dict["totalCash"] + company_dict["currentRatio"] + company_dict["capitalRatio"]) / 3
    company_dict["稼ぐ力と安全性"]       = (company_dict["FreeCashFlow"] + company_dict["OperatingCashFlow"] + company_dict["InvestingCashFlow"] + company_dict["FinancingCashFlow"]) / 4
    company_dict["配当実績と支払い能力"] = (company_dict["dividendRate"] + company_dict["dividendYield"] + company_dict["fiveYearAvgDividendYield"] + company_dict["payoutRatio"] + company_dict["RetainedEarnings"]) / 5

    # 代入
    df_Haiku.loc[i, '収益と市場優位性']     = company_dict["収益と市場優位性"]
    df_Haiku.loc[i, '財務の健全性']         = company_dict["財務の健全性"]
    df_Haiku.loc[i, '稼ぐ力と安全性']       = company_dict["稼ぐ力と安全性"]
    df_Haiku.loc[i, '配当実績と支払い能力'] = company_dict["配当実績と支払い能力"]
    df_Haiku.loc[i, '総評']                = company_dict["総評"]


# リネーム
df_Haiku.rename(columns={"symbol":"ティッカー","companyname":"企業名","stockprice":"株価","years":"連続増配年数","aristocrat_flag":"配当貴族フラグ","marketCap":"時価総額","dividendRate":"1株当りの配当金","dividendYield":"配当利回り","exDividendDate":"次回配当金の権利確定日","payoutRatio":"配当性向","fiveYearAvgDividendYield":"過去5年間の平均配当利回り","TotalRevenue":"売上高","RetainedEarnings":"利益余剰金","CapitalStock":"株主資本(純資産, 自己資本)","TotalAssets":"総資産","NetDebt":"純有利子負債","FreeCashFlow":"フリーキャッシュフロー","OperatingCashFlow":"営業キャッシュフロー","FinancingCashFlow":"財務キャッシュフロー","InvestingCashFlow":"投資キャッシュフロー","totalCash":"現金及び現金同等物","operatingMargins":"営業利益率","currentRatio":"流動比率","capitalRatio":"自己資本比率","operatingCashFlowMargin":"営業キャッシュフローマージン","outstandingBalanceofIssuedStocks":"発行済株式数","総評":"AIによる総評"}, inplace=True)

# 順番入れ替え
df_Haiku = df_Haiku[["ティッカー","企業名","収益と市場優位性","財務の健全性","稼ぐ力と安全性","配当実績と支払い能力","AIによる総評","発行済株式数","株価","連続増配年数","配当貴族フラグ","時価総額","1株当りの配当金","配当利回り","次回配当金の権利確定日","配当性向","過去5年間の平均配当利回り","売上高","利益余剰金","株主資本(純資産, 自己資本)","総資産","純有利子負債","フリーキャッシュフロー","営業キャッシュフロー","財務キャッシュフロー","投資キャッシュフロー","現金及び現金同等物","営業利益率","流動比率","自己資本比率","営業キャッシュフローマージン"]]

# Float型に変換
convert_float_cols = ['配当性向', '営業利益率', '流動比率', '配当利回り']
df_Haiku[convert_float_cols] = df_Haiku[convert_float_cols].astype(float)
# float型のカラムを小数点第2位で切り捨て
df_Haiku = truncate_float_cols(df_Haiku)

# 保存する
df_Haiku.to_csv("df.csv", index=False)