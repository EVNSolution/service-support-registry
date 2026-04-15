# service-support-registry

## Purpose / Boundary

이 repo는 지원 정본 runtime 이다.

현재 역할:
- `SupportTicket` CRUD
- `SupportTicketResponse` CRUD
- 처리 상태, priority 관리
- authenticated ticket create와 admin handling API
- admin response 저장 후 `service-notification-hub` inbox handoff
- deterministic bootstrap seed command

포함하지 않음:
- push send
- inbox notifications
- announcement posting
- approval truth
- attachment binary storage
- 플랫폼 전체 compose와 gateway 설정

## Runtime Contract / Local Role

- compose service는 `support-registry-api` 다.
- gateway prefix는 `/api/ticket/` 다.
- support response 저장은 이 repo의 truth이고, notification handoff는 best-effort 다.

## Local Run / Verification

- local run: `. .venv/bin/activate && python manage.py runserver 0.0.0.0:8000`
- local test: `. .venv/bin/activate && python manage.py test -v 2`

## Image Build / Deploy Contract

- GitHub Actions workflow 이름은 `Build service-support-registry image` 다.
- workflow는 immutable `service-support-registry:<sha>` 이미지를 ECR로 publish 한다.
- shared ECS deploy, ALB, ACM, Route53 관리는 `../infra-ev-dashboard-platform/` 이 소유한다.

## Environment Files And Safety Notes

- notification handoff 실패와 support response 저장 실패를 같은 것으로 취급하지 않는다.
- prod proof는 mutation보다 `health 200 + protected 401` 조합을 우선한다.

## Key Tests Or Verification Commands

- full Django tests: `. .venv/bin/activate && python manage.py test -v 2`
- honest smoke는 `/api/ticket/health/` 와 `/api/ticket/tickets/` protected path 조합이다.

## Root Docs / Runbooks

- `../../docs/boundaries/`
- `../../docs/mappings/`
- `../../docs/runbooks/ev-dashboard-ui-smoke-and-decommission.md`
- `../../docs/decisions/specs/2026-03-26-support-registry-phase-1-activation-design.md`
