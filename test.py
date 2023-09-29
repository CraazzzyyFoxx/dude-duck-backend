import re

from pydantic import BaseModel, EmailStr


class Test(BaseModel):
    email: EmailStr


print(Test(email="zintzov.kkirill@yandex.ru"))

print(re.fullmatch(r"([a-zA-Z0-9_-]+)", "carnego"))
