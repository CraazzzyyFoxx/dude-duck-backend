from pydantic.errors import PydanticValueError


class DudeDuckError(Exception):
    pass


class NotFoundError(PydanticValueError):
    code = "not_found"
    msg_template = "{msg} not_found"


class FieldNotFoundError(PydanticValueError):
    code = "not_found.field"
    msg_template = "{msg} not_found.field"


class ModelNotFoundError(PydanticValueError):
    code = "not_found.model"
    msg_template = "{msg}"


class ExistsError(PydanticValueError):
    code = "exists"
    msg_template = "{msg}"


class InvalidConfigurationError(PydanticValueError):
    code = "invalid.configuration"
    msg_template = "{msg}"


class InvalidFilterError(PydanticValueError):
    code = "invalid.filter"
    msg_template = "{msg}"


class InvalidUsernameError(PydanticValueError):
    code = "invalid.username"
    msg_template = "{msg}"


class InvalidPasswordError(PydanticValueError):
    code = "invalid.password"
    msg_template = "{msg}"
