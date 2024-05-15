from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/main", response_class=HTMLResponse)
async def main(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html"
    )
