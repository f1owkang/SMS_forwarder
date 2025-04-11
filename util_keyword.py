import jieba
import json
import re

jieba.load_userdict("/home/forward/dict_userwords.txt")


def load_yellow_pages():
    with open("/home/forward/config_yellowpages.json", "r", encoding="utf-8") as f:
        return json.load(f)

def extract_keyword(text):
    # code_match = re.search(r"(验证码|校验码)[^\d]{0,6}?(\d{4,8})", text)
    code_match = re.search(
        r'(验证码|校验码|动态码)[^\d]{0,10}?(\d{4,6})'  # 核心匹配
        r'(?=\D|$)',  # 边界保护
        text,
        flags=re.IGNORECASE  # 兼容大小写
    )
    if code_match:
        return f"验证码【{code_match.group(2)}】", None

    words = jieba.lcut(text)
    stopwords = {'的', '了', '请', '您', '我们', '他们', '在', '与', '和', '中', '为', '对', '等', '于', '是'}
    keywords = [w for w in words if len(w) >= 2 and w not in stopwords]

    yellow_pages = load_yellow_pages()
    for w in keywords:
        if w in yellow_pages:
            return '、'.join(keywords[:3]), yellow_pages[w]
    return '、'.join(keywords[:3]), None
