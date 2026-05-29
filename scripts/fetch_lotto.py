"""
로또 6/45 당첨번호 수집 스크립트
- 기존 data/lotto.json 에서 마지막 회차를 읽어 이후 회차만 추가로 수집
- 최초 실행 시 1회부터 현재까지 전체 수집 (약 5~8분 소요)
- 번호별 출현 빈도와 최근 5회 당첨번호 저장
"""

import json
import time
import requests
from datetime import datetime
from pathlib import Path

DATA_FILE = Path("data/lotto.json")
API_URL   = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"


def calc_latest_draw_no():
    """오늘 날짜 기준 예상 최신 회차 계산"""
    start = datetime(2002, 12, 7)
    days  = (datetime.now() - start).days
    return int(days / 7)  # 당일 미추첨 가능성 감안해 -1 하지 않음


def fetch_draw(no: int) -> dict | None:
    """단일 회차 데이터 요청"""
    try:
        r = requests.get(API_URL.format(no), timeout=10)
        r.raise_for_status()
        d = r.json()
        if d.get("returnValue") == "success":
            return d
    except Exception as e:
        print(f"  ⚠ 회차 {no} 요청 실패: {e}")
    return None


def load_existing() -> dict:
    """기존 데이터 로드 (없으면 초기값 반환)"""
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "updated":     "",
        "latestDrwNo": 0,
        "freq":        {str(i): 0 for i in range(1, 46)},
        "recent":      []
    }


def save(data: dict):
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

    new_count = 0
    for no in range(last_no + 1, latest_no + 1):
        d = fetch_draw(no)
        if not d:
            # 아직 추첨 안 된 회차면 중단
            print(f"  → 회차 {no} 데이터 없음 (미추첨). 수집 종료.")
            latest_no = no - 1
            break

        nums  = [d[f"drwtNo{i}"] for i in range(1, 7)]
        bonus = d["bnusNo"]

        # 빈도 누적
        for n in nums:
            freq[str(n)] += 1

        # 최근 5회 버퍼
        recent_buf.append({
            "drwNo":     d["drwNo"],
            "drwNoDate": d["drwNoDate"],
            "nums":      nums,
            "bonus":     bonus
        })

        new_count += 1
        if new_count % 50 == 0:
            print(f"  진행 중... {no}회 완료")

        time.sleep(0.25)   # 서버 부하 방지

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
