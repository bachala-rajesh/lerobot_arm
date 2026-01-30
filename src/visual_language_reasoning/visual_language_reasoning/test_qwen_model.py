import os
from dashscope import MultiModalConversation
import dashscope

dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# Define input content
messages = [
    {
        "role": "user",
        "content": [
            {"image": r"dog_and_girl.jpeg"},  # Replace with valid image URL
            {"text": "What is in the image?"},
        ],
    }
]

# Call the model
response = MultiModalConversation.call(
    model="qwen3-vl-plus", messages=messages, stream=True
)

# Safely handle response
full_content = ""
for chunk in response:
    # Check response structure integrity
    if (
        chunk.output
        and chunk.output.choices
        and chunk.output.choices[0].message
        and chunk.output.choices[0].message.content
    ):
        content_part = chunk.output.choices[0].message.content[0]["text"]
        if content_part:  # Skip empty strings
            full_content += content_part
            print(content_part, end="", flush=True)

    # Handle thinking process (if needed)
    elif (
        chunk.output
        and chunk.output.choices
        and chunk.output.choices[0].message.reasoning_content
    ):
        print("Thinking: " + chunk.output.choices[0].message.reasoning_content, end="")

print("\nComplete response: ", full_content)
