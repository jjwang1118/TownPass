"""匯入藥品資料到 drug_licenses 表，用於同成分檢查與藥名搜尋。

資料來源：健保署「健保用藥品項查詢檔」。`license_no` 存健保藥品代號（10 碼），
`ingredients` 存 ATC 7 碼（同一種化學成分）。原本規劃的食藥署許可證資料也可以用同一個格式匯入。

藥名搜尋（手動新增藥品）需要「同藥名只出現一次，再選劑量」，所以匯入時把品名拆成：
產品名（去掉劑量、藥廠、括號）、主成分（英文品名括號內）、劑量、劑型。
"""

import re
import unicodedata
from typing import TypedDict

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.medication.models import DrugLicense

# PostgreSQL 一個指令最多 32767 個參數，依欄位數分批寫入
_MAX_PARAMS = 32767

_UNITS_EN = {"MG": "毫克", "MCG": "微克", "UG": "微克", "G": "公克", "ML": "毫升", "IU": "單位", "%": "%"}
_UNITS_ZH = {"毫克": "毫克", "公絲": "毫克", "微克": "微克", "公克": "公克", "毫升": "毫升", "公撮": "毫升"}
_NUMBER = r"\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)*"
_STRENGTH_EN = re.compile(rf"({_NUMBER})\s*(MCG|UG|MG|ML|IU|G|%)(?![A-Z])", re.IGNORECASE)
_STRENGTH_ZH = re.compile(rf"({_NUMBER})\s*(毫克|公絲|微克|公克|毫升|公撮|MG|MCG|ML|G)", re.IGNORECASE)
_QUOTED = re.compile(r"\"[^\"]*\"|“[^”]*”|〝[^〞]*〞|「[^」]*」|『[^』]*』")
_PAREN = re.compile(r"\([^()]*\)")


class LicenseRow(TypedDict):
    license_no: str
    name_zh: str
    name_en: str | None
    ingredients: list[str]
    product_en: str | None  # 產品名（英文），例如 NORVASC TABLETS
    product_zh: str | None  # 產品名（中文），例如 脈優錠
    ingredient_en: str | None  # 英文品名括號內的主成分，例如 AMLODIPINE
    strength: str | None  # 劑量，例如「5 毫克」
    form: str | None  # 劑型，例如「錠劑」


def normalize(text: str) -> str:
    """全形轉半形（５→5、（→(），多個空白合併。"""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def _clean(text: str) -> str:
    text = _PAREN.sub(" ", _QUOTED.sub(" ", text))
    text = re.sub(r"[\"“”〝〞]", " ", text)
    return re.sub(r"\s+", " ", text).strip(" ,.-/")


def _strength(number: str, unit: str) -> str:
    number = re.sub(r"\s*/\s*", "/", number)
    unit = unit.upper() if unit.upper() in _UNITS_EN else unit
    return f"{number} {_UNITS_EN.get(unit) or _UNITS_ZH.get(unit, unit)}"


def parse_name(name_en: str, name_zh: str) -> tuple[str | None, str | None, str | None, str | None]:
    """（產品名英文, 產品名中文, 主成分英文, 劑量）。拆不出來的回傳 None。"""
    en, zh = normalize(name_en), normalize(name_zh)
    strength = None
    if (match := _STRENGTH_EN.search(en)) or (match := _STRENGTH_ZH.search(zh)):
        strength = _strength(match.group(1), match.group(2))
    ingredient = None
    if parens := re.findall(r"\(([A-Za-z][^()]*)\)", en):
        ingredient = parens[-1].strip().upper() or None
    product_en = _clean(_STRENGTH_EN.sub(" ", en)).upper() or None
    product_zh = _clean(_STRENGTH_ZH.sub(" ", zh)) or None
    return product_en, product_zh, ingredient, strength


def from_nhi(item: dict[str, str]) -> LicenseRow:
    """健保用藥品項的一筆品項 → LicenseRow。

    ATC 只有 7 碼時才代表單一化學成分；3～5 碼只是藥物類別（例如 R05X 感冒複方），
    拿來比對會誤報，所以不列入成分。
    """
    atc = item["ATC代碼"].strip().upper()
    name_zh, name_en = item["中文品名"].strip(), item["英文品名"].strip()
    product_en, product_zh, ingredient_en, strength = parse_name(name_en, name_zh)
    return {
        "license_no": item["藥品代號"].strip(),
        "name_zh": name_zh,
        "name_en": name_en or None,
        "ingredients": [atc] if len(atc) == 7 else [],
        "product_en": product_en,
        "product_zh": product_zh,
        "ingredient_en": ingredient_en,
        "strength": strength,
        "form": item.get("劑型", "").strip() or None,
    }


async def import_licenses(session: AsyncSession, rows: list[LicenseRow]) -> int:
    """新增或更新藥品資料，回傳筆數。不 commit，由呼叫端決定。"""
    batch = _MAX_PARAMS // len(LicenseRow.__annotations__)
    for start in range(0, len(rows), batch):
        stmt = insert(DrugLicense).values(rows[start : start + batch])
        stmt = stmt.on_conflict_do_update(
            index_elements=[DrugLicense.license_no],
            set_={col: stmt.excluded[col] for col in LicenseRow.__annotations__ if col != "license_no"},
        )
        await session.execute(stmt)
    return len(rows)
