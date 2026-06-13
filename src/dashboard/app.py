from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqladmin import Admin

from src.database.engine import engine, get_db
from src.helpers.person_merge import merge_persons
from src.dashboard.views import AssembledMessageAdmin, PersonAdmin, WeeklySummaryAdmin
from src.dashboard.queries import get_stats, get_diagnostics, get_person_names

app = FastAPI(title="Family Atlas Dashboard")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

admin = Admin(app, engine, title="Family Atlas")  # CRUD на /admin
admin.add_view(AssembledMessageAdmin)
admin.add_view(PersonAdmin)
admin.add_view(WeeklySummaryAdmin)


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/stats")
async def stats(request: Request):
    async with get_db() as session:
        data = await get_stats(session)
    return templates.TemplateResponse(request, "stats.html", {"s": data})


@app.get("/diagnostics")
async def diagnostics(request: Request):
    async with get_db() as session:
        rows = await get_diagnostics(session)
    return templates.TemplateResponse(request, "diagnostics.html", {"rows": rows})


@app.get("/merge")
async def merge_page(request: Request, msg: str | None = None):
    async with get_db() as session:
        names = await get_person_names(session)
    return templates.TemplateResponse(request, "merge.html", {"names": names, "msg": msg})


@app.post("/merge")
async def merge_action(source: str = Form(...), target: str = Form(...)):
    async with get_db() as session:
        result = await merge_persons(session, source, target)
    return RedirectResponse(url=f"/merge?msg={result['msg']}", status_code=303)