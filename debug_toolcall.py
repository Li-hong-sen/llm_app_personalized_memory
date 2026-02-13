"""调试 Qwen tool call 返回格式"""
import json
from openai import OpenAI

client = OpenAI(
    api_key="",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 模拟 mem0 中的 EXTRACT_ENTITIES_TOOL
EXTRACT_ENTITIES_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_entities",
        "description": "Extract entities and their types from the text.",
        "parameters": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "entity": {"type": "string", "description": "The name or identifier of the entity."},
                            "entity_type": {"type": "string", "description": "The type or category of the entity."},
                        },
                        "required": ["entity", "entity_type"],
                    },
                }
            },
            "required": ["entities"],
        },
    },
}

# 模拟 mem0 中的 RELATIONS_TOOL
RELATIONS_TOOL = {
    "type": "function",
    "function": {
        "name": "establish_relationships",
        "description": "Establish relationships among the entities based on the provided text.",
        "parameters": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string", "description": "The source entity of the relationship."},
                            "relationship": {"type": "string", "description": "The relationship between the source and destination entities."},
                            "destination": {"type": "string", "description": "The destination entity of the relationship."},
                        },
                        "required": ["source", "relationship", "destination"],
                    },
                }
            },
            "required": ["entities"],
        },
    },
}

print("=" * 60)
print("测试 1: extract_entities tool call")
print("=" * 60)

response1 = client.chat.completions.create(
    model="qwen-plus",
    messages=[
        {"role": "system", "content": "You are a smart assistant who understands entities and their types in a given text. If user message contains self reference such as 'I', 'me', 'my' etc. then use No03 as the source entity. Extract all the entities from the text."},
        {"role": "user", "content": "我喜欢吃苹果"},
    ],
    tools=[EXTRACT_ENTITIES_TOOL],
    tool_choice="auto",
)

print(f"完整 response.choices[0].message:")
msg = response1.choices[0].message
print(f"  content: {msg.content}")
print(f"  tool_calls: {msg.tool_calls}")
if msg.tool_calls:
    for tc in msg.tool_calls:
        print(f"    name: {tc.function.name}")
        print(f"    arguments (raw): {tc.function.arguments}")
        parsed = json.loads(tc.function.arguments)
        print(f"    arguments (parsed): {json.dumps(parsed, ensure_ascii=False, indent=4)}")

print()
print("=" * 60)
print("测试 2: establish_relationships tool call")
print("=" * 60)

response2 = client.chat.completions.create(
    model="qwen-plus",
    messages=[
        {"role": "system", "content": "You are a smart assistant who understands relationships between entities. Extract all relationships from the text."},
        {"role": "user", "content": "List of entities: ['no03', 'apple']. \n\nText: 我喜欢吃苹果"},
    ],
    tools=[RELATIONS_TOOL],
    tool_choice="auto",
)

print(f"完整 response.choices[0].message:")
msg2 = response2.choices[0].message
print(f"  content: {msg2.content}")
print(f"  tool_calls: {msg2.tool_calls}")
if msg2.tool_calls:
    for tc in msg2.tool_calls:
        print(f"    name: {tc.function.name}")
        print(f"    arguments (raw): {tc.function.arguments}")
        parsed = json.loads(tc.function.arguments)
        print(f"    arguments (parsed): {json.dumps(parsed, ensure_ascii=False, indent=4)}")
else:
    print("  *** 没有 tool_calls! Qwen 选择不调用工具 ***")

print()
print("=" * 60)
print("测试 3: 使用 tool_choice='required' 强制调用")
print("=" * 60)

try:
    response3 = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "You are a smart assistant who understands relationships between entities. Extract all relationships from the text."},
            {"role": "user", "content": "List of entities: ['no03', 'apple']. \n\nText: 我喜欢吃苹果"},
        ],
        tools=[RELATIONS_TOOL],
        tool_choice={"type": "function", "function": {"name": "establish_relationships"}},
    )

    msg3 = response3.choices[0].message
    print(f"  content: {msg3.content}")
    print(f"  tool_calls: {msg3.tool_calls}")
    if msg3.tool_calls:
        for tc in msg3.tool_calls:
            print(f"    name: {tc.function.name}")
            parsed = json.loads(tc.function.arguments)
            print(f"    arguments (parsed): {json.dumps(parsed, ensure_ascii=False, indent=4)}")
except Exception as e:
    print(f"  错误: {e}")

