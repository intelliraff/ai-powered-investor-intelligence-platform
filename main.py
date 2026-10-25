from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database.create_table import create_tables

from routes.dashboard import router as dashboard_router
from routes.health import router as health_router
from routes.ingestion import router as ingestion_router
from routes.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="Investor Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Static files
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

templates = Jinja2Templates(directory="templates")


# Dashboard
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={},
    )


# API routes
app.include_router(
    health_router,
    tags=["Health"],
)

app.include_router(
    dashboard_router,
    prefix="/api",
    tags=["Dashboard"],
)

app.include_router(
    ingestion_router,
    tags=["Ingestion"],
)

app.include_router(
    chat_router,
    tags=["Chat"],
)