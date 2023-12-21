import re

import jinja2
from jinja2 import FunctionLoader
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src import models, schemas
from src.core import enums, errors

from . import service


async def get(session: AsyncSession, render_id: int) -> models.RenderConfig:
    parser = await service.get(session, render_id)
    if not parser:
        raise errors.ApiHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[
                errors.ApiException(
                    msg=f"A Render Config with this id={render_id} does not exist.",
                    code="not_found",
                )
            ],
        )
    return parser


def get_order_configs(
    order_model: schemas.OrderReadSystem | models.PreOrderReadSystem,
    *,
    is_preorder: bool = False,
    creds: bool = False,
    is_gold: bool = False,
    with_response: bool = False,
    response_checked: bool = False,
) -> list[str]:
    if is_preorder:
        configs = ["pre-order"]
    else:
        configs = ["order"]
    if creds:
        configs.extend([order_model.info.game, f"{order_model.info.game}-cd"])
    else:
        configs.append(order_model.info.game)
    if is_preorder:
        configs.append(["pre-eta-price" if not is_gold else "pre-eta-price-gold"])
    else:
        configs.append("eta-price" if not is_gold else "eta-price-gold")
    if with_response:
        configs.append("response" if not response_checked else "response-check")
    return configs


async def check_availability_all_render_config_order(
    session: AsyncSession,
    integration: enums.Integration,
    order_model: schemas.OrderReadSystem | models.PreOrderReadSystem,
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
    session: AsyncSession,
    integration: enums.Integration,
    templates: list[str],
    *,
    data: dict,
) -> str:
    resp: list[str] = []
    for index, render_config_name in enumerate(templates, 1):
        render_config = await service.get_by_name(session, integration, render_config_name)
        if render_config:
            template = jinja2.Template(render_config.binary)
            rendered = template.render(**data)
            is_empty = len(rendered.replace("\n", "").replace("<br>", "").replace(" ", "")) < 1
            if not render_config.allow_separator_top and (len(resp) > 0 or is_empty):
                resp.pop(-1)
            if not is_empty:
                resp.append(rendered)
            if index < len(templates) and not is_empty:
                resp.append(f"{render_config.separator} <br>")
    rendered = "".join(resp)
    return _render_template("rendered_order", data={"rendered_order": rendered})


async def generate_body(
    session: AsyncSession,
    integration: enums.Integration,
    order: schemas.OrderReadSystem | models.PreOrderReadSystem,
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
