from beanie import PydanticObjectId


from . import flows


async def delete(order_id: PydanticObjectId):
    await flows.delete(order_id)
