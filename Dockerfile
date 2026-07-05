# 목표(요구사항): builder 스테이지.runtime 스테이지 분리 -> 최종 이미지 runtime 스테이지 기반

# 1. Builder Stage (작업실)
# local/CI/Prod 모두 같은 python 버전으로 고정
FROM python:3.13-slim AS builder

# uv 바이너리는 항상 공식 이미지를 사용
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 컨테이너 빌드시 명령이 실행될 작업 디렉토리
WORKDIR /app

# 오직 lockfiles만을 사용하여 의존성을 먼저 설치, 이 레이어는 캐시됨.
# 의존성 변경 후에만 다시 실행 — 매번 소스를 수정하지 않음.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# 소스를 복사
COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
	uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
RUN python manage.py collectstatic --noinput


# 2. Runtime Stage (실제 실행)
FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 시스템 전용유저 및 그룹 생성 (기본 uid/gid 10001번 할당)
RUN groupadd --system --gid 10001 appgroup && \
    useradd --system --uid 10001 --gid 10001 --no-create-home appuser

# builder에서 결과물을 복사해 올 때 소유권을 appuser:appgroup으로 변경
# DRF 앱 소스코드, 가상환경, 수집된 staticfiles의 소유권이 모두 전환됨.
COPY --from=builder --chown=appuser:appgroup /app /app

# Django 앱이 런타임에 미디어 파일 업로드나 로그 기록 등 쓰기 작업이 필요한 경로가 있다면 소유권 부여
RUN mkdir -p /app/media /app/logs && \
	chown -R  appuser:appgroup /app/media /app/logs
		 
ENV PATH="/app/.venv/bin:$PATH"

# USER 지시자를 통해 이후 명령 및 컨테이너 실행 유저를 비루트로 전환
USER 10001
 
EXPOSE 8000

CMD ["/app/.venv/bin/gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]