from .language import detect_language

def boundary_response(message: str) -> str | None:
    low = message.lower()
    legal = ("tax", "visa", "immigration", "legal", "ضريبة", "ضرائب", "فيزا", "قانون")
    medical = ("medical", "mental health", "self-harm", "انتحار", "طبي", "صحة نفس")
    if any(term in low for term in legal + medical):
        return "لا أستطيع إعطاء قرار قانوني أو ضريبي أو طبي نهائي. راجع مصدرًا رسميًا أو مختصًا مؤهلًا قبل اتخاذ قرار.\n\nNext step: اكتب البلد ونوع العلاقة التعاقدية لأساعدك في تحضير أسئلة للمختص."
    return None
