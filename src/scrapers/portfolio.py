"""거래소 보유자산 조회 (업비트 + 빗썸 Private API)."""

import hashlib
import hmac
import time
import uuid
import base64
import urllib.parse

import jwt
import pandas as pd
import requests


class UpbitPortfolio:
    """업비트 보유자산 조회 (JWT 인증)."""

    BASE_URL = "https://api.upbit.com/v1"

    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.session = requests.Session()

    def _get_headers(self, params: dict = None) -> dict:
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
        }
        if params:
            query_string = urllib.parse.urlencode(params)
            payload['query_hash'] = hashlib.sha512(query_string.encode()).hexdigest()
            payload['query_hash_alg'] = 'SHA512'

        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return {'Authorization': f'Bearer {token}'}

    def get_balances(self) -> pd.DataFrame:
        """보유자산 전체 조회."""
        try:
            headers = self._get_headers()
            resp = self.session.get(f"{self.BASE_URL}/accounts", headers=headers, timeout=10)
            data = resp.json()

            if isinstance(data, dict) and 'error' in data:
                print(f"업비트 인증 오류: {data['error'].get('message', '')}")
                return pd.DataFrame()

            records = []
            for item in data:
                balance = float(item.get('balance', 0))
                locked = float(item.get('locked', 0))
                total = balance + locked
                if total <= 0:
                    continue

                avg_buy_price = float(item.get('avg_buy_price', 0))
                currency = item.get('currency', '')

                records.append({
                    'currency': currency,
                    'balance': total,
                    'available': balance,
                    'locked': locked,
                    'avg_buy_price': avg_buy_price,
                    'unit_currency': item.get('unit_currency', 'KRW'),
                })

            return pd.DataFrame(records) if records else pd.DataFrame()

        except Exception as e:
            print(f"업비트 잔고 조회 오류: {e}")
            return pd.DataFrame()


class BithumbPortfolio:
    """빗썸 보유자산 조회 (HMAC-SHA512 인증)."""

    BASE_URL = "https://api.bithumb.com"

    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.session = requests.Session()

    def _get_signature(self, endpoint: str, params: str = "") -> dict:
        nonce = str(int(time.time() * 1000))
        message = f"{endpoint}\x00{params}\x00{nonce}"
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        encoded_signature = base64.b64encode(signature.encode('utf-8')).decode('utf-8')

        return {
            'Api-Key': self.api_key,
            'Api-Sign': encoded_signature,
            'Api-Nonce': nonce,
            'Content-Type': 'application/x-www-form-urlencoded',
        }

    def get_balances(self) -> pd.DataFrame:
        """보유자산 전체 조회."""
        try:
            endpoint = "/info/balance"
            params = "currency=ALL"
            headers = self._get_signature(endpoint, params)

            resp = self.session.post(
                f"{self.BASE_URL}{endpoint}",
                data=params,
                headers=headers,
                timeout=10
            )
            data = resp.json()

            if data.get('status') != '0000':
                print(f"빗썸 인증 오류: {data.get('message', 'unknown')}")
                return pd.DataFrame()

            balance_data = data.get('data', {})
            records = []

            # 빗썸 잔고 응답: total_{currency}, available_{currency} 형태
            currencies = set()
            for key in balance_data.keys():
                if key.startswith('total_') and key != 'total_krw':
                    cur = key.replace('total_', '').upper()
                    currencies.add(cur)

            for cur in currencies:
                total = float(balance_data.get(f'total_{cur.lower()}', 0))
                available = float(balance_data.get(f'available_{cur.lower()}', 0))
                if total <= 0:
                    continue

                records.append({
                    'currency': cur,
                    'balance': total,
                    'available': available,
                    'locked': total - available,
                    'avg_buy_price': 0,  # 빗썸 API는 평균매수가 미제공
                    'unit_currency': 'KRW',
                })

            # KRW 잔고 추가
            krw_total = float(balance_data.get('total_krw', 0))
            if krw_total > 0:
                records.append({
                    'currency': 'KRW',
                    'balance': krw_total,
                    'available': float(balance_data.get('available_krw', 0)),
                    'locked': krw_total - float(balance_data.get('available_krw', 0)),
                    'avg_buy_price': 1,
                    'unit_currency': 'KRW',
                })

            return pd.DataFrame(records) if records else pd.DataFrame()

        except Exception as e:
            print(f"빗썸 잔고 조회 오류: {e}")
            return pd.DataFrame()


