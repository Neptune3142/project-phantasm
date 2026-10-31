from app.routes import (  # noqa: F401
    accounts,
    approvals,
    dashboard,
    exorcism,
    health,
    incidents,
    integrations,
    simulation,
)

ROUTERS = [
    health.router,
    accounts.router,
    exorcism.router,
    incidents.router,
    dashboard.router,
    integrations.router,
    approvals.router,
    simulation.router,
]
