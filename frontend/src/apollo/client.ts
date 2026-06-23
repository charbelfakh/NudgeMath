import { ApolloClient, HttpLink, InMemoryCache } from "@apollo/client";

const graphqlUri =
  import.meta.env.VITE_GRAPHQL_URI ?? "http://localhost:8000/graphql";

export const apolloClient = new ApolloClient({
  link: new HttpLink({ uri: graphqlUri }),
  cache: new InMemoryCache(),
});
