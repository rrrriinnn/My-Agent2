from datetime import date as Date, datetime
from decimal import Decimal, InvalidOperation
import re
from zoneinfo import ZoneInfo

import requests

API_URL = "https://api.frankfurter.dev/v2"


def request_api(path: str, params: dict | None = None):
    """Frankfurter API를 호출하고 오류를 한글로 안내합니다."""
    try:
        response = requests.get(f"{API_URL}/{path}", params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.Timeout as error:
        raise ValueError("환율 서버 응답이 늦어지고 있습니다. 잠시 후 다시 조회해 주세요.") from error
    except requests.HTTPError as error:
        if response.status_code in (400, 404, 422):
            raise ValueError("해당 통화 또는 날짜의 환율 데이터가 없습니다. 입력을 확인해 주세요.") from error
        raise ValueError("환율 서버를 이용할 수 없습니다. 잠시 후 다시 조회해 주세요.") from error
    except requests.RequestException as error:
        raise ValueError("환율 서버에 연결하지 못했습니다. 인터넷 연결을 확인해 주세요.") from error
    except ValueError as error:
        raise ValueError("환율 서버의 응답을 읽지 못했습니다.") from error


def get_currencies() -> dict:
    """조회 가능한 통화를 {통화 코드: 통화 이름} 형식으로 반환합니다."""
    data = request_api("currencies")
    if not isinstance(data, list) or not data:
        raise ValueError("지원 통화 목록을 불러오지 못했습니다.")
    try:
        return {item["iso_code"]: item["name"] for item in data}
    except (KeyError, TypeError) as error:
        raise ValueError("지원 통화 목록의 형식이 올바르지 않습니다.") from error


def get_exchange_rate(
    base_currency: str,
    target_currency: str,
    amount: float = 1.0,
    date: str = "latest",
) -> dict:
    """최신 또는 과거 환율과 환산 금액을 조회합니다. 날짜는 YYYY-MM-DD 또는 latest입니다."""
    base = base_currency.strip().upper()
    target = target_currency.strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", base) or not re.fullmatch(r"[A-Z]{3}", target):
        raise ValueError("통화는 USD, KRW, JPY처럼 영문 3자리 코드로 입력해 주세요.")

    try:
        money = Decimal(str(amount))
    except InvalidOperation as error:
        raise ValueError("금액은 숫자로 입력해 주세요.") from error
    if not money.is_finite() or money < 0 or money > Decimal("1e15"):
        raise ValueError("금액은 0 이상 1,000조 이하의 유한한 숫자로 입력해 주세요.")

    params = {}
    if date != "latest":
        try:
            selected_date = Date.fromisoformat(date)
        except (TypeError, ValueError) as error:
            raise ValueError("날짜는 YYYY-MM-DD 형식으로 입력해 주세요.") from error
        if selected_date > datetime.now(ZoneInfo("Asia/Seoul")).date():
            raise ValueError("미래 날짜의 환율은 조회할 수 없습니다.")
        params["date"] = selected_date.isoformat()

    if base == target:
        if base not in get_currencies():
            raise ValueError("지원하지 않는 통화입니다. 통화 코드를 확인해 주세요.")
        return {
            "base": base, "quote": target, "amount": str(money),
            "rate": "1", "converted_amount": str(money), "date": None,
            "requested_date": date, "source": "동일 통화이므로 환율 조회 없이 계산했습니다.",
        }

    data = request_api(f"rate/{base}/{target}", params=params)
    try:
        rate = Decimal(str(data["rate"]))
        actual_date = Date.fromisoformat(data["date"]).isoformat()
        if not rate.is_finite() or rate <= 0:
            raise ValueError
    except (KeyError, TypeError, ValueError, InvalidOperation) as error:
        raise ValueError("환율 서버가 올바른 환율 데이터를 반환하지 않았습니다.") from error

    return {
        "base": base, "quote": target, "amount": str(money),
        "rate": str(rate), "converted_amount": str(money * rate),
        "date": actual_date, "requested_date": date,
        "source": "https://frankfurter.dev/",
    }
