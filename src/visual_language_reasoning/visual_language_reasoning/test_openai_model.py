import base64
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# 1. SETUP (Use the key from your environment)
llm = ChatOpenAI(model="gpt-4o", temperature=0.5)

# 2. IMAGE LOADER
def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"❌ Error: The file '{image_path}' was not found.")
        return None

# 3. SET YOUR IMAGE NAME HERE
image_filename = r"dog_and_girl.jpeg"  # <--- Change this to match your actual file name

# 4. PREPARE THE MESSAGE
base64_img = encode_image(image_filename)

if base64_img:
    print(f"Analyzing {image_filename}...")
    
    message = HumanMessage(
        content=[
            {"type": "text", "text": "What is in this image? Describe it in detail."},
            {
                "type": "image_url", 
                "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
            },
        ]
    )

    # 5. RUN
    response = llm.invoke([message])
    print("\n--- Model Description ---")
    print(response.content)