import os
from typing import List

class EmbeddingService:
    _model = None

    def __init__(self):
        self.provider = "huggingface"
        self.model_name = "BAAI/bge-small-en-v1.5"
        self.dimensions = 384

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            from sentence_transformers import SentenceTransformer
            # Lazy loads model from local cache or HuggingFace hub
            cls._model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        return cls._model

    def generate_embedding(self, text: str) -> List[float]:
        """Generates a normalized 384-dimensional embedding vector for the supplied text."""
        if not text.strip():
            # Return zero vector if empty string is supplied
            return [0.0] * self.dimensions
            
        model = self._get_model()
        # BGE models perform best when query embeddings are normalized
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    @staticmethod
    def compute_similarity(v1: List[float], v2: List[float]) -> float:
        """
        Computes cosine similarity between two vectors.
        Since our HuggingFace embeddings are pre-normalized, the dot product
        is mathematically equivalent to the cosine similarity.
        """
        if len(v1) != len(v2) or not v1 or not v2:
            return 0.0
        return sum(a * b for a, b in zip(v1, v2))

