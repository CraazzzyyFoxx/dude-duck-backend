from src import models

path_resolver: dict[models.NotificationType, str] = {
    models.NotificationType.ORDER_RESPONSE_APPROVE: "notification/response_approved",
    models.NotificationType.ORDER_RESPONSE_DECLINE: "notification/response_declined",
    models.NotificationType.ORDER_RESPONSE_ADMIN: "notification/order_admins",
    models.NotificationType.LOGGED_NOTIFY: "notification/logged",
    models.NotificationType.REGISTERED_NOTIFY: "notification/registered",
    models.NotificationType.REQUEST_VERIFY: "notification/request_verify",
    models.NotificationType.VERIFIED_NOTIFY: "notification/verified",
    models.NotificationType.ORDER_CLOSE_REQUEST: "notification/order_close_request",
    models.NotificationType.ORDER_SENT_NOTIFY: "notification/order_sent",
    models.NotificationType.ORDER_EDITED_NOTIFY: "notification/order_edited",
    models.NotificationType.ORDER_DELETED_NOTIFY: "notification/order_deleted",
    models.NotificationType.RESPONSE_CHOSE_NOTIFY: "notification/response_chose",
    models.NotificationType.ORDER_PAID_NOTIFY: "notification/order_paid",
}
