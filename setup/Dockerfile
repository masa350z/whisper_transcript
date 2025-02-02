# ベースイメージにはPython 3.9の軽量イメージを使用
FROM python:3.9-slim

# Whisperで動画ファイルを扱うためにffmpegをインストール
RUN apt-get update && apt-get install -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを /app に設定
WORKDIR /app

# requirements.txt のみ先にコピーしてpip install（依存関係をキャッシュさせるため）
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# デフォルトの実行コマンド
CMD ["python", "main.py"]
