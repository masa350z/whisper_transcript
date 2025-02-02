import json
import openai
from loguru import logger
from pydantic import BaseModel, Field
from typing import List
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter


def num_tokens_from_messages(messages: List[dict], model: str = "gpt-3.5-turbo") -> int:
    """
    チャット形式のメッセージから推定トークン数を返す。簡易実装。
    実際にはtiktoken等で正確に計測するのが好ましい。
    """
    text = ""
    for msg in messages:
        text += msg["content"]
    return int(len(text) * 1.1)


def num_tokens_from_functions(functions: list, model: str = "gpt-3.5-turbo") -> int:
    """
    function_callに渡すfunctions引数（JSONスキーマ）をおおまかに文字数カウントして
    トークンを推定（簡易実装）。
    """
    text = json.dumps(functions)
    return int(len(text) * 1.1)


COST_DICT = {
    "gpt-3.5-turbo": {
        "input": 0.0010,  # $0.001 / 1K tokens
        "output": 0.0020,  # $0.002 / 1K tokens
    },
    "gpt-4": {
        "input": 0.03,  # $0.03 / 1K tokens
        "output": 0.06,  # $0.06 / 1K tokens
    },
    "gpt-4-turbo": {
        "input": 0.01,
        "output": 0.03,
    }
}


class SimpleSummary(BaseModel):
    summary: str = Field(..., description="要約の内容を文章で書いたもの")
    summary_bullet: List[str] = Field(..., description="要点のリスト")
    decisions: List[str] = Field(..., description="タスク以外で決定された事項リスト")
    tasks: List[str] = Field(..., description="やるべきタスクのリスト")


class ChatGPTSummarizer:
    MODEL: str = "gpt-3.5-turbo"
    CHUNK_SIZE: int = 2000
    chunk_overlap: int = 0
    MAX_TOKENS: int = 2000
    COST_DICT = COST_DICT

    @classmethod
    def map_summaries(cls, text: str):
        """
        テキストを複数チャンクに分割し、それぞれをChatGPTで重要箇所を抽出する。
        (Mapフェーズに相当)
        """
        text_splitter = CharacterTextSplitter(
            separator=" ",
            chunk_size=cls.CHUNK_SIZE,
            chunk_overlap=cls.chunk_overlap
        )
        text_chunks = text_splitter.split_text(text)

        total_tokens = 0
        prompt_tokens = 0
        completion_tokens = 0
        costs = 0
        response_messages = []

        for chunk in text_chunks:
            logger.info(f"Processing chunk: {chunk[:80]}...")
            messages = [
                {
                    "role": "system",
                    "content": """
あなたは会議の議事録を作成するプロフェッショナルアシスタントです。
これから会議の文字起こししたテキストを分割して渡します。
テキストは話者分離をしていません。
この文章から重要な内容を抽出してください。
あなたの推察はせず、文章に明記されている内容をそのまま抽出してください。
抽出は箇条書きではなく、文章で行なってください。
                    """.strip(),
                },
                {"role": "user", "content": chunk},
            ]

            num_tokens = num_tokens_from_messages(messages, model=cls.MODEL)
            each_max = min(cls.MAX_TOKENS // len(text_chunks),
                           cls.MAX_TOKENS - num_tokens)
            if each_max <= 0:
                each_max = 100  # fallback

            response = openai.ChatCompletion.create(
                model=cls.MODEL,
                messages=messages,
                temperature=0,
                max_tokens=each_max,
            )

            usage = response["usage"]
            total_tokens += usage["total_tokens"]
            prompt_tokens += usage["prompt_tokens"]
            completion_tokens += usage["completion_tokens"]
            costs_chunk = (
                usage["prompt_tokens"] * cls.COST_DICT[cls.MODEL]["input"]
                + usage["completion_tokens"] *
                cls.COST_DICT[cls.MODEL]["output"]
            ) / 1000
            costs += costs_chunk

            content = response["choices"][0]["message"]["content"]
            logger.info(f"chat create chunk summary: {content}")
            response_messages.append(content)

        logger.info(f"Total tokens: {total_tokens}, costs: {costs}")
        return response_messages, costs

    @classmethod
    def get_simple_summary(cls, doc_summaries: str):
        """
        map_summariesで得られた複数要約を結合して渡し、
        最終的に構造化した議事録データ(SimpleSummaryモデル)として返す。
        """
        template = """
あなたは会議の議事録を作成するアシスタントです。
これから会議の文字起こしの要点を抽出した文章を渡します。
この会議の要約、要点のリスト、決定事項のリスト、タスクのリストを返してください。
会議の要約は渡した文章の体裁を留める程度で漏れのない文章で書いてください。
タスクのリストには今後やるべきタスクを書いてください。
タスクのリストには既に完了したことについては記載しないように注意してください。
決定事項のリストにはタスク以外で決定された事項を書いてください。

以下は要約のセットである：
{doc_summaries}
        """.strip()

        prompt = PromptTemplate(
            template=template,
            input_variables=["doc_summaries"]
        )

        messages = [
            {
                "role": "user",
                "content": prompt.format(doc_summaries=doc_summaries)
            },
        ]

        functions = [
            {
                "name": "get_simple_summary",
                "description": """会議の文字起こしの要点などを抽出した文章から
会議の要約、会議の要点のリスト、会議で決定された事項のリスト、
タスクのリストを抽出するための処理です。""",
                "parameters": SimpleSummary.schema(),
            }
        ]

        message_tokens = num_tokens_from_messages(messages, model=cls.MODEL)
        functions_tokens = num_tokens_from_functions(
            functions, model=cls.MODEL)
        max_tokens = max(cls.MAX_TOKENS - message_tokens - functions_tokens, 0)

        response = openai.ChatCompletion.create(
            model=cls.MODEL,
            messages=messages,
            functions=functions,
            function_call={"name": "get_simple_summary"},
            temperature=0,
            max_tokens=max_tokens,
        )

        usage = response["usage"]
        costs = (
            usage["prompt_tokens"] * cls.COST_DICT[cls.MODEL]["input"]
            + usage["completion_tokens"] * cls.COST_DICT[cls.MODEL]["output"]
        ) / 1000

        response_message = response["choices"][0]["message"]
        if response_message.get("function_call"):
            try:
                # function_callのargumentsをJSONとしてパース
                function_args = json.loads(
                    response_message["function_call"]["arguments"])
            except Exception as e:
                logger.error(f"Error parsing function arguments: {e}")
                function_args = None
            simple_summary = function_args
        else:
            simple_summary = None

        return simple_summary, costs
