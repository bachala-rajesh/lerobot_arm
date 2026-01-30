import base64
import os
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# 1. SETUP: Load your API Key
api_key = os.environ.get("DASHSCOPE_API_KEY")
if not api_key:
    print("❌ Error: DASHSCOPE_API_KEY not found in environment.")
    exit()

# 2. IMAGE LOADER
def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        return None

# 3. SELECT YOUR MODEL HERE
# Uncomment the one you want to test:
# selected_model = "qwen-vl-max"   # <--- The Smartest (Recommended)
selected_model = "qwen-vl-plus"  # <--- The Fastest

print(f"🤖 Testing Model: {selected_model}")

# 4. INITIALIZE
llm = ChatOpenAI(
    model=selected_model,
    openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    openai_api_key=api_key,
    temperature=0.01
)

# 5. RUN TEST
image_filename = r"dog_and_girl.jpeg"  # Ensure you have a picture!
base64_img = encode_image(image_filename)

if base64_img:
    start_time = time.time()
    
    response = llm.invoke([
        HumanMessage(content=[
            {"type": "text", "text": "Describe the spatial relationship between objects in this image. Use words like 'left of', 'right of', 'above'."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
        ])
    ])
    
    end_time = time.time()
    print(f"\n⏱️ Time Taken: {end_time - start_time:.2f} seconds")
    print("\n--- Model Output ---")
    print(response.content)
else:
    print("❌ Error: test.jpg not found.")