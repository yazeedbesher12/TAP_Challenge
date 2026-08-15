from src.language import detect_language, text_direction
def test_language_detection():
    assert detect_language("مرحبا كيف حالك") == "ar"
    assert detect_language("How can I improve my CV?") == "en"
    assert detect_language("عندي remote interview") == "mixed"
    assert text_direction("مرحبا") == "rtl"
