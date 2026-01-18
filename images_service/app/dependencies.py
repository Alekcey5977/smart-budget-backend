from fastapi import Header, HTTPException


async def get_user_id_from_header(x_user_id: str = Header(..., alias="X-User-ID")) -> int:
    """
    Получение user_id из заголовка запроса.

    Gateway проверяет токен и прокидывает user_id в заголовке X-User-ID.
    Этот dependency используется в защищенных эндпоинтах.

    Args:
        x_user_id: ID пользователя из заголовка

    Returns:
        int: ID пользователя

    Raises:
        HTTPException: Если заголовок отсутствует или невалиден
    """
    try:
        user_id = int(x_user_id)
        return user_id
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid X-User-ID header"
        )
