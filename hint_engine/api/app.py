from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from hint_engine.api.schema import schema

graphql_router = GraphQLRouter(schema, graphql_ide="graphiql")

app = FastAPI(title="NudgeMath API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(graphql_router, prefix="/graphql")
