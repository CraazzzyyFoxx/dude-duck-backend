import re

import jinja2
from jinja2 import FunctionLoader
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.core import enums, errors
from src.services.order import schemas as order_schemas
from src.services.preorder import models as preorder_models

from . import models, service


async def get(session: AsyncSession, render_id: int) -> models.RenderConfig:
    parser = await service.get(session, render_id)
    if not parser:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(msg=f"A Render Config with this id={render_id} does not exist.", code="not_found")
            ],
        )
    return parser


def get_order_configs(
    order_model: order_schemas.OrderReadSystem | preorder_models.PreOrderReadSystem,
    *,
    is_preorder: bool = False,
    creds: bool = False,
    is_gold: bool = False,
    with_response: bool = False,
    response_checked: bool = False,
) -> list[str]:
    game = order_model.info.game if not creds else f"{order_model.info.game}-cd"
    resp = "response" if not response_checked else "response-check"
    if is_preorder:
        configs = ["pre-order", game, "pre-eta-price" if not is_gold else "pre-eta-price-gold"]
    else:
        configs = ["order", game, "eta-price" if not is_gold else "eta-price-gold"]
    if with_response:
        configs.append(resp)
    return configs


def get_order_response_configs(
    order_model: order_schemas.OrderReadSystem | preorder_models.PreOrderReadSystem,
    *,
    pre: bool = False,
    creds: bool = False,
    checked: bool = False,
    is_gold: bool = False,
) -> list[str]:
    game = order_model.info.game if not creds else f"{order_model.info.game}-cd"
    resp = "response" if not checked else "response-check"
    if pre:
        return ["pre-order", game, "pre-eta-price" if not is_gold else "pre-eta-price-gold", resp]
    return ["order", game, "eta-price" if not is_gold else "eta-price-gold", resp]


async def check_availability_all_render_config_order(
    session: AsyncSession,
    integration: enums.Integration,
    order_model: order_schemas.OrderReadSystem | preorder_models.PreOrderReadSystem,
) -> tuple[bool, list[str]]:
    configs = await service.get_all_configs_for_order(session, integration, order_model)
    names = service.get_all_config_names(order_model)
    exist_names = [cfg.name for cfg in configs]
    if len(configs) != len(names):
        missing = []
        for name in names:
            if name not in exist_names:
                missing.append(name)
        return False, missing
    return True, []


def _render(pre_render: str) -> str:
    rendered = pre_render.replace("<br>", "\n")
    rendered = re.sub(" +", " ", rendered).replace(" .", ".").replace(" ,", ",")
    rendered = "\n".join(line.strip() for line in rendered.split("\n"))
    rendered = rendered.replace("{FOURSPACES}", "    ")
    return rendered


def _render_template(template_name: str, data: dict | None = None) -> str:
    template = _get_template_env().get_template(f"{template_name}.j2")
    if data is None:
        data = {}
    rendered = template.render(**data).replace("\n", " ")
    return _render(rendered)


def loadTpl(path):
    if path == "rendered_order.j2":
        return """{{rendered_order}}"""


def _get_template_env() -> jinja2.Environment:
    if not getattr(_get_template_env, "template_env", None):
        env = jinja2.Environment(
            loader=FunctionLoader(loadTpl),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        _get_template_env.template_env = env
    return _get_template_env.template_env


async def get_order_text(
    session: AsyncSession, integration: enums.Integration, templates: list[str], *, data: dict
) -> str:
    resp: list[str] = []
    last_len = 0
    for index, render_config_name in enumerate(templates, 1):
        render_config = await service.get_by_name(session, integration, render_config_name)
        if render_config:
            template = jinja2.Template(render_config.binary)
            rendered = template.render(**data)
            if not render_config.allow_separator_top and len(resp) > 0:
                resp.pop(-1)
            if len(rendered.replace("\n", "").replace("<br>", "").replace(" ", "")) > 1:
                resp.append(rendered)
            if index < len(templates) and len(resp) > last_len:
                resp.append(f"{render_config.separator} <br>")
            last_len = len(resp)
    rendered = "".join(resp)
    return _render_template("rendered_order", data={"rendered_order": rendered})


async def generate_body(
    session: AsyncSession,
    integration: enums.Integration,
    order: order_schemas.OrderReadSystem | preorder_models.PreOrderReadSystem,
    configs: list[str],
    is_preorder: bool,
    is_gold: bool,
) -> tuple[bool, str]:
    status, missing = await check_availability_all_render_config_order(session, integration, order)
    if not status:
        return status, f"Some configs for order missing, configs=[{', '.join(missing)}]"
    if not configs:
        configs = get_order_configs(order, is_preorder=is_preorder, is_gold=is_gold)
    text = await get_order_text(session, integration, configs, data={"order": order})
    return status, text
