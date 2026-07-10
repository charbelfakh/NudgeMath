import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from strawberry.fastapi import GraphQLRouter

from hint_engine.api.limits import MAX_REQUEST_BYTES
from hint_engine.api.schema import schema
from hint_engine.auth import verify_token


def _client_key(request: Request) -> str:
    """Rate-limit bucket key for the caller.

    Prefers the first ``X-Forwarded-For`` hop when present (the app is expected
    to sit behind a reverse proxy in any deployment that faces a network); falls
    back to the socket peer. Both are spoofable without a trusted proxy — this is
    a spend ceiling, not an authorization boundary.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "anonymous"


async def get_context(request: Request) -> dict:
    """Resolve an ``Authorization: Bearer <token>`` header into an admin identity.

    Anonymous requests get ``admin_username=None`` and keep full student access;
    only the admin-gated resolvers check for a username.
    """
    admin_username = None
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        admin_username = verify_token(header[len("Bearer ") :].strip())
    return {
        "request": request,
        "admin_username": admin_username,
        "client_key": _client_key(request),
    }


graphql_router = GraphQLRouter(
    schema, graphql_ide="graphiql", context_getter=get_context
)

_raw_origins = os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:5173")
_allow_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    # Release the pooled Anthropic connection on shutdown.
    from hint_engine.llm_client import close_http_client

    close_http_client()


app = FastAPI(title="NudgeMath API", lifespan=lifespan)


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    """Reject oversized bodies before they are buffered into memory.

    Starlette has no default body limit, and ``transcribeProblem`` takes a base64
    image straight into memory. The per-field cap in the resolvers is the precise
    check; this is the cheap one that fires first.
    """
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared = int(content_length)
        except ValueError:
            return JSONResponse({"detail": "Invalid Content-Length."}, status_code=400)
        if declared > MAX_REQUEST_BYTES:
            return JSONResponse(
                {"detail": f"Request body too large (limit {MAX_REQUEST_BYTES} bytes)."},
                status_code=413,
            )
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(graphql_router, prefix="/graphql")
