import os
import tempfile
import openai
from loguru import logger
from audio_processor import AudioProcessor
from summarizer import ChatGPTSummarizer


def whisper_transcribe(file_path: str, model: str = "whisper-1") -> str:
    """
    Whisper APIを使って音声ファイルを文字起こししてテキストを返す。
    """
    logger.info(f"=== start whisper transcription ===: {file_path}")
    with open(file_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe(model, audio_file)
    return transcript["text"]


def main():
    logger.add("results/app.log", rotation="1 MB", level="INFO")

    # 環境変数チェック
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY が設定されていません。")
        return

    # テストとして同一ディレクトリの sample.mp4 を用いる
    # 実際はユーザアップロードファイルなどを指定する形
    sample_video_path = "sample.mp4"
    if not os.path.exists(sample_video_path):
        logger.error(f"Sample file not found: {sample_video_path}")
        return

    # 1) 一時ファイルとして読み込み
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as input_tempfile:
        with open(sample_video_path, "rb") as f:
            input_tempfile.write(f.read())

    # 2) 動画から音声を抽出
    audio_file = AudioProcessor.extract_audio_from_video(input_tempfile)

    # 3) 音声ファイルを圧縮
    compressed_audio_file = AudioProcessor.compress_audio(audio_file)

    # 4) Whisper API で文字起こし
    transcript_text = whisper_transcribe(compressed_audio_file.name)

    # ===== 文字起こし結果をテキストファイルに保存する処理を追加 =====
    transcript_output_path = "results/transcript_text.txt"
    with open(transcript_output_path, "w", encoding="utf-8") as f:
        f.write(transcript_text)
    logger.info(f"Whisper transcription saved to {transcript_output_path}")

    # 5) ChatGPT で要約 (Map方式で部分ごとに重要点を抽出)
    doc_summaries, cost_map = ChatGPTSummarizer.map_summaries(transcript_text)
    logger.info(f"Intermediate cost (map summaries): {cost_map}")

    # 6) 要約文を結合して最終要約＋構造化
    combined_text = "\n".join(doc_summaries)
    simple_summary_dict, cost_final = ChatGPTSummarizer.get_simple_summary(
        combined_text)

    logger.info(f"Final cost (simple summary): {cost_final}")
    logger.info("=== SIMPLE SUMMARY DICT ===")
    logger.info(simple_summary_dict)

    # 7) 結果表示
    if simple_summary_dict:
        print("== Summary ==")
        print(simple_summary_dict.get("summary", ""))
        print("\n== Bullet ==")
        for b in simple_summary_dict.get("summary_bullet", []):
            print(f"- {b}")
        print("\n== Decisions ==")
        for d in simple_summary_dict.get("decisions", []):
            print(f"- {d}")
        print("\n== Tasks ==")
        for t in simple_summary_dict.get("tasks", []):
            print(f"- {t}")

        # ===== 要約結果をテキストファイルに保存する処理を追加 =====
        summary_output_path = "results/summary_text.txt"
        with open(summary_output_path, "w", encoding="utf-8") as f:
            # ここでは「要約」と「要点」「決定事項」「タスク」をまとめて書き出す例
            f.write("== Summary ==\n")
            f.write(simple_summary_dict.get("summary", "") + "\n\n")
            f.write("== Bullet ==\n")
            for b in simple_summary_dict.get("summary_bullet", []):
                f.write(f"- {b}\n")
            f.write("\n== Decisions ==\n")
            for d in simple_summary_dict.get("decisions", []):
                f.write(f"- {d}\n")
            f.write("\n== Tasks ==\n")
            for t in simple_summary_dict.get("tasks", []):
                f.write(f"- {t}\n")

        logger.info(f"Summary saved to {summary_output_path}")

    else:
        print("Summary is None")


if __name__ == "__main__":
    main()
