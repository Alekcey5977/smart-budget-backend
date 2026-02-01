import os
import jwt
from jose import JWTError
from dotenv import load_dotenv

load_dotenv()

ACCESS_SECRET_KEY = os.getenv("ACCESS_SECRET_KEY")
ALGORITHM = "HS256"


def verify_websocket_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, ACCESS_SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "access":
            return None

        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None

        return int(user_id_str)

    except (JWTError, ValueError, TypeError):
        return None
