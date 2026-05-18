from apscheduler.schedulers.background import BackgroundScheduler
from mcp_tools import mcp

scheduler = BackgroundScheduler()

def check_interviews():

    result = mcp.run(
        "gmail",
        action="check_interviews"
    )

    if result["status"] == "ok":

        interviews = result["data"].get(
            "interviews",
            []
        )

        if interviews:

            mcp.run(
                "notification",
                title="Interview Alert",
                message=f"{len(interviews)} interview emails found"
            )

scheduler.add_job(
    check_interviews,
    "interval",
    minutes=30
)

