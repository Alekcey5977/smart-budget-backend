import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest  # noqa: E402
from app.models import EntityType  # noqa: E402
from app.schemas import (  # noqa: E402
    ImageMappingItem,
    ImageMappingResponse,
    ImageMetadata,
    UpdateUserAvatarRequest,
    UploadImageRequest,
)
from pydantic import ValidationError  # noqa: E402

# ==================== ImageMetadata ====================


class TestImageMetadata:
    """Тесты схемы метаданных изображения."""

    def test_valid_data(self):
        """Корректные данные → объект создаётся."""
        meta = ImageMetadata(
            id=uuid4(),
            entity_type=EntityType.USER_AVATAR,
            mime_type="image/svg+xml",
            file_size=1024,
            is_default=True,
            created_at=datetime.now(tz=timezone.utc),
        )
        assert meta.entity_type == EntityType.USER_AVATAR
        assert meta.file_size == 1024
        assert meta.is_default is True

    def test_missing_id_raises(self):
        """Отсутствие id → ValidationError."""
        with pytest.raises(ValidationError):
            ImageMetadata(
                entity_type=EntityType.USER_AVATAR,
                mime_type="image/jpeg",
                file_size=100,
                is_default=True,
                created_at=datetime.now(),
            )

    def test_missing_entity_type_raises(self):
        """Отсутствие entity_type → ValidationError."""
        with pytest.raises(ValidationError):
            ImageMetadata(
                id=uuid4(),
                mime_type="image/jpeg",
                file_size=100,
                is_default=True,
                created_at=datetime.now(),
            )

    def test_entity_id_is_optional(self):
        """entity_id опциональный — по умолчанию None."""
        meta = ImageMetadata(
            id=uuid4(),
            entity_type=EntityType.CATEGORY,
            mime_type="image/png",
            file_size=200,
            is_default=True,
            created_at=datetime.now(),
        )
        assert meta.entity_id is None

    def test_updated_at_is_optional(self):
        """updated_at опциональный — по умолчанию None."""
        meta = ImageMetadata(
            id=uuid4(),
            entity_type=EntityType.MERCHANT,
            mime_type="image/png",
            file_size=300,
            is_default=False,
            created_at=datetime.now(),
        )
        assert meta.updated_at is None


# ==================== ImageMappingItem ====================


class TestImageMappingItem:
    """Тесты схемы маппинга сущности к изображению."""

    def test_valid_data(self):
        """Корректные данные → объект создаётся."""
        item = ImageMappingItem(
            entity_id="cat_001",
            image_id=uuid4(),
            mime_type="image/svg+xml",
        )
        assert item.entity_id == "cat_001"
        assert item.mime_type == "image/svg+xml"

    def test_missing_entity_id_raises(self):
        """Отсутствие entity_id → ValidationError."""
        with pytest.raises(ValidationError):
            ImageMappingItem(image_id=uuid4(), mime_type="image/jpeg")

    def test_missing_image_id_raises(self):
        """Отсутствие image_id → ValidationError."""
        with pytest.raises(ValidationError):
            ImageMappingItem(entity_id="cat_001", mime_type="image/jpeg")


# ==================== ImageMappingResponse ====================


class TestImageMappingResponse:
    """Тесты схемы ответа маппингов."""

    def test_valid_category_response(self):
        """Маппинг категорий с пустым списком — ok."""
        resp = ImageMappingResponse(
            entity_type=EntityType.CATEGORY,
            mappings=[],
        )
        assert resp.entity_type == EntityType.CATEGORY
        assert resp.mappings == []

    def test_valid_merchant_response_with_items(self):
        """Маппинг мерчантов с элементами — ok."""
        item = ImageMappingItem(
            entity_id="merch_1",
            image_id=uuid4(),
            mime_type="image/svg+xml",
        )
        resp = ImageMappingResponse(
            entity_type=EntityType.MERCHANT,
            mappings=[item],
        )
        assert resp.entity_type == EntityType.MERCHANT
        assert len(resp.mappings) == 1


# ==================== UpdateUserAvatarRequest ====================


class TestUpdateUserAvatarRequest:
    """Тесты схемы обновления аватарки пользователя."""

    def test_valid_uuid(self):
        """Корректный UUID → объект создаётся."""
        avatar_id = uuid4()
        req = UpdateUserAvatarRequest(image_id=avatar_id)
        assert req.image_id == avatar_id

    def test_missing_image_id_raises(self):
        """Отсутствие image_id → ValidationError."""
        with pytest.raises(ValidationError):
            UpdateUserAvatarRequest()


# ==================== UploadImageRequest ====================


class TestUploadImageRequest:
    """Тесты схемы загрузки изображения (admin endpoint)."""

    def test_valid_jpeg_mime_type(self):
        """image/jpeg → ok."""
        req = UploadImageRequest(
            entity_type=EntityType.CATEGORY,
            file_data=b"\xff\xd8\xff",
            mime_type="image/jpeg",
        )
        assert req.mime_type == "image/jpeg"

    def test_valid_png_mime_type(self):
        """image/png → ok."""
        req = UploadImageRequest(
            entity_type=EntityType.MERCHANT,
            file_data=b"\x89PNG",
            mime_type="image/png",
        )
        assert req.mime_type == "image/png"

    def test_svg_mime_type_raises(self):
        """image/svg+xml не в паттерне → ValidationError.

        Тестовые данные (testData/images_data.json) используют SVG,
        но UploadImageRequest намеренно ограничивает форматы.
        """
        with pytest.raises(ValidationError):
            UploadImageRequest(
                entity_type=EntityType.USER_AVATAR,
                file_data=b"<svg/>",
                mime_type="image/svg+xml",
            )
