import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

completion = client.chat.completions.create(
    # Model list: https://help.aliyun.com/zh/model-studio/getting-started/models
    model="qwen-plus",
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant. Please respond in English only.",
        },
        {"role": "user", "content": "Who are you?"},
    ],
)
print(completion.model_dump_json())
