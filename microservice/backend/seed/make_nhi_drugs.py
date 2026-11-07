"""把健保署「健保用藥品項查詢檔」轉成 seed/data/nhi_drugs.json.gz，給 seed.load 匯入 drug_licenses。

在 microservice/backend 執行：
    uv run python -m seed.make_nhi_drugs ../../resent_docs/健保用藥品名_英文a-z.json

來源檔格式：{"資料來源", "資料": {"a": [{"品名", "品項": [{"藥品代號", "中文品名", "英文品名", "ATC代碼", …}]}], …}}。
用英文版：中文版少了沒有中文品名的品項。
"""

import gzip
import json
import sys
from pathlib import Path

from app.integrations.fda.importer import from_nhi

OUT = Path(__file__).parent / "data" / "nhi_drugs.json.gz"


def main(source: Path) -> None:
    raw = json.loads(source.read_text(encoding="utf-8"))
    items = [item for group in raw["資料"].values() for name in group for item in name["品項"]]
    rows = sorted((from_nhi(item) for item in items), key=lambda r: r["license_no"])
    if len({r["license_no"] for r in rows}) != len(rows):
        raise SystemExit("藥品代號有重複，請檢查來源檔")
    data = {"source": raw["資料來源"], "rows": rows}
    content = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    OUT.write_bytes(gzip.compress(content, mtime=0))  # mtime=0：內容相同時檔案也相同
    matchable = sum(1 for r in rows if r["ingredients"])
    print(f"{OUT.relative_to(Path.cwd())}：{len(rows)} 筆，其中 {matchable} 筆有 ATC 7 碼可比對同成分")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("用法：uv run python -m seed.make_nhi_drugs <健保用藥品項 JSON>")
    main(Path(sys.argv[1]))
