import sys
from pathlib import Path
from unittest.mock import AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models import EntityType, Image  # noqa: E402
from app.repository.image_repository import ImageRepository  # noqa: E402


# ---------------------------------------------------------------------------
# Хелперы
# ---------------------------------------------------------------------------
USER_ID = 1
OTHER_USER_ID = 999

FAKE_SVG = b"<svg width='10' height='10'/>"
FAKE_MIME = "image/svg+xml"


def auth_headers(user_id: int = USER_ID) -> dict:
    """Заголовок авторизации X-User-ID."""
    return {"X-User-ID": str(user_id)}


async def create_default_avatar(
    db_session: AsyncSession,
    mime_type: str = FAKE_MIME,
) -> Image:
    """Создаёт предустановленную аватарку (is_default=True, entity_id=None)."""
    repo = ImageRepository(db_session)
    return await repo.create_image(
        entity_type=EntityType.USER_AVATAR,
        file_data=FAKE_SVG,
        mime_type=mime_type,
    )


async def create_category_image(
    db_session: AsyncSession,
    entity_id: str = "cat_1",
) -> Image:
    """Создаёт изображение категории."""
    repo = ImageRepository(db_session)
    return await repo.create_image(
        entity_type=EntityType.CATEGORY,
        file_data=FAKE_SVG,
        mime_type=FAKE_MIME,
        entity_id=entity_id,
    )


async def create_merchant_image(
    db_session: AsyncSession,
    entity_id: str = "merch_1",
) -> Image:
    """Создаёт изображение мерчанта."""
    repo = ImageRepository(db_session)
    return await repo.create_image(
        entity_type=EntityType.MERCHANT,
        file_data=FAKE_SVG,
        mime_type=FAKE_MIME,
        entity_id=entity_id,
    )


# ==================== Health Check ====================

class TestHealthCheck:

    async def test_health_returns_ok(self, client: AsyncClient):
        """GET /health → 200, status: healthy."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    async def test_root_returns_service_name(self, client: AsyncClient):
        """GET / → 200, service: images-service."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "images-service"
        assert data["status"] == "running"


# ==================== GET /images/avatars/default ====================

