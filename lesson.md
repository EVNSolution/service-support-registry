Source: https://lessons.md

# service-support-registry Lessons.md

Support registry owns ticket and response truth, but it does not own notification delivery success. When admin response save succeeds and the inbox handoff fails, the service should still be treated as healthy because the write truth stayed local.

The honest production smoke is `/api/ticket/health/ -> 200` plus `/api/ticket/tickets/ -> 401` without a token. That proves the route, service startup, and auth layer without creating a real production support ticket.
