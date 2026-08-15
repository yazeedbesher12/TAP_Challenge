from src.memory import delete_saved_data, empty_profile, load_saved_data, save_data
def test_memory_persistence_and_safe_deletion(tmp_path):
    path = tmp_path / "data.json"; profile = empty_profile(); profile["location"] = "Palestine"
    save_data(path, profile, [{"role":"user", "content":"hello"}], False); assert not path.exists()
    save_data(path, profile, [{"role":"user", "content":"hello"}], True); assert load_saved_data(path)["profile"]["location"] == "Palestine"
    delete_saved_data(path); assert not path.exists(); assert load_saved_data(path)["history"] == []
def test_corrupt_memory_is_safe(tmp_path):
    path = tmp_path / "bad.json"; path.write_text("not json")
    assert load_saved_data(path)["profile"] == empty_profile()
