# TASK-004. PostgreSQL·Redis Docker Compose 구성

## 상태
완료

## 날짜
2026-10-29

## 작업 요약
프로젝트 루트에 `docker-compose.yml`을 만들었다.
- `db`: postgres:15-alpine, 포트 5432, 볼륨 `postgres_data`, `pg_isready` 헬스체크
- `redis`: redis:7-alpine, 포트 6379, 볼륨 `redis_data`, `redis-cli ping` 헬스체크
- 계정 정보는 `POSTGRES_USER/PASSWORD/DB` 환경변수로 주입한다. 값이 없으면 개발용 기본값(postgres / postgres / codelearning)을 쓴다(quickstart.md와 동일).

## 변경 파일
- docker-compose.yml (신규)
- backend/tests/unit/test_docker_compose.py (신규)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소가 아님). compose 파일이 없는 상태에서 7개 테스트 전부 실패 확인.
- GREEN 커밋: 해당 없음. 구현 후 7개 테스트 전부 통과.
- REFACTOR 커밋: 해당 없음
- 테스트 커버리지: 해당 없음 (설정 파일이라 코드 커버리지 대상이 없음)

테스트 내용: 서비스 존재, Postgres ≥15, Redis ≥7, 기본 포트 노출, 자격 증명 환경변수 주입, 명명 볼륨, 헬스체크.

## 기술 결정
- **앱 컨테이너는 포함하지 않음**: T004는 PostgreSQL과 Redis만 요구한다. backend/frontend는 로컬에서 직접 실행한다(백엔드 Dockerfile 없음).
- **기본값 `:-` 사용**: `.env`(T005 예정)가 없어도 `docker compose up`이 동작하게 하기 위해서다. 운영 환경에서는 반드시 `.env`로 덮어써야 한다.
- **이미지 태그 `-alpine`**: 용량이 작다. 메이저 버전만 고정했다.

## 비고
- **실제 기동 검증 완료**: Docker Desktop 설치(Docker 29.9.2) 후 `docker compose config -q` 통과, `docker compose up -d`로 db·redis 모두 healthy 확인. `psql`로 PostgreSQL 15.19 접속, `redis-cli ping`으로 PONG 응답을 확인했다. 컨테이너는 현재 실행 중이다.
- 테스트용 pytest/pyyaml은 프로젝트 밖 임시 venv에 설치해 실행했다. `backend/requirements.txt`에는 pyyaml이 없으므로, 이 테스트를 계속 쓰려면 개발 의존성에 `pyyaml` 추가가 필요하다.
- 5432/6379 포트를 이미 로컬 Postgres/Redis가 쓰고 있으면 충돌한다.
- 다음 작업: T005(.env.example), T006, T007.
