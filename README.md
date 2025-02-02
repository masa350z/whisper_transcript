# Whisper Transcript - README

このリポジトリは、OpenAI の Whisper API と ChatGPT API を利用して「音声ファイル（または動画ファイル）から文字起こし」と「議事録要約」を自動生成するためのサンプルプロジェクトです。

## ディレクトリ構成

```
whisper_transcript
├── .env
├── .gitignore
├── audio_processor.py
├── docker-compose.yml
├── main.py
├── results
│   ├── app.log
│   ├── summary_text.txt
│   └── transcript_text.txt
├── sample.mp4
├── setup
│   ├── Dockerfile
│   └── requirements.txt
└── summarizer.py
```

## ディレクトリ・ファイルの説明

### `.env`
OpenAI APIキーを記述するためのファイルです。
```
OPENAI_API_KEY=sk-xxxx
```
の形式で記載してください。

### `.gitignore`
`results/` ディレクトリや `.env` など、バージョン管理に含めたくないファイル/ディレクトリを定義しています。

### `audio_processor.py`
ffmpeg を用いて動画から音声を抽出・圧縮し、Whisper API で文字起こしを行うための音声ファイルを準備するモジュールです。

### `docker-compose.yml`
Docker コンテナのサービス構成を定義するファイルです。この中でホスト上のカレントディレクトリ（本リポジトリのフォルダ）をコンテナ内の `/app` にマウントしています。

### `main.py`
メインのスクリプトで、以下の処理を行います。

1. `sample.mp4` を一時ファイルとして取り込み
2. 音声抽出（`AudioProcessor.extract_audio_from_video`）
3. 音声圧縮（`AudioProcessor.compress_audio`）
4. Whisper API で文字起こし
5. 要約（`ChatGPTSummarizer.map_summaries` → `ChatGPTSummarizer.get_simple_summary`）
6. 結果をコンソール出力し、同時に `results/` ディレクトリ配下へ保存
    - `transcript_text.txt`: 文字起こし結果
    - `summary_text.txt`: 要約結果

### `results/`

- `app.log`: アプリケーションのログファイル
- `transcript_text.txt`: Whisper による文字起こしの全文
- `summary_text.txt`: ChatGPT による議事録要約の結果

### `sample.mp4`
テスト用動画ファイルです。自前の音声ファイルや動画ファイルに差し替える場合は、同名で置き換えるか、`main.py` 内の該当箇所を書き換えてください。

### `setup/Dockerfile`
Docker イメージをビルドするための設定ファイルです。`Python 3.9-slim` をベースに、ffmpeg と Python ライブラリをインストールします。

### `setup/requirements.txt`
Whisper API と ChatGPT API、要約分割などに必要な Python ライブラリ (`openai`, `langchain`, `pydantic`, `loguru` など) を定義しています。

## 事前準備

### Docker のインストール
Docker および `docker-compose` がインストールされていることを確認してください。

- [Docker公式サイト](https://www.docker.com/)

### OpenAI APIキーの設定
`.env` ファイルに APIキーを記載し、`docker-compose` から読み込む形にしています。

```
OPENAI_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

## 使い方

### リポジトリをクローンまたはダウンロード

```bash
cd whisper_transcript
echo "OPENAI_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXXXX" > .env
```

またはエディタで `.env` を開いて直接記入してください。

### Dockerコンテナを起動

```bash
docker-compose up --build
```

`--build` オプションは初回や `Dockerfile` を変更した際に必要です。2回目以降の実行では省略しても構いません。

コンテナが起動すると、自動的に `main.py` が実行されます。

### 処理の流れ

1. `sample.mp4` を読み込み → ffmpeg で音声抽出 → Whisper API に送信 → 文字起こし (`transcript_text.txt` 生成)
2. ChatGPT API で要約 → 構造化された議事録を生成 → `summary_text.txt` 出力
3. 途中経過や最終結果がコンソール画面に表示され、ログは `results/app.log` に保存されます。

### 終了方法

ターミナル上で `Ctrl + C` を押すとコンテナが停止します。ネットワークなどのリソースを解放したい場合は以下を実行してください。

```bash
docker-compose down
```

### 結果確認

- `results/transcript_text.txt`: Whisper で文字起こしされた全文
- `results/summary_text.txt`: ChatGPT で要約された議事録

## 任意の音声/動画に差し替える

`sample.mp4` を自前のファイルに変更して置き換えるか、`main.py` の以下の行を編集してください。

```python
sample_video_path = "sample.mp4"
```

ファイル形式は `.mp4`, `.mov`, `.m4a`, `.wav` など ffmpeg が扱える形式であれば基本的に問題ありません。

## ログについて

`results/app.log` に実行時のログが保存されます。
Whisper や ChatGPT のやり取りの進捗が確認できます。

## 注意点

- Whisper API は音声ファイルに対して **25MB の上限** があるため、長時間の音声・動画を扱う場合、圧縮がうまく行かないとエラーになる可能性があります。圧縮に失敗した場合はビットレート設定や動画サイズを調整してください。
- ChatGPT (`gpt-3.5-turbo` など) は **トークン制限** があるため、大量の文字起こしを扱う場合は複数に分割して要約しています。

## ライセンス

各ファイルの著作権やライセンス条件に従ってご使用ください。第三者のライブラリ（`openai`, `ffmpeg` など）にはそれぞれのライセンスが適用されます。