class TestGetDefaultAvatars:

    async def test_empty_when_no_avatars(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Нет дефолтных аватарок → пустой список."""
        response = await client.get("/images/avatars/default")
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_default_avatars(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Дефолтные аватарки → список с метаданными."""
        avatar = await create_default_avatar(db_session)

        response = await client.get("/images/avatars/default")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        found = next((a for a in data if a["id"] == str(avatar.id)), None)
        assert found is not None
        assert found["entity_type"] == "user_avatar"
        assert found["is_default"] is True
        assert found["mime_type"] == FAKE_MIME
        assert "file_size" in found
        assert "created_at" in found

    async def test_no_auth_required(self, client: AsyncClient):
        """Публичный эндпоинт — не требует X-User-ID."""
        response = await client.get("/images/avatars/default")
        assert response.status_code == 200


# ==================== GET /images/avatars/me ====================

class TestGetMyAvatar:

    async def test_user_has_no_avatar_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Пользователь не выбрал аватарку → 404."""
        response = await client.get(
            "/images/avatars/me",
            headers=auth_headers(user_id=555),
        )
        assert response.status_code == 404

    async def test_returns_avatar_after_update(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """После установки аватарки — GET /avatars/me возвращает метаданные."""
        default_avatar = await create_default_avatar(db_session)

        await client.put(
            "/images/avatars/me",
            json={"image_id": str(default_avatar.id)},
            headers=auth_headers(user_id=42),
        )

        response = await client.get(
            "/images/avatars/me",
            headers=auth_headers(user_id=42),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "user_avatar"
        assert data["is_default"] is False

    async def test_missing_user_id_header(self, client: AsyncClient):
        """Без X-User-ID → 422."""
        response = await client.get("/images/avatars/me")
        assert response.status_code == 422

    async def test_invalid_user_id_header(self, client: AsyncClient):
        """Нечисловой X-User-ID → 400."""
        response = await client.get(
            "/images/avatars/me",
            headers={"X-User-ID": "abc"},
        )
        assert response.status_code == 400


# ==================== PUT /images/avatars/me ====================

class TestUpdateMyAvatar:

    async def test_valid_avatar_id_returns_metadata(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Корректный avatar_id → 200, is_default=False (пользовательская привязка)."""
        default_avatar = await create_default_avatar(db_session)

        response = await client.put(
            "/images/avatars/me",
            json={"image_id": str(default_avatar.id)},
            headers=auth_headers(user_id=10),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "user_avatar"
        assert data["is_default"] is False
        assert data["mime_type"] == FAKE_MIME

    async def test_update_replaces_previous_binding(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Повторный PUT заменяет предыдущую привязку — не падает."""
        avatar1 = await create_default_avatar(db_session)
        avatar2 = await create_default_avatar(db_session)

        response1 = await client.put(
            "/images/avatars/me",
            json={"image_id": str(avatar1.id)},
            headers=auth_headers(user_id=20),
        )
        assert response1.status_code == 200

        response2 = await client.put(
            "/images/avatars/me",
            json={"image_id": str(avatar2.id)},
            headers=auth_headers(user_id=20),
        )
        assert response2.status_code == 200

    async def test_nonexistent_avatar_id_returns_400(
        self, client: AsyncClient
    ):
        """Несуществующий avatar_id → 400 (ValueError в репозитории)."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.put(
            "/images/avatars/me",
            json={"image_id": fake_id},
            headers=auth_headers(),
        )
        assert response.status_code == 400

    async def test_missing_user_id_header(self, client: AsyncClient, db_session: AsyncSession):
        """Без X-User-ID → 422."""
        avatar = await create_default_avatar(db_session)
        response = await client.put(
            "/images/avatars/me",
            json={"image_id": str(avatar.id)},
        )
        assert response.status_code == 422

    async def test_event_publisher_called_on_success(
        self, client: AsyncClient, db_session: AsyncSession, mock_event_publisher
    ):
        """При успешном обновлении аватара — EventPublisher.publish вызывается."""
        default_avatar = await create_default_avatar(db_session)

        response = await client.put(
            "/images/avatars/me",
            json={"image_id": str(default_avatar.id)},
            headers=auth_headers(user_id=30),
        )
        assert response.status_code == 200
        mock_event_publisher.publish.assert_called_once()


# ==================== GET /images/images/{image_id} ====================

class TestGetImageById:

    async def test_returns_binary_content(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Существующее изображение → 200, бинарные данные совпадают."""
        avatar = await create_default_avatar(db_session)

        response = await client.get(f"/images/images/{avatar.id}")
        assert response.status_code == 200
        assert response.content == FAKE_SVG

    async def test_correct_content_type_header(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Content-Type соответствует mime_type изображения."""
        avatar = await create_default_avatar(db_session)

        response = await client.get(f"/images/images/{avatar.id}")
        assert response.status_code == 200
        assert FAKE_MIME in response.headers["content-type"]

    async def test_cache_control_header_present(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Cache-Control заголовок присутствует (кэш на год)."""
        avatar = await create_default_avatar(db_session)

        response = await client.get(f"/images/images/{avatar.id}")
        assert response.status_code == 200
        assert "cache-control" in response.headers
        assert "max-age" in response.headers["cache-control"]

    async def test_nonexistent_image_returns_404(self, client: AsyncClient):
        """Несуществующий ID → 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/images/images/{fake_id}")
        assert response.status_code == 404

    async def test_no_auth_required(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Публичный эндпоинт — не требует X-User-ID."""
        avatar = await create_default_avatar(db_session)
        response = await client.get(f"/images/images/{avatar.id}")
        assert response.status_code == 200


# ==================== GET /images/mappings/categories ====================

class TestGetCategoriesMapping:

    async def test_empty_when_no_categories(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Нет категорий → 200, пустой список mappings."""
        response = await client.get("/images/mappings/categories")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "category"
        assert data["mappings"] == []

    async def test_returns_category_mappings(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Есть категория → маппинг содержит entity_id, image_id, mime_type."""
        cat_image = await create_category_image(db_session, entity_id="cat_food")

        response = await client.get("/images/mappings/categories")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "category"

        mapping = next(
            (m for m in data["mappings"] if m["entity_id"] == "cat_food"),
            None,
        )
        assert mapping is not None
        assert mapping["image_id"] == str(cat_image.id)
        assert mapping["mime_type"] == FAKE_MIME

    async def test_no_auth_required(self, client: AsyncClient):
        """Публичный эндпоинт."""
        response = await client.get("/images/mappings/categories")
        assert response.status_code == 200


# ==================== GET /images/mappings/merchants ====================

class TestGetMerchantsMapping:

    async def test_empty_when_no_merchants(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Нет мерчантов → 200, пустой список mappings."""
        response = await client.get("/images/mappings/merchants")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "merchant"
        assert data["mappings"] == []

    async def test_returns_merchant_mappings(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Есть мерчант → маппинг содержит entity_id, image_id, mime_type."""
        merch_image = await create_merchant_image(db_session, entity_id="merch_sber")

        response = await client.get("/images/mappings/merchants")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "merchant"

        mapping = next(
            (m for m in data["mappings"] if m["entity_id"] == "merch_sber"),
            None,
        )
        assert mapping is not None
        assert mapping["image_id"] == str(merch_image.id)
        assert mapping["mime_type"] == FAKE_MIME

    async def test_no_auth_required(self, client: AsyncClient):
        """Публичный эндпоинт."""
        response = await client.get("/images/mappings/merchants")
        assert response.status_code == 200
