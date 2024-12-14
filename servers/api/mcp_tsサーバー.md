MCPサーバー向けのプロジェクトの場合、基本的なTypeScript + Node.jsの設定から始めるのが適切そうですね。以下のコマンドで初期化できます：

```bash
# プロジェクトディレクトリで
npm init -y
npm install typescript @types/node ts-node --save-dev
npx tsc --init

# MCPの依存関係をインストール
npm install @modelcontextprotocol/sdk
```

そして、`package.json`に必要なスクリプトを追加します：

```json
{
 "type":"module",
  /*その他の設定*/
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "ts-node src/index.ts"
  }
}
```

`tsconfig.json`の主要な設定：
```json
{
  "compilerOptions": {
    "target": "es2020",
    "module": "nodenext",
    "moduleResolution": "nodenext",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules"]
}
```

この設定が完了したら、`src`ディレクトリを作成してそこにコードを書いていけます：
```bash
mkdir src
```



```bash
mkdir src
```

index.tsができたら`npm run dev`でビルド。
tsconfig.jsonの"outDir"にjsファイルが出力されるので、
そのファイルパスをclaude_desktop_config.jsonに設定。

claude_desktop_config.json
```
 "api": {
      "command": "node",
      "args": [
        "C:\\workspace\\mcp\\servers\\api\\dist\\index.js"
      ]
    }
```

"node"以外のコマンドのやり方もいろいろありそうだが、とりあえずできたやり方。