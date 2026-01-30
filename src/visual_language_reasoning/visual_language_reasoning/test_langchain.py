import base64
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 1. SETUP: Connect LangChain to Alibaba
# We use 'ChatOpenAI' but point it to Alibaba's URL
llm = ChatOpenAI(
    model="qwen-vl-max",   # <--- IMPORTANT: Must use the 'vl' (Vision) model
    openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    openai_api_key=os.environ["DASHSCOPE_API_KEY"], # Ensure this ENV var is set
    temperature=0.01
)

# 2. IMAGE LOADER
def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"❌ Error: The file '{image_path}' was not found.")
        return None

# 3. SET YOUR IMAGE
image_filename = r"dog_and_girl.jpeg"  # Make sure this file exists

# 4. RUN
print(f"--- Sending {image_filename} to Qwen-VL-Max ---")

base64_img = encode_image(image_filename)
if base64_img:
    message = HumanMessage(
        content=[
            {"type": "text", "text": "Describe this image in detail."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}},
        ]
    )
    
    response = llm.invoke([message])
    print("\n--- Qwen Says ---")
    print(response.content)