## GitHub Actions
- Haikuで分析してその結果をCloudflare Workers KVの値を更新する
- GitHub Actionsで毎月回す

## To Do
- 以下だけ修正する。あとはフロントエンドの見た目を修正するだけ

on:<br>
  schedule:<br>
    - cron: '0 0 1 * *' # 毎月1日に実行　　　★これを復活させる
