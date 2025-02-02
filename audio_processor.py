import os
import subprocess
import tempfile
from loguru import logger


class AudioProcessor:
    """
    Whisper APIに送るための音声ファイル（25MB以下）を準備する機能をまとめたクラスです。
    - 動画ファイルから音声のみを抽出
    - 音声ファイルのビットレートを動的に計算して圧縮
    - 音声時間を取得して処理に使う
    """

    @staticmethod
    def extract_audio_from_video(input_tempfile: tempfile.NamedTemporaryFile) -> tempfile.NamedTemporaryFile:
        """
        ffmpegを用いて動画ファイルから音声のみを抽出し、mp3ファイルとして出力する。
        """
        logger.info("=== extract audio from video ===")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as output_tempfile:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    input_tempfile.name,
                    "-q:a",
                    "0",
                    "-map",
                    "a",
                    output_tempfile.name,
                ],
                check=True
            )

        # 元の一時動画ファイルは削除
        os.remove(input_tempfile.name)
        return output_tempfile

    @classmethod
    def compress_audio(cls, input_file: tempfile.NamedTemporaryFile) -> tempfile.NamedTemporaryFile:
        """
        ffmpegを用いて音声を指定ビットレートやサンプリングレートに圧縮し、サイズを25MB以下に抑えることを目指す。
        ビットレートは音声長に合わせて動的に計算する例を示す。
        """
        logger.info("=== compress audio ===")

        duration = cls.get_audio_duration(input_file.name)
        logger.info(f"Audio duration: {duration} sec")

        bitrate = cls.calculate_bitrate(duration)
        logger.info(f"Target bitrate: {bitrate}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as output_tempfile:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    input_file.name,
                    "-codec:a",
                    "mp3",
                    "-ar",
                    "16000",  # サンプリングレート16kHz
                    "-ac",
                    "1",      # モノラル
                    "-b:a",
                    bitrate,  # 動的に決まるビットレート
                    output_tempfile.name,
                ],
                check=True
            )

        os.remove(input_file.name)
        logger.info(
            f"Compressed audio size: {os.path.getsize(output_tempfile.name)} bytes")
        return output_tempfile

    @staticmethod
    def get_audio_duration(file_path: str) -> float:
        """
        ffprobeを用いて音声ファイルの長さを秒単位で取得する。
        """
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True
        )
        return float(result.stdout.strip())

    @staticmethod
    def calculate_bitrate(duration: float, target_size_mb: float = 25.0) -> str:
        """
        指定した音声の長さ(duration秒)に対して、25MB以内に収まるようなビットレートを算出する。
        実際にはエンコード効率などで誤差があるため、余裕を見て少し低めに計算する。
        """
        # 安全マージン
        margin = 0.9
        # MB -> byte
        target_size_bytes = target_size_mb * 1024 * 1024 * margin

        # duration(sec) で割って秒あたりのbyte -> bitに変換
        bits_per_second = (target_size_bytes * 8) / duration
        # mp3は(kbps)単位で指定
        kbps = max(int(bits_per_second / 1000), 16)  # 下限16kbps程度に設定
        return f"{kbps}k"
