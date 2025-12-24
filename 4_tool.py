import boto3
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()

client = boto3.client("bedrock-runtime",region_name="us-east-1")

input = "2025年7月の祝日はいつ？"
llm = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"


def get_japanese_holidays(year):
    URL = f"https://holidays-jp.github.io/api/v1/{year}/date.json"
    with urllib.request.urlopen(URL) as response:
        data = response.read()
        holidays = json.loads(data)
    return holidays

tools = [{
    "toolSpec": {
        "name": "get_japanese_holidays",
        "description": "指定された年の日本の祝日一覧を取得します",
        "inputSchema": {
            "json": {
                "type" : "object",
                "properties": {
                    "year" : {
                        "type" : "integer",
                        "description": "祝日を取得したい年(例：2024)"
                    }
                },
                "required": ["year"]
            }
        }
    }
}]

#
# 1回目の推論
#
print("[推論1回目]")
print("ユーザーの入力:",input)

response = client.converse(
    modelId=llm,
    messages=[
        {
            "role": "user",
            "content": [{"text" : input}]
        }
    ],
    toolConfig={"tools": tools}
)


#初回のレスポンス
message = response["output"]["message"]
print("LLMの回答",message["content"][0]["text"])

#Tool Useの要否をチェック
tool_use = None
for content_item in message["content"]:
    if "toolUse" in content_item:
        tool_use = content_item["toolUse"]
        print("ツール要求",tool_use)
        print()
        break

#2回目の推論
if tool_use:
    # 実際のツール実行
    year = tool_use['input']['year']
    holidays = get_japanese_holidays(year)
    tool_result = {
        "year": year,
        "holidays": holidays,
        "count": len(holidays)
    }
    print("[アプリから直接、ツール実行して結果を取得]")
    print(tool_result)
    print()

#2回目の推論ように、1回目の会話履歴＋ツール実行結果を入力
messages = [
    {
        "role": "user",
        "content": [{"text": input}]
    },
    {
        "role" : "assistant",
        "content" : message["content"]
    },
    {
        "role": "user",
        "content":[
            {
                "toolResult" : {
                    "toolUseId" : tool_use["toolUseId"],
                    "content": [{
                        "json": tool_result
                    }]
                }
            }
        ]
    }
]

#2回目の回答
final_response = client.converse(
    modelId=llm,
    messages = messages,
    toolConfig={"tools": tools}
)

output = final_response["output"]["message"]["content"][0]["text"]
print("推論2回目")
print("ユーザーの入力:(ツール実行結果)")
print("LLMの回答",output)






