import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from hint_engine.api.schema import schema

graphql_router = GraphQLRouter(schema, graphql_ide="graphiql")

_raw_origins = os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:5173")
_allow_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app = FastAPI(title="NudgeMath API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(graphql_router, prefix="/graphql")
