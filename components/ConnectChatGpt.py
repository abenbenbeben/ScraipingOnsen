import openai
from dotenv import load_dotenv
import os

# 環境変数をロードする
load_dotenv()

def requestGpt(systemContent, userContent):
    # 環境変数からAPIキーを取得
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # ChatGPTにテキストを送信して応答を受け取る
    response = openai.ChatCompletion.create(
        model="gpt-4",  # モデル名を指定
        messages=[
            {"role": "system", "content": systemContent},
            {"role": "user", "content": userContent}
        ]
    )

    return response['choices'][0]['message']['content']

if __name__ == "__main__":
    sentence = ""
    system_content = "Example system message"
    user_content = "Example user message"
    print(requestGpt(system_content, user_content))
