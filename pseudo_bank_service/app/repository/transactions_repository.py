from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.orm import selectinload
from app.models import Bank_Account, Bank, Transaction, Merchant, Category, MCC_Category
from app.schemas import (
    CategoryCreate, MCCCategoryCreate, MerchantCreate,
    BankCreate, BankAccountCreate, TransactionCreate
)

class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_account_bank(self, bank_account_hash: str):
        """Получение счёта"""
        result = await self.db.execute(
            select(Bank_Account).where(
                Bank_Account.bank_account_hash == bank_account_hash
            )
        )
        return result.scalar_one_or_none()

    async def export_account_data(self, account_hash: str):
        """Экспорт всех связанных данных по счёту"""
        account = await self.get_account_bank(account_hash)
        if not account:
            return None

        # Получаем банк
        bank_result = await self.db.execute(
            select(Bank).where(Bank.id == account.bank_id)
        )
        bank = bank_result.scalar_one()

        # Получаем транзакции с мерчантами и категориями
        transactions_result = await self.db.execute(
            select(Transaction)
            .where(Transaction.bank_account_id == account.id)
            .options(
                selectinload(Transaction.merchant).selectinload(
                    Merchant.category),
                selectinload(Transaction.category)
            )
        )
        transactions = transactions_result.scalars().all()

        # Собираем ID для категорий и мерчантов
        merchant_ids = {t.merchant_id for t in transactions if t.merchant_id}
        category_ids = {t.category_id for t in transactions}
        if merchant_ids:
            merchant_categories = await self.db.execute(
                select(Merchant.category_id)
                .where(Merchant.id.in_(merchant_ids))
            )
            category_ids.update(
                m_id for m_id, in merchant_categories.fetchall() if m_id)

        # Получаем все категории
        categories = []
        if category_ids:
            categories_result = await self.db.execute(
                select(Category).where(Category.id.in_(category_ids))
            )
            categories = categories_result.scalars().all()

        # Получаем MCC
        mccs = []
        if category_ids:
            mcc_result = await self.db.execute(
                select(MCC_Category).where(
                    MCC_Category.category_id.in_(category_ids))
            )
            mccs = mcc_result.scalars().all()

        # Получаем мерчантов (уже загружены через selectinload, но можно уточнить)
        merchants = [t.merchant for t in transactions if t.merchant]

        return {
            "account": account,
            "bank": bank,
            "transactions": transactions,
            "merchants": merchants,
            "categories": categories,
            "mccs": mccs
        }

    @staticmethod
    def to_dict(obj):
        """Утилита для сериализации SQLAlchemy-объектов"""
        if hasattr(obj, '__table__'):
            return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        return obj

    async def create_category(self, category_data: CategoryCreate):
        """Создание категории"""
        category = Category(**category_data.model_dump())
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def create_mcc_category(self, mcc_data: MCCCategoryCreate):
        """Создание MCC категории"""
        mcc = MCC_Category(**mcc_data.model_dump())
        self.db.add(mcc)
        await self.db.commit()
        await self.db.refresh(mcc)
        return mcc

    async def create_merchant(self, merchant_data: MerchantCreate):
        """Создание мерчанта"""
        merchant = Merchant(**merchant_data.model_dump())
        self.db.add(merchant)
        await self.db.commit()
        await self.db.refresh(merchant)
        return merchant

    async def create_bank(self, bank_data: BankCreate):
        """Создание банка"""
        bank = Bank(**bank_data.model_dump())
        self.db.add(bank)
        await self.db.commit()
        await self.db.refresh(bank)
        return bank

    async def create_bank_account(self, account_data: BankAccountCreate):
        """Создание банковского счета"""
        account = Bank_Account(**account_data.model_dump())
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def create_transaction(self, transaction_data: TransactionCreate):
        """Создание транзакции"""
        transaction = Transaction(**transaction_data.model_dump())
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def bulk_create_categories(self, categories: list[CategoryCreate]):
        """Массовое создание категорий"""
        stmt = insert(Category).values([cat.model_dump() for cat in categories])
        stmt = stmt.on_conflict_do_nothing(index_elements=['id'])
        await self.db.execute(stmt)
        await self.db.commit()
        return {"created": len(categories)}

    async def bulk_create_mcc_categories(self, mcc_list: list[MCCCategoryCreate]):
        """Массовое создание MCC категорий"""
        stmt = insert(MCC_Category).values([mcc.model_dump() for mcc in mcc_list])
        stmt = stmt.on_conflict_do_nothing(index_elements=['mcc'])
        await self.db.execute(stmt)
        await self.db.commit()
        return {"created": len(mcc_list)}

    async def bulk_create_merchants(self, merchants: list[MerchantCreate]):
        """Массовое создание мерчантов"""
        stmt = insert(Merchant).values([m.model_dump() for m in merchants])
        stmt = stmt.on_conflict_do_nothing(index_elements=['id'])
        await self.db.execute(stmt)
        await self.db.commit()
        return {"created": len(merchants)}

    async def bulk_create_banks(self, banks: list[BankCreate]):
        """Массовое создание банков"""
        stmt = insert(Bank).values([b.model_dump() for b in banks])
        stmt = stmt.on_conflict_do_nothing(index_elements=['id'])
        await self.db.execute(stmt)
        await self.db.commit()
        return {"created": len(banks)}

    async def bulk_create_bank_accounts(self, accounts: list[BankAccountCreate]):
        """Массовое создание банковских счетов"""
        stmt = insert(Bank_Account).values([acc.model_dump() for acc in accounts])
        stmt = stmt.on_conflict_do_nothing(index_elements=['bank_account_hash'])
        await self.db.execute(stmt)
        await self.db.commit()
        return {"created": len(accounts)}

    async def bulk_create_transactions(self, transactions: list[TransactionCreate]):
        """Массовое создание транзакций"""
        trans_list = []
        for t in transactions:
            trans_list.append(t.model_dump())

        for trans_data in trans_list:
            trans = Transaction(**trans_data)
            self.db.add(trans)

        await self.db.commit()
        return {"created": len(transactions)}
