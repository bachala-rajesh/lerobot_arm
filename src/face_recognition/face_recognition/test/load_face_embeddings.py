import json
import numpy as np


path_json_file = "faces_embeddings_data.json"

with open(path_json_file, "r") as f:
    db = json.load(f)

# For example, get all embeddings and names:
names = []
embeddings = []
for entry in db:
    names.append(entry["name"])
    embeddings.append(np.array(entry["embedding"]))

embeddings = np.stack(embeddings)  # shape: (num_users, 512)
print(embeddings.shape)