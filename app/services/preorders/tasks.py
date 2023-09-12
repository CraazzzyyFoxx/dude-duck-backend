from beanie import PydanticObjectId


from . import flows


async def delete(order_id: str):
    await flows.delete(PydanticObjectId(order_id))
