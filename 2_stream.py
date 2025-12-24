import boto3
from dotenv import load_dotenv

load_dotenv()

client = boto3.client("bedrock-runtime",region_name="us-east-1")

response = client.converse_stream(
    modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    messages=[{
        "role":"user",
        "content":[{    
            "text":"いろは歌を詠んで"
        }]
    }]
)

for event in response.get('stream',[]):
    if 'contentBlockDelta' in event:
        delta = event["contentBlockDelta"]["delta"]
        if "text" in delta:
            print(delta["text"], end="")


