import feedparser
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


agent = Agent(
    model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    tools=[get_aws_updates]
)

service_name = input(
    "アップデートを知りたいAWSサービスを入力してください:"
).strip()

prompt = f"AWSの{service_name}の最新アップデートを日付つきで要約して。"
response = agent(prompt)

print(response)
