"""
Lưu và tìm kiếm vector bằng Chroma (chạy local, lưu file, không cần server riêng).
Hỗ trợ 2 loại nguồn: "pdf" (theo trang) và "video" (theo thời gian/giây).
Metadata luôn có "content_type" để phân biệt khi hiển thị trích dẫn.
"""
import os
import chromadb

from app.core.database import BASE_DIR

VECTOR_DB_PATH = os.path.join(BASE_DIR, "vector_store")
os.makedirs(VECTOR_DB_PATH, exist_ok=True)

_client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
_collection = _client.get_or_create_collection(name="documents")


def add_chunks(document_id: int, source_name: str, chunks: list[dict], embeddings: list[list[float]]):
    """PDF: chunks = [{"text": ..., "page": ...}, ...]"""
    ids = [f"doc{document_id}_chunk{i}" for i in range(len(chunks))]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "content_type": "pdf",
            "document_id": document_id,
            "page": c["page"],
            "source_name": source_name,
        }
        for c in chunks
    ]
    _collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def add_video_chunks(video_id: int, source_name: str, chunks: list[dict], embeddings: list[list[float]]):
    """Video: chunks = [{"text": ..., "start_time": giây}, ...]"""
    ids = [f"video{video_id}_chunk{i}" for i in range(len(chunks))]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "content_type": "video",
            "video_id": video_id,
            "start_time": c["start_time"],
            "source_name": source_name,
        }
        for c in chunks
    ]
    _collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def query(query_embedding: list[float], n_results: int = 4, document_id: int | None = None):
    where = {"document_id": document_id} if document_id else None
    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
    )
    hits = []
    if results["documents"]:
        for text, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        ):
            hit = {
                "text": text,
                "content_type": meta.get("content_type", "pdf"),
                "source_name": meta["source_name"],
                "distance": dist,
            }
            if meta.get("content_type") == "video":
                hit["video_id"] = meta["video_id"]
                hit["start_time"] = meta["start_time"]
            else:
                hit["document_id"] = meta.get("document_id")
                hit["page"] = meta.get("page")
            hits.append(hit)
    return hits


def get_chunks_for_source(document_id: int | None = None, video_id: int | None = None, limit: int = 6) -> list[str]:
    """Lấy các đoạn text đã lưu của 1 tài liệu/video cụ thể, dùng làm nguyên liệu cho AI tạo câu hỏi."""
    where = {}
    if document_id:
        where = {"document_id": document_id}
    elif video_id:
        where = {"video_id": video_id}
    else:
        return []

    result = _collection.get(where=where, limit=limit)
    return result.get("documents", [])


def delete_document(document_id: int):
    _collection.delete(where={"document_id": document_id})


def delete_video(video_id: int):
    _collection.delete(where={"video_id": video_id})