class PortfolioManager:
    """통합 포트폴리오 매니저."""

    def __init__(self, upbit_keys: dict = None, bithumb_keys: dict = None):
        self.upbit = None
        self.bithumb = None

        if upbit_keys and upbit_keys.get('access_key') and upbit_keys.get('secret_key'):
            self.upbit = UpbitPortfolio(upbit_keys['access_key'], upbit_keys['secret_key'])

        if bithumb_keys and bithumb_keys.get('api_key') and bithumb_keys.get('secret_key'):
            self.bithumb = BithumbPortfolio(bithumb_keys['api_key'], bithumb_keys['secret_key'])

    @property
    def has_any_exchange(self) -> bool:
        return self.upbit is not None or self.bithumb is not None

    def get_all_holdings(self, price_map: dict = None) -> pd.DataFrame:
        """전체 거래소 보유자산 통합 조회.

        Args:
            price_map: {symbol: current_price} 현재가 매핑 (외부에서 제공)

        Returns:
            DataFrame with columns: exchange, currency, balance, avg_buy_price,
                                    current_price, eval_amount, profit, profit_pct
        """
        if price_map is None:
            price_map = {}

        all_records = []

        # 업비트 잔고
        if self.upbit:
            upbit_df = self.upbit.get_balances()
            if not upbit_df.empty:
                for _, row in upbit_df.iterrows():
                    cur = row['currency']
                    if cur == 'KRW':
                        all_records.append({
                            'exchange': '업비트',
                            'currency': 'KRW',
                            'balance': row['balance'],
                            'avg_buy_price': 1,
                            'current_price': 1,
                            'eval_amount': row['balance'],
                            'profit': 0,
                            'profit_pct': 0,
                        })
                        continue

                    current_price = price_map.get(cur, 0)
                    avg = row['avg_buy_price']
                    bal = row['balance']
                    eval_amt = bal * current_price
                    buy_amt = bal * avg if avg > 0 else 0
                    profit = eval_amt - buy_amt
                    profit_pct = (profit / buy_amt * 100) if buy_amt > 0 else 0

                    all_records.append({
                        'exchange': '업비트',
                        'currency': cur,
                        'balance': bal,
                        'avg_buy_price': avg,
                        'current_price': current_price,
                        'eval_amount': eval_amt,
                        'profit': profit,
                        'profit_pct': round(profit_pct, 2),
                    })

        # 빗썸 잔고
        if self.bithumb:
            bithumb_df = self.bithumb.get_balances()
            if not bithumb_df.empty:
                for _, row in bithumb_df.iterrows():
                    cur = row['currency']
                    if cur == 'KRW':
                        all_records.append({
                            'exchange': '빗썸',
                            'currency': 'KRW',
                            'balance': row['balance'],
                            'avg_buy_price': 1,
                            'current_price': 1,
                            'eval_amount': row['balance'],
                            'profit': 0,
                            'profit_pct': 0,
                        })
                        continue

                    current_price = price_map.get(cur, 0)
                    bal = row['balance']
                    avg = row['avg_buy_price']
                    eval_amt = bal * current_price
                    buy_amt = bal * avg if avg > 0 else 0
                    profit = eval_amt - buy_amt if avg > 0 else 0
                    profit_pct = (profit / buy_amt * 100) if buy_amt > 0 else 0

                    all_records.append({
                        'exchange': '빗썸',
                        'currency': cur,
                        'balance': bal,
                        'avg_buy_price': avg,
                        'current_price': current_price,
                        'eval_amount': eval_amt,
                        'profit': profit,
                        'profit_pct': round(profit_pct, 2),
                    })

        if not all_records:
            return pd.DataFrame()

        df = pd.DataFrame(all_records)
        df = df.sort_values('eval_amount', ascending=False).reset_index(drop=True)
        return df
