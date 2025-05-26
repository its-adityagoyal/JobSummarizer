import json
from sentence_transformers import SentenceTransformer, util
# import os

# Load sentence-transformer model
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

# ---------- Helper Functions ----------

def flatten_json(y):
    """
    Flattens any nested JSON into a single dict of key→value strings.
    """
    out = {}
    def flatten(x, name=''):
        if isinstance(x, dict):
            for a in x:
                flatten(x[a], f'{name}{a}_')
        elif isinstance(x, list):
            for i, a in enumerate(x):
                flatten(a, f'{name}{i}_')
        else:
            out[name[:-1]] = str(x)
    flatten(y)
    return out

def entry_to_string(entry):
    """
    Converts one JSON entry into a single string of all its values,
    dropping the keys entirely.
    """
    flat = flatten_json(entry)
    return " ".join(flat.values())

def load_json_entries(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data if isinstance(data, list) else [data]

def compute_max_pairwise_similarity(list1, list2):
    # Convert entries to value-only strings
    strings1 = [entry_to_string(e) for e in list1]
    strings2 = [entry_to_string(e) for e in list2]

    # --- Print out the flattened strings for human inspection ---
    # print("\n=== Flattened Entries from List 1 ===")
    # for i, s in enumerate(strings1, start=1):
    #     print(f"[List1 #{i}]: {s}\n")

    # print("=== Flattened Entries from List 2 ===")
    # for i, s in enumerate(strings2, start=1):
    #     print(f"[List2 #{i}]: {s}\n")
    # ------------------------------------------------------------

    # Compute embeddings
    embeddings1 = model.encode(strings1, convert_to_tensor=True)
    embeddings2 = model.encode(strings2, convert_to_tensor=True)

    # Pairwise cosine similarity
    cosine_scores = util.pytorch_cos_sim(embeddings1, embeddings2)

    # For each entry in list1, take its best match in list2
    best_scores = cosine_scores.max(dim=1).values

    return best_scores.mean().item() * 100  # percentage

# ---------- Main Execution ----------

entries1 = load_json_entries("Output (openai_gpt-4o)\\PDF7.json")
entries2 = load_json_entries("Output (deepseek_deepseek-r1)\\PDF8.json")

similarity_score = compute_max_pairwise_similarity(entries1, entries2)

print(f"Similarity Score: {similarity_score:.2f}%")
