import streamlit as st
from sentence_transformers import SentenceTransformer


@st.cache_resource
def load_embedding_model():
    return SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")

# Load model only once
model = load_embedding_model()


def create_embeddings(chunks):
    return model.encode(chunks)