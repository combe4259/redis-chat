![coredot-chat-demo](logo.svg)

Redis를 이용한 채팅 구현의 이해를 돕기 위해서 만든 데모입니다.

## 활용 라이브러리

-   redis==4.6.0
-   starlette==0.27.0
-   broadcaster[redis]==0.2.0

## 이용방법

run.py가 사용하는 라이브러리들을 설치해 줍니다

```bash
pip install -r requirements.txt
```

uvicorn을 이용하여 run.py 의 app을 실행해 줍니다.  
8000번 포트로 웹서버를 실행하도록 구성하였습니다.

```bash
uvicorn run:app --reload --port 8000
```

## 스크린샷

![스크린샷 2024-01-09 오후 3 13 37](https://github.com/CoreDotToday/coredot-chat-demo/assets/5226919/be19882a-ce3f-4d49-8b40-a21a4c1dfb1e)
