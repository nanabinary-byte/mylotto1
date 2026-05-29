"""
로또 6/45 당첨번호 수집 스크립트 v2
- cloudscraper로 봇 차단 우회 시도
- 실패 시 상세 오류 출력
"""

import json
import time
import sys
from datetime import datetime
from pathlib import Path

try:
    import cloudscraper
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    print("✅ cloudscraper 로드 완료")
except Exception as e:
    print(f"❌ cloudscraper 로드 실패: {e}")
    sys.exit(1)

DATA_FILE = Path("data/lotto.json")
API_URL   = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"

def calc_latest_draw_no():
    start = datetime(2002, 12, 7)
    days  = (datetime.now() - start).days
    return int(days / 7)

def fetch_draw(no: int):
    try:
        r = scraper.get(API_URL.format(no), timeout=15)
        r.raise_for_status()
        text = r.text.strip()
        if text.startswith("{"):
            d = r.json()
            if d.get("returnValue") == "success":
                return d
            print(f"  ⚠ 회차 {no} API 응답 오류: {d.get('returnValue')}")
        else:
            print(f"  ⚠ 회차 {no} HTML 응답 — 차단됨: {text[:100]}")
    except Exception as e:
        print(f"  ⚠ 회차 {no} 오류: {e}")
    return None

def load_existing():
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "updated": "", "latestDrwNo": 0,
        "freq": {str(i): 0 for i in range(1, 46)},
        "recent": []
    }

def save(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    existing  = load_existing()
    freq      = {str(i): existing["freq"].get(str(i), 0) for i in range(1, 46)}
    last_no   = existing.get("latestDrwNo", 0)
    latest_no = calc_latest_draw_no()
    recent_buf = list(existing.get("recent", []))

    print(f"마지막 저장 회차: {last_no}  /  수집 대상: {last_no+1} ~ {latest_no}")

    # 연결 테스트
    print("연결 테스트 중...")
    test = fetch_draw(last_no + 1 if last_no > 0 else 1)
    if test is None:
        print("❌ 차단 확인 — cloudscraper도 실패. 다른 방법 필요.")
        sys.exit(1)

    print(f"✅ 연결 성공! 수집 시작...")
    new_count = 0

    for no in range(last_no + 1, latest_no + 1):
        d = test if no == (last_no + 1 if last_no > 0 else 1) else fetch_draw(no)
        if not d:
            latest_no = no - 1
            break

        nums  = [d[f"drwtNo{i}"] for i in range(1, 7)]
        bonus = d["bnusNo"]
        for n in nums:
            freq[str(n)] += 1

        recent_buf.append({
            "drwNo": d["drwNo"], "drwNoDate": d["drwNoDate"],
            "nums": nums, "bonus": bonus
        })
        new_count += 1
        if new_count % 100 == 0:
            print(f"  진행 중... {no}회 완료")
        time.sleep(0.3)

    recent_buf = sorted(recent_buf, key=lambda x: x["drwNo"])[-5:]
    save({
        "updated": str(datetime.now().date()),
        "latestDrwNo": latest_no,
        "freq": freq,
        "recent": recent_buf
    })

    print(f"\n✅ 완료 — {new_count}회차 수집, 최신: {latest_no}")
    print(f"   최근 5회: {[r['drwNo'] for r in recent_buf]}")

if __name__ == "__main__":
    main()
