"""Run once per day with Windows Task Scheduler: advance the world and create today's serial story."""
from db import init_db, get_state, set_state
from sim_engine import init_world, simulate_day, generate_daily_story, current_day

if __name__ == "__main__":
    init_db()
    init_world(100)
    # Make daily task useful even if web settings were never opened.
    set_state("auto_story_enabled", get_state("auto_story_enabled", "1"))
    day = simulate_day(use_ai=get_state("auto_use_ai", "0") == "1")
    generate_daily_story(day, use_ai=get_state("auto_story_use_ai", "0") == "1")
    print(f"SimWorld v7 auto story completed: Day {current_day()}")
