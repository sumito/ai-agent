import asyncio
from langchain_core.messages import HumanMessage
import operator
import os
from typing import Annotated, Dict, List

import boto3
from dotenv import load_dotenv
from pydantic import BaseModel

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AnyMessage,
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langchain_tavily import TavilySearch

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

load_dotenv()

# --------------------
# Tools
# --------------------

web_search = TavilySearch(max_results=2)

@tool
def send_aws_sns(text: str):
    """テキストをAWS SNSのトピックにPublishする"""
    print("🔥 send_aws_sns CALLED")
    topic_arn = os.getenv("SNS_TOPIC_ARN")

    #print(text)
    print('topic_arn:',topic_arn)

    sns_client = boto3.client("sns")
    sns_client.publish(
        TopicArn=topic_arn,
        Message=text
    )
    print("** end send_aws_sns")

tools = [web_search, send_aws_sns]

# --------------------
# LLM
# --------------------

llm = init_chat_model(
    model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    model_provider="bedrock_converse",
)

llm_with_tools = llm.bind_tools(tools)

# --------------------
# State
# --------------------
class AgentState(BaseModel):
    messages: Annotated[list[AnyMessage], operator.add]
    search_result: str | None = None
    sent: bool = False

# --------------------
# Nodes
# --------------------

system_prompt = """
あなたは情報検索アシスタントです。

【ルール】
1. TavilySearch を必ず1回だけ使用してください
2. 検索結果を日本語で簡潔に要約してください
3. 要約が完了したら、それ以上ツールを呼び出してはいけません
"""

async def agent(state: AgentState):
    print("* start agent")

    response = await llm_with_tools.ainvoke(
        [SystemMessage(system_prompt)] + state.messages
    )

    updates = {"messages": [response]}

    # tool 呼び出し直後は ToolNode に任せる
    if response.tool_calls:
        print("* agent -> tool_calls")
        return updates

    # ToolMessage（検索結果）を拾う
    for msg in reversed(state.messages):
        if isinstance(msg, ToolMessage):
            print("* found ToolMessage")
            updates["search_result"] = msg.content
            break

    print("* end agent")
    return updates

tool_node = ToolNode(tools)

# --------------------
# Routing logic
# --------------------
def route(state: AgentState):
    last = state.messages[-1]

    print(last)

    if last.tool_calls:
        print("** route return \"tools\"")
        return "tools"

    if state.search_result and not state.sent:
        print("** route return \"send_sns\"")
        return "send_sns"

    print("** route return \"END\"")
    return END

def send_search_result(state: AgentState):
    print("** start send_search_result")
    if state.search_result and not state.sent:
        send_aws_sns.run(
            f"検索結果まとめ:\n{state.search_result}"
        )
        print("** end send_search_result OK")
        return {"sent": True}

    print("** end send_search_result no send")
    return {}
# --------------------
# Graph
# --------------------

builder = StateGraph(AgentState)

builder.add_node("agent", agent)
builder.add_node("tools", tool_node)
builder.add_node("send_sns", send_search_result)
builder.add_edge(START, "agent")

builder.add_conditional_edges(
    "agent",
    route,
    {
        "tools": "tools",
        "send_sns": "send_sns",
        END: END,
    },
)

builder.add_edge("tools", "agent")
builder.add_edge("send_sns", END)

app = builder.compile()

async def main():
    print("* start main()")
    question = "LangGraphの基本をやさしく解説して"
    response = await app.ainvoke(
        {"messages" : [HumanMessage(question)]}
    )
    print("* end main()")
    return response


asyncio.run(main())
#response = asyncio.run(main())
#print(response)
