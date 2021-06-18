# Speech-to-Text-App

Azure Speech SDKを使用したSpeech-to-Textアプリ。

[参考URL](https://docs.microsoft.com/ja-jp/azure/cognitive-services/speech-service/get-started-speech-to-text?tabs=script%2Cwindowsinstall&pivots=programming-language-python)

## 更新履歴
- 2021.02.17
  - Slackとの連携が実現
  - Slackのチャンネルに文字起こしテキストをアップロードする
  - アプリ画面上でメンションの設定が可能
  

- 2021.01.20
  - 動画（mp4）での読み込み対応可能に
  

- 2021.01.18
  - YouTubeのURLから音声文字起こしが可能に
    - 画面にファイルからとYouTubeからの2パターンのラジオボタンを実装
  - 音声認識の完了予定時刻を出力（あくまで目安）
  

- 2020.01.06
  - バグ修正：ステレオ音源をモノラル音源に
    - ライブラリの仕様に合わせるため


- 2020.01.05
  - 出力テキストに改行を追加（句点位置）
  

- 2020.10.28
  - アプリインターフェイスを日本語に変更
  - Azure Storageとの連携（音声ファイル、および認識したテキストを格納）


- 2020.10.14
  - 対応形式をwav, m4a, mp3まで拡大
  - 「読み取りボタン」の廃止（アップロード後自動で文字起こし）


- 2020.10.08
  - アップロード時に音声ファイル分割（タイムアウト対策）
  - 読み取り時間の設定を廃止
  - プログレスバーの導入
  - ダウンロードリンクの出力


## 前提

- Macであること
- Dockerがインストールされていること
- AzureのCognitive Servicesの[Speech Services](https://azure.microsoft.com/ja-jp/services/cognitive-services/speech-services/)が使用可能であること


## ローカル実行方法

.env.sampleの各項目をそれぞれ設定を行い、`.env`とリネームする

```
SPEECH_KEY = "<Azure Speech Service Key>"
SPEECH_SERVICE_REGION = "<Azure Speech Service Region Name>"
BLOB_ACCOUNT_KEY = "<Azure Blob Account Key>"
BLOB_ACCOUNT_NAME = "<Azure Blob Account Name>"
SLACK_CHANNEL_ID = "<Slack Channel ID>"
SLACK_OAUTH_TOKEN = "<Slack OAuth Token>"
SLACK_WEBHOOK_URL = "<Slack Webhook URL>"
```


以下コマンドより環境構築＆アプリを起動

```
docker-compose up -d
```

アプリは以下よりアクセスできます。

```
http://localhost:80
```

### **注意**

ソースにある`DEBUG`を`TRUE`にすることで、ローカルで実行できます。


## アプリの操作方法

- Webアプリ上で文字起こししたい音声ファイルをアップロードする。
- アップロード後、自動で文字起こしアルゴリズムが実行する。

文字起こしの結果はアプリ上に一部表示されます。

全テキストはアプリに出力されるダウンロードリンクから取得できます。


## Azure上のデプロイ方法

### **注意**

ソースにある`DEBUG`が`FALSE`であることを確認し、下記手順に従い実施する。


ターミナルを用いてAzureにログインする

```commandline
az login
```

ログイン後に、Azure Container Registry にログインする

```commandline
az acr login --name <Registiry Name>
```

Webアプリを構成するDockerを一度構築してから落としておく

```commandline
docker-compose up --build -d
docker-compose down
```

Azure Container Registryにプッシュする

```commandline
docker-compose push
```

より詳細な内容は、[チュートリアル](https://docs.microsoft.com/en-us/azure/container-instances/tutorial-docker-compose)
を参照のこと

