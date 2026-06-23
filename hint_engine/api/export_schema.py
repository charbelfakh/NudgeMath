"""Export the GraphQL SDL for frontend codegen."""

from strawberry.printer import print_schema

from hint_engine.api.schema import schema


def main() -> None:
    print(print_schema(schema))


if __name__ == "__main__":
    main()
