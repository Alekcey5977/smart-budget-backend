from datetime import datetime, timedelta, timezone
import uuid
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

load_dotenv()

ACCESS_SECRET_KEY = os.getenv("ACCESS_SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY")
ALGORITHM = "HS256"

# Хэширование паролей
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# Проверка валидности пароля
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# Получение хэш пароля
def get_password_hash(password):
    return pwd_context.hash(password)


# Создание access токена
def create_access_token(data: dict, expires_delta: timedelta = None, refresh_jti: str | None = None) -> str:
    if not isinstance(data, dict):
        raise TypeError("data must be a dict")
    if not data:
        raise ValueError("data must not be empty")

    try:
        if not ACCESS_SECRET_KEY or not isinstance(ACCESS_SECRET_KEY, str) or not ACCESS_SECRET_KEY.strip():
            raise ValueError("ACCESS_SECRET_KEY must be a non-empty string")

        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        expire = now + (expires_delta or timedelta(minutes=15))

        to_encode.update({
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "type": "access",
        })

        if refresh_jti is not None:
            to_encode["refresh_jti"] = str(refresh_jti)

        encoded_jwt = jwt.encode(
            to_encode, ACCESS_SECRET_KEY, algorithm=ALGORITHM)

        if not isinstance(encoded_jwt, str):
            encoded_jwt = encoded_jwt.decode("utf-8")

        return encoded_jwt

    except (TypeError, ValueError) as ve:
        raise ValueError(f"Validation error in create_access_token: {ve}")
    except (JWTError, Exception) as e:
        raise RuntimeError(f"Failed to create access token: {e}")


# Создание refresh токена
def create_refresh_token(data: dict, expires_delta: timedelta):
    if not isinstance(data, dict):
        raise TypeError("data must be a dict")
    if not data:
        raise ValueError("data must not be empty")
    
    try:
        if not REFRESH_SECRET_KEY or not isinstance(REFRESH_SECRET_KEY, str) or not REFRESH_SECRET_KEY.strip():
            raise ValueError("REFRESH_SECRET_KEY must be a non-empty string")

        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        expire = now + (expires_delta or timedelta(days=7))

        to_encode.update({
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "type": "refresh",
            "jti": str(uuid.uuid4()),
        })

        encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)

        if not isinstance(encoded_jwt, str):
            encoded_jwt = encoded_jwt.decode("utf-8")

        return encoded_jwt
    
    except (TypeError, ValueError) as ve:
        raise ValueError(f"Validation error in create_refresh_token: {ve}")
    except (JWTError, Exception) as e:
        raise RuntimeError(f"Failed to create refresh token: {e}")



# Проверка валидности токена
def verify_token(token: str, refresh_token_from_cookie: str | None = None):
    try:
        payload = jwt.decode(token, ACCESS_SECRET_KEY, algorithms=[ALGORITHM])
        refresh_jti_in_access = str(payload.get("refresh_jti"))

        if refresh_jti_in_access:
            if not refresh_token_from_cookie:
                return None
            try:
                refresh_payload = jwt.decode(
                    refresh_token_from_cookie,
                    REFRESH_SECRET_KEY,
                    algorithms=[ALGORITHM],
                    options={"require": ["jti"]}
                )
                current_refresh_jti = str(refresh_payload.get("jti"))

                if refresh_jti_in_access != current_refresh_jti:
                    return None
            except JWTError:
                return None
        return payload 

    except JWTError:
        return None
