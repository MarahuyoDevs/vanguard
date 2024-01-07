import base64
import json
from math import e
import os
from types import ModuleType
from typing import Any, Generator, Union
import jinja2
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import HTTPException, Request, Response
from jinja2 import Environment, FileSystemLoader, Template
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
import importlib.util

FILE_CONVENTIONS = ["layout.html", "page.html", "script.py", "load.py", "404.html"]


class VanguardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, directory: str, base_template):
        super().__init__(app)
        self.app = app
        self.base_template = Environment(loader=FileSystemLoader(base_template))
        self.directory = directory
        self.routes = {}

        for root, convention, route in self.walk(directory):
            if convention in ["script.py", "load.py"]:
                module = self.loadPython(convention, root)
                if module:
                    self.routes.setdefault(route, {}).update({convention: module})
            elif convention in ["layout.html", "page.html", "404.html"]:
                template = self.loadTemplate(convention, root)
                self.routes.setdefault(route, {}).update({convention: template})

    def loadTemplate(self, name: str, directory: str) -> Template:
        if not os.path.exists(directory + f"/{name}"):
            raise OSError(
                f"Template file '{name}' does not exist in directory '{directory}'"
            )
        template = Environment(
            loader=FileSystemLoader(directory),
        ).get_template(name)
        return template

    def walk(self, directory: str) -> Generator[tuple[str, str, str], Any, None]:
        for root, _, files in os.walk(directory):
            for convention in FILE_CONVENTIONS:
                if convention in files:
                    yield root, convention, root.replace(directory, "").replace(
                        "\\", "/"
                    ).replace("[", "{").replace("]", "}").replace(
                        "\\routes\\", "/"
                    ) + "/"

    def loadPython(self, name: str, directory: str) -> str | ModuleType | None:
        if not os.path.exists(directory + f"/{name}"):
            return None

        if name == "script.py":
            with open(directory + f"/{name}", "r") as f:
                return f.read()

        spec = importlib.util.spec_from_file_location(name, directory + f"/{name}")
        module = importlib.util.module_from_spec(spec)  # type: ignore
        try:
            spec.loader.exec_module(module)  # type: ignore
        except Exception as e:
            print(f"Error executing module: {e}")
            return None
        return module

    async def dispatch(
        self, request: Request, call_next
    ) -> HTMLResponse | JSONResponse | Response | None:
        try:
            url_path = (
                request.url.path + "/" if request.url.path != "/" else request.url.path
            )
            if url_path in self.routes:
                if (
                    request.headers.get("X-Requested-With") == "XMLHttpRequest"
                    and request.headers.get("Content-Type") == "application/python"
                ):
                    return await self.renderHTML(request, "partial")
                else:
                    if "text/html" in request.headers.get("accept", "").split(","):
                        return await self.renderHTML(request, "full")
                if url_path not in self.routes:
                    raise HTTPException(detail="Page Not Found", status_code=404)
            else:
                return await call_next(request)
        except HTTPException as e:
            return HTMLResponse(
                content=self.base_template.get_template("404.html").render(
                    request=request, error_message=e.detail, error_code=e.status_code
                ),
                status_code=e.status_code,
            )

    async def render(
        self, url_path: str, request: Request, mode: str = "full"
    ) -> Union[HTMLResponse, JSONResponse]:
        loaded_data = {}

        if "load.py" in self.routes[url_path]:
            loaded_data = await self.routes[url_path]["load.py"].load(request)
        html = (
            self.routes[url_path]["page.html"].render(**loaded_data)
            if loaded_data
            else self.routes[url_path]["page.html"].render()
        )

        components = url_path.strip("/").split("/")
        routes = [
            "/" + "/".join(components[: i + 1]) + "/"
            for i in range(len(components))
            if i != 0
        ][::-1]
        routes = [route for route in routes if route != "//"]

        for route in routes:
            if "layout.html" in self.routes[route]:
                html = self.routes[route]["layout.html"].render(slot=html)

        if url_path == "/" and "layout.html" in self.routes[url_path]:
            html = self.routes[url_path]["layout.html"].render(slot=html)

        if mode == "full":
            return HTMLResponse(
                content=self.base_template.get_template("app.html").render(
                    slot=html, script=self.routes[url_path]["script.py"], **loaded_data
                ),
                status_code=200,
            )
        else:
            return JSONResponse(
                content={
                    "body": html,
                    "script": self.routes[url_path]["script.py"],
                    **loaded_data,
                }
            )

    async def renderHTML(
        self, request: Request, mode: str
    ) -> HTMLResponse | JSONResponse:
        url_path = (
            request.url.path + "/"
            if request.url.path != "/" and request.url.path[-1] != "/"
            else request.url.path
        )
        try:
            if "page.html" not in self.routes[url_path]:
                raise HTTPException(status_code=404)
            return await self.render(url_path, request, mode)
        except HTTPException as e:
            error_template = self.routes[url_path].get(
                "404.html"
            ) or self.base_template.get_template("404.html")
            return HTMLResponse(
                content=error_template.render(request=request, error_message=e.detail),
                status_code=404,
            )
