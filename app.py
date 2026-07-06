from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auto_runner import start_background_runner, tick_once
from db import fetch_all, init_db
from sim_engine import (
    app_settings,
    dashboard_data,
    export_novel_markdown,
    generate_conversation_for_scene,
    generate_missing_conversations,
    get_director_room,
    get_writer_room,
    get_serial_room,
    get_today_story,
    get_gossip_room,
    get_share_room,
    export_share_card_markdown,
    generate_gossip_report,
    get_story_by_day,
    export_serial_markdown,
    generate_daily_story,
    generate_missing_daily_stories,
    get_people,
    get_person,
    get_storylines,
    init_world,
    protagonist_candidates,
    reset_world,
    simulate_day,
    update_settings,
)

app = FastAPI(title="M6 SimWorld Mobile v7")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup() -> None:
    init_db()
    init_world(100)
    start_background_runner()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, **dashboard_data()})


@app.post("/simulate-day")
def simulate_one_day(ai: int = 0):
    simulate_day(use_ai=bool(ai))
    return RedirectResponse(url="/", status_code=303)


@app.post("/simulate-days")
def simulate_days(days: int = 7, ai: int = 0):
    days = max(1, min(days, 90))
    for _ in range(days):
        simulate_day(use_ai=bool(ai))
    return RedirectResponse(url="/", status_code=303)


@app.post("/reset")
def reset():
    reset_world()
    init_world(100)
    return RedirectResponse(url="/", status_code=303)


@app.get("/people", response_class=HTMLResponse)
def people(request: Request, q: str = ""):
    return templates.TemplateResponse("people.html", {"request": request, "people": get_people(q), "q": q})


@app.get("/person/{person_id}", response_class=HTMLResponse)
def person(request: Request, person_id: int):
    data = get_person(person_id)
    if not data:
        raise HTTPException(status_code=404, detail="Person not found")
    return templates.TemplateResponse("person.html", {"request": request, **data})


@app.get("/events", response_class=HTMLResponse)
def events(request: Request, day: int | None = None):
    if day is None:
        rows = fetch_all("SELECT * FROM events ORDER BY day DESC, hour DESC, importance DESC LIMIT 500")
    else:
        rows = fetch_all("SELECT * FROM events WHERE day=? ORDER BY hour DESC, importance DESC", (day,))
    return templates.TemplateResponse("events.html", {"request": request, "events": rows, "day_filter": day})


@app.get("/storylines", response_class=HTMLResponse)
def storylines(request: Request):
    return templates.TemplateResponse("storylines.html", {"request": request, **get_storylines()})


@app.get("/director", response_class=HTMLResponse)
def director(request: Request):
    return templates.TemplateResponse("director.html", {"request": request, **get_director_room()})


@app.get("/writer", response_class=HTMLResponse)
def writer(request: Request):
    return templates.TemplateResponse("writer.html", {"request": request, **get_writer_room()})


@app.get("/gossip", response_class=HTMLResponse)
def gossip(request: Request):
    return templates.TemplateResponse("gossip.html", {"request": request, **get_gossip_room()})


@app.post("/gossip/generate")
def gossip_generate():
    generate_gossip_report()
    return RedirectResponse(url="/gossip", status_code=303)


@app.get("/share", response_class=HTMLResponse)
def share(request: Request):
    return templates.TemplateResponse("share.html", {"request": request, **get_share_room()})


@app.get("/export/share-card")
def export_share_card():
    path = export_share_card_markdown()
    return FileResponse(path, media_type="text/markdown; charset=utf-8", filename="simworld_share_card_v7.md")


@app.get("/today", response_class=HTMLResponse)
def today_story(request: Request):
    return templates.TemplateResponse("today.html", {"request": request, **get_today_story()})


@app.get("/serial", response_class=HTMLResponse)
def serial_room(request: Request):
    return templates.TemplateResponse("serial.html", {"request": request, **get_serial_room()})


@app.get("/serial/{day}", response_class=HTMLResponse)
def serial_day(request: Request, day: int):
    data = get_story_by_day(day)
    if not data:
        raise HTTPException(status_code=404, detail="Story not found")
    return templates.TemplateResponse("today.html", {"request": request, "day": day, "recent_stories": [], **data})


@app.post("/serial/generate-today")
def serial_generate_today(ai: int = 0):
    generate_daily_story(use_ai=bool(ai), force=True)
    return RedirectResponse(url="/today", status_code=303)


@app.post("/serial/backfill")
def serial_backfill(limit: int = 30, ai: int = 0):
    generate_missing_daily_stories(limit=limit, use_ai=bool(ai))
    return RedirectResponse(url="/serial", status_code=303)


@app.post("/writer/generate")
def writer_generate(limit: int = 8, ai: int = 0):
    generate_missing_conversations(limit=limit, use_ai=bool(ai))
    return RedirectResponse(url="/writer", status_code=303)


@app.post("/scene/{scene_id}/generate")
def scene_generate(scene_id: int, ai: int = 0):
    generate_conversation_for_scene(scene_id, use_ai=bool(ai), force=True)
    return RedirectResponse(url="/writer", status_code=303)


@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "settings": app_settings()})


@app.post("/settings")
def save_settings(
    auto_enabled: int = 0,
    interval_minutes: int = 1440,
    auto_use_ai: int = 0,
    auto_story_enabled: int = 0,
    auto_story_export: int = 0,
    auto_story_use_ai: int = 0,
    auto_story_catchup: int = 0,
):
    update_settings(
        bool(auto_enabled),
        interval_minutes,
        bool(auto_use_ai),
        bool(auto_story_enabled),
        bool(auto_story_export),
        bool(auto_story_use_ai),
        bool(auto_story_catchup),
    )
    return RedirectResponse(url="/settings", status_code=303)


@app.post("/auto-tick")
def auto_tick_now():
    tick_once()
    return RedirectResponse(url="/", status_code=303)


@app.get("/export/novel")
def export_novel():
    path = export_novel_markdown()
    return FileResponse(path, media_type="text/markdown; charset=utf-8", filename="simworld_novel_seed_v7.md")


@app.get("/export/serial")
def export_serial():
    path = export_serial_markdown()
    return FileResponse(path, media_type="text/markdown; charset=utf-8", filename="simworld_serial_v7.md")


@app.get("/api/state")
def api_state():
    data = dashboard_data()
    return {
        "version": "v7",
        "day": data["day"],
        "people_count": data["people_count"],
        "auto_enabled": data["auto_enabled"],
        "auto_interval_minutes": data["auto_interval_minutes"],
        "average": {k: round(float(data["avg"][k]), 1) for k in ["happiness", "energy", "health", "wealth"]},
        "gossip_url": "/gossip",
        "protagonists": [
            {"id": p["id"], "name": p["name"], "score": p["story_score"], "goal": p["life_goal"]}
            for p in protagonist_candidates(5)
        ],
    }


@app.post("/api/simulate-day")
def api_simulate_day(ai: int = 0):
    day = simulate_day(use_ai=bool(ai))
    return {"ok": True, "day": day}
