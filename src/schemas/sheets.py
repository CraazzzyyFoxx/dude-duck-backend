from src.models.integrations.message import CreateOrderMessage, DeleteOrderMessage, UpdateOrderMessage

__all__ = ("CreateOrderSheetMessage", "UpdateOrderSheetMessage", "DeleteOrderSheetMessage")


class CreateOrderSheetMessage(CreateOrderMessage):
    order_id: str


class UpdateOrderSheetMessage(UpdateOrderMessage):
    order_id: str


class DeleteOrderSheetMessage(DeleteOrderMessage):
    order_id: str
