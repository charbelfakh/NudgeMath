import { ApolloClient, ApolloLink, HttpLink, InMemoryCache } from "@apollo/client";
import { getToken } from "../auth/tokenStore";

const graphqlUri =
  import.meta.env.VITE_GRAPHQL_URI ?? "http://localhost:8000/graphql";

// Attach the admin bearer token (if any) to every request. Reads localStorage
// per-request so login/logout take effect without recreating the client.
const authLink = new ApolloLink((operation, forward) => {
  const token = getToken();
  if (token) {
    operation.setContext((prev: { headers?: Record<string, string> }) => ({
      headers: { ...(prev.headers ?? {}), Authorization: `Bearer ${token}` },
    }));
  }
  return forward(operation);
});

export const apolloClient = new ApolloClient({
  link: ApolloLink.from([authLink, new HttpLink({ uri: graphqlUri })]),
  cache: new InMemoryCache(),
});
