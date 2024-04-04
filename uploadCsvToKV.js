const fs = require('fs');
const Papa = require('papaparse');
const { execSync } = require('child_process');

// CSV ファイルのパス
const csvFilePath = './df.csv';

// KV ネームスペースのバインディング名
const kvNamespaceBinding = 'MY_KV_STORE';

// CSV ファイルを読み込む
const csvFile = fs.readFileSync(csvFilePath, 'utf-8');

// CSVをパースする
Papa.parse(csvFile, {
  header: true,
  complete: function(results) {
    // カラムごとにデータを抽出
    const data = results.data;
    const columns = results.meta.fields;

    columns.forEach(column => {
      const values = data.map(row => row[column]).filter(value => value !== undefined && value !== '');
      
      // キー（カラム名）と値（カラムの値のリスト）をKVに保存
      const key = column;
      const value = JSON.stringify(values);

      const command = `wrangler kv:key put "${key}" '${value}' --binding=${kvNamespaceBinding}`;
      
      try {
        // コマンドを実行
        execSync(command, { stdio: 'inherit' });
        console.log(`Success: ${key}`);
      } catch (error) {
        console.error(`Error saving ${key}: ${error}`);
      }
    });
  }
});
