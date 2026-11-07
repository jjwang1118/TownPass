"""把 data/rx_samples.json 的範例藥袋產生成 QR 圖檔，輸出到 seed/qr/。

在 microservice/backend 執行：uv run python -m seed.make_qr
"""

import json
from pathlib import Path

import segno

from app.modules.medication.service import MedicationService

SEED_DIR = Path(__file__).parent
OUT_DIR = SEED_DIR / "qr"


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    samples = json.loads((SEED_DIR / "data" / "rx_samples.json").read_text(encoding="utf-8"))
    for sample in samples:
        MedicationService._from_app_qr(sample["payload"])  # 確認格式正確（規格書 §8.1）
        content = json.dumps(sample["payload"], ensure_ascii=False, separators=(",", ":"))
        path = OUT_DIR / f"{sample['file']}.png"
        segno.make(content, error="m").save(path, scale=8, border=4)
        print(f"{path.relative_to(SEED_DIR.parent)}：{sample['note']}")


if __name__ == "__main__":
    main()
