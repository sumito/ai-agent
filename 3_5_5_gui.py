import feedparser
import asyncio
import streamlit as st
from strands import Agent, tool
from dotenv import load_dotenv

load_dotenv()

@tool
def get_aws_updates(service_name: str) -> list:
    """
    指定された AWS サービス名に関連する
    AWS What's New の最新アップデートを最大3件取得する
    """
    feed = feedparser.parse(
        "https://aws.amazon.com/about-aws/whats-new/recent/feed/"
    )

    result = []

    for entry in feed.entries:
        if service_name.lower() not in entry.title.lower():
            continue

        result.append({
            "title": entry.get("title", ""),
            "published": entry.get("published", "N/A"),
            "summary": entry.get("summary", "")
        })

        if len(result) >= 3:
            break

    return result


#エージェント作成
agent = Agent(
    model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    tools=[get_aws_updates]
)

st.title("AWSアップデート確認くん")
service_name = st.text_input("アップデートを知りたいAWSサービス名を入力してください:")

async def process_stream(service_name,container):
    text_holder = container.empty()
    response = ""
    prompt = f"AWS{service_name.strip()}の最新アップデートを、日付つきでようやくして。"

    # エージェントからのストリーミングレスポンスを処理
    async for chunk in agent.stream_async(prompt):
        if isinstance(chunk,dict):
            event = chunk.get("event",{})

            #ツールを実行して検出して表示
            if "contentBlockStart" in event:
                tool_use = event["contentBlockStart"].get("start",{}).get("toolUse",{})
                tool_name = tool_use.get("name")

                #バッファをクリア
                if response : 
                    text_holder.markdown(response)
                    response = ""

                #ツール実行のメッセージ表示
                container.info(f" {tool_name} ツールを実行中…")
                text_holder = container.empty()

            #テキストを抽出してリアルタイム表示
            if text := chunk.get("data"):
                response += text
                text_holder.markdown(response)
#
if st.button("確認"):
    if service_name:
        with st.spinner("アップデート確認中…"):
            container = st.container()
            asyncio.run(process_stream(service_name,container))




