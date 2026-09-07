import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
print("dotenv loaded")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
print("client created")

def embed(text):
    print("embedding:", text)
    return client.models.embed_content(
        model="gemini-embedding-001", contents=text
    ).embeddings[0].values

cat = embed("a small cat")
print("cat done, length:", len(cat))
dog = embed("a friendly dog")
db = embed("database indexing strategy")

def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a) ** 0.5
    nb = sum(y*y for y in b) ** 0.5
    return dot / (na * nb)

print("cat vs dog:", cosine(cat, dog))
print("cat vs db:", cosine(cat, db))