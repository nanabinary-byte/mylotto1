"""
로또 6/45 당첨번호 수집 스크립트
- 브라우저 헤더 사용으로 차단 우회
- 기존 data/lotto.json 에서 마지막 회차를 읽어 이후 회차만 추가 수집
- 최초 실행 시 1회부터 현재까지 전체 수집
"""

import json
import time
import requests
from datetime import datetime
from pathlib import Path

DATA_FILE = Path("data/lotto.json")
API_URL   = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"

# 브라우저로 위장하는 헤더
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://www.dhlottery.co.kr/gameResult.do?method=byWin",
    "X-Requested-With": "XMLHttpRequest",
}

def calc_latest_draw_no():
    start = datetime(2002, 12, 7)
    days  = (datetime.now() - start).days
    return int(days / 7)

def fetch_draw(no: int):
    try:
        r = requests.get(API_URL.format(no), headers=HEADERS, timeout=10)
        r.raise_for_status()
        # 응답이 JSON인지 확인
        if "application/json" in r.headers.get("Content-Type", "") or r.text.strip().startswith("{"):
            d = r.json()
            if d.get("returnValue") == "success":
                return d
        else:
            print(f"  ⚠ 회차 {no} HTML 응답 (차단 가능성): {r.text[:80]}")
    except requests.exceptions.RequestException as e:
        print(f"  ⚠ 회차 {no} 네트워크 오류: {e}")
    except json.JSONDecodeError as e:
        print(f"  ⚠ 회차 {no} JSON 파싱 실패: {e}")
    return None

def load_existing():
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "updated":     "",
        "latestDrwNo": 0,
        "freq":        {str(i): 0 for i in range(1, 46)},
        "recent":      []
    }

def save(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    existing   = load_existing()
    freq       = {str(i): existing["freq"].get(str(i), 0) for i in range(1, 46)}
    last_no    = existing.get("latestDrwNo", 0)
    latest_no  = calc_latest_draw_no()
    recent_buf = list(existing.get("recent", []))

    print(f"마지막 저장 회차: {last_no}  /  수집 대상: {last_no+1} ~ {latest_no}")

    # 첫 요청으로 연결 테스트
    test = fetch_draw(1 if last_no == 0 else last_no + 1)
    if test is None:
        print("❌ 서버 연결 실패 — 요청이 차단됐거나 네트워크 오류입니다.")
        return

    new_count = 0
    start_no  = last_no + 1

    for no in range(start_no, latest_no + 1):
        d = test if no == start_no else fetch_draw(no)
        if not d:
            print(f"  → 회차 {no} 데이터 없음. 수집 종료.")
            latest_no = no - 1
            break

        nums  = [d[f"drwtNo{i}"] for i in range(1, 7)]
        bonus = d["bnusNo"]

        for n in nums:
            freq[str(n)] += 1

        recent_buf.append({
            "drwNo":     d["drwNo"],
            "drwNoDate": d["drwNoDate"],
            "nums":      nums,
            "bonus":     bonus
        })

        new_count += 1
        if new_count % 100 == 0:
            print(f"  진행 중... {no}회 완료 ({new_count}개 수집)")

        time.sleep(0.3)

    recent_buf = sorted(recent_buf, key=lambda x: x["drwNo"])[-5:]

    result = {
        "updated":     str(datetime.now().date()),
        "latestDrwNo": latest_no,
        "freq":        freq,
        "recent":      recent_buf
    }
    save(result)

    print(f"\n✅ 완료 — 신규 {new_count}회차 수집, 최신 회차: {latest_no}")
    print(f"   최근 5회: {[r['drwNo'] for r in recent_buf]}")

if __name__ == "__main__":
    main()
