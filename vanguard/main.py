from pypox import Pypox
import os
from fastapi import FastAPI
from vanguard.middleware import VanguardMiddleware
from starlette.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app: FastAPI = Pypox(os.path.dirname(__file__))()

app.mount(
    "/static",
    StaticFiles(directory=os.path.dirname(__file__) + "/static"),
    name="static",
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    VanguardMiddleware,
    directory=os.path.dirname(__file__) + "/routes",
    base_template=os.path.dirname(__file__) + "/static",
)
