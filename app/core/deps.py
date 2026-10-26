from typing import Annotated

from fastapi import Depends, Request


async def form_fields(request: Request) -> dict[str, str]:
    form = await request.form()
    return {k: v for k, v in form.items() if isinstance(v, str)}


FormFields = Annotated[dict[str, str], Depends(form_fields)]
