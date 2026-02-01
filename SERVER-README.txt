========================================
  Investor Tracker Server 가이드
========================================

[접속 주소]
- 외부: https://investor.pointing.co.kr
- 로컬: http://localhost:8501

[서버 시작/중지]
- 시작: start-server.bat 실행 (콘솔 표시)
- 백그라운드 시작: start-server-background.vbs 실행
- 중지: stop-server.bat 실행

[자동 시작 설정]
- Windows 로그인 시 자동 시작됨
- 위치: 시작 프로그램 폴더에 investor-tracker.vbs 등록됨

[수동으로 자동 시작 해제하려면]
1. Win+R → shell:startup 입력
2. investor-tracker.vbs 파일 삭제

[Cloudflare Tunnel 설정]
- 터널명: investor-tracker
- 설정파일: C:\Users\k\.cloudflared\config.yml
- 인증서: C:\Users\k\.cloudflared\cert.pem

[주요 파일 위치]
- 대시보드: src/web/dashboard.py
- 국내주식 스크래퍼: src/scrapers/korean_stocks.py
- 연금저축 스크래퍼: src/scrapers/pension_etf.py
- 텔레그램 봇: src/bot/telegram_bot.py

[문제 해결]
1. 사이트 접속 안될 때:
   - stop-server.bat 실행 후 start-server.bat 재실행

2. Cloudflare 터널 오류:
   cloudflared tunnel run investor-tracker

3. Streamlit만 재시작:
   python -m streamlit run src/web/dashboard.py

[데이터 업데이트 시간]
- 국내주식: 장 마감 후 (약 18:00 이후)
- 실시간 아님 (종가 기준)

========================================
