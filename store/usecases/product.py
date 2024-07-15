from typing import List, Optional
from uuid import UUID

from pydantic import UUID4
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import pymongo
from store.db.mongo import db_client
from store.models.product import ProductModel
from store.schemas.product import ProductIn, ProductOut, ProductUpdate, ProductUpdateOut
from store.core.exceptions import NotFoundException
from datetime import datetime


class ProductUsecase:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient = db_client.get()
        self.database: AsyncIOMotorDatabase = self.client.get_database()
        self.collection = self.database.get_collection("products")

    async def create(self, body: ProductIn) -> ProductOut:
        product_model = ProductModel(**body.model_dump())
        await self.collection.insert_one(product_model.model_dump())

        return ProductOut(**product_model.model_dump())

    async def get(self, id: UUID) -> ProductOut:
        result = await self.collection.find_one({"id": id})

        if not result:
            raise NotFoundException(message=f"Product not found with filter: {id}")

        return ProductOut(**result)

    async def query(self, price_min: Optional[float] = None, price_max: Optional[float] = None) -> List[ProductOut]:
        products = [ProductOut(**item) async for item in self.collection.find()]

        if price_min is not None:
            products = [product for product in products if product.price > price_min]
        if price_max is not None:
            products = [product for product in products if product.price < price_max]

        return products

    async def update(self, id: UUID4, body: ProductUpdate) -> ProductUpdateOut:
        # Buscar o produto pelo id
        product = await self.collection.find_one({"id": id})

        if not product:
            raise NotFoundException(f"Produto com ID {id} não encontrado")

        # Atualizar os campos do produto com os valores do body
        for field, value in body.dict().items():
            if value is not None:
                setattr(product, field, value)

        # Atualizar o campo updated_at para o horário atual
        product['updated_at'] = datetime.now()

        # Salvar o produto atualizado no banco de dados
        result = await self.collection.find_one_and_update(
            filter={"id": id},
            update={"$set": product},
            return_document=pymongo.ReturnDocument.AFTER,
        )

        return ProductUpdateOut(**result)

    async def delete(self, id: UUID) -> bool:
        product = await self.collection.find_one({"id": id})
        if not product:
            raise NotFoundException(message=f"Product not found with filter: {id}")

        result = await self.collection.delete_one({"id": id})

        return True if result.deleted_count > 0 else False
    
product_usecase = ProductUsecase()
