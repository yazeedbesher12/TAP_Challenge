from src.config import KB_PATH
from src.data_loader import load_knowledge_base
def test_kb_loads_and_has_unique_complete_items():
    kb = load_knowledge_base(KB_PATH)
    ids = [item["id"] for item in kb["items"]]
    assert len(ids) == len(set(ids)) == 47
    assert all(item["question_variants"] for item in kb["items"])
